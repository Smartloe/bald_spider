from contextlib import aclosing
from inspect import isgenerator, isasyncgen
from typing import Callable
from bald_spider.exceptions import TransformTypeError


async def transform(func_reuslt):
    try:
        if isgenerator(func_reuslt):
            try:
                for r in func_reuslt:
                    yield r
            finally:
                # 提前退出时显式关闭同步生成器，执行用户 finally。
                try:
                    func_reuslt.close()
                except Exception:
                    pass
        elif isasyncgen(func_reuslt):
            async with aclosing(func_reuslt) as generator:
                async for r in generator:
                    yield r
        else:
            raise TransformTypeError("callnack return value must be `generator` or `async generator` ")
    except Exception as exc:
        yield exc
