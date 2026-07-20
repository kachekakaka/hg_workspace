# HG Workspace（红果电视 APP）

HG Workspace 是一个简单、Docker 化、可审计的单仓库项目：

- Python 3.12 + FastAPI + SQLite 后端；
- FastAPI 同域托管的原生 Web 管理页，不引入 Node；
- 一个 Kotlin + Compose 手机/电视通用 Android APK；
- 反向代理、域名、TLS 和需要时的媒体代理由用户自己的 NAS 负责。

唯一代码权威源是 GitHub 仓库 `kachekakaka/hg_workspace`。只有 GitHub 文件、commit、branch、PR 和 CI 能证明工作已经完成。

## 当前能力

后端和 Web：

- 版本化 SQLite、作品/分集 API、旧 catalog 导入和持久化任务；
- 原生静态作品、统计、任务与导入页面；
- `novelquick` 公开 SSR 全量/增量发现与详情/分集 enrichment；
- provider-neutral playback 契约和短期解析缓存；
- `direct` / `external_proxy_required` 交付边界，后端不代理媒体字节。

Android：

- 单一 `android/app` module，同时支持普通 Launcher 和 Leanback Launcher；
- `leanback required=false`、`touchscreen required=false`；
- 手动保存后端或 NAS 服务地址；
- 读取 `/api/status`、`/api/works`、作品详情和分集 API；
- 手机纵向作品/分集列表；
- TV 遥控器可聚焦作品/分集网格；
- 作品详情显示简介、标签、演员、来源和集数；
- Docker 中运行 JVM 单元测试并生成 Debug APK。

生产环境目前没有注册 playback provider。Media3 播放、NAS handoff、设备端下载和真机测试尚未完成。

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

本仓库不固定公网 IP，不提供媒体 `/stream` 或 `/proxy` endpoint，也不实现 DNS pinning、HTTP Range 或视频字节转发。Android 不接收 provider Cookie、Authorization 或其他敏感请求头。

## 宿主机要求

必需：Docker（含 Compose）、Git、编辑器。可选：Android Platform-Tools 中的 `adb`。

不要求安装 Android Studio、本机 JDK、本机 Android SDK、本机 Python、Qt、MSVC、CMake 或 Node。

## 启动后端

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

## 构建 Android Debug APK

```bash
docker compose --profile build run --rm android-builder
```

Windows：

```text
scripts\build-apk.bat
```

输出：

```text
dist/hg-client-debug.apk
```

构建容器固定 JDK 17、Android SDK Platform 35、Build Tools 35.0.0 和 Gradle 8.7。APK 作为 GitHub Actions artifact 发布，不提交 Git。

可选安装：

```text
scripts\install-apk.bat
```

详细说明见 `docs/ANDROID_DEVELOPMENT.md`。

## Android 服务地址

客户端支持：

- `192.168.1.10:8000` → `http://192.168.1.10:8000`；
- `https://nas.example/hg` 这类 NAS 路径前缀；
- HTTP 仅允许 localhost、局域网单标签主机、`.local`、私网 IPv4 和本地 IPv6；
- 公网域名必须使用 HTTPS；
- 不允许 URL 用户名/密码、query、fragment 或上级目录路径。

地址保存在应用私有 SharedPreferences。Manifest 暂时允许 cleartext 以支持局域网 Debug；URL 校验阻止公网明文 HTTP，Release 网络安全策略后续收紧。

## Android 浏览流程

```text
配置服务地址
→ 加载作品列表
→ 打开作品详情
→ 加载 /api/v1/works/{work_id}
→ 加载 /api/v1/works/{work_id}/episodes
→ 手机列表或 TV 焦点网格选择分集
```

点击分集目前只显示稳定身份、集序和可选时长，不显示虚假的播放或下载按钮。

## Playback 解析契约

```text
POST   /api/v1/episodes/{episode_id}/playback/resolve
GET    /api/v1/episodes/{episode_id}/playback
DELETE /api/v1/episodes/{episode_id}/playback
GET    /api/v1/playback/providers
```

- `direct`：HTTPS、无 provider headers、provider 明确允许，返回短期 URL；
- `external_proxy_required`：存在 provider headers，不返回来源 URL 或 headers，等待 NAS 对接；
- provider 未配置返回 HTTP 503，非法或失败的 provider 返回脱敏 HTTP 502；
- 来源 URL 和 headers 只保存在后端短期 SQLite 记录中，过期后不再可读。

## 测试

后端：

```bash
docker compose --profile test build backend-test
docker compose --profile test run --rm backend-test
```

Android：

```bash
docker compose --profile build run --rm android-builder
```

CI 运行仓库卫生、明显 secret、Python 编译、Compose 配置、后端 test/runtime images、容器健康检查、Android JVM 测试和 Debug APK 构建。内容源测试使用合成 fixture，不在 CI 中访问第三方网络。

## 后续顺序

1. 增加 Android playback `direct` / `external_proxy_required` 客户端模型；
2. 在授权边界明确后实现首个生产 playback provider；
3. 与 NAS 定义最小、可审计的外部代理 handoff；
4. 使用 Media3 完成在线播放；
5. 实现设备端下载和离线播放；
6. 完成 Android 14、Android TV/盒子和华为 S65 兼容验证。

项目只处理有权访问、保存、播放和下载的内容，不绕过 DRM、付费、登录或其他访问控制，也不恢复 Qt/C++、`catalog.pack`、手机伴侣、TV 内置服务器、mDNS 或 WebSocket 控制链路。
