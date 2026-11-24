"""针对已修复缺陷的回归测试。

约束：本文件为新增测试，不修改 tests/test_main.py 中的既有断言。
"""

import asyncio
import logging
from types import SimpleNamespace

import pytest

from bald_spider import Request, Response
from bald_spider.exceptions import IgnoreRequest
from bald_spider.middleware.default_header import DefaultHeader
from bald_spider.middleware.middleware_manager import MiddlewareManager
from bald_spider.middleware.response_filter import ResponseFilter
from bald_spider.middleware.retry import Retry
from bald_spider.settings.settings_manager import SettingsManager
from bald_spider.spider import Spider
from bald_spider.subscriber import Subscriber
from bald_spider.task_manager import TaskManager


def _response(request, status_code=200, headers=None, body=b""):
    return Response(
        request.url,
        request=request,
        headers=headers or {},
        body=body,
        status_code=status_code,
    )


def test_package_exports_main():
    import bald_spider
    from bald_spider.main import main

    assert bald_spider.main is main
    assert "main" in bald_spider.__all__


def test_response_text_uses_charset_from_headers():
    request = Request("http://example.com", encoding="utf-8")
    response = _response(
        request,
        headers={"Content-Type": "text/html; charset=gbk"},
        body="中文内容".encode("gbk"),
    )

    assert response.text == "中文内容"
    assert response.encoding == "gbk"


def test_default_header_does_not_short_circuit_request():
    middleware = DefaultHeader(
        user_agent="TestAgent", headers={"X-Test": "1"}, spider=None
    )
    request = Request("http://example.com")

    asyncio.run(middleware.spider_opened())
    result = middleware.process_request(request, None)

    assert result is None
    assert request.headers["User-Agent"] == "TestAgent"
    assert request.headers["X-Test"] == "1"


def test_retry_uses_status_code_attribute():
    stats = SimpleNamespace(inc_value=lambda *args, **kwargs: None)
    retry = Retry(
        retry_http_codes=[500],
        ignore_http_codes=[404],
        max_retry_times=2,
        retry_exceptions=[],
        stats=stats,
    )
    request = Request("http://example.com")

    retried = retry.process_response(request, _response(request, 500), None)
    assert retried is request
    assert request.meta["retry_times"] == 1

    ignored = _response(request, 404)
    assert retry.process_response(request, ignored, None) is ignored


def test_response_filter_uses_status_code_attribute():
    response_filter = ResponseFilter(allowed_codes=[404], log_level="INFO")
    request = Request("http://example.com")

    ok = _response(request, 200)
    assert response_filter.process_response(request, ok, None) is ok

    allowed = _response(request, 404)
    assert response_filter.process_response(request, allowed, None) is allowed

    with pytest.raises(IgnoreRequest):
        response_filter.process_response(request, _response(request, 500), None)


class _FakeDownloader:
    async def download(self, request):
        return None


class _FakeEngine:
    def __init__(self):
        self.downloader = _FakeDownloader()
        self.enqueued = []

    async def enqueue_request(self, request):
        self.enqueued.append(request)


class _FakeCrawler:
    def __init__(self):
        self.settings = SettingsManager({"MIDDLEWARES": []})
        self.engine = _FakeEngine()
        self.stats = SimpleNamespace(inc_value=lambda *args, **kwargs: None)
        self.spider = None
        self.subscriber = Subscriber()


def test_middleware_manager_enqueues_returned_request():
    crawler = _FakeCrawler()
    manager = MiddlewareManager(crawler)
    original = Request("http://original.example.com")
    replacement = Request("http://replacement.example.com")

    async def process_request(request):
        return replacement

    manager._process_request = process_request

    asyncio.run(manager.download(original))

    assert crawler.engine.enqueued == [replacement]


def test_subscriber_notify_awaits_receivers():
    async def scenario():
        subscriber = Subscriber()
        called = []

        async def receiver():
            await asyncio.sleep(0)
            called.append(True)

        subscriber.subscriber(receiver, event="test_event")
        await subscriber.notify("test_event")
        return called

    assert asyncio.run(scenario()) == [True]


def test_task_manager_logs_unhandled_task_exception(caplog):
    async def scenario():
        manager = TaskManager(total_concurrency=1)

        async def boom():
            raise RuntimeError("boom-task")

        await manager.semaphore.acquire()
        task = manager.create_task(boom())
        await asyncio.gather(task, return_exceptions=True)
        await asyncio.sleep(0)
        return manager

    with caplog.at_level(logging.ERROR):
        manager = asyncio.run(scenario())

    assert manager.all_done()
    assert "boom-task" in caplog.text


def test_spider_parse_raises_not_implemented_error():
    with pytest.raises(NotImplementedError):
        Spider().parse(None)
