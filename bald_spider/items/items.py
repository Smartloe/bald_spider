from copy import deepcopy
from pprint import pformat
from collections.abc import MutableMapping
from bald_spider.exceptions import ItemAttribuError, ItemInError
from bald_spider.items import Field, ItemMeta


class Item(MutableMapping, metaclass=ItemMeta):

    FIELDS: dict

    def __init__(self, *args, **kwargs) -> None:
        self._values = {}
        if args:
            raise ItemInError(f"{self.__class__.__name__} : position args is not suppored,use keywords args.")
        if kwargs:
            for key, value in kwargs.items():
                self[key] = value

    def __setitem__(self, key, value):
        if key in self.FIELDS:
            self._values[key] = value
        else:
            raise KeyError(f"{self.__class__.__name__} does not support field: {key}")

    def __repr__(self) -> str:
        return pformat(dict(self))

    def __getitem__(self, key):
        return self._values[key]

    def __delitem__(self, key):
        del self._values[key]

    def __setattr__(self, key, value):
        # 允许设置内部属性：以 _ 开头的，或者特定的内部属性
        if key.startswith("_") or key in ["values"]:
            super().__setattr__(key, value)
        else:
            raise AttributeError(f"use item[{key!r}]={value!r} to set field value.")

    def __getattr__(self, item):
        raise AttributeError(
            f"{self.__class__.__name__} does not support field: {item}."
            f"please add the `{item}` field to the {self.__class__.__name__},"
            f"and use item `{item!r}` to get field value!"
        )

    def __getattribute__(self, item):
        # 检查是否是字段访问
        fields = super().__getattribute__("FIELDS")
        if item in fields:
            raise ItemAttribuError(f"use item[{item!r}] to get field value.")
        else:
            return super().__getattribute__(item)

    __str__ = __repr__

    def __iter__(self):
        return iter(self._values)

    def __len__(self):
        return len(self._values)

    def to_dict(self):
        return dict(self)

    def copy(self):
        return deepcopy(self)


if __name__ == "__main__":

    class TestItem(Item):
        url = Field()
        title = Field()

    test_item = TestItem("www.baidu.com")
    # test_item["url"] = "www.baidu.com"
    print(test_item["url"])
