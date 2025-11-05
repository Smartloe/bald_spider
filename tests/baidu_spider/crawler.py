from bald_spider.spider import Spider
from typing import Type
from bald_spider.settings.settins_manager import SettingsManager


class Crawler:
    def __init__(self, spider_cls, settings):
        self.spider_cls = spider_cls
        self.settings: SettingsManager = settings


class CrawlerProcess:

    def __init__(self, spider, settings=None):
        self.settings = settings

    def crawl(self, spider: Type[Spider]):
        crawler: Crawler = self._create_crawler(spider)

    def _create_crawler(self, spider_cls) -> Crawler:
        crawler = Crawler(spider_cls, self.settings)
