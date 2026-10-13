# this_file: tests/test_beautify.py
"""Language, layout and timing acceptance tests with synthetic dialogue."""

import json
from dataclasses import asdict

import pytest

from vexy_subs.beautify import audit, beautify
from vexy_subs.beautify_config import load_config
from vexy_subs.layout import balanced_lines
from vexy_subs.types import Word
from vexy_subs.typography import clean_words, typograph


def test_typography_uses_language_quotes_apostrophes_and_spacing():
    assert typograph('"It\'s... fine"', "en") == "“It’s… fine”"
    assert typograph('"Hallo"', "de") == "„Hallo“"
    assert typograph('"Bonjour" !', "fr") == "«\u202fBonjour\u202f»\u202f!"
    assert typograph('"Cześć"', "pl") == "„Cześć”"
    assert typograph("3.14 -- 4.5", "en") == "3.14 — 4.5"


def test_cleanup_retains_raw_words_speaker_changes_and_meaningful_repetition():
    raw = [
        Word(t, i / 4, (i + 1) / 4, "a")
        for i, t in enumerate(
            [
                "Uhm,",
                "I",
                "I",
                "think",
                "that,",
                "that",
                "works.",
                "Very",
                "very",
                "good.",
            ]
        )
    ]
    original = [asdict(w) for w in raw]
    cleaned, edits = clean_words(raw, "en")
    assert [w.text for w in cleaned] == [
        "I",
        "think",
        "that",
        "works.",
        "Very",
        "very",
        "good.",
    ]
    assert [asdict(w) for w in raw] == original, "Raw recognition must remain untouched"
    assert len(edits) == 3
    assert (
        len(clean_words([Word("Yes.", 0, 1, "a"), Word("Yes.", 1, 2, "b")], "en")[0])
        == 2
    )


def test_balanced_lines_obey_limit_and_do_not_strand_articles():
    text = "We should preserve the original font and its carefully drawn outlines."
    lines = balanced_lines(text, "en")
    assert len(lines.splitlines()) == 2
    assert all(len(line) <= 42 for line in lines.splitlines())
    assert not lines.splitlines()[0].endswith(("the", "its", "and"))
    assert " ".join(lines.splitlines()) == text


def test_beautification_merges_short_sentences_and_respects_frames():
    words = [
        Word(t, i * 0.2, i * 0.2 + 0.18, "a")
        for i, t in enumerate(["Hi.", "This", "is", "a", "simple", "example."])
    ]
    cleaned, cues, info = beautify(words, duration=3, language="en", fps=25)
    assert cleaned and cues
    assert all(5 / 6 <= c.end - c.start <= 7 for c in cues)
    assert all(abs(c.start * 25 - round(c.start * 25)) < 1e-5 for c in cues)
    assert not info["audit"]["violations"]


def test_unsatisfiable_timing_is_reported_without_shifting_dialogue():
    words = [Word("One.", 0, 0.1, "a"), Word("Two.", 0.1, 0.2, "b")]
    _, cues, info = beautify(words, duration=0.3, language="en", fps=25)
    assert info["audit"]["violations"], (
        "Dense speaker changes must not get a false pass"
    )
    assert max(c.end for c in cues) <= 0.3
    assert {c.speaker for c in cues} == {"a", "b"}


def test_configuration_has_canonical_path_and_env_precedence(tmp_path, monkeypatch):
    toml = tmp_path / "config.toml"
    toml.write_text(
        '[beautify]\nbackend="local"\n[llm]\nmodel="file-model"\nbase_url="http://localhost:1234/v1"\n'
    )
    env = tmp_path / ".env"
    env.write_text("VEXY_SUBS_LLM_MODEL=dotenv-model\n")
    monkeypatch.setenv("VEXY_SUBS_LLM_MODEL", "environment-model")
    config = load_config(str(toml), str(env))
    assert config.model == "environment-model"
    assert config.base_url == "http://localhost:1234/v1"
    assert "config.toml" in str(load_config().config_path)
    with pytest.raises(ValueError):
        load_config(backend="unknown")


