from pathlib import Path

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def build_client(tmp_path: Path, *, max_upload_bytes: int = 1024) -> TestClient:
    app = create_app(
        Settings(
            app_name="Test API",
            app_env="test",
            app_version="0.0.0-test",
            cors_origins=["http://localhost:5173"],
            video_upload_dir=tmp_path,
            video_max_upload_bytes=max_upload_bytes,
        ),
    )

    return TestClient(app)


def test_create_engagement_analysis_accepts_supported_video(tmp_path: Path) -> None:
    client = build_client(tmp_path)

    response = client.post(
        "/api/engagement-analyses",
        files={"file": ("sample.mp4", b"fake-video-bytes", "video/mp4")},
    )

    body = response.json()

    assert response.status_code == 202
    assert body["filename"] == "sample.mp4"
    assert body["content_type"] == "video/mp4"
    assert body["size_bytes"] == len(b"fake-video-bytes")
    assert body["status"] == "completed"
    assert body["report"]["summary"] == "Placeholder engagement analysis report generated."
    assert body["report"]["media"]["detected_modalities"] == ["video", "audio"]
    assert body["report"]["scoring"]["overall_score"] == 0
    assert body["report"]["recommendations"]["priority_actions"]
    assert len(list(tmp_path.iterdir())) == 1


def test_create_engagement_analysis_rejects_unsupported_content_type(tmp_path: Path) -> None:
    client = build_client(tmp_path)

    response = client.post(
        "/api/engagement-analyses",
        files={"file": ("sample.txt", b"not-a-video", "text/plain")},
    )

    assert response.status_code == 415
    assert not list(tmp_path.iterdir())


def test_create_engagement_analysis_rejects_empty_file(tmp_path: Path) -> None:
    client = build_client(tmp_path)

    response = client.post(
        "/api/engagement-analyses",
        files={"file": ("empty.mp4", b"", "video/mp4")},
    )

    assert response.status_code == 400
    assert not list(tmp_path.iterdir())


def test_create_engagement_analysis_rejects_oversized_file(tmp_path: Path) -> None:
    client = build_client(tmp_path, max_upload_bytes=4)

    response = client.post(
        "/api/engagement-analyses",
        files={"file": ("large.mp4", b"too-large", "video/mp4")},
    )

    assert response.status_code == 413
    assert not list(tmp_path.iterdir())
