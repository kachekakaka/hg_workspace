# 当前交接与核验状态

核验日期：2026-07-19
唯一权威仓库：`kachekakaka/hg_workspace`

## 已合并基线

```text
PR #1 -> main
Docker/FastAPI 基线、仓库卫生检查、旧工程审计、纯解析逻辑

PR #2 -> main
版本化 SQLite、作品/分集 repository、正式作品 API、旧 Web 只读兼容 API

PR #3 -> main
旧 catalog 纯映射、SQLite 持久化任务、单线程 worker、retry 和启动恢复
```

PR #3 merge commit：

```text
3ffb59951d5540706345814c21f71f9a619b5a90
```

## 当前批次

分支：`phase-2/static-web-admin`

实现范围：

- FastAPI 同域托管原生静态管理页；
- 作品分页、搜索、状态/标签过滤和详情；
- 已入库分集展示；
- 统计和服务状态；
- 本地 catalog JSON 文件上传并创建持久化任务；
- 任务进度、结果、失败/中断重试；
- 手机尺寸的基础响应式布局；
- 不引入 Node、npm、React、Vue 或远程 CDN。

## 安全与真实性边界

- 管理页不显示尚未实现的网络抓取和 enrich 按钮；
- 本地 JSON 由浏览器读取后作为请求体提交，后端不读取用户提供的服务器文件路径；
- 动态作品字段使用 DOM 文本节点；封面和来源链接只允许 HTTP/HTTPS；
- 本批次没有 Cookie/Authorization、播放、Range 代理、缓存、下载或 Android 实现；
- 不恢复 Qt/C++、catalog.pack、手机伴侣、TV Server、mDNS 或 WebSocket。

## 仍未完成

- 全量/增量内容源适配器和抓取任务；
- playback direct/proxy/cache 与 HTTP Range；
- 服务端媒体缓存和下载；
- Android 通用 APK、Docker Android builder 和真机测试。

每次后续报告继续列出：branch、commit SHA、PR、修改文件、实际命令、结果、CI 和未解决问题。
