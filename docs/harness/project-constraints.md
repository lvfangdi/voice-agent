# Project Mechanical Constraints

## 文档定位

本文件登记当前项目的项目级机械约束：哪些工程边界已经变成可执行检查，哪些还只是文档约束，哪些计划后续接入。

它不定义通用 lint 规则，也不预设某个业务项目的架构边界。初始化后，项目维护者需要基于真实代码、架构文档、运行入口和协作规则补齐本文件。

固定原则：

- 没有可执行命令或 gate 时，不得假装 `enforced`
- `enforced` 必须能对应到本地命令、CI、linter、script、test、contract diff、E2E 或 review gate
- `documented` 只表示已有文档规则，不表示机器会拦截
- `partial` 必须说明哪些部分已机械化，哪些仍需人工 review
- 项目专属规则不要写进 base harness 模板本身，先登记到本文件，再按项目选择 linter / script / test / E2E 载体

## 状态枚举

| Status | 含义 |
| --- | --- |
| `enforced` | 已有可执行命令或 gate 会在违反时失败 |
| `partial` | 部分已机械化，仍有人工 review 或后续补齐项 |
| `documented` | 只有文档约束，尚无可执行检查 |
| `planned` | 已决定后续接入，但当前没有规则或命令 |
| `not_applicable` | 当前项目明确不适用 |

## 分类枚举

| Category | 典型内容 |
| --- | --- |
| `architecture` | 分层、依赖方向、目录职责、模块边界 |
| `contract` | API / schema / DTO / OpenAPI / provider-consumer contract |
| `runtime` | 配置、环境变量、日志、指标、trace、启动方式 |
| `verification` | 测试矩阵、E2E、live self-test、构建和验证入口 |
| `docs` | 设计文档、runbook、计划、结果摘要和链接同步 |
| `security` | secret、权限、副作用、脱敏、危险命令 |
| `cross-repo` | provider / consumer / shared truth 分层与同步 |

## 维护循环关联

Maintenance loop 默认扫描本文件，用来判断项目规则是否仍停留在文档层、是否需要建 issue，或是否已具备升级为机械检查的条件。

| Maintenance Tag | 含义 |
| --- | --- |
| `maintenance_candidate` | 维护循环应定期扫描该规则是否漂移，但当前不一定适合机械化 |
| `rule_promotion_candidate` | 重复 review finding 或已有稳定命令，适合评估升级为机械检查 |
| `human_decision_required` | 涉及产品、API、安全、数据或跨团队取舍，需要人类确认后才能修改 |

固定规则：

- maintenance loop 发现 `documented` 规则长期未机械化时，只能报告或建议建 issue，不得自动把它改成 `enforced`。
- repeated review finding 可以升级为 `project-check`、linter、contract diff、E2E 或 harness check，但必须先写清 evidence、目标 `Rule ID`、执行命令、回归验证和回滚方式。
- `rule_promotion_candidate` 只是候选标签，不代表已经允许自动新增检查脚本或 CI。

## 约束登记表

| Rule ID | Category | Rule | Source | Enforcement | Command | Status | Maintenance Tag | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `RUNTIME-001` | `runtime` | 本地开发入口为 `uv run bot.py`，依赖 `.env` 中的 API 密钥 | `README.md` / `AGENTS.md` | manual | `uv run bot.py` | `documented` | `maintenance_candidate` | 首次启动约 20s 下载模型 |
| `RUNTIME-002` | `runtime` | 生产部署走 Pipecat Cloud + `pcc-deploy.toml` + Docker 镜像 | `README.md` / `pcc-deploy.toml` | manual | `uv run pcc deploy` | `documented` | `maintenance_candidate` | 需 Docker Hub 与 `pcc auth login` |
| `ARCH-001` | `architecture` | LLM 适配在 `app/qwen_omni_live_service.py`，bot 编排在 `app/bot.py` | `AGENTS.md` / 源码 | review | — | `documented` | `maintenance_candidate` | 根目录 `bot.py` 为入口 shim；备选 `app/bot_cascade.py` |
| `SECURITY-001` | `security` | `.env`、`credentials.json` 等凭据文件不得提交 | `.gitignore` / `env.example` | gitignore | — | `documented` | `maintenance_candidate` | 示例配置用 `env.example` |
| `VERIFY-001` | `verification` | 尚无自动化测试；本地验证为手动 WebRTC 连接 | `README.md` | manual | `uv run bot.py` + 浏览器 Connect | `documented` | `rule_promotion_candidate` | lint 可用 `uv run ruff check .`，未接入 harness gate |
| `ARCH-002` | `architecture` | 园区业务逻辑不得侵入 `app/qwen_omni_live_service.py` 协议层 | `AGENTS.md` / ExecPlan | review | — | `documented` | `maintenance_candidate` | 业务放 `app/visitor_registration.py` |
| `ARCH-003` | `architecture` | 访客登记业务集中在 `app/visitor_registration.py`；`app/bot.py` 仅做装配 | `AGENTS.md` / ExecPlan | review | — | `documented` | `maintenance_candidate` | 业务代码统一在 `app/`；主流程不引用 `game_content.py` |
| `RUNTIME-004` | `runtime` | 企微 webhook URL 从 `.env` 的 `WECOM_WEBHOOK_URL` 读取，不得硬编码 | `env.example` / VA-004 | manual | — | `documented` | `maintenance_candidate` | MVP 唯一数据出口 |
| `VERIFY-002` | `verification` | MVP 验收 = WebRTC 全链路 + 25s 硬性 gate + 自然对话样例 | `docs/test/visitor-registration-mvp-runbook.md` | manual | runbook 主路径 ×3 | `documented` | `rule_promotion_candidate` | 起点 Agent 首句，终点 webhook HTTP 200 |
| `SECURITY-002` | `security` | `WECOM_WEBHOOK_URL` 等 webhook 凭据不得提交 | `.gitignore` / `env.example` | gitignore | — | `documented` | `maintenance_candidate` | 与 `SECURITY-001` 同类 |

## `project-check` 挂载协议

base harness 不默认生成 `project-check`，也不生成永远 pass 的占位脚本。

当项目已有稳定的项目级机械约束后，可以按需补充：

```text
scripts/project-checks/
  check.sh
  check-architecture.sh
  check-contracts.sh
  check-runtime.sh
  check-docs.sh
```

推荐 Makefile 入口：

```makefile
project-check:
	bash scripts/project-checks/check.sh
```

固定要求：

- 一旦某条规则标记为 `enforced`，`Command` 必须指向真实可执行入口
- `project-check` 可以汇总项目专属检查，但不替代 `make harness-check`
- `make harness-check` 只校验本文件作为登记入口存在且结构完整，不替项目臆造项目规则
- 违反规则时，失败信息应说明违反了哪条 `Rule ID`、参考哪个 `Source`、应运行或修复哪个 `Command`

## 初始化后补齐步骤

1. 从 `AGENTS.md`、目录级 `AGENTS.md`、README、架构文档和现有 Makefile 里提取项目不可违反的规则。
2. 先把规则登记到上方表格，并诚实标注 `Status`。
3. 已有命令或 gate 的规则，补齐 `Enforcement` 和 `Command`。
4. 只有文档约束的规则，保持 `documented`，不要写成 `enforced`。
5. 后续把稳定规则逐步接入 linter、script、test、contract diff、E2E 或 CI。
6. 为每条规则补齐 `Maintenance Tag`，让 maintenance loop 能区分扫描、升级和人工决策边界。
