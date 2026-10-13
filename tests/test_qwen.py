# this_file: tests/test_qwen.py
"""Qwen selection, lexical retention and actual alignment contracts."""

import json
import wave
from types import SimpleNamespace as N

import pytest


def test_auto_when_mlx_missing_then_selects_qwen_native(monkeypatch):
    from vexy_subs import qwen

    monkeypatch.setattr(qwen, "mlx_available", lambda: False)
    assert qwen.select_backend("auto") == "audiocpp", "Fallback must still use Qwen"
    monkeypatch.setattr(qwen, "mlx_available", lambda: True)
    assert qwen.select_backend("auto") == "mlx", "Prefer MLX when available"


@pytest.mark.parametrize("model", ["voxtral-small", "granite-speech", "kroko-en"])
def test_rejected_model_when_selected_then_fails_before_loading(model):
    from vexy_subs.qwen import check_model

    with pytest.raises(ValueError, match="removed"):
        check_model(model)


def test_aligner_when_punctuation_changes_then_preserves_original_text():
    from vexy_subs.qwen import retain_words

    words = retain_words(
        "FontLab 8.4, isn't bad!",
        [
            N(text="FontLab", start_time=0.1, end_time=0.5),
            N(text="84", start_time=0.5, end_time=1),
            N(text="isn't", start_time=1, end_time=1.3),
            N(text="bad", start_time=1.3, end_time=1.7),
        ],
        30,
        2,
    )
    assert [w.text for w in words] == ["FontLab", "8.4,", "isn't", "bad!"]
    assert words[0].start == 30.1 and words[-1].end == 31.7


@pytest.mark.parametrize(
    "text,items",
    [
        ("20 units", [N(text="2", start_time=0, end_time=1)]),
        ("hello", [N(text="hello", start_time=1, end_time=0)]),
        ("hello", [N(text="hello", start_time=0, end_time=3)]),
    ],
)
def test_alignment_when_content_or_bounds_invalid_then_rejects(text, items):
    from vexy_subs.qwen import retain_words

    with pytest.raises(ValueError):
        retain_words(text, items, 0, 2)


def test_mlx_when_audio_spans_chunks_then_aligns_each_and_offsets_times(
    tmp_path, monkeypatch
):
    import sys

    from vexy_subs import qwen

    wav = tmp_path / "input.wav"
    with wave.open(str(wav), "wb") as out:
        out.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
        out.writeframes(b"\0\0" * 496000)
    observed = []

    def generate(audio, **kwargs):
        observed.append(kwargs)
        return N(text="API works.", generation_tokens=3)

    aligner = N(
        generate=lambda **kwargs: N(
            items=[
                N(text="API", start_time=0, end_time=0.4),
                N(text="works", start_time=0.4, end_time=0.8),
            ]
        )
    )
    monkeypatch.setitem(
        sys.modules,
        "mlx_audio.stt",
        N(
            load=lambda model, **kwargs: (
                aligner if "Aligner" in model else N(generate=generate)
            )
        ),
    )
    words, raw = qwen.transcribe(wav, "Terms: API.", "en", qwen.MODEL, qwen.ALIGNER)
    assert len(raw["segments"]) == 2 and words[2].start == 30
    assert observed[0]["system_prompt"] == observed[1]["system_prompt"]
    assert "API" in observed[0]["system_prompt"]
    assert raw["alignment"]["word_timestamps"] == "forced_alignment"


