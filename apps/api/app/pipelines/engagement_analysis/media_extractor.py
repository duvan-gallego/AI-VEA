from __future__ import annotations

import importlib
import json
import logging
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from app.pipelines.engagement_analysis.models import (
    AudioFeature,
    FrameSnapshot,
    MediaUnderstanding,
    SceneSegment,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class MediaExtractionOptions:
    whisper_model_size: str = "base"
    whisper_compute_type: str = "int8"
    whisper_local_files_only: bool = True
    ffmpeg_path: str | None = None
    max_key_frames: int = 10
    audio_sample_rate: int = 16_000
    command_timeout_seconds: int = 120


class MediaUnderstandingExtractor:
    def __init__(self, options: MediaExtractionOptions | None = None) -> None:
        self._options = options or MediaExtractionOptions()

    async def extract(self, video_path: Path, analysis_id: str) -> MediaUnderstanding:
        logger.info(
            "Starting media extraction analysis_id=%s video_path=%s", analysis_id, video_path
        )
        notes: list[str] = []
        transcript = self._extract_transcript(video_path, notes)
        scenes = self._detect_scenes(video_path, notes)
        frames = self._extract_key_frames(video_path, analysis_id, scenes, notes)
        audio_features = self._extract_audio_features(video_path, transcript, notes)
        duration_seconds = self._infer_duration_seconds(scenes, audio_features)
        logger.info(
            "Completed media extraction analysis_id=%s transcript_chars=%s scenes=%s frames=%s "
            "audio_features=%s duration_seconds=%s notes=%s",
            analysis_id,
            len(transcript),
            len(scenes),
            len(frames),
            len(audio_features),
            duration_seconds,
            len(notes),
        )

        return MediaUnderstanding(
            transcript=transcript,
            scenes=scenes,
            frames=frames,
            audio_features=audio_features,
            duration_seconds=duration_seconds,
            detected_modalities=["video", "audio"],
            notes=notes,
        )

    def _extract_transcript(self, video_path: Path, notes: list[str]) -> str:
        try:
            logger.info(
                "Starting transcript extraction video_path=%s model_size=%s local_files_only=%s",
                video_path,
                self._options.whisper_model_size,
                self._options.whisper_local_files_only,
            )
            result = subprocess.run(  # noqa: S603
                [
                    sys.executable,
                    "-m",
                    "app.pipelines.engagement_analysis.whisper_worker",
                    str(video_path),
                    "--model-size",
                    self._options.whisper_model_size,
                    "--compute-type",
                    self._options.whisper_compute_type,
                    "--local-files-only",
                    str(self._options.whisper_local_files_only).lower(),
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=self._options.command_timeout_seconds,
            )
            payload = json.loads(result.stdout)
            notes.append("Transcript extracted with faster-whisper.")
            transcript = str(payload.get("transcript", ""))
            logger.info("Completed transcript extraction transcript_chars=%s", len(transcript))
            return transcript
        except subprocess.CalledProcessError as exc:
            details = self._format_process_error(exc)
            notes.append(f"Transcript extraction skipped: {details}")
            logger.warning(
                "Transcript extraction skipped video_path=%s reason=%s", video_path, details
            )
            return ""
        except Exception as exc:
            notes.append(f"Transcript extraction skipped: {exc}")
            logger.warning(
                "Transcript extraction skipped video_path=%s",
                video_path,
                exc_info=True,
            )
            return ""

    def _detect_scenes(self, video_path: Path, notes: list[str]) -> list[SceneSegment]:
        try:
            logger.info("Starting scene detection video_path=%s", video_path)
            scenedetect = importlib.import_module("scenedetect")
            detectors = importlib.import_module("scenedetect.detectors")
            scene_list = cast(Any, scenedetect).detect(
                str(video_path),
                cast(Any, detectors).AdaptiveDetector(),
            )
            scenes = [
                SceneSegment(
                    start_seconds=float(start_time.get_seconds()),
                    end_seconds=float(end_time.get_seconds()),
                )
                for start_time, end_time in scene_list
            ]
            notes.append("Scenes detected with PySceneDetect.")
            logger.info("Completed scene detection scenes=%s", len(scenes))
            return scenes
        except Exception as exc:
            notes.append(f"Scene detection skipped: {exc}")
            logger.warning("Scene detection skipped video_path=%s", video_path, exc_info=True)
            return []

    def _extract_key_frames(
        self,
        video_path: Path,
        analysis_id: str,
        scenes: list[SceneSegment],
        notes: list[str],
    ) -> list[FrameSnapshot]:
        try:
            logger.info(
                "Starting key frame extraction video_path=%s candidate_scenes=%s",
                video_path,
                len(scenes),
            )
            cv2 = importlib.import_module("cv2")
            capture = cast(Any, cv2).VideoCapture(str(video_path))
            if not capture.isOpened():
                notes.append("Key frame extraction skipped: OpenCV could not read the video.")
                logger.warning(
                    "Key frame extraction skipped because OpenCV could not read video_path=%s",
                    video_path,
                )
                return []

            fps = float(capture.get(cast(Any, cv2).CAP_PROP_FPS) or 0)
            frame_count = int(capture.get(cast(Any, cv2).CAP_PROP_FRAME_COUNT) or 0)
            if fps <= 0 or frame_count <= 0:
                notes.append(
                    "Key frame extraction skipped: video FPS or frame count is unavailable.",
                )
                logger.warning(
                    "Key frame extraction skipped: FPS/frame_count unavailable path=%s",
                    video_path,
                )
                return []

            timestamps = self._select_frame_timestamps(scenes, frame_count / fps)
            frame_dir = video_path.parent / analysis_id / "frames"
            frame_dir.mkdir(parents=True, exist_ok=True)

            frames: list[FrameSnapshot] = []
            for index, timestamp_seconds in enumerate(timestamps, start=1):
                capture.set(cast(Any, cv2).CAP_PROP_POS_MSEC, timestamp_seconds * 1000)
                ok, frame = capture.read()
                if not ok:
                    continue

                output_path = frame_dir / f"frame_{index:03d}.jpg"
                if not cast(Any, cv2).imwrite(str(output_path), frame):
                    continue

                height, width = frame.shape[:2]
                frames.append(
                    FrameSnapshot(
                        timestamp_seconds=timestamp_seconds,
                        path=str(output_path),
                        width=int(width),
                        height=int(height),
                    ),
                )

            capture.release()
            notes.append("Key frames extracted with OpenCV.")
            logger.info("Completed key frame extraction frames=%s", len(frames))
            return frames
        except Exception as exc:
            notes.append(f"Key frame extraction skipped: {exc}")
            logger.warning("Key frame extraction skipped video_path=%s", video_path, exc_info=True)
            return []

    def _select_frame_timestamps(
        self,
        scenes: list[SceneSegment],
        duration_seconds: float,
    ) -> list[float]:
        if scenes:
            return [
                (scene.start_seconds + scene.end_seconds) / 2
                for scene in scenes[: self._options.max_key_frames]
            ]

        count = min(self._options.max_key_frames, max(1, int(duration_seconds)))
        interval = duration_seconds / (count + 1)
        return [round(interval * index, 3) for index in range(1, count + 1)]

    def _extract_audio_features(
        self,
        video_path: Path,
        transcript: str,
        notes: list[str],
    ) -> list[AudioFeature]:
        with tempfile.TemporaryDirectory() as temporary_dir:
            audio_path = Path(temporary_dir) / "audio.wav"
            try:
                logger.info("Starting audio feature extraction video_path=%s", video_path)
                self._extract_audio_with_ffmpeg(video_path, audio_path)
                librosa = importlib.import_module("librosa")
                numpy = importlib.import_module("numpy")

                audio, sample_rate = cast(Any, librosa).load(
                    str(audio_path),
                    sr=self._options.audio_sample_rate,
                    mono=True,
                )
                duration_seconds = float(
                    cast(Any, librosa).get_duration(y=audio, sr=sample_rate),
                )
                rms = cast(Any, librosa).feature.rms(y=audio)[0]
                mean_energy = float(cast(Any, numpy).mean(rms))
                mean_volume_db = float(
                    cast(Any, numpy).mean(cast(Any, librosa).amplitude_to_db(rms)),
                )
                tempo_result = cast(Any, librosa).beat.beat_track(y=audio, sr=sample_rate)
                tempo_value = (
                    tempo_result[0][0] if hasattr(tempo_result[0], "__len__") else tempo_result[0]
                )
                tempo = float(tempo_value)
                non_silent = cast(Any, librosa).effects.split(audio, top_db=30)
                silence = self._build_silence_intervals(non_silent, sample_rate, duration_seconds)
                speech_rate = self._calculate_speech_rate(transcript, duration_seconds)

                notes.append("Audio features extracted with ffmpeg and librosa.")
                logger.info(
                    "Completed audio feature extraction duration=%s speech_rate=%s tempo=%s",
                    duration_seconds,
                    speech_rate,
                    tempo,
                )
                return [
                    AudioFeature(name="duration", value=duration_seconds, unit="seconds"),
                    AudioFeature(name="silence", value=silence, unit="seconds"),
                    AudioFeature(name="speech_rate", value=speech_rate, unit="words_per_minute"),
                    AudioFeature(name="volume", value=mean_volume_db, unit="db"),
                    AudioFeature(name="energy", value=mean_energy, unit="rms"),
                    AudioFeature(name="tempo", value=tempo, unit="bpm"),
                ]
            except Exception as exc:
                notes.append(f"Audio feature extraction skipped: {exc}")
                logger.warning(
                    "Audio feature extraction skipped video_path=%s", video_path, exc_info=True
                )
                return []

    def _extract_audio_with_ffmpeg(self, video_path: Path, audio_path: Path) -> None:
        ffmpeg_path = self._resolve_ffmpeg_path()
        if ffmpeg_path is None:
            msg = (
                "ffmpeg executable was not found. Install ffmpeg, configure "
                "MediaExtractionOptions.ffmpeg_path, or install imageio-ffmpeg."
            )
            raise RuntimeError(msg)

        logger.debug("Running ffmpeg audio extraction ffmpeg_path=%s", ffmpeg_path)
        subprocess.run(  # noqa: S603
            [
                ffmpeg_path,
                "-y",
                "-i",
                str(video_path),
                "-vn",
                "-ac",
                "1",
                "-ar",
                str(self._options.audio_sample_rate),
                str(audio_path),
            ],
            check=True,
            capture_output=True,
            timeout=self._options.command_timeout_seconds,
        )

    def _resolve_ffmpeg_path(self) -> str | None:
        if self._options.ffmpeg_path:
            return self._options.ffmpeg_path

        system_ffmpeg_path = shutil.which("ffmpeg")
        if system_ffmpeg_path:
            return system_ffmpeg_path

        try:
            imageio_ffmpeg = importlib.import_module("imageio_ffmpeg")
            return str(cast(Any, imageio_ffmpeg).get_ffmpeg_exe())
        except Exception:
            return None

    def _format_process_error(self, error: subprocess.CalledProcessError) -> str:
        stderr = self._decode_process_output(error.stderr).strip()
        stdout = self._decode_process_output(error.stdout).strip()
        output = stderr or stdout

        if "LocalEntryNotFoundError" in output:
            return (
                "faster-whisper model is not cached locally and local_files_only=true. "
                "Download/provision the model first, or set whisper_local_files_only=false "
                "in a controlled environment."
            )

        if output:
            return output.splitlines()[-1]

        return f"worker exited with status {error.returncode}."

    def _decode_process_output(self, output: str | bytes | None) -> str:
        if output is None:
            return ""
        if isinstance(output, bytes):
            return output.decode("utf-8", errors="replace")
        return output

    def _build_silence_intervals(
        self,
        non_silent_intervals: Any,
        sample_rate: int,
        duration_seconds: float,
    ) -> list[dict[str, float]]:
        silence_intervals: list[dict[str, float]] = []
        cursor_seconds = 0.0

        for start_sample, end_sample in non_silent_intervals:
            start_seconds = float(start_sample) / sample_rate
            end_seconds = float(end_sample) / sample_rate
            if start_seconds > cursor_seconds:
                silence_intervals.append(
                    {"start_seconds": cursor_seconds, "end_seconds": start_seconds},
                )
            cursor_seconds = end_seconds

        if cursor_seconds < duration_seconds:
            silence_intervals.append(
                {"start_seconds": cursor_seconds, "end_seconds": duration_seconds},
            )

        return silence_intervals

    def _calculate_speech_rate(self, transcript: str, duration_seconds: float) -> float | None:
        if not transcript or duration_seconds <= 0:
            return None

        word_count = len(transcript.split())
        return word_count / (duration_seconds / 60)

    def _infer_duration_seconds(
        self,
        scenes: list[SceneSegment],
        audio_features: list[AudioFeature],
    ) -> float | None:
        for feature in audio_features:
            if feature.name == "duration" and isinstance(feature.value, float):
                return feature.value

        if scenes:
            return max(scene.end_seconds for scene in scenes)

        return None
