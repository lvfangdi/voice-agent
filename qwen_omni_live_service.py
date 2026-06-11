#
# Copyright (c) 2024–2025, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

"""Pipecat adapter for DashScope Qwen-Omni Realtime API."""

import asyncio
import audioop
import base64
import json
import os
import uuid
from typing import Any, Dict, List, Optional, Union

import dashscope
from dashscope.audio.qwen_omni import (
    AudioFormat,
    MultiModality,
    OmniRealtimeCallback,
    OmniRealtimeConversation,
)
from loguru import logger
from pydantic import BaseModel, Field

from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.frames.frames import (
    CancelFrame,
    EndFrame,
    Frame,
    InputAudioRawFrame,
    InputTextRawFrame,
    InterruptionFrame,
    LLMContextFrame,
    LLMFullResponseEndFrame,
    LLMFullResponseStartFrame,
    LLMMessagesAppendFrame,
    LLMRunFrame,
    LLMSetToolsFrame,
    LLMTextFrame,
    LLMUpdateSettingsFrame,
    StartFrame,
    TranscriptionFrame,
    TTSAudioRawFrame,
    TTSStartedFrame,
    TTSStoppedFrame,
    TTSTextFrame,
    UserStartedSpeakingFrame,
    UserStoppedSpeakingFrame,
)
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.openai_llm_context import (
    OpenAILLMContext,
    OpenAILLMContextFrame,
)
from pipecat.processors.frame_processor import FrameDirection
from pipecat.services.llm_service import FunctionCallParams, LLMService
from pipecat.utils.time import time_now_iso8601

DEFAULT_MODEL = "qwen3.5-omni-plus-realtime"
DEFAULT_VOICE = "Tina"
DEFAULT_URL = "wss://dashscope.aliyuncs.com/api-ws/v1/realtime"
INPUT_SAMPLE_RATE = 16000
OUTPUT_SAMPLE_RATE = 24000


class InputParams(BaseModel):
    """Input parameters for Qwen Omni Realtime generation."""

    voice: str = Field(default=DEFAULT_VOICE)
    turn_detection_threshold: float = Field(default=0.5)
    turn_detection_silence_duration_ms: int = Field(default=800)
    prefix_padding_ms: int = Field(default=300)
    enable_input_audio_transcription: bool = Field(default=True)


def _tools_to_qwen_format(tools: Optional[Union[List[dict], ToolsSchema]]) -> List[Dict[str, Any]]:
    if not tools:
        return []

    if isinstance(tools, ToolsSchema):
        schemas = tools.standard_tools
    else:
        schemas = tools

    qwen_tools = []
    for tool in schemas:
        if isinstance(tool, FunctionSchema):
            qwen_tools.append(
                {
                    "type": "function",
                    "function": tool.to_default_dict(),
                }
            )
        elif isinstance(tool, dict):
            qwen_tools.append(tool)
    return qwen_tools


def _resample_pcm(audio: bytes, in_rate: int, out_rate: int, channels: int = 1) -> bytes:
    if in_rate == out_rate:
        return audio
    converted, _ = audioop.ratecv(audio, 2, channels, in_rate, out_rate, None)
    return converted


class _QwenOmniCallback(OmniRealtimeCallback):
    def __init__(self, service: "QwenOmniLiveLLMService"):
        self._service = service

    def on_open(self) -> None:
        self._service._schedule_coroutine(self._service._on_connected())

    def on_close(self, close_status_code: int, close_msg: str) -> None:
        self._service._schedule_coroutine(
            self._service._on_disconnected(close_status_code, close_msg)
        )

    def on_event(self, response: dict) -> None:
        self._service._schedule_coroutine(self._service._on_event(response))


