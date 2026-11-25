"""针对已修复缺陷的回归测试。

约束：本文件为新增测试，不修改 tests/test_main.py 中的既有断言。
"""

import asyncio
import logging
from types import SimpleNamespace

import httpx
import pytest

from bald_spider import Request, Response
from bald_spider.core.downloader import ActiveRequestManger, DownloaderBase
from bald_spider.core.downloader.aiohttp_downloder import AioDownloader
from bald_spider.core.downloader.httpx_downloader import HTTPXDownloader
from bald_spider.core.processor import Processor
from bald_spider.crawler import Crawler
from bald_spider.event import item_successful
from bald_spider.exceptions import IgnoreRequest
from bald_spider.items import Field
from bald_spider.items.items import Item
from bald_spider.middleware.default_header import DefaultHeader
from bald_spider.middleware.middleware_manager import MiddlewareManager
from bald_spider.middleware.request_ignore import RequestIngore
from bald_spider.middleware.response_filter import ResponseFilter
from bald_spider.middleware.retry import Retry
from bald_spider.settings.settings_manager import SettingsManager
from bald_spider.spider import Spider
from bald_spider.stats_collector import StatsCollector
from bald_spider.subscriber import Subscriber
from bald_spider.task_manager import TaskManager
from bald_spider.utils.pqueue import SpoderPriorityQueue


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


def test_request_priority_orders_higher_priority_first():
    async def scenario():
        queue = SpoderPriorityQueue()
        for priority in (0, 10, 5, 1):
            await queue.put(Request(f"http://example.com/{priority}", priority=priority))
        return [(await queue.get()).priority for _ in range(4)]

    assert asyncio.run(scenario()) == [10, 5, 1, 0]


class _BaseItem(Item):
    url = Field()


class _ChildItem(_BaseItem):
    title = Field()


def test_item_meta_inherits_parent_fields():
    item = _ChildItem()
    item["url"] = "http://example.com"
    item["title"] = "title"

    assert item.to_dict() == {"url": "http://example.com", "title": "title"}


def test_active_request_manager_counts_duplicate_requests():
    manager = ActiveRequestManger()
    request = Request("http://example.com")

    manager.add(request)
    manager.add(request)
    assert len(manager) == 1

    manager.remove(request)
    assert len(manager) == 1

    manager.remove(request)
    assert len(manager) == 0

    # 重复移除不应抛 KeyError
    manager.remove(request)
    assert len(manager) == 0


class _NullDownloader(DownloaderBase):
    async def download(self, request):
        return _response(request)


class _AsyncListSpider(Spider):
    start_urls = ["http://example.invalid/"]

    async def parse(self, response):
        # 异步回调返回列表：应被明确上报为 TransformTypeError，而不是静默丢弃。
        return [Request("http://example.invalid/next")]


def test_async_callback_return_value_is_not_silently_dropped():
    settings = SettingsManager(
        {
            "DOWNLOADER": _NullDownloader,
            "LOG_LEVEL": "CRITICAL",
            "STATS_DUMP": False,
            "REQUEST_TIMEOUT": 1,
            "CONCURRENCY": 1,
        }
    )
    crawler = Crawler(_AsyncListSpider, settings)

    asyncio.run(asyncio.wait_for(crawler.crawl(), timeout=10))

    stats = crawler.stats.get_stats()
    assert stats.get("spider_exceptions/TransformTypeError") == 1


def test_request_ignore_process_exception_is_bound_instance_method():
    stats = SimpleNamespace(inc_value=lambda *args, **kwargs: None)
    middleware = RequestIngore(stats=stats, log_level="INFO")
    request = Request("http://example.com")

    # 普通异常交给后续中间件处理
    assert middleware.process_exception(request, ConnectionError("boom"), None) is None
    # IgnoreRequest 表示已处理
    assert middleware.process_exception(request, IgnoreRequest("ignored"), None) is True


class _FlakyDownloader(DownloaderBase):
    calls = 0

    async def download(self, request):
        type(self).calls += 1
        if type(self).calls == 1:
            raise httpx.ConnectError("boom")
        return _response(request)


class _PlainSpider(Spider):
    start_urls = ["http://example.invalid/"]

    async def parse(self, response):
        return None


def test_retry_chain_works_with_request_ignore_middleware():
    _FlakyDownloader.calls = 0
    settings = SettingsManager(
        {
            "DOWNLOADER": _FlakyDownloader,
            "MIDDLEWARES": [Retry, RequestIngore],
            "RETRY_HTTP_CODES": [],
            "IGNORE_HTTP_CODES": [],
            "MAX_RETRY_TIMES": 2,
            "RETRY_EXCEPTIONS": [],
            "LOG_LEVEL": "CRITICAL",
            "STATS_DUMP": False,
            "REQUEST_TIMEOUT": 1,
            "CONCURRENCY": 1,
        }
    )
    crawler = Crawler(_PlainSpider, settings)

    asyncio.run(asyncio.wait_for(crawler.crawl(), timeout=10))

    stats = crawler.stats.get_stats()
    assert _FlakyDownloader.calls == 2
    assert stats.get("retry_count") == 1
    assert stats.get("response_received_count") == 1
    assert "spider_exceptions/TypeError" not in stats


