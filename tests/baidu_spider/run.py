import asyncio
import sys
import os
import time
from tests.baidu_spider.spiders.baidu import BaiduSpider
from bald_spider.utils.project import get_settings
from bald_spider.crawler import CrawlerProcess
from bald_spider.utils import system as _


async def run():
    # 添加当前目录到 Python 路径，确保可以导入 settings 模块
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)

    settings = get_settings("settings")
    process = CrawlerProcess(settings)
    await process.crawl(BaiduSpider)
    await process.start()


s = time.time()
asyncio.run(run())
print(time.time() - s)
