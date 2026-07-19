# ADR 0005：公开元数据来源适配器与持久化抓取任务

- 状态：Accepted
- 日期：2026-07-19

## 背景

旧全量/增量脚本把 HTTP、SSR 解析、checkpoint 文件和 C++ merge 链路混在一起。新后端已经有 SQLite catalog、持久化任务和 Web 管理页，需要把发现能力改成可测试的来源适配器，而不是恢复 JSON 主库或 C++ 中间层。

## 决策

1. 来源适配器返回标准 `WorkImport`，worker 直接幂等写入 SQLite。
2. 首个适配器只读取 `novelquickapp.com` 公开 SSR 作品元数据。
3. `incremental` 使用首页、分类默认列表、前三个时间筛选和第一个推荐排序；`full` 遍历受支持 selector。
4. 请求固定为 HTTPS 同源，不发送 Cookie/Authorization；单响应最多 8 MiB，分类请求最多 200 个。
5. 任务类型为 `scrape_full` 和 `scrape_incremental`，同一时间只允许一个抓取任务。
6. CI 使用合成 SSR fixture；不把第三方网络稳定性作为单元测试前提。
7. 本阶段不解析播放 URL，不实现 DRM、付费、登录或访问控制绕过。

## 原因

- 来源网络变化与 catalog 持久化解耦，便于 fixture 测试和失败定位；
- SQLite 复合键保证任务重试不会重复创建作品；
- 请求边界和显式限额降低 SSR 页面异常或配置错误造成的风险；
- 先完成元数据闭环，再单独设计需要凭据和过期策略的 playback 层。

## 影响

正面：

- Web 和 API 可以创建真实 full/incremental 持久化任务；
- 不再生成 checkpoint 主库；
- 失败写入任务记录，可观察、可 retry；
- 后续可增加其他合法来源适配器而不修改 catalog repository。

限制：

- 页面结构或来源策略变化仍可能让任务失败；
- 本批次未做在线来源 smoke test，部署时必须手动验证；
- 不标记“本次未发现”的旧作品为 removed，避免因来源临时缺页误下架。
