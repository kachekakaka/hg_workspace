# 当前交接与核验状态

核验日期：2026-07-20
唯一权威仓库：`kachekakaka/hg_workspace`

## 已合并基线

```text
PR #1  Docker/FastAPI 基线、旧工程审计和纯解析逻辑
PR #2  SQLite 作品/分集目录与 API
PR #3  旧 catalog 映射、持久化任务和 worker
PR #4  FastAPI 同域原生静态管理页
PR #5  公开 SSR 全量/增量发现任务
PR #6  公开详情与分集 enrichment
PR #7  provider-neutral playback 解析契约与短期缓存
```

本批次基线：

```text
main @ 7b15ff9889d05a98b7ac8ce038c37208b077d23f
```

## 当前批次

分支：`agent/nas-proxy-boundary`

范围：

- 将带服务端 headers 的交付声明从 `proxy_required` 改为 `external_proxy_required`；
- 明确媒体代理、TLS、域名和公网入口由用户 NAS 负责；
- 后端不实现 `/stream`、`/proxy`、HTTP Range 或媒体字节转发；
- direct 仍只允许 HTTPS、无 headers、provider 显式允许的短期 URL；
- 更新 API 模型、服务测试、README、重构计划和 ADR；
- 后端版本更新为 `0.7.1`。

## 设计边界

- 后端继续保存短期解析结果，但不向 Android 暴露 provider headers；
- `external_proxy_required` 只是能力声明，在 NAS 对接协议定义前不可直接播放；
- 本仓库不固定公网 IP，不实现 DNS pinning 代理，也不转发视频字节；
- NAS 代理不是 TV 内置服务器，也不恢复旧 LAN Server/WebSocket 架构；
- 不注册任何未经授权的生产 playback provider；
- 不绕过 DRM、付费、登录或访问控制。

## 下一批

优先建立 Docker 化 Android 通用工程：

- 单一 app module；
- 手机 Launcher + TV Leanback Launcher；
- `leanback required=false`、`touchscreen required=false`；
- 手动配置后端/NAS 服务地址；
- 先实现作品、详情和分集浏览，不伪造播放或下载完成状态。

## 仍未完成

- 授权来源的生产 playback provider；
- NAS 外部代理对接协议；
- Android 通用 APK、Docker Android builder、Media3、设备端下载和真机测试。

每次后续报告必须继续列出 branch、commit SHA、PR、修改文件、实际命令、结果、CI 和未解决问题。
