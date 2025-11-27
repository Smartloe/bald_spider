# 修复 downloader.py 中 debug 日志不输出问题

## 问题分析
通过分析代码，发现以下问题：

1. **日志级别配置问题**：虽然在 `tests/baidu_spider/settings.py` 中设置了 `LOG_LEVEL = "DEBUG"`，但在日志初始化时存在问题
2. **Logger 类使用问题**：在 `bald_spider/utils/log.py` 中，使用了 `logging.Logger` 类，但没有正确设置日志级别
3. **日志级别传递问题**：downloader 中获取到的 log_level 可能没有正确传递给 logger

## 具体问题点

### 1. Logger 初始化问题
在 `bald_spider/utils/log.py` 第 18 行：
```python
_logger = Logger(name)
```
这里使用的 `logging.Logger` 类需要手动设置 propagate 属性，否则不会向控制台输出。

### 2. 日志级别设置问题
虽然设置了 `handler.setLevel(log_level or INFO)` 和 `_logger.setLevel(log_level or INFO)`，但 Logger 类的特殊性导致 debug 级别日志无法输出。

## 解决方案

### 方案一：修改 Logger 类使用方式（推荐）
将 `bald_spider/utils/log.py` 中的 `Logger` 改为 `logging.getLogger()`，这是标准的日志获取方式。

### 方案二：修复现有 Logger 配置
设置 Logger 的 propagate 属性为 True，并确保所有日志处理器配置正确。

### 方案三：检查设置加载顺序
确保项目设置中的 LOG_LEVEL 能够正确覆盖默认设置。

## 实施步骤

1. 修改 `bald_spider/utils/log.py` 中的日志创建方式
2. 确保日志级别正确传递和应用
3. 测试 debug 日志输出
4. 验证其他日志级别是否正常工作

## 预期结果
修复后，运行 `run.py` 时应该能看到 downloader 中的 debug 日志输出：
```
request downloading: https://www.baidu.com, method: GET
```