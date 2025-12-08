import asyncio
from bald_spider import Request
from bald_spider import event
from bald_spider.spider import Spider
from tests.baidu_spider.items import BaiduItem
from bald_spider.event import spider_error


class BaiduSpider(Spider):
    start_urls = ["https://www.baidu.com", "https://www.baidu.com"]

    @classmethod
    def create_instance(cls, crawler):
        # 实例化的逻辑
        o = cls()
        o.crawler = crawler
        crawler.subscriber.subscriber(o.spider_error, event=spider_error)
        return o

    async def parse(self, response):
        for i in range(2):
            url = "https://www.baidu.com"
            request = Request(url, callback=self.parse_page)
            yield request

    async def parse_page(self, response):
        1 / 0
        for i in range(5):
            url = "https://www.baidu.com"
            request = Request(url, callback=self.parse_detail)
            yield request

    def parse_detail(self, response):
        item = BaiduItem()
        item["url"] = response.url
        item["title"] = response.xpath("//title/text()").get()
        yield item

    async def spider_opened(self):
        print("爬虫开始了")

    async def spider_closed(self):
        print("爬虫结束了")

    async def spider_error(self, exc, spider):
        print(f"爬虫出错了{exc},请紧急处理一下!")
