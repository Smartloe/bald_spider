from bald_spider.items import Field, ItemMeta


class Item(metaclass=ItemMeta):

    FIELDS: dict

    def __init__(self) -> None:
        self.values = {}
        print(f"Fields: {self.FIELDS}")

    def __setitem__(self, key, value):
        if key in self.FIELDS:
            self.values[key] = value
        else:
            raise KeyError(f"{self.__class__.__name__} does not support field: {key}")

    def __repr__(self) -> str:
        return str(self.values)

    def __getitem__(self, key):
        return self.values[key]

    def __delitem__(self, key):
        del self.values[key]

    __str__ = __repr__


if __name__ == "__main__":

    class TestItem(Item):
        url = Field()
        title = Field()

    class TestItem2(Item):
        name = Field()

    test_item = TestItem()
    test_item["url"] = "https://www.baidu.com"
    print(test_item["url"])
    print(test_item)
