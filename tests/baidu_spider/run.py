import asyncio
import sys
import os
import time
from bald_spider.core.engine import Engine
from tests.baidu_spider.spiders.baidu import BaiduSpider, BaiduSpider2
from bald_spider.utils.project import get_settings
from bald_spider.settings.settins_manager import SettingsManager
from tests.baidu_spider.crawler import CrawlerProcess


async def run():
    # 添加当前目录到 Python 路径，确保可以导入 settings 模块
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)

    settings = get_settings("settings")
    process = CrawlerProcess(settings)
    await process.crawl(BaiduSpider)
    await process.crawl(BaiduSpider2)
    await process.start()
    # baidu_spider = BaiduSpider()
    # engine = Engine()
    # await engine.start_spider(baidu_spider)


s = time.time()
asyncio.run(run())
print(time.time() - s)
