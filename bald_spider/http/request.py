from typing import Dict, Callable


class Request:
    def __init__(
        self,
        url: str,
        *,
        headers: Dict | None = None,
        callback: Callable | None = None,
        priority: int = 0,
        method: str = "GET",
        cookie: Dict | None = None,
        proxy: str | None = None,
        body="",
        encoding="utf-8",
        meta: Dict | None = None,
    ):
        self.url = url
        self.headers = headers if headers else {}
        self.callback = callback
        self.priority = priority
        self.method = method
        self.cookie = cookie
        self.proxy = proxy
        self.body = body
        self.encoding = encoding
        self._meta = meta if meta is not None else {}

    def __str__(self):
        return f" {self.url} {self.method}"

    def __lt__(self, other):
        # PriorityQueue 是最小堆，取反后 priority 数值越大越先出队（与文档“高优先级”一致）。
        return self.priority > other.priority

    @property
    def meta(self):
        return self._meta
