# 从 tests.baidu_spider 包中导入 settings 模块
from tests.baidu_spider import settings

print(type(settings))  # <class 'module'>
# 确认 settings 确实是一个模块对象

for name in dir(settings):
	# dir(settings) 返回模块中所有可访问的属性名列表
	if name.isupper():
		# 只处理全大写的属性名（通常是常量）
		print(getattr(settings, name))
		# 使用 getattr 动态获取该属性的值并打印
