PROJECT_NAME = "baidu_spider"
TEST = 331
CONCURRENCY = 1
LOG_LEVEL = "DEBUG"
USE_SESSION = True
DOWNLOADER = "bald_spider.core.downloader.httpx_downloader.HTTPXDownloader"
STATS_DUMP = True
MIDDLEWARES = [
    # engine side
    "bald_spider.middleware.download_delay.DownloadDelay",
    "bald_spider.middleware.default_header.DefaultHeader",
    "bald_spider.middleware.retry.Retry",
    "bald_spider.middleware.response_code.ResponseCodeStats",
    "bald_spider.middleware.request_ignore.RequestIngore",
    "middleware.TestMiddlware",
    "middleware.TestMiddlware2",
    #     "middleware.TestMiddlware3",
    # downloader side
]
DOWNLOAD_DELAY = 2
RANDOMNESS = True
RANDEOM_RANGE = (0.75, 1.25)
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Connection": "keep-alive",
}
