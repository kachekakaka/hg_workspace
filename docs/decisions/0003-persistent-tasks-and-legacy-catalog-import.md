# ADR 0003：使用 SQLite 持久化单线程任务并纯映射旧 catalog

- 状态：Accepted
- 日期：2026-07-19

## 背景

Phase 2 已建立作品/分集 repository，但旧 catalog 仍是 JSON，抓取和导入仍缺少可恢复的服务端执行边界。第一版不需要 Redis、Celery 或分布式 worker，同时不能把旧脚本的 checkpoint 文件重新变成主库。

## 决策

1. 任务继续使用已有 SQLite `tasks` 表，不引入消息队列。
2. 后端进程内只启动一个工作线程，使用事务原子领取最早的 pending 任务。
3. 任务状态固定为 `pending/running/completed/failed/interrupted`。
4. 服务启动时把遗留 `running` 任务改为 `interrupted`，不把未知完成度伪装成成功。
5. failed/interrupted 任务可以显式 retry。
6. 旧 catalog 导入分成两层：纯 JSON 映射先完整验证，再把标准化 `WorkImport` 写入任务参数。
7. 旧 catalog 的 `source` 字段只代表发现路径，不用作稳定唯一键；API 调用方明确指定稳定 source，默认 `novelquick`。
8. 无分集数组时允许保存来源声明的 `episode_count`；一旦提供分集快照，实际分集数量优先。
9. 本批次不执行网络抓取，不读取任意服务器文件路径，也不处理 Cookie/Authorization。

## 原因

- SQLite 任务与作品数据可以一起备份和审计；
- 单线程避免第一版并发写入复杂度；
- 明确 interrupted 状态能真实反映进程中断；
- 任务参数保存标准化数据，使重试不依赖原始文件仍然存在；
- 作品 upsert 幂等，因此批次中途失败后重试不会重复创建记录；
- 纯映射可使用旧 catalog fixture 测试，不依赖内容源在线状态。

## 影响和限制

- 大型 catalog 会增大 `tasks.params_json`；第一版限制为最多 10000 部，后续可改为受控导入文件表；
- 批次按作品分别提交，失败前已导入的作品会保留，但重试是幂等的；
- 只有一个后端实例可以作为正式部署目标，多实例 worker 不在第一版范围；
- 抓取、播放、代理和下载必须作为后续独立任务类型实现。
