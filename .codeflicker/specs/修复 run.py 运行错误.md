# 修复 run.py 运行错误

## 问题分析
根据错误信息，主要有以下几个问题：

### 1. 主要错误：Response 对象创建失败
**错误信息**：`AttributeError: 'ClientResponse' object has no attribute 'header'`
**问题位置**：`bald_spider/core/downloader.py` 第74行
**问题代码**：
```python
status=response.headers.status  # 错误：headers 是字典，没有 status 属性
```
**正确代码**：
```python
status=response.status  # 正确：ClientResponse 对象有 status 属性
```

### 2. 次要问题：资源未正确关闭
**错误信息**：
- `Unclosed client session`
- `Unclosed connector`
**问题原因**：downloader 的 session 和 connector 没有在使用完毕后正确关闭

### 3. POST 请求方法错误
**问题位置**：`bald_spider/core/downloader.py` 第93行
**问题代码**：
```python
response = await self.session.get(...)  # POST 请求使用了 get 方法
```
**正确代码**：
```python
response = await self.session.post(...)  # POST 请求应该使用 post 方法
```

## 修复方案

### 方案一：修复 Response 创建错误（紧急修复）
1. 修复 `structure_response` 方法中的 `response.headers.status` 为 `response.status`
2. 这是导致运行失败的主要原因

### 方案二：修复 POST 请求方法
1. 将 `_post` 方法中的 `session.get` 改为 `session.post`

### 方案三：添加资源清理机制
1. 在 downloader 中添加 `close` 方法
2. 在 engine 中确保 downloader 被正确关闭
3. 使用 try-finally 或 context manager 确保资源释放

### 方案四：错误处理优化
1. 在 `download` 方法中改进异常处理
2. 确保异常情况下也能正确返回或处理错误

## 实施优先级
1. **高优先级**：修复 Response 创建错误（方案一）
2. **中优先级**：修复 POST 请求方法（方案二）
3. **低优先级**：添加资源清理机制（方案三）

## 预期结果
修复后，`run.py` 应该能够：
- ✅ 正常发起 HTTP 请求
- ✅ 正确创建 Response 对象
- ✅ 输出 debug 日志
- ✅ 正常处理爬虫数据
- ✅ 避免资源泄漏警告