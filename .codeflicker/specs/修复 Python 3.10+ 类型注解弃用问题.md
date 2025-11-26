# 修复 Python 3.10+ 类型注解弃用问题

## 概述
将项目中的弃用类型注解 `Optional` 和 `Generator` 替换为 Python 3.11+ 推荐的新语法。

## 修改内容

### 1. `bald_spider/core/engine.py`
- **第4行**：将 `from typing import Optional, Generator, Callable` 
  改为 `from collections.abc import Generator; from typing import Callable`
- **第19行**：将 `self.downloader: Optional[Downloader] = None`
  改为 `self.downloader: Downloader | None = None`
- **第20行**：将 `self.start_requests: Optional[Generator] = None`
  改为 `self.start_requests: Generator | None = None`
- **第21-23行**：类似地将其他 `Optional[X]` 改为 `X | None`

### 2. `bald_spider/http/request.py`
- **第1行**：将 `from typing import Dict, Optional, Callable`
  改为 `from typing import Dict, Callable`
- **第9行**：将 `headers: Optional[Dict] = None`
  改为 `headers: Dict | None = None`
- **第10行**：将 `callback: Optional[Callable] = None`
  改为 `callback: Callable | None = None`
- **第13-14行**：类似地修改其他 `Optional[Dict]` 为 `Dict | None`

### 3. `bald_spider/core/scheduler.py`
- **第1行**：将 `from typing import Optional`
  改为 `from collections.abc import Generator`（如果需要 Generator）或删除（如果不需要）
- **第7行**：将 `self.request_queue: Optional[SpoderPriorityQueue] = None`
  改为 `self.request_queue: SpoderPriorityQueue | None = None`

## 技术细节
- 使用 `X | None` 语法替代 `Optional[X]`（Python 3.10+ 特性）
- 使用 `collections.abc.Generator` 替代 `typing.Generator`
- 保持代码功能不变，仅更新类型注解语法
- 确保与 Python 3.11+ 兼容

## 验证
- 运行类型检查（如果有 mypy 等工具）
- 运行现有测试确保功能正常
- 检查代码格式（black 已配置）