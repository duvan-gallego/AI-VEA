import pytest

from app.pipelines.engagement_analysis.llm_client import ChatMessage
from app.pipelines.engagement_analysis.models import (
    AudioFeature,
    MediaUnderstanding,
    SceneSegment,
)
from app.pipelines.engagement_analysis.structural_analyzer import (
    StructuralUnderstandingAnalyzer,
)


class FakeChatClient:
    def __init__(self, response: str) -> None:
        self.response = response
        self.messages: list[ChatMessage] = []

    async def complete_json(self, messages: list[ChatMessage]) -> str:
        self.messages = messages
        return self.response


@pytest.mark.anyio
async def test_structural_analyzer_uses_openai_compatible_json_response() -> None:
    client = FakeChatClient(
        """
        {
          "hook": {
            "title": "Hook",
            "summary": "Opens with the core promise.",
            "start_seconds": 0,
            "end_seconds": 4,
            "evidence": ["I can double your retention"],
            "confidence": 0.91
          },
          "setup": {
            "title": "Setup",
            "summary": "Explains why retention drops.",
            "start_seconds": 4,
            "end_seconds": 12,
            "evidence": ["most videos lose people early"],
            "confidence": 0.82
          },
          "main_content": {
            "title": "Main content",
            "summary": "Walks through the improvement framework.",
            "start_seconds": 12,
            "end_seconds": 50,
            "evidence": ["first, rewrite your opening"],
            "confidence": 0.86
          },
          "cta": {
            "title": "CTA",
            "summary": "Asks viewers to try the checklist.",
            "start_seconds": 50,
            "end_seconds": 60,
            "evidence": ["download the checklist"],
            "confidence": 0.8
          },
          "notes": ["Transcript evidence was sufficient."]
        }
        """,
    )
    analyzer = StructuralUnderstandingAnalyzer(chat_client=client)

    result = await analyzer.analyze(
        MediaUnderstanding(
            transcript="I can double your retention. Download the checklist.",
            scenes=[SceneSegment(start_seconds=0, end_seconds=60)],
            audio_features=[AudioFeature(name="tempo", value=120, unit="bpm")],
            duration_seconds=60,
        ),
    )

    assert result.hook is not None
    assert result.hook.summary == "Opens with the core promise."
    assert result.setup is not None
    assert result.main_content is not None
    assert result.cta is not None
    assert result.hook_detected is True
    assert result.estimated_scene_count == 1
    assert client.messages[0].role == "system"


@pytest.mark.anyio
async def test_structural_analyzer_returns_heuristic_sections_without_llm() -> None:
    analyzer = StructuralUnderstandingAnalyzer()

    result = await analyzer.analyze(
        MediaUnderstanding(
            transcript="Intro, explanation, and subscribe.",
            scenes=[SceneSegment(start_seconds=0, end_seconds=100)],
            duration_seconds=100,
        ),
    )

    assert result.hook is not None
    assert result.hook.start_seconds == 0
    assert result.hook.end_seconds == 15
    assert result.setup is not None
    assert result.main_content is not None
    assert result.cta is not None
    assert result.cta.start_seconds == 85
    assert result.cta.end_seconds == 100
    assert result.hook_detected is True
    assert "LLM structural analysis skipped" in result.notes[0]
