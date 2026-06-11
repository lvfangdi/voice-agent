# Repo Issue: 园区访客语音登记 — 需求澄清

- `issue_id`: VA-001
- `status`: Done
- `kind`: Requirement Clarification
- `issue_provider`: repo
- `created_at`: 2026-06-11
- `updated_at`: 2026-06-11

## Goal

- `goal`: 澄清园区停车场访客车辆语音登记 MVP 的业务背景、目标流程、采集字段、验收标准与明确边界，为 Master Issue 与 ExecPlan 提供协作真相。
- `success_criteria`:
  - 业务痛点与 AI 自动化目标流程已写清
  - MVP 三项交付目标（全链路、25s 硬性 gate、自然对话）已冻结
  - 5 项采集字段与对话体验标准已定义
  - Non-Goals 9 项已登记，避免实现阶段范围漂移

## Scope

- `included`:
  - 园区停车场入口访客车辆登记场景
  - 目标流程：拨打电话（MVP 用 WebRTC 代替）→ Agent 接听 → 自然中文对话采集 → 企微 webhook 推送 → 保安手动放行
  - MVP 采集字段：车牌号、来访单位、手机号、来访事由、入场时间（系统记录）
  - 对话体验标准（自然对话 vs 机械一问一答）
  - 本地 WebRTC 验收环境
  - 企微 webhook 作为唯一数据出口（MVP 不写 MySQL）
- `excluded`:
  - 海康威视 API 联动抬杆（二期：保安企微审批流成熟后再联动）
  - 白名单实时校验（入口已由海康过滤内部车，Agent 侧无业务价值）
  - 工作时间限制（7×24 运行）
  - 可视化管理后台（日均通话量稳定 >50 次/日后再开发）
  - 门卫查询统计 Agent（独立场景，分开验证）
  - 多语言支持（普通话覆盖 >95% 园区场景）
  - 声纹识别（Caller ID + 车牌已足够）
  - 多租户架构（当前仅 1 个园区 1 个入口）
  - Twilio 电话链路（MVP 仅本地 WebRTC）
  - Pipecat Cloud 部署验收（MVP 不做）
  - `bot-cascade.py` Gemini cascade 路径维护

## Acceptance Matrix

- `acceptance_matrix`:

| 类别 | 口径 |
| --- | --- |
| 构建 | 需求文档可被 Master Issue 与 ExecPlan 直接引用，无未决阻塞项 |
| 测试 | 对话体验 ✓/✗ 样例可作为 runbook 验收参考 |
| review | Non-Goals 与采集字段无歧义 |
| writeback | VA-002 Master Issue 可基于本文档创建 |

## Execution Contract

- `stop_when`: 需求澄清文档完成且用户已确认全部信息；不顺手展开实现设计细节。
- `write_scope_limit`: 仅 `docs/issues/VA-001-*.md` 及 harness 协作文档引用。
- `verification_commands`: 人工 review 本文档字段完整性。
- `rollback_unit`: 删除或回退本 issue 文件。
- `dependencies_blockers`: 无。
- `follow_up_candidates`: VA-002 Master Issue、`.agents/plans/2026-06-11-visitor-registration-mvp.md`

## Recovery

- `current_issue_state`: Done — 需求已全部确认。
- `recovery_point`: 本文档即为恢复点。
- `next_action`: 创建 VA-002 Master Issue 并进入 ExecPlan。

## Orchestration

- `orchestration_mode`: single-issue
- `mode`: plan-only
- `root_goal`: 园区访客语音登记 MVP
- `root_issue`: VA-001
- `goal_state`: clarified
- `goal_unit_roster`: VA-002, VA-003, VA-004, VA-005
- `main_thread`: 人工 + agent 协作
- `threads`: —
- `active_write_leases`: —
- `recent_write_leases`: —
- `branch_refs`: main
- `worktree_refs`: —
- `verification_policy`: 文档 review
- `waiting_on`: —
- `next_check`: VA-002 创建后

## Current State

- `current_phase`: collect
- `current_state`: 需求澄清完成，信息已冻结。
- `title_marker_pending`: false
- `blockers`: 无
- `residual_risks`: 企微消息格式细节在 VA-004 落地时最终确认
- `post_integration_verify_summary`: —
- `goal_level_verification_summary`: —

## Thread Status Log

（无子 thread）

## Writeback Log

### 2026-06-11 - collect

- `result`: pass
- `verification_summary`: 用户已确认业务背景、MVP 目标、字段、Non-Goals、验收环境
- `review_summary`: 无 blocking findings
- `integration_summary`: —
- `post_integration_verify_summary`: —
- `writeback_summary`: 需求澄清文档已写入
- `residual_risks`: 企微消息排版模板待 VA-004 细化
- `next_action`: 推进 VA-002

---

## 附录：业务背景

园区每天有大量车辆进出。内部车辆已录入海康威视门禁系统，可自动识别放行。访客车辆需保安走到车旁人工问询登记，流程低效。

**目标 AI 流程：**

停车场入口张贴电话号码 → 未登记车辆驾驶员拨打（MVP 用浏览器 WebRTC 代替）→ Voice Agent 自动接听 → 自然对话采集必要信息 → 结构化推送保安企微 → 保安确认后远程放行。

## 附录：采集字段

| 字段 | 说明 | 来源 | 示例 |
| --- | --- | --- | --- |
| 车牌号 | 访客车辆牌照 | 对话采集 | 沪A12345 |
| 来访单位 | 园区内目标公司名称，自由文本 | 对话采集 | 蓝色鲸鱼科技 |
| 手机号 | 访客联系电话 | 对话采集 | 138xxxx1234 |
| 来访事由 | 送货、拜访、面试等 | 对话采集 | 送货 |
| 入场时间 | 系统记录推送时刻 | 系统自动 | 2025-04-13 14:30 |

## 附录：对话体验标准

### ✗ 机械式一问一答（不可接受）

```
AI：您好，请问您的车牌号是多少？
用户：沪A12345
AI：好的，请问您来访哪家公司？
用户：蓝色鲸鱼
AI：请问您来访的事由是？
用户：送货
AI：请问您的手机号？
用户：138xxxx1234
AI：请问您预计停留多久？
（全程 6 轮对话，约 45 秒）
```

### ✓ 自然对话（期望效果）

```
AI：您好，请问车牌号多少，今天找哪家公司，什么事儿？
用户：沪A12345，来蓝色鲸鱼送货的。
AI：收到，手机号方便留一下吗？
用户：138xxxx1234。
AI：好的！沪A12345，蓝色鲸鱼送货，已通知门卫，请稍等放行。
（全程 3 轮对话，约 15 秒）
```

## 附录：MVP 交付目标

1. **全链路跑通**：浏览器 Connect → Agent 接听 → 自然对话采集 → 企微 webhook 推送完整访客消息。
2. **25 秒硬性验收**：从 Agent 开始说话到企微消息发出（不含振铃），runbook 记录耗时，超时视为未通过。
3. **Human Friendly**：对话必须像真人门卫，参考上方 ✓ 样例。
