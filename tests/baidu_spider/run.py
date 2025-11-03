import asyncio
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bald_spider.core.engine import Engine
from tests.baidu_spider.baidu import BaiduSpider


async def run():
    baidu_spider = BaiduSpider()
    engine = Engine()
    await engine.start_spider(baidu_spider)


asyncio.run(run())

