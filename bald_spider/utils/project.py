from bald_spider.settings.settins_manager import SettingsManager


def get_settings(settings="settings"):
    _settings = SettingsManager()
    _settings.set_settings(settings)
    return _settings


def merge_settings(spider,settings):
    if hasattr(spider, "custom_settings"):
        custom_settings = getattr(spider, "custom_settings")
        settings.update_values(custom_settings)
