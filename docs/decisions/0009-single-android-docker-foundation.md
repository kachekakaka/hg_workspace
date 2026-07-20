# ADR 0009：建立 Docker 构建的单一 Android 手机/电视客户端

- 状态：Accepted
- 日期：2026-07-20

## 背景

后端目录、任务、Web 和 playback 交付契约已经稳定。旧 `hg_tv` 包含可复用的 Compose/Media3 思路，但同时包含完整本地片库、TV 内置 Ktor Server、mDNS、WebSocket 和来源解析；旧 `hg_remote` 不是可干净重建的完整工程。项目要求宿主机不安装 Android Studio、JDK 或 Android SDK，并且只维护一个 APK。

## 决策

1. 新建干净的 `android/` 工程，而不是复制旧构建目录。
2. 使用一个 `app` module，同时声明 `LAUNCHER` 和 `LEANBACK_LAUNCHER`。
3. `android.software.leanback` 与 `android.hardware.touchscreen` 都设为 `required=false`。
4. 第一批只实现服务地址、后端状态和作品列表；不提前加入播放或下载按钮。
5. Room 不保存完整作品库；当前甚至不引入 Room，只用 SharedPreferences 保存服务地址。
6. 客户端使用后端 API，不包含抓取器、Cookie、Authorization、播放解析或 NAS 凭据。
7. Android 构建环境放入 `docker/android-builder.Dockerfile`，固定 JDK 17、SDK 35、Build Tools 35.0.0 和 Gradle 8.7。
8. CI 在 Docker 中运行 JVM 单元测试并生成 Debug APK，APK 只作为 workflow artifact，不提交 Git。Gradle 固定在构建镜像中，宿主机不需要 Wrapper 或本机 Gradle。
9. 局域网 HTTP 仅通过客户端 URL 校验允许；公网地址必须使用 HTTPS。

## 原因

- 单工程、单 APK 降低维护和发布复杂度；
- 新建干净工程避免把旧 LAN Server、catalog 和构建缓存带回主线；
- 先走通后端连接和作品列表，能尽早验证手机/TV 共用数据层；
- Docker 构建符合宿主机零污染目标；
- 不引入播放器和下载，避免在 NAS handoff 尚未定义时制造错误接口。

## 影响

正面：

- 干净 clone 后只需 Docker 即可构建 APK；
- 手机和 TV 使用同一包名和数据层；
- CI 可提供可下载的 Debug APK artifact；
- 旧架构依赖没有进入新 APK。

限制：

- 当前只浏览首页作品，不含详情、分集导航、播放或下载；
- cleartext 仅为局域网 Debug 兼容，Release 网络安全策略后续收紧；
- 尚未完成真机、盒子或华为智慧屏验证；
- 第一次 Docker/Gradle 构建需要下载较大的 SDK 和 Maven 依赖。