class QwenOmniLiveLLMService(LLMService):
    """Pipecat service for DashScope Qwen-Omni Realtime speech-to-speech API."""

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        voice: str = DEFAULT_VOICE,
        url: str = DEFAULT_URL,
        system_instruction: Optional[str] = None,
        tools: Optional[Union[List[dict], ToolsSchema]] = None,
        params: Optional[InputParams] = None,
        inference_on_context_initialization: bool = True,
        **kwargs,
    ):
        super().__init__(**kwargs)

        self._api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
        if not self._api_key:
            raise ValueError("DASHSCOPE_API_KEY is required")

        dashscope.api_key = self._api_key

        params = params or InputParams()
        self._params = params
        self.set_model_name(model)
        self._voice = voice
        self._url = url
        self._system_instruction = system_instruction
        self._tools = _tools_to_qwen_format(tools)
        self._inference_on_context_initialization = inference_on_context_initialization

        self._conversation: Optional[OmniRealtimeConversation] = None
        self._callback: Optional[_QwenOmniCallback] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._connected = False
        self._disconnecting = False
        self._context: Optional[LLMContext] = None
        self._bot_is_responding = False
        self._bot_text_buffer = ""
        self._pending_initial_response = False
        self._session_configured = False
        self._end_frame_pending_bot_turn_finished: Optional[EndFrame] = None

    def _schedule_coroutine(self, coro):
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(coro, self._loop)

    async def start(self, frame: StartFrame):
        await super().start(frame)
        self._loop = asyncio.get_running_loop()
        await self._connect()

    async def stop(self, frame: EndFrame):
        await super().stop(frame)
        await self._disconnect()

    async def cancel(self, frame: CancelFrame):
        await super().cancel(frame)
        await self._disconnect()

    async def _connect(self):
        if self._conversation:
            return

        logger.info("Connecting to Qwen Omni Realtime service")
        self._callback = _QwenOmniCallback(self)
        self._conversation = OmniRealtimeConversation(
            model=self._model_name,
            callback=self._callback,
            url=self._url,
            api_key=self._api_key,
        )

        await asyncio.to_thread(self._conversation.connect)

    async def _disconnect(self):
        if not self._conversation or self._disconnecting:
            return

        self._disconnecting = True
        logger.info("Disconnecting from Qwen Omni Realtime service")
        try:
            conversation = self._conversation
            self._conversation = None
            self._connected = False
            self._session_configured = False
            await asyncio.to_thread(conversation.close)
        finally:
            self._disconnecting = False

    async def _on_connected(self):
        self._connected = True
        await self._configure_session()
        if self._pending_initial_response:
            self._pending_initial_response = False
            await self._create_initial_response()

    async def _on_disconnected(self, close_status_code: int, close_msg: str):
        logger.info(
            f"Qwen Omni connection closed (code={close_status_code}, msg={close_msg})"
        )
        self._connected = False
        self._session_configured = False

    async def _configure_session(self):
        if not self._conversation or self._session_configured:
            return

        instructions = self._system_instruction
        if self._context:
            for message in self._context.messages:
                if message.get("role") == "system":
                    content = message.get("content", "")
                    if content:
                        instructions = str(content)
                        break

        self._conversation.update_session(
            output_modalities=[MultiModality.AUDIO, MultiModality.TEXT],
            voice=self._voice,
            input_audio_format=AudioFormat.PCM_16000HZ_MONO_16BIT,
            output_audio_format=AudioFormat.PCM_24000HZ_MONO_16BIT,
            enable_input_audio_transcription=self._params.enable_input_audio_transcription,
            enable_turn_detection=True,
            turn_detection_type="semantic_vad",
            prefix_padding_ms=self._params.prefix_padding_ms,
            turn_detection_threshold=self._params.turn_detection_threshold,
            turn_detection_silence_duration_ms=self._params.turn_detection_silence_duration_ms,
            instructions=instructions,
            tools=self._tools or None,
        )
        self._session_configured = True
        logger.info("Qwen Omni session configured")

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        if isinstance(frame, EndFrame):
            if self._bot_is_responding:
                logger.debug("Deferring EndFrame until bot turn is finished")
                self._end_frame_pending_bot_turn_finished = frame
                return

        await super().process_frame(frame, direction)

        if isinstance(frame, (LLMContextFrame, OpenAILLMContextFrame)):
            context = (
                frame.context
                if isinstance(frame, LLMContextFrame)
                else LLMContext.from_openai_context(frame.context)
            )
            await self._handle_context(context)
        elif isinstance(frame, InputAudioRawFrame):
            await self._send_user_audio(frame)
            await self.push_frame(frame, direction)
        elif isinstance(frame, InputTextRawFrame):
            await self._send_user_text(frame.text)
            await self.push_frame(frame, direction)
        elif isinstance(frame, InterruptionFrame):
            await self._handle_interruption()
            await self.push_frame(frame, direction)
        elif isinstance(frame, UserStartedSpeakingFrame):
            await self.push_frame(frame, direction)
        elif isinstance(frame, UserStoppedSpeakingFrame):
            await self.start_ttfb_metrics()
            await self.push_frame(frame, direction)
        elif isinstance(frame, LLMMessagesAppendFrame):
            await self._create_response_from_messages(frame.messages)
        elif isinstance(frame, LLMUpdateSettingsFrame):
            await self._update_settings(frame.settings)
        elif isinstance(frame, LLMSetToolsFrame):
            self._tools = _tools_to_qwen_format(frame.tools)
            await self._reconfigure_session()
        else:
            await self.push_frame(frame, direction)

    async def _handle_context(self, context: LLMContext):
        if not self._context:
            self._context = context
            await self._reconfigure_session()
            await self._create_initial_response()
        else:
            self._context = context

    async def _reconfigure_session(self):
        self._session_configured = False
        if self._connected:
            await self._configure_session()

    async def _create_initial_response(self):
        if not self._context or not self._inference_on_context_initialization:
            return

        user_messages = [
            message.get("content", "")
            for message in self._context.messages
            if message.get("role") == "user" and message.get("content")
        ]
        if not user_messages:
            return

        instructions = str(user_messages[-1])
        await self._create_response(instructions)

    async def _create_response_from_messages(self, messages_list: List[dict]):
        user_messages = [
            message.get("content", "")
            for message in messages_list
            if message.get("role") == "user" and message.get("content")
        ]
        if not user_messages:
            return
        await self._create_response(str(user_messages[-1]))

    async def _create_response(self, instructions: Optional[str] = None):
        if self._disconnecting:
            return

        if not self._conversation or not self._connected:
            self._pending_initial_response = True
            return

        await self.start_ttfb_metrics()
        await asyncio.to_thread(
            self._conversation.create_response,
            instructions,
            [MultiModality.AUDIO, MultiModality.TEXT],
        )

    async def _send_user_audio(self, frame: InputAudioRawFrame):
        if self._disconnecting or not self._conversation or not self._connected:
            return

        audio = _resample_pcm(
            frame.audio,
            frame.sample_rate,
            INPUT_SAMPLE_RATE,
            frame.num_channels,
        )
        audio_b64 = base64.b64encode(audio).decode("ascii")
        await asyncio.to_thread(self._conversation.append_audio, audio_b64)

    async def _send_user_text(self, text: str):
        if self._disconnecting or not self._conversation or not self._connected:
            return
        await self._create_response(text)

    async def _handle_interruption(self):
        if not self._conversation or not self._connected:
            return

        if self._bot_is_responding:
            await self._set_bot_is_responding(False)
            await self.push_frame(TTSStoppedFrame())

        await asyncio.to_thread(self._conversation.cancel_response)

    async def _set_bot_is_responding(self, responding: bool):
        if self._bot_is_responding == responding:
            return

        self._bot_is_responding = responding
        if not self._bot_is_responding and self._end_frame_pending_bot_turn_finished:
            await self.queue_frame(self._end_frame_pending_bot_turn_finished)
            self._end_frame_pending_bot_turn_finished = None

    async def _on_event(self, response: Dict[str, Any]):
        event_type = response.get("type", "")

        if event_type == "response.audio.delta":
            await self._handle_audio_delta(response)
        elif event_type in ("response.audio_transcript.delta", "response.text.delta"):
            await self._handle_text_delta(response)
        elif event_type == "response.done":
            await self._handle_response_done()
        elif event_type == "conversation.item.input_audio_transcription.completed":
            await self._handle_user_transcription(response)
        elif event_type == "input_audio_buffer.speech_started":
            await self._handle_speech_started()
        elif event_type == "response.function_call_arguments.done":
            await self._handle_function_call(response)

    async def _handle_audio_delta(self, response: Dict[str, Any]):
        audio_b64 = response.get("delta", "")
        if not audio_b64:
            return

        await self.stop_ttfb_metrics()

        if not self._bot_is_responding:
            await self._set_bot_is_responding(True)
            await self.push_frame(TTSStartedFrame())
            await self.push_frame(LLMFullResponseStartFrame())

        audio = base64.b64decode(audio_b64)
        await self.push_frame(
            TTSAudioRawFrame(
                audio=audio,
                sample_rate=OUTPUT_SAMPLE_RATE,
                num_channels=1,
            )
        )

    async def _handle_text_delta(self, response: Dict[str, Any]):
        text = response.get("delta", "")
        if not text:
            return

        if not self._bot_is_responding:
            await self._set_bot_is_responding(True)
            await self.push_frame(TTSStartedFrame())
            await self.push_frame(LLMFullResponseStartFrame())

        self._bot_text_buffer += text
        await self.push_frame(TTSTextFrame(text=text))
        await self.push_frame(LLMTextFrame(text=text))

    async def _handle_response_done(self):
        if self._bot_is_responding:
            await self._set_bot_is_responding(False)
            await self.push_frame(TTSStoppedFrame())
            await self.push_frame(LLMFullResponseEndFrame())
        self._bot_text_buffer = ""

    async def _handle_user_transcription(self, response: Dict[str, Any]):
        transcript = response.get("transcript", "")
        if not transcript:
            return

        await self.push_frame(
            TranscriptionFrame(
                text=transcript,
                user_id="",
                timestamp=time_now_iso8601(),
                result=response,
            ),
            FrameDirection.UPSTREAM,
        )

    async def _handle_speech_started(self):
        if self._bot_is_responding:
            await self._handle_interruption()

    async def _handle_function_call(self, response: Dict[str, Any]):
        if not self._context:
            logger.error("Function calls require a context object")
            return

        # #region agent log
        import json as _json_dbg
        import time as _time_dbg
        from pathlib import Path as _PathDbg

        def _dbg_qwen(loc: str, msg: str, data: dict, hid: str) -> None:
            _log_path = _PathDbg(__file__).resolve().parent / "debug-0e7ac3.log"
            _log_path.open("a", encoding="utf-8").write(
                _json_dbg.dumps(
                    {
                        "sessionId": "0e7ac3",
                        "timestamp": int(_time_dbg.time() * 1000),
                        "location": loc,
                        "message": msg,
                        "data": data,
                        "hypothesisId": hid,
                        "runId": "pre-fix",
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )

        # #endregion

        function_name = response.get("name", "")
        call_id = response.get("call_id", "")
        try:
            arguments = json.loads(response.get("arguments", "{}") or "{}")
        except json.JSONDecodeError:
            arguments = {}

        if function_name not in self._functions:
            logger.warning(f"Function '{function_name}' is not registered")
            await self._send_tool_result(call_id, json.dumps({"error": "unknown_function"}))
            await self._create_response()
            return

        item = self._functions[function_name]
        result_value: Dict[str, Any] = {"status": "ok"}

        async def result_callback(result: Any, *, properties=None):
            nonlocal result_value
            result_value = result if isinstance(result, dict) else {"result": result}

        params = FunctionCallParams(
            function_name=function_name,
            tool_call_id=call_id,
            arguments=arguments,
            llm=self,
            context=self._context,
            result_callback=result_callback,
        )

        # #region agent log
        _dbg_qwen(
            "qwen:_handle_function_call:before_handler",
            "invoking handler",
            {"function_name": function_name},
            "A",
        )
        # #endregion
        try:
            if item.handler_deprecated:
                await item.handler(
                    function_name,
                    call_id,
                    arguments,
                    self,
                    self._context,
                    result_callback,
                )
            else:
                await item.handler(params)
        except Exception as e:
            logger.error(f"Error executing function '{function_name}': {e}")
            result_value = {"error": str(e)}

        # #region agent log
        _dbg_qwen(
            "qwen:_handle_function_call:after_handler",
            "handler returned",
            {"function_name": function_name, "result_status": result_value.get("status")},
            "A",
        )
        # #endregion
        await self._send_tool_result(call_id, json.dumps(result_value, ensure_ascii=False))
        # #region agent log
        _dbg_qwen("qwen:_handle_function_call:after_send_tool_result", "tool result sent", {}, "B")
        # #endregion
        await self._create_response()
        # #region agent log
        _dbg_qwen("qwen:_handle_function_call:after_create_response", "create_response done", {}, "B")
        # #endregion

    async def _send_tool_result(self, call_id: str, output: str):
        if not self._conversation or not self._connected:
            return

        item = {
            "id": f"item_{uuid.uuid4().hex}",
            "type": "function_call_output",
            "call_id": call_id,
            "output": output,
        }
        await asyncio.to_thread(self._conversation.create_item, item)

    async def _update_settings(self, settings: dict):
        if "voice" in settings:
            self._voice = settings["voice"]
        if "system_instruction" in settings:
            self._system_instruction = settings["system_instruction"]
        await self._reconfigure_session()
