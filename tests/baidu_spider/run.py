import asyncio
from bald_spider.core.engine import Engine
from tests.baidu_spider.baidu import BaiduSpider
from bald_spider.utils.project import get_settings
from bald_spider.settings.settins_manager import SettingsManager


async def run():
    settings = get_settings("settings")
    baidu_spider = BaiduSpider()
    engine = Engine()
    await engine.start_spider(baidu_spider)


asyncio.run(run())
