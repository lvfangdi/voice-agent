# Repo Issue: 【Master】园区访客语音登记 MVP

- `issue_id`: VA-002
- `status`: In Progress
- `kind`: Master Issue
- `issue_provider`: repo
- `created_at`: 2026-06-11
- `updated_at`: 2026-06-11

## Goal

- `goal`: 交付园区访客车辆语音登记 MVP：用户通过 WebRTC 连接 Agent，在自然中文对话中完成信息采集，25 秒内推送完整访客消息至保安企微 webhook，Agent 告知「已通知门卫，请稍等放行」后结束通话。
- `success_criteria`:
  - 全链路跑通：Connect → 对话采集 → 企微推送 → 结束语挂断
  - 25s 硬性 gate：Agent 首句输出到 webhook HTTP 200，runbook 记录且 ≤25s
  - 自然对话样例（VA-001 ✓ 脚本）验收通过
  - 企微消息含 5 项字段且排版可读
  - 完全替换 Two Truths and a Lie 游戏主流程

## Scope

- `included`:
  - 替换 `bot.py` 业务装配，移除 `game_content.py` 主流程依赖
  - 新增 `visitor_registration.py`（prompt、字段结构化、企微推送）
  - 中文自然对话 prompt 与多字段合并询问
  - 企微 webhook 推送（`WECOM_WEBHOOK_URL` 从 `.env` 读取）
  - 本地 WebRTC 验收与 runbook
  - harness 文档：ExecPlan、Execution Issues、project-constraints 更新
- `excluded`:
  - 海康抬杆 API、白名单校验、工作时间限制
  - 管理后台、门卫统计 Agent、多语言、声纹、多租户
  - MySQL 落库（MVP 仅企微）
  - Twilio 电话、Pipecat Cloud 部署验收
  - `bot-cascade.py` 维护
  - 来访单位园区名单校验（自由文本）

## Acceptance Matrix

- `acceptance_matrix`:

| 类别 | 口径 |
| --- | --- |
| 构建 | `uv run bot.py` 可启动，无 game 逻辑残留引用 |
| 测试 | `docs/test/visitor-registration-mvp-runbook.md` 3 次演示全通过且均 ≤25s |
| review | prompt 符合自然对话标准；企微消息 5 字段齐全；结束语正确 |
| writeback | 各 Execution Issue `writeback_log` 与 runbook 脱敏摘要已更新 |

## Execution Contract

- `stop_when`: Master Exit Criteria 全部满足：VA-003、VA-004、VA-005 均为 Done，runbook 3/3 通过。
- `write_scope_limit`: `bot.py`、`visitor_registration.py`、`env.example`、harness 文档；不改 `qwen_omni_live_service.py` 协议层。
- `verification_commands`:
  - `uv run bot.py` + 浏览器 http://localhost:7860 Connect
  - `docs/test/visitor-registration-mvp-runbook.md` 主路径
  - `uv run ruff check .`（非 blocker，建议执行）
- `rollback_unit`: 回退至 harness 初始化 commit 前的 `bot.py` / `game_content.py` 状态。
- `dependencies_blockers`:
  - `DASHSCOPE_API_KEY` 已配置
  - `WECOM_WEBHOOK_URL` 已配置且可访问
- `follow_up_candidates`:
  - 海康抬杆 API 联动（二期）
  - Twilio 电话链路
  - MySQL 落库与统计后台

## Recovery

- `current_issue_state`: In Progress — VA-003 代码完成；VA-004 代码完成，待 webhook 配置与联调
- `recovery_point`: `.agents/plans/2026-06-11-visitor-registration-mvp.md`
- `next_action`: 配置 `WECOM_WEBHOOK_URL`，执行 VA-005 runbook

## Orchestration

- `orchestration_mode`: master-inventory
- `mode`: implement-no-merge
- `root_goal`: 园区访客语音登记 MVP
- `root_issue`: VA-002
- `goal_state`: planned
- `goal_unit_roster`:
  - VA-003: 自然对话 prompt 与流程（无推送）
  - VA-004: 企微 webhook 推送
  - VA-005: 全链路验收与 runbook
- `main_thread`: 单 thread 串行推进
- `threads`: —
- `active_write_leases`: —
- `recent_write_leases`: —
- `branch_refs`: main
- `worktree_refs`: —
- `verification_policy`: 每 slice 完成后局部验证；VA-005 做 post-integration 验证
- `waiting_on`: —
- `next_check`: VA-003 开始后

## Current State

- `current_phase`: implement
- `current_state`: VA-003/004 代码已落地；待 webhook 配置与 VA-005 验收
- `title_marker_pending`: false
- `blockers`: 无
- `residual_risks`: 25s gate 依赖 Qwen 响应延迟与网络；需在 VA-005 实测
- `post_integration_verify_summary`: 未执行
- `goal_level_verification_summary`: 未执行

## Thread Status Log

（无子 thread）

## Writeback Log

### 2026-06-11 - freeze

- `result`: pass
- `verification_summary`: VA-001 需求已确认；Master / ExecPlan / Execution 拆分完成
- `review_summary`: 无 blocking findings
- `integration_summary`: —
- `post_integration_verify_summary`: —
- `writeback_summary`: Master Issue 与 execution roster 已建立
- `residual_risks`: 实现阶段需关注 25s 实测
- `next_action`: 开始 VA-003

---

## Master Exit Criteria

- [x] VA-003 Done（代码）：自然对话 prompt 与 `submit_visitor` 已落地；WebRTC 对话待人工验收
- [ ] VA-004 Done：企微推送含 5 项字段（blocked：`WECOM_WEBHOOK_URL` 未配置）
- [ ] VA-005 Done：全链路 3 次演示均通过且 ≤25s
- [ ] `game_content.py` 不再被 `bot.py` 主流程引用
- [ ] runbook 脱敏摘要已回写

## Execution Issue 清单

| Issue ID | 标题 | 状态 | 依赖 |
| --- | --- | --- | --- |
| VA-003 | 自然对话 prompt 与访客登记流程 | Todo | VA-001 |
| VA-004 | 企微 webhook 推送 | Todo | VA-003 |
| VA-005 | MVP 全链路验收与 runbook | Todo | VA-004 |
