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
```

本批次基线：

```text
main @ a66658cc29cb985d3a9d9f48d244a11e9270cba1
```

## 当前批次

分支：`agent/android-client-foundation`

范围：

- 新建干净的 `android/` 单模块工程；
- 手机 Launcher + TV Leanback Launcher；
- `leanback required=false`、`touchscreen required=false`；
- 手动保存并校验后端/NAS 服务地址；
- 读取 `/api/status` 和 `/api/works`；
- 手机纵向列表、TV 遥控器可聚焦网格和作品摘要弹窗；
- Docker Android Builder、JVM 单元测试、Debug APK 构建和 CI artifact；
- 不恢复旧本地 catalog、APK 内抓取、TV Server、mDNS 或 WebSocket；
- 不提前显示播放或下载入口。

## 构建边界

```text
Docker image
- JDK 17
- Android command-line tools 11076708
- Platform 35
- Build Tools 35.0.0
- Gradle 8.7
```

宿主机不需要 Android Studio、JDK、SDK 或 Gradle。APK 输出到 `dist/hg-client-debug.apk`，CI 作为 workflow artifact 上传，不提交 Git。

## 安全边界

- 公网服务地址必须 HTTPS；HTTP 仅允许局域网/本地主机；
- 服务地址不能带用户名、密码、query 或 fragment；
- Android 不包含 Cookie、Authorization、内容源抓取器或播放解析器；
- 后端仍不提供媒体 `/stream` 或 `/proxy`；
- 当前没有生产 playback provider 或 NAS handoff；
- 不处理无权访问、播放或下载的内容。

## 下一批

- Android 作品详情和分集导航；
- playback `direct` / `external_proxy_required` 客户端模型；
- 在 NAS handoff 明确后接入 Media3；
- 设备端下载和离线播放；
- Android 14、TV/盒子和华为 S65 真机验证。

## 仍未完成

- 授权来源的生产 playback provider；
- NAS 外部代理对接协议；
- Media3 播放、设备端下载和离线播放；
- Release 签名；
- 手机、盒子和智慧屏真机测试。

每次后续报告必须继续列出 branch、commit SHA、PR、修改文件、实际命令、结果、CI 和未解决问题。
