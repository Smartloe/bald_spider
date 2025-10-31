from typing import Optional
from bald_spider.utils.pqueue import SpoderPriorityQueue


class Scheduler:
    def __init__(self):
        self.request_queue: Optional[SpoderPriorityQueue] = None

    def open(self):
        self.request_queue = SpoderPriorityQueue()

    async def next_request(self):
        request = await self.request_queue.get()
        return request

    async def enqueue_request(self, request):
        await self.request_queue.put(request)
