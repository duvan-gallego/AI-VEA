from app.pipelines.engagement_analysis.context import EngagementAnalysisContext
from app.pipelines.engagement_analysis.media_extractor import MediaUnderstandingExtractor


class MediaUnderstandingStage:
    name = "media_understanding"

    def __init__(self, extractor: MediaUnderstandingExtractor | None = None) -> None:
        self._extractor = extractor or MediaUnderstandingExtractor()

    async def run(self, context: EngagementAnalysisContext) -> EngagementAnalysisContext:
        context.media = await self._extractor.extract(
            video_path=context.video_path,
            analysis_id=context.analysis_id,
        )
        return context
