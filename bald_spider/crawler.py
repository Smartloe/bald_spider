import asyncio
import signal
from bald_spider.core.engine import Engine
from bald_spider.event import spider_closed, spider_opened
from bald_spider.spider import Spider
from typing import Final, Set, Type
from bald_spider.settings.settings_manager import SettingsManager
from bald_spider.exceptions import SpiderTypeError
from bald_spider.stats_collector import StatsCollector
from bald_spider.subscriber import Subscriber
from bald_spider.utils.project import merge_settings
from bald_spider.utils.log import get_logger
from bald_spider.utils.date import now

logger = get_logger(__name__)


class Crawler:
    def __init__(self, spider_cls, settings):
        self.spider_cls = spider_cls
        self.settings: SettingsManager = settings.copy()
        self.spider: Spider | None = None
        self.engine: Engine | None = None
        self.stats: StatsCollector | None = None
        self.subscriber: Subscriber | None = None
        self._shutdown_requested = False

    async def crawl(self):
        self.subscriber = self._create_subscriber()
        self.spider = self._create_spider()
        self.engine = self._create_engine()
        self.stats = self._create_stats()
        await self.engine.start_spider(self.spider)

    def _create_subscriber(self):
        return Subscriber(self.settings.get("LOG_LEVEL"))

    def _create_engine(self):
        engine = Engine(self)
        return engine

    def _create_stats(self):
        stats = StatsCollector(self)
        stats["start_time"] = now()
        return stats

    def _create_spider(self) -> Spider:
        spider = self.spider_cls.create_instance(self)
        self._set_spider(spider)
        return spider

    def _set_spider(self, spider):
        self.subscriber.subscriber(spider.spider_opened, event=spider_opened)
        self.subscriber.subscriber(spider.spider_closed, event=spider_closed)
        merge_settings(self.spider_cls, self.settings)

    async def close(self, reason="finished"):
        await self.subscriber.notify(spider_closed)
        self.stats.close_spider(self.spider, reason)


class CrawlerProcess:

    def __init__(self, settings=None):
        self.crawlers: Final[Set] = set()
        self._active: Final[Set] = set()
        self.settings = settings if settings is not None else SettingsManager()
        self._previous_sigint = None
        self._signal_installed = False

    def _install_signal_handler(self):
        if self._signal_installed:
            return
        try:
            self._previous_sigint = signal.getsignal(signal.SIGINT)
            signal.signal(signal.SIGINT, self._shutdown)
            self._signal_installed = True
        except ValueError:
            # 非主线程无法注册信号处理器，退化为默认行为。
            logger.warning("SIGINT handler not installed (not running in main thread).")

    def _restore_signal_handler(self):
        if not self._signal_installed:
            return
        try:
            signal.signal(signal.SIGINT, self._previous_sigint)
        except ValueError:
            pass
        finally:
            self._signal_installed = False
            self._previous_sigint = None

    async def crawl(self, spider: Type[Spider]):
        crawler: Crawler = self._create_crawler(spider)
        self.crawlers.add(crawler)
        task = self._crawl(crawler)
        self._active.add(task)

    @staticmethod
    def _crawl(crawler):
        return asyncio.create_task(crawler.crawl())

    async def start(self):
        self._install_signal_handler()
        try:
            await asyncio.gather(*self._active)
        except BaseException:
            # 任一爬虫失败时取消其余兄弟任务，避免进程常驻时后台残留。
            siblings = [task for task in self._active if not task.done()]
            for task in siblings:
                task.cancel()
            if siblings:
                await asyncio.gather(*siblings, return_exceptions=True)
            raise
        finally:
            self._restore_signal_handler()

    def _create_crawler(self, spider_cls) -> Crawler:
        if isinstance(spider_cls, str):
            raise SpiderTypeError(f"{type(self)}.crawl args: String is not supported.")
        crawler = Crawler(spider_cls, self.settings)
        return crawler

    def _shutdown(self, signum, frame):
        for crawler in self.crawlers:
            # 记录停机请求，即使 SIGINT 落在 Engine 刚创建、running 尚未置 True 的窗口也不会丢失。
            crawler._shutdown_requested = True
            if crawler.engine is not None:
                crawler.engine.running = False
                crawler.engine.normal = False
            if crawler.stats is not None and crawler.spider is not None:
                crawler.stats.close_spider(crawler.spider, "ctrl + c")
        logger.warning(f"spiders received `ctrl + c` signal, closed.")
