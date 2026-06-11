# Repo Issue: 企微 webhook 推送

- `issue_id`: VA-004
- `status`: In Progress
- `kind`: Execution Issue
- `issue_provider`: repo
- `created_at`: 2026-06-11
- `updated_at`: 2026-06-11
- `parent_master`: VA-002

## Goal

- `goal`: 在 VA-003 对话流程基础上，实现访客信息结构化与企微 webhook 推送，消息含 5 项字段（含系统记录的入场时间）。
- `success_criteria`:
  - `submit_visitor` 触发后 POST 企微 webhook 成功（HTTP 200）
  - 企微群收到 markdown 消息，5 字段齐全且可读
  - `WECOM_WEBHOOK_URL` 从 `.env` 读取，`env.example` 已补充说明
  - 推送成功后再播报结束语并挂断

## Scope

- `included`:
  - `visitor_registration.py` 增加 `push_to_wecom()` 函数
  - 入场时间 `datetime.now()` 在推送前自动记录
  - 企微 markdown 消息模板（5 字段）
  - `env.example` 增加 `WECOM_WEBHOOK_URL=`
  - `bot.py` 集成：function call 回调中调用推送
  - webhook 失败时 Agent 提示「系统繁忙，请稍后再拨或联系门卫」
- `excluded`:
  - 25s 硬性计时验收（VA-005）
  - MySQL 落库
  - 企微消息卡片 / 审批流
  - 保安确认回传通道
  - 修改 `qwen_omni_live_service.py`

## Acceptance Matrix

- `acceptance_matrix`:

| 类别 | 口径 |
| --- | --- |
| 构建 | `uv run bot.py` 启动正常，`WECOM_WEBHOOK_URL` 从环境读取 |
| 测试 | 完成一次对话后企微群可见 5 字段消息 |
| review | webhook URL 未硬编码、未出现在提交版文档 |
| writeback | 本 issue `writeback_log` 更新 |

## Execution Contract

- `stop_when`: runbook 可见完整企微消息，5 字段齐全；不顺手做 25s 批量验收。
- `write_scope_limit`:
  - `visitor_registration.py`
  - `bot.py`（推送集成）
  - `env.example`
- `verification_commands`:
  - `uv run bot.py` + Connect + 完成样例对话
  - 人工检查企微群消息
- `rollback_unit`: 移除 `push_to_wecom()` 调用，保留 VA-003 对话能力
- `dependencies_blockers`:
  - VA-003 Done
  - `WECOM_WEBHOOK_URL` 已配置且可用
- `follow_up_candidates`: VA-005 全链路验收

## Recovery

- `current_issue_state`: In Progress — `push_to_wecom()` 已实现，待配置 `WECOM_WEBHOOK_URL` 后联调
- `recovery_point`: `visitor_registration.py` `push_to_wecom` @ 2026-06-11
- `next_action`: 用户在 `.env` 填入 `WECOM_WEBHOOK_URL` 后执行一次全链路推送验证

## Orchestration

- `orchestration_mode`: single-issue
- `mode`: implement-no-merge
- `root_goal`: 园区访客语音登记 MVP
- `root_issue`: VA-002
- `verification_policy`: 局部验证 — 推送成功即可

## Current State

- `current_phase`: verify
- `current_state`: 代码已集成；`.env` 中 `WECOM_WEBHOOK_URL` 尚未配置
- `blockers`: `WECOM_WEBHOOK_URL` 缺失，无法完成企微推送验收
- `residual_risks`: 企微 webhook 限频或网络延迟

## Writeback Log

### 2026-06-11 - implement

- `result`: partial
- `verification_summary`: `push_to_wecom()` 与 markdown 模板已实现；`env.example` 已补充；`.env` 中 webhook URL 未配置，推送未实测
- `review_summary`: webhook URL 从环境变量读取，未硬编码
- `integration_summary`: `submit_visitor_handler` 在推送成功/失败后返回对应 status
- `post_integration_verify_summary`: 未执行
- `writeback_summary`: VA-004 代码完成，验收 blocked on config
- `residual_risks`: 需用户补充 `WECOM_WEBHOOK_URL`
- `next_action`: 配置后本地全链路验证

---

## 附录：企微消息模板

```markdown
## 访客登记通知
- **车牌号**：沪A12345
- **来访单位**：蓝色鲸鱼科技
- **手机号**：138xxxx1234
- **来访事由**：送货
- **入场时间**：2026-06-11 14:30
```
