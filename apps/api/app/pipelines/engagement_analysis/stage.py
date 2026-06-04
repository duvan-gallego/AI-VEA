from typing import Protocol

from app.pipelines.engagement_analysis.context import EngagementAnalysisContext


class EngagementAnalysisStage(Protocol):
    name: str

    async def run(self, context: EngagementAnalysisContext) -> EngagementAnalysisContext: ...
