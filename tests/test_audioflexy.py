# this_file: tests/test_audioflexy.py
"""Provider integration through real library APIs with only model engines faked."""

import json
import sys
import wave
from types import ModuleType
from types import SimpleNamespace as N

from vexy_audioflexy.speech import inference, qwen
from vexy_audioflexy.speech.types import Turn, Word

from vexy_subs import pipeline
from vexy_subs.cli import CLI
from vexy_subs.speech_identity import implementation


def test_pipeline_when_library_engines_fake_then_aligns_exports_and_resumes(
    tmp_path, monkeypatch
):
    from vexy_subs import inference as legacy_inference
    from vexy_subs import qwen as legacy_qwen
    from vexy_subs.types import Turn as LegacyTurn
    from vexy_subs.types import Word as LegacyWord

    assert legacy_inference is inference and legacy_qwen is qwen
    assert LegacyWord is Word and LegacyTurn is Turn
    assert pipeline.transcribe is inference.transcribe
    assert pipeline.diarize is inference.diarize
    observed = []

    def recognize(audio, **kwargs):
        observed.append(("asr", kwargs))
        return N(text="Hello API. Ready now?", generation_tokens=6)

    def align(**kwargs):
        observed.append(("alignment", kwargs))
        return N(
            items=[
                N(text=text, start_time=start, end_time=end)
                for text, start, end in (
                    ("Hello", 0, 0.4),
                    ("API", 0.4, 0.8),
                    ("Ready", 1.1, 1.5),
                    ("now", 1.5, 1.9),
                )
            ]
        )

    def diarize(audio, **kwargs):
        observed.append(("diarization", kwargs))
        return N(segments=[N(start=0, end=1, speaker=0), N(start=1, end=2, speaker=1)])

    def streaming(config):
        assert config == "offline"

    stt, vad = ModuleType("mlx_audio.stt"), ModuleType("mlx_audio.vad")
    stt.load = lambda model, strict: N(
        generate=align if model == qwen.ALIGNER else recognize
    )
    vad.load = lambda model, strict: N(generate=diarize, set_streaming_config=streaming)
    monkeypatch.setitem(sys.modules, "mlx_audio.stt", stt)
    monkeypatch.setitem(sys.modules, "mlx_audio.vad", vad)
    monkeypatch.setattr(qwen, "mlx_available", lambda: True)
    video = tmp_path / "synthetic.wav"
    with wave.open(str(video), "wb") as wav:
        wav.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
        wav.writeframes(b"\0\0" * 32000)
    hints = tmp_path / "hints.txt"
    hints.write_text("Terms: API.\nTitle: Synthetic test")
    reference = tmp_path / "reference.srt"
    reference.write_text("1\n00:00:00,000 --> 00:00:01,000\nHello API.\n")
    options = {
        "prompt_file": str(hints),
        "reference_file": str(reference),
        "beautify": False,
    }
    result = pipeline.run(str(video), **options)
    assert [item[0] for item in observed] == ["asr", "alignment", "diarization"]
    assert "Known terminology: API" in observed[0][1]["system_prompt"]
    assert "Title: Synthetic test" in observed[0][1]["system_prompt"]
    assert "Human-edited transcript of this passage" in observed[0][1]["system_prompt"]
    assert result["verification"]["speakers"] == 2
    assert result["alignment"]["dropped_chunks"] == []
    words = json.loads((tmp_path / "synthetic.words.json").read_text())["words"]
    assert [word["text"] for word in words] == ["Hello", "API.", "Ready", "now?"]
    assert {word["speaker"] for word in words} == {"speaker_0", "speaker_1"}
    assert pipeline.run(str(video), **options) == result
    assert len(observed) == 3
    assert CLI().verify(str(tmp_path))["verified"] == 1
    assert (
        CLI().render(
            str(tmp_path / "synthetic.words.json"),
            str(tmp_path / "edited"),
            beautify=False,
        )["speakers"]
        == 2
    )

    # Installing punctuation alone must reuse recognition, alignment and diarization.
    from vexy_subs import speech_identity

    original_version = speech_identity.version
    monkeypatch.setattr(
        speech_identity,
        "version",
        lambda name: (
            "changed-punctuation-version"
            if name == "deepmultilingualpunctuation"
            else original_version(name)
        ),
    )
    runtime_refreshed = pipeline.run(str(video), force=True, **options)
    assert runtime_refreshed["key"] != result["key"] and len(observed) == 3

    # A punctuation implementation change must leave recognition/diarization cached.
    def changed(*modules):
        identity = implementation(*modules)
        if "punctuation" in modules:
            identity["sha256"] = "changed-provider-punctuation"
        return identity

    monkeypatch.setattr(pipeline, "implementation", changed)
    refreshed = pipeline.run(str(video), force=True, **options)
    assert refreshed["key"] != result["key"] and len(observed) == 3
    options.update(beautify=True, beautify_language="de")
    editorial = pipeline.run(str(video), force=True, **options)
    assert len(observed) == 3

    def editorial_change(*modules):
        identity = changed(*modules)
        if "language" in modules:
            identity["sha256"] = "changed-provider-editorial"
        return identity

    monkeypatch.setattr(pipeline, "implementation", editorial_change)
    updated = pipeline.run(str(video), force=True, **options)
    assert updated["key"] != editorial["key"] and len(observed) == 3


def test_identity_when_provider_source_changes_then_cache_digest_changes(
    tmp_path, monkeypatch
):
    from vexy_audioflexy.speech import hints

    original = implementation("hints")
    source = tmp_path / "hints.py"
    source.write_bytes(b"# different provider implementation")
    monkeypatch.setattr(hints, "__file__", str(source))
    assert implementation("hints")["sha256"] != original["sha256"]


def test_cli_when_base_install_then_reports_actual_provider():
    assert CLI().models()["provider"]["package"] == "vexy-audioflexy"
    assert CLI().doctor()["inference_provider"] == "vexy-audioflexy"


def test_doctor_when_both_native_envs_set_then_uses_provider_precedence(monkeypatch):
    from vexy_subs import cli

    monkeypatch.setenv("VEXY_AUDIOFLEXY_AUDIOCPP_BIN", "provider-cli")
    monkeypatch.setenv("VEXY_SUBS_AUDIOCPP_BIN", "legacy-cli")
    monkeypatch.setattr(
        cli.shutil, "which", lambda name: name if name == "provider-cli" else None
    )
    report = CLI().doctor()
    assert (
        report["audiocpp_installed"] is True and report["inference_installed"] is True
    )


def test_identity_when_only_punctuation_runtime_changes_then_inference_stays_reusable(
    monkeypatch,
):
    from vexy_subs import speech_identity

    modules = (
        "inference",
        "qwen",
        "alignment",
        "audiocpp",
        "workspace",
        "hints",
        "types",
        "io",
    )
    before = implementation(*modules)
    punctuation = implementation("punctuation", "hints", "types")
    original_version = speech_identity.version
    monkeypatch.setattr(
        speech_identity,
        "version",
        lambda name: (
            "changed-punctuation-version"
            if name == "deepmultilingualpunctuation"
            else original_version(name)
        ),
    )
    assert implementation(*modules) == before
    assert implementation("punctuation", "hints", "types") != punctuation
    assert "transformers" in before["runtimes"]
