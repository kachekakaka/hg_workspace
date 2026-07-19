# 下一窗口实施提示词

使用 GitHub 仓库：

`kachekakaka/hg_workspace`

作为唯一代码权威源。

不要依赖聊天记录中声称已完成但未提交的内容，所有进度以 GitHub 仓库文件、commit、issue、PR 和 CI 为准。

## 首先读取

1. README.md
2. docs/HG_REFACTOR_PLAN.md
3. 全部 docs 文档
4. 当前仓库目录结构
5. git log

## 项目目标

将旧 hg_workspace 重构为：

- Python FastAPI 后端
- Web 管理页面
- 一个 Android 手机/电视通用 APK

不要恢复旧架构。

禁止新增：

- Qt 管理程序
- C++ 服务层
- 手机遥控伴侣
- catalog.pack 同步
- TV 内置服务器
- mDNS 自动发现
- WebSocket 控制链路

## 开发原则

第一优先级：开发环境简单。

目标：

宿主机只需要：

- Docker
- Git
- 编辑器
- 可选 adb

不要要求用户安装：

- Android Studio
- Python 环境
- JDK
- Android SDK
- Qt

使用 Docker 固化开发环境。

## 实施顺序

Phase 1：

- 清理仓库
- 建立正确目录结构
- 删除构建产物
- 增加 Docker 基础环境

Phase 2：

- 建立 FastAPI 后端
- 迁移现有 Python 抓取逻辑
- SQLite 数据模型
- Web 管理 API

Phase 3：

- 精简 Android 客户端
- 删除本地作品库同步逻辑
- 改为访问后端 API
- Media3 播放

Phase 4：

- 下载和离线播放
- 真机测试

每一步都需要：

- 更新 docs
- 提交 commit
- 保持 main 可构建
- 记录变更原因
