"""针对已修复缺陷的回归测试。

约束：本文件为新增测试，不修改 tests/test_main.py 中的既有断言。
"""

import asyncio
import logging
import time
from types import SimpleNamespace

import httpx
import pytest

from bald_spider import Request, Response
from bald_spider.core.downloader import ActiveRequestManger, DownloaderBase
from bald_spider.core.downloader.aiohttp_downloder import AioDownloader
from bald_spider.core.downloader.httpx_downloader import HTTPXDownloader
from bald_spider.core.engine import Engine
from bald_spider.core.processor import Processor
from bald_spider.crawler import Crawler, CrawlerProcess
from bald_spider.event import item_successful, response_received
from bald_spider.exceptions import DecodeError, IgnoreRequest, InvalidOutputError, RequestMethodError
from bald_spider.items import Field
from bald_spider.items.items import Item
from bald_spider.middleware.default_header import DefaultHeader
from bald_spider.middleware.download_delay import DownloadDelay
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


class _RecordingStats:
    def __init__(self):
        self.values = {}

    def inc_value(self, key, count=1, start=0):
        self.values[key] = self.values.get(key, start) + count

    def get_value(self, key, default=None):
        return self.values.get(key, default)


class _FakeEngine:
    def __init__(self):
        self.downloader = _FakeDownloader()
        self.enqueued = []

    async def enqueue_request(self, request):
        self.enqueued.append(request)

    async def requeue_request(self, request):
        self.enqueued.append(request)


class _FakeCrawler:
    def __init__(self):
        self.settings = SettingsManager({"MIDDLEWARES": []})
        self.engine = _FakeEngine()
        self.stats = _RecordingStats()
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


class _TwoUrlSpider(Spider):
    start_urls = ["http://example.invalid/1", "http://example.invalid/2"]

    async def parse(self, response):
        # 模拟同步解析耗时：制造“监视器 tick 与信号量释放对齐”的窗口
        deadline = time.monotonic() + 0.08
        while time.monotonic() < deadline:
            pass


class _ShortSleepDownloader(DownloaderBase):
    async def download(self, request):
        await asyncio.sleep(0.05)
        return _response(request)


def test_saturated_semaphore_does_not_drop_requests():
    settings = SettingsManager(
        {
            "DOWNLOADER": _ShortSleepDownloader,
            "LOG_LEVEL": "CRITICAL",
            "STATS_DUMP": False,
            "REQUEST_TIMEOUT": 1,
            "CONCURRENCY": 1,
            "INTERVAL": 100,
        }
    )
    crawler = Crawler(_TwoUrlSpider, settings)

    asyncio.run(asyncio.wait_for(crawler.crawl(), timeout=10))

    assert crawler.stats.get_value("response_received_count") == 2
    assert crawler.stats.get_value("request_scheduler_count") == 2


def test_short_circuit_request_is_not_counted_as_response():
    crawler = _FakeCrawler()
    received = []

    async def on_received(response, spider):
        received.append(response)

    crawler.subscriber.subscriber(on_received, event=response_received)
    manager = MiddlewareManager(crawler)
    request = Request("http://original.example.com")

    async def process_request(request):
        return request

    manager._process_request = process_request

    asyncio.run(manager.download(request))

    assert crawler.engine.enqueued == [request]
    assert crawler.stats.get_value("response_received_count") is None
    assert received == []


def test_process_exception_only_true_means_handled():
    manager = MiddlewareManager(_FakeCrawler())
    request = Request("http://example.com")

    async def returns_false(request, exception, spider):
        return False

    async def returns_true(request, exception, spider):
        return True

    async def returns_string(request, exception, spider):
        return "handled"

    manager.methods["process_exception"] = [returns_false]
    with pytest.raises(ValueError):
        asyncio.run(manager._process_exception(request, ValueError("boom")))

    manager.methods["process_exception"] = [returns_true]
    assert asyncio.run(manager._process_exception(request, ValueError("boom"))) is None

    manager.methods["process_exception"] = [returns_string]
    with pytest.raises(InvalidOutputError):
        asyncio.run(manager._process_exception(request, ValueError("boom")))


