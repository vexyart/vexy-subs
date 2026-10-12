# this_file: tests/test_translate.py
"""Subtitle I/O and the two-pass translation pipeline, with a mocked LLM."""

import asyncio
import json
from pathlib import Path

import httpx
import pysubs2
import pytest

import vexy_subs
from vexy_subs import translate as tr
from vexy_subs.cli import CLI
from vexy_subs.formats import write
from vexy_subs.types import Cue

SRT = "1\n00:00:01,000 --> 00:00:04,000\nHello world\n\n2\n00:00:05,000 --> 00:00:08,000\nSecond subtitle\nwith two lines\n"
SPEC = "m::VEXY_TEST_KEY::http://llm.test/v1"

REAL_CLIENT = httpx.Client


def mock_llm(monkeypatch, transform=lambda t: "PL " + t, broken: int = 0):
    """Echo cues back transformed; the first ``broken`` replies drop a cue."""
    state = {"calls": [], "broken": broken}

    def handler(request):
        body = json.loads(request.content)
        state["calls"].append(body)
        request_text = body["messages"][1]["content"].split("\n\nYour previous reply")[
            0
        ]
        cues = json.loads(request_text)["cues"]
        out = [{"id": c["id"], "text": transform(c["text"])} for c in cues]
        if state["broken"] > 0:
            state["broken"] -= 1
            out = out[:-1]
        content = json.dumps({"cues": out}, ensure_ascii=False)
        return httpx.Response(
            200, json={"choices": [{"message": {"content": content}}]}
        )

    monkeypatch.setattr(
        httpx,
        "Client",
        lambda **kw: REAL_CLIENT(transport=httpx.MockTransport(handler), **kw),
    )
    return state


@pytest.fixture
def srt(tmp_path) -> Path:
    path = tmp_path / "in.srt"
    path.write_text(SRT)
    return path


def test_load_subtitles_when_srt_then_ms_timing_and_multiline_text(srt):
    loaded = tr.load_subtitles(srt)
    assert loaded.format == "srt" and loaded.source_path == str(srt)
    assert [(e.start_ms, e.end_ms) for e in loaded.events] == [
        (1000, 4000),
        (5000, 8000),
    ]
    assert loaded.events[1].text == "Second subtitle\nwith two lines"


@pytest.mark.parametrize("ext", [".srt", ".vtt", ".ass"])
def test_save_load_roundtrip_when_format_then_identical_events(srt, tmp_path, ext):
    loaded = tr.load_subtitles(srt)
    out = tmp_path / f"out{ext}"
    tr.save_subtitles(loaded, out)
    again = tr.load_subtitles(out)
    assert again.events == loaded.events, ext
    assert again.format == ext[1:]


def test_save_subtitles_when_extension_differs_then_extension_wins(srt, tmp_path):
    out = tmp_path / "out.vtt"
    tr.save_subtitles(tr.load_subtitles(srt), out)
    assert out.read_text().startswith("WEBVTT"), "SRT content written to a .vtt file"
    tr.save_subtitles(tr.load_subtitles(srt), tmp_path / "forced.txt", fmt="srt")
    assert "-->" in (tmp_path / "forced.txt").read_text()


def test_save_subtitles_when_built_from_scratch_then_plain_file(tmp_path):
    sf = tr.SubtitleFile([tr.Subtitle(0, 1000, "a"), tr.Subtitle(1000, 2000, "b\nc")])
    tr.save_subtitles(sf, tmp_path / "x.srt")
    assert [e.text for e in tr.load_subtitles(tmp_path / "x.srt").events] == [
        "a",
        "b\nc",
    ]


def test_load_subtitles_when_empty_file_then_no_events(tmp_path):
    empty = tmp_path / "empty.srt"
    empty.write_text("")
    loaded = tr.load_subtitles(empty)
    assert loaded.events == [] and loaded.format == "srt"


def test_chunk_subtitles_when_100_events_then_40_40_20():
    events = [tr.Subtitle(i, i + 1, str(i)) for i in range(100)]
    assert [len(c) for c in tr.chunk_subtitles(events)] == [40, 40, 20]
    assert tr.chunk_subtitles([]) == []
    assert [len(c) for c in tr.chunk_subtitles(events[:5])] == [5]
    with pytest.raises(ValueError):
        tr.chunk_subtitles(events, 0)


def test_load_vocabulary_when_valid_none_missing_or_bad(tmp_path):
    vocab = tmp_path / "v.json"
    vocab.write_text(
        json.dumps(
            {"API": "API", "neural network": "sieć neuronowa"}, ensure_ascii=False
        )
    )
    assert tr.load_vocabulary(vocab)["neural network"] == "sieć neuronowa"
    assert tr.load_vocabulary(None) == {} and tr.load_vocabulary("") == {}
    with pytest.raises(FileNotFoundError):
        tr.load_vocabulary(tmp_path / "missing.json")
    vocab.write_text("[1, 2]")
    with pytest.raises(ValueError, match="JSON object"):
        tr.load_vocabulary(vocab)


