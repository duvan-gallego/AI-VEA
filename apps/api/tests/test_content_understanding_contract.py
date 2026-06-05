from pathlib import Path

import pytest
from pydantic import ValidationError

from app.pipelines.engagement_analysis.context import EngagementAnalysisContext
from app.pipelines.engagement_analysis.models import (
    ContentEntity,
    ContentEvidence,
    ContentOffer,
    ContentSegmentInsight,
    ContentUnderstanding,
    MediaUnderstanding,
    SpokenClaim,
    VisualAction,
)
from app.pipelines.engagement_analysis.stages.content_understanding import (
    ContentUnderstandingStage,
)


def test_content_understanding_defaults_are_backward_compatible() -> None:
    content = ContentUnderstanding(topics=["retention"], sentiment="urgent")

    assert content.summary == ""
    assert content.topics == ["retention"]
    assert content.sentiment == "urgent"
    assert content.entities == []
    assert content.visual_actions == []
    assert content.spoken_claims == []
    assert content.offer is None
    assert content.confidence is None


def test_content_understanding_captures_evidence_grounded_artifacts() -> None:
    evidence = ContentEvidence(
        source="transcript",
        description="Speaker promises to double retention.",
        start_seconds=1.5,
        end_seconds=4.0,
        confidence=0.92,
    )

    content = ContentUnderstanding(
        summary="The video explains a retention improvement framework.",
        topics=["retention", "creator growth"],
        sentiment="confident",
        entities=[
            ContentEntity(
                name="Retention checklist",
                type="lead magnet",
                description="Downloadable resource promoted near the end.",
                evidence=[evidence],
                confidence=0.86,
            ),
        ],
        visual_actions=[
            VisualAction(
                actor="Presenter",
                action="points at checklist graphic",
                object="checklist",
                start_seconds=8,
                end_seconds=10,
                evidence=[
                    ContentEvidence(
                        source="frame",
                        description="Frame shows checklist graphic beside presenter.",
                        frame_path="storage/uploads/analysis-1/frames/frame_002.jpg",
                        confidence=0.8,
                    ),
                ],
                confidence=0.78,
            ),
        ],
        spoken_claims=[
            SpokenClaim(
                claim="This framework can double retention.",
                speaker="Presenter",
                start_seconds=1.5,
                end_seconds=4,
                evidence=[evidence],
                confidence=0.9,
            ),
        ],
        offer=ContentOffer(
            name="Retention checklist",
            description="A downloadable checklist for improving video retention.",
            promised_outcome="Improve retention.",
            target_audience="Video creators",
            evidence=[evidence],
            confidence=0.84,
        ),
        narrative_arc=[
            "Introduces a retention problem.",
            "Explains the framework.",
            "Invites viewers to download the checklist.",
        ],
        segment_insights=[
            ContentSegmentInsight(
                section="Hook",
                summary="The opening promises a specific retention outcome.",
                intent="Earn attention through a concrete result.",
                tone="direct",
                viewer_takeaway="There is a practical way to improve retention.",
                start_seconds=0,
                end_seconds=5,
                evidence=[evidence],
                confidence=0.88,
            ),
        ],
        content_intent="Teach and convert viewers to a download.",
        tone="confident",
        viewer_takeaway="Use the framework and download the checklist.",
        evidence=[evidence],
        confidence=0.87,
    )

    payload = content.model_dump()

    assert payload["summary"] == "The video explains a retention improvement framework."
    assert payload["entities"][0]["type"] == "lead magnet"
    assert payload["visual_actions"][0]["evidence"][0]["source"] == "frame"
    assert payload["spoken_claims"][0]["claim"] == "This framework can double retention."
    assert payload["offer"]["target_audience"] == "Video creators"
    assert payload["segment_insights"][0]["section"] == "Hook"


def test_content_evidence_rejects_unknown_sources() -> None:
    try:
        ContentEvidence(source="guess", description="Unsupported source.")
    except ValidationError as error:
        assert "source" in str(error)
    else:
        raise AssertionError("Expected ContentEvidence to reject unknown sources.")


@pytest.mark.anyio
async def test_content_understanding_stage_returns_placeholder_contract(tmp_path: Path) -> None:
    context = EngagementAnalysisContext(
        analysis_id="analysis-1",
        video_path=tmp_path / "sample.mp4",
        original_filename="sample.mp4",
        content_type="video/mp4",
        size_bytes=128,
        media=MediaUnderstanding(transcript="Learn how to improve retention."),
    )

    result = await ContentUnderstandingStage().run(context)

    assert result.content is not None
    assert result.content.summary == "Learn how to improve retention."
    assert result.content.entities == []
    assert result.content.confidence == 0.25
