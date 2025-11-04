from importlib import import_module
from bald_spider.settings import default_settings
from collections.abc import MutableMapping


class SettingsManager(MutableMapping):
    """
    设置管理器类，用于管理爬虫项目的配置设置
    继承自MutableMapping，使其具备类似字典的操作能力
    """

    def __init__(self, values=None):
        """初始化设置管理器"""
        self.attributes = {}  # 存储所有设置的字典
        self.set_settings(default_settings)  # 加载默认设置
        self.update_values(values)  # 更新用户自定义设置

    def __getitem__(self, item):
        """通过键获取设置值，如果键不存在返回None"""
        if item not in self:
            return None
        return self.attributes[item]

    def get(self, name, default=None):
        """安全获取设置值，如果值不存在返回默认值"""
        return self[name] if self[name] is not None else default

    def getint(self, name, default=0):
        """获取整数类型的设置值"""
        return int(self.get(name, default))

    def getfloat(self, name, default=0.0):
        """获取浮点数类型的设置值"""
        return float(self.get(name, default))

    def getbool(self, name, default=False):
        """获取布尔类型的设置值，支持多种布尔值格式"""
        got = self.get(name, default)
        try:
            return bool(int(got))  # 尝试将数字字符串转换为布尔值
        except ValueError:
            # 处理文本形式的布尔值
            if got in ("True", "true", "TRUE"):
                return True
            if got in ("False", "false", "FALSE"):
                return False
            # 如果无法转换，抛出详细的错误信息
            raise ValueError(
                f"Invalid boolean value '{got}' for setting '{name}'. "
                f"Supported values are: "
                f"• True values: 1, '1', True, 'True', 'true', 'TRUE'"
                f"• False values: 0, '0', False, 'False', 'false', 'FALSE'"
                f"Received type: {type(got).__name__}, value: {repr(got)}"
            )

    def getlist(self, name, default=None):
        """获取列表类型的设置值，支持逗号分隔的字符串自动转换为列表"""
        value = self.get(name, default or [])
        if isinstance(value, str):
            value = value.split(",")  # 将逗号分隔的字符串拆分为列表
        return list(value)

    def __contains__(self, item):
        """检查设置键是否存在"""
        return item in self.attributes

    def __setitem__(self, key, value):
        """设置配置值"""
        self.set(key, value)

    def set(self, key, value):
        """设置单个配置项"""
        self.attributes[key] = value

    def __delitem__(self, key):
        """删除配置项"""
        del self.attributes[key]

    def delete(self, key):
        """删除配置项的别名方法"""
        del self.attributes[key]

    def set_settings(self, module):
        """从模块加载设置，只加载大写的变量"""
        if isinstance(module, str):
            module = import_module(module)  # 如果是字符串，导入对应的模块
        for key in dir(module):
            if key.isupper():  # 只处理大写的变量（约定为常量/设置）
                self.set(key, getattr(module, key))

    def __str__(self):
        """返回设置的字符串表示"""
        return f"<Settings values = {self.attributes}>"

    __repr__ = __str__  # 让repr和str显示相同的内容

    def __iter__(self):
        """返回设置的迭代器"""
        return iter(self.attributes)

    def __len__(self):
        """返回设置的数量"""
        return len(self.attributes)

    def update_values(self, values):
        """批量更新设置值"""
        if values is not None:
            for key, value in values.items():
                self.set(key, value)
