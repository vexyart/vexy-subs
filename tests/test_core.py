# this_file: tests/test_core.py
"""Synthetic fixtures only: no conference material or personal data."""

import pysubs2
import pytest
import webvtt

from vexy_subs.cues import segment
from vexy_subs.formats import verify, write
from vexy_subs.hints import read_prompt
from vexy_subs.punctuation import apply_labels
from vexy_subs.speakers import assign
from vexy_subs.types import Turn, Word


def test_prompt_file_accepts_markdown_and_text(tmp_path):
    for suffix in (".md", ".txt"):
        p = tmp_path / ("hints" + suffix)
        p.write_text("Terms: QuasarAPI.")
        text, receipt = read_prompt(str(p))
        assert text == "Terms: QuasarAPI." and len(receipt["sha256"]) == 64
        assert "Terms" not in str(receipt), (
            "Do not leak prompt content into provenance metadata"
        )
    with pytest.raises(ValueError):
        read_prompt(str(tmp_path / "hints.json"))


def test_speaker_attribution_retains_overlap_ambiguity():
    words = [Word("hello", 0, 1), Word("there", 2, 3), Word("both", 4, 5)]
    assign(
        words,
        [
            Turn(0, 1, "speaker_0"),
            Turn(2, 3, "speaker_1"),
            Turn(4, 5, "speaker_0"),
            Turn(4, 5, "speaker_1"),
        ],
    )
    assert words[0].speaker == "speaker_0" and words[1].speaker == "speaker_1"
    assert words[2].ambiguous


def test_punctuation_changes_case_and_marks_without_rewriting_words():
    words = [Word("hello", 0, 1), Word("there", 1, 2), Word("quasarapi", 2, 3)]
    apply_labels(
        words,
        [["hello", "0", 1], ["there", "?", 1], ["quasarapi", ".", 1]],
        "Terms: QuasarAPI.",
    )
    assert [w.text for w in words] == ["Hello", "there?", "QuasarAPI."]
    assert [(w.start, w.end) for w in words] == [(0, 1), (1, 2), (2, 3)]
    with pytest.raises(ValueError):
        apply_labels(words, [])


def test_cues_break_at_speaker_changes_and_sentence_boundaries():
    words = [
        Word("Hello.", 0, 1, "speaker_0"),
        Word("Are", 1, 2, "speaker_0"),
        Word("you", 2, 3, "speaker_0"),
        Word("ready?", 3, 4, "speaker_1"),
    ]
    cues = segment(words)
    assert [c.text for c in cues] == ["Hello.", "Are you", "ready?"]
    assert [c.speaker for c in cues] == ["speaker_0", "speaker_0", "speaker_1"]


def test_all_formats_preserve_colours_voice_text_and_times(tmp_path):
    cues = segment([Word("Hello.", 0, 1, "speaker_0"), Word("Yes!", 1, 2, "speaker_1")])
    stem = tmp_path / "sample"
    palette = write(cues, stem)
    report = verify(stem, 2)
    assert report["speakers"] == 2 and report["vtt_styles"] == 2
    assert palette["speaker_0"]["color"] != palette["speaker_1"]["color"]
    assert "color=" in stem.with_suffix(".srt").read_text(), (
        "SubRip must retain font colour tags"
    )
    vtt = webvtt.read(str(stem) + ".vtt")
    assert [c.voice for c in vtt] == ["speaker_0", "speaker_1"]
    ass = pysubs2.load(str(stem) + ".ass")
    assert ass.styles["speaker_0"].primarycolor != ass.styles["speaker_1"].primarycolor


def test_invalid_times_fail_at_boundary():
    with pytest.raises(ValueError):
        Word("bad", 2, 1)
    with pytest.raises(ValueError):
        Turn(float("nan"), 1, "speaker_0")


def test_instant_words_inherit_actual_activity_and_stay_in_readable_cues():
    words = [Word("Hello.", 0, 1), Word("I.", 1, 1), Word("Agree.", 1, 2)]
    assign(words, [Turn(0, 2, "speaker_0")])
    assert all(w.speaker == "speaker_0" for w in words)
    cues = segment(words)
    assert " ".join(c.text for c in cues) == "Hello. I. Agree."
    assert all(c.end > c.start for c in cues), (
        "Instant words cannot become zero-length cues"
    )


def test_sentence_case_and_phrase_hints_preserve_generic_word_casing():
    words = [
        Word(t, i, i + 1)
        for i, t in enumerate(
            ["hello", "But", "a", "model", "uses", "model", "context", "protocol"]
        )
    ]
    apply_labels(
        words,
        [[w.text, "," if i == 0 else "0", 1] for i, w in enumerate(words)],
        "Terms: Model Context Protocol.",
    )
    assert [w.text for w in words] == [
        "Hello,",
        "but",
        "a",
        "model",
        "uses",
        "Model",
        "Context",
        "Protocol",
    ]


def test_more_than_eight_voices_receive_distinct_colours(tmp_path):
    words = [Word("Hello.", i, i + 0.8, f"speaker_{i:02}") for i in range(12)]
    palette = write(segment(words), tmp_path / "many")
    assert len({s["color"] for s in palette.values()}) == 12
    assert verify(tmp_path / "many", 12)["speakers"] == 12


def test_instant_completion_stays_with_previous_voice_at_handoff():
    words = [Word("We.", 0, 1), Word("Oh,", 1, 1), Word("Yes.", 1.2, 2)]
    assign(words, [Turn(0, 1, "speaker_0"), Turn(1.2, 2, "speaker_1")])
    cues = segment(words)
    assert [(c.text, c.speaker) for c in cues] == [
        ("We. Oh,", "speaker_0"),
        ("Yes.", "speaker_1"),
    ]
    assert words[1].ambiguous, "An instantaneous token is not certain voice evidence"


def test_instant_word_wrap_carries_timed_context_without_dropping_text():
    words = [Word("abcdefghijklmnop", i, i + 0.8, "speaker_0") for i in range(5)]
    words += [Word("instant", 4.8, 4.8, "speaker_0"), Word("Next.", 5, 6, "speaker_1")]
    cues = segment(words)
    assert sum(c.text.count("abcdefghijklmnop") for c in cues) == 5
    assert any("instant" in c.text for c in cues)
    assert all(len(c.text.splitlines()) <= 2 for c in cues)
