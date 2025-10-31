from bald_spider.core.downloader import Downloader
from bald_spider.core.scheduler import Scheduler
from typing import Optional, Generator
import asyncio


class Engine:
    def __init__(self):
        self.downloader: Optional[Downloader] = None
        self.start_requests: Optional[Generator] = None
        self.scheduler: Optional[Scheduler] = None

    async def start_spider(self, spider):
        self.scheduler = Scheduler()
        if hasattr(self.scheduler, "open"):
            self.scheduler.open()
        self.downloader = Downloader()
        self.start_requests = iter(spider.start_requests())
        await self.crawl()

    async def crawl(self):
        """主逻辑"""
        while True:
            if request := await self._get_next_request() is not None:
                await self._crawl(request)
            else:
                try:
                    start_request = next(self.start_requests)  # noqa

                except StopIteration:
                    self.start_requests = None
                except Exception as e:
                    break
                else:
                    # 入队
                    await self.enqueue_request(start_request)

    async def _crawl(self, request):
        await self.downloader.download(request)

    async def enqueue_request(self, request):
        await self._schedule_request(request)

    async def _schedule_request(self, request):
        # todo 去重
        await self.scheduler.enqueue_request(request)

    async def _get_next_request(self):
        return await self.scheduler.next_request()
