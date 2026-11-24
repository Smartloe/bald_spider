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

### 5分钟上手

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
                callback=self.parse_detail
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

## 🏗️ 核心特性

### ⚡ 异步高性能
- 基于 asyncio 的异步架构，支持高并发网络请求
- 智能并发控制，默认支持16个并发请求
- 内存友好的生成器模式，避免大量数据加载

### 🎯 智能调度
- 优先级队列支持，priority 数值越大越先处理
- 基于优先级的请求调度
- 非阻塞的请求队列管理

### 🔧 灵活配置
- 分层配置系统：默认配置 → 项目配置 → 爬虫自定义配置
- 支持多种数据类型：int、float、bool、list
- 运行时配置动态调整

### 📦 模块化设计
- 清晰的组件分离：引擎、下载器、调度器、任务管理器
- 易于扩展和定制
- 支持中间件和插件系统

## 📁 项目结构

```
bald_spider/
├── bald_spider/                    # 主要包目录
│   ├── __init__.py                # 包导出
│   ├── main.py                    # 包入口点
│   ├── crawler.py                 # Crawler / CrawlerProcess
│   ├── event.py                   # 事件常量
│   ├── exceptions.py              # 自定义异常
│   ├── stats_collector.py         # 统计收集
│   ├── subscriber.py              # 事件订阅/通知
│   ├── task_manager.py            # 并发控制
│   ├── core/                      # 核心组件
│   │   ├── engine.py              # 中央协调引擎
│   │   ├── processor.py           # 输出处理
│   │   ├── scheduler.py           # 请求队列管理
│   │   └── downloader/            # HTTP 下载器实现
│   │       ├── aiohttp_downloder.py
│   │       └── httpx_downloader.py
│   ├── http/                      # HTTP 数据结构
│   │   ├── request.py             # 请求
│   │   └── response.py            # 响应
│   ├── items/                     # 数据项定义
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
│   │   ├── default_settings.py    # 默认配置
│   │   └── settings_manager.py    # 设置加载/合并
│   └── utils/                     # 工具模块
│       ├── date.py
│       ├── log.py
│       ├── pqueue.py              # 自定义优先级队列
│       ├── project.py             # 项目设置工具
│       ├── spider.py              # 爬虫辅助函数
│       └── system.py
├── tests/                         # 测试套件和示例
│   ├── test_main.py               # 基础框架测试
│   ├── test_regressions.py        # 回归测试
│   └── baidu_spider/              # 示例爬虫项目
│       ├── spiders/               # 爬虫实现
│       │   ├── baidu.py           # 百度示例爬虫
│       │   └── baidu2.py          # 多爬虫示例
│       ├── items.py               # 项目特定数据项
│       ├── middleware.py          # 示例中间件
│       ├── settings.py            # 项目配置
│       └── run.py                 # 爬虫执行脚本
├── main.py                        # 仓库根入口脚本
├── pyproject.toml                 # 现代 Python 包配置
├── uv.lock                        # 依赖锁定文件
└── README.md                      # 项目文档
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
```

注意：`Item` 的字段必须通过 `item["field"] = value` 赋值，不能使用 `item.field = value`。

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
                    "Authorization": "Bearer token"
                },
                method="POST",
                body='{"query": "data"}',
                priority=10,  # 高优先级
                callback=self.parse
            )
```

### 爬虫级配置

```python
class HighConcurrencySpider(Spider):
    start_urls = ["https://example.com"]
    custom_settings = {
        "CONCURRENCY": 32,  # 为这个爬虫设置更高的并发数
        "REQUEST_TIMEOUT": 30
    }
    
    async def parse(self, response):
        # 解析逻辑
        pass
```

### 多爬虫项目

```python
# run_multiple.py
async def main():
    settings = get_settings()
    process = CrawlerProcess(settings)
    
    # 添加多个爬虫
    await process.crawl(MySpider)
    await process.crawl(AnotherSpider)
    await process.crawl(ThirdSpider)
    
    await process.start()
```

## 🔧 开发

### 环境设置

```bash
# 安装开发依赖
uv sync

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
uv run pytest tests/test_main.py
```

### 代码格式化

```bash
# 格式化代码
uv run black .

# 检查类型
mypy bald_spider/
```

### 运行示例

```bash
# 运行百度爬虫示例
cd tests/baidu_spider
python run.py
```

## ⚙️ 配置选项

### 默认配置

```python
# bald_spider/settings/default_settings.py
CONCURRENCY = 16              # 最大并发请求数
REQUEST_TIMEOUT = 60          # 请求超时时间（秒）
```

### 项目配置

```python
# settings.py
PROJECT_NAME = "my_project"
CONCURRENCY = 8               # 降低并发数
REQUEST_TIMEOUT = 30          # 请求超时时间（秒）
MAX_RETRY_TIMES = 3           # 最大重试次数
DOWNLOAD_DELAY = 1.0          # 下载延迟（秒）
```

### 中间件执行顺序

`MIDDLEWARES` 中的 `process_request` 按配置顺序执行，而 `process_response` / `process_exception` 按**逆序**执行。需要重试时，请把 `Retry` 放在 `ResponseFilter` **之后**（即示例配置中的顺序），否则 500 响应会先被 `ResponseFilter` 抛出的 `IgnoreRequest` 拦截，导致重试失效。

### 支持的配置类型

```python
# 获取不同类型的配置值
settings.getint("CONCURRENCY", 16)      # 整数
settings.getfloat("TIMEOUT", 30.0)      # 浮点数
settings.getbool("DEBUG", False)        # 布尔值
settings.getlist("PROXIES", [])         # 列表
```

## 📊 性能特性

- **异步优先设计**：基于 asyncio 的高性能并发处理
- **内存效率**：生成器模式避免大量数据加载
- **I/O 优化**：异步操作避免网络请求阻塞
- **可配置负载**：信号量控制防止服务器过载
- **可扩展设计**：模块化架构支持水平扩展

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
- **架构文档**：[ARCHITECTURE.md](ARCHITECTURE.md) - 详细的系统架构和组件设计
- **开发指南**：[DEVELOPMENT_GUIDE.md](DEVELOPMENT_GUIDE.md) - 贡献指南和开发规范
- **技术栈**：[TECH_STACK_AND_PREFERENCES.md](TECH_STACK_AND_PREFERENCES.md) - 技术选择和最佳实践
- **项目概述**：[PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md) - 项目愿景和发展路线图

---

🕷️ **Bald Spider** - 让网络爬取变得简单而强大
