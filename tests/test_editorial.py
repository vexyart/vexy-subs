# this_file: tests/test_editorial.py
"""Editorial cleanup protects literal meanings and speaker boundaries."""

from vexy_subs.editorial import discourse, sentence_case
from vexy_subs.types import Word


def timed(text):
    return [Word(t, i / 4, (i + 1) / 4, "a") for i, t in enumerate(text.split())]


def test_discourse_removes_hedges_and_marked_asides():
    result, edits = discourse(
        timed("So, yeah, I basically kind of draw, you know, outlines.")
    )
    assert " ".join(w.text for w in result) == "I draw outlines.", (
        "Remove discourse fillers"
    )
    assert len(edits) == 7, "Every removed token must have an audit record"


def test_discourse_preserves_literal_kinds_comparisons_and_knowledge():
    raw = timed("This kind of font is like that. You know how it works. I mean it.")
    result, edits = discourse(raw)
    assert result == raw and not edits, "Literal language must survive"


def test_discourse_preserves_adjectives_and_complement_clauses():
    raw = timed(
        "It works well, with a special kind of font. Tell me what you know, John. That is what I mean, too."
    )
    assert discourse(raw)[0] == raw, (
        "Do not mistake grammatical expressions for fillers"
    )


def test_discourse_does_not_cross_speakers_or_remove_answers():
    raw = timed("Yes. Okay. Kind of")
    raw[-1].speaker = "b"
    assert discourse(raw)[0] == raw, "Keep answers and split-speaker words"


def test_sentence_case_preserves_acronyms_and_corrects_continuations():
    raw = timed("hello. this Is a Glyphs API. We Use it.")
    result = sentence_case(raw)
    assert (
        " ".join(w.text for w in result) == "Hello. This is a Glyphs API. We Use it."
    ), "Keep names and acronyms"
    assert raw[0].text == "hello.", "Never mutate the source"


def test_discourse_removes_phrase_restarts_and_transfers_terminal_punctuation():
    result, edits = discourse(timed("We can we can draw outlines basically."))
    assert " ".join(w.text for w in sentence_case(result)) == "We can draw outlines.", (
        "Keep sentence punctuation after deletions"
    )
    assert len(edits) == 3


def test_discourse_keeps_negation_emphasis_and_grammatical_repeats():
    raw = timed(
        "No no. It is very very good. I had had enough. I know that that works."
    )
    assert discourse(raw)[0] == raw, "Do not collapse meaningful repetition"


def test_sentence_case_repairs_greeting_boundaries_and_repeated_responses():
    result, _ = discourse(timed("Yes, yes, excellent, Thank you. This Almost works."))
    assert (
        " ".join(w.text for w in sentence_case(result))
        == "Yes, excellent. Thank you. This almost works."
    )


def test_sentence_case_closes_standalone_responses_at_speaker_change():
    words = timed("No, we know.")
    words[1].speaker = words[2].speaker = "b"
    assert sentence_case(words)[0].text == "No.", "Responses need terminal punctuation"


def test_boundaries_protect_conjunctions_articles_and_contractions():
    from vexy_subs.layout import boundary_cost

    for left, right in [("the", "font"), ("and", "then"), ("It’s", "good")]:
        assert boundary_cost(left, right, "en") >= 1000, (
            "Keep grammatical phrases together"
        )
