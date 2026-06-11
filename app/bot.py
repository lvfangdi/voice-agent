#
# Copyright (c) 2024–2025, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

"""Qwen Omni Realtime visitor registration bot.

A Pipecat bot for parking gate visitor registration via voice.
Uses DashScope Qwen-Omni Realtime; connect locally via SmallWebRTC.

Run locally (from repo root)::

    uv run bot.py
"""

import asyncio
import os

from dotenv import load_dotenv
from loguru import logger
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.frames.frames import EndTaskFrame, LLMRunFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    AssistantTurnStoppedMessage,
    LLMContextAggregatorPair,
    UserTurnStoppedMessage,
)
from pipecat.processors.frame_processor import FrameDirection
from pipecat.processors.frameworks.rtvi import RTVIObserver, RTVIProcessor
from pipecat.runner.types import RunnerArguments
from pipecat.runner.utils import create_transport
from pipecat.services.llm_service import FunctionCallParams
from pipecat.transports.base_transport import BaseTransport, TransportParams
from pipecat.transports.websocket.fastapi import FastAPIWebsocketParams

from app.qwen_omni_live_service import InputParams, QwenOmniLiveLLMService
from app.visitor_registration import (
    INITIAL_USER_MESSAGE,
    SYSTEM_INSTRUCTION,
    build_tools,
    submit_visitor_record,
)

load_dotenv(override=True)

_DEBUG_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "debug-0e7ac3.log")


def _dbg(location: str, message: str, data: dict, hypothesis_id: str, run_id: str = "pre-fix") -> None:
    # #region agent log
    import json
    import time
    from pathlib import Path

    entry = {
        "sessionId": "0e7ac3",
        "timestamp": int(time.time() * 1000),
        "location": location,
        "message": message,
        "data": data,
        "hypothesisId": hypothesis_id,
        "runId": run_id,
    }
    Path(_DEBUG_LOG).open("a", encoding="utf-8").write(json.dumps(entry, ensure_ascii=False) + "\n")
    # #endregion


async def submit_visitor_handler(params: FunctionCallParams):
    """Handle submit_visitor: push to WeCom, return status, then end the call."""
    # #region agent log
    _dbg("bot.py:submit_visitor_handler:entry", "handler started", {"arg_keys": list(params.arguments.keys())}, "A")
    # #endregion
    result = await submit_visitor_record(params.arguments)
    logger.info("submit_visitor result: status={}", result.get("status"))
    # #region agent log
    _dbg(
        "bot.py:submit_visitor_handler:after_record",
        "submit_visitor_record done",
        {"status": result.get("status")},
        "D",
    )
    # #endregion
    await params.result_callback(result)
    # #region agent log
    _dbg("bot.py:submit_visitor_handler:after_callback", "result_callback done", {}, "A")
    # #endregion
    # Allow the LLM to speak the closing message before hanging up.
    await asyncio.sleep(3)
    # #region agent log
    _dbg("bot.py:submit_visitor_handler:before_end_task", "about to push EndTaskFrame", {}, "A")
    # #endregion
    await params.llm.push_frame(EndTaskFrame(), FrameDirection.UPSTREAM)
    # #region agent log
    _dbg("bot.py:submit_visitor_handler:after_end_task", "EndTaskFrame pushed", {}, "A")
    # #endregion


async def run_bot(transport: BaseTransport, runner_args: RunnerArguments):
    logger.info("Starting visitor registration bot")

    llm = QwenOmniLiveLLMService(
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        model="qwen3.5-omni-plus-realtime",
        voice="Tina",
        system_instruction=SYSTEM_INSTRUCTION,
        tools=build_tools(),
        params=InputParams(),
    )

    llm.register_function("submit_visitor", submit_visitor_handler)

    messages = [{"role": "user", "content": INITIAL_USER_MESSAGE}]

    context = LLMContext(messages)
    user_aggregator, assistant_aggregator = LLMContextAggregatorPair(context)

    rtvi = RTVIProcessor()

    pipeline = Pipeline(
        [
            transport.input(),
            rtvi,
            user_aggregator,
            llm,
            transport.output(),
            assistant_aggregator,
        ]
    )

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            enable_metrics=True,
            enable_usage_metrics=True,
        ),
        idle_timeout_secs=runner_args.pipeline_idle_timeout_secs,
        observers=[RTVIObserver(rtvi)],
    )

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        logger.info("Client connected")
        await task.queue_frames([LLMRunFrame()])

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info("Client disconnected")
        # #region agent log
        _dbg("bot.py:on_client_disconnected", "client disconnected", {}, "E")
        # #endregion
        await task.cancel()

    @user_aggregator.event_handler("on_user_turn_stopped")
    async def on_user_turn_stopped(aggregator, strategy, message: UserTurnStoppedMessage):
        timestamp = f"[{message.timestamp}] " if message.timestamp else ""
        logger.info(f"Transcript: {timestamp}user: {message.content}")

    @assistant_aggregator.event_handler("on_assistant_turn_stopped")
    async def on_assistant_turn_stopped(aggregator, message: AssistantTurnStoppedMessage):
        timestamp = f"[{message.timestamp}] " if message.timestamp else ""
        logger.info(f"Transcript: {timestamp}assistant: {message.content}")
        # #region agent log
        _dbg(
            "bot.py:on_assistant_turn_stopped",
            "assistant turn",
            {"content_len": len(message.content or ""), "preview": (message.content or "")[:80]},
            "B",
        )
        # #endregion

    runner = PipelineRunner(handle_sigint=runner_args.handle_sigint)
    await runner.run(task)


async def bot(runner_args: RunnerArguments):
    """Main bot entry point compatible with Pipecat Cloud."""
    if os.environ.get("ENV") != "local":
        from pipecat.audio.filters.krisp_viva_filter import KrispVivaFilter

        krisp_filter = KrispVivaFilter()
    else:
        krisp_filter = None

    transport_params = {
        "twilio": lambda: FastAPIWebsocketParams(
            audio_in_enabled=True,
            audio_in_filter=krisp_filter,
            audio_out_enabled=True,
            vad_analyzer=SileroVADAnalyzer(params=VADParams(stop_secs=0.5)),
        ),
        "webrtc": lambda: TransportParams(
            audio_in_enabled=True,
            audio_in_filter=krisp_filter,
            audio_out_enabled=True,
            vad_analyzer=SileroVADAnalyzer(params=VADParams(stop_secs=0.5)),
        ),
    }

    transport = await create_transport(runner_args, transport_params)
    await run_bot(transport, runner_args)


if __name__ == "__main__":
    from pipecat.runner.run import main

    main()
