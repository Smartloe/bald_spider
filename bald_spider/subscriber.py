from collections import defaultdict
from collections.abc import Coroutine
from typing import Callable, Any
import asyncio


class Subscriber:
    def __init__(self):
        self._subscriber: dict[str, set[Callable[..., Coroutine[Any, Any, Any]]]] = defaultdict(set)

    def subscriber(self, receiver: Callable[..., Coroutine[Any, Any, Any]], *, event: str) -> None:
        self._subscriber[event].add(receiver)

    def unsubscriber(self, receiver: Callable[..., Coroutine[Any, Any, Any]], *, event: str) -> None:
        self._subscriber[event].remove(receiver)

    async def notify(self, event: str, *args, **kwargs):
        for receiver in self._subscriber[event]:
            asyncio.create_task(receiver(*args, **kwargs))
