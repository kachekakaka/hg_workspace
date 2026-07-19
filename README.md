# HG Workspace（红果电视 APP）

HG Workspace 正在重构为一个简单、可审计的单仓库项目：

- Python 3.12 + FastAPI + SQLite 后端；
- 后端同域托管的原生 Web 管理页面，不引入 Node；
- 一个 Kotlin + Compose + Media3 通用 APK（后续阶段）。

## 代码权威源

唯一代码权威源是 GitHub 仓库 `kachekakaka/hg_workspace`。只有 GitHub 文件、commit、branch、PR 和 CI 能证明工作已完成；聊天、本地压缩包和旧 APK 只可作为迁移输入。

## 当前进度

已合并：

- PR #1：Docker/FastAPI 基线、仓库卫生检查、旧工程审计和纯解析逻辑；
- PR #2：版本化 SQLite、作品/分集 repository、正式 API 和旧 Web 只读兼容 API；
- PR #3：旧 catalog 纯映射、SQLite 持久化任务、单线程 worker、retry 和启动恢复。

当前批次增加原生静态管理页：

- 作品分页、搜索、状态和标签过滤；
- 作品详情和已入库分集展示；
- 统计和后端状态；
- 本机 catalog JSON 导入；
- 任务历史、进度、结果和失败/中断重试；
- 手机尺寸基础响应式布局；
- 全部 HTML/CSS/JavaScript 随后端镜像部署，无 npm、Node 或外部 CDN。

尚未接入全量/增量网络抓取、Cookie/Authorization、播放解析、Range 代理、媒体缓存、下载和 Android 客户端。

## 宿主机要求

必需：

- Docker（含 Docker Compose）；
- Git；
- VS Code/Cursor 或其他编辑器。

可选：`adb`，用于后续真机安装和调试。

不要求安装 Android Studio、本机 JDK、本机 Android SDK、本机 Python、Qt、MSVC、CMake 或 Node。

## 启动后端和管理页

```bash
docker compose up --build backend
```

打开：

```text
管理页：http://localhost:8000/
API 文档：http://localhost:8000/docs
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

## Web 管理页面

### 作品库

`/` 提供：

- 作品分页；
- 剧名/简介搜索；
- 状态和标签过滤；
- 作品元数据详情；
- 已导入分集列表。

播放入口在 playback API 完成前不会显示。

### 统计

`/stats.html` 显示：

- 总作品数；
- 上架与下架数量；
- 后端版本和端口；
- 每 30 秒自动刷新。

### 任务与导入

`/tasks.html` 支持：

- 从浏览器选择本地 catalog JSON；
- 指定稳定来源名；
- 创建持久化 `catalog_import` 任务；
- 查看 pending/running/completed/failed/interrupted；
- 查看进度和导入结果；
- retry 失败或中断任务。

管理页文件限制为 20 MiB。超大 catalog 可使用 API 或拆分数据。该页面不会根据文件输入框路径让后端读取任意服务器文件。

## 导入单部标准化作品

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

规则：

- `(source, source_work_id)` 唯一，重复提交更新同一作品；
- 缺省 `episodes` 时保留现有分集；
- 此时可用 `episode_count` 保存来源声明的总集数；
- 提供 `episodes` 数组时，该数组是权威快照，实际数组长度覆盖声明集数；
- 空 `episodes` 数组清空分集；
- 播放 URL 不作为永久作品数据保存。

## 通过 API 异步导入旧 catalog

下列请求只解析 JSON 请求体，不会触发网络抓取：

```bash
curl --fail --request POST \
  'http://localhost:8000/api/v1/imports/catalog?source=novelquick' \
  --header 'Content-Type: application/json' \
  --data-binary @catalog.json
```

返回 HTTP 202 和任务 ID：

```bash
curl --fail http://localhost:8000/api/v1/tasks/<task-id>
```

支持的根结构：

- 作品数组；
- `{ "works": [...] }`；
- `{ "works": { "series-id": {...} } }` checkpoint 映射。

旧记录中的 `source` 往往是发现路径，不作为稳定来源键。调用方通过查询参数指定稳定适配器名，默认 `novelquick`。

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

## 任务语义

```text
API 写入 pending
→ worker 原子领取为 running
→ 持续写入 progress/message
→ completed 或 failed
```

进程重启时，旧 `running` 任务转为 `interrupted`，可通过 retry API 重新排队。catalog 导入按作品幂等写入；若批次中途停止，重试不会重复创建已导入作品。

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
│   ├── app/services/          # 映射、worker 与其他服务逻辑
│   ├── app/sources/           # 内容源纯解析器
│   ├── app/static/            # 原生 Web 管理页
│   └── tests/                 # fixture 和静态页面测试
├── docs/                      # 架构、审计、计划和 ADR
├── scripts/                   # 仓库级检查
├── .github/workflows/ci.yml
└── compose.yaml
```

## 后续顺序

1. 把全量/增量抓取改为内容源适配器输出 `WorkImport`，不再维护 checkpoint 主库；
2. 实现抓取任务类型及 Web 触发端点；
3. 为有权访问的内容实现 playback direct/proxy/cache；
4. 实现 HTTP Range、媒体缓存和下载任务；
5. 建立 Docker 化 Android 通用 APK；
6. 实现在线播放、单集下载、离线播放和设备验证。
