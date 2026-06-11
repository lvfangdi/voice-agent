# Repo Issue: MVP 全链路验收与 runbook

- `issue_id`: VA-005
- `status`: Todo
- `kind`: Execution Issue
- `issue_provider`: repo
- `created_at`: 2026-06-11
- `updated_at`: 2026-06-11
- `parent_master`: VA-002

## Goal

- `goal`: 完成园区访客登记 MVP 全链路集成验收：3 次演示均全链路通过（对话 → 企微推送 → 结束语挂断），且每次从 Agent 首句到 webhook HTTP 200 ≤25 秒。
- `success_criteria`:
  - `docs/test/visitor-registration-mvp-runbook.md` 主路径执行 3 次，均通过
  - 3 次耗时均 ≤25s（硬性 gate）
  - VA-001 ✓ 自然对话样例通过；✗ 机械式样例不出现
  - runbook 脱敏摘要已回写
  - VA-002 Master Exit Criteria checklist 全部勾选

## Scope

- `included`:
  - 全链路集成验证（VA-003 + VA-004 合并验收）
  - 25s 计时实现或手动计时记录（起点：Agent 首句；终点：webhook HTTP 200）
  - 执行并回写 `docs/test/visitor-registration-mvp-runbook.md`
  - 更新 VA-002 / VA-003 / VA-004 `writeback_log`
  - prompt 微调（仅限验收暴露问题的最小修复）
- `excluded`:
  - 新功能开发
  - Twilio / Pipecat Cloud 验收
  - 自动化测试脚本（MVP 手动 runbook）
  - 性能优化超出 25s gate 所需范围

## Acceptance Matrix

- `acceptance_matrix`:

| 类别 | 口径 |
| --- | --- |
| 构建 | `uv run bot.py` 正常 |
| 测试 | runbook 3/3 通过，3/3 ≤25s |
| review | 无机械式对话；企微 5 字段；结束语正确 |
| writeback | runbook + 全部相关 issue writeback 已更新 |

## Execution Contract

- `stop_when`: 3 次演示均全链路通过且 ≤25s；Master Exit Criteria 全部满足；不顺手扩展 MVP 范围。
- `write_scope_limit`:
  - `docs/test/visitor-registration-mvp-runbook.md`
  - `docs/issues/VA-*.md`（writeback_log 段）
  - `bot.py` / `visitor_registration.py`（仅验收暴露问题的最小 prompt 修复）
- `verification_commands`:
  - `docs/test/visitor-registration-mvp-runbook.md` 完整主路径 ×3
  - `uv run ruff check .`（建议，非 blocker）
- `rollback_unit`: 回退至 VA-004 完成态
- `dependencies_blockers`:
  - VA-003 Done
  - VA-004 Done
  - `WECOM_WEBHOOK_URL` 可用
- `follow_up_candidates`:
  - Twilio 电话链路
  - 海康 API 联动
  - MySQL 落库

## Recovery

- `current_issue_state`: Todo
- `recovery_point`: `docs/test/visitor-registration-mvp-runbook.md`
- `next_action`: VA-003、VA-004 完成后执行 runbook

## Orchestration

- `orchestration_mode`: single-issue
- `mode`: implement-no-merge
- `root_goal`: 园区访客语音登记 MVP
- `root_issue`: VA-002
- `verification_policy`: post-integration 权威验证

## Current State

- `current_phase`: verify
- `current_state`: 待 VA-003、VA-004 完成后实施
- `blockers`: 依赖 VA-003、VA-004
- `residual_risks`: LLM 延迟可能导致偶发 >25s

## Writeback Log

（实施后填写）

---

## 附录：25s 计时口径

| 节点 | 定义 |
| --- | --- |
| 起点 T0 | Agent 第一句语音/文本输出时刻（用户 Connect 后 Agent 开始说话） |
| 终点 T1 | 企微 webhook 返回 HTTP 200 时刻 |
| 耗时 | T1 - T0，必须 ≤25s |
| 不含 | 用户拨号振铃、浏览器 Connect 握手 |

## 附录：验收对话脚本（VA-001 ✓ 样例）

```
AI：您好，请问车牌号多少，今天找哪家公司，什么事儿？
用户：沪A12345，来蓝色鲸鱼送货的。
AI：收到，手机号方便留一下吗？
用户：138xxxx1234。
AI：好的！沪A12345，蓝色鲸鱼送货，已通知门卫，请稍等放行。
```

预期：3 轮对话，企微收到 5 字段消息，耗时 ≤25s。
