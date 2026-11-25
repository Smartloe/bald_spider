# Bald Spider 技术栈与偏好

## 🛠️ 核心技术栈

### Python 生态系统
- **Python 3.11+** - 利用最新的语言特性
- **asyncio** - 异步编程基础
- **typing** - 类型注解支持
- **uv** - 现代包管理器

### 异步编程
```python
# 推荐：使用 async/await
async def fetch_data(url: str) -> str:
    await asyncio.sleep(0.1)  # 模拟异步操作
    return "data"

# 避免：同步阻塞调用
def fetch_data_sync(url: str) -> str:
    time.sleep(0.1)  # 阻塞操作
    return "data"
```

### 包管理
```toml
# pyproject.toml
[project]
name = "bald-spider"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "aiohttp>=3.13.2",
    "httpx>=0.28.1",
    "parsel>=1.10.0",
    "requests>=2.32.5",
    "ujson>=5.11.0",
]

[project.optional-dependencies]
dev = [
    "black>=25.9.0",
    "pytest>=8.4.2",
]
```

## 🎯 设计原则

### 1. 异步优先
- 所有 I/O 操作必须异步
- 避免阻塞主线程
- 使用生成器模式处理数据流

### 2. 类型安全
- 强制类型注解
- 使用类型检查工具
- 运行时类型验证

### 3. 错误处理
- 优雅的异常处理
- 任务级别的错误隔离
- 可配置的重试机制

### 4. 可扩展性
- 模块化设计
- 中间件机制与可替换组件
- 接口抽象清晰

## 📊 性能优化

### 并发控制
```python
# 使用信号量控制并发
semaphore = asyncio.Semaphore(16)

async def limited_task():
    async with semaphore:
        # 执行任务
        pass
```

### 内存管理
```python
# 使用生成器避免大量数据加载
def generate_requests(urls):
    for url in urls:
        yield Request(url)

# 及时清理资源
async def cleanup():
    if hasattr(self, '_resource'):
        await self._resource.close()
        del self._resource
```

### 网络优化
```python
# aiohttp / httpx 下载器均支持连接复用（USE_SESSION=True）
async def create_client():
    return httpx.AsyncClient(
        limits=httpx.Limits(
            max_connections=100,
            max_keepalive_connections=20
        )
    )
```

## 🧪 测试策略

### 单元测试
```python
def test_request_creation():
    request = Request(url="https://example.com")
    assert request.url == "https://example.com"
```

### 集成测试
```python
import asyncio

from bald_spider.crawler import Crawler
from bald_spider.settings.settings_manager import SettingsManager


def test_spider_integration():
    settings = SettingsManager({"LOG_LEVEL": "CRITICAL"})
    crawler = Crawler(TestSpider, settings)
    asyncio.run(asyncio.wait_for(crawler.crawl(), timeout=10))
    # 验证结果
```

### 性能测试
```python
async def benchmark_crawl():
    start_time = time.time()
    # 运行爬虫
    await run_spider()
    duration = time.time() - start_time
    assert duration < 60  # 应在60秒内完成
```

## 🔧 开发工具

### 代码格式化
```bash
# 使用 black 格式化代码
uv run black .

# 检查格式
uv run black --check .
```

### 类型检查
```bash
# 使用 mypy 检查类型
mypy bald_spider/
```

### 测试运行
```bash
# 运行测试
uv run pytest

# 详细输出
uv run pytest -v
```

## 📋 代码规范

### 命名约定
```python
# 类名使用 PascalCase
class SpiderEngine:
    pass

# 函数和变量使用 snake_case
def start_spider():
    pass

# 常量使用 UPPER_SNAKE_CASE
MAX_CONCURRENCY = 16
```

### 导入顺序
```python
# 标准库
import asyncio
import time
from typing import Optional, Generator

# 第三方库
import requests

# 本地模块
from bald_spider.http.request import Request
from bald_spider.spider import Spider
```

### 文档字符串
```python
async def fetch_data(url: str) -> str:
    """
    异步获取网页数据
    
    Args:
        url: 目标网页URL
        
    Returns:
        网页内容字符串
        
    Raises:
        RequestError: 当请求失败时
        TimeoutError: 当请求超时时
    """
    pass
```

## 🚀 性能监控

### 指标收集
```python
class Metrics:
    def __init__(self):
        self.requests_count = 0
        self.errors_count = 0
        self.start_time = time.time()
    
    def increment_requests(self):
        self.requests_count += 1
    
    def increment_errors(self):
        self.errors_count += 1
    
    @property
    def requests_per_second(self):
        elapsed = time.time() - self.start_time
        return self.requests_count / elapsed if elapsed > 0 else 0
```

### 日志配置
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('spider.log'),
        logging.StreamHandler()
    ]
)
```

## 🔒 安全考虑

### 请求安全
```python
# 验证URL格式
def validate_url(url: str) -> bool:
    try:
        result = urllib.parse.urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False

# 限制请求频率
class RateLimiter:
    def __init__(self, max_requests: int, window: int):
        self.max_requests = max_requests
        self.window = window
        self.requests = []
    
    async def acquire(self):
        now = time.time()
        # 清理过期记录
        self.requests = [r for r in self.requests if now - r < self.window]
        
        if len(self.requests) >= self.max_requests:
            await asyncio.sleep(self.window)
        
        self.requests.append(now)
```

### 数据验证
```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class SafeItem:
    title: str
    url: str
    content: Optional[str] = None
    
    def __post_init__(self):
        if not self.title or len(self.title) > 1000:
            raise ValueError("Title is required and must be under 1000 characters")
        
        if not validate_url(self.url):
            raise ValueError("Invalid URL format")
```

## 📈 未来规划

### 短期目标
- [x] 集成真实 HTTP 客户端（httpx/aiohttp）
- [ ] 实现请求去重机制
- [x] 添加中间件系统
- [x] 完善错误处理和重试机制

### 中期目标
- [ ] 实现数据管道系统
- [ ] 添加分布式支持
- [ ] 实现持久化存储
- [ ] 完善监控和日志系统

### 长期目标
- [ ] 支持 JavaScript 渲染页面
- [ ] 实现智能反爬虫策略
- [ ] 提供 Web 管理界面
- [ ] 构建插件生态系统