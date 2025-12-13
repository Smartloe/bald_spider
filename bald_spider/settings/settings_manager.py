from copy import deepcopy
from importlib import import_module
import json
from typing import Any, Dict, List, Union, Optional
from bald_spider.settings import default_settings
from collections.abc import MutableMapping


class SettingsManager(MutableMapping):
    """
    设置管理器类，用于管理爬虫项目的配置设置
    继承自MutableMapping，使其具备类似字典的操作能力
    """

    def __init__(self, values: Optional[Dict[str, Any]] = None):
        """初始化设置管理器"""
        self.attributes: Dict[str, Any] = {}  # 存储所有设置的字典
        self.set_settings(default_settings)  # 加载默认设置
        self.update_values(values)  # 更新用户自定义设置

    def __getitem__(self, item: str) -> Any:
        """通过键获取设置值，如果键不存在返回None"""
        if item not in self:
            return None
        return self.attributes[item]

    def get(self, name: str, default: Any = None) -> Any:
        """安全获取设置值，如果值不存在返回默认值"""
        value = self[name]
        return value if value is not None else default

    def getint(self, name: str, default: int = 0) -> int:
        """获取整数类型的设置值"""
        value = self.get(name, default)
        if value is None:
            return default
        return int(value)

    def getfloat(self, name: str, default: float = 0.0) -> float:
        """获取浮点数类型的设置值"""
        value = self.get(name, default)
        if value is None:
            return default
        return float(value)

    def getbool(self, name: str, default: bool = False) -> bool:
        """获取布尔类型的设置值，支持多种布尔值格式"""
        got = self.get(name, default)
        
        # 如果是 None，返回默认值
        if got is None:
            return default
            
        # 如果已经是布尔类型，直接返回
        if isinstance(got, bool):
            return got
            
        try:
            # 尝试将数字字符串转换为布尔值
            int_val = int(got)
            return bool(int_val)
        except (ValueError, TypeError):
            # 处理文本形式的布尔值
            str_val = str(got).lower()
            if str_val in ("true", "1", "yes", "on"):
                return True
            if str_val in ("false", "0", "no", "off"):
                return False
            # 如果无法转换，抛出详细的错误信息
            raise ValueError(
                f"Invalid boolean value '{got}' for setting '{name}'. "
                f"Supported values are: "
                f"• True values: 1, '1', True, 'true', 'TRUE', 'yes', 'on'"
                f"• False values: 0, '0', False, 'false', 'FALSE', 'no', 'off'"
                f"Received type: {type(got).__name__}, value: {repr(got)}"
            )

    def getlist(self, name: str, default: Optional[List[Any]] = None) -> List[Any]:
        """获取列表类型的设置值，支持逗号分隔的字符串自动转换为列表"""
        if default is None:
            default = []
        value = self.get(name, default)
        
        if value is None:
            return default
            
        if isinstance(value, str):
            # 将逗号分隔的字符串拆分为列表
            value = [item.strip() for item in value.split(",") if item.strip()]
            
        if not hasattr(value, '__iter__') or isinstance(value, (str, bytes)):
            # 如果不是可迭代对象（除了字符串），包装成列表
            return [value]
            
        return list(value)

    def getdict(self, name: str, default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """获取字典类型的设置值，支持JSON字符串自动转换为字典"""
        if default is None:
            default = {}
        value = self.get(name, default)
        
        if value is None:
            return default
            
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError as e:
                raise ValueError(
                    f"Invalid JSON string for setting '{name}': {value}. "
                    f"Error: {e}"
                )
                
        if not isinstance(value, dict):
            # 尝试转换为字典，如果失败则返回默认值
            try:
                return dict(value)
            except (TypeError, ValueError):
                return default
                
        return value

    def __contains__(self, item: str) -> bool:
        """检查设置键是否存在"""
        return item in self.attributes

    def __setitem__(self, key: str, value: Any) -> None:
        """设置配置值"""
        self.set(key, value)

    def set(self, key: str, value: Any) -> None:
        """设置单个配置项"""
        self.attributes[key] = value

    def __delitem__(self, key: str) -> None:
        """删除配置项"""
        del self.attributes[key]

    def delete(self, key: str) -> None:
        """删除配置项的别名方法"""
        del self.attributes[key]

    def set_settings(self, module: Union[str, Any]) -> None:
        """从模块加载设置，只加载大写的变量"""
        if isinstance(module, str):
            module = import_module(module)  # 如果是字符串，导入对应的模块
        for key in dir(module):
            if key.isupper():  # 只处理大写的变量（约定为常量/设置）
                self.set(key, getattr(module, key))

    def __str__(self) -> str:
        """返回设置的字符串表示"""
        return f"<Settings values = {self.attributes}>"

    __repr__ = __str__  # 让repr和str显示相同的内容

    def __iter__(self):
        """返回设置的迭代器"""
        return iter(self.attributes)

    def __len__(self) -> int:
        """返回设置的数量"""
        return len(self.attributes)

    def update_values(self, values: Optional[Dict[str, Any]]) -> None:
        """批量更新设置值"""
        if values is not None:
            if not hasattr(values, 'items'):
                raise TypeError(f"Expected dict-like object, got {type(values).__name__}")
            for key, value in values.items():
                self.set(key, value)

    def copy(self) -> 'SettingsManager':
        """返回设置管理器的深拷贝"""
        return deepcopy(self)
