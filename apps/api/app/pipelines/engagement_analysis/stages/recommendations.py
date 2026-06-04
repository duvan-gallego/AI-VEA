from app.pipelines.engagement_analysis.context import EngagementAnalysisContext
from app.pipelines.engagement_analysis.models import EngagementAnalysisReport, Recommendations


class RecommendationsStage:
    name = "recommendations"

    async def run(self, context: EngagementAnalysisContext) -> EngagementAnalysisContext:
        context.recommendations = Recommendations(
            priority_actions=[
                "Connect media, transcription, audience, and scoring tools to replace "
                "placeholder outputs.",
            ],
            experiments=[],
        )

        if (
            context.media is None
            or context.structure is None
            or context.content is None
            or context.engagement is None
            or context.audience is None
            or context.scoring is None
        ):
            msg = "Recommendations stage requires all previous pipeline stages to complete."
            raise ValueError(msg)

        context.report = EngagementAnalysisReport(
            summary="Placeholder engagement analysis report generated.",
            media=context.media,
            structure=context.structure,
            content=context.content,
            engagement=context.engagement,
            audience=context.audience,
            scoring=context.scoring,
            recommendations=context.recommendations,
        )
        return context
