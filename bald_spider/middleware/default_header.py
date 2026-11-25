from bald_spider.event import spider_opened


class DefaultHeader:
    def __init__(self, user_agent, headers, spider) -> None:
        self.user_agent = user_agent
        self.headers = headers or {}
        self.spider = spider

    @classmethod
    def create_instance(cls, crawler):
        o = cls(
            user_agent=crawler.settings.get("USER_AGENT"),
            headers=crawler.settings.getdict("DEFAULT_HEADERS"),
            spider=crawler.spider,
        )
        crawler.subscriber.subscriber(o.spider_opened, event=spider_opened)
        return o

    async def spider_opened(self):
        self.user_agent = getattr(self.spider, "user_agent", self.user_agent)
        self.headers = getattr(self.spider, "default_headers", self.headers)
        if self.user_agent:
            self.headers.setdefault("User-Agent", self.user_agent)

    def process_request(self, request, spider):
        # 每请求惰性读取 spider 级配置，避免依赖 spider_opened 与其他订阅者的执行顺序。
        spider = spider or self.spider
        user_agent = getattr(spider, "user_agent", self.user_agent) if spider is not None else self.user_agent
        headers = getattr(spider, "default_headers", self.headers) if spider is not None else self.headers
        if user_agent:
            request.headers.setdefault("User-Agent", user_agent)
        if headers:
            for k, v in headers.items():
                request.headers.setdefault(k, v)
        # 返回 None 表示继续走后续中间件/下载器；返回 request 会被视为短路并导致请求被重复入队。
        return None
