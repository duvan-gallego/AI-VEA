from pathlib import Path

import pytest

from app.pipelines.engagement_analysis.context import EngagementAnalysisContext
from app.pipelines.engagement_analysis.pipeline import build_default_engagement_analysis_pipeline


@pytest.mark.anyio
async def test_default_engagement_analysis_pipeline_builds_placeholder_report(
    tmp_path: Path,
) -> None:
    pipeline = build_default_engagement_analysis_pipeline()
    context = EngagementAnalysisContext(
        analysis_id="analysis-1",
        video_path=tmp_path / "sample.mp4",
        original_filename="sample.mp4",
        content_type="video/mp4",
        size_bytes=128,
    )

    result = await pipeline.run(context)

    assert result.media is not None
    assert result.structure is not None
    assert result.content is not None
    assert result.engagement is not None
    assert result.audience is not None
    assert result.scoring is not None
    assert result.recommendations is not None
    assert result.report is not None
    assert result.report.summary == "Placeholder engagement analysis report generated."