def test_native_when_outputs_present_then_preserves_text_and_sample_times(
    tmp_path, monkeypatch
):
    from vexy_subs import audiocpp

    wav = tmp_path / "clip.wav"
    with wave.open(str(wav), "wb") as out:
        out.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
        out.writeframes(b"\0\0" * 32000)
    model, aligner = tmp_path / "qwen.gguf", tmp_path / "aligner.gguf"
    model.touch()
    aligner.touch()
    observed = []

    def run(args, **kwargs):
        observed.append(args)
        from pathlib import Path

        Path(args[args.index("--text-out") + 1]).with_name("text_000.txt").write_text(
            "API works."
        )
        Path(args[args.index("--words-out") + 1]).with_name(
            "words_000.json"
        ).write_text(
            json.dumps(
                [
                    {"word": "API", "start_sample": 1600, "end_sample": 8000},
                    {"word": "works", "start_sample": 8000, "end_sample": 16000},
                ]
            )
        )
        return N(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(audiocpp.subprocess, "run", run)
    words, raw = audiocpp.transcribe(
        wav, "Terms: API.", "en", str(model), str(aligner), "fixture", "cpu"
    )
    assert words[-1].text == "works." and words[0].start == 0.1
    assert observed[0][observed[0].index("--family") + 1] == "qwen3_asr"
    assert raw["alignment"]["word_timestamps"] == "forced_alignment"


def test_native_configuration_when_missing_then_gives_setup_guidance(
    tmp_path, monkeypatch
):
    from vexy_subs import audiocpp

    monkeypatch.delenv("VEXY_SUBS_QWEN_MODEL", raising=False)
    with pytest.raises(FileNotFoundError, match="VEXY_SUBS_QWEN_MODEL"):
        audiocpp.model_path("", "default", "VEXY_SUBS_QWEN_MODEL")
    model = tmp_path / "qwen.gguf"
    model.write_bytes(b"weights")
    monkeypatch.setenv("VEXY_SUBS_QWEN_MODEL", str(model))
    assert audiocpp.model_path("default", "default", "VEXY_SUBS_QWEN_MODEL") == str(
        model
    )
    with pytest.raises(FileNotFoundError, match="audiocpp_cli"):
        audiocpp.binary_path("nonexistent-vexy-executable")
    with pytest.raises(ValueError):
        audiocpp.backend_name("unknown")


def test_native_failure_when_engine_errors_then_reports_without_fallback(monkeypatch):
    from vexy_subs import audiocpp

    monkeypatch.setattr(
        audiocpp.subprocess, "run", lambda *a, **k: N(returncode=1, stderr="bad model")
    )
    with pytest.raises(RuntimeError, match="bad model"):
        audiocpp.execute(["fixture"])


def test_pipeline_when_mlx_unavailable_then_native_qwen_reaches_all_formats(
    tmp_path, monkeypatch
):
    import sys
    from pathlib import Path

    from vexy_subs import audiocpp, pipeline, qwen

    wav = tmp_path / "clip.wav"
    with wave.open(str(wav), "wb") as out:
        out.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
        out.writeframes(b"\0\0" * 32000)
    model, aligner, diar = [
        tmp_path / name for name in ("qwen.gguf", "aligner.gguf", "diar.gguf")
    ]
    for name, path in [
        ("QWEN_MODEL", model),
        ("QWEN_ALIGNER", aligner),
        ("NEMOTRON_MODEL", diar),
    ]:
        path.write_bytes(b"fixture")
        monkeypatch.setenv("VEXY_SUBS_" + name, str(path))
    monkeypatch.setattr(qwen, "mlx_available", lambda: False)
    calls = []

    def execute(args):
        calls.append(args)
        if "--words-out" in args:
            Path(args[args.index("--text-out") + 1]).with_name(
                "text_000.txt"
            ).write_text("API works.")
            Path(args[args.index("--words-out") + 1]).with_name(
                "words_000.json"
            ).write_text(
                json.dumps(
                    [
                        {"word": "API", "start_sample": 1600, "end_sample": 8000},
                        {"word": "works", "start_sample": 8000, "end_sample": 16000},
                    ]
                )
            )
        else:
            Path(args[args.index("--turns-out") + 1]).write_text(
                json.dumps([{"speaker_id": 0, "start_sample": 0, "end_sample": 32000}])
            )

    monkeypatch.setattr(audiocpp, "execute", execute)
    result = pipeline.run(
        str(wav), diar_backend="audiocpp", audiocpp_bin=sys.executable, beautify=False
    )
    assert result["settings"]["asr_backend"] == "audiocpp"
    assert result["settings"]["punctuation_model"] == "asr"
    assert str(diar) in result["settings"]["native_diarization_identity"]
    assert result["verification"]["cues"] >= 1
    assert (
        pipeline.run(
            str(wav),
            diar_backend="audiocpp",
            audiocpp_bin=sys.executable,
            beautify=False,
        )
        == result
    )
    assert len(calls) == 2, "Resume must skip native recognition and diarization"
    model.write_bytes(b"changed weights")
    with pytest.raises(FileExistsError):
        pipeline.run(
            str(wav),
            diar_backend="audiocpp",
            audiocpp_bin=sys.executable,
            beautify=False,
        )


def test_models_when_listed_then_exposes_selected_stack_only():
    from vexy_subs.cli import CLI

    models = CLI().models()
    text = json.dumps(models).casefold()
    assert "qwen3-asr-1.7b" in text and "forcedaligner" in text and "nemotron" in text
    assert all(name not in text for name in ("voxtral", "granite", "kroko"))


def test_batch_when_native_options_requested_then_forwards_every_model(
    tmp_path, monkeypatch
):
    from vexy_subs.cli import CLI

    (tmp_path / "clip.mp4").touch()
    calls = []
    monkeypatch.setattr(
        "vexy_subs.cli.subprocess.run", lambda args, **kwargs: calls.append(args)
    )
    CLI().batch(
        str(tmp_path),
        asr_backend="audiocpp",
        asr_model="qwen.gguf",
        alignment_model="align.gguf",
        diar_model="diar.gguf",
        audiocpp_bin="engine",
        audiocpp_backend="cpu",
        max_speakers=20,
    )
    for argument in [
        "--asr_backend=audiocpp",
        "--asr_model=qwen.gguf",
        "--alignment_model=align.gguf",
        "--diar_model=diar.gguf",
        "--audiocpp_bin=engine",
        "--audiocpp_backend=cpu",
        "--max_speakers=20",
    ]:
        assert argument in calls[0], f"Missing batch option {argument}"
