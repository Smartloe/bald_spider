# Bald Spider 开发指南

## 🛠️ 开发环境设置

### 安装依赖

```bash
# 使用 uv（推荐）
uv sync

# 或使用 pip
pip install -e ".[dev]"
```

### 开发工具

- **uv** - 现代 Python 包管理器
- **pytest** - 测试框架
- **black** - 代码格式化
- **mypy** - 类型检查（可选）

## 📝 编码规范

### Python 版本要求
- 最低版本：Python 3.11
- 推荐使用最新稳定版本

### 类型注解
所有公共接口都必须包含类型注解：

```python
from typing import Optional, Generator, Callable, Dict, Any

def example_function(
    url: str, 
    headers: Optional[Dict[str, str]] = None,
    callback: Optional[Callable[[str], Any]] = None
) -> Generator[Request, None, None]:
    pass
```

### 异步编程
- 所有 I/O 操作必须使用异步方式
- 避免在异步代码中使用同步阻塞调用
- 正确处理异常和超时

```python
async def fetch_data(url: str) -> str:
    try:
        # 使用异步 HTTP 客户端
        response = await http_client.get(url, timeout=30)
        return response.text
    except asyncio.TimeoutError:
        logger.warning(f"Request timeout for {url}")
        raise
```

### 错误处理
- 使用自定义异常类
- 提供详细的错误信息
- 实现优雅的降级处理

```python
class SpiderError(Exception):
    """基础爬虫异常类"""
    pass

class RequestError(SpiderError):
    """请求异常"""
    def __init__(self, message: str, request: Request):
        super().__init__(message)
        self.request = request
```

## 🧪 测试指南

### 测试结构

```
tests/
├── unit/           # 单元测试
├── integration/    # 集成测试
├── fixtures/       # 测试数据
└── examples/       # 示例代码测试
```

### 编写测试

```python
import pytest
import asyncio
from bald_spider.core.engine import Engine
from bald_spider.spider import Spider
from bald_spider.http.request import Request


class TestEngine:
    @pytest.mark.asyncio
    async def test_engine_start_stop(self):
        """测试引擎启动和停止"""
        engine = Engine()
        spider = Spider()
        
        # 测试启动
        await engine.start_spider(spider)
        assert engine.running is True
        
        # 测试停止
        await engine.stop()
        assert engine.running is False

    @pytest.mark.asyncio
    async def test_request_processing(self):
        """测试请求处理"""
        # 测试代码
        pass
```

### 运行测试

```bash
# 运行所有测试
uv run pytest

# 运行特定测试文件
uv run pytest tests/test_engine.py

# 运行带覆盖率的测试
uv run pytest --cov=bald_spider

# 运行性能测试
uv run pytest tests/performance/ -v
```

## 🔧 调试技巧

### 日志配置

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### 调试异步代码

```python
import asyncio
import sys

# 启用 asyncio 调试模式
asyncio.get_event_loop().set_debug(True)

# 使用 uvloop 提升性能（可选）
if sys.platform != 'win32':
    import uvloop
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
```

### 性能分析

```python
import cProfile
import pstats

async def profile_crawl():
    profiler = cProfile.Profile()
    profiler.enable()
    
    # 运行爬虫
    await run_spider()
    
    profiler.disable()
    
    # 保存分析结果
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(20)
```

## 🚀 扩展开发

### 自定义中间件

```python
class CustomMiddleware:
    async def process_request(self, request: Request, spider: Spider) -> Optional[Request]:
        """处理请求"""
        # 添加自定义逻辑
        request.headers['User-Agent'] = 'CustomBot/1.0'
        return request
    
    async def process_response(self, request: Request, response: str, spider: Spider) -> str:
        """处理响应"""
        # 添加自定义逻辑
        return response
    
    async def process_exception(self, request: Request, exception: Exception, spider: Spider):
        """处理异常"""
        # 添加自定义逻辑
        logger.error(f"Exception in {request.url}: {exception}")
        return None
```

### 自定义调度器

```python
class CustomScheduler(Scheduler):
    def __init__(self):
        super().__init__()
        self.custom_queue = []
    
    async def enqueue_request(self, request: Request):
        """自定义请求入队逻辑"""
        # 添加自定义逻辑
        await super().enqueue_request(request)
    
    async def next_request(self) -> Optional[Request]:
        """自定义请求出队逻辑"""
        # 添加自定义逻辑
        return await super().next_request()
```

### 自定义下载器

```python
class CustomDownloader(Downloader):
    async def download(self, request: Request) -> str:
        """自定义下载逻辑"""
        # 使用真实的 HTTP 客户端
        async with httpx.AsyncClient() as client:
            response = await client.get(
                request.url,
                headers=request.headers,
                timeout=30
            )
            return response.text
```

## 📋 代码审查清单

### 功能性
- [ ] 代码实现了预期功能
- [ ] 处理了边界情况
- [ ] 有适当的错误处理
- [ ] 性能表现良好

### 代码质量
- [ ] 遵循 PEP 8 规范
- [ ] 包含完整的类型注解
- [ ] 有适当的注释和文档
- [ ] 代码简洁易懂

### 测试
- [ ] 包含单元测试
- [ ] 测试覆盖了主要功能
- [ ] 测试通过了所有检查
- [ ] 包含集成测试

### 安全性
- [ ] 没有硬编码的敏感信息
- [ ] 正确处理用户输入
- [ ] 遵循安全最佳实践

## 🔄 提交和发布

### 提交信息规范

```
feat: 添加新功能
fix: 修复 bug
docs: 更新文档
style: 代码格式调整
refactor: 重构代码
test: 添加测试
chore: 构建过程或辅助工具的变动
```

### 版本发布

1. 更新 `pyproject.toml` 中的版本号
2. 更新 `CHANGELOG.md`
3. 创建 git tag
4. 构建和发布包

```bash
# 构建包
uv build

# 发布到 PyPI
uv publish
```