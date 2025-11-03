"""
Bald Spider - A Python web scraping framework
"""

__version__ = "0.1.0"
__author__ = "Your Name"

from .main import main
from .http.request import Request

__all__ = ["main", "Request"]
