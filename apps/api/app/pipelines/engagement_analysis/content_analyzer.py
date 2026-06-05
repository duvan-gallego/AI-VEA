import json
import logging
import re
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field

from app.pipelines.engagement_analysis.llm_client import ChatCompletionClient, ChatMessage
from app.pipelines.engagement_analysis.models import (
    AudioFeature,
    ContentEvidence,
    ContentSegmentInsight,
    ContentUnderstanding,
    FrameSnapshot,
    MediaUnderstanding,
    SpokenClaim,
    StructuralSection,
    StructuralUnderstanding,
    VisualAction,
)

TRANSCRIPT_CONTEXT_LIMIT = 12_000
MAX_FRAME_CONTEXT = 50
MAX_SCENE_CONTEXT = 50
logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ContentAnalysisOptions:
    enabled: bool = True


class ContentAnalysisResponse(BaseModel):
    summary: str = ""
    topics: list[str] = Field(default_factory=list)
    sentiment: str | None = None
    entities: list[Any] = Field(default_factory=list)
    visual_actions: list[Any] = Field(default_factory=list)
    spoken_claims: list[Any] = Field(default_factory=list)
    offer: dict[str, Any] | None = None
    narrative_arc: list[str] = Field(default_factory=list)
    segment_insights: list[Any] = Field(default_factory=list)
    content_intent: str | None = None
    tone: str | None = None
    viewer_takeaway: str | None = None
    evidence: list[Any] = Field(default_factory=list)
    confidence: float | None = Field(default=None, ge=0, le=1)
    notes: list[str] = Field(default_factory=list)


class ContentUnderstandingAnalyzer:
    def __init__(
        self,
        chat_client: ChatCompletionClient | None = None,
        options: ContentAnalysisOptions | None = None,
    ) -> None:
        self._chat_client = chat_client
        self._options = options or ContentAnalysisOptions()

    async def analyze(
        self,
        media: MediaUnderstanding | None,
        structure: StructuralUnderstanding | None,
    ) -> ContentUnderstanding:
        if media is None:
            return ContentUnderstanding(
                notes=["Content analysis skipped because media understanding is missing."],
            )

        if self._chat_client is None or not self._options.enabled:
            logger.info("Skipping LLM content analysis because chat client is not configured")
            return _build_heuristic_content(
                media,
                structure,
                notes=[
                    "LLM content analysis skipped because LLM settings are not configured.",
                    "Returned heuristic content placeholders from media and structure metadata.",
                ],
            )

        try:
            logger.info(
                "Starting LLM content analysis transcript_chars=%s scenes=%s frames=%s "
                "audio_features=%s structure=%s",
                len(media.transcript),
                len(media.scenes),
                len(media.frames),
                len(media.audio_features),
                structure is not None,
            )
            raw_response = await self._chat_client.complete_json(
                _build_messages(media, structure),
                json_schema=_build_content_response_format(),
            )
            parsed_response = ContentAnalysisResponse.model_validate_json(raw_response)
            content = ContentUnderstanding.model_validate(parsed_response.model_dump())
        except Exception as error:
            logger.warning("LLM content analysis skipped: %s", error)
            return _build_heuristic_content(
                media,
                structure,
                notes=[
                    f"LLM content analysis skipped: {error}",
                    "Returned heuristic content placeholders from media and structure metadata.",
                ],
            )

        logger.info(
            "Completed LLM content analysis topics=%s claims=%s visual_actions=%s confidence=%s",
            len(content.topics),
            len(content.spoken_claims),
            len(content.visual_actions),
            content.confidence,
        )
        return content


def _build_messages(
    media: MediaUnderstanding,
    structure: StructuralUnderstanding | None,
) -> list[ChatMessage]:
    return [
        ChatMessage(
            role="system",
            content=(
                "You analyze what happens in videos for an engagement pipeline. "
                "Return only valid JSON. Ground every meaningful observation in evidence. "
                "Separate observable content from inferred intent."
            ),
        ),
        ChatMessage(role="user", content=_build_user_prompt(media, structure)),
    ]


