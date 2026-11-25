from asyncio import Queue
import asyncio
from bald_spider import Request, Item
from bald_spider.event import item_successful
from bald_spider.utils.log import get_logger


class Processor:
    def __init__(self, crawler):
        self.crawler = crawler
        # 处理器队列不设上限：产出侧已由 CONCURRENCY 限制；对处理器队列做阻塞限制
        # 会在“scheduler 满 + 主循环等待并发许可”时形成等待环。
        self.queue: Queue = Queue()
        settings = getattr(crawler, "settings", None)
        log_level = settings.get("LOG_LEVEL") if settings is not None else None
        self.logger = get_logger(self.__class__.__name__, log_level)
        self._processing = False
        self._task: asyncio.Task | None = None
        self._closed = False

    def start(self):
        """确保存在一个处理任务；可重复调用。"""
        if self._closed:
            return None
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self.process())
        return self._task

    async def close(self):
        self._closed = True
        if self._task is not None and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def process(self):
        if self._processing:
            return
        self._processing = True
        try:
            while len(self) > 0:
                result = await self.queue.get()
                try:
                    if isinstance(result, Request):
                        await self.crawler.engine.enqueue_request(result)
                    else:
                        assert isinstance(result, Item)
                        await self._process_item(result)
                except Exception as exc:
                    stats = getattr(self.crawler, "stats", None)
                    if stats is not None:
                        stats.inc_value(f"processor_exceptions/{exc.__class__.__name__}")
                    self.logger.error(
                        f"error while processing {type(result).__name__}: {exc.__class__.__name__}: {exc}",
                        exc_info=(type(exc), exc, exc.__traceback__),
                    )
                finally:
                    self.queue.task_done()
        finally:
            self._processing = False
            # 关闭处理循环与 enqueue 之间的竞态：若期间又有新元素，重新拉起处理任务。
            if not self._closed and len(self) > 0:
                self.start()

    async def _process_item(self, item: Item):
        self.crawler.stats.inc_value("item_successful_count")
        await self.crawler.subscriber.notify(item_successful, item, self.crawler.spider)
        # 使用异步日志替代同步print，避免阻塞事件循环
        self.logger.info(f"Item processed: {item}")

    async def enqueue(self, output: Request | Item):
        await self.queue.put(output)
        # 由 Processor 自己管理处理任务的拉起，避免多次重复创建。
        self.start()

    def idle(self):
        return len(self) == 0 and not self._processing

    def __len__(self):
        return self.queue.qsize()
