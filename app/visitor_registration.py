"""Visitor registration business logic for parking gate voice agent."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

import aiohttp
from loguru import logger
from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.adapters.schemas.tools_schema import ToolsSchema

SYSTEM_INSTRUCTION = """你是园区停车场门卫，用自然、简洁的中文与驾驶员对话，完成访客车辆登记。

## 采集字段（4 项，全部由对话获取）
- 车牌号：如沪A12345
- 来访单位：园区内目标公司，自由文本，如蓝色鲸鱼科技
- 来访事由：如送货、拜访、面试
- 手机号：访客联系电话

## 对话风格（必须遵守）
- 像真人门卫说话，不要机械地一次只问一个字段
- 第一轮尽量合并询问：车牌号、来访单位、事由
- 用户一次说了多项就确认缺失项，不要重复追问已有信息
- 仅当手机号未提供时，再单独追问一次
- 全程控制在 3～4 轮对话内完成

## 正确示例
AI：您好，请问车牌号多少，今天找哪家公司，什么事儿？
用户：沪A12345，来蓝色鲸鱼送货的。
AI：收到，手机号方便留一下吗？
用户：138xxxx1234。
AI：好的！沪A12345，蓝色鲸鱼送货，已通知门卫，请稍等放行。
（然后调用 submit_visitor）

## 错误示例（禁止）
逐字段单独追问：先问车牌 → 再问公司 → 再问事由 → 再问手机号 → 再问停留时长。

## 结束流程
1. 确认四项信息齐全后，先调用 submit_visitor 函数提交登记
2. 根据函数返回结果播报结束语：
   - 成功：「好的！{车牌}，{单位}{事由}，已通知门卫，请稍等放行。」
   - 推送失败：「系统繁忙，请稍后再拨或联系门卫。」
3. 不要编造用户未提供的字段

## 其它
- 来访单位不做名单校验，按用户口述记录
- 入场时间由系统自动记录，无需询问用户
"""


INITIAL_USER_MESSAGE = (
    "请用一句自然的中文问候开始，合并询问车牌号、来访单位和事由。"
    "例如：您好，请问车牌号多少，今天找哪家公司，什么事儿？"
)


@dataclass
class VisitorRecord:
    plate_number: str
    company: str
    phone: str
    reason: str
    entry_time: Optional[datetime] = None

    def to_dict(self) -> dict[str, str]:
        entry = self.entry_time or datetime.now()
        return {
            "plate_number": self.plate_number,
            "company": self.company,
            "phone": self.phone,
            "reason": self.reason,
            "entry_time": entry.strftime("%Y-%m-%d %H:%M"),
        }


def build_tools() -> ToolsSchema:
    submit_visitor = FunctionSchema(
        name="submit_visitor",
        description=(
            "当车牌号、来访单位、来访事由、手机号四项信息均已从对话中确认后调用，"
            "提交访客登记并通知门卫。仅在信息齐全时调用。"
        ),
        properties={
            "plate_number": {
                "type": "string",
                "description": "访客车辆牌照，如沪A12345",
            },
            "company": {
                "type": "string",
                "description": "来访单位/公司名称",
            },
            "phone": {
                "type": "string",
                "description": "访客手机号",
            },
            "reason": {
                "type": "string",
                "description": "来访事由，如送货、拜访、面试",
            },
        },
        required=["plate_number", "company", "phone", "reason"],
    )
    return ToolsSchema(standard_tools=[submit_visitor])


def format_wecom_markdown(record: VisitorRecord) -> str:
    data = record.to_dict()
    return (
        "## 访客登记通知\n"
        f"- **车牌号**：{data['plate_number']}\n"
        f"- **来访单位**：{data['company']}\n"
        f"- **手机号**：{data['phone']}\n"
        f"- **来访事由**：{data['reason']}\n"
        f"- **入场时间**：{data['entry_time']}"
    )


async def push_to_wecom(record: VisitorRecord, webhook_url: str) -> bool:
    """POST markdown message to WeCom group webhook. Returns True on HTTP 200."""
    if not webhook_url:
        logger.error("WECOM_WEBHOOK_URL is not configured")
        return False

    payload = {
        "msgtype": "markdown",
        "markdown": {"content": format_wecom_markdown(record)},
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                webhook_url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=5.0),
            ) as response:
                body = await response.text()
                if response.status == 200:
                    logger.info("WeCom webhook push succeeded")
                    return True
                logger.error(
                    "WeCom webhook push failed: status={} body={}",
                    response.status,
                    body[:200],
                )
                return False
    except Exception as exc:
        logger.error("WeCom webhook push error: {}", exc)
        return False


def record_from_arguments(arguments: dict[str, Any]) -> VisitorRecord:
    return VisitorRecord(
        plate_number=str(arguments.get("plate_number", "")).strip(),
        company=str(arguments.get("company", "")).strip(),
        phone=str(arguments.get("phone", "")).strip(),
        reason=str(arguments.get("reason", "")).strip(),
        entry_time=datetime.now(),
    )


def get_wecom_webhook_url() -> str:
    return os.getenv("WECOM_WEBHOOK_URL", "").strip()


async def submit_visitor_record(arguments: dict[str, Any]) -> dict[str, Any]:
    """Process visitor registration: log, optional WeCom push, return status for LLM."""
    record = record_from_arguments(arguments)
    logger.info("Visitor registration: {}", record.to_dict())

    webhook_url = get_wecom_webhook_url()
    if not webhook_url:
        logger.warning("WECOM_WEBHOOK_URL not set; registration logged only")
        return {
            "status": "recorded",
            "message": "信息已记录，门卫将为您放行。",
            "record": record.to_dict(),
        }

    pushed = await push_to_wecom(record, webhook_url)
    if pushed:
        return {
            "status": "ok",
            "message": f"已通知门卫：{record.plate_number}，{record.company}{record.reason}",
            "record": record.to_dict(),
        }

    return {
        "status": "push_failed",
        "message": "系统繁忙，请稍后再拨或联系门卫。",
        "record": record.to_dict(),
    }
