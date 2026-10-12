# this_file: src/vexy_subs/postprocess.py
"""Beautify existing artifact sets or standalone captions without repeating ASR."""

import hashlib
import html
import json
import shutil
import subprocess
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path

import pysubs2
import webvtt
from loguru import logger

from .beautify import beautify
from .beautify_config import load_config
from .formats import verify, write
from .io import save, sha256
from .types import Word

EXTENSIONS = (".srt", ".vtt", ".ass", ".words.json", ".vexy-subs.json")
EXCLUDED = {"private", ".venv", ".git", "beautify-original"}


def frame_rate(source: Path | None, fps: float = 0) -> float:
    """Read actual video rate when available; audio/caption-only defaults to 25 fps."""
    if fps:
        return fps
    if (
        source
        and source.is_file()
        and source.suffix.lower() not in {".srt", ".vtt", ".ass"}
    ):
        data = json.loads(
            subprocess.check_output(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-select_streams",
                    "v:0",
                    "-show_entries",
                    "stream=avg_frame_rate",
                    "-of",
                    "json",
                    str(source),
                ],
                timeout=60,
            )
        )
        for stream in data.get("streams", []):
            numerator, denominator = map(float, stream["avg_frame_rate"].split("/"))
            if numerator > 0 and denominator > 0:
                return numerator / denominator
    return 25


def read_captions(path: Path) -> tuple[list[Word], dict]:
    """Import available cues; approximate word times only when originals are absent."""
    words, names = [], {}
    if path.suffix == ".vtt":
        events = [
            (
                c.start_in_seconds,
                c.end_in_seconds,
                html.unescape(c.text),
                c.voice or "unassigned",
            )
            for c in webvtt.read(str(path))
        ]
    else:
        subs = pysubs2.load(str(path), format_=path.suffix.lstrip("."))
        events = [
            (
                e.start / 1000,
                e.end / 1000,
                html.unescape(e.plaintext),
                e.style if path.suffix == ".ass" else "unassigned",
            )
            for e in subs
        ]
        names = {e.style: e.name for e in subs if e.name}
    for start, end, text, speaker in events:
        tokens = text.split()
        if not tokens or end <= start:
            continue
        weights = [max(1, len(t)) for t in tokens]
        total, cursor = sum(weights), start
        for token, weight in zip(tokens, weights, strict=True):
            next_time = cursor + (end - start) * weight / total
            words.append(Word(token, cursor, min(end, next_time), speaker))
            cursor = next_time
    return words, names


def resolve_stem(path: Path) -> Path:
    """Keep dots inside media stems; remove only known complete artifact suffixes."""
    for extension in (".vexy-subs.json", ".words.json", ".srt", ".vtt", ".ass"):
        if path.name.endswith(extension):
            return path.with_name(path.name.removesuffix(extension))
    raise ValueError(
        "Input must be a subtitle folder, SRT/VTT/ASS, words JSON or receipt"
    )


def targets(path: Path, recursive: bool) -> list[Path]:
    """Deduplicate styled sets and leave archives/inference working directories alone."""
    if path.is_file():
        resolve_stem(path)
        return [path]
    if not path.is_dir():
        raise FileNotFoundError(path)
    groups = {}
    for item in path.rglob("*") if recursive else path.iterdir():
        if not item.is_file() or any(
            part in EXCLUDED or part.endswith(".work")
            for part in item.relative_to(path).parts
        ):
            continue
        if item.suffix.lower() not in {".srt", ".vtt", ".ass"}:
            continue
        stem = resolve_stem(item)
        if stem not in groups or item.suffix == ".ass":
            groups[stem] = item
    return [groups[key] for key in sorted(groups)]


