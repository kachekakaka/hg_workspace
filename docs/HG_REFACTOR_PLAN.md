# HG Workspace 精简重构方案

## 目标

将原有复杂架构收缩为：

- Python 后端负责抓取、作品管理、播放地址解析、下载任务。
- Web 页面负责管理和任务操作。
- 一个 Android APK 同时支持手机、安卓电视盒子和兼容的智慧屏设备。

目标是降低开发和部署复杂度。

## 最终架构

```
Python FastAPI Backend
    |
    | HTTP API
    |
Android Client APK
    ├── Android 手机
    ├── Android TV/盒子
    └── 华为智慧屏兼容测试
```

## 保留

### Python

- 现有抓取逻辑
- 增量更新
- 分集解析
- 播放地址解析
- 视频质量处理
- Web 管理页面

### Android

保留：

- Media3 ExoPlayer
- 作品列表
- 详情页
- 播放页面
- 遥控器焦点支持

## 删除或停止维护

- Qt 管理工具
- C++ 中间层
- catalog.pack 同步机制
- 手机遥控伴侣端
- TV 内置 HTTP Server
- mDNS/NSD 自动发现
- WebSocket 控制链路
- APK 内置完整作品库

## 开发环境要求

优先目标：宿主机零污染。

宿主机只需要：

- Docker
- Git
- VS Code/Cursor
- 可选 adb 工具

不要要求安装：

- Android Studio
- 本机 JDK
- 本机 Android SDK
- 本机 Python
- Qt 环境

所有依赖通过 Docker 固化。

## 后端

技术：

- Python 3.12
- FastAPI
- SQLite
- Docker Compose

第一阶段不引入：

- Redis
- Celery
- PostgreSQL
- 微服务

## Android

技术：

- Kotlin
- Jetpack Compose（继续复用现有代码）
- Media3
- 一个通用 APK

功能：

- 连接后端
- 浏览作品
- 选择分集
- 在线播放
- 下载
- 离线播放

## 实施阶段

### Phase 1

仓库清理：

- 删除 build 产物
- 删除 APK/DLL/缓存
- 完善 .gitignore
- 固化 Docker 构建

### Phase 2

Python 后端：

- FastAPI
- SQLite
- 作品 API
- 任务 API
- 播放 API

### Phase 3

Android 客户端：

- 删除本地 catalog 导入
- 改为 API 获取作品
- 接入播放接口

### Phase 4

下载能力：

- 后端缓存
- APK 下载管理
- 离线播放

## 验收标准

最终实现：

1. docker compose 一键启动服务。
2. Web 页面管理作品和任务。
3. Android 手机连接后可以播放。
4. Android TV/盒子遥控器可操作。
5. APK 不依赖本机开发环境。