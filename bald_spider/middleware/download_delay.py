import asyncio
from random import uniform
from bald_spider.exceptions import NotConfigured
from bald_spider.utils.log import get_logger


class DownloadDelay:
    def __init__(self, settings, log_level) -> None:
        self.delay = settings.getfloat("DOWNLOAD_DELAY")
        if not self.delay:
            raise NotConfigured
        self.randomness = settings.getbool("RANDOMNESS")
        if "RANDEOM_RANGE" in settings:
            # 兼容旧拼写；显式设置时优先。
            self.floor, self.upper = settings.getlist("RANDEOM_RANGE")
        else:
            self.floor, self.upper = settings.getlist("RANDOM_RANGE")
        self.logger = get_logger(self.__class__.__name__, log_level)

    @classmethod
    def create_instance(cls, crawler):
        o = cls(settings=crawler.settings, log_level=crawler.settings.get("LOG_LEVEL"))
        return o

    async def process_request(self, _request, _spider):
        if self.randomness:
            await asyncio.sleep(uniform(self.delay * self.floor, self.delay * self.upper))
        else:
            await asyncio.sleep(self.delay)
