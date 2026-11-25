from typing import Dict
from bald_spider import Request
import ujson
import re
from parsel import Selector
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
        self._selector = None

    @property
    def text(self):
        if self._text_cache is not None:
            return self._text_cache
        try:
            self._text_cache = self.body.decode(self.encoding)
        except LookupError as exc:
            raise DecodeError(f"unknown encoding {self.encoding!r}: {exc}") from exc
        except UnicodeDecodeError:
            _encoding_re = re.compile(r"charset=([\w-]+)", flags=re.I)
            _encoding_string = ""
            for header, value in self.headers.items():
                if header.lower() == "content-type":
                    _encoding_string = value or ""
                    break
            _encoding = _encoding_re.search(_encoding_string)
            if not _encoding:
                raise DecodeError(f"can not decode {self.body} with {self.encoding}")
            self.encoding = _encoding.group(1)
            try:
                self._text_cache = self.body.decode(self.encoding)
            except UnicodeDecodeError as exc:
                raise UnicodeDecodeError(exc.encoding, exc.object, exc.start, exc.end, f"{self.request}")
            except LookupError as exc:
                raise DecodeError(f"unknown encoding {self.encoding!r}: {exc}") from exc
        return self._text_cache

    def xpath(self, xpath_sting):
        if self._selector is None:
            self._selector = Selector(self.text)
        return self._selector.xpath(xpath_sting)

    def json(self):
        return ujson.loads(self.text)

    def urljoin(self, url):
        return _urljoin(self.url, url)

    def __str__(self):
        return f"<Response {self.status_code} {self.url}>"

    @property
    def meta(self):
        return self.request.meta
