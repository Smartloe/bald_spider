import asyncio
import time
from tests.baidu_spider.spiders.baidu import BaiduSpider
from bald_spider.utils.project import get_settings
from bald_spider.crawler import CrawlerProcess
from bald_spider.utils import system as _


async def run():
    settings = get_settings("settings")
    process = CrawlerProcess(settings)
    await process.crawl(BaiduSpider)
    await process.start()


s = time.time()
asyncio.run(run())
print(time.time() - s)
