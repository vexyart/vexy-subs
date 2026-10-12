# this_file: src/vexy_subs/beautify_llm.py
"""Optional OpenAI-compatible editing, validated against original timed tokens."""

import json
from dataclasses import replace

import httpx

from .beautify_config import Config
from .types import Word
from .typography import lexical


def edit(
    words: list[Word], language: str, config: Config
) -> tuple[list[Word], list[dict]]:
    """Permit deletions, casing and punctuation; reject rewritten/inserted lexical text."""
    prompt = (
        f"Edit {language} subtitle tokens. Remove hesitation fillers and accidental "
        "restarts, preserving intentional emphasis, negation, names, numbers and meaning. "
        "Fix sentence casing, punctuation, apostrophes and quotations. Never translate, "
        "paraphrase, add words or change spelling of technical terms. Return ONLY JSON "
        '{"words":[{"id":0,"text":"token"},...]}. Keep original IDs in increasing order; '
        "omit only unnecessary tokens. Each text must remain one original lexical token."
    )
    headers = {"Authorization": f"Bearer {config.api_key}"} if config.api_key else {}
    result, edits = [], []
    with httpx.Client(timeout=config.timeout, headers=headers) as client:
        for offset in range(0, len(words), 160):
            batch = words[offset : offset + 160]
            payload = [
                {"id": i + offset, "text": w.text, "speaker": w.speaker}
                for i, w in enumerate(batch)
            ]
            response = client.post(
                config.base_url + "/chat/completions",
                json={
                    "model": config.model,
                    "temperature": 0,
                    "messages": [
                        {"role": "system", "content": prompt},
                        {
                            "role": "user",
                            "content": json.dumps(payload, ensure_ascii=False),
                        },
                    ],
                },
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"].strip()
            if content.startswith("```"):
                content = "\n".join(content.splitlines()[1:-1])
            entries = json.loads(content)["words"]
            selected = validate(entries, batch, offset)
            result.extend(selected)
            retained = {item["id"] for item in entries}
            edits.extend(
                {
                    "index": i + offset,
                    "text": w.text,
                    "start": w.start,
                    "end": w.end,
                    "speaker": w.speaker,
                    "reason": "llm_deletion",
                }
                for i, w in enumerate(batch)
                if i + offset not in retained
            )
    return result, edits


def validate(entries: list, batch: list[Word], offset: int) -> list[Word]:
    """Reject malformed, reordered or hallucinated output before writing any captions."""
    if not isinstance(entries, list) or not entries:
        raise ValueError("LLM returned no valid words")
    ids = [e["id"] for e in entries]
    if ids != sorted(set(ids)) or any(
        type(i) is not int or not offset <= i < offset + len(batch) for i in ids
    ):
        raise ValueError("LLM changed token IDs or their order")
    if len(entries) < len(batch) * 0.7:
        raise ValueError(
            "LLM deleted over 30% of a batch; refusing destructive editing"
        )
    result = []
    for entry in entries:
        original = batch[entry["id"] - offset]
        text = entry["text"]
        if not isinstance(text, str) or not text.strip():
            raise ValueError("LLM returned an empty/non-string token")
        normalize = lambda s: lexical(s).replace("’", "'")
        if normalize(text) != normalize(original.text):
            raise ValueError(
                "LLM rewrote lexical text; only case/punctuation changes are allowed"
            )
        result.append(replace(original, text=text))
    for index, word in enumerate(batch):
        if index + offset not in ids and (
            any(c.isdigit() for c in word.text) or word.text.isupper()
        ):
            raise ValueError("LLM deleted a number or acronym")
    return result
