# Android 通用客户端开发

## 范围

当前 Android 工程是一个手机/电视通用 APK 的最小基础：

- 同一个 `app` module；
- 同时声明普通 Launcher 和 Leanback Launcher；
- `leanback required=false`、`touchscreen required=false`；
- 手动保存 FastAPI/NAS 服务地址；
- 读取 `/api/status` 和 `/api/works`；
- 手机使用纵向列表，TV 使用遥控器可聚焦网格；
- 当前没有播放器、下载、Room 主片库、TV 内置服务、mDNS 或 WebSocket。

## 构建

宿主机只需要 Docker：

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

Docker 镜像固定安装：

- JDK 17；
- Android command-line tools `11076708`；
- Android Platform 35；
- Build Tools 35.0.0；
- 项目 Gradle 8.7。

不提交 `local.properties`，也不在宿主机设置 `JAVA_HOME` 或 `ANDROID_HOME`。

## 安装

可选使用便携版 adb：

```text
scripts\install-apk.bat
```

也可以把 `dist/hg-client-debug.apk` 复制到手机、U 盘或 NAS 后手动安装。

## 服务地址规则

- 输入 `192.168.1.10:8000` 会规范化为 `http://192.168.1.10:8000`；
- 公网域名必须使用 HTTPS；
- HTTP 只允许 localhost、单标签局域网主机、`.local`、RFC1918 IPv4 和本地 IPv6；
- 不允许 URL 用户名/密码、query 或 fragment；
- 地址保存在应用私有 SharedPreferences；
- Android Manifest 暂时允许 cleartext，以支持局域网 Debug；URL 校验阻止公网明文 HTTP。

## 后续

1. 作品详情与分集页面；
2. playback `direct` / `external_proxy_required` 客户端模型；
3. 与 NAS 的最小代理 handoff；
4. Media3 在线播放；
5. Media3 设备端下载和离线播放；
6. 手机触控、TV 遥控器和华为 S65 兼容测试。
