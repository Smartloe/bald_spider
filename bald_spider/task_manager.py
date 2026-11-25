from typing import Set, Final
import asyncio
from asyncio import Task, Future, Semaphore
from bald_spider.utils.log import get_logger


class TaskManager:
    def __init__(self, total_concurrency=16, log_level=None):
        self.current_task: Final[Set] = set()
        # 并发数必须为正；0 会让主循环永久阻塞在信号量上。
        self.semaphore: Semaphore = Semaphore(max(1, total_concurrency))
        self.logger = get_logger(self.__class__.__name__, log_level)

    def create_task(self, coroutine) -> Task:
        task = asyncio.create_task(coroutine)
        self.current_task.add(task)

        def done_callback(_fut: Future):
            self.current_task.discard(task)
            self.semaphore.release()
            if task.cancelled():
                return
            exc = task.exception()
            if exc is not None:
                self.logger.error(
                    f"task raised unhandled exception: {exc.__class__.__name__}: {exc}",
                    exc_info=(type(exc), exc, exc.__traceback__),
                )

        task.add_done_callback(done_callback)
        return task

    def all_done(self):
        return len(self.current_task) == 0
