# AI VEA API

FastAPI backend service for the AI VEA monorepo.

## Development

```bash
uv sync
uv run uvicorn app.main:app --reload
```

## Checks

```bash
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run pytest
```

## Engagement Analyses

Create an engagement analysis from a video upload with multipart form data:

```bash
curl -X POST http://localhost:8000/api/engagement-analyses \
  -F "file=@/path/to/video.mp4;type=video/mp4"
```

Uploads are validated by extension, content type, non-empty body, and max size before being handed
to `app.services.engagement_analysis_processor.EngagementAnalysisProcessor`.

The default processor runs a placeholder pipeline under `app.pipelines.engagement_analysis`:

1. Media Understanding
2. Structural Understanding
3. Content Understanding
4. Engagement Understanding
5. Audience Simulation
6. Consensus & Scoring
7. Recommendations

Each stage returns typed placeholder output today, so ffmpeg, Whisper, scoring models, or workers
can be connected behind individual stages later.
