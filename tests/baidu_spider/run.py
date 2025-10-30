from bald_spider.core.engine import Engine
from baidu import BaiduSpider

baidu_spider = BaiduSpider()
engine = Engine()
engine.start_spider(baidu_spider)
