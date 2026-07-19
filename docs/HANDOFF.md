# 当前交接与核验状态

核验日期：2026-07-19
唯一权威仓库：`kachekakaka/hg_workspace`

## 已合并基线

```text
PR #1  Docker/FastAPI 基线、旧工程审计和纯解析逻辑
PR #2  SQLite 作品/分集目录与 API
PR #3  旧 catalog 映射、持久化任务和 worker
PR #4  FastAPI 同域原生静态管理页
PR #5  公开 SSR 全量/增量发现任务
```

本批次基线：

```text
main @ 012e5300334413809acfc830dd61bda2704f477e
```

## 当前批次

分支：`phase-2/episode-enrichment`

范围：

- 从公开 SSR `seriesDetail` 刷新一部作品；
- 将非空 `vid_list` 规范化为 `source_episode_id`、集序和标题；
- `enrich_work` 持久化任务、进度、失败和 retry；
- 同一作品重复 enrichment 防护，同时允许不同作品排队；
- 正式和旧 Web 兼容 API；
- 作品详情管理页刷新按钮和任务结果展示；
- 合成 SSR、任务闭环、身份校验和静态页面测试。

## 设计边界

- 只读取公开详情页元数据；
- 不请求 player 页面，不读取或保存播放 URL；
- 不发送 Cookie、Authorization 或凭据；
- 只有解析到非空分集列表时才替换分集快照，避免来源临时缺失导致误删；
- CI 不访问第三方网络；
- 不恢复 Qt/C++、`catalog.pack`、手机伴侣、TV Server、mDNS 或 WebSocket。

## 仍未完成

- playback provider、短期 URL/headers/expiry；
- direct/proxy/cache 和 HTTP Range；
- 服务端媒体缓存和下载任务；
- Android 通用 APK、Docker Android builder、Media3 和真机测试。

每次后续报告必须继续列出 branch、commit SHA、PR、修改文件、实际命令、结果、CI 和未解决问题。
