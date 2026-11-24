# Bald Spider 架构文档

## 数据流

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
   Processor 队列 ──► 新 Request 重新入队 / Item 计数与处理
```

## 核心组件

- `crawler.Crawler` / `CrawlerProcess`：装配与生命周期，创建 subscriber、spider、engine、stats，并处理 SIGINT。
- `core.engine.Engine`：主循环。取请求、并发执行（TaskManager 信号量限流）、解析回调输出、判断退出条件、关闭资源。
- `core.scheduler.Scheduler`：优先级队列与周期性统计日志。
- `core.processor.Processor`：消费回调产物，Request 重新入队，Item 计数。
- `core.downloader`：`DownloaderBase` 定义接口，`AioDownloader` / `HTTPXDownloader` 为具体实现。
- `middleware`：`MiddlewareManager` 串联 process_request / process_response / process_exception；内置默认请求头、下载延迟、状态码过滤、重试、异常忽略等。
- `http`：`Request`（优先级、meta、callback）与 `Response`（text / xpath / json / urljoin）。
- `items`：基于 `ItemMeta` 的字段声明式容器，支持继承。
- `settings`：默认配置 + 项目配置 + 爬虫 `custom_settings` 三层合并。
- `subscriber` / `event`：事件订阅（spider_opened / spider_closed / spider_error 等）。

## 并发与退出

- `TaskManager` 用 `Semaphore(CONCURRENCY)` 限制在途任务数，维护任务集合并记录未处理异常。
- `Engine` 在 `start_requests` 耗尽，且调度器、下载器、任务、处理器均空闲时退出；随后关闭下载器并触发 `spider_closed`。
- Ctrl+C 由 `CrawlerProcess` 捕获，置 `engine.running = False`；非正常关闭时仍补发 `spider_closed`。

## 已知限制

- 请求去重尚未实现（`Engine._schedule_request` 中为 TODO）。
- 数据管道、持久化与分布式能力留待后续版本。
