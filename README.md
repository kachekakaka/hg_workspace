# HG Workspace（红果电视 APP）

HG Workspace 正在重构为一个简单、可审计的单仓库项目：

- Python 3.12 + FastAPI + SQLite 后端；
- 后端托管的原生 Web 管理页面（后续迁移，不引入 Node）；
- 一个 Kotlin + Compose + Media3 通用 APK（后续阶段）。

## 代码权威源

唯一代码权威源是 GitHub 仓库 `kachekakaka/hg_workspace`。只有 GitHub 文件、commit、branch、PR 和 CI 能证明工作已完成；聊天、本地压缩包和旧 APK 只可作为迁移输入。

## 当前进度

Phase 1 已通过 PR #1 合入 `main`，建立了 Docker/FastAPI 基线、仓库卫生检查、旧工程审计和两组纯解析逻辑。

`phase-2/backend-foundation` 增加首个持久化作品目录闭环：

- 直接使用 Python `sqlite3`，不引入 SQLAlchemy 或 Alembic；
- 使用 `backend/app/migrations/NNNN_*.sql` 管理版本化 SQL；
- 建立 `works`、`episodes`、`media_cache`、`tasks`、`settings` 表；
- 幂等导入一部作品及其分集；
- 分页、搜索、状态和标签过滤；
- 作品详情与分集读取；
- 为旧原生 Web 提供作品、详情、统计和状态的只读兼容接口；
- 使用合成 fixture 测试，不进行外部网络抓取。

尚未接入全量/增量抓取、Cookie/Authorization、播放解析、Range 代理、下载任务、Web 静态页面和 Android 客户端。

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

SQLite 默认保存在 Docker volume 的 `/data/hg.db`。可通过 `.env` 覆盖：

```text
HG_DATABASE=/data/hg.db
HG_BACKEND_PORT=8000
```

## 导入合成作品

`POST /api/v1/works/import` 接受作品和可选分集快照：

```bash
curl --fail --request POST http://localhost:8000/api/v1/works/import \
  --header 'Content-Type: application/json' \
  --data '{
    "source": "manual",
    "source_work_id": "demo-001",
    "series_name": "测试作品",
    "tags": ["测试"],
    "episodes": [
      {
        "source_episode_id": "demo-001-ep-1",
        "episode_index": 1,
        "title": "第一集"
      }
    ]
  }'
```

导入规则：

- `(source, source_work_id)` 唯一，重复提交会更新同一作品；
- 缺省 `episodes` 表示只更新作品元数据并保留现有分集；
- 提供 `episodes` 数组时，该数组是权威快照；空数组会清空该作品分集；
- 播放 URL 不作为永久作品数据保存。

## 当前 API

新版 API：

```text
POST /api/v1/works/import
GET  /api/v1/works?q=&status=&tag=&limit=&offset=
GET  /api/v1/works/{id}
GET  /api/v1/works/{id}/episodes
GET  /api/v1/stats
```

旧 Web 只读兼容 API：

```text
GET /api/works?q=&status=&tag=&page=&page_size=
GET /api/works/{series_id}
GET /api/stats
GET /api/status
```

交互式 OpenAPI：`http://localhost:8000/docs`。

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
│   ├── app/repositories/      # sqlite3 repository
│   ├── app/services/          # 纯服务逻辑
│   ├── app/sources/           # 内容源纯解析器
│   └── tests/                 # fixture 驱动测试
├── docs/                      # 架构、审计、计划和 ADR
├── scripts/                   # 仓库级检查
├── .github/workflows/ci.yml
└── compose.yaml
```

## 后续顺序

1. 迁移旧 catalog JSON 的纯导入映射并补 fixture；
2. 把全量/增量抓取改为写入 repository，而不是 checkpoint 主库；
3. 实现任务持久化、崩溃恢复和旧 Web 任务 API；
4. 迁移原生静态 Web；
5. 实现授权内容的播放 direct/proxy/cache；
6. 建立 Docker 化 Android 通用 APK，再实现下载和设备验证。
