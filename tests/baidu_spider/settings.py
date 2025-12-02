PROJECT_NAME = "baidu_spider"
TEST = 331
CONCURRENCY = 8
LOG_LEVEL = "DEBUG"
USE_SESSION = True
DOWNLOADER = "bald_spider.core.downloader.httpx_downloader.HTTPXDownloader"
MIDDLEWARES = [
    "middleware.TestMiddlware",
    "middleware.TestMiddlware2",
    "middleware.TestMiddlware3",
]
