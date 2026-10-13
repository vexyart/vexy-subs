# this_file: src/vexy_subs/beautify_config.py
"""Small local-model/optional-LLM configuration with no secrets in receipts."""

import math
import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from platformdirs import user_config_path

from .llm import load_env, resolve_all, spec_text


@dataclass(frozen=True)
class Config:
    backend: str
    model: str
    base_url: str
    api_key: str = field(repr=False)
    timeout: float
    font: str
    config_path: Path

    def receipt(self) -> dict:
        """Public settings only: never persist environment values or API keys."""
        return {
            "policy": 8,
            "backend": self.backend,
            "model": self.model,
            "base_url": self.base_url,
            "font": self.font,
        }


def load_config(
    config_file: str = "", env_file: str = "", backend: str = "", llm_spec: str = ""
) -> Config:
    """Resolve explicit flags > environment/.env > platformdirs TOML > defaults.

    An LLM spec (``llm_spec``, ``VEXY_SUBS_LLM`` or ``[llm] profile``) names a
    ``[profiles.*]`` entry or ``model::ENV_KEY::base_url`` and supplies the model,
    endpoint and key, replacing the separate ``[llm]`` model/base_url/key settings.
    ``VEXY_SUBS_LLM_MODEL``/``_BASE_URL`` still beat a TOML profile; the local
    backend never resolves a spec.
    """
    path = (
        Path(config_file).expanduser()
        if config_file
        else user_config_path("vexy-subs", appauthor=False) / "config.toml"
    )
    if config_file and not path.is_file():
        raise FileNotFoundError(path)
    load_env(env_file, path)
    data = tomllib.loads(path.read_text()) if path.exists() else {}
    llm, beauty = data.get("llm", {}), data.get("beautify", {})
    model = os.getenv("VEXY_SUBS_LLM_MODEL", llm.get("model", ""))
    url = os.getenv(
        "VEXY_SUBS_LLM_BASE_URL", llm.get("base_url", "http://localhost:1234/v1")
    )
    # Credentials stay in the environment or private .env; TOML can name a key variable.
    key = os.getenv(
        "VEXY_SUBS_LLM_API_KEY", os.getenv(llm.get("api_key_env", "OPENAI_API_KEY"), "")
    )
    selected = backend or os.getenv(
        "VEXY_SUBS_BEAUTIFY_BACKEND", beauty.get("backend", "auto")
    )
    # Flag > VEXY_SUBS_LLM > VEXY_SUBS_LLM_MODEL/BASE_URL > [llm] profile > [llm] model.
    spec = spec_text(llm_spec) or os.getenv("VEXY_SUBS_LLM", "")
    if not spec and not any(
        os.getenv(v) for v in ("VEXY_SUBS_LLM_MODEL", "VEXY_SUBS_LLM_BASE_URL")
    ):
        spec = llm.get("profile", "")
    if spec and selected != "local":
        first = spec_text(spec).split(",")[0]  # Beautify uses the first of a list.
        endpoint = resolve_all(first, data)[0]
        model, url, key = endpoint.model, endpoint.base_url, endpoint.api_key
    if selected == "auto":
        selected = "llm" if model else "local"
    timeout = float(os.getenv("VEXY_SUBS_LLM_TIMEOUT", llm.get("timeout", 60)))
    if selected not in {"local", "llm"} or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("Require backend local/llm/auto and positive finite timeout")
    if selected == "llm" and (not model or not url.startswith(("http://", "https://"))):
        raise ValueError("LLM backend requires model and HTTP(S) base_url")
    font = os.getenv("VEXY_SUBS_FONT", beauty.get("font", ""))
    return Config(selected, model, url.rstrip("/"), key, timeout, font, path)
