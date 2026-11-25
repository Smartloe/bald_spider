from collections import defaultdict
from collections.abc import Coroutine
from typing import Callable, Any
import asyncio
import inspect
from bald_spider.utils.log import get_logger


class Subscriber:
    def __init__(self, log_level=None):
        self._subscriber: dict[str, set[Callable[..., Coroutine[Any, Any, Any]]]] = defaultdict(set)
        self.logger = get_logger(self.__class__.__name__, log_level)

    def subscriber(self, receiver: Callable[..., Coroutine[Any, Any, Any]], *, event: str) -> None:
        self._subscriber[event].add(receiver)

    def unsubscriber(self, receiver: Callable[..., Coroutine[Any, Any, Any]], *, event: str) -> None:
        self._subscriber[event].remove(receiver)

    async def notify(self, event: str, *args, **kwargs):
        receivers = list(self._subscriber[event])
        if not receivers:
            return
        awaitables = []
        for receiver in receivers:
            call = getattr(receiver, "__call__", None)
            if not (
                inspect.iscoroutinefunction(receiver)
                or inspect.iscoroutinefunction(call)
            ):
                # 同步订阅者直接跳过（不执行），避免拖垮 Processor 等调用方。
                self.logger.error(f"subscriber {receiver!r} must be a coroutine function")
                continue
            try:
                result = receiver(*args, **kwargs)
            except Exception as exc:
                self.logger.error(
                    f"subscriber {receiver!r} raised {exc.__class__.__name__}: {exc}",
                    exc_info=(type(exc), exc, exc.__traceback__),
                )
                continue
            if not inspect.isawaitable(result):
                self.logger.error(f"subscriber {receiver!r} must return an awaitable")
                continue
            awaitables.append(result)
        if not awaitables:
            return
        results = await asyncio.gather(*awaitables, return_exceptions=True)
        for result in results:
            if isinstance(result, Exception):
                self.logger.error(
                    f"subscriber of event {event!r} raised {result.__class__.__name__}: {result}",
                    exc_info=(type(result), result, result.__traceback__),
                )