def test_standalone_managed_cleanup_preserves_hash_verification(tmp_path):
    from vexy_subs.cli import CLI
    from vexy_subs.formats import write
    from vexy_subs.io import save, sha256
    from vexy_subs.types import Cue

    stem = tmp_path / "sample"
    words = [Word("Uhm,", 0, 0.2, "a"), Word("Hello.", 0.2, 1, "a")]
    save(tmp_path / "sample.words.json", {"words": [asdict(w) for w in words]})
    write([Cue(0, 1, "Uhm, Hello.", "a")], stem)
    save(
        tmp_path / "sample.vexy-subs.json",
        {
            "duration": 2,
            "settings": {},
            "source_filename": "sample.mp4",
            "outputs": {
                e: sha256(tmp_path / ("sample" + e))
                for e in (".srt", ".vtt", ".ass", ".words.json")
            },
        },
    )
    result = CLI().beautify(str(tmp_path), language="en", fps=25)
    assert result["processed"] == 1
    assert CLI().verify(str(tmp_path))["verified"] == 1
    receipt = json.loads((tmp_path / "sample.vexy-subs.json").read_text())
    assert receipt["beautification"]["removed_words"] == 1
    assert (tmp_path / "sample.work" / "beautify-original" / "sample.srt").exists()
    assert CLI().beautify(str(tmp_path), language="en", fps=25)["skipped"] == 1


def test_audit_counts_visible_characters_and_flags_long_tokens():
    from vexy_subs.types import Cue

    result = audit([Cue(0, 1, "x" * 43, "a")], 2, 25, "en")
    assert "line_length" in result["violations"][0]["rules"]


def test_llm_uses_configured_endpoint_and_rejects_rewrites(monkeypatch):
    import httpx

    from vexy_subs.beautify_llm import edit, validate

    config = load_config(backend="local")
    from dataclasses import replace

    config = replace(
        config,
        backend="llm",
        model="tiny-editor",
        base_url="http://localhost:1234/v1",
        api_key="test-only",
    )
    real_client = httpx.Client
    seen = []

    def handler(request):
        seen.append(json.loads(request.content))
        assert request.url.path == "/v1/chat/completions"
        assert request.headers["authorization"] == "Bearer test-only"
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "words": [
                                        {"id": 0, "text": "Hello,"},
                                        {"id": 1, "text": "there!"},
                                    ]
                                }
                            )
                        }
                    }
                ]
            },
        )

    monkeypatch.setattr(
        httpx,
        "Client",
        lambda **kwargs: real_client(transport=httpx.MockTransport(handler), **kwargs),
    )
    words = [Word("hello", 0, 1, "a"), Word("there", 1, 2, "a")]
    result, edits = edit(words, "en", config)
    assert [w.text for w in result] == ["Hello,", "there!"] and not edits
    assert seen[0]["model"] == "tiny-editor"
    assert "test-only" not in json.dumps(config.receipt())
    for entries in (
        [],
        [{"id": 1, "text": "there"}, {"id": 0, "text": "hello"}],
        [{"id": 0, "text": "Goodbye"}, {"id": 1, "text": "there"}],
    ):
        with pytest.raises(ValueError):
            validate(entries, words, 0)


def test_standalone_srt_vtt_ass_import_and_strict_preserve_originals(tmp_path):
    from vexy_subs.cli import CLI
    from vexy_subs.postprocess import read_captions, resolve_stem, targets

    p = tmp_path / "a.b.srt"
    p.write_text("1\n00:00:00,000 --> 00:00:02,000\nUhm, hello there.\n\n")
    assert resolve_stem(p).name == "a.b"
    assert len(read_captions(p)[0]) == 3
    result = CLI().beautify(str(p), backend="local", language="en")
    assert result["processed"] == 1
    assert len(targets(tmp_path, True)) == 1
    assert read_captions(tmp_path / "a.b.vtt")[0]
    assert read_captions(tmp_path / "a.b.ass")[0]
    assert CLI().verify(str(tmp_path))["verified"] == 1
    bad = tmp_path / "bad.srt"
    bad.write_text("1\n00:00:00,000 --> 00:00:00,100\n" + "x" * 100 + "\n\n")
    original = bad.read_bytes()
    with pytest.raises(ValueError, match="constraints"):
        CLI().beautify(str(bad), backend="local", language="en", strict=True)
    assert bad.read_bytes() == original
    CLI().beautify(str(bad), backend="local", language="en")
    with pytest.raises(ValueError, match="constraints"):
        CLI().verify(str(tmp_path), strict=True)
    with pytest.raises(ValueError, match="constraints"):
        CLI().beautify(str(bad), backend="local", language="en", strict=True)


def test_non_english_detection_and_empty_subtitles():
    from vexy_subs.beautify import detect_language

    french = [
        Word(
            "Bonjour tout le monde, je vous présente notre nouveau logiciel de typographie.",
            0,
            4,
        )
    ]
    assert detect_language(french)["language"] == "fr"
    assert beautify([], duration=0)[1] == []
    with pytest.raises(ValueError):
        beautify([Word("Bad", 2, 3)], duration=1)
    with pytest.raises(ValueError):
        detect_language([], "nonsense")


