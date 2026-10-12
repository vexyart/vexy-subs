# this_file: src/vexy_subs/beautify.py
"""Local language detection, conservative editing, balanced cues and timing audit."""

import itertools
import math
from dataclasses import replace
from functools import lru_cache

from .beautify_config import Config, load_config
from .layout import balanced_lines, boundary_cost
from .syntax import tags as pos_tags
from .types import Cue, Word
from .typography import clean_words, typograph

# Verified adult translated-subtitle profiles; SDH and children's limits differ.
PROFILES = {"en": (42, 20), "de": (42, 17), "fr": (42, 17), "pl": (42, 17)}


@lru_cache(maxsize=1)
def identifier():
    """Load langid's bundled 97-language Naive Bayes model once; no model download."""
    from langid.langid import LanguageIdentifier, model

    return LanguageIdentifier.from_modelstring(model, norm_probs=True)


def detect_language(words: list[Word], language: str = "") -> dict:
    """Sample across the recording, not only a short introductory greeting."""
    sample = " ".join(w.text for w in words[:: max(1, len(words) // 2000)])[:20000]
    detected, probability = (
        identifier().classify(sample) if sample.strip() else ("und", 0)
    )
    chosen = (language or detected).lower().replace("_", "-").split("-")[0]
    if chosen != "und" and chosen not in identifier().nb_classes:
        raise ValueError(f"Unsupported language code: {chosen}")
    return {
        "language": chosen,
        "detected": detected,
        "probability": float(probability),
        "overridden": bool(language),
        "model": "langid-1.1.6-naive-bayes",
    }


def candidate(
    words: list[Word], language: str, config: Config, tags: tuple[str, ...] = ()
) -> Cue | None:
    """Construct only length-bounded candidates; retain indivisible oversized tokens."""
    text = " ".join(w.text.replace("<unk>", "[unk]") for w in words)
    limit = PROFILES.get(language, (42, 17))[0]
    if words[-1].end - words[0].start > 7 and len(words) > 1:
        return None
    try:
        text = balanced_lines(text, language, limit, config.font, tags)
    except ValueError:
        if len(words) > 1:
            return None
    return Cue(words[0].start, words[-1].end, text, words[0].speaker)


def segment_block(
    words: list[Word], language: str, config: Config, fps: float
) -> list[Cue]:
    """Dynamic programming chooses phrase boundaries and avoids flashing short cues."""
    count = len(words)
    scores, choices = [math.inf] * (count + 1), [None] * count
    scores[count] = 0
    cps = PROFILES.get(language, (42, 17))[1]
    tags = pos_tags([w.text for w in words], language)
    for start in range(count - 1, -1, -1):
        for end in range(start + 1, min(count, start + 60) + 1):
            cue = candidate(words[start:end], language, config, tags[start:end])
            if cue is None:
                break
            following = words[end].start if end < count else cue.end + 0.5
            available = max(0.04, min(7, following - cue.start - 2 / fps))
            chars = len(cue.text.replace("\n", ""))
            cost = (
                3
                + 5000 * max(0, 5 / 6 - available)
                + 100 * max(0, chars / available - cps) ** 2
            )
            if end < count:
                cost += boundary_cost(
                    words[end - 1].text,
                    words[end].text,
                    language,
                    tags[end - 1],
                    tags[end],
                )
            else:
                cost -= 1
            if cost + scores[end] < scores[start]:
                scores[start], choices[start] = cost + scores[end], (end, cue)
    result, index = [], 0
    while index < count:
        end, cue = choices[index]
        result.append(cue)
        index = end
    return result


def retime(cues: list[Cue], duration: float, fps: float, language: str) -> list[Cue]:
    """Snap to frames, borrow up to half a second and preserve a two-frame gap."""
    result = []
    cps = PROFILES.get(language, (42, 17))[1]
    last_frame = math.floor(duration * fps + 1e-7)
    starts = [max(0, math.ceil(c.start * fps - 1e-7)) for c in cues]
    for index in range(1, len(starts)):
        starts[index] = max(starts[index], starts[index - 1] + 3)
    for index, cue in enumerate(cues):
        start = starts[index]
        following = starts[index + 1] - 2 if index + 1 < len(cues) else last_frame
        latest = min(following, last_frame, start + math.floor(7 * fps))
        required = math.ceil(
            max(5 / 6, len(cue.text.replace("\n", "")) / cps) * fps - 1e-7
        )
        end = max(math.ceil(cue.end * fps - 1e-7), start + required)
        end = min(end, latest, math.floor((cue.end + 0.5) * fps + 1e-7))
        # Close sub-half-second gaps only when audio-tail and maximum-duration permit.
        if 2 / fps <= (following - end + 2) / fps < 0.5 and following <= math.floor(
            (cue.end + 0.5) * fps
        ):
            end = min(following, start + math.floor(7 * fps), last_frame)
        if end <= start:
            # Infeasible handoffs must remain visible and be flagged by the audit.
            end = min(last_frame, start + 1)
        if end <= start:
            raise ValueError(
                "No display frame available; inspect source duration/alignment"
            )
        result.append(Cue(start / fps, end / fps, cue.text, cue.speaker))
    return result


def audit(cues: list[Cue], duration: float, fps: float, language: str) -> dict:
    """Audit visible text/durations/gaps; full shot/audio editorial conformance is separate."""
    limit, cps = PROFILES.get(language, (42, 17))
    violations = []
    peak = 0
    for index, cue in enumerate(cues):
        seconds = cue.end - cue.start
        rate = len(cue.text.replace("\n", "")) / max(seconds, 0.001)
        peak = max(peak, rate)
        rules = []
        if len(cue.text.splitlines()) > 2:
            rules.append("line_count")
        if any(len(line) > limit for line in cue.text.splitlines()):
            rules.append("line_length")
        if seconds < 5 / 6 - 0.001:
            rules.append("minimum_duration")
        if seconds > 7.001:
            rules.append("maximum_duration")
        if rate > cps + 0.05:
            rules.append("reading_speed")
        if not 0 <= cue.start < cue.end <= duration + 0.001:
            rules.append("timeline")
        if index:
            gap = cue.start - cues[index - 1].end
            if gap < 2 / fps - 0.001:
                rules.append("frame_gap")
            elif 2 / fps + 0.001 < gap < 0.5 - 0.001:
                rules.append("short_gap")
        if rules:
            violations.append(
                {
                    "cue": index + 1,
                    "start": cue.start,
                    "rules": rules,
                    "cps": round(rate, 2),
                }
            )
    return {
        "cues": len(cues),
        "profile": language if language in PROFILES else "unverified-language-fallback",
        "max_chars_per_line": limit,
        "max_cps": cps,
        "fps": fps,
        "peak_cps": round(peak, 2),
        "violations": violations,
        "numeric_rules_pass": not violations and language in PROFILES,
        "editorial_review_required": True,
    }


def beautify(
    words: list[Word],
    duration: float,
    language: str = "",
    fps: float = 25,
    config: Config | None = None,
) -> tuple[list[Word], list[Cue], dict]:
    """Detect language → clean → optional validated LLM → typography → layout → audit."""
    if not math.isfinite(duration + fps) or duration < 0 or fps <= 0:
        raise ValueError("Require nonnegative finite duration and positive finite fps")
    words, timing_repairs = repair_instantaneous(words)
    if any(w.end > duration + 0.1 for w in words) or any(
        a.start > b.start for a, b in itertools.pairwise(words)
    ):
        raise ValueError("Word timing exceeds source duration or is nonmonotonic")
    config = config or load_config()
    detection = detect_language(words, language)
    language = detection["language"]
    from .editorial import discourse, sentence_case

    prepared, edits = discourse(words) if language == "en" else (words, [])
    cleaned, local_edits = clean_words(prepared, language)
    edits.extend(local_edits)
    if language == "en":
        cleaned = sentence_case(cleaned)
    if config.backend == "llm" and cleaned:
        from .beautify_llm import edit

        cleaned, llm_edits = edit(cleaned, language, config)
        edits.extend(llm_edits)
    by_speaker = {}
    for word in cleaned:
        by_speaker.setdefault(word.speaker, []).append(word)
    for spoken in by_speaker.values():
        parts = typograph(" \u2063".join(w.text for w in spoken), language).split(
            "\u2063"
        )
        for word, text in zip(spoken, parts, strict=True):
            word.text = text.strip(" ")
    blocks = []
    for word in cleaned:
        if (
            not blocks
            or word.speaker != blocks[-1][-1].speaker
            or word.start - blocks[-1][-1].end > 0.8
        ):
            blocks.append([])
        blocks[-1].append(word)
    cues = []
    for block in blocks:
        cues.extend(segment_block(block, language, config, fps))
    before_retime = cues
    cues = retime(cues, duration, fps, language)
    checks = audit(cues, duration, fps, language)
    for index, (before, after) in enumerate(zip(before_retime, cues, strict=True)):
        if abs(before.start - after.start) > 2 / fps + 0.001:
            checks["violations"].append(
                {"cue": index + 1, "start": after.start, "rules": ["audio_start_sync"]}
            )
        if before.end - after.end > 2 / fps + 0.001:
            checks["violations"].append(
                {
                    "cue": index + 1,
                    "start": after.start,
                    "rules": ["audio_end_truncation"],
                }
            )
    checks["numeric_rules_pass"] = not checks["violations"] and language in PROFILES
    return (
        cleaned,
        cues,
        {
            "settings": config.receipt(),
            "language_detection": detection,
            "input_words": len(words),
            "output_words": len(cleaned),
            "removed_words": len(edits),
            "timing_repairs": timing_repairs,
            "edits": edits,
            "audit": checks,
        },
    )


def repair_instantaneous(words: list[Word]) -> tuple[list[Word], list[dict]]:
    """Clamp out-of-order zero-duration ASR tokens to neighboring timed context."""
    copied = [replace(w) for w in words]
    next_timed = [None] * len(words)
    following = None
    for index in range(len(copied) - 1, -1, -1):
        next_timed[index] = following
        if copied[index].end > copied[index].start:
            following = copied[index]
    repairs, previous = [], None
    for index, word in enumerate(copied):
        if word.start != word.end:
            previous = word
            continue
        following = next_timed[index]
        low = previous.end if previous else 0
        high = following.start if following else max(low, word.start)
        if low > high:
            low = previous.start if previous else high
        anchor = max(low, min(word.start, high))
        if anchor != word.start:
            repairs.append(
                {
                    "index": index,
                    "text": word.text,
                    "original_start": word.start,
                    "start": anchor,
                    "reason": "instantaneous_neighbor_clamp",
                }
            )
            word.start = word.end = anchor
            word.ambiguous = True
    return copied, repairs
