# this_file: tests/test_pipeline.py
"""Real local media decoding with synthetic, deterministic inference fixtures."""

import json
import wave

import pytest

from vexy_subs import pipeline
from vexy_subs.cli import CLI
from vexy_subs.types import Turn, Word


def test_pipeline_passes_prompt_then_colours_distinct_speakers_and_resumes(
    tmp_path, monkeypatch
):
    monkeypatch.setattr("vexy_subs.qwen.mlx_available", lambda: True)
    video = tmp_path / "clip.wav"
    with wave.open(str(video), "wb") as wav:
        wav.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
        wav.writeframes(b"\0\0" * 32000)
    prompt = tmp_path / "hints.txt"
    prompt.write_text("Terms: QuasarAPI.")
    observed = []

    def transcribe(wav, hints, *args):
        observed.append(hints)
        return [Word("hello", 0, 1), Word("quasarapi", 1, 2)], {
            "text": "hello quasarapi"
        }

    def diarize(*args):
        turns = [Turn(0, 1, "speaker_0"), Turn(1, 2, "speaker_1")]
        return turns, {
            "capacity": 8,
            "turns": [
                {"start": t.start, "end": t.end, "speaker": t.speaker} for t in turns
            ],
        }

    def restore(words, hints, *args):
        from vexy_subs.punctuation import apply_labels

        apply_labels(words, [["hello", ".", 1], ["quasarapi", "?", 1]], hints)
        return {"model": "fixture", "words": 2}

    monkeypatch.setattr(pipeline, "transcribe", transcribe)
    monkeypatch.setattr(pipeline, "diarize", diarize)
    monkeypatch.setattr(pipeline, "restore", restore)
    monkeypatch.setattr(
        pipeline,
        "repair",
        lambda *args: {"model": "fixture", "windows": 0, "repaired_words": 0},
    )
    data = pipeline.run(str(video), prompt_file=str(prompt))
    assert observed == ["Terms: QuasarAPI."], (
        "The actual prompt contents must reach ASR"
    )
    assert data["verification"]["speakers"] == 2
    assert pipeline.run(str(video), prompt_file=str(prompt)) == data
    assert len(observed) == 1, "Resume must skip expensive inference"
    assert CLI().verify(str(tmp_path))["verified"] == 1
    pipeline.run(str(video), prompt_file=str(prompt), force=True, beautify=False)
    assert len(observed) == 1, (
        "Changing beautification must reuse successful ASR caches"
    )
    prompt.write_text("Terms: ChangedAPI.")
    with pytest.raises(FileExistsError):
        pipeline.run(str(video), prompt_file=str(prompt))
    (tmp_path / "clip.srt").write_text("tampered")
    with pytest.raises(ValueError, match="Changed output"):
        CLI().verify(str(tmp_path))


def test_batch_requires_a_prompt_for_every_video_before_launch(tmp_path, monkeypatch):
    (tmp_path / "clip.mp4").touch()
    prompts = tmp_path / "prompts"
    prompts.mkdir()
    launched = []
    monkeypatch.setattr(
        "vexy_subs.cli.subprocess.run", lambda *args, **kwargs: launched.append(args)
    )
    with pytest.raises(ValueError, match="exactly one prompt"):
        CLI().batch(str(tmp_path), prompt_dir=str(prompts))
    assert not launched, "An incomplete hint set must fail before processing"


def test_doctor_does_not_require_credentials():
    assert CLI().doctor()["auth_required"] is False


def test_version_command_matches_package_version():
    from vexy_subs import __version__

    assert CLI().version() == __version__ and __version__, "Version is nonempty"


def test_offline_render_supports_manual_punctuation_edits(tmp_path):
    path = tmp_path / "edited.words.json"
    path.write_text(
        json.dumps(
            {
                "words": [
                    {"text": "Ready?", "start": 0, "end": 1, "speaker": "speaker_0"},
                    {"text": "Yes.", "start": 1, "end": 2, "speaker": "speaker_1"},
                ]
            }
        )
    )
    report = CLI().render(str(path), str(tmp_path / "edited"))
    assert report["cues"] == 2 and report["speakers"] == 2
    with pytest.raises(FileExistsError):
        CLI().render(str(path), str(tmp_path / "edited"))
