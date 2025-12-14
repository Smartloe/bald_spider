"""
defult config
"""

CONCURRENCY = 16
LOG_LEVEL = "INFO"
VERIFY_SSL = True
REQUEST_TIMEOUT = 60
USE_SESSION = True
DOWNLOADER = "bald_spider.core.downloader.aiohttp_downloder.AioDownloader"
INTERVAL = 5
STATS_DUMP = True
# download delay
DOWNLOAD_DELAY = 0
RANDOMNESS = True
RANDEOM_RANGE = (0.75, 1.25)
# retry
RETRY_HTTP_CODES = [408, 429, 500, 503, 504, 522, 524]
IGNORE_HTTP_CODES = [403, 404]
MAX_RETRY_TIMES = 2
ALLOWED_CODES = []
