import asyncio

from bald_spider.event import request_scheduled
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
        # 有界队列为生产者提供背压；0 表示不限制。
        maxsize = self.crawler.settings.getint("SCHEDULER_QUEUE_SIZE")
        self.request_queue = SpoderPriorityQueue(maxsize=maxsize)

    async def next_request(self):
        # 阻塞等待，由 Engine 在空闲时投放关闭哨兵唤醒，避免轮询与取消问题。
        return await self.request_queue.get()

    async def put_request(self, request):
        await self.request_queue.put(request)

    async def enqueue_request(self, request):
        await self.request_queue.put(request)
        await self.crawler.subscriber.notify(request_scheduled, request, self.crawler.spider)
        self.crawler.stats.inc_value("request_scheduler_count")

    def idle(self) -> bool:
        """检查调度器是否空闲"""
        if self.request_queue is None:
            return True
        return self.request_queue.empty()

    async def interval_log(self, interval):
        # 防御性钳制，避免 0/负数导致忙轮询或 ValueError 使日志任务退出。
        interval = max(float(interval), 0.1)
        while True:
            last_item_count = self.crawler.stats.get_value("item_successful_count", default=0)
            last_response_count = self.crawler.stats.get_value("response_received_count", default=0)
            item_rate = last_item_count - self.item_count
            response_rate = last_response_count - self.response_count
            self.item_count, self.response_count = last_item_count, last_response_count
            self.logger.info(
                f"Crawled {last_response_count} pages (at {response_rate} pages/{interval}s), "
                f"Got {last_item_count} items (at {item_rate} items/{interval}s)"
            )
            await asyncio.sleep(interval)

    def __len__(self):
        if self.request_queue is None:
            return 0
        return self.request_queue.qsize()
