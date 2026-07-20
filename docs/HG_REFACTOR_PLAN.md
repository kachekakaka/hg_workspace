# HG Workspace 精简重构方案

## 目标

将旧 `hg_workspace` 收缩为：

- Python FastAPI 后端负责作品抓取、导入、作品/分集管理、任务和播放地址解析契约；
- 原生 Web 页面负责作品、任务和配置管理；
- 一个 Kotlin + Compose + Media3 APK 同时支持 Android 手机和电视；
- 用户 NAS 负责反向代理、域名/TLS、公网入口和需要时的媒体代理；
- Android 负责设备端播放、下载和离线播放。

## 最终架构

```text
公开元数据/授权内容源
        │
        ▼
Python FastAPI Backend
├── works / episodes / tasks / settings
├── source adapters
├── playback resolution contract
└── static Web administration
        │ HTTP API
        ▼
用户 NAS
├── 反向代理
├── TLS / 域名 / 公网入口
└── 可选媒体代理
        │
        ▼
一个 Android 通用 APK
├── Android 14 手机
├── Android TV / AOSP 盒子
└── 华为智慧屏兼容测试
```

HG 后端本身不固定公网 IP，不提供媒体 `/stream` 或 `/proxy` endpoint，不承担 HTTP Range 和视频字节转发。

## 保留

### Python

- 作品抓取和增量更新思路；
- 分集与公开详情解析；
- 播放地址解析与视频质量选择的纯逻辑；
- 原生 Web 管理页面。

### Android

- Kotlin、Compose 和 Media3；
- 作品列表、搜索、详情、分集和播放页面；
- 观看历史、收藏等少量本地状态；
- 遥控器焦点与横屏播放思路。

## 删除或停止维护

- Qt 管理工具和 C++ 中间层；
- `catalog.pack` 同步；
- 手机遥控伴侣；
- TV 内置 HTTP/WebSocket Server；
- mDNS/NSD 自动发现和二维码配对；
- WebSocket 推片；
- APK 内置完整作品库和第三方凭据；
- RTMP、SRT、WebRTC、MediaMTX；
- Redis、Celery、PostgreSQL 和微服务。

## 开发环境

宿主机只需要：

- Docker；
- Git；
- VS Code/Cursor 或其他编辑器；
- 可选 `adb`。

不要要求安装 Android Studio、本机 JDK、Android SDK、本机 Python、Qt、MSVC、CMake 或 Node。后端与 Android 构建环境尽量 Docker 化。

## 后端

技术：Python 3.12、FastAPI、Uvicorn、SQLite、Docker Compose、原生 HTML/CSS/JS。

职责：

- 作品和分集目录；
- 全量/增量公开元数据任务；
- 旧 catalog 导入；
- 持久化任务与恢复；
- provider-neutral playback resolution；
- 短期 URL/headers/expiry 安全校验与缓存；
- Web 管理页面。

不承担：

- 公网 IP 固定；
- TLS 终止；
- 媒体反向代理；
- 视频字节转发、HTTP Range 和带宽控制；
- NAS 内部配置；
- 未授权 Cookie/Authorization 获取。

Playback 交付：

```text
direct
    HTTPS、无敏感 headers，返回短期 URL

external_proxy_required
    不返回来源 URL 或 headers；等待 NAS 对接协议
```

## Android

使用一个 app module 和一个 APK：

- 普通 `LAUNCHER` + `LEANBACK_LAUNCHER`；
- `android.software.leanback required=false`；
- `android.hardware.touchscreen required=false`；
- 手机触控布局和电视遥控焦点共享数据层；
- 手动配置后端/NAS 服务地址；
- 作品、搜索、详情、分集来自 FastAPI；
- Media3 负责在线播放和设备端下载；
- Room 只保存服务地址、观看历史、收藏和本地下载索引。

## 实施阶段

### Phase 1：仓库与 Docker 基线

已完成仓库清理、忽略规则、FastAPI `/health`、测试和 CI。

### Phase 2：后端与 Web

已完成 SQLite、目录 API、任务、公开抓取、分集 enrichment、静态 Web 和 playback 契约。当前批次确认媒体代理属于外部 NAS。

### Phase 3：Android 通用客户端

- 建立 Docker Android Builder；
- 建立单一通用 Android 工程；
- 配置服务地址；
- 浏览作品、搜索、详情和分集；
- 接入 direct/NAS playback 交付模式。

### Phase 4：设备端播放与离线

- Media3 在线播放；
- 单集下载、进度、恢复、删除和离线播放；
- 手机与电视焦点/触控体验；
- Android 14、盒子和华为智慧屏测试。

## 验收标准

1. `docker compose up --build backend` 可启动后端和管理页；
2. Web 可管理作品、抓取和任务；
3. Docker 命令可构建一个 Debug APK；
4. Android 手机和电视可配置服务地址、浏览作品和分集；
5. direct 或 NAS 代理链路能够播放一条有权使用的测试媒体；
6. 单集下载后断网可离线播放；
7. APK 不包含服务端凭据或完整 catalog；
8. 不恢复任何被淘汰的 Qt/C++、TV Server、手机伴侣或 WebSocket 架构。
