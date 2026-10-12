# this_file: src/vexy_subs/llm.py
"""OpenAI-compatible endpoints from Codex-style providers/profiles or explicit specs.

Config lives in the vexy-subs ``config.toml`` beside ``[beautify]`` and ``[llm]``:

    [model_providers.cerebras]
    base_url = "https://api.cerebras.ai/v1"
    env_key = "CEREBRAS_API_KEY"

    [profiles.cerebras-code]
    model = "zai-glm-4.7"
    model_provider = "cerebras"

A spec is a profile name or ``model::ENV_KEY::base_url``; ``a,b`` tries ``a``
then ``b``. Providers are also discovered from ``{PREFIX}_API_KEY`` paired with
``{PREFIX}_API_ENDPOINT`` (or ``{PREFIX}_API_OPENAI``). Only variable names are
ever written to disk; key values stay in the environment.
"""

import json
import os
import random
import re
import tempfile
import time
import tomllib
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

import httpx
from dotenv import find_dotenv, load_dotenv
from loguru import logger
from platformdirs import user_config_path

_KEY_RE = re.compile(r"^([A-Z0-9_]+)_API_KEY$")
_SECTION_NAME = re.compile(r"^[A-Za-z0-9_-]+$")
_THINK = re.compile(r"^\s*<think>.*?</think>\s*", re.DOTALL)
RETRY_DELAY = (
    1.0  # Seconds before retrying a 429/5xx/network error; doubled per attempt.
)


@dataclass(frozen=True)
class Endpoint:
    """One resolved chat model; ``api_key`` is read from ``env_key`` and never stored."""

    model: str
    base_url: str
    env_key: str = ""
    api_key: str = field(default="", repr=False)

    def receipt(self) -> dict:
        """Public description without the key value."""
        return {"model": self.model, "base_url": self.base_url, "env_key": self.env_key}


def config_path() -> Path:
    """The shared vexy-subs config file in the platform config directory."""
    return user_config_path("vexy-subs", appauthor=False) / "config.toml"


def read_config(path: str | Path = "") -> dict:
    """Parse the TOML config; a missing default file is an empty config."""
    target = Path(path).expanduser() if path else config_path()
    if path and not target.is_file():
        raise FileNotFoundError(target)
    return tomllib.loads(target.read_text()) if target.exists() else {}


def load_env(env_file: str = "", config_file: str | Path = "") -> None:
    """Load ``env_file`` (or a discovered working-directory ``.env``) and the
    ``.env`` beside the config file, never overriding variables already set."""
    if env_file and not Path(env_file).is_file():
        raise FileNotFoundError(env_file)
    folder = (Path(config_file).expanduser() if config_file else config_path()).parent
    for env in (env_file or find_dotenv(usecwd=True), str(folder / ".env")):
        if env:
            load_dotenv(env, override=False)


def spec_text(spec: object) -> str:
    """Normalise a CLI spec: Fire turns ``a,b`` into a tuple and ``1.5`` into a float.

    Profile names that look like numbers or booleans (``1e3``, ``true``) cannot be
    recovered from Fire's conversion; name profiles with letters.
    """
    if isinstance(spec, (list, tuple)):
        return ",".join(str(s) for s in spec)
    return "" if spec is None else str(spec)


def discover_providers(environ: Mapping[str, str] | None = None) -> dict[str, dict]:
    """Providers implied by ``{PREFIX}_API_KEY`` plus an endpoint variable."""
    env = os.environ if environ is None else environ
    found = {}
    for key in sorted(env):
        match = _KEY_RE.match(key)
        if not match:
            continue
        prefix = match.group(1)
        url = env.get(f"{prefix}_API_ENDPOINT") or env.get(f"{prefix}_API_OPENAI")
        if url and url.startswith(("http://", "https://")):
            name = prefix.lower()
            found[name] = {
                "name": name,
                "base_url": url.rstrip("/"),
                "env_key": key,
                "wire_api": "chat",
            }
    return found


def providers(data: dict, environ: Mapping[str, str] | None = None) -> dict[str, dict]:
    """Configured providers override discovered ones of the same name."""
    return {**discover_providers(environ), **data.get("model_providers", {})}


def _endpoint(
    model: str, base_url: str, env_key: str, environ: Mapping[str, str]
) -> Endpoint:
    if not model or not base_url.startswith(("http://", "https://")):
        raise ValueError(
            f"LLM needs a model and an HTTP(S) base_url, got {model!r} at {base_url!r}"
        )
    return Endpoint(
        model,
        base_url.rstrip("/"),
        env_key,
        environ.get(env_key, "") if env_key else "",
    )


