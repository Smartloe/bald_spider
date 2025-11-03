class A:
    def __getitem__(self, item):
        """
        实现索引访问操作 a[key] 时调用
        item: 可以是整数索引、切片对象(slice)或字符串键
        """
        print(item)

    def __setitem__(self, name, val):
        """
        实现索引赋值操作 a[key] = value 时调用
        name: 键名
        val: 要设置的值
        """
        print(name, val)


a = A()
a[1]  # 输出: 1 - 调用 __getitem__
a[1:3]  # 输出: slice(1, 3, None) - 调用 __getitem__，传入slice对象
a["key"] = "val"  # 输出: key val - 调用 __setitem__