def test_prompts_when_vocab_and_context_then_included():
    plain = tr.translation_prompt("en", "pl", {}, None)
    assert "from en to pl" in plain and '"cues"' in plain
    assert "terminology" not in plain and "previously translated" not in plain
    rich = tr.translation_prompt(
        "en", "pl", {"API": "API"}, [tr.Subtitle(0, 1, "Line 0")]
    )
    assert "API → API" in rich and "Line 0" in rich
    refine = tr.refinement_prompt("en", "pl")
    assert "Review and refine" in refine and "pl" in refine and "same ids" in refine


def test_translate_run_when_two_pass_then_timing_kept_and_receipt_has_no_key(
    srt, tmp_path, monkeypatch
):
    monkeypatch.setenv("VEXY_TEST_KEY", "sk-secret")
    vocab = tmp_path / "v.json"
    vocab.write_text('{"world": "świat"}')
    state = mock_llm(monkeypatch)
    out = tmp_path / "out.vtt"
    result = tr.run(str(srt), str(out), SPEC, "en", "pl", vocab=str(vocab))
    assert len(state["calls"]) == 2, "translate + refine"
    assert "świat" in state["calls"][0]["messages"][0]["content"]
    loaded = tr.load_subtitles(out)
    assert [e.text for e in loaded.events] == [
        "PL PL Hello world",
        "PL PL Second subtitle\nwith two lines",
    ]
    assert [(e.start_ms, e.end_ms) for e in loaded.events] == [
        (1000, 4000),
        (5000, 8000),
    ]
    assert result["cues"] == 2 and result["format"] == "vtt"
    assert "sk-secret" not in json.dumps(result)


def test_translate_run_when_guards_then_errors(srt, tmp_path, monkeypatch):
    mock_llm(monkeypatch)
    out = tmp_path / "out.srt"
    out.write_text("x")
    with pytest.raises(FileExistsError):
        tr.run(str(srt), str(out), SPEC, "en", "pl")
    with pytest.raises(ValueError, match="overwrite the input"):
        tr.run(str(srt), str(srt), SPEC, "en", "pl", force=True)
    with pytest.raises(FileNotFoundError):
        tr.run(
            str(srt),
            str(tmp_path / "o.srt"),
            SPEC,
            "en",
            "pl",
            vocab=str(tmp_path / "nope.json"),
        )
    tr.run(str(srt), str(out), SPEC, "en", "pl", force=True, refine=False)
    assert tr.load_subtitles(out).events[0].text == "PL Hello world"


def test_translate_when_cue_dropped_once_then_retried(srt, monkeypatch):
    state = mock_llm(monkeypatch, broken=1)
    sf = tr.translate_file(tr.load_subtitles(srt), SPEC, "en", "pl", refine=False)
    assert len(state["calls"]) == 2 and len(sf.events) == 2
    assert "previous reply was rejected" in state["calls"][1]["messages"][1]["content"]


def test_translate_when_cue_always_dropped_then_fails_loud(srt, monkeypatch):
    mock_llm(monkeypatch, broken=99)
    with pytest.raises(ValueError, match="cue ids"):
        tr.translate_file(tr.load_subtitles(srt), SPEC, "en", "pl")


def test_translate_when_empty_text_reply_then_rejected(srt, monkeypatch):
    mock_llm(monkeypatch, transform=lambda t: " ")
    with pytest.raises(ValueError, match="empty"):
        tr.translate_file(tr.load_subtitles(srt), SPEC, "en", "pl")


def test_checker_when_reply_shape_wrong_then_value_error():
    check = tr._checker([0])
    for bad in ({}, [], {"cues": "x"}, {"cues": [{"id": 1, "text": "a"}]}):
        with pytest.raises(ValueError):
            check(bad)
    assert check({"cues": [{"id": 0, "text": " ok "}]}) == ["ok"]


def test_translate_when_previous_chunk_then_context_is_translated_text(
    tmp_path, monkeypatch
):
    state = mock_llm(monkeypatch)
    events = [tr.Subtitle(i * 1000, i * 1000 + 500, f"line {i}") for i in range(3)]
    out = tr.translate_events(
        events, tr.resolve_all(SPEC, {}), "en", "pl", chunk_size=2, refine=False
    )
    assert [e.text for e in out] == ["PL line 0", "PL line 1", "PL line 2"]
    assert "PL line 1" in state["calls"][1]["messages"][0]["content"]


def test_translate_when_ass_from_vexy_subs_then_speaker_styles_kept(
    tmp_path, monkeypatch
):
    mock_llm(monkeypatch)
    stem = tmp_path / "talk"
    write([Cue(0, 1, "Hi there", "SPEAKER_00"), Cue(1, 2, "Hello", "SPEAKER_01")], stem)
    out = tmp_path / "talk.pl.ass"
    tr.run(str(stem) + ".ass", str(out), SPEC, "en", "pl")
    original, translated = pysubs2.load(str(stem) + ".ass"), pysubs2.load(str(out))
    assert (
        [e.style for e in translated]
        == [e.style for e in original]
        == ["SPEAKER_00", "SPEAKER_01"]
    )
    assert (
        translated.styles["SPEAKER_01"].primarycolor
        == original.styles["SPEAKER_01"].primarycolor
    )
    assert [e.plaintext for e in translated] == ["PL PL Hi there", "PL PL Hello"]


