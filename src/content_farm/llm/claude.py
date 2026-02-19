"""
Claude (Anthropic) adapter implementing the browser-use BaseChatModel Protocol.

browser-use passes messages as [SystemMessage, UserMessage, ...context_messages].
The conversation never contains assistant turns in history — it's always a fresh
call with the current page state embedded in the user message.
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass, field
from typing import Any, TypeVar, Union, overload

import anthropic

from browser_use.llm.base import BaseChatModel
from browser_use.llm.messages import (
    AssistantMessage,
    BaseMessage,
    ContentPartImageParam,
    ContentPartTextParam,
    SystemMessage,
    UserMessage,
)
from browser_use.llm.views import ChatInvokeCompletion, ChatInvokeUsage
from pydantic import BaseModel

T = TypeVar("T", bound=Union[BaseModel, str])


def _serialize_content(
    content: str | list[ContentPartTextParam | ContentPartImageParam],
) -> list[dict[str, Any]]:
    """Convert browser-use content parts to Anthropic content blocks."""
    if isinstance(content, str):
        return [{"type": "text", "text": content}]

    blocks: list[dict[str, Any]] = []
    for part in content:
        if part.type == "text":
            blocks.append({"type": "text", "text": part.text})
        elif part.type == "image_url":
            url = part.image_url.url
            media_type = part.image_url.media_type or "image/png"
            if url.startswith("data:"):
                # data:<media_type>;base64,<data>
                header, data = url.split(",", 1)
                detected_type = header.split(";")[0].split(":")[1]
                blocks.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": detected_type,
                        "data": data,
                    },
                })
            else:
                blocks.append({
                    "type": "image",
                    "source": {"type": "url", "url": url},
                })
    return blocks


def _to_anthropic_messages(
    messages: list[BaseMessage],
) -> tuple[str, list[dict[str, Any]]]:
    """
    Convert browser-use messages to Anthropic (system, messages) format.
    Returns (system_prompt, anthropic_messages).
    """
    system_parts: list[str] = []
    api_messages: list[dict[str, Any]] = []

    for msg in messages:
        if isinstance(msg, SystemMessage):
            text = msg.text if isinstance(msg.content, list) else msg.content
            system_parts.append(text)
        elif isinstance(msg, UserMessage):
            blocks = _serialize_content(msg.content)
            if len(blocks) == 1 and blocks[0]["type"] == "text":
                api_messages.append({"role": "user", "content": blocks[0]["text"]})
            else:
                api_messages.append({"role": "user", "content": blocks})
        elif isinstance(msg, AssistantMessage):
            text = msg.text
            api_messages.append({"role": "assistant", "content": text or ""})

    return "\n".join(system_parts), api_messages


@dataclass
class ChatClaude:
    """
    Anthropic Claude adapter for browser-use, implementing BaseChatModel Protocol.
    """

    model: str = "claude-sonnet-4-6"
    max_tokens: int = 4096
    temperature: float = 0.2

    _client: anthropic.AsyncAnthropic = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._client = anthropic.AsyncAnthropic()

    @property
    def provider(self) -> str:
        return "anthropic"

    @property
    def name(self) -> str:
        return self.model

    @property
    def model_name(self) -> str:
        return self.model

    @overload
    async def ainvoke(
        self, messages: list[BaseMessage], output_format: None = None, **kwargs: Any
    ) -> ChatInvokeCompletion[str]: ...

    @overload
    async def ainvoke(
        self, messages: list[BaseMessage], output_format: type[T], **kwargs: Any
    ) -> ChatInvokeCompletion[T]: ...

    async def ainvoke(
        self,
        messages: list[BaseMessage],
        output_format: type[T] | None = None,
        **kwargs: Any,
    ) -> ChatInvokeCompletion[T] | ChatInvokeCompletion[str]:
        system, api_messages = _to_anthropic_messages(messages)

        if output_format is None:
            response = await self._client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=system or anthropic.NOT_GIVEN,
                messages=api_messages,
            )
            text = response.content[0].text if response.content else ""
            usage = _make_usage(response.usage)
            return ChatInvokeCompletion(
                completion=text,
                usage=usage,
                stop_reason=response.stop_reason,
            )

        # Structured output via forced tool use
        schema = output_format.model_json_schema()
        # Anthropic tool input_schema must not have a top-level 'title'
        schema.pop("title", None)

        tools = [{
            "name": "agent_output",
            "description": "Output the structured agent response.",
            "input_schema": schema,
        }]

        response = await self._client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            system=system or anthropic.NOT_GIVEN,
            messages=api_messages,
            tools=tools,
            tool_choice={"type": "tool", "name": "agent_output"},
        )

        usage = _make_usage(response.usage)

        # Extract tool input from response
        tool_block = next(
            (b for b in response.content if b.type == "tool_use"),
            None,
        )
        if tool_block is None:
            # Fallback: try to parse text as JSON
            text_block = next((b for b in response.content if b.type == "text"), None)
            raw = json.loads(text_block.text) if text_block else {}
        else:
            raw = tool_block.input

        parsed = output_format.model_validate(raw)
        return ChatInvokeCompletion(
            completion=parsed,
            usage=usage,
            stop_reason=response.stop_reason,
        )


def _make_usage(usage: Any) -> ChatInvokeUsage:
    return ChatInvokeUsage(
        prompt_tokens=getattr(usage, "input_tokens", 0),
        prompt_cached_tokens=getattr(usage, "cache_read_input_tokens", None),
        prompt_cache_creation_tokens=getattr(usage, "cache_creation_input_tokens", None),
        prompt_image_tokens=None,
        completion_tokens=getattr(usage, "output_tokens", 0),
        total_tokens=getattr(usage, "input_tokens", 0) + getattr(usage, "output_tokens", 0),
    )
