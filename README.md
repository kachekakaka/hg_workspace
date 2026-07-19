# HG Workspace（红果电视 APP）

HG Workspace 正在重构为一个简单、可审计的单仓库项目：

- Python 3.12 + FastAPI + SQLite 后端；
- 后端托管的原生 Web 管理页面（后续阶段实现，不引入 Node）；
- 一个 Kotlin + Compose + Media3 通用 APK，覆盖手机和电视设备（后续阶段实现）。

## 代码权威源

唯一代码权威源是 GitHub 仓库 `kachekakaka/hg_workspace`。只有 GitHub 文件、commit、branch、PR 和 CI 能证明工作已完成；聊天记录、本地压缩包和旧 APK 仅可作为迁移线索。

## 当前阶段

`phase-1/repository-bootstrap` 只建立可验证的仓库基础：

- Docker 化 FastAPI `/health` 服务；
- 最小自动化测试；
- 仓库卫生与基础 secret 检查；
- GitHub Actions；
- 忽略规则和设计记录。

旧工程源码尚未进入当前 GitHub 仓库。本阶段不会假装迁移了未提供的旧源码，也不会恢复 Qt/C++、`catalog.pack`、手机遥控伴侣、TV 内置服务器、mDNS 或 WebSocket 控制链路。

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
├── backend/                  # FastAPI 后端和测试
├── docs/                     # 架构、计划与决策记录
├── scripts/                  # 仓库级检查脚本
├── .github/workflows/ci.yml  # 基础 CI
└── compose.yaml              # Docker 开发入口
```

## 后续顺序

1. 用户重新提供旧工程压缩包和详细 Review 文档；
2. 对旧源码执行文件清单、secret scan 和选择性迁移；
3. 建立 SQLite 数据模型与作品/分集 API；
4. 迁移原生 Web 管理页面；
5. 建立并 Docker 化 Android 通用 APK；
6. 完成在线播放、下载、离线播放和设备验证。
