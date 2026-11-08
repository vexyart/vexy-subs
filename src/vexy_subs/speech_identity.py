# this_file: src/vexy_subs/speech_identity.py
"""Fingerprint the provider implementation rather than subtitle presentation."""

import hashlib
import importlib
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path


def implementation(*modules: str) -> dict:
    """Include actual provider bytes and installed model-runtime versions in caches."""
    digest = hashlib.sha256()
    for name in modules:
        module = importlib.import_module(f"vexy_audioflexy.speech.{name}")
        digest.update(name.encode())
        digest.update(Path(module.__file__).read_bytes())
    runtimes = {}
    packages = (
        "mlx",
        "mlx-audio",
        "mlx-whisper",
        "torch",
        "transformers",
        "diarize",
        "numpy",
        "soundfile",
    )
    if "punctuation" in modules:
        packages += ("deepmultilingualpunctuation",)
    if set(modules) <= {"language", "syntax"}:
        packages = ("langid", "nltk")
    for name in packages:
        try:
            runtimes[name] = version(name)
        except PackageNotFoundError:
            runtimes[name] = None
    return {
        "provider": "vexy-audioflexy",
        "sha256": digest.hexdigest(),
        "runtimes": runtimes,
    }
