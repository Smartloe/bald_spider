from bald_spider.core.downloader import Downloader
from typing import Optional, Generator


class Engine:
    def __init__(self):
        self.downloader: Downloader = Downloader()
        self.start_requests: Optional[Generator] = None

    def start_spider(self, spider):
        self.start_requests = iter(spider.start_requests())
        self.crawl()

    def crawl(self):
        """主逻辑"""
        while True:
            try:
                start_request = next(self.start_requests)  # noqa
                self.downloader.download(start_request)
            except StopIteration:
                self.start_requests = None
            except Exception as e:
                break
