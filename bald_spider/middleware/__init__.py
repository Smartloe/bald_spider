from bald_spider.http.request import Request
from bald_spider.http.response import Response


class BaseMiddleware:
    def process_request(self, request, spider) -> None | Request | Response:
        pass

    def process_response(self, request, response, spider) -> Request | Response:
        pass

    def process_exception(self, request, exception, spider) -> None | Request | Response:
        pass

    @classmethod
    def create_instance(cls, crawler):
        return cls()
