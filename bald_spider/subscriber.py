from collections import defaultdict
from collections.abc import Coroutine
from typing import Callable, Any
import asyncio
from bald_spider.utils.log import get_logger


class Subscriber:
    def __init__(self):
        self._subscriber: dict[str, set[Callable[..., Coroutine[Any, Any, Any]]]] = defaultdict(set)
        self.logger = get_logger(self.__class__.__name__)

    def subscriber(self, receiver: Callable[..., Coroutine[Any, Any, Any]], *, event: str) -> None:
        self._subscriber[event].add(receiver)

    def unsubscriber(self, receiver: Callable[..., Coroutine[Any, Any, Any]], *, event: str) -> None:
        self._subscriber[event].remove(receiver)

    async def notify(self, event: str, *args, **kwargs):
        receivers = list(self._subscriber[event])
        if not receivers:
            return
        results = await asyncio.gather(
            *(receiver(*args, **kwargs) for receiver in receivers), return_exceptions=True
        )
        for result in results:
            if isinstance(result, Exception):
                self.logger.error(
                    f"subscriber of event {event!r} raised {result.__class__.__name__}: {result}",
                    exc_info=(type(result), result, result.__traceback__),
                )
