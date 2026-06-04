from dataclasses import dataclass
from pathlib import Path

from app.pipelines.engagement_analysis.models import (
    AudienceSimulation,
    ConsensusScoring,
    ContentUnderstanding,
    EngagementAnalysisReport,
    EngagementUnderstanding,
    MediaUnderstanding,
    Recommendations,
    StructuralUnderstanding,
)


@dataclass(slots=True)
class EngagementAnalysisContext:
    analysis_id: str
    video_path: Path
    original_filename: str
    content_type: str
    size_bytes: int
    media: MediaUnderstanding | None = None
    structure: StructuralUnderstanding | None = None
    content: ContentUnderstanding | None = None
    engagement: EngagementUnderstanding | None = None
    audience: AudienceSimulation | None = None
    scoring: ConsensusScoring | None = None
    recommendations: Recommendations | None = None
    report: EngagementAnalysisReport | None = None
