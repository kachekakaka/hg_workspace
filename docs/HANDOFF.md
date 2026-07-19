# 当前交接与核验状态

核验日期：2026-07-19
唯一权威仓库：`kachekakaka/hg_workspace`

## 已合并基线

```text
PR #1 -> main
Docker/FastAPI 基线、仓库卫生检查、旧工程审计、纯解析逻辑

PR #2 -> main
版本化 SQLite、作品/分集 repository、正式作品 API、旧 Web 只读兼容 API
```

PR #2 的 merge commit：

```text
6f3749363ed5c30ce1e5d186cb9118381545c9bf
```

## 当前批次

分支：`phase-2/catalog-import-tasks`

实现范围：

- 旧 catalog/checkpoint JSON 的纯映射；
- 可选声明集数与实际分集快照语义；
- SQLite 持久化任务 repository；
- 单工作线程 worker；
- `running -> interrupted` 启动恢复；
- failed/interrupted retry；
- catalog 异步导入；
- 正式任务 API 与旧 Web 兼容任务读取接口。

## 安全边界

- catalog 导入只处理请求体中的本地 JSON；
- 本批次没有第三方网络请求；
- 没有迁移 Cookie、Authorization、播放地址解析或 probe 输出；
- 没有把旧压缩包、APK、DLL、日志或本机路径提交到 GitHub；
- 不绕过 DRM、付费或访问控制。

## 仍未完成

- 全量/增量抓取适配器和抓取任务；
- 原生静态 Web 页面；
- 播放 direct/proxy/cache、Range 和下载；
- Android 通用 APK、Docker Android builder 和真机测试。

每次后续报告继续列出：branch、commit SHA、PR、修改文件、实际命令、结果、CI 和未解决问题。
