"""Sarvam-105B as a LangChain chat model with tool calling, so it can drive the same
LangGraph agent (create_react_agent) as any other model."""
from __future__ import annotations

import json
import re
import uuid
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.utils.function_calling import convert_to_openai_tool

from .. import config
from ..services import sarvam

_THINK = re.compile(r"<think>.*?</think>", re.S)


def _to_sarvam(m: BaseMessage) -> dict:
    content = m.content if isinstance(m.content, str) else json.dumps(m.content, ensure_ascii=False)
    if isinstance(m, SystemMessage):
        return {"role": "system", "content": content}
    if isinstance(m, HumanMessage):
        return {"role": "user", "content": content}
    if isinstance(m, ToolMessage):
        return {"role": "tool", "tool_call_id": m.tool_call_id, "content": content}
    if isinstance(m, AIMessage):
        out: dict[str, Any] = {"role": "assistant", "content": content or ""}
        if m.tool_calls:
            out["tool_calls"] = [
                {"id": tc["id"], "type": "function",
                 "function": {"name": tc["name"], "arguments": json.dumps(tc["args"], ensure_ascii=False)}}
                for tc in m.tool_calls
            ]
        return out
    return {"role": "user", "content": content}


class ChatSarvam(BaseChatModel):
    model: str = config.SARVAM_CHAT_MODEL
    temperature: float = 0.3
    max_tokens: int = 500

    @property
    def _llm_type(self) -> str:
        return "sarvam"

    def bind_tools(self, tools, **kwargs):
        return self.bind(tools=[convert_to_openai_tool(t) for t in tools], **kwargs)

    def _generate(self, messages: list[BaseMessage], stop=None, run_manager=None, **kwargs) -> ChatResult:
        params: dict[str, Any] = {
            "model": self.model,
            "messages": [_to_sarvam(m) for m in messages],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "reasoning_effort": "low",
        }
        if kwargs.get("tools"):
            params["tools"] = kwargs["tools"]
            params["tool_choice"] = kwargs.get("tool_choice") or "auto"
        r = sarvam._client().chat.completions(**params)
        msg = r.choices[0].message
        tool_calls = []
        for tc in msg.tool_calls or []:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            tool_calls.append({"name": tc.function.name, "args": args, "id": tc.id or str(uuid.uuid4()), "type": "tool_call"})
        text = _THINK.sub("", msg.content or "").strip()
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=text, tool_calls=tool_calls))])
