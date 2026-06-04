from app.pipelines.engagement_analysis.context import EngagementAnalysisContext
from app.pipelines.engagement_analysis.models import ConsensusScoring


class ConsensusScoringStage:
    name = "consensus_scoring"

    async def run(self, context: EngagementAnalysisContext) -> EngagementAnalysisContext:
        context.scoring = ConsensusScoring(
            overall_score=0,
            confidence=0,
            notes=[
                "Placeholder consensus scoring completed.",
                "Future implementation can combine model, heuristic, and tool outputs into "
                "normalized scores.",
            ],
        )
        return context
