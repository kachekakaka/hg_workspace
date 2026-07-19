# ADR 0002：使用 sqlite3、版本化 SQL 和来源复合键建立作品目录

- 状态：Accepted
- 日期：2026-07-19

## 背景

Phase 1 只提供可构建的 FastAPI 骨架和经过审计的纯解析函数。旧工程以 JSON/checkpoint 和 C++ merge 作为主数据链路，无法提供服务端事务、查询、任务恢复或稳定的 APK API。

第一版规模不需要 ORM、独立数据库服务或分布式任务系统，但需要可审计、可升级、可在 Docker volume 中持久化的数据层。

## 决策

1. 使用 Python 标准库 `sqlite3`；不引入 SQLAlchemy 或 Alembic。
2. 数据库变更放入 `backend/app/migrations/NNNN_name.sql`，由 `schema_migrations` 记录已应用版本。
3. 作品使用内部整数 `id`，并以 `(source, source_work_id)` 保证来源内幂等。
4. 分集使用内部整数 `id`，并以 `(work_id, source_episode_id)` 保证幂等。
5. 导入 payload 未提供 `episodes` 时只更新作品元数据；提供数组时将其视为该作品的权威分集快照。
6. JSON 只用于标签、演员、任务参数/结果和短期请求头等边缘字段，不再作为作品主库。
7. 首批 API 同时提供 `/api/v1` 正式接口和旧原生 Web 需要的只读兼容接口。
8. 播放地址不作为永久作品字段；短期解析结果只允许进入后续播放/缓存表并带过期时间。

## 原因

- `sqlite3` 足以支撑单机第一版，并保持 Docker 依赖简单；
- SQL 文件易于 Review、测试和故障定位；
- 内部 ID 让 APK/API 不依赖第三方来源 ID 的格式；
- 来源复合键支持重复抓取的幂等写入；
- 明确的分集快照语义避免“只更新元数据”时误删分集；
- 兼容只读端点可以在后续迁移原生 Web 时减少同时变更多个层次的风险。

## 影响

正面：

- 数据库可在启动时自动、幂等升级；
- 作品和分集可分页、搜索、过滤并跨进程重启保存；
- 抓取器后续只需输出 `WorkImport`，不再直接重写 catalog JSON；
- API 和 repository 可用合成 fixture 完整测试。

代价与限制：

- 第一版只支持 SQLite 单机写入；
- 旧 catalog 仍需单独映射和导入；
- 任务 worker、播放代理、缓存清理和 Android 数据模型尚未实现；
- 如未来必须迁移数据库，需要新增 SQL migration，而不是修改已合并的历史 migration。