def test_out_of_order_instant_token_is_clamped_without_reordering_text():
    words = [
        Word("In", 0, 0.5, "a"),
        Word("the", 2, 2, "a"),
        Word("font.", 0.6, 1, "a"),
    ]
    cleaned, _, info = beautify(words, 3, language="en")
    assert [w.text for w in cleaned] == ["In", "the", "font."]
    assert cleaned[1].start == 0.6
    assert words[1].start == 2, "Original timestamps must remain recoverable"
    assert info["timing_repairs"][0]["reason"] == "instantaneous_neighbor_clamp"


def test_marked_phrase_restarts_are_removed_but_emphasis_survives():
    words = [
        Word(t, i * 0.2, i * 0.2 + 0.18, "a")
        for i, t in enumerate(["This", "is-", "this", "is", "the", "font."])
    ]
    cleaned, edits = clean_words(words, "en")
    assert [w.text for w in cleaned] == ["This", "is", "the", "font."]
    assert len(edits) == 2 and edits[0]["reason"] == "phrase_restart"
    raw = [
        Word(t, i, i + 0.8, "a")
        for i, t in enumerate(["Thank", "you,", "thank", "you!"])
    ]
    assert len(clean_words(raw, "en")[0]) == 4


@pytest.mark.parametrize("article", ["a", "an", "the"])
def test_article_fragment_restart_when_model_adds_period_then_keeps_completion(article):
    from vexy_subs.editorial import discourse

    raw = [
        Word(t, i * 0.2, i * 0.2 + 0.18, "a")
        for i, t in enumerate(
            ["Now,", "That's", article + ".", "that's", article, "lesson."]
        )
    ]
    original = [asdict(w) for w in raw]
    cleaned, edits = discourse(raw)
    assert [w.text for w in cleaned] == ["Now,", "that's", article, "lesson."], (
        "A model period after an unfinished article must not preserve a restart"
    )
    assert cleaned[1].start == raw[3].start, "Keep the completed phrase's timing"
    assert [e["reason"] for e in edits] == ["phrase_restart"] * 2
    assert [asdict(w) for w in raw] == original, "Preserve original recognition"


@pytest.mark.parametrize(
    "boundary",
    [
        "sentence",
        "question",
        "speaker",
        "pause",
        "unfinished",
        "completion_speaker",
        "completion_pause",
    ],
)
def test_phrase_restart_when_boundary_is_meaningful_then_retains_repetition(boundary):
    from vexy_subs.editorial import discourse

    tokens = ["That's", "good.", "That's", "good."]
    if boundary != "sentence":
        tokens = [
            "That's",
            "a?" if boundary == "question" else "a.",
            "that's",
            "a",
            "lesson.",
        ]
    raw = [Word(t, i * 0.2, i * 0.2 + 0.18, "a") for i, t in enumerate(tokens)]
    if boundary == "speaker":
        for w in raw[2:]:
            w.speaker = "b"
    if boundary == "pause":
        for w in raw[2:]:
            w.start += 1
            w.end += 1
    if boundary == "unfinished":
        raw = raw[:-1]
    if boundary == "completion_speaker":
        raw[-1].speaker = "b"
    if boundary == "completion_pause":
        raw[-1].start += 1
        raw[-1].end += 1
    cleaned, edits = discourse(raw)
    assert [asdict(w) for w in cleaned] == [asdict(w) for w in raw], (
        "Complete utterances, questions, speaker changes and pauses are not restarts"
    )
    assert not edits, "No deletion should be recorded for meaningful repetition"


def test_frame_rounding_preserves_word_ends_within_two_frames():
    from vexy_subs.beautify import retime
    from vexy_subs.types import Cue

    raw = [Cue(34.74, 35.86, "See me", "a"), Cue(35.86, 36.6, "because", "a")]
    adjusted = retime(raw, 38, 25, "en")
    assert raw[0].end - adjusted[0].end <= 2 / 25 + 1e-6
    assert adjusted[1].start - adjusted[0].end >= 2 / 25 - 1e-6
    assert abs(adjusted[1].start - raw[1].start) <= 1 / 25


def test_all_filler_input_becomes_valid_empty_subtitles(tmp_path):
    from vexy_subs.cli import CLI

    source = tmp_path / "fillers.srt"
    source.write_text("1\n00:00:00,000 --> 00:00:02,000\nUhm, err.\n\n")
    result = CLI().beautify(str(source), language="en", backend="local")
    assert result["sets"][0]["audit"]["cues"] == 0
    assert CLI().verify(str(tmp_path))["verified"] == 1
