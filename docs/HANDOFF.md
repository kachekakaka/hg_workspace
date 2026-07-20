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
PR #8  NAS 外部媒体代理责任边界
PR #9  Docker 化手机/TV 通用 Android 客户端基础与 Debug APK CI
PR #10 Android 作品详情、身份校验和手机/TV 分集导航
```

本批次基线：

```text
main @ 5bdbdc0ce0cfc5820a59cfbc5ace84e91e049d44
```

## 当前批次

分支：`agent/android-playback-contract`

范围：

- Android 连接时读取 `/api/v1/playback/providers`；
- 新增 `PlaybackDelivery` 与 `PlaybackResolution` 客户端模型；
- 解析 `direct` 和 `external_proxy_required`；
- 拒绝旧 `proxy_required`、跨分集 ID、HTTP direct URL、URL 凭据/fragment，以及 external 响应泄露 URL；
- provider 未配置时不显示可执行检查；
- provider 已配置时允许检查一次短期 playback resolution；
- UI 只显示 provider、交付模式、缓存状态、MIME 和过期时间；
- 不显示来源 URL，不启动播放器或下载；
- Android app 版本更新为 `0.3.0`；
- 同步 README、Android 开发文档和 ADR。

## 安全与范围边界

- Android 仍不包含 Cookie、Authorization、内容源抓取器或播放解析器；
- Android 不接收服务端 provider headers；
- `direct` URL 只在内存模型中校验，当前 UI 不展示；
- `external_proxy_required` 必须没有 URL，等待 NAS handoff；
- 本批次不增加 Media3、下载、Room 主片库或后台服务；
- 不处理无权访问、播放或下载的内容。

## 下一批

- 在授权边界明确后实现首个 production playback provider；
- 定义 NAS handoff；
- 再接入 Media3 direct 播放和外部代理播放。

## 仍未完成

- 授权来源的 production playback provider；
- NAS 外部代理对接协议；
- Media3 播放、设备端下载和离线播放；
- Release 签名与网络安全收紧；
- 手机、盒子和智慧屏真机测试。

每次后续报告必须继续列出 branch、commit SHA、PR、修改文件、实际命令、结果、CI 和未解决问题。
