import asyncio
import signal
from bald_spider.core.engine import Engine
from bald_spider.spider import Spider
from typing import Final, Set, Type, Optional
from bald_spider.settings.settins_manager import SettingsManager
from bald_spider.exceptions import SpiderTypeError
from bald_spider.utils.project import merge_settings
from bald_spider.utils.log import get_logger

logger = get_logger(__name__)


class Crawler:
    def __init__(self, spider_cls, settings):
        self.spider_cls = spider_cls
        self.settings: SettingsManager = settings.copy()
        self.spider: Optional[Spider] = None
        self.engine: Optional[Engine] = None

    async def crawl(self):
        self.spider = self._create_spider()
        self.engine = self._create_engine()
        await self.engine.start_spider(self.spider)

    def _create_engine(self):
        engine = Engine(self)
        return engine

    def _create_spider(self) -> Spider:
        spider = self.spider_cls.create_instance(self)
        self._set_spider(spider)
        return spider

    def _set_spider(self, spider):
        merge_settings(self.spider_cls, self.settings)


class CrawlerProcess:

    def __init__(self, settings=None):
        self.crawlers: Final[Set] = set()
        self._active: Final[Set] = set()
        self.settings = settings
        signal.signal(signal.SIGINT, self._shutdown)

    async def crawl(self, spider: Type[Spider]):
        crawler: Crawler = self._create_crawler(spider)
        self.crawlers.add(crawler)
        task = self._crawl(crawler)
        self._active.add(task)

    @staticmethod
    def _crawl(crawler):
        return asyncio.create_task(crawler.crawl())

    async def start(self):
        await asyncio.gather(*self._active)

    def _create_crawler(self, spider_cls) -> Crawler:
        if isinstance(spider_cls, str):
            raise SpiderTypeError(f"{type(self)}.crawl args: String is not supported.")
        crawler = Crawler(spider_cls, self.settings)
        return crawler

    def _shutdown(self, signum, frame):
        for crawler in self.crawlers:
            crawler.engine.running = False
        logger.warning(f"sipders received `ctrl+c` signal, closed.")
