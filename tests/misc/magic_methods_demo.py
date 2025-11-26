"""
教学代码：Python属性访问魔法方法详解
演示__getattr__、__getattribute__和__setattr__的使用和区别
"""


class A:
    # 类属性
    a = 1

    def __setattr__(self, key, value) -> None:
        """
        属性设置拦截器
        每当给实例设置属性时都会调用此方法
        """
        # 使用super()调用父类的__setattr__来实际设置属性
        super().__setattr__(key, value)  # 修正：应该是super()而不是super

    def __getattr__(self, item):
        """
        属性缺失处理器
        只有当正常属性查找失败（即属性不存在时）才会调用
        """
        print(f"__getattr__被调用，访问了不存在的属性: {item}")

    def __getattribute__(self, item):
        """
        属性访问拦截器（无条件调用）
        每次访问属性时都会首先调用此方法，无论属性是否存在
        """
        print(f"__getattribute__被调用，正在访问属性: {item}")
        # 注意：这里应该返回属性值，否则会返回None
        # 修正：应该调用父类的__getattribute__来避免递归
        return super().__getattribute__(item)


# 创建实例
a = A()

# 测试代码
# a.a = 3  # 这行被注释掉了，如果取消注释会触发__setattr__

print(a.aaaa)  # 访问不存在的属性
