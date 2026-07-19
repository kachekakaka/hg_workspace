# 当前交接与核验状态

核验日期：2026-07-19
唯一权威仓库：`kachekakaka/hg_workspace`

## 已合并基线

Phase 1 已通过 PR #1 合入 `main`：

```text
main merge commit
c68d33b5e1a552a5cc4706515f54b05eb17796d7
```

Phase 1 包含 Docker/FastAPI `/health` 基线、CI、仓库卫生检查、旧工程审计，以及视频质量和 NovelQuick SSR 的无网络纯解析迁移。

## 当前功能分支

```text
phase-2/backend-foundation
base: c68d33b5e1a552a5cc4706515f54b05eb17796d7
```

本分支范围：

- Python `sqlite3` 数据库封装；
- `NNNN_*.sql` 版本化迁移；
- `works`、`episodes`、`media_cache`、`tasks`、`settings` 初始 schema；
- 作品/分集 repository；
- 幂等作品导入和权威分集快照同步；
- 分页、搜索、状态/标签过滤和统计；
- `/api/v1` 作品、详情、分集和导入接口；
- 旧原生 Web 所需的作品、详情、统计、状态只读兼容接口；
- 合成 fixture、迁移幂等、repository、API 和重启持久化测试。

## 重要设计边界

- 不使用 SQLAlchemy、Alembic、Redis、Celery 或 PostgreSQL；
- `episodes` 缺省时保留已有分集，显式数组才执行快照同步；
- 本分支不发起外部内容源请求；
- 不存储或下发 Cookie、Authorization、私钥或长期播放 URL；
- 未实现抓取任务、播放解析、Range 代理、下载、Web 静态页面或 Android；
- Qt/C++、`catalog.pack`、手机伴侣、TV 内置 Server、mDNS 和 WebSocket 不恢复。

## 旧工程输入

旧归档和详细 Review 已审计但没有原样提交：

```text
hg_workspace(3).rar
SHA-256 a0b95437b120ec9ed57a61d5acc04dfa883f8b4362fac12b96f77be667e8bfbf

HG_精简重构方案_Review(1).md
SHA-256 b4cfdb9dae01e744f7586b7283dbd6f4a3129e358684b171d590b1e8314c1fed
```

审计结果见 `docs/LEGACY_SOURCE_AUDIT.md`。

## 后续入口

下一批工作必须先以 fixture 驱动方式迁移旧 catalog/抓取结果到 `WorkImport`，再实现持久化任务 worker；不能把旧 checkpoint JSON 继续当作服务端主库。

每次报告仍必须列出：branch、commit SHA、PR、修改文件、实际命令、结果、CI 状态和未解决问题。
