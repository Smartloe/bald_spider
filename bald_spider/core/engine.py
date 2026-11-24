from bald_spider.core.downloader import DownloaderBase
from bald_spider.core.processor import Processor
from bald_spider.core.scheduler import Scheduler
from collections.abc import Generator
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


class Engine:
    def __init__(self, crawler):
        self.logger = get_logger(self.__class__.__name__)
        self.crawler = crawler
        self.settings = crawler.settings
        self.downloader: DownloaderBase | None = None
        self.start_requests: Generator | None = None
        self.spider: Scheduler | None = None
        self.scheduler: Scheduler | None = None
        self.processor: Processor | None = None
        self.task_manager: TaskManager = TaskManager(self.settings.getint("CONCURRENCY"))
        self.interval_log_task: asyncio.Task | None = None
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
        self.running = True
        self.logger.info(f"info bald_spider started.(project_name:{self.settings.get('PROJECT_NAME')})")
        self.spider = spider
        self.scheduler = Scheduler(self.crawler)
        if hasattr(self.scheduler, "open"):
            self.scheduler.open()
        downloader_cls = self._get_downloader_cls()
        self.downloader = downloader_cls.create_instance(self.crawler)
        if hasattr(self.downloader, "open"):
            self.downloader.open()
        self.processor = Processor(self.crawler)
        self.start_requests = iter(spider.start_requests())
        await self._open_spider()

    async def _open_spider(self):
        # 先等待 spider_opened 等钩子完成，保证 spider 级配置（如 headers）在首个请求前生效。
        await self.crawler.subscriber.notify(spider_opened)
        # 启动处理器的后台处理任务
        asyncio.create_task(self.processor.process())
        crawling = asyncio.create_task(self.crawl())
        # 这里可以做其他的事情
        self.interval_log_task = asyncio.create_task(
            self.scheduler.interval_log(self.settings.getint("INTERVAL"))
        )
        await crawling

    async def crawl(self):
        """主逻辑"""
        while self.running:
            request = await self._get_next_request()
            if request is not None:
                await self._crawl(request)
                continue
            if self.start_requests is not None:
                try:
                    start_request = next(self.start_requests)
                except StopIteration:
                    # 1.发起请求的task运行完毕
                    self.start_requests = None
                except Exception as e:
                    # 2.start_requests 抛异常：记录并通知，避免静默吞掉后死循环
                    self.start_requests = None
                    self.logger.error(f"Error during start_requests: {e}", exc_info=True)
                    asyncio.create_task(
                        self.crawler.subscriber.notify(spider_error, e, self.spider)
                    )
                else:
                    # 入队
                    await self.enqueue_request(start_request)
                    continue
            # 3.调度器、下载器、任务、处理器是否都空闲
            if not await self._exit():
                continue
            self.running = False
        if not self.running:
            await self.close_spider()

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

        # asyncio.create_task(crawl_task())
        await self.task_manager.semaphore.acquire()
        self.task_manager.create_task(crawl_task())

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

    async def _schedule_request(self, request):
        # TODO 去重
        await self.scheduler.enqueue_request(request)

    async def _get_next_request(self):
        return await self.scheduler.next_request()

    async def _handle_spider_output(self, outputs):
        async for spider_output in outputs:
            if isinstance(spider_output, (Request, Item)):
                await self.processor.enqueue(spider_output)
            elif isinstance(spider_output, Exception):
                asyncio.create_task(self.crawler.subscriber.notify(spider_error, spider_output, self.spider))
                raise spider_output
            else:
                raise OutputError(f"{type(self.spider)} must return `Request` or `Item`")

    async def _exit(self):
        if self.scheduler.idle() and self.downloader.idle() and self.task_manager.all_done() and self.processor.idle():
            return True
        return False

    async def close_spider(self):
        if self.interval_log_task is not None and not self.interval_log_task.done():
            self.interval_log_task.cancel()
            try:
                await self.interval_log_task
            except asyncio.CancelledError:
                pass
        results = await asyncio.gather(*self.task_manager.current_task, return_exceptions=True)
        for result in results:
            if isinstance(result, Exception):
                self.logger.error(
                    f"task raised unhandled exception during shutdown: {result.__class__.__name__}: {result}",
                    exc_info=(type(result), result, result.__traceback__),
                )
        await self.downloader.close()
        if self.normal:
            await self.crawler.close()
        else:
            # ctrl+c 等非正常关闭：统计已由信号处理器记录，这里补发关闭事件。
            await self.crawler.subscriber.notify(spider_closed)
