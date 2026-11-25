from bald_spider.core.downloader import DownloaderBase
from bald_spider.core.processor import Processor
from bald_spider.core.scheduler import Scheduler
from typing import Callable
import asyncio
from bald_spider.event import spider_closed, spider_error, spider_opened
from bald_spider.exceptions import OutputError
from bald_spider.http.request import Request
from bald_spider.items.items import Item
from inspect import iscoroutine
from bald_spider.utils.spider import transform
from bald_spider.task_manager import TaskManager
from bald_spider.utils.log import get_logger
from bald_spider.utils.project import load_class


class _CloseRequest(Request):
    """唤醒阻塞在队列上的主循环；priority 极低，保证真实请求先被取出。"""

    def __init__(self):
        super().__init__("", priority=-(10**9))


_CLOSE_SENTINEL = _CloseRequest()


class Engine:
    def __init__(self, crawler):
        self.crawler = crawler
        self.settings = crawler.settings
        self.logger = get_logger(self.__class__.__name__, self.settings.get("LOG_LEVEL"))
        self.downloader: DownloaderBase | None = None
        self.start_requests = None
        self.spider = None
        self.scheduler: Scheduler | None = None
        self.processor: Processor | None = None
        self.task_manager: TaskManager = TaskManager(
            self.settings.getint("CONCURRENCY"), self.settings.get("LOG_LEVEL")
        )
        self.interval_log_task: asyncio.Task | None = None
        self.start_requests_task: asyncio.Task | None = None
        self.exit_monitor_task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()
        self._closed = False
        self._dispatching = 0
        self._cancelled_during_close = False
        self.running = False
        self.normal = True

    def _get_downloader_cls(self):
        downloader_cls = load_class(self.settings.get("DOWNLOADER"))
        if not issubclass(downloader_cls, DownloaderBase):
            raise TypeError(
                f"The downloader class ({self.settings.get('DOWNLOADER')}) doesn't fully implemented required interface."
            )
        return downloader_cls

    async def start_spider(self, spider):
        shutdown_requested = getattr(self.crawler, "_shutdown_requested", False)
        self.running = not shutdown_requested
        if shutdown_requested:
            self.normal = False
        self.logger.info(f"info bald_spider started.(project_name:{self.settings.get('PROJECT_NAME')})")
        self.spider = spider
        try:
            self.scheduler = Scheduler(self.crawler)
            if hasattr(self.scheduler, "open"):
                self.scheduler.open()
            downloader_cls = self._get_downloader_cls()
            self.downloader = downloader_cls.create_instance(self.crawler)
            if hasattr(self.downloader, "open"):
                self.downloader.open()
            self.processor = Processor(self.crawler)
            self.start_requests = spider.start_requests()
            await self._open_spider()
        except BaseException:
            # 启动阶段失败（含取消）时兜底释放已创建资源，避免会话泄漏。
            if not self._closed:
                await self._close_resources()
                try:
                    await self.crawler.subscriber.notify(spider_closed)
                    if self.crawler.stats is not None:
                        self.crawler.stats.close_spider(self.spider, "startup failed")
                except Exception:
                    self.logger.exception("error while cleaning up after startup failure")
            raise

    async def _open_spider(self):
        # 先等待 spider_opened 等钩子完成，保证 spider 级配置（如 headers）在首个请求前生效。
        await self.crawler.subscriber.notify(spider_opened)
        # 启动处理器的后台处理任务
        self.processor.start()
        self.interval_log_task = asyncio.create_task(
            self.scheduler.interval_log(self.settings.getint("INTERVAL"))
        )
        self.start_requests_task = asyncio.create_task(self._enqueue_start_requests())
        self.exit_monitor_task = asyncio.create_task(self._monitor_exit())
        try:
            await self.crawl()
        finally:
            for task in (self.start_requests_task, self.exit_monitor_task):
                if task is None or task.done():
                    continue
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                except Exception as exc:
                    self.logger.error(
                        f"background task raised during shutdown: {exc.__class__.__name__}: {exc}",
                        exc_info=(type(exc), exc, exc.__traceback__),
                    )

    async def _enqueue_start_requests(self):
        """后台任务：把 start_requests 产出的请求逐个入队，兼容同步/异步生成器。"""
        try:
            count = 0
            if hasattr(self.start_requests, "__aiter__"):
                async for request in self.start_requests:
                    if not self.running:
                        break
                    await self.enqueue_request(request)
                    count += 1
                    if count % 100 == 0:
                        await asyncio.sleep(0)
            else:
                for request in self.start_requests:
                    if not self.running:
                        break
                    await self.enqueue_request(request)
                    count += 1
                    if count % 100 == 0:
                        # 用户可能返回无限生成器；定期让出事件循环，保证取消/停机可生效。
                        await asyncio.sleep(0)
        except Exception as exc:
            self.logger.error(f"Error during start_requests: {exc}", exc_info=True)
            await self.crawler.subscriber.notify(spider_error, exc, self.spider)
        finally:
            self.start_requests = None

    async def _monitor_exit(self):
        """所有工作完成后（或被外部停机）唤醒主循环。使用普通 sleep 轮询，避免 wait_for 的取消问题。"""
        while True:
            if not self.running:
                # 外部停机（如 Ctrl+C）：主循环可能仍阻塞在取队列/信号量上，先解除等待再唤醒。
                self._stop_event.set()
                await self.scheduler.put_request(_CLOSE_SENTINEL)
                return
            if self.start_requests is None and await self._exit():
                self.running = False
                self._stop_event.set()
                await self.scheduler.put_request(_CLOSE_SENTINEL)
                return
            await asyncio.sleep(0.1)

    async def crawl(self):
        """主逻辑：阻塞等待请求，收到哨兵后退出。"""
        cancelled = False
        try:
            while self.running:
                request = await self._get_next_request()
                if request is _CLOSE_SENTINEL:
                    self.running = False
                    break
                # 请求已出队但尚未登记为任务：计入在途，避免被空闲监视器误判并丢弃。
                self._dispatching += 1
                try:
                    await self._crawl(request)
                finally:
                    self._dispatching -= 1
        except asyncio.CancelledError:
            # 取消时仍要完成资源清理与关闭事件，随后再向上传播。
            cancelled = True
        finally:
            self.running = False
            self._stop_event.set()
            await self._run_close(cancel_tasks=cancelled or not self.normal)
            if self._cancelled_during_close:
                cancelled = True
        if cancelled:
            raise asyncio.CancelledError

    async def _run_close(self, cancel_tasks):
        """执行关闭流程；关闭期间的取消要等待清理完成，并向上传播 CancelledError。"""
        close_task = asyncio.create_task(self.close_spider(cancel_tasks=cancel_tasks))
        while not close_task.done():
            try:
                await asyncio.shield(close_task)
            except asyncio.CancelledError:
                self._cancelled_during_close = True
                continue
        return close_task.result()

    async def _crawl(self, request):
        # 实现并发
        async def crawl_task():
            try:
                outputs = await self._fetch(request)
                # 处理outputs
                if outputs:
                    await self._handle_spider_output(outputs)
            except Exception as exc:
                self.crawler.stats.inc_value(f"spider_exceptions/{exc.__class__.__name__}")
                self.logger.error(
                    f"error while crawling {request}: {exc.__class__.__name__}: {exc}",
                    exc_info=(type(exc), exc, exc.__traceback__),
                )

        if not await self._acquire_semaphore():
            return
        self.task_manager.create_task(crawl_task())

    async def _acquire_semaphore(self):
        """可中断地获取并发信号量：停机事件触发时立即返回 False。"""
        if self._stop_event.is_set() or not self.running:
            return False
        # 快路径：有空闲名额时同步获取，不让出事件循环，避免“请求已出队但尚未登记”被误判为空闲。
        if not self.task_manager.semaphore.locked():
            await self.task_manager.semaphore.acquire()
            return True
        acquire = asyncio.create_task(self.task_manager.semaphore.acquire())
        stop = asyncio.create_task(self._stop_event.wait())
        try:
            done, pending = await asyncio.wait(
                {acquire, stop}, return_when=asyncio.FIRST_COMPLETED
            )
        except asyncio.CancelledError:
            for task in (acquire, stop):
                if not task.done():
                    task.cancel()
            # 已拿到许可但随后被取消时归还，避免关闭期信号量泄漏。
            if acquire.done() and not acquire.cancelled() and acquire.exception() is None:
                self.task_manager.semaphore.release()
            raise
        finally:
            for task in (acquire, stop):
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except (asyncio.CancelledError, Exception):
                        pass
        if self._stop_event.is_set() or not self.running:
            if acquire.done() and not acquire.cancelled() and acquire.exception() is None:
                self.task_manager.semaphore.release()
            return False
        return acquire.done() and acquire.exception() is None

    async def _fetch(self, request):
        async def _success(_response):
            callback: Callable = request.callback or self.spider.parse
            result = callback(_response)
            if iscoroutine(result):
                result = await result
            if result:
                # 同步/异步回调统一走 transform，避免协程返回值被静默丢弃。
                return transform(result)

        _response = await self.downloader.fetch(request)
        if _response is None:
            return None
        outputs = await _success(_response)
        return outputs

    async def enqueue_request(self, request):
        await self._schedule_request(request)

    async def requeue_request(self, request):
        """重新入队（中间件返回 Request 时使用）。

        交由无并发许可的 Processor 任务转交调度队列，避免持有信号量的
        crawl_task 直接阻塞在有界调度队列上而与其他等待形成死锁。
        """
        if self.processor is not None:
            await self.processor.enqueue(request)
        else:
            await self._schedule_request(request)

    async def _schedule_request(self, request):
        # TODO 去重
        await self.scheduler.enqueue_request(request)

    async def _get_next_request(self):
        return await self.scheduler.next_request()

    async def _handle_spider_output(self, outputs):
        count = 0
        async for spider_output in outputs:
            if isinstance(spider_output, (Request, Item)):
                await self.processor.enqueue(spider_output)
            elif isinstance(spider_output, Exception):
                await self.crawler.subscriber.notify(spider_error, spider_output, self.spider)
                raise spider_output
            else:
                raise OutputError(f"{type(self.spider)} must return `Request` or `Item`")
            count += 1
            if count % 100 == 0:
                # 用户可能返回无限同步生成器；定期让出事件循环，保证取消与超时能生效。
                await asyncio.sleep(0)

    async def _exit(self):
        if (
            self._dispatching == 0
            and self.scheduler.idle()
            and self.downloader.idle()
            and self.task_manager.all_done()
            and self.processor.idle()
        ):
            return True
        return False

    async def _close_resources(self):
        """释放下载器与后台任务；可重复调用，单步失败不影响其余清理。"""
        if self._closed:
            return
        self._closed = True
        if self.interval_log_task is not None and not self.interval_log_task.done():
            self.interval_log_task.cancel()
            try:
                await self.interval_log_task
            except asyncio.CancelledError:
                pass
            except Exception:
                self.logger.exception("error while cancelling interval log task")
        if self.processor is not None:
            try:
                await self.processor.close()
            except Exception:
                self.logger.exception("error while closing processor")
        if self.downloader is not None:
            try:
                await self.downloader.close()
            except Exception:
                self.logger.exception("error while closing downloader")

    async def close_spider(self, cancel_tasks=False):
        if self._closed:
            return
        tasks = list(self.task_manager.current_task)
        if cancel_tasks:
            # 取消场景下，在途任务可能仍在无限产出，必须先取消，否则关闭会永久挂起。
            for task in tasks:
                task.cancel()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, Exception):
                self.logger.error(
                    f"task raised unhandled exception during shutdown: {result.__class__.__name__}: {result}",
                    exc_info=(type(result), result, result.__traceback__),
                )
        await self._close_resources()
        if self.normal:
            await self.crawler.close()
        else:
            # ctrl+c 等非正常关闭：补发关闭事件并写入统计（close_spider 已做幂等保护）。
            await self.crawler.subscriber.notify(spider_closed)
            self.crawler.stats.close_spider(self.spider, "shutdown")
