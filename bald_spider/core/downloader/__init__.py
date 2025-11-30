from re import A
from typing import Final, Set
from contextlib import asynccontextmanager

from attr import has
from bald_spider import Request
from bald_spider.http.response import Response
from bald_spider.utils.log import get_logger
from abc import ABC, abstractmethod, ABCMeta


class DwonloaderMeta(ABCMeta):

    def __subclasscheck__(self, subclass) -> bool:
        requied_methods = ("download", "fetch", "create_instance", "close")
        is_subclass = all(
            hasattr(subclass, method) and callable(getattr(subclass, method, None)) for method in requied_methods
        )
        return is_subclass


class DownloaderBase(ABC, metaclass=DwonloaderMeta):
    def __init__(self, crawler) -> None:
        self.crawler = crawler
        self._active = ActiveRequestManger()
        self.logger = get_logger(self.__class__.__name__, crawler.settings.get("LOG_LEVEL"))

    @classmethod
    def create_instance(cls, *args, **kwargs):
        return cls(*args, **kwargs)

    def open(self):
        self.logger.info(
            f"{self.crawler.spider} <downloader class: {type(self).__name__}"
            f"<concurrency: {self.crawler.settings.getint('CONCURRENCY')}"
        )

    async def fetch(self, request) -> Response | None:
        async with self._active(request):
            response = await self.download(request)
            return response

    @abstractmethod
    async def download(self, request: Request) -> Response | None:
        pass

    def idle(self) -> bool:
        return len(self) == 0

    def __len__(self):
        return len(self._active)

    async def close(self):
        pass


class ActiveRequestManger:
    def __init__(self):
        self._active: Final[Set] = set()

    def add(self, request):
        print("add request", request)
        self._active.add(request)

    def remove(self, request):
        print("remove request", request)
        self._active.remove(request)

    @asynccontextmanager
    async def __call__(self, request):
        try:
            yield self.add(request)
        finally:
            self.remove(request)

    def __len__(self):
        return len(self._active)
