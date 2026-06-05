import pytest

from app.pipelines.engagement_analysis.content_analyzer import ContentUnderstandingAnalyzer
from app.pipelines.engagement_analysis.llm_client import ChatMessage
from app.pipelines.engagement_analysis.models import (
    FrameSnapshot,
    MediaUnderstanding,
    SceneSegment,
    StructuralSection,
    StructuralUnderstanding,
)


class FakeChatClient:
    def __init__(self, response: str) -> None:
        self.response = response
        self.messages: list[ChatMessage] = []
        self.json_schema: dict[str, object] | None = None

    async def complete_json(
        self,
        messages: list[ChatMessage],
        json_schema: dict[str, object] | None = None,
    ) -> str:
        self.messages = messages
        self.json_schema = json_schema
        return self.response


@pytest.mark.anyio
async def test_content_analyzer_uses_openai_compatible_json_response() -> None:
    client = FakeChatClient(
        """
        {
          "summary": "The video teaches a retention framework and promotes a checklist.",
          "topics": ["retention", "creator growth"],
          "sentiment": "confident",
          "entities": [
            {
              "name": "Retention checklist",
              "type": "lead magnet",
              "description": "Downloadable checklist promoted by the presenter.",
              "evidence": [
                {
                  "source": "transcript",
                  "description": "Presenter says to download the checklist.",
                  "start_seconds": 50,
                  "end_seconds": 60,
                  "frame_path": null,
                  "confidence": 0.86
                }
              ],
              "confidence": 0.84
            }
          ],
          "visual_actions": [
            {
              "actor": "Presenter",
              "action": "points to an on-screen checklist",
              "object": "checklist graphic",
              "start_seconds": 8,
              "end_seconds": 10,
              "evidence": [
                {
                  "source": "frame",
                  "description": "Frame shows checklist graphic beside presenter.",
                  "start_seconds": 8,
                  "end_seconds": 8,
                  "frame_path": "frames/frame_001.jpg",
                  "confidence": 0.8
                }
              ],
              "confidence": 0.78
            }
          ],
          "spoken_claims": [
            {
              "claim": "This framework can double retention.",
              "speaker": "Presenter",
              "start_seconds": 0,
              "end_seconds": 4,
              "evidence": [
                {
                  "source": "transcript",
                  "description": "The opening promises to double retention.",
                  "start_seconds": 0,
                  "end_seconds": 4,
                  "frame_path": null,
                  "confidence": 0.91
                }
              ],
              "confidence": 0.9
            }
          ],
          "offer": {
            "name": "Retention checklist",
            "description": "A downloadable checklist for creators.",
            "promised_outcome": "Improve retention.",
            "target_audience": "Video creators",
            "evidence": [],
            "confidence": 0.82
          },
          "narrative_arc": [
            "Promises a retention outcome.",
            "Explains the framework.",
            "Asks viewers to download the checklist."
          ],
          "segment_insights": [
            {
              "section": "Hook",
              "summary": "The hook promises a concrete improvement.",
              "intent": "Earn attention with a measurable outcome.",
              "tone": "direct",
              "viewer_takeaway": "Retention can be improved.",
              "start_seconds": 0,
              "end_seconds": 4,
              "evidence": [],
              "confidence": 0.88
            }
          ],
          "content_intent": "Teach and convert viewers to a checklist download.",
          "tone": "confident",
          "viewer_takeaway": "Use the framework and download the checklist.",
          "evidence": [],
          "confidence": 0.87,
          "notes": ["Transcript and frame evidence were available."]
        }
        """,
    )
    analyzer = ContentUnderstandingAnalyzer(chat_client=client)

    result = await analyzer.analyze(
        MediaUnderstanding(
            transcript="This framework can double retention. Download the checklist.",
            scenes=[SceneSegment(start_seconds=0, end_seconds=60)],
            frames=[
                FrameSnapshot(
                    timestamp_seconds=8,
                    path="frames/frame_001.jpg",
                    width=1920,
                    height=1080,
                ),
            ],
            duration_seconds=60,
        ),
        StructuralUnderstanding(
            hook=StructuralSection(
                title="Hook",
                summary="Opens with the core promise.",
                start_seconds=0,
                end_seconds=4,
                evidence=["double retention"],
                confidence=0.91,
            ),
        ),
    )

    assert result.summary == "The video teaches a retention framework and promotes a checklist."
    assert result.topics == ["retention", "creator growth"]
    assert result.entities[0].name == "Retention checklist"
    assert result.visual_actions[0].action == "points to an on-screen checklist"
    assert result.spoken_claims[0].claim == "This framework can double retention."
    assert result.offer is not None
    assert result.offer.target_audience == "Video creators"
    assert result.segment_insights[0].section == "Hook"
    assert result.confidence == 0.87
    assert client.messages[0].role == "system"
    assert client.json_schema is not None
    assert client.json_schema["type"] == "json_schema"


@pytest.mark.anyio
async def test_content_analyzer_returns_heuristic_content_without_llm() -> None:
    analyzer = ContentUnderstandingAnalyzer()

    result = await analyzer.analyze(
        MediaUnderstanding(
            transcript=(
                "I can double your retention. First, rewrite your opening. "
                "Download the checklist."
            ),
            frames=[FrameSnapshot(timestamp_seconds=3, path="frames/frame_001.jpg")],
            duration_seconds=30,
        ),
        StructuralUnderstanding(
            hook=StructuralSection(
                title="Hook",
                summary="Opening segment intended to earn attention.",
                start_seconds=0,
                end_seconds=5,
                confidence=0.2,
            ),
            cta=StructuralSection(
                title="CTA",
                summary="Closing action or next-step segment.",
                start_seconds=25,
                end_seconds=30,
                confidence=0.2,
            ),
        ),
    )

    assert result.summary == "I can double your retention. First, rewrite your opening."
    assert "retention" in result.topics
    assert result.sentiment == "positive"
    assert result.tone == "promotional"
    assert result.visual_actions[0].evidence[0].frame_path == "frames/frame_001.jpg"
    assert result.spoken_claims[0].claim == "I can double your retention."
    assert result.segment_insights[0].section == "Hook"
    assert result.confidence == 0.25
    assert "LLM content analysis skipped" in result.notes[0]
