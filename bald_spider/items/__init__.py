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

        # 合并父类字段，保证继承来的 Field 仍可用；子类同名字段覆盖父类。
        inherited_fields = {}
        for base in bases:
            inherited_fields.update(getattr(base, "FIELDS", {}))
        inherited_fields.update(field)

        cls_instance = super().__new__(mcs, name, bases, new_attrs)
        cls_instance.FIELDS = inherited_fields
        return cls_instance
