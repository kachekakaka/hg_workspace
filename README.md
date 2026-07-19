# HG Workspace（红果电视 APP）

HG Workspace 正在重构为一个简单、可审计的单仓库项目：

- Python 3.12 + FastAPI + SQLite 后端；
- 后端托管的原生 Web 管理页面（后续迁移，不引入 Node）；
- 一个 Kotlin + Compose + Media3 通用 APK（后续阶段）。

## 代码权威源

唯一代码权威源是 GitHub 仓库 `kachekakaka/hg_workspace`。只有 GitHub 文件、commit、branch、PR 和 CI 能证明工作已完成；聊天、本地压缩包和旧 APK 只可作为迁移输入。

## 当前进度

已合入的基础：

- PR #1：Docker/FastAPI 基线、仓库卫生检查、旧工程审计和纯解析逻辑；
- PR #2：版本化 SQLite、作品/分集 repository、正式 API 和旧 Web 只读兼容 API。

当前批次增加：

- 旧 `catalog.json` / checkpoint JSON 到 `WorkImport` 的纯映射；
- 声明集数导入，同时保留“实际分集快照优先”的语义；
- SQLite 持久化任务队列；
- 单进程、单线程任务 worker；
- 服务重启时把遗留 `running` 任务标记为 `interrupted`；
- 失败或中断任务重试；
- 正式与旧 Web 兼容的任务查询和 catalog 导入 API。

本批次不会访问第三方网络，不迁移 Cookie/Authorization，也不实现抓取、播放、代理或下载。

## 宿主机要求

必需：

- Docker（含 Docker Compose）；
- Git；
- VS Code/Cursor 或其他编辑器。

可选：`adb`，用于后续真机安装和调试。

不要求安装 Android Studio、本机 JDK、本机 Android SDK、本机 Python、Qt、MSVC、CMake 或 Node。

## 启动后端

```bash
docker compose up --build backend
```

健康检查：

```bash
curl --fail http://localhost:8000/health
```

预期响应：

```json
{"status":"ok","service":"hg-backend"}
```

SQLite 默认保存在 Docker volume 的 `/data/hg.db`。任务 worker 默认启用：

```text
HG_DATABASE=/data/hg.db
HG_TASK_WORKER_ENABLED=true
HG_TASK_POLL_INTERVAL=0.5
```

## 导入单部作品

`POST /api/v1/works/import` 接受标准化作品和可选分集快照：

```bash
curl --fail --request POST http://localhost:8000/api/v1/works/import \
  --header 'Content-Type: application/json' \
  --data '{
    "source": "manual",
    "source_work_id": "demo-001",
    "series_name": "测试作品",
    "episode_count": 12
  }'
```

导入规则：

- `(source, source_work_id)` 唯一，重复提交更新同一作品；
- 缺省 `episodes` 时保留现有分集；
- 此时可用 `episode_count` 保存来源声明的总集数；
- 提供 `episodes` 数组时，该数组是权威快照，实际数组长度覆盖声明集数；
- 空 `episodes` 数组清空该作品分集；
- 播放 URL 不作为永久作品数据保存。

## 异步导入旧 catalog

下列命令只解析本地 JSON 请求体，不会触发网络抓取：

```bash
curl --fail --request POST \
  'http://localhost:8000/api/v1/imports/catalog?source=novelquick' \
  --header 'Content-Type: application/json' \
  --data-binary @catalog.json
```

接口返回 HTTP 202 和任务 ID。查询任务：

```bash
curl --fail http://localhost:8000/api/v1/tasks/<task-id>
```

支持的旧 catalog 根结构：

- 作品数组；
- `{ "works": [...] }`；
- `{ "works": { "series-id": {...} } }` checkpoint 映射。

旧记录中的 `source` 往往是发现路径，不作为稳定来源键。调用方通过 `source` 查询参数指定稳定适配器名，默认是 `novelquick`。

## 当前 API

正式 API：

```text
POST /api/v1/works/import
POST /api/v1/imports/catalog
GET  /api/v1/works
GET  /api/v1/works/{id}
GET  /api/v1/works/{id}/episodes
GET  /api/v1/stats
GET  /api/v1/tasks
GET  /api/v1/tasks/{id}
POST /api/v1/tasks/{id}/retry
```

旧 Web 兼容 API：

```text
GET  /api/works
GET  /api/works/{series_id}
POST /api/works/import
GET  /api/stats
GET  /api/status
GET  /api/tasks
GET  /api/tasks/{task_id}
```

交互式 OpenAPI：`http://localhost:8000/docs`。

## 任务语义

```text
API 写入 pending
→ worker 原子领取为 running
→ 持续写入 progress/message
→ completed 或 failed
```

进程重启时，旧的 `running` 任务转为 `interrupted`，可通过 retry API 重新排队。catalog 导入按作品幂等写入；若进程在批次中途停止，重试不会重复创建已导入作品。

## 运行测试

```bash
docker compose --profile test build backend-test
docker compose --profile test run --rm backend-test
```

GitHub Actions 还会运行仓库卫生、明显 secret、Python 编译、Compose 配置、Docker 构建和容器健康检查。

## 当前目录

```text
.
├── backend/
│   ├── app/api/               # FastAPI 路由
│   ├── app/migrations/        # 版本化 SQLite SQL
│   ├── app/repositories/      # catalog 与 task repositories
│   ├── app/services/          # 纯映射、任务 worker 与其他服务逻辑
│   ├── app/sources/           # 内容源纯解析器
│   └── tests/                 # fixture 驱动测试
├── docs/                      # 架构、审计、计划和 ADR
├── scripts/                   # 仓库级检查
├── .github/workflows/ci.yml
└── compose.yaml
```

## 后续顺序

1. 把全量/增量抓取改为内容源适配器输出 `WorkImport`，不再维护 checkpoint 主库；
2. 实现抓取任务类型及旧 Web 的 full/incremental 触发端点；
3. 迁移原生静态 Web；
4. 为有权访问的内容实现 playback direct/proxy/cache；
5. 建立 Docker 化 Android 通用 APK；
6. 实现单集下载、离线播放和设备验证。
