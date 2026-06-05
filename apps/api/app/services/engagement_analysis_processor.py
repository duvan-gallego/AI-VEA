import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol

from app.config import Settings, get_settings
from app.pipelines.engagement_analysis.context import EngagementAnalysisContext
from app.pipelines.engagement_analysis.llm_client import OpenAICompatibleChatOptions
from app.pipelines.engagement_analysis.media_extractor import MediaExtractionOptions
from app.pipelines.engagement_analysis.models import EngagementAnalysisReport
from app.pipelines.engagement_analysis.pipeline import (
    EngagementAnalysisPipeline,
    build_default_engagement_analysis_pipeline,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class EngagementAnalysisProcessingRequest:
    analysis_id: str
    source_path: Path
    original_filename: str
    content_type: str
    size_bytes: int


@dataclass(frozen=True, slots=True)
class EngagementAnalysisProcessingResult:
    analysis_id: str
    status: Literal["completed"]
    report: EngagementAnalysisReport


class EngagementAnalysisProcessor(Protocol):
    async def enqueue(
        self,
        request: EngagementAnalysisProcessingRequest,
    ) -> EngagementAnalysisProcessingResult: ...


class LocalEngagementAnalysisProcessor:
    def __init__(
        self,
        pipeline: EngagementAnalysisPipeline | None = None,
        settings: Settings | None = None,
    ) -> None:
        resolved_settings = settings or get_settings()
        media_options = MediaExtractionOptions(
            whisper_model_size=resolved_settings.whisper_model_size,
            whisper_compute_type=resolved_settings.whisper_compute_type,
            whisper_local_files_only=resolved_settings.whisper_local_files_only,
            ffmpeg_path=resolved_settings.ffmpeg_path,
        )
        llm_options = (
            OpenAICompatibleChatOptions(
                base_url=resolved_settings.llm_base_url,
                api_key=resolved_settings.llm_api_key,
                model=resolved_settings.llm_model,
                timeout_seconds=resolved_settings.llm_timeout_seconds,
                temperature=resolved_settings.llm_temperature,
                response_format=resolved_settings.llm_response_format,
            )
            if resolved_settings.llm_api_key
            else None
        )
        self._pipeline = pipeline or build_default_engagement_analysis_pipeline(
            media_options=media_options,
            llm_options=llm_options,
        )

    async def enqueue(
        self,
        request: EngagementAnalysisProcessingRequest,
    ) -> EngagementAnalysisProcessingResult:
        logger.info(
            "Starting engagement analysis processing analysis_id=%s filename=%s size_bytes=%s",
            request.analysis_id,
            request.original_filename,
            request.size_bytes,
        )
        context = EngagementAnalysisContext(
            analysis_id=request.analysis_id,
            video_path=request.source_path,
            original_filename=request.original_filename,
            content_type=request.content_type,
            size_bytes=request.size_bytes,
        )
        result_context = await self._pipeline.run(context)

        if result_context.report is None:
            msg = "Engagement analysis pipeline completed without a report."
            raise RuntimeError(msg)

        logger.info(
            "Completed engagement analysis processing analysis_id=%s status=completed",
            request.analysis_id,
        )
        return EngagementAnalysisProcessingResult(
            analysis_id=request.analysis_id,
            status="completed",
            report=result_context.report,
        )


def get_engagement_analysis_processor() -> EngagementAnalysisProcessor:
    return LocalEngagementAnalysisProcessor()
