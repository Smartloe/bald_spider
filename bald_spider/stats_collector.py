from bald_spider.utils.log import get_logger
from pprint import pformat
from bald_spider.utils.date import date_delta, now


class StatsCollector:
    def __init__(self, crawler) -> None:
        self.crawler = crawler
        self._dump = self.crawler.settings.getbool("STATS_DUMP")
        self._stats = {}
        self.log = get_logger(self.__class__.__name__, "INFO")

    def inc_value(self, key, count=1, start=0):
        self._stats[key] = self._stats.get(key, start) + count

    def get_value(self, key, default=None):
        return self._stats.get(key, default)

    def get_stats(self):
        return self._stats

    def set_stats(self, Stats):
        self._stats = Stats

    def clear_stats(self):
        self._stats.clear()

    def close_spider(self, spider, reason):
        self._stats["end_time"] = now()
        self._stats["reason"] = reason
        self._stats["use_time"] = date_delta(self._stats["start_time"], self._stats["end_time"])
        if self._dump:
            self.log.info(f"{spider} stats:\n" + pformat(self._stats))

    def __getitem__(self, key):
        return self._stats[key]

    def __setitem__(self, key, value):
        self._stats[key] = value

    def __delitem__(self, key):
        del self._stats[key]
