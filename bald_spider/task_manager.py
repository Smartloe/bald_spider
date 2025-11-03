from typing import Set, Final
import asyncio
from asyncio import Task, Future, Semaphore


class TaskManager:
    def __init__(self, total_concurrency=16):
        self.current_task: Final[Set] = set()
        self.semaphore: Semaphore = Semaphore(total_concurrency)

    def create_task(self, coroutine) -> Task:
        task = asyncio.create_task(coroutine)
        self.current_task.add(task)

        def done_callback(_fut: Future):
            self.current_task.remove(task)
            self.semaphore.release()

        task.add_done_callback(done_callback)

    def all_done(self):
        return len(self.current_task) == 0
