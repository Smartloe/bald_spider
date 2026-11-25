# Bald Spider 🕷️

一个现代化的 Python 异步网络爬虫框架，专为高性能、可扩展的网络爬取而设计。基于 asyncio 构建，提供简洁而强大的 API。

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Build](https://img.shields.io/badge/Build-Modern%20Python-yellow.svg)](pyproject.toml)

## 🚀 快速开始

### 安装

```bash
# 使用 uv（推荐）
uv pip install -e .

# 或使用 pip
pip install -e .
```

### 5 分钟上手

创建你的第一个爬虫（以下三个文件放在同一目录）：

```python
# settings.py
PROJECT_NAME = "my_project"
CONCURRENCY = 8
```

```python
# my_spider.py
from bald_spider.spider import Spider
from bald_spider.http.request import Request


class MySpider(Spider):
    start_urls = ["https://httpbin.org"]

    async def parse(self, response):
        print(f"抓取完成: {response}")

        # 生成新的请求
        for i in range(5):
            yield Request(
                url=f"https://httpbin.org/delay/{i}",
                callback=self.parse_detail,
            )

    def parse_detail(self, response):
        print(f"详情页面: {response}")
```

```python
# run.py
import asyncio

from bald_spider.crawler import CrawlerProcess
from bald_spider.utils.project import get_settings
from my_spider import MySpider


async def main():
    settings = get_settings()
    process = CrawlerProcess(settings)
    await process.crawl(MySpider)
    await process.start()


if __name__ == "__main__":
    asyncio.run(main())
```

运行你的爬虫：

```bash
python run.py
```

> `get_settings()` 会导入当前目录下的 `settings.py`。不传参时 `CrawlerProcess()` 使用内置默认配置，但 `get_settings()` 需要该模块存在。

## 🏗️ 核心特性

### ⚡ 异步高性能
- 基于 asyncio 的异步架构，支持高并发网络请求
- 信号量并发控制，默认 16 个并发任务
- 生成器 / 异步生成器回调，内存友好
- 内置 `AioDownloader`（aiohttp）与 `HTTPXDownloader`（httpx），默认复用连接

### 🎯 智能调度
- 优先级队列：`priority` 数值越大越先处理
- 请求在调度器、下载器、处理器之间流式传递
- 阻塞式取队列 + 空闲监视器，工作耗尽后自动退出

### 🧩 中间件机制
- `process_request` / `process_response` / `process_exception` 三段式处理
- 内置默认请求头、下载延迟、状态码过滤、重试、状态码统计、异常忽略
- 支持按项目或按爬虫配置启用

### 🔧 灵活配置
- 分层配置系统：默认配置 → 项目配置 → 爬虫 `custom_settings`
- 支持 int / float / bool / list / dict 类型读取
- 文件内 `settings.py` 与爬虫级配置合并

### 🛡️ 生命周期与停机
- `spider_opened` 在首个请求发出前完成
- 正常结束、异常、任务取消、`Ctrl+C` 都会关闭下载器并触发 `spider_closed`
- 停机时取消在途任务，不会无限等待慢请求

## 🔄 工作流程

```
Spider.start_requests
        │
        ▼
   Scheduler（优先级队列）
        │  Request
        ▼
   Downloader.fetch ──► MiddlewareManager.download
        │                     │ process_request
        │                     ▼
        │              HTTP 下载器（aiohttp / httpx）
        │                     │ process_response / process_exception
        ▼                     ▼
      Response
        │
        ▼
   Engine._fetch ──► callback(parse) ──► transform（生成器 / 异步生成器）
        │
        ▼
   Processor 队列 ──► 新 Request 重新入队 / Item 计数与事件
```

## 📁 项目结构

```
bald_spider/
├── bald_spider/                    # 主要包目录
│   ├── __init__.py                # 包导出（Request / Response / Item / main）
│   ├── main.py                    # 包入口点
│   ├── crawler.py                 # Crawler / CrawlerProcess
│   ├── event.py                   # 事件常量
│   ├── exceptions.py              # 自定义异常
│   ├── stats_collector.py         # 统计收集
│   ├── subscriber.py              # 事件订阅/通知
│   ├── task_manager.py            # 并发与任务管理
│   ├── core/                      # 核心组件
│   │   ├── engine.py              # 中央协调引擎与退出模型
│   │   ├── processor.py           # 输出处理（Request 重新入队 / Item）
│   │   ├── scheduler.py           # 请求队列与周期统计
│   │   └── downloader/            # HTTP 下载器实现
│   │       ├── aiohttp_downloder.py
│   │       └── httpx_downloader.py
│   ├── http/                      # HTTP 数据结构
│   │   ├── __init__.py
│   │   ├── request.py             # 请求（优先级 / meta / 回调）
│   │   └── response.py            # 响应（text / xpath / json / urljoin）
│   ├── items/                     # 数据项定义
│   │   ├── __init__.py            # Field / ItemMeta
│   │   └── items.py               # 基础 Item 类
│   ├── middleware/                # 中间件
│   │   ├── middleware_manager.py  # 中间件管理器
│   │   ├── default_header.py
│   │   ├── download_delay.py
│   │   ├── request_ignore.py
│   │   ├── response_code.py
│   │   ├── response_filter.py
│   │   └── retry.py
│   ├── spider/                    # 爬虫框架
│   │   └── __init__.py            # 基础 Spider 类
│   ├── settings/                  # 配置管理
│   │   ├── __init__.py
│   │   ├── default_settings.py    # 默认配置
│   │   └── settings_manager.py    # 设置加载/合并
│   └── utils/                     # 工具模块
│       ├── date.py
│       ├── log.py
│       ├── pqueue.py              # 优先级队列
│       ├── project.py             # 项目设置/动态导入
│       ├── spider.py              # 回调输出转换
│       └── system.py
├── tests/                         # 测试套件和示例
│   ├── test_main.py               # 包入口测试
│   ├── test_regressions.py        # 回归测试
│   └── baidu_spider/              # 示例爬虫项目
│       ├── spiders/               # 爬虫实现
│       │   ├── baidu.py
│       │   └── baidu2.py
│       ├── items.py
│       ├── middleware.py
│       ├── settings.py
│       └── run.py
├── main.py                        # 仓库根入口脚本
├── pyproject.toml                 # 项目与工具配置
├── uv.lock                        # 依赖锁定文件
└── README.md
```

## 🎮 进阶用法

### 自定义数据项

```python
from bald_spider.items import Field
from bald_spider.items.items import Item


class ProductItem(Item):
    name = Field()
    price = Field()
    description = Field()


item = ProductItem()
item["name"] = "示例商品"
item["price"] = 99.0
```

注意：

- 字段必须通过 `item["field"] = value` 赋值，不能使用 `item.field = value`。
- `Item` 支持继承，子类会合并父类的 `FIELDS`。

### 同步 / 异步回调

`parse` 及 `callback` 可以是普通函数、生成器、`async def` 协程或**异步生成器**：

```python
from bald_spider.items import Field
from bald_spider.items.items import Item


class PageItem(Item):
    url = Field()


class CallbackSpider(Spider):
    start_urls = ["https://example.com"]

    # 异步生成器：边解析边产出 Request / Item
    async def parse(self, response):
        for link in response.xpath("//a/@href").getall():
            yield Request(response.urljoin(link), callback=self.parse_detail)

    def parse_detail(self, response):
        item = PageItem()
        item["url"] = response.url
        yield item  # 回调只接受 Request / Item
```

> 回调的返回值必须是生成器 / 异步生成器；返回其他类型会被包装为 `TransformTypeError` 并记录到 `spider_exceptions/*` 统计，不会静默丢弃。返回 `None` 或空列表表示本次没有产出。

`start_requests` 同样支持同步或异步生成器：

```python
class AsyncStartSpider(Spider):
    async def start_requests(self):
        yield Request("https://example.com", callback=self.parse)
```

### 高级请求配置

```python
from bald_spider.http.request import Request


class AdvancedSpider(Spider):
    start_urls = ["https://api.example.com"]

    def start_requests(self):
        for url in self.start_urls:
            yield Request(
                url=url,
                headers={
                    "User-Agent": "BaldSpider/1.0",
                    "Authorization": "Bearer token",
                },
                method="POST",
                body='{"query": "data"}',
                priority=10,          # 数值越大越先处理
                callback=self.parse,
                meta={"dont_retry": True},
            )
```

请求还支持 `cookie`、`proxy`（URL 字符串）、`encoding`。

### 爬虫级配置

```python
class HighConcurrencySpider(Spider):
    start_urls = ["https://example.com"]
    custom_settings = {
        "CONCURRENCY": 32,
        "REQUEST_TIMEOUT": 30,
    }

    async def parse(self, response):
        pass
```

### 生命周期与事件

```python
class LifecycleSpider(Spider):
    start_urls = ["https://example.com"]

    async def spider_opened(self):
        # 在首个请求发出前完成，适合登录、初始化请求头
        self.default_headers = {"Authorization": "Bearer token"}

    async def spider_closed(self):
        # 正常结束、异常、取消、Ctrl+C 时都会触发
        pass
```

框架会自动把 `spider_opened` / `spider_closed` 事件绑定到 Spider 的同名方法。其余事件会照常派发，可通过 `crawler.subscriber` 手动订阅：

```python
from bald_spider.event import item_successful, spider_error


class SubscribeSpider(Spider):
    start_urls = ["https://example.com"]

    async def spider_opened(self):
        self.crawler.subscriber.subscriber(self.on_item, event=item_successful)
        self.crawler.subscriber.subscriber(self.on_error, event=spider_error)

    async def on_item(self, item, spider):
        print(f"产出 Item: {item}")

    async def on_error(self, exception, spider):
        # 回调产出异常对象时触发，同时计入 spider_exceptions/* 统计
        print(f"爬虫异常: {exception}")
```

可用事件：`spider_opened`、`spider_closed`、`spider_error`、`request_scheduled`、`response_received`、`item_successful`、`ignore_request`。

### 自定义中间件

```python
from bald_spider.middleware import BaseMiddleware


class CustomMiddleware(BaseMiddleware):
    def process_request(self, request, spider):
        # 修改后返回 None；返回 Request 会被视为短路并重新入队
        request.headers["User-Agent"] = "CustomBot/1.0"
        return None

    async def process_response(self, request, response, spider):
        # 返回 Response 继续处理；返回 Request 则重新入队
        return response

    async def process_exception(self, request, exception, spider):
        # 返回 True 表示已处理；返回 False / None 交给后续中间件
        return None
```

在 `settings.py` 中启用：

```python
MIDDLEWARES = [
    "middleware.CustomMiddleware",
    "bald_spider.middleware.default_header.DefaultHeader",
    "bald_spider.middleware.download_delay.DownloadDelay",
    "bald_spider.middleware.response_filter.ResponseFilter",
    "bald_spider.middleware.retry.Retry",
    "bald_spider.middleware.response_code.ResponseCodeStats",
    "bald_spider.middleware.request_ignore.RequestIngore",
]
```

### 多爬虫项目

```python
# run_multiple.py
async def main():
    settings = get_settings()
    process = CrawlerProcess(settings)

    await process.crawl(MySpider)
    await process.crawl(AnotherSpider)
    await process.crawl(ThirdSpider)

    await process.start()
```

### 优雅停机

- 正常结束：调度器、下载器、任务、处理器全部空闲后自动退出。
- `Ctrl+C`：置停主循环，取消在途任务，关闭下载器并触发 `spider_closed`。
- 程序化取消 `crawler.crawl()` 任务：同样会完成资源清理后再向上传播 `CancelledError`。
- 已出队但尚未登记为任务的请求被计入在途，不会被误判为空闲而丢弃。

## 🔧 开发

### 环境设置

```bash
# 安装开发依赖
uv sync --extra dev

# 或使用 pip
pip install -e ".[dev]"
```

### 运行测试

```bash
# 运行所有测试
uv run pytest

# 详细输出
uv run pytest -v

# 运行特定测试
uv run pytest tests/test_regressions.py
```

### 代码格式化

```bash
uv run black .
```

### 运行示例

```bash
cd tests/baidu_spider
python run.py
```

## ⚙️ 配置选项

### 默认配置（`bald_spider/settings/default_settings.py`）

| 配置项 | 默认值 | 说明 |
|---|---|---|
| `CONCURRENCY` | `16` | 最大并发任务数 |
| `LOG_LEVEL` | `"INFO"` | 日志级别 |
| `PROJECT_NAME` | `""` | 项目名（用于日志） |
| `VERIFY_SSL` | `True` | 是否校验 SSL 证书 |
| `REQUEST_TIMEOUT` | `60` | 请求超时（秒） |
| `USE_SESSION` | `True` | 是否复用 HTTP 连接 |
| `DOWNLOADER` | `AioDownloader` | 下载器类路径 |
| `INTERVAL` | `5` | 统计日志间隔（秒） |
| `STATS_DUMP` | `True` | 结束时打印统计 |
| `SCHEDULER_QUEUE_SIZE` | `1000` | 调度队列上限，`0` 表示不限制 |
| `MIDDLEWARES` | `[]` | 启用的中间件；默认为空 |
| `USER_AGENT` | `""` | 默认 User-Agent（配合 `DefaultHeader`） |
| `DEFAULT_HEADERS` | `{}` | 默认请求头（配合 `DefaultHeader`） |
| `DOWNLOAD_DELAY` | `0` | 请求间隔（秒），`0` 表示不启用延迟中间件 |
| `RANDOMNESS` | `True` | 延迟是否随机波动 |
| `RANDOM_RANGE` | `(0.75, 1.25)` | 随机延迟范围系数（旧拼写 `RANDEOM_RANGE` 仍兼容） |
| `RETRY_HTTP_CODES` | `[408, 429, 500, 503, 504, 522, 524]` | 触发重试的状态码 |
| `IGNORE_HTTP_CODES` | `[403, 404]` | 不重试的状态码 |
| `MAX_RETRY_TIMES` | `2` | 最大重试次数 |
| `RETRY_EXCEPTIONS` | `[]` | 额外需要重试的异常类型 |
| `ALLOWED_CODES` | `[]` | 额外允许的状态码 |

> 默认配置**不启用任何中间件**。需要重试、默认请求头、下载延迟等能力时，请在 `settings.py` 中显式配置 `MIDDLEWARES`。

### 项目配置

```python
# settings.py
PROJECT_NAME = "my_project"
CONCURRENCY = 8               # 降低并发数
REQUEST_TIMEOUT = 30          # 请求超时（秒）
MAX_RETRY_TIMES = 3           # 最大重试次数
DOWNLOAD_DELAY = 1.0          # 下载延迟（秒）

USER_AGENT = "MyBot/1.0"
DEFAULT_HEADERS = {
    "User-Agent": "MyBot/1.0",
    "Connection": "keep-alive",
}

MIDDLEWARES = [
    "bald_spider.middleware.default_header.DefaultHeader",
    "bald_spider.middleware.download_delay.DownloadDelay",
    "bald_spider.middleware.response_filter.ResponseFilter",
    "bald_spider.middleware.retry.Retry",
]
```

### 中间件执行顺序

`MIDDLEWARES` 中的 `process_request` 按配置顺序执行，而 `process_response` / `process_exception` 按**逆序**执行。需要重试时，请把 `Retry` 放在 `ResponseFilter` **之后**（即示例配置中的顺序），否则 500 响应会先被 `ResponseFilter` 抛出的 `IgnoreRequest` 拦截，导致重试失效。

### 支持的配置类型

```python
settings.getint("CONCURRENCY", 16)      # 整数
settings.getfloat("DOWNLOAD_DELAY", 0)  # 浮点数
settings.getbool("VERIFY_SSL", True)    # 布尔值
settings.getlist("MIDDLEWARES", [])     # 列表
settings.getdict("DEFAULT_HEADERS", {}) # 字典
```

## 📊 性能特性

- **异步优先**：基于 asyncio 的高性能并发处理
- **内存效率**：生成器 / 异步生成器回调，避免一次性加载大量数据
- **连接复用**：aiohttp / httpx 下载器默认复用会话（`USE_SESSION=True`）
- **可配置负载**：信号量限制并发，`DownloadDelay` 控制请求频率
- **模块化**：引擎、调度器、下载器、处理器、中间件职责清晰，便于替换与扩展

## ⚠️ 已知限制

- **请求去重尚未实现**：同一 URL 会被重复抓取（`Engine._schedule_request` 中为 TODO）。
- **背压可配置**：调度队列默认上限 1000（`SCHEDULER_QUEUE_SIZE`），超限时生产者会等待；设为 `0` 可关闭限制。
- **处理器队列不设上限**：无限解析输出会持续占用内存并长期持有并发许可；背压仅作用于调度队列。
- **无数据管道与持久化**：`Item` 目前只做计数与事件通知，需自行处理存储。
- **无分布式支持与 Web 界面**：属于后续规划。
- `HTTPXDownloader` 在设置 per-request `proxy` 时会退化为一次性 client。

## 🤝 贡献

欢迎贡献代码！请遵循以下步骤：

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

### 开发约定

- 使用 Python 3.11+ 和现代语法
- 添加类型注解
- 编写单元测试
- 保持代码格式一致（使用 black）

## 📄 许可证

本项目采用 [MIT 许可证](LICENSE) - 开源、免费、无限制使用。

## 🙏 致谢

- [Python asyncio](https://docs.python.org/3/library/asyncio.html) - 异步编程基础
- [Scrapy](https://scrapy.org/) - 灵感来源
- [uv](https://github.com/astral-sh/uv) - 现代包管理

## 📚 更多资源

- **完整示例**：查看 `tests/baidu_spider/` 目录
- **架构文档**：[ARCHITECTURE.md](ARCHITECTURE.md) - 系统架构与数据流
- **开发指南**：[DEVELOPMENT_GUIDE.md](DEVELOPMENT_GUIDE.md) - 贡献指南和开发规范
- **技术栈**：[TECH_STACK_AND_PREFERENCES.md](TECH_STACK_AND_PREFERENCES.md) - 技术选择和最佳实践
- **项目概述**：[PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md) - 项目愿景和发展路线图

---

🕷️ **Bald Spider** - 让网络爬取变得简单而强大
