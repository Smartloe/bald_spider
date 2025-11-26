from bald_spider.http.request import Request
from bald_spider.spider import Spider
import asyncio
from tests.baidu_spider.items import BaiduItem


class BaiduSpider(Spider):
    start_urls = ["https://www.baidu.com", "https://www.baidu.com"]

    @classmethod
    def create_instance(cls, crawler):
        # 实例化的逻辑
        o = cls()
        o.crawler = crawler
        return o

    async def parse(self, response):
        for i in range(10):
            url = "https://www.baidu.com"
            request = Request(url, callback=self.parse_page)
            yield request

    def parse_page(self, response):
        for i in range(10):
            url = "https://www.baidu.com"
            request = Request(url, callback=self.parse_detail)
            yield request

    def parse_detail(self, response):
        # print("parse_detail2", response)
        item = BaiduItem()
        item["url"] = "www.baidu.com"
        item["title"] = "百度首页"
        # item["aaa"] = "百度首页"
        yield item
