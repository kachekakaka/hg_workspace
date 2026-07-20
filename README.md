# HG Workspace（红果电视 APP）

HG Workspace 正在重构为一个简单、Docker 化、可审计的单仓库项目：

- Python 3.12 + FastAPI + SQLite 后端；
- FastAPI 同域托管的原生 Web 管理页，不引入 Node；
- 一个 Kotlin + Compose + Media3 手机/电视通用 APK；
- 反向代理、域名、TLS 和需要时的媒体代理由用户的 NAS 负责。

唯一代码权威源是 GitHub 仓库 `kachekakaka/hg_workspace`。只有 GitHub 文件、commit、branch、PR 和 CI 能证明工作已经完成。

## 当前能力

已经合入：

- Docker/FastAPI 基线、仓库卫生和 secret 检查；
- 版本化 SQLite、作品/分集 API、旧 catalog 导入和持久化任务；
- 原生静态作品、统计、任务与导入页面；
- `novelquick` 公开 SSR 全量/增量发现与详情/分集 enrichment；
- provider-neutral playback 契约和短期解析缓存。

生产环境目前没有注册 playback provider，因此不会返回真实播放地址。Android 工程、NAS 对接协议、设备端下载和真机测试尚未完成。

## 部署边界

```text
内容源适配器
    │ 公开元数据 / 已授权播放解析
    ▼
HG FastAPI 后端
    ├── 作品、分集、任务和配置
    ├── 短期 playback resolution
    ├── direct：返回短期 HTTPS URL
    └── external_proxy_required：不返回来源 URL 或请求头
                    │
                    ▼
             用户自己的 NAS
       反向代理 / 域名 / TLS / 媒体代理
                    │
                    ▼
       Android 手机 / Android TV / 智慧屏
```

本仓库不固定公网 IP，不提供媒体 `/stream` 或 `/proxy` endpoint，也不实现 DNS pinning、HTTP Range 或视频字节转发。`external_proxy_required` 只表示候选不能由客户端直接消费；它在 NAS 对接协议完成前不是可播放 URL。Android 不接收 provider Cookie、Authorization 或其他敏感请求头。

## 启动

宿主机只需要 Docker、Git、编辑器和可选 `adb`，不要求 Android Studio、本机 JDK/SDK、本机 Python、Qt、MSVC、CMake 或 Node。

```bash
docker compose up --build backend
```

```text
管理页：http://localhost:8000/
任务页：http://localhost:8000/tasks.html
API 文档：http://localhost:8000/docs
```

```bash
curl --fail http://localhost:8000/health
```

主要配置：

```text
HG_DATABASE=/data/hg.db
HG_TASK_WORKER_ENABLED=true
HG_TASK_POLL_INTERVAL=0.5
HG_SOURCE_TIMEOUT=20
HG_SOURCE_RETRIES=3
HG_SOURCE_DELAY=0.15
HG_PLAYBACK_MAX_TTL=21600
```

## 当前 API

作品和任务：

```text
POST /api/v1/works/import
POST /api/v1/works/{id}/enrich
POST /api/v1/imports/catalog
POST /api/v1/tasks/scrape/full
POST /api/v1/tasks/scrape/incremental
GET  /api/v1/works
GET  /api/v1/works/{id}
GET  /api/v1/works/{id}/episodes
GET  /api/v1/tasks
GET  /api/v1/tasks/{id}
POST /api/v1/tasks/{id}/retry
```

Playback 契约：

```text
POST   /api/v1/episodes/{episode_id}/playback/resolve
GET    /api/v1/episodes/{episode_id}/playback
DELETE /api/v1/episodes/{episode_id}/playback
GET    /api/v1/playback/providers
```

交付规则：

- `direct`：HTTPS、无 provider headers、provider 明确允许，返回短期 URL；
- `external_proxy_required`：存在 provider headers，不返回来源 URL 或 headers，等待 NAS 对接；
- provider 未配置返回 HTTP 503，非法或失败的 provider 返回脱敏 HTTP 502；
- 来源 URL 和 headers 只保存在后端短期 SQLite 记录中，过期后不再可读。

## 测试

```bash
docker compose --profile test build backend-test
docker compose --profile test run --rm backend-test
```

CI 还运行仓库卫生、明显 secret、Python 编译、Compose 配置、Docker test/runtime image 和容器健康检查。内容源测试使用合成 fixture，不在 CI 中访问第三方网络。

## 后续顺序

1. 建立 Docker 化 Kotlin + Compose 通用 Android 工程和 API 客户端；
2. 完成手机/TV 共用的服务地址、作品、详情和分集浏览；
3. 在授权边界明确后实现首个生产 playback provider；
4. 与 NAS 定义最小、可审计的外部代理对接协议；
5. 使用 Media3 完成在线播放、设备端下载和离线播放；
6. 完成 Android 14、Android TV/盒子和华为 S65 兼容验证。

项目只处理有权访问、保存、播放和下载的内容，不绕过 DRM、付费、登录或其他访问控制，也不恢复 Qt/C++、`catalog.pack`、手机伴侣、TV 内置服务器、mDNS 或 WebSocket 控制链路。
