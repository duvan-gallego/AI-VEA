from pydantic import BaseModel, Field


def _scene_segments_factory() -> list["SceneSegment"]:
    return []


def _frame_snapshots_factory() -> list["FrameSnapshot"]:
    return []


def _audio_features_factory() -> list["AudioFeature"]:
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


class ContentUnderstanding(BaseModel):
    topics: list[str] = Field(default_factory=list)
    sentiment: str | None = None
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