class _LifecycleSpider(Spider):
    start_urls = ["http://example.invalid/"]
    opened_done = False

    async def spider_opened(self):
        await asyncio.sleep(0.01)
        type(self).opened_done = True

    async def parse(self, response):
        return None


class _OrderDownloader(DownloaderBase):
    seen = []

    async def download(self, request):
        type(self).seen.append(_LifecycleSpider.opened_done)
        return _response(request)


def test_spider_opened_completes_before_first_request():
    _LifecycleSpider.opened_done = False
    _OrderDownloader.seen = []
    settings = SettingsManager(
        {
            "DOWNLOADER": _OrderDownloader,
            "LOG_LEVEL": "CRITICAL",
            "STATS_DUMP": False,
            "REQUEST_TIMEOUT": 1,
            "CONCURRENCY": 1,
        }
    )
    crawler = Crawler(_LifecycleSpider, settings)

    asyncio.run(asyncio.wait_for(crawler.crawl(), timeout=10))

    assert _OrderDownloader.seen == [True]


def test_aiohttp_response_url_uses_final_url():
    request = Request("http://old.example.com/old")
    raw = SimpleNamespace(url="http://new.example.com/new/dir/page", headers={}, status=200)

    response = AioDownloader.structure_response(request, raw, b"")

    assert response.url == "http://new.example.com/new/dir/page"
    assert response.urljoin("a.html") == "http://new.example.com/new/dir/a.html"


def test_httpx_response_url_uses_final_url():
    request = Request("http://old.example.com/old")
    raw = SimpleNamespace(url="http://new.example.com/new/dir/page", headers={}, status_code=200)

    response = HTTPXDownloader.structure_response(request, raw, b"")

    assert response.url == "http://new.example.com/new/dir/page"
    assert response.urljoin("a.html") == "http://new.example.com/new/dir/a.html"


class _BusySpider(Spider):
    start_urls = ["http://example.invalid/"]
    closed_called = False

    async def parse(self, response):
        yield Request(self.start_urls[0], callback=self.parse)

    async def spider_closed(self):
        type(self).closed_called = True


class _TrackingDownloader(DownloaderBase):
    closed = False

    async def download(self, request):
        return _response(request)

    async def close(self):
        type(self).closed = True


def test_cancellation_runs_cleanup_and_spider_closed():
    _TrackingDownloader.closed = False
    _BusySpider.closed_called = False
    settings = SettingsManager(
        {
            "DOWNLOADER": _TrackingDownloader,
            "LOG_LEVEL": "CRITICAL",
            "STATS_DUMP": False,
            "REQUEST_TIMEOUT": 1,
            "CONCURRENCY": 1,
            "INTERVAL": 100,
        }
    )
    crawler = Crawler(_BusySpider, settings)

    async def scenario():
        task = asyncio.create_task(crawler.crawl())
        await asyncio.sleep(0.3)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(task, timeout=5)

    asyncio.run(scenario())

    assert _TrackingDownloader.closed is True
    assert _BusySpider.closed_called is True


class _SlowSpider(Spider):
    start_urls = ["http://example.invalid/"]
    closed_called = False

    async def parse(self, response):
        return None

    async def spider_closed(self):
        type(self).closed_called = True


class _SlowDownloader(DownloaderBase):
    closed = False

    async def download(self, request):
        await asyncio.sleep(10)
        return _response(request)

    async def close(self):
        type(self).closed = True


def test_external_stop_interrupts_slow_download():
    _SlowDownloader.closed = False
    _SlowSpider.closed_called = False
    settings = SettingsManager(
        {
            "DOWNLOADER": _SlowDownloader,
            "LOG_LEVEL": "CRITICAL",
            "STATS_DUMP": False,
            "REQUEST_TIMEOUT": 1,
            "CONCURRENCY": 1,
            "INTERVAL": 100,
        }
    )
    crawler = Crawler(_SlowSpider, settings)

    async def scenario():
        task = asyncio.create_task(crawler.crawl())
        await asyncio.sleep(0.2)
        # 模拟 CrawlerProcess._shutdown 的 Ctrl+C 行为
        crawler.engine.running = False
        crawler.engine.normal = False
        await asyncio.wait_for(task, timeout=3)

    asyncio.run(scenario())

    assert _SlowDownloader.closed is True
    assert _SlowSpider.closed_called is True


class _EndlessStartSpider(Spider):
    def start_requests(self):
        while True:
            yield Request("http://example.invalid/")

    async def parse(self, response):
        return None


def test_endless_start_requests_can_be_stopped():
    settings = SettingsManager(
        {
            "DOWNLOADER": _NullDownloader,
            "LOG_LEVEL": "CRITICAL",
            "STATS_DUMP": False,
            "REQUEST_TIMEOUT": 1,
            "CONCURRENCY": 1,
            "INTERVAL": 100,
        }
    )
    crawler = Crawler(_EndlessStartSpider, settings)

    async def scenario():
        task = asyncio.create_task(crawler.crawl())
        await asyncio.sleep(0.3)
        crawler.engine.running = False
        crawler.engine.normal = False
        await asyncio.wait_for(task, timeout=3)

    asyncio.run(scenario())


