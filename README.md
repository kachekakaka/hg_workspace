# HG Workspace（红果电视 APP）

HG Workspace 正在重构为一个简单、可审计的单仓库项目：

- Python 3.12 + FastAPI + SQLite 后端；
- 后端同域托管的原生 Web 管理页面，不引入 Node；
- 一个 Kotlin + Compose + Media3 通用 APK（后续阶段）。

## 代码权威源

唯一代码权威源是 GitHub 仓库 `kachekakaka/hg_workspace`。只有 GitHub 文件、commit、branch、PR 和 CI 能证明工作已完成；聊天、本地压缩包和旧 APK 只可作为迁移输入。

## 当前进度

已经建立：

- Docker/FastAPI 基线、仓库卫生和 secret 检查；
- 版本化 SQLite、作品/分集 repository 和 API；
- 旧 catalog 纯映射、持久化任务、retry 和启动恢复；
- 原生静态作品、统计、任务与导入管理页；
- `novelquick` 公开 SSR 作品元数据适配器；
- 全量/增量发现任务和 Web 触发入口；
- 公开详情页 enrichment 任务，将分集标识和集序写入 SQLite。

仍未实现 Cookie/Authorization 播放解析、playback direct/proxy/cache、HTTP Range、媒体下载、Android APK 和真机测试。

## 宿主机要求

必需：Docker（含 Compose）、Git、编辑器。可选 `adb`。不要求安装 Android Studio、本机 JDK、本机 Android SDK、本机 Python、Qt、MSVC、CMake 或 Node。

## 启动

```bash
docker compose up --build backend
```

```text
管理页：http://localhost:8000/
任务页：http://localhost:8000/tasks.html
API 文档：http://localhost:8000/docs
```

健康检查：

```bash
curl --fail http://localhost:8000/health
```

## 配置

```text
HG_DATABASE=/data/hg.db
HG_TASK_WORKER_ENABLED=true
HG_TASK_POLL_INTERVAL=0.5
HG_SOURCE_TIMEOUT=20
HG_SOURCE_RETRIES=3
HG_SOURCE_DELAY=0.15
```

`HG_SOURCE_*` 只控制公开元数据请求的超时、重试和请求间隔。适配器固定使用 HTTPS 来源，不发送 Cookie 或 Authorization，并限制单响应大小和分类任务数量。

## Web 管理页面

- `/`：作品分页、搜索、状态/标签过滤、详情、已入库分集和“刷新公开详情与分集”任务；
- `/stats.html`：作品统计和服务状态；
- `/tasks.html`：增量/全量公开元数据发现、本地 catalog JSON 导入、任务历史、进度、结果和 retry。

播放入口在 playback API 完成前不会显示。

## 全量与增量发现

增量任务：

```bash
curl --fail --request POST \
  'http://localhost:8000/api/v1/tasks/scrape/incremental?source=novelquick'
```

全量任务：

```bash
curl --fail --request POST \
  'http://localhost:8000/api/v1/tasks/scrape/full?source=novelquick'
```

两者都返回 HTTP 202 和持久化任务 ID。查询：

```bash
curl --fail http://localhost:8000/api/v1/tasks/<task-id>
```

语义：

- 增量发现读取首页、分类默认列表、最近时间筛选和最新排序；
- 全量发现遍历官网 SSR 暴露的受支持分类筛选；
- 发现结果直接转换成 `WorkImport` 并幂等写入 SQLite，不再写 checkpoint 主库；
- 同一时间只允许一个 full/incremental 抓取任务；
- 进程重启时 `running` 任务变为 `interrupted`，可 retry；
- 本批次只保存作品元数据，不保存或解析播放地址。

## 刷新公开详情与分集

已入库作品可以创建持久化 enrichment 任务：

```bash
curl --fail --request POST \
  http://localhost:8000/api/v1/works/<work-id>/enrich
```

兼容旧 Web 的入口：

```text
POST /api/works/{series_id}/enrich
```

该任务读取公开 SSR `seriesDetail`，更新名称、封面、简介、标签等元数据，并把非空 `vid_list` 规范化为分集标识和集序。它不请求 player 页面，也不保存播放 URL。来源暂时返回空或不可用 `vid_list` 时，现有分集不会被清空。

## 安全与内容边界

内容源功能只适用于有权访问和保存的公开作品元数据。当前实现：

- 不发送 Cookie、Authorization 或用户凭据；
- 不解析或代理播放 URL；
- 不绕过 DRM、付费、登录或其他访问控制；
- 不恢复 Qt/C++、`catalog.pack`、手机伴侣、TV 内置服务器、mDNS 或 WebSocket 控制链路。

## 旧 catalog 导入

```bash
curl --fail --request POST \
  'http://localhost:8000/api/v1/imports/catalog?source=novelquick' \
  --header 'Content-Type: application/json' \
  --data-binary @catalog.json
```

支持作品数组、`{"works": [...]}` 和 `{"works": {"series-id": {...}}}`。浏览器管理页限制 20 MiB；服务端不会根据文件输入框路径读取任意宿主机文件。

## 当前 API

```text
POST /api/v1/works/import
POST /api/v1/works/{id}/enrich
POST /api/v1/imports/catalog
POST /api/v1/tasks/scrape/full
POST /api/v1/tasks/scrape/incremental
GET  /api/v1/works
GET  /api/v1/works/{id}
GET  /api/v1/works/{id}/episodes
GET  /api/v1/stats
GET  /api/v1/tasks
GET  /api/v1/tasks/{id}
POST /api/v1/tasks/{id}/retry
```

兼容入口：

```text
POST /api/tasks/scrape/full
POST /api/tasks/scrape/incremental
POST /api/works/import
POST /api/works/{series_id}/enrich
GET  /api/works
GET  /api/works/{series_id}
GET  /api/stats
GET  /api/status
GET  /api/tasks
GET  /api/tasks/{task_id}
```

## 测试

```bash
docker compose --profile test build backend-test
docker compose --profile test run --rm backend-test
```

CI 还运行仓库卫生、明显 secret、Python 编译、Compose 配置、Docker test/runtime image 和容器健康检查。内容源测试全部使用合成 SSR fixture，不在 CI 中访问第三方网络。

## 后续顺序

1. 为有权访问的内容建立 playback provider 接口和短期解析结果；
2. 实现 direct/proxy/cache、HTTP Range 和日志脱敏；
3. 实现服务端媒体缓存与下载任务；
4. 建立 Docker 化 Kotlin + Compose + Media3 通用 APK；
5. 实现在线播放、单集下载、离线播放和手机/电视/华为 S65 验证。
