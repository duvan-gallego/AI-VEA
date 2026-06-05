from app.pipelines.engagement_analysis.context import EngagementAnalysisContext
from app.pipelines.engagement_analysis.structural_analyzer import StructuralUnderstandingAnalyzer


class StructuralUnderstandingStage:
    name = "structural_understanding"

    def __init__(self, analyzer: StructuralUnderstandingAnalyzer | None = None) -> None:
        self._analyzer = analyzer or StructuralUnderstandingAnalyzer()

    async def run(self, context: EngagementAnalysisContext) -> EngagementAnalysisContext:
        context.structure = await self._analyzer.analyze(context.media)
        return context
