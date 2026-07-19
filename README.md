# HG Workspace（红果电视 APP）

HG Workspace 正在重构为一个简单、可审计的单仓库项目：

- Python 3.12 + FastAPI + SQLite 后端；
- 后端托管的原生 Web 管理页面（后续阶段实现，不引入 Node）；
- 一个 Kotlin + Compose + Media3 通用 APK，覆盖手机和电视设备（后续阶段实现）。

## 代码权威源

唯一代码权威源是 GitHub 仓库 `kachekakaka/hg_workspace`。只有 GitHub 文件、commit、branch、PR 和 CI 能证明工作已完成；聊天记录、本地压缩包和旧 APK 仅可作为迁移输入。

## 当前阶段

`phase-1/repository-bootstrap` 建立可验证的仓库基础：

- Docker 化 FastAPI `/health` 服务；
- 最小自动化测试；
- 仓库卫生与基础 secret 检查；
- GitHub Actions；
- 旧工程归档审计和设计记录；
- 从旧 Python 中选择性迁移无网络、无凭据的纯解析逻辑。

旧压缩包没有原样进入仓库。当前只迁移了视频质量选择和 SSR 分集/播放器信息解析；抓取、Cookie 鉴权、Web 页面、Android UI 和播放/下载链路尚未接入。Qt/C++、`catalog.pack`、手机遥控伴侣、TV 内置服务器、mDNS 和 WebSocket 控制链路不会恢复。

详细结果见：

- [`docs/LEGACY_SOURCE_AUDIT.md`](docs/LEGACY_SOURCE_AUDIT.md)

## 宿主机要求

必需：

- Docker（含 Docker Compose）；
- Git；
- VS Code/Cursor 或其他编辑器。

可选：

- `adb`，用于后续真机安装和调试。

不要求安装 Android Studio、本机 JDK、本机 Android SDK、本机 Python、Qt、MSVC、CMake 或 Node。

## 启动后端

```bash
docker compose up --build backend
```

服务健康检查：

```bash
curl --fail http://localhost:8000/health
```

预期响应：

```json
{"status":"ok","service":"hg-backend"}
```

## 运行测试

```bash
docker compose --profile test build backend-test
docker compose --profile test run --rm backend-test
```

仓库卫生和明显 secret 检查由 GitHub Actions 自动执行，检查对象是 Git 实际跟踪的文件，不要求宿主机安装 Python。

## 当前目录

```text
.
├── backend/
│   ├── app/services/         # 纯服务层逻辑
│   ├── app/sources/          # 内容源纯解析器；暂不含网络抓取
│   └── tests/                # 后端单元测试
├── docs/                     # 架构、审计、计划与决策记录
├── scripts/                  # 仓库级检查脚本
├── .github/workflows/ci.yml  # 基础 CI
└── compose.yaml              # Docker 开发入口
```

## 后续顺序

1. 合并通过 CI 的 Phase 1 仓库基础；
2. 建立 SQLite schema、repository 和版本化 SQL；
3. 以 fixture 驱动方式迁移全量/增量抓取和导入逻辑；
4. 实现作品、分集、任务和旧 Web 兼容 API，再迁移原生静态页面；
5. 建立并 Docker 化 Android 通用 APK；
6. 完成授权内容的在线播放、下载、离线播放和设备验证。
