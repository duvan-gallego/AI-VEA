import json
from typing import Literal

import httpx
import pytest

from app.pipelines.engagement_analysis.llm_client import (
    ChatMessage,
    OpenAICompatibleChatClient,
    OpenAICompatibleChatOptions,
)


def _options(
    *,
    response_format: Literal["json_schema", "json_object", "text"] = "json_schema",
) -> OpenAICompatibleChatOptions:
    return OpenAICompatibleChatOptions(
        base_url="https://api.openai.test/v1",
        api_key="test-key",
        model="gpt-4.1-mini",
        timeout_seconds=30,
        temperature=0.1,
        response_format=response_format,
    )


@pytest.mark.anyio
async def test_openai_compatible_chat_client_sends_json_schema_payload() -> None:
    captured_payload: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_payload
        captured_payload = json.loads(request.content)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": '{"hook": null}'}}]},
        )

    client = OpenAICompatibleChatClient(
        options=_options(),
        transport=httpx.MockTransport(handler),
    )

    result = await client.complete_json([ChatMessage(role="user", content="Return JSON.")])

    assert result == '{"hook": null}'
    assert captured_payload["model"] == "gpt-4.1-mini"
    response_format = captured_payload["response_format"]
    assert isinstance(response_format, dict)
    assert response_format["type"] == "json_schema"
    assert "json_schema" in response_format


@pytest.mark.anyio
async def test_openai_compatible_chat_client_accepts_per_call_json_schema() -> None:
    captured_payload: dict[str, object] = {}
    custom_schema = {
        "type": "json_schema",
        "json_schema": {
            "name": "custom_layer_schema",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {"summary": {"type": "string"}},
                "required": ["summary"],
                "additionalProperties": False,
            },
        },
    }

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_payload
        captured_payload = json.loads(request.content)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": '{"summary": "ok"}'}}]},
        )

    client = OpenAICompatibleChatClient(
        options=_options(),
        transport=httpx.MockTransport(handler),
    )

    result = await client.complete_json(
        [ChatMessage(role="user", content="Return JSON.")],
        json_schema=custom_schema,
    )

    assert result == '{"summary": "ok"}'
    assert captured_payload["response_format"] == custom_schema


@pytest.mark.anyio
async def test_openai_compatible_chat_client_supports_legacy_json_object_payload() -> None:
    captured_payload: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_payload
        captured_payload = json.loads(request.content)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": '{"hook": null}'}}]},
        )

    client = OpenAICompatibleChatClient(
        options=_options(response_format="json_object"),
        transport=httpx.MockTransport(handler),
    )

    result = await client.complete_json([ChatMessage(role="user", content="Return JSON.")])

    assert result == '{"hook": null}'
    assert captured_payload["response_format"] == {"type": "json_object"}


@pytest.mark.anyio
async def test_openai_compatible_chat_client_can_omit_response_format() -> None:
    captured_payload: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_payload
        captured_payload = json.loads(request.content)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": '{"hook": null}'}}]},
        )

    client = OpenAICompatibleChatClient(
        options=_options(response_format="text"),
        transport=httpx.MockTransport(handler),
    )

    await client.complete_json([ChatMessage(role="user", content="Return JSON.")])

    assert "response_format" not in captured_payload


@pytest.mark.anyio
async def test_openai_compatible_chat_client_includes_provider_error_message() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400,
            json={
                "error": {
                    "message": "Unsupported parameter: 'response_format'.",
                    "type": "invalid_request_error",
                },
            },
        )

    client = OpenAICompatibleChatClient(
        options=_options(),
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(RuntimeError, match="Unsupported parameter"):
        await client.complete_json([ChatMessage(role="user", content="Return JSON.")])
