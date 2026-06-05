from app.pipelines.engagement_analysis.content_analyzer import ContentUnderstandingAnalyzer
from app.pipelines.engagement_analysis.context import EngagementAnalysisContext


class ContentUnderstandingStage:
    name = "content_understanding"

    def __init__(self, analyzer: ContentUnderstandingAnalyzer | None = None) -> None:
        self._analyzer = analyzer or ContentUnderstandingAnalyzer()

    async def run(self, context: EngagementAnalysisContext) -> EngagementAnalysisContext:
        context.content = await self._analyzer.analyze(
            media=context.media,
            structure=context.structure,
        )
        return context
