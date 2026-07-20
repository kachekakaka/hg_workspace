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
```

本批次基线：

```text
main @ 798967b85c9972233caaf4166cfe910abde9f8ee
```

## 当前批次

分支：`agent/android-details-episodes`

范围：

- Android 读取正式作品详情 API；
- Android 读取正式分集 API；
- 严格校验作品详情和分集的内部 ID/来源 ID；
- 手机显示详情卡和分集纵向列表；
- TV 显示详情侧栏和遥控器可聚焦分集网格；
- 点击分集只显示身份、集序和时长，不伪造播放或下载能力；
- Android app 版本更新为 `0.2.0`；
- 同步 README、Android 开发文档和 ADR。

## 安全与范围边界

- Android 仍不包含 Cookie、Authorization、内容源抓取器或播放解析器；
- Android 不读取服务端短期 provider headers；
- 后端仍不提供媒体 `/stream` 或 `/proxy`；
- `external_proxy_required` 的 NAS handoff 尚未定义；
- 本批次不增加 Media3、下载、Room 片库或后台服务；
- 不处理无权访问、播放或下载的内容。

## 下一批

- Android playback response model 和状态显示；
- 在 production provider 和 NAS handoff 可用前继续隐藏播放入口；
- 之后再接入 Media3 在线播放、设备端下载和离线播放。

## 仍未完成

- 授权来源的生产 playback provider；
- NAS 外部代理对接协议；
- Media3 播放、设备端下载和离线播放；
- Release 签名与网络安全收紧；
- 手机、盒子和智慧屏真机测试。

每次后续报告必须继续列出 branch、commit SHA、PR、修改文件、实际命令、结果、CI 和未解决问题。
