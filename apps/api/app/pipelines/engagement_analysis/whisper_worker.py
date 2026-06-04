import argparse
import importlib
import json
from pathlib import Path
from typing import Any, cast


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Transcribe a video with faster-whisper.")
    parser.add_argument("video_path", type=Path)
    parser.add_argument("--model-size", default="base")
    parser.add_argument("--compute-type", default="int8")
    parser.add_argument("--local-files-only", default="true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    local_files_only = args.local_files_only.lower() == "true"
    faster_whisper = importlib.import_module("faster_whisper")
    whisper_model = cast(Any, faster_whisper).WhisperModel
    model = whisper_model(
        args.model_size,
        compute_type=args.compute_type,
        local_files_only=local_files_only,
    )
    segments, _ = model.transcribe(str(args.video_path))
    transcript_parts: list[str] = [segment.text.strip() for segment in segments]
    print(json.dumps({"transcript": " ".join(part for part in transcript_parts if part)}))


if __name__ == "__main__":
    main()
