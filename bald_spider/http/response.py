from typing import Dict
from bald_spider import Request
import ujson
import re
from urllib.parse import urljoin as _urljoin
from bald_spider.exceptions import DecodeError


class Response:
    def __init__(
        self,
        url: str,
        *,
        request: Request,
        headers: Dict,
        body: bytes = b"",
        status_code: int = 200,
    ):
        self.url = url
        self.request = request
        self.headers = headers
        self.body = body
        self.status_code = status_code
        self.encoding = request.encoding
        self._text_cache = None

    @property
    def text(self):
        if self._text_cache:
            return self._text_cache
        try:
            self._text_cache = self.body.decode(self.encoding)
        except UnicodeDecodeError:
            try:
                _encoding_re = re.compile(r"charset=([\w-]+)", flags=re.I)
                _encoding_string = self.headers.get("Content-Type", "") or self.headers.get("content-type", "")
                _encoding = _encoding_re.search(_encoding_string)
                if _encoding:
                    _encoding = _encoding.group(1)
                    self._text_cache = self.body.decode(self.encoding)
                else:
                    raise DecodeError(f"can not decode {self.body} with {self.encoding}")
            except UnicodeDecodeError as exc:
                raise UnicodeDecodeError(exc.encoding, exc.object, exc.start, exc.end, f"{self.request}")
        return self._text_cache

    def json(self):
        return ujson.loads(self.text)

    def urljoin(self, url):
        return _urljoin(self.url, url)
