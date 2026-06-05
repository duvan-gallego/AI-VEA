import logging
from collections.abc import Sequence
from time import perf_counter

from app.pipelines.engagement_analysis.content_analyzer import ContentUnderstandingAnalyzer
from app.pipelines.engagement_analysis.context import EngagementAnalysisContext
from app.pipelines.engagement_analysis.llm_client import (
    ChatCompletionClient,
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

logger = logging.getLogger(__name__)


class EngagementAnalysisPipeline:
    def __init__(self, stages: Sequence[EngagementAnalysisStage]) -> None:
        self._stages = stages

    async def run(self, context: EngagementAnalysisContext) -> EngagementAnalysisContext:
        current_context = context

        for stage in self._stages:
            started_at = perf_counter()
            logger.info(
                "Starting pipeline stage analysis_id=%s stage=%s",
                current_context.analysis_id,
                stage.name,
            )
            try:
                current_context = await stage.run(current_context)
            except Exception:
                logger.exception(
                    "Failed pipeline stage analysis_id=%s stage=%s",
                    current_context.analysis_id,
                    stage.name,
                )
                raise

            elapsed_ms = int((perf_counter() - started_at) * 1000)
            logger.info(
                "Completed pipeline stage analysis_id=%s stage=%s elapsed_ms=%s",
                current_context.analysis_id,
                stage.name,
                elapsed_ms,
            )

        return current_context


def build_default_engagement_analysis_pipeline(
    media_options: MediaExtractionOptions | None = None,
    llm_options: OpenAICompatibleChatOptions | None = None,
) -> EngagementAnalysisPipeline:
    chat_client: ChatCompletionClient | None = (
        OpenAICompatibleChatClient(llm_options) if llm_options is not None else None
    )
    structural_analyzer = StructuralUnderstandingAnalyzer(
        chat_client=chat_client,
    )
    content_analyzer = ContentUnderstandingAnalyzer(
        chat_client=chat_client,
    )

    return EngagementAnalysisPipeline(
        stages=[
            MediaUnderstandingStage(
                extractor=MediaUnderstandingExtractor(options=media_options),
            ),
            StructuralUnderstandingStage(analyzer=structural_analyzer),
            ContentUnderstandingStage(analyzer=content_analyzer),
            EngagementUnderstandingStage(),
            AudienceSimulationStage(),
            ConsensusScoringStage(),
            RecommendationsStage(),
        ],
    )
