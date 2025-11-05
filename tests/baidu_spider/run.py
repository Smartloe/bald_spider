import asyncio
from bald_spider.core.engine import Engine
from tests.baidu_spider.spiders.baidu import BaiduSpider, BaiduSpider2
from bald_spider.utils.project import get_settings
from bald_spider.settings.settins_manager import SettingsManager
from baidu_spider.crawler import CrawlerProcess


async def run():
    settings = get_settings("settings")
    process = CrawlerProcess(settings)
    process.crawl(BaiduSpider)
    process.crawl(BaiduSpider2)
    # baidu_spider = BaiduSpider()
    # engine = Engine()
    # await engine.start_spider(baidu_spider)


asyncio.run(run())
