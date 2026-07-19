# 当前交接与核验状态

核验日期：2026-07-19  
唯一权威仓库：`kachekakaka/hg_workspace`

## 已验证的 Phase 1 起点

在建立本分支前，GitHub 默认分支为 `main`，最新可验证提交为：

```text
be04662a13186f53c450c3429d3d45f0172f0d52
```

当时仓库只正向验证到以下文件：

```text
docs/HG_REFACTOR_PLAN.md
docs/NEXT_WINDOW_PROMPT.md
```

根 `README.md` 不存在；未发现 PR；该提交没有可验证的 commit status，PR 触发的 workflow runs 也为空。

## 本分支范围

分支：`phase-1/repository-bootstrap`

本分支只建立：

- 根 README、忽略规则和开发入口；
- Docker 化 FastAPI `/health` 骨架；
- 最小单元测试；
- 仓库卫生和明显 secret 检查；
- 基础 GitHub Actions；
- 架构决策记录。

## 旧源码迁移状态

**未执行。** 当前聊天没有可供读取的 `hg_workspace(1).rar` 和 `HG_精简重构方案_Review.md` 原文件，因此：

- 没有读取或迁移旧 Python、Web、Android、Qt/C++ 源码；
- 没有对旧源码完成 secret scan；
- 没有删除旧压缩包中的构建产物，因为这些内容尚未进入 GitHub；
- 交接文档中描述的旧文件只作为后续调查线索。

在用户重新上传旧文件后，必须先生成清单、哈希和 secret scan 报告，再选择性迁移；不得把压缩包原样提交。

## 本地作者环境验证

本分支文件在一个独立临时目录中验证。作者环境没有 Docker，也无法直接解析 `github.com`，因此验证边界如下：

| 验证 | 状态 |
|---|---|
| `(cd backend && PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider)` | 通过：`1 passed in 0.68s` |
| `PYTHONPYCACHEPREFIX=/tmp/hg_pycache python3 -m compileall -q backend/app backend/tests scripts` | 通过 |
| `python3 scripts/check_repository.py` | 通过：`repository hygiene check passed` |
| PyYAML 解析 `compose.yaml` 与 `.github/workflows/ci.yml` | 通过 |
| 本机 Uvicorn + `GET /health` smoke test | 通过：HTTP 200，响应 `{"status":"ok","service":"hg-backend"}` |
| `docker compose config` | 未运行：作者环境没有 Docker |
| Docker image build / 容器内 health smoke test | 未运行：作者环境没有 Docker |
| 旧源码 secret scan | 未运行：旧源码文件不可用 |
| Android 构建或真机测试 | 不在本分支范围，未运行 |

CI 的实际状态只能以 draft PR 创建后的 GitHub Actions 记录为准。