def _build_user_prompt(
    media: MediaUnderstanding,
    structure: StructuralUnderstanding | None,
) -> str:
    payload = {
        "transcript": _truncate(media.transcript),
        "duration_seconds": media.duration_seconds,
        "structure": _structure_payload(structure),
        "scenes": [
            {
                "start_seconds": scene.start_seconds,
                "end_seconds": scene.end_seconds,
            }
            for scene in media.scenes[:MAX_SCENE_CONTEXT]
        ],
        "frames": [_frame_payload(frame) for frame in media.frames[:MAX_FRAME_CONTEXT]],
        "audio_features": [_audio_feature_payload(feature) for feature in media.audio_features],
        "media_notes": media.notes,
    }

    return (
        "Explain what is happening in this video. Identify topics, visible actions, spoken "
        "claims, entities, offers, narrative progression, intent, tone, and viewer takeaway. "
        "Use null or empty arrays when evidence is insufficient. Prefer transcript evidence, "
        "then structural sections, then scene/frame/audio evidence.\n\n"
        f"Input artifact:\n{json.dumps(payload)}"
    )


def _structure_payload(structure: StructuralUnderstanding | None) -> dict[str, Any] | None:
    if structure is None:
        return None
    return {
        "hook": _section_payload(structure.hook),
        "setup": _section_payload(structure.setup),
        "main_content": _section_payload(structure.main_content),
        "cta": _section_payload(structure.cta),
        "hook_detected": structure.hook_detected,
        "estimated_scene_count": structure.estimated_scene_count,
        "notes": structure.notes,
    }


def _section_payload(section: StructuralSection | None) -> dict[str, Any] | None:
    if section is None:
        return None
    return {
        "title": section.title,
        "summary": section.summary,
        "start_seconds": section.start_seconds,
        "end_seconds": section.end_seconds,
        "evidence": section.evidence,
        "confidence": section.confidence,
    }


def _frame_payload(frame: FrameSnapshot) -> dict[str, Any]:
    return {
        "timestamp_seconds": frame.timestamp_seconds,
        "path": frame.path,
        "width": frame.width,
        "height": frame.height,
    }


def _audio_feature_payload(feature: AudioFeature) -> dict[str, Any]:
    return {
        "name": feature.name,
        "value": feature.value,
        "unit": feature.unit,
        "notes": feature.notes,
    }


def _build_content_response_format() -> dict[str, Any]:
    evidence_schema = {
        "type": "object",
        "properties": {
            "source": {
                "type": "string",
                "enum": ["transcript", "frame", "scene", "audio", "structure", "inference"],
            },
            "description": {"type": "string"},
            "start_seconds": {"type": ["number", "null"]},
            "end_seconds": {"type": ["number", "null"]},
            "frame_path": {"type": ["string", "null"]},
            "confidence": {"type": ["number", "null"], "minimum": 0, "maximum": 1},
        },
        "required": [
            "source",
            "description",
            "start_seconds",
            "end_seconds",
            "frame_path",
            "confidence",
        ],
        "additionalProperties": False,
    }
    evidence_array_schema = {"type": "array", "items": evidence_schema}

    entity_schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "type": {"type": "string"},
            "description": {"type": "string"},
            "evidence": evidence_array_schema,
            "confidence": {"type": ["number", "null"], "minimum": 0, "maximum": 1},
        },
        "required": ["name", "type", "description", "evidence", "confidence"],
        "additionalProperties": False,
    }
    visual_action_schema = {
        "type": "object",
        "properties": {
            "actor": {"type": ["string", "null"]},
            "action": {"type": "string"},
            "object": {"type": ["string", "null"]},
            "start_seconds": {"type": ["number", "null"]},
            "end_seconds": {"type": ["number", "null"]},
            "evidence": evidence_array_schema,
            "confidence": {"type": ["number", "null"], "minimum": 0, "maximum": 1},
        },
        "required": [
            "actor",
            "action",
            "object",
            "start_seconds",
            "end_seconds",
            "evidence",
            "confidence",
        ],
        "additionalProperties": False,
    }
    spoken_claim_schema = {
        "type": "object",
        "properties": {
            "claim": {"type": "string"},
            "speaker": {"type": ["string", "null"]},
            "start_seconds": {"type": ["number", "null"]},
            "end_seconds": {"type": ["number", "null"]},
            "evidence": evidence_array_schema,
            "confidence": {"type": ["number", "null"], "minimum": 0, "maximum": 1},
        },
        "required": [
            "claim",
            "speaker",
            "start_seconds",
            "end_seconds",
            "evidence",
            "confidence",
        ],
        "additionalProperties": False,
    }
    offer_schema = {
        "type": ["object", "null"],
        "properties": {
            "name": {"type": ["string", "null"]},
            "description": {"type": "string"},
            "promised_outcome": {"type": ["string", "null"]},
            "target_audience": {"type": ["string", "null"]},
            "evidence": evidence_array_schema,
            "confidence": {"type": ["number", "null"], "minimum": 0, "maximum": 1},
        },
        "required": [
            "name",
            "description",
            "promised_outcome",
            "target_audience",
            "evidence",
            "confidence",
        ],
        "additionalProperties": False,
    }
    segment_insight_schema = {
        "type": "object",
        "properties": {
            "section": {"type": "string"},
            "summary": {"type": "string"},
            "intent": {"type": ["string", "null"]},
            "tone": {"type": ["string", "null"]},
            "viewer_takeaway": {"type": ["string", "null"]},
            "start_seconds": {"type": ["number", "null"]},
            "end_seconds": {"type": ["number", "null"]},
            "evidence": evidence_array_schema,
            "confidence": {"type": ["number", "null"], "minimum": 0, "maximum": 1},
        },
        "required": [
            "section",
            "summary",
            "intent",
            "tone",
            "viewer_takeaway",
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
            "name": "engagement_analysis_content",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string"},
                    "topics": {"type": "array", "items": {"type": "string"}},
                    "sentiment": {"type": ["string", "null"]},
                    "entities": {"type": "array", "items": entity_schema},
                    "visual_actions": {"type": "array", "items": visual_action_schema},
                    "spoken_claims": {"type": "array", "items": spoken_claim_schema},
                    "offer": offer_schema,
                    "narrative_arc": {"type": "array", "items": {"type": "string"}},
                    "segment_insights": {"type": "array", "items": segment_insight_schema},
                    "content_intent": {"type": ["string", "null"]},
                    "tone": {"type": ["string", "null"]},
                    "viewer_takeaway": {"type": ["string", "null"]},
                    "evidence": evidence_array_schema,
                    "confidence": {"type": ["number", "null"], "minimum": 0, "maximum": 1},
                    "notes": {"type": "array", "items": {"type": "string"}},
                },
                "required": [
                    "summary",
                    "topics",
                    "sentiment",
                    "entities",
                    "visual_actions",
                    "spoken_claims",
                    "offer",
                    "narrative_arc",
                    "segment_insights",
                    "content_intent",
                    "tone",
                    "viewer_takeaway",
                    "evidence",
                    "confidence",
                    "notes",
                ],
                "additionalProperties": False,
            },
        },
    }


