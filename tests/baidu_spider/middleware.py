from bald_spider.middleware import BaseMiddleware
import random
from asyncio import sleep


class TestMiddlware(BaseMiddleware):
    async def process_request(self, request, spider):
        print("test middleware", request, spider)
        await sleep(0.5)

    def process_response(self, request, response, spider):
        print("test middleware response", request, response, spider)
        return response

    def process_exception(self, request, exception, spider):
        print("test middleware exception", request, exception, spider)


class TestMiddlware2(BaseMiddleware):
    def process_request(self, request, spider):
        # if random.randint(1, 3) == 1:
        #     1 / 0
        pass

    def process_exception(self, request, exception, spider):
        print("test2 middleware exception", request, exception, spider)


class TestMiddlware3(BaseMiddleware):
    def process_response(self, request, response, spider):
        print("test3 middleware response", request, response, spider)
        return response

    def process_exception(self, request, exception, spider):
        print("test3 middleware exception", request, exception, spider)
        if isinstance(exception, ZeroDivisionError):
            print("middleware3 处理了除零异常")
            return True
