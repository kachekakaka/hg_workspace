# 当前交接与核验状态

核验日期：2026-07-19  
唯一权威仓库：`kachekakaka/hg_workspace`

## 已验证的 Phase 1 起点

建立本分支前，GitHub 默认分支为 `main`，最新可验证提交为：

```text
be04662a13186f53c450c3429d3d45f0172f0d52
```

当时仓库只包含：

```text
docs/HG_REFACTOR_PLAN.md
docs/NEXT_WINDOW_PROMPT.md
```

根 `README.md` 不存在；未发现 PR；该提交没有可验证的 status checks。

## 本分支

```text
phase-1/repository-bootstrap
```

本分支建立：

- 根 README、忽略规则和 Docker 开发入口；
- FastAPI `/health` 骨架；
- 单元测试；
- 仓库卫生和明显 secret 检查；
- GitHub Actions；
- 架构决策、旧工程审计和详细 Review；
- 两组经过重写与测试的纯迁移逻辑：视频质量选择、SSR 分集/播放器信息解析。

## 旧源码核验状态

用户重新提供的文件已经读取：

```text
hg_workspace(3).rar
SHA-256 a0b95437b120ec9ed57a61d5acc04dfa883f8b4362fac12b96f77be667e8bfbf

HG_精简重构方案_Review(1).md
SHA-256 b4cfdb9dae01e744f7586b7283dbd6f4a3129e358684b171d590b1e8314c1fed
```

已完成 RAR 元数据清单、生成物分类、敏感文件名扫描、明文凭据模式扫描和迁移矩阵。结果见 `docs/LEGACY_SOURCE_AUDIT.md`。

重要边界：

- 压缩包、旧 APK、DLL、EXE、日志和缓存没有提交；
- 没有把“未命中正则”写成绝对安全保证；
- Cookie/Authorization 相关代码没有进入生产路径；
- 抓取、Web、Android 和 SQLite 业务仍未完成；
- Qt/C++、手机伴侣、TV Server、mDNS、WebSocket 和 `catalog.pack` 明确不迁移。

## 验证要求

每次后续报告都必须列出：branch、commit SHA、PR、修改文件、实际执行命令、结果、CI 状态和未解决问题。未执行或失败的验证不得写成成功。
