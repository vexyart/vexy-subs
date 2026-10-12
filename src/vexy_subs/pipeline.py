# this_file: src/vexy_subs/pipeline.py
"""ASR → continuous diarization → punctuation → styled subtitle exports."""

import hashlib
import json
import sys
import tempfile
import time
from dataclasses import asdict
from pathlib import Path

from . import __version__
from .alignment import MODEL as ALIGNER
from .alignment import repair
from .beautify import beautify as beautify_words
from .beautify_config import load_config
from .cues import segment
from .formats import verify, write
from .hints import read_prompt
from .inference import ASR, DIAR, diarize, transcribe
from .io import decode, probe, save, sha256, stage
from .postprocess import frame_rate
from .punctuation import MODEL, restore
from .speakers import assign
from .types import Turn, Word

EXTENSIONS = (".srt", ".vtt", ".ass", ".words.json")


def run(
    video: str,
    output_dir: str = "",
    prompt_file: str = "",
    prompt: str = "",
    language: str = "en",
    asr_model: str = ASR,
    diar_model: str = DIAR,
    punctuation_model: str = MODEL,
    alignment_model: str = ALIGNER,
    diar_backend: str = "auto",
    turns_file: str = "",
    max_speakers: int = 40,
    speaker_map: str = "",
    force: bool = False,
    beautify: bool = True,
    beautify_backend: str = "",
    beautify_language: str = "",
    config_file: str = "",
    env_file: str = "",
    fps: float = 0,
    strict: bool = False,
) -> dict:
    """Generate real speaker colours; retain recoverable local stage artifacts."""
    source = Path(video).resolve()
    duration = probe(source)
    hints, hint_receipt = read_prompt(prompt_file, prompt)
    names = json.loads(Path(speaker_map).read_text()) if speaker_map else {}
    if diar_backend not in {"auto", "nemotron", "cluster"} or max_speakers < 1:
        raise ValueError("Require a supported diar_backend and positive max_speakers")
    if not isinstance(names, dict) or not all(
        isinstance(v, str) and v.strip() for v in names.values()
    ):
        raise ValueError(
            "speaker_map must be a JSON object mapping IDs to nonempty labels"
        )
    folder = Path(output_dir).resolve() if output_dir else source.parent
    folder.mkdir(parents=True, exist_ok=True)
    stem = folder / source.stem
    receipt = Path(str(stem) + ".vexy-subs.json")
    options = {
        "version": __version__,
        "input_sha256": sha256(source),
        "prompt": hint_receipt,
        "language": language,
        "asr_model": asr_model,
        "diar_model": diar_model,
        "punctuation_model": punctuation_model,
        "alignment_model": alignment_model,
        "speaker_names": names,
        "recognition_context": "lexicon-v1",
        "punctuation_policy": 3,
    }
    if diar_backend not in {"auto", "nemotron"}:
        options.update(diar_backend=diar_backend, max_speakers=max_speakers)
    elif diar_backend == "auto" and max_speakers != 40:
        options["max_speakers"] = max_speakers
    if turns_file:
        options["turns_sha256"] = sha256(Path(turns_file))
    # Layout/editorial changes must not invalidate the costly inference caches.
    punctuation_key = hashlib.sha256(
        json.dumps(options, sort_keys=True).encode()
    ).hexdigest()
    config = load_config(config_file, env_file, beautify_backend) if beautify else None
    rate = frame_rate(source, fps) if beautify else 0
    if config:
        options["beautification"] = {
            **config.receipt(),
            "language": beautify_language,
            "fps": rate,
        }
    key = hashlib.sha256(json.dumps(options, sort_keys=True).encode()).hexdigest()
    inference_key = hashlib.sha256(
        json.dumps(
            {
                k: v
                for k, v in options.items()
                if k not in {"punctuation_policy", "beautification"}
            },
            sort_keys=True,
        ).encode()
    ).hexdigest()
    if receipt.exists() and not force:
        old = json.loads(receipt.read_text())
        comparable = {k: v for k, v in old["settings"].items() if k != "turns_sha256"}
        compatible_cluster = (
            diar_backend == "auto"
            and old.get("diarization_backend") == "cluster"
            and comparable == options
        )
        if (old["key"] == key or compatible_cluster) and all(
            sha256(Path(str(stem) + ext)) == digest
            for ext, digest in old["outputs"].items()
        ):
            verify(stem, duration)
            print(f"SKIP {source.name}: verified", file=sys.stderr)
            return old
        raise FileExistsError("Existing output differs; use --force to regenerate")
    if not force and any(Path(str(stem) + ext).exists() for ext in EXTENSIONS):
        raise FileExistsError("Unmanaged subtitles exist; choose output_dir or --force")
    work = folder / (source.stem + ".work")
    work.mkdir(exist_ok=True)
    start = time.monotonic()
    with tempfile.TemporaryDirectory(dir=work) as temp:
        wav = Path(temp) / "input.wav"
        decode(source, wav)

        def asr_stage() -> dict:
            print(f"ASR {source.name}", file=sys.stderr, flush=True)
            words, raw = transcribe(wav, hints, language, asr_model)
            return {"words": [asdict(w) for w in words], "raw": raw}

        base = stage(work / "asr.json", inference_key, asr_stage)
        words = [Word(**w) for w in base["words"]]

        def alignment_stage() -> dict:
            info = repair(
                wav,
                words,
                language or base["raw"].get("language", "en"),
                alignment_model,
            )
            return {"words": [asdict(w) for w in words], "info": info}

        aligned = stage(work / "alignment.json", inference_key, alignment_stage)
        words = [Word(**w) for w in aligned["words"]]

        def diar_stage() -> dict:
            print(f"DIARIZATION {source.name}", file=sys.stderr, flush=True)
            if turns_file:
                return json.loads(Path(turns_file).read_text())
            _, raw = diarize(wav, diar_model, diar_backend, max_speakers)
            return raw

        speakers = stage(work / "diarization.json", inference_key, diar_stage)
        turns = [Turn(**t) for t in speakers["turns"]]
        assign(words, turns)

        def punctuation_stage() -> dict:
            print(f"PUNCTUATION {source.name}", file=sys.stderr, flush=True)
            info = restore(words, hints, punctuation_model)
            return {"words": [asdict(w) for w in words], "info": info}

        punctuated = stage(
            work / "punctuation.json", punctuation_key, punctuation_stage
        )
        words = [Word(**w) for w in punctuated["words"]]
    if config:
        words, cues, beauty_info = beautify_words(
            words, duration, beautify_language, rate, config
        )
        beauty_info["request"] = options["beautification"]
        if strict and not beauty_info["audit"]["numeric_rules_pass"]:
            raise ValueError(
                "Unresolved subtitle constraints; inspect beautification or disable --strict"
            )
    else:
        cues = segment(words)
        beauty_info = {"disabled": True}
    if words and not turns:
        raise ValueError("No speaker activity detected for recognized speech")
    palette = write(cues, stem, names)
    save(Path(str(stem) + ".words.json"), {"words": [asdict(w) for w in words]})
    checks = verify(stem, duration)
    data = {
        "key": key,
        "settings": options,
        "source_filename": source.name,
        "duration": duration,
        "speaker_palette": palette,
        "verification": checks,
        "wall_seconds": time.monotonic() - start,
        "ambiguous_words": sum(w.ambiguous for w in words),
        "unassigned_words": sum(w.speaker == "unassigned" for w in words),
        "diarization_capacity": speakers["capacity"],
        "diarization_backend": speakers.get("backend", "nemotron"),
        "punctuation": punctuated["info"],
        "alignment": aligned["info"],
        "outputs": {ext: sha256(Path(str(stem) + ext)) for ext in EXTENSIONS},
        "beautification": beauty_info,
    }
    save(receipt, data)
    print(
        f"DONE {source.name}: {len(cues)} cues, {len(palette)} speakers",
        file=sys.stderr,
        flush=True,
    )
    return data
