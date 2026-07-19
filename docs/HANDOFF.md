# 当前交接与核验状态

核验日期：2026-07-19
唯一权威仓库：`kachekakaka/hg_workspace`

## 已合并基线

```text
PR #1  Docker/FastAPI 基线、旧工程审计和纯解析逻辑
PR #2  SQLite 作品/分集目录与 API
PR #3  旧 catalog 映射、持久化任务和 worker
PR #4  FastAPI 同域原生静态管理页
PR #5  公开 SSR 全量/增量发现任务
PR #6  公开详情与分集 enrichment
```

本批次基线：

```text
main @ a5d757a04a7a98137c783a854b7be718d0e2a6af
```

## 当前批次

分支：`phase-2/playback-contract`

范围：

- provider-neutral `PlaybackProvider` / `PlaybackCandidate` 契约；
- `0002_playback_resolutions.sql` 短期解析缓存；
- HTTPS、URL 凭据、header、expiry、provider 名称和 TTL 校验；
- direct / proxy_required 两种交付声明；
- 解析、读取缓存、失效和 provider 列表 API；
- 默认生产 provider registry 为空；
- 合成 provider 测试，确保 headers 不进入 API 响应、异常不泄露 provider 内部信息。

## 设计边界

- 本批次不迁移旧 Cookie/Authorization 解析脚本；
- 不注册任何第三方生产 playback provider；
- 不实现 proxy、HTTP Range、缓存下载或 Web 播放按钮；
- 含 provider headers 的结果只标记 `proxy_required`，不会返回 URL 或 headers；
- direct 仅允许 HTTPS、无 headers、provider 显式允许的短期 URL；
- CI 不访问第三方网络，不证明任何真实来源可播放；
- 不绕过 DRM、付费、登录或访问控制。

## 仍未完成

- 授权来源的生产 playback provider；
- proxy、HTTP Range、header 注入和日志脱敏；
- 服务端媒体缓存、下载任务和配额；
- Android 通用 APK、Docker Android builder、Media3 和真机测试。

每次后续报告必须继续列出 branch、commit SHA、PR、修改文件、实际命令、结果、CI 和未解决问题。
