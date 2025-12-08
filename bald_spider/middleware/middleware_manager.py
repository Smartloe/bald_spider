from asyncio import create_task
from tkinter import N, NO
from types import MethodType
from typing import Callable
from bald_spider.exceptions import IgnoreRequest, InvalidOutputError, MiddlewareInitError, RequestMethodError
from bald_spider.http.response import Response
from bald_spider.http.request import Request
from bald_spider.middleware import BaseMiddleware
from bald_spider.utils.log import get_logger
from bald_spider.utils.project import load_class
from pprint import pformat
from collections import defaultdict
from bald_spider.utils.project import common_call
from bald_spider.event import ignore_request, response_received


class MiddlewareManager:
    def __init__(self, crawler) -> None:
        self.crawler = crawler
        self.logger = get_logger(self.__class__.__name__, crawler.settings.get("LOG_LEVEL"))
        self.middlewares = []
        self.methods: dict[str, list[MethodType]] = defaultdict(list)
        middlewares = self.crawler.settings.getlist("MIDDLEWARES")
        self._add_middlewares(middlewares)
        self._add_methods()
        self.download_method: Callable = crawler.engine.downloader.download
        self._stats = crawler.stats

    async def _process_request(self, request: Request):
        for method in self.methods["process_request"]:
            # result = method(request, self.crawler.spider)
            result = await common_call(method, request, self.crawler.spider)
            if result == None:
                continue
            if isinstance(result, (Request, Response)):
                return result
            raise InvalidOutputError(
                f"middleware {method.__qualname__} must return Request, Response or None,got {type(result).__name__}"
            )
        return await self.download_method(request)

    async def _process_response(self, request: Request, response: Response):
        for method in reversed(self.methods["process_response"]):
            try:
                response = await common_call(method, request, response, self.crawler.spider)
            except IgnoreRequest as exc:
                create_task(self.crawler.subscriber.notify(ignore_request, exc, request, self.crawler.spider))
                self.logger.info(f"{request} ignored.")
                self._stats.inc_value(f"request_ignored_count")
                reason = exc.msg
                if reason:
                    self._stats.inc_value(f"request_ignored_count/{reason}")
                return None
            else:
                if isinstance(response, Request):
                    return response
                if isinstance(response, Response):
                    continue
                raise InvalidOutputError(
                    f"middleware {method.__qualname__} must return Request or Response,got {type(response).__name__}"
                )
        return response

    async def _process_exception(self, request: Request, exception: Exception):
        for method in reversed(self.methods["process_exception"]):
            response = await common_call(method, request, exception, self.crawler.spider)
            if response is None:
                continue
            if isinstance(response, (Request, Response)):
                return response
            if response:
                break
            raise InvalidOutputError(
                f"middleware {method.__qualname__} must return Request, Response or None,got {type(response).__name__}"
            )
        else:
            raise exception

    async def download(self, request: Request) -> Response | None:
        try:
            response = await self._process_request(request)
        except KeyError:
            raise RequestMethodError(f"{request.method.lower()} is not supported.")
        except IgnoreRequest as exc:
            create_task(self.crawler.subscriber.notify(ignore_request, exc, request, self.crawler.spider))
            self.logger.info(f"{request} ignored.")
            self._stats.inc_value(f"request_ignore_count")
            reason = exc.msg
            if reason:
                self._stats.inc_value(f"request_ignore_count/{reason}")
            response = await self._process_exception(request, exc)
        except Exception as exc:
            self._stats.inc_value(f"download_error/{exc.__class__.__name__}")
            response = await self._process_exception(request, exc)
        else:
            create_task(self.crawler.subscriber.notify(response_received, response, self.crawler.spider))
            self.crawler.stats.inc_value("response_received_count")
        if isinstance(response, Response):
            response = await self._process_response(request, response)
        if isinstance(response, Request):
            await self.crawler.engine.enqueue_request(request)
            return None
        return response

    def _add_methods(self):
        for middleware in self.middlewares:
            if hasattr(middleware, "process_request"):
                if self._validate_method("process_request", middleware):
                    self.methods["process_request"].append(middleware.process_request)
            if hasattr(middleware, "process_response"):
                if self._validate_method("process_response", middleware):
                    self.methods["process_response"].append(middleware.process_response)
            if hasattr(middleware, "process_exception"):
                if self._validate_method("process_exception", middleware):
                    self.methods["process_exception"].append(middleware.process_exception)

    def _add_middlewares(self, middlewares):
        enabled_middlewares = [m for m in middlewares if self._validate_middleware(m)]
        if enabled_middlewares:
            self.logger.info(f"enabled middlewares: \n {pformat(enabled_middlewares)}")

    def _validate_middleware(self, middleware):
        middleware_cls = load_class(middleware)
        if not hasattr(middleware_cls, "create_instance"):
            raise MiddlewareInitError(
                f"Middleware init failed, must inherit from `BaseMiddleware` or `create_instance` method."
            )
        instance = middleware_cls.create_instance(self.crawler)
        self.middlewares.append(instance)
        return True

    @classmethod
    def create_instance(cls, *args, **kwargs):
        return cls(*args, **kwargs)

    @staticmethod
    def _validate_method(method_name, middleware) -> bool:
        method = getattr(type(middleware), method_name)

        base_method = getattr(BaseMiddleware, method_name)

        return method != base_method
