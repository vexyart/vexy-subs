# this_file: src/vexy_subs/hints.py
"""User-owned UTF-8 recognition hints; never bundled into distributions."""

import hashlib
from pathlib import Path


def read_prompt(prompt_file: str = "", prompt: str = "") -> tuple[str, dict]:
    """Accept .md or .txt, and record its digest without leaking its contents."""
    if not prompt_file:
        return prompt, {"sha256": hashlib.sha256(prompt.encode()).hexdigest()}
    path = Path(prompt_file)
    if path.suffix.lower() not in {".md", ".txt"}:
        raise ValueError("prompt_file must be a UTF-8 .md or .txt file")
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError("prompt_file is empty")
    return "\n".join(filter(None, (prompt, text))), {
        "filename": path.name,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def vocabulary(prompt: str) -> list[str]:
    """Use optional Names:/Terms: lines for casing; free-form hints still reach ASR."""
    terms = []
    for line in prompt.splitlines():
        if line.startswith(("Names:", "Terms:")):
            terms.extend(
                t.strip().rstrip(".") for t in line.split(":", 1)[1].split(",")
            )
    return [t for t in terms if t]
