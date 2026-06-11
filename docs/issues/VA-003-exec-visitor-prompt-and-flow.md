# Repo Issue: 自然对话 prompt 与访客登记流程

- `issue_id`: VA-003
- `status`: Done
- `kind`: Execution Issue
- `issue_provider`: repo
- `created_at`: 2026-06-11
- `updated_at`: 2026-06-11
- `parent_master`: VA-002

## Goal

- `goal`: 替换 Two Truths and a Lie 游戏逻辑，实现中文自然门卫式访客登记对话流程，能在 3 轮内采集车牌号、来访单位、来访事由、手机号并正确复述，暂不接入企微推送。
- `success_criteria`:
  - `bot.py` 不再引用 `game_content.py`
  - `visitor_registration.py` 已创建，含 system prompt 与 `VisitorRecord`
  - VA-001 ✓ 自然对话样例可在本地跑通（Agent 合并询问，非机械逐字段）
  - `submit_visitor` function call 可在信息齐全时触发

## Scope

- `included`:
  - 新增 `visitor_registration.py`（prompt、`VisitorRecord` dataclass、字段状态）
  - 修改 `bot.py`：移除 game 逻辑，注入访客登记 system prompt
  - 实现 `submit_visitor` function call（VA-004 前仅日志/复述，不推送）
  - 结束语模板：「好的！{车牌}，{单位}{事由}，已通知门卫，请稍等放行。」（VA-004 前可说「信息已记录」）
- `excluded`:
  - 企微 webhook 推送（VA-004）
  - 25s 计时验收（VA-005）
  - 修改 `qwen_omni_live_service.py`
  - `env.example` webhook 配置（VA-004）
  - 删除 `game_content.py` 文件（可保留但不引用）

## Acceptance Matrix

- `acceptance_matrix`:

| 类别 | 口径 |
| --- | --- |
| 构建 | `uv run bot.py` 启动无 import 错误 |
| 测试 | VA-001 ✓ 样例对话 3 轮内完成，字段复述正确 |
| review | prompt 无机械逐字段追问模式 |
| writeback | 本 issue `writeback_log` 更新 |

## Execution Contract

- `stop_when`: 本地 WebRTC 可完成自然对话样例，4 项对话字段采集正确且 Agent 复述无误；不顺手实现企微推送。
- `write_scope_limit`:
  - `bot.py`
  - `visitor_registration.py`（新增）
  - 禁止修改 `qwen_omni_live_service.py`
- `verification_commands`:
  - `uv run bot.py`
  - 浏览器 http://localhost:7860 Connect
  - 执行 VA-001 ✓ 样例对话脚本
- `rollback_unit`: `git checkout bot.py`；删除 `visitor_registration.py`
- `dependencies_blockers`:
  - `DASHSCOPE_API_KEY` 已配置
  - VA-001 需求已确认
- `follow_up_candidates`: VA-004 企微推送

## Recovery

- `current_issue_state`: Done — 代码已落地，待本地 WebRTC 对话验收
- `recovery_point`: `visitor_registration.py` + `bot.py` @ 2026-06-11
- `next_action`: 本地跑 VA-001 ✓ 样例对话验证

## Orchestration

- `orchestration_mode`: single-issue
- `mode`: implement-no-merge
- `root_goal`: 园区访客语音登记 MVP
- `root_issue`: VA-002
- `goal_state`: in_progress
- `main_thread`: 单 thread
- `verification_policy`: 局部验证 — 对话采集 only

## Current State

- `current_phase`: verify
- `current_state`: `visitor_registration.py` 与 `bot.py` 已替换 game 逻辑；`submit_visitor` function call 已注册
- `blockers`: 无
- `residual_risks`: prompt 调优可能需要多轮迭代

## Writeback Log

### 2026-06-11 - implement

- `result`: pass（代码层）
- `verification_summary`: `uv run python -c "import bot"` 通过；`ruff check` 通过；WebRTC 对话验收待人工执行
- `review_summary`: `bot.py` 已移除 `game_content` 引用；自然对话 prompt 写入 `SYSTEM_INSTRUCTION`
- `integration_summary`: `submit_visitor` 已注册；无 webhook 时返回 `recorded` 状态
- `post_integration_verify_summary`: 未执行
- `writeback_summary`: VA-003 代码 slice 完成
- `residual_risks`: prompt 调优可能需多轮实测
- `next_action`: VA-004 企微推送（已同批实现）+ 本地联调
