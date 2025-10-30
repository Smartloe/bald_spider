"""
Tests for the main module of bald_spider
"""

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
