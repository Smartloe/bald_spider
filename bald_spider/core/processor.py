from asyncio import Queue
import asyncio
from bald_spider import Request, Item
from bald_spider.utils.log import get_logger


class Processor:
    def __init__(self, crawler):
        self.crawler = crawler
        self.queue: Queue = Queue()
        self.logger = get_logger(self.__class__.__name__)
        self._processing = False

    async def process(self):
        if self._processing:
            return
        self._processing = True
        try:
            while not self.idle():
                result = await self.queue.get()
                if isinstance(result, Request):
                    await self.crawler.engine.enqueue_request(result)
                else:
                    assert isinstance(result, Item)
                    await self._process_item(result)
                self.queue.task_done()
        finally:
            self._processing = False

    async def _process_item(self, item: Item):
        self.crawler.stats.inc_value("item_successful_count")
        # 使用异步日志替代同步print，避免阻塞事件循环
        self.logger.info(f"Item processed: {item}")

    async def enqueue(self, output: Request | Item):
        await self.queue.put(output)
        # 不要每次都立即处理，让处理器自己管理
        if not self._processing:
            asyncio.create_task(self.process())

    def idle(self):
        return len(self) == 0

    def __len__(self):
        return self.queue.qsize()
