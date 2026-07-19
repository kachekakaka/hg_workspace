# 当前交接与核验状态

核验日期：2026-07-19
唯一权威仓库：`kachekakaka/hg_workspace`

## 已合并基线

```text
PR #1  Docker/FastAPI 基线、旧工程审计和纯解析逻辑
PR #2  SQLite 作品/分集目录与 API
PR #3  旧 catalog 映射、持久化任务和 worker
PR #4  FastAPI 同域原生静态管理页
```

本批次基线：

```text
main @ c1859c19c97bcd5cdd06c1aaf8bdc016e81c13c5
```

## 当前批次

分支：`phase-2/source-tasks`

范围：

- `novelquick` 公开 SSR 作品元数据适配器；
- HTTPS 同源、超时、重试、8 MiB 响应和最多 200 个分类任务限制；
- full/incremental 持久化任务；
- 任务进度、失败持久化、retry 和重复抓取防护；
- 正式和旧 Web 兼容的抓取触发 API；
- `/tasks.html` 全量/增量触发按钮；
- 合成 SSR fixture、任务闭环、配置和静态页面测试。

## 设计边界

- 只读取公开 SSR 作品元数据；
- 不发送 Cookie、Authorization 或凭据；
- 不解析播放地址，不绕过 DRM、付费、登录或访问控制；
- 不写 checkpoint JSON 主库，结果直接幂等写入 SQLite；
- CI 不访问第三方网络；真实来源可用性仍需部署环境手动验证；
- 不恢复 Qt/C++、`catalog.pack`、手机伴侣、TV Server、mDNS 或 WebSocket。

## 仍未完成

- playback provider、短期 URL/headers/expiry；
- direct/proxy/cache 和 HTTP Range；
- 服务端媒体缓存和下载任务；
- Android 通用 APK、Docker Android builder、Media3 和真机测试。

每次后续报告必须继续列出 branch、commit SHA、PR、修改文件、实际命令、结果、CI 和未解决问题。
