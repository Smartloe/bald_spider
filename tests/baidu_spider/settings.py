PROJECT_NAME = "baidu_spider"
TEST = 331
CONCURRENCY = 1
LOG_LEVEL = "DEBUG"
USE_SESSION = True
DOWNLOADER = "bald_spider.core.downloader.httpx_downloader.HTTPXDownloader"
STATS_DUMP = True
MIDDLEWARES = [
    "middleware.TestMiddlware",
    #     "middleware.TestMiddlware2",
    #     "middleware.TestMiddlware3",
]
