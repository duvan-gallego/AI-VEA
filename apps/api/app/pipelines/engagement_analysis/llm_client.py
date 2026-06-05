import logging
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal, Protocol, cast

import httpx


@dataclass(frozen=True, slots=True)
class ChatMessage:
    role: str
    content: str


logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class OpenAICompatibleChatOptions:
    base_url: str
    api_key: str | None
    model: str
    timeout_seconds: float
    temperature: float
    response_format: Literal["json_schema", "json_object", "text"] = "json_schema"


class ChatCompletionClient(Protocol):
    async def complete_json(
        self,
        messages: list[ChatMessage],
        json_schema: dict[str, Any] | None = None,
    ) -> str: ...


class OpenAICompatibleChatClient:
    def __init__(
        self,
        options: OpenAICompatibleChatOptions,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._options = options
        self._transport = transport

    async def complete_json(
        self,
        messages: list[ChatMessage],
        json_schema: dict[str, Any] | None = None,
    ) -> str:
        if not self._options.api_key:
            msg = "LLM_API_KEY is not configured."
            raise RuntimeError(msg)

        payload: dict[str, Any] = {
            "model": self._options.model,
            "messages": [
                {"role": message.role, "content": message.content} for message in messages
            ],
            "temperature": self._options.temperature,
        }
        if self._options.response_format == "json_schema":
            payload["response_format"] = json_schema or _build_json_schema_response_format()
        elif self._options.response_format == "json_object":
            payload["response_format"] = {"type": "json_object"}
        headers = {"Authorization": f"Bearer {self._options.api_key}"}

        logger.info(
            "Sending LLM chat completion request base_url=%s model=%s response_format=%s",
            self._options.base_url,
            self._options.model,
            self._options.response_format,
        )
        async with httpx.AsyncClient(
            base_url=self._options.base_url.rstrip("/"),
            timeout=self._options.timeout_seconds,
            transport=self._transport,
        ) as client:
            response = await client.post(
                "/chat/completions",
                json=payload,
                headers=headers,
            )

        if response.is_error:
            msg = _format_http_error(response)
            logger.warning(
                "LLM chat completion request failed status_code=%s error=%s",
                response.status_code,
                msg,
            )
            raise RuntimeError(msg)

        response_body = cast(object, response.json())
        content = _extract_message_content(response_body)
        if not content:
            msg = "LLM response did not include message content."
            raise RuntimeError(msg)

        logger.info("Completed LLM chat completion request response_chars=%s", len(content))
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


def _build_json_schema_response_format() -> dict[str, Any]:
    section_schema = {
        "type": ["object", "null"],
        "properties": {
            "title": {"type": "string"},
            "summary": {"type": "string"},
            "start_seconds": {"type": ["number", "null"]},
            "end_seconds": {"type": ["number", "null"]},
            "evidence": {"type": "array", "items": {"type": "string"}},
            "confidence": {"type": ["number", "null"], "minimum": 0, "maximum": 1},
        },
        "required": [
            "title",
            "summary",
            "start_seconds",
            "end_seconds",
            "evidence",
            "confidence",
        ],
        "additionalProperties": False,
    }

    return {
        "type": "json_schema",
        "json_schema": {
            "name": "engagement_analysis_structure",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "hook": section_schema,
                    "setup": section_schema,
                    "main_content": section_schema,
                    "cta": section_schema,
                    "notes": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["hook", "setup", "main_content", "cta", "notes"],
                "additionalProperties": False,
            },
        },
    }


def _format_http_error(response: httpx.Response) -> str:
    error_message = _extract_openai_error_message(cast(object, _safe_response_json(response)))
    if error_message is None:
        error_message = response.text.strip()

    detail = f": {error_message}" if error_message else ""
    return f"LLM request failed with HTTP {response.status_code}{detail}"


def _safe_response_json(response: httpx.Response) -> object | None:
    try:
        return cast(object, response.json())
    except ValueError:
        return None


def _extract_openai_error_message(response_body: object) -> str | None:
    if not isinstance(response_body, Mapping):
        return None

    body = cast(Mapping[str, object], response_body)
    error = body.get("error")
    if not isinstance(error, Mapping):
        return None

    error_body = cast(Mapping[str, object], error)
    message = error_body.get("message")
    return message if isinstance(message, str) else None
