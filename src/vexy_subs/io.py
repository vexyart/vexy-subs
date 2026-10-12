# this_file: src/vexy_subs/io.py
"""Local media boundaries and content-addressed stage receipts."""

import hashlib
import json
import subprocess
from pathlib import Path


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def probe(path: Path) -> float:
    if not path.is_file():
        raise FileNotFoundError(path)
    result = json.loads(
        subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration:stream=codec_type",
                "-of",
                "json",
                str(path),
            ],
            timeout=60,
        )
    )
    if not any(s["codec_type"] == "audio" for s in result["streams"]):
        raise ValueError("Input has no audio stream")
    return float(result["format"]["duration"])


def decode(path: Path, wav: Path) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-nostdin",
            "-v",
            "error",
            "-y",
            "-i",
            str(path),
            "-map",
            "0:a:0",
            "-ac",
            "1",
            "-ar",
            "16000",
            str(wav),
        ],
        check=True,
        timeout=3600,
    )


def save(path: Path, data: dict) -> None:
    """Write JSON atomically so interrupted jobs cannot create false completion."""
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    temporary.replace(path)


def stage(path: Path, key: str, compute) -> dict:
    """Reuse completed inference only for exactly matching input and settings."""
    if path.exists():
        cached = json.loads(path.read_text())
        if cached.get("key") == key:
            return cached["data"]
    data = compute()
    save(path, {"key": key, "data": data})
    return data
