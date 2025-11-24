from bald_spider.items import Field


class Item:

    FIELDS: dict

    def __init__(self) -> None:
        pass

    def __setitem__(self, key, value):
        pass


if __name__ == "__main__":

    class TestItem(Item):
        url = Field()
        title = Field()

    tes_item = TestItem()
