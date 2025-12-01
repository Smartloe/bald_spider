import asyncio

from httpx._transports import default
from bald_spider.utils.pqueue import SpoderPriorityQueue
from bald_spider.utils.log import get_logger


class Scheduler:
    def __init__(self, crawler):
        self.request_queue: SpoderPriorityQueue | None = None
        self.crawler = crawler
        self.item_count = 0
        self.response_count = 0
        self.logger = get_logger(self.__class__.__name__, log_level=crawler.settings.get("LOG_LEVEL"))

    def open(self):
        self.request_queue = SpoderPriorityQueue()

    async def next_request(self):
        request = await self.request_queue.get()
        return request

    async def enqueue_request(self, request):
        await self.request_queue.put(request)
        self.crawler.stats.inc_value("request_scheduler_count")

    def idle(self) -> bool:
        """检查调度器是否空闲"""
        if self.request_queue is None:
            return True
        return self.request_queue.empty()

    async def interval_log(self, interval):
        while True:
            last_item_count = self.crawler.stats.get_value("item_successful_count", default=0)
            last_response_count = self.crawler.stats.get_value("response_received_count", default=0)
            item_rate = last_item_count - self.item_count
            response_rate = last_response_count - self.response_count
            self.item_count, self.response_count = item_rate, response_rate
            self.logger.info(
                f"Crawled {last_response_count} pages (at {response_rate} pages/{interval}s),"
                f"Got {last_item_count} pages (at {item_rate} pages/{interval}s),"
            )
            await asyncio.sleep(interval)

    def __len__(self):
        return self.request_queue.qsize()
