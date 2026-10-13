# this_file: src/vexy_subs/workspace.py
"""Run isolated local speech adapters without bundling models or private workspace data."""

import itertools
import json
import os
import subprocess
import tempfile
from pathlib import Path

from .io import sha256
from .qwen import check_model
from .types import Word


def root_path(value: str = "") -> Path:
    """Require the actual adapter workspace only when its backend is selected."""
    value = value or os.getenv("VEXY_SUBS_MODEL_WORKSPACE", "")
    if not value:
        raise FileNotFoundError("Set --model_workspace or VEXY_SUBS_MODEL_WORKSPACE")
    root = Path(value).expanduser().resolve()
    if not (root / "myasr/tools/speech-issue301.py").is_file():
        raise FileNotFoundError("Model workspace lacks myasr/tools/speech-issue301.py")
    return root


def signature(value: str) -> dict:
    """Invalidate cached inference when its local adapters/catalogue/runtime change."""
    root = root_path(value)
    paths = list((root / "myasr/tools").glob("*.py"))
    paths += list((root / "myasr/catalogs").glob("*.json"))
    paths += list((root / "myasr").glob("asr_all.py"))
    binary = (
        root / ".external/audio.cpp-issue301/build/macos-metal-release/bin/audiocpp_cli"
    )
    if binary.is_file():
        paths.append(binary)
    return {str(p.relative_to(root)): sha256(p) for p in sorted(paths)}


def transcribe(
    wav: Path, hints: str, language: str, model: str, root: str
) -> tuple[list[Word], dict]:
    """Consume actual worker words; forced-aligned output retains recognition wording."""
    check_model(model)
    script = root_path(root) / "myasr/tools/speech-issue301.py"
    with tempfile.TemporaryDirectory() as temporary:
        output = Path(temporary) / "recognized.json"
        subprocess.run(
            [
                "uv",
                "run",
                str(script),
                "recognize",
                f"--audio={wav}",
                f"--output={output}",
                f"--model={model}",
                f"--language={language}",
                f"--prompt={hints}",
            ],
            check=True,
            timeout=3600,
            capture_output=True,
            text=True,
        )
        data = json.loads(output.read_text())
    words = [Word(w["text"], float(w["start"]), float(w["end"])) for w in data["words"]]
    if any(a.start > b.start for a, b in itertools.pairwise(words)):
        raise ValueError("Workspace words are out of order")
    return words, data["raw"]


def diarize(wav: Path, family: str, root: str) -> dict:
    """Keep continuous native speaker activity and explicit model channel capacity."""
    capacities = {"nemotron_3_diar": 8, "sortformer_diar": 4, "sortformer_diar_v2": 4}
    if family not in capacities:
        raise ValueError("Require a supported workspace diarization family")
    script = root_path(root) / "myasr/tools/speech-issue301.py"
    with tempfile.TemporaryDirectory() as temporary:
        output = Path(temporary) / "diarization"
        mode = "streaming" if family == "sortformer_diar_v2" else "offline"
        subprocess.run(
            [
                "uv",
                "run",
                str(script),
                "task",
                f"--audio={wav}",
                f"--output={output}",
                f"--family={family}",
                f"--mode={mode}",
            ],
            check=True,
            timeout=3600,
            capture_output=True,
            text=True,
        )
        report = json.loads((output / "report.json").read_text())
    return {
        "turns": report["result"]["turns"],
        "capacity": capacities[family],
        "backend": "workspace",
        "native": report,
    }
