import json
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field

from app.pipelines.engagement_analysis.llm_client import ChatCompletionClient, ChatMessage
from app.pipelines.engagement_analysis.models import (
    AudioFeature,
    MediaUnderstanding,
    StructuralSection,
    StructuralUnderstanding,
)

TRANSCRIPT_CONTEXT_LIMIT = 12_000


@dataclass(frozen=True, slots=True)
class StructuralAnalysisOptions:
    enabled: bool = True


class StructuralAnalysisResponse(BaseModel):
    hook: StructuralSection | None = None
    setup: StructuralSection | None = None
    main_content: StructuralSection | None = None
    cta: StructuralSection | None = None
    notes: list[str] = Field(default_factory=list)


class StructuralUnderstandingAnalyzer:
    def __init__(
        self,
        chat_client: ChatCompletionClient | None = None,
        options: StructuralAnalysisOptions | None = None,
    ) -> None:
        self._chat_client = chat_client
        self._options = options or StructuralAnalysisOptions()

    async def analyze(self, media: MediaUnderstanding | None) -> StructuralUnderstanding:
        if media is None:
            return StructuralUnderstanding(
                notes=["Structural analysis skipped because media understanding is missing."],
            )

        if self._chat_client is None or not self._options.enabled:
            return _build_heuristic_structure(
                media,
                notes=[
                    "LLM structural analysis skipped because LLM settings are not configured.",
                    "Returned heuristic section placeholders from media metadata.",
                ],
            )

        try:
            raw_response = await self._chat_client.complete_json(_build_messages(media))
            parsed_response = StructuralAnalysisResponse.model_validate_json(raw_response)
        except Exception as error:
            return _build_heuristic_structure(
                media,
                notes=[
                    f"LLM structural analysis skipped: {error}",
                    "Returned heuristic section placeholders from media metadata.",
                ],
            )

        return StructuralUnderstanding(
            hook=parsed_response.hook,
            setup=parsed_response.setup,
            main_content=parsed_response.main_content,
            cta=parsed_response.cta,
            hook_detected=parsed_response.hook is not None,
            estimated_scene_count=len(media.scenes),
            notes=parsed_response.notes,
        )


def _build_messages(media: MediaUnderstanding) -> list[ChatMessage]:
    return [
        ChatMessage(
            role="system",
            content=(
                "You analyze short-form and long-form video structure for engagement. "
                "Return only valid JSON. Identify the Hook, Setup, Main content, and CTA. "
                "Use null for a section only when there is not enough evidence."
            ),
        ),
        ChatMessage(
            role="user",
            content=_build_user_prompt(media),
        ),
    ]


def _build_user_prompt(media: MediaUnderstanding) -> str:
    schema = {
        "hook": _section_schema(),
        "setup": _section_schema(),
        "main_content": _section_schema(),
        "cta": _section_schema(),
        "notes": ["short caveats about evidence quality"],
    }
    payload = {
        "transcript": _truncate(media.transcript),
        "duration_seconds": media.duration_seconds,
        "scenes": [
            {
                "start_seconds": scene.start_seconds,
                "end_seconds": scene.end_seconds,
            }
            for scene in media.scenes[:50]
        ],
        "frames": [
            {
                "timestamp_seconds": frame.timestamp_seconds,
                "width": frame.width,
                "height": frame.height,
            }
            for frame in media.frames[:50]
        ],
        "audio_features": [_audio_feature_payload(feature) for feature in media.audio_features],
        "media_notes": media.notes,
    }

    return (
        "Analyze how this video is organized. Prefer transcript evidence, then scenes, "
        "frames, audio pacing, silence, energy, and tempo. Return JSON matching this schema:\n"
        f"{json.dumps(schema)}\n\n"
        f"Media understanding input:\n{json.dumps(payload)}"
    )


def _section_schema() -> dict[str, Any]:
    return {
        "title": "short section label",
        "summary": "what this section does",
        "start_seconds": 0,
        "end_seconds": 10,
        "evidence": ["specific transcript, scene, frame, or audio evidence"],
        "confidence": 0.8,
    }


def _audio_feature_payload(feature: AudioFeature) -> dict[str, Any]:
    return {
        "name": feature.name,
        "value": feature.value,
        "unit": feature.unit,
        "notes": feature.notes,
    }


def _truncate(value: str) -> str:
    if len(value) <= TRANSCRIPT_CONTEXT_LIMIT:
        return value
    return f"{value[:TRANSCRIPT_CONTEXT_LIMIT]}\n[Transcript truncated]"


def _build_heuristic_structure(
    media: MediaUnderstanding,
    *,
    notes: list[str],
) -> StructuralUnderstanding:
    duration = media.duration_seconds or _duration_from_scenes(media)
    return StructuralUnderstanding(
        hook=_section_from_ratio(
            title="Hook",
            summary="Opening segment intended to earn attention.",
            duration_seconds=duration,
            start_ratio=0,
            end_ratio=0.15,
        ),
        setup=_section_from_ratio(
            title="Setup",
            summary="Context-setting segment before the core message.",
            duration_seconds=duration,
            start_ratio=0.15,
            end_ratio=0.3,
        ),
        main_content=_section_from_ratio(
            title="Main content",
            summary="Primary value, story, or explanation segment.",
            duration_seconds=duration,
            start_ratio=0.3,
            end_ratio=0.85,
        ),
        cta=_section_from_ratio(
            title="CTA",
            summary="Closing action or next-step segment.",
            duration_seconds=duration,
            start_ratio=0.85,
            end_ratio=1,
        ),
        hook_detected=bool(media.transcript or media.scenes or media.frames),
        estimated_scene_count=len(media.scenes),
        notes=notes,
    )


def _section_from_ratio(
    *,
    title: str,
    summary: str,
    duration_seconds: float | None,
    start_ratio: float,
    end_ratio: float,
) -> StructuralSection:
    start_seconds = duration_seconds * start_ratio if duration_seconds is not None else None
    end_seconds = duration_seconds * end_ratio if duration_seconds is not None else None
    return StructuralSection(
        title=title,
        summary=summary,
        start_seconds=start_seconds,
        end_seconds=end_seconds,
        confidence=0.2,
    )


def _duration_from_scenes(media: MediaUnderstanding) -> float | None:
    if not media.scenes:
        return None
    return max(scene.end_seconds for scene in media.scenes)
