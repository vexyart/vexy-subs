# this_file: src/vexy_subs/beautify_config.py
"""Small local-model/optional-LLM configuration with no secrets in receipts."""

import math
import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import find_dotenv, load_dotenv
from platformdirs import user_config_path


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
            "policy": 7,
            "backend": self.backend,
            "model": self.model,
            "base_url": self.base_url,
            "font": self.font,
        }


def load_config(config_file: str = "", env_file: str = "", backend: str = "") -> Config:
    """Resolve explicit flags > environment/.env > platformdirs TOML > defaults."""
    path = (
        Path(config_file).expanduser()
        if config_file
        else user_config_path("vexy-subs", appauthor=False) / "config.toml"
    )
    if config_file and not path.is_file():
        raise FileNotFoundError(path)
    if env_file and not Path(env_file).is_file():
        raise FileNotFoundError(env_file)
    for env in (env_file or find_dotenv(usecwd=True), str(path.parent / ".env")):
        if env:
            load_dotenv(env, override=False)
    data = tomllib.loads(path.read_text()) if path.exists() else {}
    llm, beauty = data.get("llm", {}), data.get("beautify", {})
    model = os.getenv("VEXY_SUBS_LLM_MODEL", llm.get("model", ""))
    selected = backend or os.getenv(
        "VEXY_SUBS_BEAUTIFY_BACKEND", beauty.get("backend", "auto")
    )
    if selected == "auto":
        selected = "llm" if model else "local"
    url = os.getenv(
        "VEXY_SUBS_LLM_BASE_URL", llm.get("base_url", "http://localhost:1234/v1")
    )
    timeout = float(os.getenv("VEXY_SUBS_LLM_TIMEOUT", llm.get("timeout", 60)))
    if selected not in {"local", "llm"} or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("Require backend local/llm/auto and positive finite timeout")
    if selected == "llm" and (not model or not url.startswith(("http://", "https://"))):
        raise ValueError("LLM backend requires model and HTTP(S) base_url")
    # Credentials stay in the environment or private .env; TOML can name a key variable.
    key = os.getenv(
        "VEXY_SUBS_LLM_API_KEY", os.getenv(llm.get("api_key_env", "OPENAI_API_KEY"), "")
    )
    font = os.getenv("VEXY_SUBS_FONT", beauty.get("font", ""))
    return Config(selected, model, url.rstrip("/"), key, timeout, font, path)
