from tkinter import N
from token import OP
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
        proxy: Dict | None = None,
        body="",
        encoding="utf-8",
        meta: Dict | None = None,
    ):
        self.url = url
        self.headers = headers
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

    def __lt__(slef, other):
        return slef.priority < other.priority

    @property
    def meta(self):
        return self._meta
