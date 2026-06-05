from typing import Literal

from pydantic import BaseModel, Field


def _scene_segments_factory() -> list["SceneSegment"]:
    return []


def _frame_snapshots_factory() -> list["FrameSnapshot"]:
    return []


def _audio_features_factory() -> list["AudioFeature"]:
    return []


def _content_entities_factory() -> list["ContentEntity"]:
    return []


def _visual_actions_factory() -> list["VisualAction"]:
    return []


def _spoken_claims_factory() -> list["SpokenClaim"]:
    return []


def _content_segments_factory() -> list["ContentSegmentInsight"]:
    return []


def _content_evidence_factory() -> list["ContentEvidence"]:
    return []


class SceneSegment(BaseModel):
    start_seconds: float
    end_seconds: float


class FrameSnapshot(BaseModel):
    timestamp_seconds: float
    path: str
    width: int | None = None
    height: int | None = None


class AudioFeature(BaseModel):
    name: str
    value: float | list[dict[str, float]] | None
    unit: str | None = None
    notes: list[str] = Field(default_factory=list)


class MediaUnderstanding(BaseModel):
    transcript: str = ""
    scenes: list[SceneSegment] = Field(default_factory=_scene_segments_factory)
    frames: list[FrameSnapshot] = Field(default_factory=_frame_snapshots_factory)
    audio_features: list[AudioFeature] = Field(default_factory=_audio_features_factory)
    duration_seconds: float | None = None
    detected_modalities: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class StructuralSection(BaseModel):
    title: str
    summary: str = ""
    start_seconds: float | None = None
    end_seconds: float | None = None
    evidence: list[str] = Field(default_factory=list)
    confidence: float | None = Field(default=None, ge=0, le=1)


class StructuralUnderstanding(BaseModel):
    hook: StructuralSection | None = None
    setup: StructuralSection | None = None
    main_content: StructuralSection | None = None
    cta: StructuralSection | None = None
    hook_detected: bool | None = None
    estimated_scene_count: int | None = None
    notes: list[str] = Field(default_factory=list)


ContentEvidenceSource = Literal["transcript", "frame", "scene", "audio", "structure", "inference"]


class ContentEvidence(BaseModel):
    source: ContentEvidenceSource
    description: str
    start_seconds: float | None = None
    end_seconds: float | None = None
    frame_path: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)


class ContentEntity(BaseModel):
    name: str
    type: str
    description: str = ""
    evidence: list[ContentEvidence] = Field(default_factory=_content_evidence_factory)
    confidence: float | None = Field(default=None, ge=0, le=1)


class VisualAction(BaseModel):
    actor: str | None = None
    action: str
    object: str | None = None
    start_seconds: float | None = None
    end_seconds: float | None = None
    evidence: list[ContentEvidence] = Field(default_factory=_content_evidence_factory)
    confidence: float | None = Field(default=None, ge=0, le=1)


class SpokenClaim(BaseModel):
    claim: str
    speaker: str | None = None
    start_seconds: float | None = None
    end_seconds: float | None = None
    evidence: list[ContentEvidence] = Field(default_factory=_content_evidence_factory)
    confidence: float | None = Field(default=None, ge=0, le=1)


class ContentOffer(BaseModel):
    name: str | None = None
    description: str = ""
    promised_outcome: str | None = None
    target_audience: str | None = None
    evidence: list[ContentEvidence] = Field(default_factory=_content_evidence_factory)
    confidence: float | None = Field(default=None, ge=0, le=1)


class ContentSegmentInsight(BaseModel):
    section: str
    summary: str = ""
    intent: str | None = None
    tone: str | None = None
    viewer_takeaway: str | None = None
    start_seconds: float | None = None
    end_seconds: float | None = None
    evidence: list[ContentEvidence] = Field(default_factory=_content_evidence_factory)
    confidence: float | None = Field(default=None, ge=0, le=1)


class ContentUnderstanding(BaseModel):
    summary: str = ""
    topics: list[str] = Field(default_factory=list)
    sentiment: str | None = None
    entities: list[ContentEntity] = Field(default_factory=_content_entities_factory)
    visual_actions: list[VisualAction] = Field(default_factory=_visual_actions_factory)
    spoken_claims: list[SpokenClaim] = Field(default_factory=_spoken_claims_factory)
    offer: ContentOffer | None = None
    narrative_arc: list[str] = Field(default_factory=list)
    segment_insights: list[ContentSegmentInsight] = Field(
        default_factory=_content_segments_factory,
    )
    content_intent: str | None = None
    tone: str | None = None
    viewer_takeaway: str | None = None
    evidence: list[ContentEvidence] = Field(default_factory=_content_evidence_factory)
    confidence: float | None = Field(default=None, ge=0, le=1)
    notes: list[str] = Field(default_factory=list)


class EngagementUnderstanding(BaseModel):
    likely_engagement_drivers: list[str] = Field(default_factory=list)
    friction_points: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class AudienceSimulation(BaseModel):
    personas: list[str] = Field(default_factory=list)
    predicted_reactions: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class ConsensusScoring(BaseModel):
    overall_score: int = Field(ge=0, le=100)
    confidence: float = Field(ge=0, le=1)
    notes: list[str] = Field(default_factory=list)


class Recommendations(BaseModel):
    priority_actions: list[str] = Field(default_factory=list)
    experiments: list[str] = Field(default_factory=list)


class EngagementAnalysisReport(BaseModel):
    summary: str
    media: MediaUnderstanding
    structure: StructuralUnderstanding
    content: ContentUnderstanding
    engagement: EngagementUnderstanding
    audience: AudienceSimulation
    scoring: ConsensusScoring
    recommendations: Recommendations