def resolve(
    spec: str, data: dict | None = None, environ: Mapping[str, str] | None = None
) -> Endpoint:
    """Resolve one profile name or ``model::ENV_KEY::base_url`` spec."""
    env = os.environ if environ is None else environ
    spec = spec.strip()
    if "::" in spec:
        parts = spec.split("::")
        if len(parts) != 3:
            raise ValueError(
                f"Explicit spec must be 'model::ENV_KEY::base_url', got {spec!r}; "
                "e.g. 'gpt-4o::OPENAI_API_KEY::https://api.openai.com/v1'"
            )
        return _endpoint(parts[0], parts[2], parts[1], env)
    data = read_config() if data is None else data
    profile = data.get("profiles", {}).get(spec)
    if profile is None:
        raise ValueError(
            f"Unknown LLM profile {spec!r}; add [profiles.{spec}] or use 'model::ENV_KEY::base_url'"
        )
    provider = providers(data, env).get(profile.get("model_provider", ""))
    if provider is None:
        raise ValueError(
            f"Provider {profile.get('model_provider')!r} of profile {spec!r} is not configured"
        )
    return _endpoint(
        profile.get("model", ""),
        provider.get("base_url", ""),
        provider.get("env_key", ""),
        env,
    )


def resolve_all(
    specs: str | Sequence[str],
    data: dict | None = None,
    environ: Mapping[str, str] | None = None,
) -> list[Endpoint]:
    """Resolve a comma-separated fallback list, in order.

    The config file is read only when a spec names a profile.
    """
    names = [s.strip() for s in spec_text(specs).split(",") if s.strip()]
    if not names:
        raise ValueError(
            "Require an LLM spec: a profile name or 'model::ENV_KEY::base_url'"
        )
    if data is None and not all("::" in n for n in names):
        data = read_config()
    return [resolve(name, data or {}, environ) for name in names]


def reply_text(content: object) -> str:
    """Message text without code fences or a leading ``<think>`` block."""
    if not isinstance(content, str):
        raise ValueError(f"LLM returned no text content ({type(content).__name__})")  # noqa: TRY004  (bad reply, retried)
    content = _THINK.sub("", content).strip()
    if content.startswith("```"):
        content = "\n".join(content.splitlines()[1:-1]).strip()
    return content


def parse_json(text: str) -> object:
    """Parse a JSON reply, tolerating prose around a single top-level object."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start < 0 or end <= start:
            raise
        return json.loads(text[start : end + 1])


def chat(endpoint: Endpoint, system: str, user: str, timeout: float = 60) -> str:
    """One deterministic chat completion; returns the cleaned message text."""
    headers = (
        {"Authorization": f"Bearer {endpoint.api_key}"} if endpoint.api_key else {}
    )
    with httpx.Client(timeout=timeout, headers=headers) as client:
        response = client.post(
            endpoint.base_url + "/chat/completions",
            json={
                "model": endpoint.model,
                "temperature": 0,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
        )
        response.raise_for_status()
    return reply_text(response.json()["choices"][0]["message"].get("content"))


def _retryable(exc: Exception) -> bool:
    """Wrong credentials or a bad request will not improve on retry; rate limits may."""
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
        return code in (408, 429) or code >= 500
    return True


def ask_json[T](
    endpoints: list[Endpoint],
    system: str,
    payload: object,
    check: Callable[[object], T],
    timeout: float = 60,
    attempts: int = 2,
) -> T:
    """Send JSON, parse the JSON reply and validate it with ``check``.

    Each endpoint gets ``attempts`` tries. A rejected reply is retried with the
    reason appended; 429/5xx/network errors wait and retry; other 4xx errors skip
    to the next endpoint. The last error is raised.
    """
    request = json.dumps(payload, ensure_ascii=False)
    error: Exception = ValueError("No LLM endpoints")
    for endpoint in endpoints:
        user = request
        for attempt in range(1, attempts + 1):
            try:
                return check(parse_json(chat(endpoint, system, user, timeout)))
            except (
                ValueError,
                KeyError,
                TypeError,
                IndexError,
                httpx.HTTPError,
            ) as exc:
                error = exc
                logger.warning("{} attempt {} failed: {}", endpoint.model, attempt, exc)
                if not _retryable(exc):
                    break
                if attempt == attempts:
                    break
                if isinstance(exc, httpx.HTTPError):
                    time.sleep(RETRY_DELAY * attempt * (1 + random.random() / 2))
                else:
                    user = (
                        f"{request}\n\nYour previous reply was rejected: {exc}. "
                        "Answer again in exactly the required JSON format."
                    )
    raise error


def append_providers(found: dict[str, dict], path: str | Path = "") -> list[str]:
    """Append new ``[model_providers.*]`` tables, keeping existing text and comments."""
    target = Path(path).expanduser() if path else config_path()
    existing = read_config(target) if target.exists() else {}
    known = existing.get("model_providers", {})
    added = [name for name in found if name not in known and _SECTION_NAME.match(name)]
    if not added:
        return []
    blocks = []
    for name in added:
        provider = found[name]
        lines = [f"[model_providers.{name}]"]
        lines += [
            f"{key} = {json.dumps(str(provider[key]))}"
            for key in ("name", "base_url", "env_key", "wire_api")
        ]
        blocks.append("\n".join(lines))
    text = target.read_text() if target.exists() else ""
    separator = (
        ""
        if not text or text.endswith("\n\n")
        else ("\n" if text.endswith("\n") else "\n\n")
    )
    merged = text + separator + "\n\n".join(blocks) + "\n"
    tomllib.loads(merged)  # Refuse to write a merge that would not parse.
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", dir=target.parent, delete=False, suffix=".tmp", encoding="utf-8"
    ) as handle:
        handle.write(merged)
    os.replace(handle.name, target)
    return added
