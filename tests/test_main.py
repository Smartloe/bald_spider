"""
Tests for the main module of bald_spider
"""

import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from bald_spider.main import main


def test_main_function(capsys):
    """Test that main function prints the expected message"""
    main()
    captured = capsys.readouterr()
    assert "Hello from bald-spider!" in captured.out


def test_main_module_execution():
    """Test that the module can be imported and executed"""
    # This test ensures the module structure is correct
    import bald_spider
    assert hasattr(bald_spider, 'main')
    assert callable(bald_spider.main)
