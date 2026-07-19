# ADR 0004：由 FastAPI 同域托管原生静态管理页

- 状态：Accepted
- 日期：2026-07-19

## 背景

旧工程已有原生 HTML/CSS/JavaScript 管理页，但依赖 Qt/C++ HTTP 服务、未实现的 enrich 和抓取按钮。当前后端已经具备作品、统计、catalog 导入和持久化任务 API。项目要求宿主机简单，不应为管理页增加 Node、npm、前端框架或第二个部署服务。

## 决策

1. 管理页放在 `backend/app/static/`，由 FastAPI/Starlette `StaticFiles` 同域托管。
2. `/`、`/stats.html`、`/tasks.html` 分别提供作品、统计、任务和本地 catalog 导入页面。
3. 页面只使用原生 HTML、CSS 和 ES modules，不引入 Node 构建链或远程 CDN 资源。
4. 作品页复用旧信息架构，但移除未实现的 enrich；详情只显示数据库内容和分集。
5. 任务页不展示尚未实现的全量/增量网络抓取按钮，只支持本地 JSON 请求体导入、任务查看和失败/中断重试。
6. 封面和来源详情 URL 只接受 HTTP/HTTPS；动态内容使用 DOM `textContent`，避免把作品字段直接插入 HTML。
7. API、健康检查和 OpenAPI 路由在静态根挂载前注册，保证 `/api/*`、`/health`、`/docs` 不被静态路由覆盖。

## 原因

- 同域部署避免 CORS、版本同步和额外容器；
- 原生页面足以完成第一版管理任务；
- 移除不存在的操作比提供必然失败的按钮更诚实；
- 无外部 CDN 使 Docker 部署在局域网和受限网络下更可预测；
- DOM 安全构造降低旧页面字符串模板带来的 XSS 风险。

## 影响和限制

- 页面不是复杂 SPA，不提供离线前端缓存；
- catalog 文件在浏览器内解析，管理页限制为 20 MiB，超大导入应使用 API 或拆分；
- 抓取触发、播放、代理、下载和 Android 管理不在本批次；
- 后续新增 API 时应保持旧页面兼容或同步更新静态模块测试。