def process(
    path: Path,
    config,
    language: str,
    fps: float,
    force: bool,
    output_dir: str = "",
    strict: bool = False,
) -> dict:
    """Stage/verify exports, back up originals, then update captions and hash receipt."""
    stem = resolve_stem(path)
    receipt_path = Path(str(stem) + ".vexy-subs.json")
    old = json.loads(receipt_path.read_text()) if receipt_path.exists() else {}
    words_path = Path(str(stem) + ".words.json")
    backup = stem.parent / (stem.name + ".work") / "beautify-original"
    raw_path = backup / words_path.name
    if not raw_path.exists():
        raw_path = words_path
    names = {
        key: value["label"] for key, value in old.get("speaker_palette", {}).items()
    }
    if raw_path.exists():
        words = [Word(**word) for word in json.loads(raw_path.read_text())["words"]]
        approximate = False
    else:
        original_caption = backup / path.name
        words, imported_names = read_captions(
            original_caption if original_caption.exists() else path
        )
        names.update(imported_names)
        approximate = True
    duration = old.get("duration", max((w.end for w in words), default=0) + 0.5)
    source = stem.parent / old.get("source_filename", stem.name + ".mp4")
    rate = frame_rate(source if source.exists() else None, fps)
    settings = {**config.receipt(), "language": language, "fps": rate}
    previous = old.get("beautification", {})
    if not output_dir and not force and previous.get("request") == settings:
        for ext, digest in old["outputs"].items():
            if sha256(Path(str(stem) + ext)) != digest:
                raise ValueError(
                    f"Changed output: {stem.name}{ext}; inspect or use --force"
                )
        verify(stem, duration)
        if strict and not previous["audit"]["numeric_rules_pass"]:
            raise ValueError(f"Unresolved subtitle constraints: {stem.name}")
        return {"stem": str(stem), "status": "skipped", "audit": previous["audit"]}
    cleaned, cues, info = beautify(words, duration, language, rate, config)
    info.update(request=settings, approximate_word_timings=approximate)
    if strict and not info["audit"]["numeric_rules_pass"]:
        raise ValueError(
            f"Unresolved subtitle constraints: {stem.name}: {info['audit']['violations'][:3]}"
        )
    destination = Path(output_dir).resolve() / stem.name if output_dir else stem
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent) as temporary:
        staged = Path(temporary) / stem.name
        palette = write(cues, staged, names)
        save(Path(str(staged) + ".words.json"), {"words": [asdict(w) for w in cleaned]})
        checks = verify(staged, duration)
        data = {
            **old,
            "duration": duration,
            "speaker_palette": palette,
            "verification": checks,
            "beautification": info,
            "source_filename": old.get("source_filename", path.name),
            "settings": {**old.get("settings", {}), "beautification": settings},
            "outputs": {
                ext: sha256(Path(str(staged) + ext)) for ext in EXTENSIONS[:-1]
            },
        }
        data["key"] = hashlib.sha256(
            json.dumps(data["settings"], sort_keys=True).encode()
        ).hexdigest()
        save(Path(str(staged) + ".vexy-subs.json"), data)
        backup.mkdir(parents=True, exist_ok=True)
        for ext in EXTENSIONS:
            original = Path(str(stem) + ext)
            if original.exists() and not (backup / original.name).exists():
                shutil.copy2(original, backup / original.name)
        # Imported cue-only files also get an immutable timed-word baseline.
        if not (backup / words_path.name).exists():
            save(backup / words_path.name, {"words": [asdict(w) for w in words]})
        for ext in EXTENSIONS:
            Path(str(staged) + ext).replace(Path(str(destination) + ext))
    return {
        "stem": str(destination),
        "status": "processed",
        "removed_words": info["removed_words"],
        "language": info["language_detection"],
        "audit": info["audit"],
    }


def run(
    path: str = ".",
    language: str = "",
    fps: float = 0,
    backend: str = "",
    config_file: str = "",
    env_file: str = "",
    llm: str = "",
    recursive: bool = False,
    output_dir: str = "",
    force: bool = False,
    strict: bool = False,
    verbose: bool = False,
) -> dict:
    """Beautify existing subtitles in place with backups; optionally write output_dir.

    Use --recursive for a video tree. --strict rejects unresolved numeric constraints
    before replacing each set. Inference and archived private data are never rerun.
    """
    config = load_config(config_file, env_file, backend, llm)
    inputs = targets(Path(path).resolve(), recursive)
    if not inputs:
        raise ValueError("No subtitle sets found")
    reports = []
    for index, item in enumerate(inputs, 1):
        print(
            f"BEAUTIFY [{index}/{len(inputs)}] {item.name}", file=sys.stderr, flush=True
        )
        reports.append(process(item, config, language, fps, force, output_dir, strict))
        if verbose:
            logger.debug(
                "{status}: {stem}; {count} unresolved constraints",
                status=reports[-1]["status"],
                stem=reports[-1]["stem"],
                count=len(reports[-1]["audit"]["violations"]),
            )
    return {
        "processed": sum(r["status"] == "processed" for r in reports),
        "skipped": sum(r["status"] == "skipped" for r in reports),
        "sets": reports,
    }