def test_shutdown_requested_before_start_is_honored():
    _TrackingDownloader.closed = False
    _SlowSpider.closed_called = False
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
    crawler = Crawler(_SlowSpider, settings)
    crawler._shutdown_requested = True

    asyncio.run(asyncio.wait_for(crawler.crawl(), timeout=5))

    assert _TrackingDownloader.closed is True
    assert _SlowSpider.closed_called is True


def test_second_cancellation_still_completes_cleanup():
    _SlowCloseDownloader.closed = False
    _BusySpider.closed_called = False
    settings = SettingsManager(
        {
            "DOWNLOADER": _SlowCloseDownloader,
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
        await asyncio.sleep(0.2)
        task.cancel()
        await asyncio.sleep(0.05)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(task, timeout=3)

    asyncio.run(scenario())

    assert _SlowCloseDownloader.closed is True
    assert _BusySpider.closed_called is True


def test_queue_limits_apply_backpressure_to_endless_producer():
    settings = SettingsManager(
        {
            "DOWNLOADER": _ShortSleepDownloader,
            "SCHEDULER_QUEUE_SIZE": 2,
            "LOG_LEVEL": "CRITICAL",
            "STATS_DUMP": False,
            "REQUEST_TIMEOUT": 1,
            "CONCURRENCY": 2,
            "INTERVAL": 100,
        }
    )
    crawler = Crawler(_EndlessStartSpider, settings)

    async def scenario():
        task = asyncio.create_task(crawler.crawl())
        await asyncio.sleep(0.3)
        scheduler_size = len(crawler.engine.scheduler)
        crawler.engine.running = False
        crawler.engine.normal = False
        await asyncio.wait_for(task, timeout=3)
        return scheduler_size

    assert asyncio.run(scenario()) <= 2


def test_response_text_handles_content_type_case_insensitively():
    request = Request("http://example.com", encoding="utf-8")
    response = _response(
        request,
        headers={"Content-TYPE": "text/html; charset=gbk"},
        body="中文内容".encode("gbk"),
    )

    assert response.text == "中文内容"


def test_download_delay_supports_new_and_legacy_range_keys():
    new = DownloadDelay(SettingsManager({"DOWNLOAD_DELAY": 1}), "INFO")
    assert (new.floor, new.upper) == (0.75, 1.25)

    legacy = DownloadDelay(
        SettingsManager({"DOWNLOAD_DELAY": 1, "RANDEOM_RANGE": (2, 3)}), "INFO"
    )
    assert (legacy.floor, legacy.upper) == (2, 3)


class _WideSpider(Spider):
    start_urls = ["http://example.invalid/"]

    async def parse(self, response):
        depth = response.meta.get("depth", 0)
        if depth >= 2:
            return
        for index in range(10):
            yield Request(
                f"http://example.invalid/{depth}/{index}",
                callback=self.parse,
                meta={"depth": depth + 1},
            )


def test_bounded_queues_with_multi_level_yields_do_not_deadlock():
    settings = SettingsManager(
        {
            "DOWNLOADER": _NullDownloader,
            "SCHEDULER_QUEUE_SIZE": 10,
            "LOG_LEVEL": "CRITICAL",
            "STATS_DUMP": False,
            "REQUEST_TIMEOUT": 1,
            "CONCURRENCY": 4,
            "INTERVAL": 100,
        }
    )
    crawler = Crawler(_WideSpider, settings)

    asyncio.run(asyncio.wait_for(crawler.crawl(), timeout=10))

    assert crawler.stats.get_value("request_scheduler_count") == 111
    assert crawler.stats.get_value("response_received_count") == 111


class _HeaderSpider(Spider):
    user_agent = "SpiderUA"
    default_headers = {"X-Spider": "1"}


def test_default_header_reads_spider_attributes_lazily():
    middleware = DefaultHeader(user_agent="", headers={}, spider=None)
    request = Request("http://example.com")

    middleware.process_request(request, _HeaderSpider())

    assert request.headers["User-Agent"] == "SpiderUA"
    assert request.headers["X-Spider"] == "1"


def test_logger_manager_preserves_user_handlers():
    import logging as logging_module

    from bald_spider.utils.log import get_logger

    name = "bald_spider_test_custom_logger"
    logger = logging_module.getLogger(name)
    user_handler = logging_module.NullHandler()
    logger.addHandler(user_handler)
    try:
        get_logger(name, "INFO")
        assert user_handler in logger.handlers
    finally:
        logger.removeHandler(user_handler)


def test_response_text_unknown_charset_raises_decode_error():
    request = Request("http://example.com", encoding="utf-8")
    response = _response(
        request,
        headers={"Content-Type": "text/html; charset=no-such-codec"},
        body=b"\xff\xfe",
    )

    with pytest.raises(DecodeError):
        _ = response.text


def test_middleware_key_error_is_not_masked_as_request_method_error():
    manager = MiddlewareManager(_FakeCrawler())
    request = Request("http://example.com")

    async def process_request(request):
        raise KeyError("from-middleware")

    manager._process_request = process_request

    with pytest.raises(KeyError):
        asyncio.run(manager.download(request))


def test_aiohttp_downloader_rejects_unsupported_method():
    crawler = SimpleNamespace(settings=SettingsManager({"LOG_LEVEL": "CRITICAL"}))
    downloader = AioDownloader(crawler)
    request = Request("http://example.com", method="PUT")

    with pytest.raises(RequestMethodError):
        asyncio.run(downloader.send_request(None, request))


class _Always500Downloader(DownloaderBase):
    async def download(self, request):
        return _response(request, status_code=500)


class _RetryBoundedSpider(Spider):
    start_urls = ["http://example.invalid/1", "http://example.invalid/2"]

    async def parse(self, response):
        for index in range(2):
            yield Request(f"{response.url}/{index}", callback=self.parse_detail)

    def parse_detail(self, response):
        pass


def test_bounded_scheduler_with_retry_requeue_does_not_deadlock():
    settings = SettingsManager(
        {
            "DOWNLOADER": _Always500Downloader,
            "MIDDLEWARES": [Retry],
            "RETRY_HTTP_CODES": [500],
            "IGNORE_HTTP_CODES": [],
            "MAX_RETRY_TIMES": 1,
            "RETRY_EXCEPTIONS": [],
            "SCHEDULER_QUEUE_SIZE": 1,
            "LOG_LEVEL": "CRITICAL",
            "STATS_DUMP": False,
            "REQUEST_TIMEOUT": 1,
            "CONCURRENCY": 1,
            "INTERVAL": 100,
        }
    )
    crawler = Crawler(_RetryBoundedSpider, settings)

    asyncio.run(asyncio.wait_for(crawler.crawl(), timeout=15))

    assert crawler.stats.get_value("request_scheduler_count") == 12
    assert crawler.stats.get_value("response_received_count") == 12


def test_unhandled_ignore_request_is_not_an_exception():
    manager = MiddlewareManager(_FakeCrawler())
    request = Request("http://example.com")

    async def process_request(request):
        raise IgnoreRequest("ignore")

    manager._process_request = process_request

    assert asyncio.run(manager.download(request)) is None


class _FailingCloseDownloader(DownloaderBase):
    async def download(self, request):
        return _response(request)

    async def close(self):
        raise RuntimeError("close-fail")


def test_downloader_close_failure_still_emits_spider_closed():
    _SlowSpider.closed_called = False
    settings = SettingsManager(
        {
            "DOWNLOADER": _FailingCloseDownloader,
            "LOG_LEVEL": "CRITICAL",
            "STATS_DUMP": False,
            "REQUEST_TIMEOUT": 1,
            "CONCURRENCY": 1,
            "INTERVAL": 100,
        }
    )
    crawler = Crawler(_SlowSpider, settings)

    asyncio.run(asyncio.wait_for(crawler.crawl(), timeout=10))

    assert _SlowSpider.closed_called is True
    assert crawler.stats.get_value("reason") == "finished"


def test_zero_concurrency_is_clamped():
    assert TaskManager(total_concurrency=0).semaphore._value == 1


class _NoIdleDownloader:
    @classmethod
    def create_instance(cls, *args, **kwargs):
        return cls()

    async def fetch(self, request):
        pass

    async def download(self, request):
        pass

    async def close(self):
        pass


def test_downloader_requires_idle_method():
    assert issubclass(_NoIdleDownloader, DownloaderBase) is False


class _EmptySpider(Spider):
    start_urls = []
    closed_called = False

    async def parse(self, response):
        return None

    async def spider_closed(self):
        type(self).closed_called = True


class _SlowCloseDownloader(DownloaderBase):
    closed = False

    async def download(self, request):
        return _response(request)

    async def close(self):
        await asyncio.sleep(0.5)
        type(self).closed = True


def test_empty_start_urls_finishes_cleanly():
    _EmptySpider.closed_called = False
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
    crawler = Crawler(_EmptySpider, settings)

    asyncio.run(asyncio.wait_for(crawler.crawl(), timeout=10))

    assert _EmptySpider.closed_called is True
    assert crawler.stats.get_value("response_received_count") is None


def test_cancellation_during_close_propagates_and_cleans_up():
    _SlowCloseDownloader.closed = False
    _EmptySpider.closed_called = False
    settings = SettingsManager(
        {
            "DOWNLOADER": _SlowCloseDownloader,
            "LOG_LEVEL": "CRITICAL",
            "STATS_DUMP": False,
            "REQUEST_TIMEOUT": 1,
            "CONCURRENCY": 1,
            "INTERVAL": 100,
        }
    )
    crawler = Crawler(_EmptySpider, settings)

    async def scenario():
        task = asyncio.create_task(crawler.crawl())
        await asyncio.sleep(0.3)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(task, timeout=5)

    asyncio.run(scenario())

    assert _SlowCloseDownloader.closed is True
    assert _EmptySpider.closed_called is True


class _EightUrlSpider(Spider):
    start_urls = [f"http://example.invalid/{index}" for index in range(8)]

    async def parse(self, response):
        return None


def test_concurrency_8_processes_all_requests():
    settings = SettingsManager(
        {
            "DOWNLOADER": _NullDownloader,
            "LOG_LEVEL": "CRITICAL",
            "STATS_DUMP": False,
            "REQUEST_TIMEOUT": 1,
            "CONCURRENCY": 8,
            "INTERVAL": 100,
        }
    )
    crawler = Crawler(_EightUrlSpider, settings)

    asyncio.run(asyncio.wait_for(crawler.crawl(), timeout=10))

    assert crawler.stats.get_value("response_received_count") == 8


class _ThreeItemSpider(Spider):
    start_urls = ["http://example.invalid/"]

    async def parse(self, response):
        for index in range(3):
            item = _ChildItem()
            item["url"] = f"{response.url}/{index}"
            item["title"] = "title"
            yield item


def test_items_are_counted():
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
    crawler = Crawler(_ThreeItemSpider, settings)

    asyncio.run(asyncio.wait_for(crawler.crawl(), timeout=10))

    assert crawler.stats.get_value("item_successful_count") == 3


def test_crawler_process_restores_sigint_handler():
    import signal

    process = CrawlerProcess(SettingsManager({"LOG_LEVEL": "CRITICAL"}))
    before = signal.getsignal(signal.SIGINT)

    asyncio.run(process.start())

    assert signal.getsignal(signal.SIGINT) is before


def test_engine_logger_uses_configured_log_level():
    crawler = _FakeCrawler()
    crawler.settings = SettingsManager({"MIDDLEWARES": [], "LOG_LEVEL": "CRITICAL"})

    engine = Engine(crawler)

    assert engine.logger.level == logging.CRITICAL


class _SlowStopEvent:
    def __init__(self):
        self._set = False
        self.cancelled = None

    def is_set(self):
        return self._set

    def set(self):
        self._set = True

    async def wait(self):
        try:
            await asyncio.sleep(5)
        except asyncio.CancelledError:
            self.cancelled.set()
            await asyncio.sleep(0.2)


def test_acquire_semaphore_does_not_swallow_outer_cancellation():
    engine = Engine(_FakeCrawler())

    async def scenario():
        stop_event = _SlowStopEvent()
        stop_event.cancelled = asyncio.Event()
        engine._stop_event = stop_event
        engine.running = True
        engine.task_manager.semaphore = asyncio.Semaphore(0)

        task = asyncio.create_task(engine._acquire_semaphore())
        await asyncio.sleep(0)
        engine.task_manager.semaphore.release()
        # 等到 finally 已取消 stop 任务并正在等待其结束
        await stop_event.cancelled.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(task, timeout=5)

    asyncio.run(scenario())
