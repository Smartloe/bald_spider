from bald_spider.http.request import Request
from bald_spider.spider import Spider
import asyncio


class BaiduSpider(Spider):
    start_urls = ["https://www.baidu.com", "https://www.baidu.com"]

    async def parse(self, response):
        print(f"parse {response}")
        # for i in range(10):
        #     url = "https://www.baidu.com"
        #     request = Request(url)
        #     yield request
