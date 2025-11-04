from inspect import isgenerator, isasyncgen
from bald_spider.exceptions import TransformTypeError


async def transform(func_reuslt):
	if isgenerator(func_reuslt):
		for r in func_reuslt:
			yield r
	elif isasyncgen(func_reuslt):
		async for r in func_reuslt:
			yield r
	else:
		raise TransformTypeError("callnack return value must be `generator` or `async generator` ")
