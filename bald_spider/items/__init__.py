from abc import ABCMeta


class Field(dict):
    pass


class ItemMeta(ABCMeta):

    def __new__(mcs, name, bases, attrs):
        field = dict()
        # 创建一个新的属性字典，移除 Field 实例
        new_attrs = {}
        for key, value in attrs.items():
            if isinstance(value, Field):
                field[key] = value
            else:
                new_attrs[key] = value
        
        cls_instance = super().__new__(mcs, name, bases, new_attrs)
        cls_instance.FIELDS = field
        return cls_instance
