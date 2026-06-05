from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol, cast

import httpx


@dataclass(frozen=True, slots=True)
class ChatMessage:
    role: str
    content: str


@dataclass(frozen=True, slots=True)
class OpenAICompatibleChatOptions:
    base_url: str
    api_key: str | None
    model: str
    timeout_seconds: float
    temperature: float


class ChatCompletionClient(Protocol):
    async def complete_json(self, messages: list[ChatMessage]) -> str: ...


class OpenAICompatibleChatClient:
    def __init__(self, options: OpenAICompatibleChatOptions) -> None:
        self._options = options

    async def complete_json(self, messages: list[ChatMessage]) -> str:
        if not self._options.api_key:
            msg = "LLM_API_KEY is not configured."
            raise RuntimeError(msg)

        payload: dict[str, Any] = {
            "model": self._options.model,
            "messages": [
                {"role": message.role, "content": message.content} for message in messages
            ],
            "temperature": self._options.temperature,
            "response_format": {"type": "json_object"},
        }
        headers = {"Authorization": f"Bearer {self._options.api_key}"}

        async with httpx.AsyncClient(
            base_url=self._options.base_url.rstrip("/"),
            timeout=self._options.timeout_seconds,
        ) as client:
            response = await client.post(
                "/chat/completions",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()

        response_body = cast(object, response.json())
        content = _extract_message_content(response_body)
        if not content:
            msg = "LLM response did not include message content."
            raise RuntimeError(msg)

        return content


def _extract_message_content(response_body: object) -> str | None:
    if not isinstance(response_body, Mapping):
        return None

    body = cast(Mapping[str, object], response_body)
    choices = body.get("choices")
    if not isinstance(choices, list) or not choices:
        return None

    first_choice = cast(object, choices[0])
    if not isinstance(first_choice, Mapping):
        return None

    choice = cast(Mapping[str, object], first_choice)
    message = choice.get("message")
    if not isinstance(message, Mapping):
        return None

    message_body = cast(Mapping[str, object], message)
    content = message_body.get("content")
    return content if isinstance(content, str) else None