def _truncate(value: str) -> str:
    if len(value) <= TRANSCRIPT_CONTEXT_LIMIT:
        return value
    return f"{value[:TRANSCRIPT_CONTEXT_LIMIT]}\n[Transcript truncated]"


def _build_heuristic_content(
    media: MediaUnderstanding,
    structure: StructuralUnderstanding | None,
    *,
    notes: list[str],
) -> ContentUnderstanding:
    transcript = media.transcript.strip()
    evidence = _transcript_evidence(transcript, media.duration_seconds)
    claims = _spoken_claims_from_transcript(transcript, evidence)
    visual_actions = _visual_actions_from_frames(media.frames)

    return ContentUnderstanding(
        summary=_summary_from_transcript(transcript),
        topics=_topics_from_transcript(transcript),
        sentiment=_sentiment_from_transcript(transcript),
        visual_actions=visual_actions,
        spoken_claims=claims,
        narrative_arc=_narrative_arc_from_structure(structure),
        segment_insights=_segment_insights_from_structure(structure),
        content_intent=_content_intent_from_structure(structure),
        tone=_tone_from_transcript(transcript),
        viewer_takeaway=_viewer_takeaway_from_transcript(transcript, structure),
        evidence=[evidence] if evidence is not None else [],
        confidence=0.25 if transcript or media.frames or structure is not None else 0,
        notes=notes,
    )


def _summary_from_transcript(transcript: str) -> str:
    sentences = _sentences(transcript)
    if not sentences:
        return ""
    return " ".join(sentences[:2])


def _topics_from_transcript(transcript: str) -> list[str]:
    words = [
        word
        for word in re.findall(r"[A-Za-z][A-Za-z'-]{3,}", transcript.lower())
        if word not in _STOP_WORDS
    ]
    counts: dict[str, int] = {}
    for word in words:
        counts[word] = counts.get(word, 0) + 1
    return [
        word
        for word, _count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:5]
    ]


def _sentiment_from_transcript(transcript: str) -> str | None:
    lowered = transcript.lower()
    positive_hits = sum(1 for word in _POSITIVE_WORDS if word in lowered)
    negative_hits = sum(1 for word in _NEGATIVE_WORDS if word in lowered)
    if positive_hits > negative_hits:
        return "positive"
    if negative_hits > positive_hits:
        return "negative"
    if transcript:
        return "neutral"
    return None


