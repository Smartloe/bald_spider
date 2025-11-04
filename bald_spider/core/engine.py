from bald_spider.core.downloader import Downloader
from bald_spider.core.scheduler import Scheduler
from typing import Optional, Generator, Callable
import asyncio
from bald_spider.exceptions import OutputError, TransformTypeError
from bald_spider.http.request import Request
from bald_spider.spider import Spider
from inspect import iscoroutine
from bald_spider.utils.spider import transform
from bald_spider.task_manager import TaskManager


class Engine:
    def __init__(self):
        self.downloader: Optional[Downloader] = None
        self.start_requests: Optional[Generator] = None
        self.spider: Optional[Scheduler] = None
        self.scheduler: Optional[Scheduler] = None
        self.task_manager: TaskManager = TaskManager()
        self.running = False

    async def start_spider(self, spider):
        self.running = True
        self.spider = spider
        self.scheduler = Scheduler()
        if hasattr(self.scheduler, "open"):
            self.scheduler.open()
        self.downloader = Downloader()
        self.start_requests = iter(spider.start_requests())
        await self._open_spider()

    async def _open_spider(self):
        crawling = asyncio.create_task(self.crawl())
        # 这里可以做其他的事情
        await crawling

    async def crawl(self):
        """主逻辑"""
        while self.running:
            request = await self._get_next_request()
            if request is not None:
                await self._crawl(request)
            else:
                try:
                    start_request = next(self.start_requests)  # noqa

                except StopIteration:
                    self.start_requests = None
                except Exception as e:
                    # 1.发起请求的task运行完毕
                    # 2.调度器是否空闲
                    # 3.下载器是否空闲
                    if not await self._exit():
                        continue

                    self.running = False
                else:
                    # 入队
                    await self.enqueue_request(start_request)

    async def _crawl(self, request):
        # 实现并发
        async def crawl_task():
            outputs = await self._fetch(request)
            # 处理outputs
            if outputs:
                await self._handle_spider_output(outputs)

        # asyncio.create_task(crawl_task())
        await self.task_manager.semaphore.acquire()
        self.task_manager.create_task(crawl_task())

    async def _fetch(self, request):
        async def _success(_response):
            callback: Callable = request.callback or self.spider.parse
            result = callback(_response)
            if result:
                if iscoroutine(result):
                    await result
                else:
                    return transform(result)

        _response = await self.downloader.fetch(request)
        outputs = await _success(_response)
        return outputs

    async def enqueue_request(self, request):
        await self._schedule_request(request)

    async def _schedule_request(self, request):
        # todo 去重
        await self.scheduler.enqueue_request(request)

    async def _get_next_request(self):
        return await self.scheduler.next_request()

    async def _handle_spider_output(self, outputs):
        async for spider_output in outputs:
            if isinstance(spider_output, Request):
                await self.enqueue_request(spider_output)
            # todo 判断是否为数据,暂定为Item
            else:
                raise OutputError(f"{type(self.spider)} must return `Request` or `Item`")

    async def _exit(self):
        if self.scheduler.idle() and self.downloader.idle() and self.task_manager.all_done():
            return True
        return False
