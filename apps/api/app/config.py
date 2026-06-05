from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="AI VEA API", alias="APP_NAME")
    app_env: str = Field(default="local", alias="APP_ENV")
    app_version: str = Field(default="0.1.0", alias="APP_VERSION")
    cors_origins: list[str] = Field(default=["http://localhost:5173"], alias="CORS_ORIGINS")
    video_upload_dir: Path = Field(default=Path("storage/uploads"), alias="VIDEO_UPLOAD_DIR")
    video_max_upload_bytes: int = Field(
        default=500 * 1024 * 1024,
        alias="VIDEO_MAX_UPLOAD_BYTES",
        gt=0,
    )
    video_allowed_content_types: list[str] = Field(
        default=[
            "video/mp4",
            "video/mpeg",
            "video/quicktime",
            "video/webm",
            "video/x-matroska",
        ],
        alias="VIDEO_ALLOWED_CONTENT_TYPES",
    )
    video_allowed_extensions: list[str] = Field(
        default=[".mp4", ".mpeg", ".mov", ".webm", ".mkv"],
        alias="VIDEO_ALLOWED_EXTENSIONS",
    )
    whisper_model_size: str = Field(default="base", alias="WHISPER_MODEL_SIZE")
    whisper_compute_type: str = Field(default="int8", alias="WHISPER_COMPUTE_TYPE")
    whisper_local_files_only: bool = Field(default=True, alias="WHISPER_LOCAL_FILES_ONLY")
    ffmpeg_path: str | None = Field(default=None, alias="FFMPEG_PATH")
    llm_base_url: str = Field(
        default="https://api.openai.com/v1",
        alias="LLM_BASE_URL",
    )
    llm_api_key: str | None = Field(default=None, alias="LLM_API_KEY")
    llm_model: str = Field(default="gpt-4.1-mini", alias="LLM_MODEL")
    llm_timeout_seconds: float = Field(default=30.0, alias="LLM_TIMEOUT_SECONDS", gt=0)
    llm_temperature: float = Field(default=0.1, alias="LLM_TEMPERATURE", ge=0, le=2)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        populate_by_name=True,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