def _tone_from_transcript(transcript: str) -> str | None:
    lowered = transcript.lower()
    if any(word in lowered for word in ("download", "subscribe", "buy", "sign up", "try")):
        return "promotional"
    if any(word in lowered for word in ("how to", "step", "first", "second", "learn")):
        return "instructional"
    if transcript:
        return "informational"
    return None


def _spoken_claims_from_transcript(
    transcript: str,
    evidence: ContentEvidence | None,
) -> list[SpokenClaim]:
    claim_markers = (
        "can ",
        "will ",
        "should ",
        "helps ",
        "improves ",
        "increase",
        "reduce",
        "double",
        "best",
    )
    claims: list[SpokenClaim] = []
    for sentence in _sentences(transcript):
        if any(marker in sentence.lower() for marker in claim_markers):
            claims.append(
                SpokenClaim(
                    claim=sentence,
                    speaker=None,
                    evidence=[evidence] if evidence is not None else [],
                    confidence=0.35,
                ),
            )
    return claims[:5]


def _visual_actions_from_frames(frames: list[FrameSnapshot]) -> list[VisualAction]:
    return [
        VisualAction(
            action="key frame available for visual inspection",
            start_seconds=frame.timestamp_seconds,
            end_seconds=frame.timestamp_seconds,
            evidence=[
                ContentEvidence(
                    source="frame",
                    description="Key frame extracted from the video.",
                    start_seconds=frame.timestamp_seconds,
                    end_seconds=frame.timestamp_seconds,
                    frame_path=frame.path,
                    confidence=0.2,
                ),
            ],
            confidence=0.2,
        )
        for frame in frames[:5]
    ]


def _narrative_arc_from_structure(structure: StructuralUnderstanding | None) -> list[str]:
    if structure is None:
        return []
    return [
        section.summary
        for section in (structure.hook, structure.setup, structure.main_content, structure.cta)
        if section is not None and section.summary
    ]


def _segment_insights_from_structure(
    structure: StructuralUnderstanding | None,
) -> list[ContentSegmentInsight]:
    if structure is None:
        return []

    insights: list[ContentSegmentInsight] = []
    for section_name, section in (
        ("Hook", structure.hook),
        ("Setup", structure.setup),
        ("Main content", structure.main_content),
        ("CTA", structure.cta),
    ):
        if section is None:
            continue
        insights.append(
            ContentSegmentInsight(
                section=section_name,
                summary=section.summary,
                intent=f"{section_name} content role inferred from structural analysis.",
                start_seconds=section.start_seconds,
                end_seconds=section.end_seconds,
                evidence=[
                    ContentEvidence(
                        source="structure",
                        description=section.summary or section.title,
                        start_seconds=section.start_seconds,
                        end_seconds=section.end_seconds,
                        confidence=section.confidence,
                    ),
                ],
                confidence=section.confidence,
            ),
        )
    return insights


def _content_intent_from_structure(structure: StructuralUnderstanding | None) -> str | None:
    if structure is None:
        return None
    if structure.cta is not None:
        return "Inform or persuade viewers toward a next action."
    if structure.main_content is not None:
        return "Deliver the main message or explanation."
    return None


def _viewer_takeaway_from_transcript(
    transcript: str,
    structure: StructuralUnderstanding | None,
) -> str | None:
    if structure is not None and structure.cta is not None and structure.cta.summary:
        return structure.cta.summary
    sentences = _sentences(transcript)
    return sentences[-1] if sentences else None


def _transcript_evidence(
    transcript: str,
    duration_seconds: float | None,
) -> ContentEvidence | None:
    if not transcript:
        return None
    return ContentEvidence(
        source="transcript",
        description=_summary_from_transcript(transcript),
        start_seconds=0,
        end_seconds=duration_seconds,
        confidence=0.35,
    )


def _sentences(transcript: str) -> list[str]:
    return [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+", transcript.strip())
        if sentence.strip()
    ]


_STOP_WORDS = {
    "about",
    "after",
    "again",
    "because",
    "before",
    "could",
    "first",
    "from",
    "have",
    "into",
    "just",
    "like",
    "more",
    "that",
    "their",
    "there",
    "this",
    "through",
    "with",
    "your",
}

_POSITIVE_WORDS = {
    "better",
    "best",
    "double",
    "easy",
    "good",
    "great",
    "grow",
    "improve",
    "increase",
    "win",
}

_NEGATIVE_WORDS = {
    "bad",
    "drop",
    "fail",
    "hard",
    "lose",
    "problem",
    "risk",
    "worse",
}
