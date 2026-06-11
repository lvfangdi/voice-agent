# Voice Agent

园区停车场**访客车辆语音登记** Agent。基于 [Pipecat](https://docs.pipecat.ai/) 构建，fork 自上游 [daily-co/pcc-gemini-twilio](https://github.com/daily-co/pcc-gemini-twilio)，LLM 已切换为 DashScope **Qwen3-Omni Realtime**（音频进 / 音频出）。

驾驶员通过电话或 WebRTC 与门卫式 AI 自然对话，采集车牌、来访单位、事由与手机号后，经企微 webhook 通知保安放行。MVP 验收以本地 WebRTC 为主；生产路径为 Twilio + Pipecat Cloud。

## 项目状态

| 项 | 说明 |
| --- | --- |
| 阶段 | 访客登记 MVP 实施中（VA-003 / VA-004 已实现，VA-005 验收中） |
| 本地调试 | `uv run bot.py` → http://localhost:7860/client |
| 生产部署 | Pipecat Cloud + Twilio（见 `pcc-deploy.toml`、`Dockerfile`） |
| Master Issue | [`docs/issues/VA-002-【Master】visitor-registration-mvp.md`](docs/issues/VA-002-【Master】visitor-registration-mvp.md) |
| 验收 runbook | [`docs/test/visitor-registration-mvp-runbook.md`](docs/test/visitor-registration-mvp-runbook.md) |

## 代码结构

业务代码统一放在 `app/` 目录；仓库根目录仅保留 `bot.py` 入口 shim（供 Pipecat Cloud 与本地 `uv run bot.py` 使用）。

```
bot.py                              # 入口 shim → app.bot
app/
  visitor_registration.py           # 业务：prompt、字段校验、submit_visitor、企微推送
  bot.py                            # 编排骨架：Pipeline、transport、function handler
  qwen_omni_live_service.py         # LLM 协议层：Qwen Omni Realtime WebSocket 适配
  bot_cascade.py                    # 遗留：ASR + LLM + TTS 级联路径（非主路径）
  game_content.py                   # 遗留：上游游戏内容（仅 bot_cascade 引用）
```

业务与协议分层：改对话逻辑优先动 `app/visitor_registration.py` 与 `app/bot.py`；改模型协议才动 `app/qwen_omni_live_service.py`。

## 环境要求

- Python 3.10+
- [uv](https://docs.astral.sh/uv/getting-started/installation/) 包管理器

### 服务与密钥

| 服务 | 用途 | 必需 |
| --- | --- | --- |
| [DashScope](https://dashscope.aliyun.com/) | Qwen3-Omni Realtime | 是 |
| 企微群机器人 Webhook | 访客登记推送给保安 | 是（MVP） |
| [Twilio](https://www.twilio.com/try-twilio) | 生产电话接入 | 部署时需要 |
| Google Gemini / STT / TTS | 仅 `app/bot_cascade.py` 遗留路径 | 否 |

## 快速开始

### 1. 克隆与依赖

```bash
git clone https://github.com/lvfangdi/voice-agent.git
cd voice-agent
uv sync
```

### 2. 配置环境变量

```bash
cp env.example .env
```

编辑 `.env`，至少填写：

```ini
DASHSCOPE_API_KEY=          # DashScope API Key
WECOM_WEBHOOK_URL=          # 企微群机器人 Webhook
```

生产部署时还需 Twilio 相关项；若运行遗留级联路径，另需 `GOOGLE_API_KEY` 与 `credentials.json`：

```bash
uv run python -m app.bot_cascade
```

### 3. 本地运行

```bash
uv run bot.py
```

浏览器打开 **http://localhost:7860/client**，点击 Connect 开始对话。

> 首次启动可能需约 20 秒，Pipecat 会下载 VAD 等依赖模型。

### 4. 本地验收要点

- 自然门卫式中文，3～4 轮内收齐四项信息
- 调用 `submit_visitor` 后企微收到登记消息
- 全链路目标 ≤ 25s（详见 runbook）

## 生产部署

将本地 bot 发布到 Pipecat Cloud，由 Twilio 将电话媒体流接入云端 Agent。

### 前置条件

1. 注册 [Pipecat Cloud](https://pipecat.daily.co/sign-up)
2. 安装 [Docker](https://www.docker.com/)，注册 [Docker Hub](https://hub.docker.com/) 并 `docker login`
3. 登录 Pipecat Cloud CLI：

   ```bash
   uv run pcc auth login
   ```

### 配置 Twilio

1. [购买带语音能力的号码](https://help.twilio.com/articles/223135247-How-to-Search-for-and-Buy-a-Twilio-Phone-Number-from-Console)
2. 查询组织名：`pcc organizations list`
3. 创建 [TwiML Bin](https://help.twilio.com/articles/360043489573-Getting-started-with-TwiML-Bins)：

   ```xml
   <?xml version="1.0" encoding="UTF-8"?>
   <Response>
   <Connect>
      <Stream url="wss://api.pipecat.daily.co/ws/twilio">
         <Parameter name="_pipecatCloudServiceHost"
            value="AGENT_NAME.ORGANIZATION_NAME"/>
      </Stream>
   </Connect>
   </Response>
   ```

   将 `AGENT_NAME.ORGANIZATION_NAME` 替换为实际 agent 与组织名（例如 `pcc-gemini-twilio.industrious-purple-cat-123`）。

4. 在 Twilio 控制台将该 TwiML Bin 绑定到电话号码（Phone Numbers → Configure → A call comes in → TwiML Bin）

### 配置部署清单

编辑 `pcc-deploy.toml`，更新 Docker 镜像地址：

```ini
agent_name = "pcc-gemini-twilio"
image = "YOUR_DOCKERHUB_USERNAME/pcc-gemini-twilio:0.1"
secret_set = "pcc-gemini-twilio-secrets"

[scaling]
min_agents = 1
```

### 上传密钥、构建与发布

```bash
uv run pcc secrets set pcc-gemini-twilio-secrets --file .env
uv run pcc docker build-push
uv run pcc deploy
```

部署完成后，拨打已配置的 Twilio 号码即可接入 bot。

## 协作与质量

本仓库使用**最小 harness** 管理需求、计划与验收（`issue-provider=repo`，issue 前缀 `VA`）。

| 主题 | 入口 |
| --- | --- |
| 协作总入口 | [`AGENTS.md`](AGENTS.md) |
| 控制面 / Issue Workflow | [`docs/harness/`](docs/harness/) |
| 仓库内 issue | [`docs/issues/`](docs/issues/) |
| 项目级机械约束 | [`docs/harness/project-constraints.md`](docs/harness/project-constraints.md) |
| 计划协议 | [`.agents/PLANS.md`](.agents/PLANS.md) |
| 当前 ExecPlan | [`.agents/plans/2026-06-11-visitor-registration-mvp.md`](.agents/plans/2026-06-11-visitor-registration-mvp.md) |

**验证 harness 结构（Windows PowerShell）：**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\harness\check.ps1
```

**本地 lint：**

```bash
uv run ruff check .
```

## 延伸阅读

- [Pipecat 文档](https://docs.pipecat.ai/)
- [Twilio WebSocket 自定义参数](https://docs.pipecat.ai/guides/telephony/twilio-websockets#custom-parameters-with-twiml)
- [Pipecat Discord 社区](https://discord.gg/pipecat)

---

## 技术选型

以下记录本项目的核心取舍，便于后续维护与扩展时保持同一套前提。

### 语音流水线：Pipecat 二次开发

选择基于 **Pipecat** 在上游示例上二次开发，而不是：

| 路径 | 未选原因（简述） |
| --- | --- |
| 自研流水线 | 需自行处理 VAD、打断、帧调度、媒体桥接与 telephony 集成，迭代成本高 |
| [LiveKit Agents](https://docs.livekit.io/agents/) | 生态与部署模型不同，与现有 Pipecat Cloud + Twilio 路径不匹配 |
| 商业 SaaS（VAPI、Retell 等） | 定制业务逻辑、数据落库与私有化部署空间受限 |

Pipecat 提供可组合的 `Pipeline`、transport 抽象与 Pipecat Cloud 部署路径，适合在电话场景上快速叠加自有业务。

### 电话接入：Twilio

电话层选用 **Twilio Media Streams**，而非自研 SIP Trunk：

- Twilio 负责号码、信令与媒体流，通过 WebSocket 将音频送入 Pipecat
- 自研 SIP Trunk 需额外承担运营商对接、媒体网关与高可用运维

本地用 **SmallWebRTC** 模拟媒体面；生产经 TwiML Bin 指向 Pipecat Cloud。

### LLM：音频进 / 音频出（Qwen3-Omni）

选用 **端到端实时语音模型**，而非 ASR → LLM → TTS 三段式级联：

| 方案 | 说明 |
| --- | --- |
| 级联（ASR + LLM + TTS） | 延迟与打断体验更难统一，组件与故障面更多 |
| Gemini Live | 能力相近，但在国内环境接入与稳定性成本较高 |
| **Qwen3-Omni Realtime**（当前） | 与 Gemini Live 同属 speech-to-speech 范式，通过 DashScope 在国内更易落地 |

### 架构：Server-to-Server

媒体与推理链路采用 **服务端到服务端**（Twilio ↔ Pipecat Cloud ↔ DashScope），而不是 Client-to-Server（浏览器直连模型 API）：

- API 密钥与 webhook 留在服务端，不暴露给终端
- 电话场景天然是 server 侧媒体桥接；WebRTC 本地调试仅作开发用途

### 开发协作：最小 Harness

任务与验收若只散落在单次 prompt 中，实现后容易漏边界、出 bug、频繁返工。因此落地最小 harness，将 Issue、计划、runbook 与 gate 沉淀在 repo：**Issue Tracker 为协作真相，repo 为执行真相**。

上游 fork 曾提供 Gemini Live 公测号码 1-970-548-3274；本仓库以 Qwen3-Omni 与访客登记业务为准，请按本文「快速开始」自行验收。
