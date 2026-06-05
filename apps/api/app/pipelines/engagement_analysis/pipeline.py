from collections.abc import Sequence

from app.pipelines.engagement_analysis.context import EngagementAnalysisContext
from app.pipelines.engagement_analysis.llm_client import (
    OpenAICompatibleChatClient,
    OpenAICompatibleChatOptions,
)
from app.pipelines.engagement_analysis.media_extractor import (
    MediaExtractionOptions,
    MediaUnderstandingExtractor,
)
from app.pipelines.engagement_analysis.stage import EngagementAnalysisStage
from app.pipelines.engagement_analysis.stages.audience_simulation import AudienceSimulationStage
from app.pipelines.engagement_analysis.stages.consensus_scoring import ConsensusScoringStage
from app.pipelines.engagement_analysis.stages.content_understanding import ContentUnderstandingStage
from app.pipelines.engagement_analysis.stages.engagement_understanding import (
    EngagementUnderstandingStage,
)
from app.pipelines.engagement_analysis.stages.media_understanding import MediaUnderstandingStage
from app.pipelines.engagement_analysis.stages.recommendations import RecommendationsStage
from app.pipelines.engagement_analysis.stages.structural_understanding import (
    StructuralUnderstandingStage,
)
from app.pipelines.engagement_analysis.structural_analyzer import StructuralUnderstandingAnalyzer


class EngagementAnalysisPipeline:
    def __init__(self, stages: Sequence[EngagementAnalysisStage]) -> None:
        self._stages = stages

    async def run(self, context: EngagementAnalysisContext) -> EngagementAnalysisContext:
        current_context = context

        for stage in self._stages:
            current_context = await stage.run(current_context)

        return current_context


def build_default_engagement_analysis_pipeline(
    media_options: MediaExtractionOptions | None = None,
    llm_options: OpenAICompatibleChatOptions | None = None,
) -> EngagementAnalysisPipeline:
    structural_analyzer = StructuralUnderstandingAnalyzer(
        chat_client=OpenAICompatibleChatClient(llm_options) if llm_options is not None else None,
    )

    return EngagementAnalysisPipeline(
        stages=[
            MediaUnderstandingStage(
                extractor=MediaUnderstandingExtractor(options=media_options),
            ),
            StructuralUnderstandingStage(analyzer=structural_analyzer),
            ContentUnderstandingStage(),
            EngagementUnderstandingStage(),
            AudienceSimulationStage(),
            ConsensusScoringStage(),
            RecommendationsStage(),
        ],
    )
