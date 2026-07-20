# Android 通用客户端开发

## 当前范围

Android 工程是一个手机/电视通用 APK：

- 同一个 `app` module；
- 同时声明普通 Launcher 和 Leanback Launcher；
- `leanback required=false`、`touchscreen required=false`；
- 手动保存 FastAPI/NAS 服务地址；
- 读取 `/api/status` 和 `/api/works`；
- 读取 `/api/v1/works/{work_id}` 和 `/api/v1/works/{work_id}/episodes`；
- 手机使用作品/分集纵向列表；
- TV 使用遥控器可聚焦作品/分集网格；
- 读取 playback provider 列表并解析 `direct` / `external_proxy_required`；
- 当前没有 Media3 播放器、下载、Room 主片库、TV 内置服务、mDNS 或 WebSocket。

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
- Gradle 8.7。

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
- 不允许 URL 用户名/密码、query、fragment 或上级目录路径；
- 地址保存在应用私有 SharedPreferences；
- Manifest 暂时允许 cleartext，以支持局域网 Debug；URL 校验阻止公网明文 HTTP。

## 作品详情和分集

客户端先从 `/api/works` 获取作品摘要。打开作品时依次读取：

```text
GET /api/v1/works/{internal-work-id}
GET /api/v1/works/{internal-work-id}/episodes
```

客户端校验：

- 详情内部 ID 必须与列表一致；
- 详情来源作品 ID 必须与列表一致；
- 每一集的 `work_id` 必须指向当前作品；
- 无效分集行会被忽略；
- 分集按 `episode_index` 和内部 ID 排序；

手机详情页显示元数据和分集列表。TV 详情页使用左侧元数据、右侧焦点网格。

客户端连接时读取 `GET /api/v1/playback/providers`。点击分集时：

- 来源未配置 provider：只显示明确提示；
- 来源已配置 provider：允许调用 `POST /api/v1/episodes/{episode_id}/playback/resolve`；
- `direct`：校验 HTTPS URL，但不显示 URL、不启动播放器；
- `external_proxy_required`：要求 URL 必须为空，只显示等待 NAS handoff；
- 旧 `proxy_required`、HTTP URL、跨分集 ID 或泄露来源 URL 的响应会被拒绝。

## 后续

1. 授权来源 production playback provider；
2. 与 NAS 的最小代理 handoff；
3. Media3 `direct` 在线播放；
4. NAS handoff 完成后的外部代理播放；
5. Media3 设备端下载和离线播放；
6. 手机触控、TV 遥控器和华为 S65 兼容测试。
