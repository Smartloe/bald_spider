import requests
from bald_spider.core.engine import Engine


class BaiduSpider:
    start_url = "https://www.baidu.com"

    def start_requests(self):
        response = requests.get(self.start_url)
        print(response)


if __name__ == "__main__":
    baidu_spider = BaiduSpider()
    engine = Engine()
    engine.start_spider(baidu_spider)
