# this_file: tests/test_workspace.py
"""Workspace recognition must reach captions with real timing and cache identity."""

import json
from pathlib import Path

import pytest


def test_workspace_recognition_when_worker_returns_words_then_keeps_native_times(
    tmp_path, monkeypatch
):
    from vexy_subs import workspace

    root = tmp_path / "models"
    worker = root / "myasr/tools/speech-issue301.py"
    worker.parent.mkdir(parents=True)
    worker.write_text("# fixture")
    wav = tmp_path / "input.wav"
    wav.write_bytes(b"fixture")
    observed = []

    def run(args, **kwargs):
        observed.append(args)
        output = Path(
            next(x.split("=", 1)[1] for x in args if x.startswith("--output="))
        )
        output.write_text(
            json.dumps(
                {
                    "words": [{"text": "API", "start": 0.1, "end": 0.6}],
                    "raw": {
                        "language": "en",
                        "alignment": {"native_word_estimates": True},
                    },
                }
            )
        )

    monkeypatch.setattr(workspace.subprocess, "run", run)
    words, raw = workspace.transcribe(wav, "Terms: API", "en", "chosen", str(root))
    assert words[0].start == 0.1 and words[0].end == 0.6, (
        "Do not interpolate actual word times"
    )
    assert raw["alignment"]["native_word_estimates"] is True
    assert "--model=chosen" in observed[0], "Use the requested workspace model"
    assert "--prompt=Terms: API" in observed[0], (
        "Forward recognition context as one argv value"
    )


def test_workspace_when_unconfigured_then_rejects_before_inference(monkeypatch):
    from vexy_subs import workspace

    monkeypatch.delenv("VEXY_SUBS_MODEL_WORKSPACE", raising=False)
    with pytest.raises(FileNotFoundError):
        workspace.root_path("")


def test_workspace_signature_when_worker_changes_then_invalidates_stage(tmp_path):
    from vexy_subs import workspace

    worker = tmp_path / "myasr/tools/speech-issue301.py"
    worker.parent.mkdir(parents=True)
    worker.write_text("first")
    first = workspace.signature(str(tmp_path))
    worker.write_text("second")
    assert workspace.signature(str(tmp_path)) != first, (
        "Worker changes must not reuse old inference"
    )
