
from bald_spider.utils.pqueue import SpoderPriorityQueue


class Scheduler:
	def __init__(self):
		self.request_queue: SpoderPriorityQueue | None = None

	def open(self):
		self.request_queue = SpoderPriorityQueue()

	async def next_request(self):
		request = await self.request_queue.get()
		return request

	async def enqueue_request(self, request):
		await self.request_queue.put(request)

	def idle(self) -> bool:
		"""检查调度器是否空闲"""
		if self.request_queue is None:
			return True
		return self.request_queue.empty()
