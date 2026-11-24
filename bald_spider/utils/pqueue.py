from asyncio import PriorityQueue


class SpoderPriorityQueue(PriorityQueue):
	def __init__(self, maxsize=0):
		super(SpoderPriorityQueue, self).__init__(maxsize)
