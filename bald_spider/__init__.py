"""
Bald Spider - A Python web scraping framework
"""

__version__ = "0.1.0"
__author__ = "陈希瑞"

from bald_spider.http.request import Request
from bald_spider.http.response import Response
from bald_spider.items.items import Item
from bald_spider.main import main

__all__ = ["main", "Request", "Response", "Item"]
