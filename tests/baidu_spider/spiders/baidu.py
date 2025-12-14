import asyncio
from bald_spider import Request
from bald_spider import event
from bald_spider.spider import Spider
from tests.baidu_spider.items import BaiduItem
from bald_spider.event import spider_error


class BaiduSpider(Spider):
    start_urls = ["https://www.baidu.com", "https://www.baidu.com"]
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36 Edg/143.0.0.0"
    }

    async def parse(self, response):
        # 减少请求数量，避免指数级爆炸
        for i in range(1):  # 改为1个
            url = "https://www.baidu.com"
            request = Request(url, callback=self.parse_page)
            yield request

    async def parse_page(self, response):
        # 减少请求数量，使用正确的URL
        for i in range(2):  # 改为2个
            meta = {"dont_retry": True}
            url = "https://www.baidu.com"  # 修复URL
            request = Request(url, callback=self.parse_detail, meta=meta)
            yield request

    def parse_detail(self, response):
        item = BaiduItem()
        item["url"] = response.url
        item["title"] = response.xpath("//title/text()").get()
        yield item

    # async def spider_opened(self):
    #     print("爬虫开始了")

    # async def spider_closed(self):
    #     print("爬虫结束了")

    # async def spider_error(self, exc, spider):
    #     print(f"爬虫出错了{exc},请紧急处理一下!")