class _AsyncStartSpider(Spider):
    start_urls = []

    async def start_requests(self):
        yield Request("http://example.invalid/")

    async def parse(self, response):
        return None


def test_async_generator_start_requests_is_supported():
    settings = SettingsManager(
        {
            "DOWNLOADER": _NullDownloader,
            "LOG_LEVEL": "CRITICAL",
            "STATS_DUMP": False,
            "REQUEST_TIMEOUT": 1,
            "CONCURRENCY": 1,
            "INTERVAL": 100,
        }
    )
    crawler = Crawler(_AsyncStartSpider, settings)

    asyncio.run(asyncio.wait_for(crawler.crawl(), timeout=10))

    assert crawler.stats.get_value("response_received_count") == 1


class _TwoSlowSpider(Spider):
    start_urls = ["http://example.invalid/1", "http://example.invalid/2"]

    async def parse(self, response):
        return None


class _VerySlowDownloader(DownloaderBase):
    closed = False

    async def download(self, request):
        await asyncio.sleep(10)
        return _response(request)

    async def close(self):
        type(self).closed = True


def test_stop_interrupts_semaphore_wait():
    _VerySlowDownloader.closed = False
    settings = SettingsManager(
        {
            "DOWNLOADER": _VerySlowDownloader,
            "LOG_LEVEL": "CRITICAL",
            "STATS_DUMP": False,
            "REQUEST_TIMEOUT": 1,
            "CONCURRENCY": 1,
            "INTERVAL": 100,
        }
    )
    crawler = Crawler(_TwoSlowSpider, settings)

    async def scenario():
        task = asyncio.create_task(crawler.crawl())
        # 第一个请求占满信号量，第二个请求阻塞在可中断的信号量等待上
        await asyncio.sleep(0.4)
        crawler.engine.running = False
        crawler.engine.normal = False
        await asyncio.wait_for(task, timeout=3)

    asyncio.run(scenario())

    assert _VerySlowDownloader.closed is True


class _BrokenStartSpider(Spider):
    def start_requests(self):
        raise RuntimeError("boom-start")


def test_startup_failure_closes_downloader():
    _TrackingDownloader.closed = False
    settings = SettingsManager(
        {
            "DOWNLOADER": _TrackingDownloader,
            "LOG_LEVEL": "CRITICAL",
            "STATS_DUMP": False,
            "REQUEST_TIMEOUT": 1,
            "CONCURRENCY": 1,
        }
    )
    crawler = Crawler(_BrokenStartSpider, settings)

    with pytest.raises(RuntimeError):
        asyncio.run(crawler.crawl())

    assert _TrackingDownloader.closed is True


def test_processor_emits_item_successful_event():
    called = []

    async def receiver(item, spider):
        called.append(item)

    subscriber = Subscriber()
    subscriber.subscriber(receiver, event=item_successful)
    crawler = SimpleNamespace(
        stats=SimpleNamespace(inc_value=lambda *args, **kwargs: None),
        spider="spider",
        subscriber=subscriber,
        engine=None,
    )
    processor = Processor(crawler)
    item = _ChildItem()
    item["url"] = "http://example.com"
    item["title"] = "title"

    asyncio.run(processor._process_item(item))

    assert called == [item]


def test_stats_close_spider_is_idempotent():
    crawler = SimpleNamespace(settings=SettingsManager({"STATS_DUMP": False}))
    stats = StatsCollector(crawler)
    stats["start_time"] = "2024-01-01 00:00:00"

    stats.close_spider(None, "first")
    stats.close_spider(None, "second")

    assert stats["reason"] == "first"


def test_item_hasattr_does_not_raise():
    item = _ChildItem()

    assert hasattr(item, "url") is False
    with pytest.raises(AttributeError):
        item.url


class _DownloaderCrawler:
    def __init__(self):
        self.settings = SettingsManager(
            {"USE_SESSION": True, "VERIFY_SSL": False, "LOG_LEVEL": "CRITICAL"}
        )
        self.stats = SimpleNamespace(inc_value=lambda *args, **kwargs: None)
        self.subscriber = Subscriber()
        self.spider = None
        self.engine = SimpleNamespace(downloader=None)


def test_httpx_downloader_reuses_and_closes_client():
    crawler = _DownloaderCrawler()
    downloader = HTTPXDownloader(crawler)
    crawler.engine.downloader = downloader

    downloader.open()
    client = downloader._client
    assert client is not None
    assert client.is_closed is False

    asyncio.run(downloader.close())

    assert downloader._client is None
    assert client.is_closed is True


def test_retry_covers_httpx_timeout_exceptions():
    stats = SimpleNamespace(inc_value=lambda *args, **kwargs: None)
    retry = Retry(
        retry_http_codes=[],
        ignore_http_codes=[],
        max_retry_times=1,
        retry_exceptions=[],
        stats=stats,
    )

    for exception in (httpx.ConnectTimeout, httpx.WriteTimeout, httpx.PoolTimeout):
        assert exception in retry.retry_exceptions