def test_public_api_when_vttrix_style_calls_then_work(srt, monkeypatch):
    mock_llm(monkeypatch)
    subs = vexy_subs.load_subtitles(srt)
    sync = vexy_subs.translate_subtitles_sync(subs, SPEC, "en", "pl")
    asynced = asyncio.run(vexy_subs.translate_subtitles(subs, SPEC, "en", "pl"))
    assert sync.events == asynced.events and sync.events[0].text == "PL PL Hello world"


def test_cli_llm_group_when_called_then_json_safe_and_no_keys(tmp_path, monkeypatch):
    config = tmp_path / "config.toml"
    env = tmp_path / "empty.env"
    env.write_text("")
    config.write_text('[profiles.p]\nmodel = "m"\nmodel_provider = "zz"\n')
    for key in list(__import__("os").environ):
        if key.endswith("_API_KEY"):
            monkeypatch.delenv(key)
    monkeypatch.setenv("ZZ_API_KEY", "sk-hidden")
    monkeypatch.setenv("ZZ_API_ENDPOINT", "http://zz/v1")
    cli = CLI()
    assert cli.llm.path().endswith("config.toml")
    listing = cli.llm.profiles(str(config), env_file=str(env))
    assert listing["profiles"]["p"]["provider_found"] is True
    assert listing["providers"]["zz"]["key_set"] is True
    assert cli.llm.check("p", str(config), env_file=str(env)) == [
        {
            "model": "m",
            "base_url": "http://zz/v1",
            "env_key": "ZZ_API_KEY",
            "key_set": True,
        }
    ]
    assert cli.llm.discover(config_file=str(config), env_file=str(env))["saved"] == []
    assert cli.llm.discover(save=True, config_file=str(config), env_file=str(env))[
        "saved"
    ] == ["zz"]
    dumped = json.dumps([listing, cli.llm.profiles(str(config), env_file=str(env))])
    assert "sk-hidden" not in dumped and "sk-hidden" not in config.read_text()


def test_translate_when_chunk_keeps_failing_then_halved(monkeypatch):
    calls = []
    real = REAL_CLIENT

    def handler(request):
        body = json.loads(request.content)
        cues = json.loads(
            body["messages"][1]["content"].split("\n\nYour previous reply")[0]
        )["cues"]
        calls.append(len(cues))
        out = [{"id": c["id"], "text": "PL " + c["text"]} for c in cues]
        if len(cues) > 1:
            out = out[:1]  # The model always merges multi-cue requests.
        return httpx.Response(
            200, json={"choices": [{"message": {"content": json.dumps({"cues": out})}}]}
        )

    monkeypatch.setattr(
        httpx, "Client", lambda **kw: real(transport=httpx.MockTransport(handler), **kw)
    )
    events = [tr.Subtitle(i, i + 1, f"c{i}") for i in range(3)]
    out = tr.translate_events(
        events, tr.resolve_all(SPEC, {}), "en", "pl", refine=False
    )
    assert [e.text for e in out] == ["PL c0", "PL c1", "PL c2"]
    assert calls[:2] == [3, 3] and 1 in calls


def test_translate_run_when_input_is_not_subtitles_then_error(tmp_path, monkeypatch):
    mock_llm(monkeypatch)
    junk = tmp_path / "notes.srt"
    junk.write_text("just some prose, no timing")
    with pytest.raises(ValueError, match="No subtitle cues"):
        tr.run(str(junk), str(tmp_path / "o.srt"), SPEC, "en", "pl")


def test_translate_run_when_key_in_env_file_then_sent(srt, tmp_path, monkeypatch):
    monkeypatch.delenv("VEXY_TEST_KEY", raising=False)
    env = tmp_path / "keys.env"
    env.write_text("VEXY_TEST_KEY=from-dotenv\n")
    seen = []
    real = REAL_CLIENT

    def handler(request):
        seen.append(request.headers.get("authorization"))
        cues = json.loads(json.loads(request.content)["messages"][1]["content"])["cues"]
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": json.dumps({"cues": cues})}}]},
        )

    monkeypatch.setattr(
        httpx, "Client", lambda **kw: real(transport=httpx.MockTransport(handler), **kw)
    )
    tr.run(
        str(srt),
        str(tmp_path / "o.srt"),
        SPEC,
        "en",
        "pl",
        env_file=str(env),
        refine=False,
    )
    assert seen == ["Bearer from-dotenv"]


def test_translate_run_when_header_only_vtt_then_empty_output(tmp_path, monkeypatch):
    mock_llm(monkeypatch)
    empty = tmp_path / "empty.vtt"
    empty.write_text("WEBVTT\n\n")
    result = tr.run(str(empty), str(tmp_path / "o.vtt"), SPEC, "en", "pl")
    assert result["cues"] == 0 and (tmp_path / "o.vtt").read_text().startswith("WEBVTT")
