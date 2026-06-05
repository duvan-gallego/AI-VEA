import logging
from pathlib import Path
from typing import Annotated
from uuid import uuid4

import anyio
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from app.config import Settings, get_settings
from app.pipelines.engagement_analysis.models import EngagementAnalysisReport
from app.services.engagement_analysis_processor import (
    EngagementAnalysisProcessingRequest,
    EngagementAnalysisProcessor,
    LocalEngagementAnalysisProcessor,
)

router = APIRouter(prefix="/engagement-analyses", tags=["engagement analyses"])
logger = logging.getLogger(__name__)

CHUNK_SIZE_BYTES = 1024 * 1024


class EngagementAnalysisCreateResponse(BaseModel):
    id: str = Field(description="Stable analysis identifier for later processing lookup.")
    filename: str
    content_type: str
    size_bytes: int
    status: str
    report: EngagementAnalysisReport


def get_engagement_analysis_processor(
    settings: Annotated[Settings, Depends(get_settings)],
) -> EngagementAnalysisProcessor:
    return LocalEngagementAnalysisProcessor(settings=settings)


@router.post(
    "",
    response_model=EngagementAnalysisCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_engagement_analysis(
    file: Annotated[UploadFile, File(...)],
    settings: Annotated[Settings, Depends(get_settings)],
    processor: Annotated[
        EngagementAnalysisProcessor,
        Depends(get_engagement_analysis_processor),
    ],
) -> EngagementAnalysisCreateResponse:
    original_filename = _validate_upload_metadata(file, settings)
    analysis_id = uuid4().hex
    stored_path = _build_upload_path(settings.video_upload_dir, analysis_id, original_filename)
    logger.info(
        "Received engagement analysis upload analysis_id=%s filename=%s content_type=%s",
        analysis_id,
        original_filename,
        file.content_type or "application/octet-stream",
    )

    size_bytes = await _persist_upload(file, stored_path, settings.video_max_upload_bytes)
    logger.info(
        "Stored engagement analysis upload analysis_id=%s path=%s size_bytes=%s",
        analysis_id,
        stored_path,
        size_bytes,
    )
    processing_result = await processor.enqueue(
        EngagementAnalysisProcessingRequest(
            analysis_id=analysis_id,
            source_path=stored_path,
            original_filename=original_filename,
            content_type=file.content_type or "application/octet-stream",
            size_bytes=size_bytes,
        ),
    )

    return EngagementAnalysisCreateResponse(
        id=analysis_id,
        filename=original_filename,
        content_type=file.content_type or "application/octet-stream",
        size_bytes=size_bytes,
        status=processing_result.status,
        report=processing_result.report,
    )


def _validate_upload_metadata(file: UploadFile, settings: Settings) -> str:
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A video filename is required.",
        )

    filename = Path(file.filename).name
    extension = Path(filename).suffix.lower()

    if extension not in settings.video_allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported video extension: {extension or '<none>'}.",
        )

    if file.content_type not in settings.video_allowed_content_types:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported video content type: {file.content_type or '<none>'}.",
        )

    return filename


def _build_upload_path(upload_dir: Path, upload_id: str, filename: str) -> Path:
    extension = Path(filename).suffix.lower()
    return upload_dir / f"{upload_id}{extension}"


async def _persist_upload(file: UploadFile, destination: Path, max_bytes: int) -> int:
    size_bytes = 0

    await anyio.Path(destination.parent).mkdir(parents=True, exist_ok=True)

    try:
        async with await anyio.open_file(destination, "wb") as output:
            while chunk := await file.read(CHUNK_SIZE_BYTES):
                size_bytes += len(chunk)
                if size_bytes > max_bytes:
                    raise HTTPException(
                        status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                        detail="Uploaded video exceeds the maximum allowed size.",
                    )

                await output.write(chunk)
    except HTTPException:
        await anyio.Path(destination).unlink(missing_ok=True)
        raise

    if size_bytes == 0:
        await anyio.Path(destination).unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded video cannot be empty.",
        )

    logger.debug("Persisted upload destination=%s size_bytes=%s", destination, size_bytes)
    return size_bytes
