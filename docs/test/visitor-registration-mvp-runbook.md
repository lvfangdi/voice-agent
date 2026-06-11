# 园区访客登记 MVP — 测试 Runbook

本 runbook 用于验收 VA-002 Master Issue 全链路：WebRTC 对话采集 → 企微推送 → 结束语挂断，含 25s 硬性 gate。

## 当前验证结果

- 记录时间：2026-06-11
- 记录目录：`docs/test/`
- 本轮任务性质：MVP 全链路验收（VA-005）
- 当前结论：`未执行`
- 自动化入口：无（手动验收）
- 对应计划 / issue：VA-002 Master、VA-005 Execution、[`.agents/plans/2026-06-11-visitor-registration-mvp.md`](../../.agents/plans/2026-06-11-visitor-registration-mvp.md)
- 结果说明：runbook 已创建，待 VA-003、VA-004 完成后执行

### 本次执行结果

- 执行时间：未执行
- 执行目录：未执行
- 本次结论：`未执行`
- 影响范围：本地 bot 进程、企微 webhook（发送访客登记消息）
- 清理结果：未执行
- 敏感信息处理：未写入真实凭据、webhook URL、手机号全号、原始 HTTP 响应

### 当前步骤状态

| 步骤 | 结果 | 备注 |
| --- | --- | --- |
| 前置检查 | 未执行 |  |
| 主路径验证（第 1 次） | 未执行 |  |
| 主路径验证（第 2 次） | 未执行 |  |
| 主路径验证（第 3 次） | 未执行 |  |
| 清理 | 未执行 |  |

## 目标

- 验证目标：园区访客语音登记 MVP 全链路
- 成功标准：
  - 3 次演示均全链路通过（对话 → 企微 5 字段 → 结束语挂断）
  - 3 次耗时均 ≤25s（Agent 首句 → webhook HTTP 200）
  - 自然对话 ✓ 样例通过，不出现 ✗ 机械式逐字段追问
- 本 runbook 供 agent 或工程师直接执行，不是泛化 QA 说明

## 执行副作用

- 可能写入的本地文件：无（仅 issue / runbook 回写）
- 可能访问的服务：DashScope Qwen Omni API、企微 webhook
- 可能创建的临时数据：企微群中的访客登记通知消息（3 条）
- 明确不会触达的范围：海康 API、MySQL、Twilio 电话、Pipecat Cloud
- 执行前必须先确认 `WECOM_WEBHOOK_URL` 指向测试群，避免骚扰生产保安群

## 前置条件

1. 当前工作目录：仓库根目录
2. 当前分支：`main`（或 VA-005 实施分支）
3. 必需命令：`uv`、浏览器
4. 必需配置：
   - `.env` 含 `DASHSCOPE_API_KEY`（有效）
   - `.env` 含 `WECOM_WEBHOOK_URL`（有效，指向测试企微群）
5. 必需测试环境：本地可访问 DashScope 与企微 webhook

## 测试变量 / 初始化

```powershell
# Windows PowerShell
Set-Location C:\Users\o0oii\project\pcc-gemini-twilio

# 确认环境变量存在（不打印真实值）
if (-not $env:DASHSCOPE_API_KEY) { Write-Error "DASHSCOPE_API_KEY missing" }
if (-not $env:WECOM_WEBHOOK_URL) { Write-Error "WECOM_WEBHOOK_URL missing" }

Write-Output "REPO_ROOT=$(Get-Location)"
Write-Output "RUN_ID=test-run-$(Get-Date -Format 'yyyyMMddHHmmss')"
```

预期结果：

- 初始化命令成功退出
- 环境变量存在确认，不输出敏感值

## 主路径

### 1. 前置检查

```powershell
uv run bot.py
```

在另一个终端或后台运行后：

- 打开浏览器 http://localhost:7860
- 确认页面可加载，Connect 按钮可用
- 首次启动约 20s 下载模型属正常

预期结果：

- bot 进程无报错退出
- WebRTC 页面可访问

### 2. 执行验证（执行 3 次，每次记录耗时）

**计时口径：**

- T0 = Agent 第一句输出时刻（Connect 后 Agent 开始说话）
- T1 = 企微 webhook 返回成功（观察企微群消息出现时刻，或日志中 HTTP 200）
- 耗时 = T1 - T0，必须 ≤25s

**对话脚本（VA-001 ✓ 自然对话样例）：**

| 轮次 | 角色 | 内容 |
| --- | --- | --- |
| 1 | AI | 您好，请问车牌号多少，今天找哪家公司，什么事儿？ |
| 1 | 用户 | 沪A12345，来蓝色鲸鱼送货的。 |
| 2 | AI | 收到，手机号方便留一下吗？ |
| 2 | 用户 | 138xxxx1234。 |
| 3 | AI | 好的！沪A12345，蓝色鲸鱼送货，已通知门卫，请稍等放行。 |

**每次验证检查项：**

| 检查项 | 通过标准 |
| --- | --- |
| 对话轮次 | ≤4 轮（非机械式 6 轮） |
| 字段采集 | 车牌、单位、事由、手机号正确 |
| 企微消息 | 5 字段齐全：车牌号、来访单位、手机号、来访事由、入场时间 |
| 结束语 | 含「已通知门卫，请稍等放行」 |
| 耗时 | ≤25s |
| 通话 | Agent 播报结束语后挂断 |

**记录模板（每次填写，脱敏）：**

| 次数 | 耗时(s) | 对话轮次 | 企微 5 字段 | 结束语 | 结论 |
| --- | --- | --- | --- | --- | --- |
| 1 |  |  |  |  |  |
| 2 |  |  |  |  |  |
| 3 |  |  |  |  |  |

预期结果：

- 3/3 次通过
- 3/3 次 ≤25s

### 3. 失败样例检查（可选，确认不出现）

若 Agent 出现以下 ✗ 机械式模式，视为未通过：

```
AI：您好，请问您的车牌号是多少？
（逐字段单独追问，6 轮以上）
```

### 4. 清理

```powershell
# 停止 bot 进程（Ctrl+C 或关闭终端）
```

预期结果：

- bot 进程已停止
- 无残留监听端口

## 失败处理

| 失败点 | 停止条件 | 记录方式 | 恢复 / 重跑方式 |
| --- | --- | --- | --- |
| 环境变量缺失 | 停止 | runbook 记 blocker | 补齐 `.env` 后重跑 |
| bot 启动失败 | 停止 | 记错误摘要 | 检查 `DASHSCOPE_API_KEY` |
| 机械式对话 | 停止 | 记对话轮次与内容摘要 | 调整 prompt（VA-003）后重跑 |
| 企微推送失败 | 停止 | 记 HTTP 状态（脱敏） | 检查 `WECOM_WEBHOOK_URL`（VA-004） |
| 耗时 >25s | 停止 | 记耗时与轮次 | prompt 优化或网络排查 |
| 字段缺失 | 停止 | 记缺失字段 | 调整采集逻辑后重跑 |

## 结果回写

执行完成后，回写本文前部的 `当前验证结果`、`本次执行结果` 和 `当前步骤状态`，并更新：

- `docs/issues/VA-005-exec-mvp-acceptance-runbook.md` → `writeback_log`
- `docs/issues/VA-002-【Master】visitor-registration-mvp.md` → Master Exit Criteria checklist

固定规则：

- 已执行步骤写真实脱敏结果
- 未执行写 `未执行` 或 `blocker`
- 不写入真实 webhook URL、完整手机号、原始 HTTP 响应
