# 旧工程源码审计与选择性迁移记录

- 审计日期：2026-07-19
- 功能分支：`phase-1/repository-bootstrap`
- 输入压缩包：`hg_workspace(3).rar`
- 压缩包 SHA-256：`a0b95437b120ec9ed57a61d5acc04dfa883f8b4362fac12b96f77be667e8bfbf`
- 详细 Review 原文件 SHA-256：`b4cfdb9dae01e744f7586b7283dbd6f4a3129e358684b171d590b1e8314c1fed`

压缩包只是迁移输入，不会原样提交到 GitHub。本记录中的“已迁移”仅指下文明确列出的文件和逻辑。

## 1. 归档清单

使用 RAR 元数据和只读流式检查得到：

| 指标 | 数值 |
|---|---:|
| 条目 | 3329 |
| 文件 | 2335 |
| 目录 | 994 |
| 解压文件总大小 | 491,057,872 bytes（约 468.3 MiB） |

主要顶层目录大小：

| 目录 | Bytes | 判断 |
|---|---:|---|
| `hg_tv` | 198,505,421 | 主要是 Gradle 构建输出；少量 Compose/Media3 源码可供后续迁移 |
| `hg_remote` | 153,006,226 | 主要是构建输出；旧手机伴侣整体不进入新架构 |
| `hg_app` | 127,783,890 | Qt DLL/EXE、旧 APK、配置和日志；不进入主线 |
| `hg_tool` | 9,763,093 | Qt/C++ 服务和 GUI；停止维护 |
| `output` | 1,729,742 | 运行输出；不提交 |
| `python` | 142,491 | 抓取、解析和探测脚本；按能力拆分迁移 |
| `web` | 22,914 | 原生静态管理页；待 Phase 2 API 兼容后迁移 |

归档中确认存在旧 APK、DLL、EXE、Gradle `build/`、`.gradle/`、`local.properties`、日志和运行输出。这些都被忽略规则和仓库卫生检查明确排除。

## 2. 安全扫描

执行了以下检查：

1. 文件名扫描：私钥、keystore、P12/PFX、`.env`、常见 credentials/secrets 文件名；
2. 673 个不含明显二进制 NUL、单文件不超过 10 MiB 的文件内容扫描，共检查 10,703,964 bytes；
3. 高风险明文模式扫描：私钥头、GitHub/AWS/Google Token 形态、JWT、带值的 Basic/Bearer Authorization、带值的 Cookie；
4. 单独记录 Cookie/Authorization 处理代码和本机绝对路径。

结果：

- 没有命中高风险明文凭据模式；
- 没有发现私钥或 keystore 类文件名；
- 发现 22 个涉及 Cookie/Authorization 处理的文件；
- 发现 42 个包含宿主机路径或 `sdk.dir` 痕迹的文件，其中大量来自构建输出；
- `hg_app/config/config.json`、默认配置和 `hg_tool/config.runtime.json` 中的 `api_key` / `play_cookie` 当前为空；
- 日志和 `local.properties` 暴露旧机器目录，不能提交到新仓库。

“没有命中”不等于绝对没有秘密：该扫描不能证明二进制、加密、混淆或未知格式中不存在敏感数据。因此旧压缩包仍禁止原样提交，后续每一批迁移文件都必须再次经过 GitHub CI 检查。

## 3. 本次实际迁移

本次只迁移可独立测试、无网络、无凭据的纯逻辑：

| 旧来源 | 新位置 | 处理 |
|---|---|---|
| `python/video_quality.py` | `backend/app/services/video_quality.py` | 重写为健壮、类型清晰的纯 URL/质量选择函数；不发起 HTTP 请求 |
| `python/novelquick_episodes.py` 的 SSR 解析与分集规范化 | `backend/app/sources/novelquick.py` | 仅保留 HTML/JSON 解析和 URL 构造；删除 CLI 与网络请求 |
| `python/novelquick_web_play.py` 的 `video_player_info` 解析 | `backend/app/sources/novelquick.py` | 仅保留纯解析；不获取播放地址、不携带 Cookie |

同时新增对应单元测试。迁移代码不接入生产路由，不触发外部抓取，也不把第三方会话信息传给客户端。

## 4. 明确不迁移或暂缓

### 永久排除新主线

- `hg_tool/` Qt/C++ GUI、中间层和内置 HTTP 服务；
- `catalog.pack` 导入导出链路；
- `hg_remote/` 手机遥控伴侣；
- TV 内置 Ktor HTTP/WebSocket Server；
- mDNS/NSD、二维码配对和 WebSocket 推片；
- 旧 APK、DLL、EXE、OBJ、缓存、日志、运行数据和硬编码 `local.properties`。

### Phase 2 前暂缓

- `scrape_all.py`、`scrape_incr.py`、`import_work.py`：需要先把 checkpoint/JSON 写入改成 SQLite repository，并增加固定 fixture 测试；
- `play_auth.py`、`hongguo_official_play.py`、`play_url_resolver.py`：涉及 Cookie、Authorization、短期 URL 和多个回退端点，必须先定义服务端 secret 存储、授权内容源政策、日志脱敏和过期策略；
- `probe_*.py`：只可进入独立 `tools/probes/`，不得成为生产服务代码；
- `web/`：待旧 API 兼容端点具备测试后迁入 `backend/app/static/`；
- `hg_tv` Compose/Media3 UI：待 Phase 3 创建单一通用 Android 工程后，按页面和数据层逐个迁移，不能复制 LAN Server、片库导入或 APK 内播放解析。

## 5. 设计结论

1. 旧压缩包的价值集中在少量 Python 解析逻辑、原生 Web 页面以及 Android UI/播放器思路，而不是现有构建目录。
2. 新主线不保存完整旧仓库，也不建立长期 `archive/legacy/` 目录。
3. 源码迁移必须“拆能力、补测试、去网络副作用、去凭据、再接入 API”，不能机械复制。
4. 对第三方内容源只允许在有权访问、缓存和播放的范围内实现；不得绕过 DRM、付费或访问控制。
