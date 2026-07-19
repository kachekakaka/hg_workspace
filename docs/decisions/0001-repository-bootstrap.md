# ADR 0001：以最小 Docker/FastAPI 骨架建立仓库基线

- 状态：Accepted
- 日期：2026-07-19

## 背景

GitHub `main` 在 Phase 1 开始前只有两份规划文档，旧工程源码只在其他聊天或本地压缩包中被描述。项目需要先建立一个可构建、可测试、可审计的共同基线，同时避免重新引入旧架构和复杂宿主机依赖。

## 决策

1. GitHub 文件、commit、branch、PR 和 CI 是唯一完成证据。
2. 首个实现分支使用 `phase-1/repository-bootstrap`，通过 draft PR 合入 `main`。
3. 后端基线采用 Python 3.12、FastAPI 和 Uvicorn，并通过 Docker 构建和运行。
4. Phase 1 只提供 `/health`，不提前实现作品、分集、播放、下载或 SQLite 业务模型。
5. Web 管理页后续复用原生静态页面，不为管理页引入 Node 构建链。
6. Android 后续只维护一个 Kotlin + Compose + Media3 通用 APK；Phase 1 不创建未经旧源码审计的 Android 工程。
7. 不引入 Qt/C++、`catalog.pack`、手机遥控伴侣、TV 内置 Server、mDNS、WebSocket 控制链路、Redis、Celery、PostgreSQL 或微服务。
8. 旧源码必须在重新提供后先执行 secret scan 和文件清单，再选择性迁移。

## 原因

- 先建立可重复验证的最小闭环，比一次性迁移数百兆旧目录更安全。
- Docker 把 Python 运行环境固定在项目内，符合宿主机只依赖 Docker/Git/编辑器的目标。
- 单体 FastAPI + SQLite 足以支撑第一版，不需要消息队列和微服务。
- 将旧源码迁移与仓库 bootstrap 分开，可避免把 APK、DLL、缓存、日志和凭据带入 Git 历史。

## 影响

正面影响：

- PR 可以立即运行健康检查、测试和仓库卫生检查；
- 后续后端开发有稳定入口；
- 迁移边界清晰，不会把聊天描述误写成已完成实现。

代价与待办：

- 在旧文件重新上传前，抓取逻辑、原生 Web 和 Android UI 均不可迁移；
- Android Docker builder 仍需独立 PoC；
- SQLite 数据模型、任务持久化和播放代理留到后续阶段。
