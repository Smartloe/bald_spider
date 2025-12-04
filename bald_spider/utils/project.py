from inspect import iscoroutinefunction
import sys
from typing import Callable
from bald_spider.settings.settins_manager import SettingsManager
import os
from importlib import import_module


async def common_call(func: Callable, *args, **kwargs):
    if iscoroutinefunction(func):
        return await func(*args, **kwargs)
    else:
        return func(*args, **kwargs)


def _get_closest(path="."):
    path = os.path.abspath(path)
    return path


def _init_env():
    closest = _get_closest()
    if closest:
        project_dir = os.path.dirname(closest)
        sys.path.append(project_dir)


def get_settings(settings="settings"):
    _settings = SettingsManager()
    _init_env()
    _settings.set_settings(settings)
    return _settings


def merge_settings(spider, settings):
    if hasattr(spider, "custom_settings"):
        custom_settings = getattr(spider, "custom_settings")
        settings.update_values(custom_settings)


def load_class(_path):
    if not isinstance(_path, str):
        if callable(_path):
            return _path
        else:
            raise TypeError(f"args excepted string or object, got: {type(_path)}")
    module, name = _path.rsplit(".", 1)
    mod = import_module(module)
    try:
        cls = getattr(mod, name)
    except AttributeError:
        raise NameError(f"Module {module!r} doesn't define any object named {name!r}")
    return cls
