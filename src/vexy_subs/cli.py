# this_file: src/vexy_subs/cli.py
"""Fire CLI; JSON results on stdout and progress on stderr."""

import html
import importlib.util
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

from . import __version__
from . import llm as llm_module
from .formats import verify
from .io import sha256
from .pipeline import run
from .postprocess import run as beautify_run
from .translate import run as translate_run


class LLM:
    """OpenAI-compatible providers and profiles shared by translate and beautify."""

    def path(self) -> str:
        """Print the config file that holds [model_providers.*] and [profiles.*]."""
        return str(llm_module.config_path())

    def profiles(self, config_file: str = "", env_file: str = "") -> dict:
        """List profiles and providers (configured plus discovered); never key values."""
        llm_module.load_env(env_file, config_file)
        data = llm_module.read_config(config_file)
        found = llm_module.providers(data)
        return {
            "config": config_file or str(llm_module.config_path()),
            "profiles": {
                name: {
                    "model": p.get("model", ""),
                    "provider": p.get("model_provider", ""),
                    "provider_found": p.get("model_provider", "") in found,
                }
                for name, p in data.get("profiles", {}).items()
            },
            "providers": {
                name: {
                    "base_url": p.get("base_url", ""),
                    "env_key": p.get("env_key", ""),
                    "key_set": bool(os.environ.get(p.get("env_key", ""))),
                }
                for name, p in found.items()
            },
        }

    def discover(
        self, save: bool = False, config_file: str = "", env_file: str = ""
    ) -> dict:
        """Find {PREFIX}_API_KEY + {PREFIX}_API_ENDPOINT pairs; --save appends them to config."""
        llm_module.load_env(env_file, config_file)
        found = llm_module.discover_providers()
        added = llm_module.append_providers(found, config_file) if save else []
        return {
            "discovered": {
                n: {"base_url": p["base_url"], "env_key": p["env_key"]}
                for n, p in found.items()
            },
            "saved": added,
        }

    def check(self, spec: str, config_file: str = "", env_file: str = "") -> list:
        """Resolve an LLM spec (profile, model::ENV_KEY::base_url, or a,b) without calling it."""
        llm_module.load_env(env_file, config_file)
        return [
            {**e.receipt(), "key_set": bool(e.api_key)}
            for e in llm_module.resolve_all(spec, llm_module.read_config(config_file))
        ]


class CLI:
    """Local coloured subtitles, private prompt files and independent verification."""

    transcribe = staticmethod(run)
    beautify = staticmethod(beautify_run)
    translate = staticmethod(translate_run)
    llm = LLM()

    def version(self) -> str:
        """Print the installed package version."""
        return __version__

    def doctor(self) -> dict:
        """Report local prerequisites; no API keys or cloud authentication are required."""
        return {
            "version": __version__,
            "auth_required": False,
            "platform": platform.system(),
            "architecture": platform.machine(),
            "ffmpeg": bool(shutil.which("ffmpeg")),
            "ffprobe": bool(shutil.which("ffprobe")),
            "inference_installed": all(
                importlib.util.find_spec(p) is not None
                for p in ("mlx_whisper", "mlx_audio", "deepmultilingualpunctuation")
            ),
            "cluster_installed": importlib.util.find_spec("diarize") is not None,
        }

    def render(
        self,
        words_file: str,
        output_stem: str,
        speaker_map: str = "",
        force: bool = False,
        beautify: bool = True,
        language: str = "",
        fps: float = 25,
        backend: str = "",
        config_file: str = "",
        env_file: str = "",
        llm: str = "",
    ) -> dict:
        """Render edited timed words offline, without loading inference models."""
        from .cues import segment
        from .formats import write
        from .types import Word

        source = Path(words_file)
        words = [Word(**w) for w in json.loads(source.read_text())["words"]]
        stem = Path(output_stem)
        if not force and any(
            Path(str(stem) + ext).exists() for ext in (".srt", ".vtt", ".ass")
        ):
            raise FileExistsError(
                "Existing captions; use --force to render edited words"
            )
        stem.parent.mkdir(parents=True, exist_ok=True)
        names = json.loads(Path(speaker_map).read_text()) if speaker_map else {}
        if beautify:
            from .beautify import beautify as beautify_words
            from .beautify_config import load_config

            duration = max((w.end for w in words), default=0) + 0.5
            _, cues, info = beautify_words(
                words,
                duration,
                language,
                fps,
                load_config(config_file, env_file, backend, llm),
            )
        else:
            cues, info = segment(words), {"disabled": True}
            duration = max((w.end for w in words), default=0)
        palette = write(cues, stem, names)
        return {
            "speaker_palette": palette,
            "beautification": info,
            **verify(stem, duration),
        }

    def batch(
        self,
        folder: str = ".",
        output_dir: str = "",
        prompt_dir: str = "",
        pattern: str = "*.mp4",
        force: bool = False,
        language: str = "en",
        diar_backend: str = "auto",
        max_speakers: int = 40,
        beautify: bool = True,
        beautify_backend: str = "",
        config_file: str = "",
        env_file: str = "",
        llm: str = "",
        strict: bool = False,
        beautify_language: str = "",
        fps: float = 0,
    ) -> dict:
        """Process videos sequentially; require every per-video hint when prompt_dir is given."""
        videos = sorted(Path(folder).resolve().glob(pattern))
        if not videos:
            raise ValueError("No matching videos")
        prompts = {}
        if prompt_dir:
            for video in videos:
                matches = [
                    Path(prompt_dir) / (video.stem + ext) for ext in (".md", ".txt")
                ]
                matches = [p for p in matches if p.is_file()]
                if len(matches) != 1:
                    raise ValueError(f"Require exactly one prompt for {video.name}")
                prompts[video] = matches[0].resolve()
        failed = []
        for index, video in enumerate(videos, 1):
            print(f"[{index}/{len(videos)}] {video.name}", file=sys.stderr, flush=True)
            command = [
                sys.executable,
                "-m",
                "vexy_subs.cli",
                "transcribe",
                str(video),
                f"--output_dir={output_dir}",
                f"--force={force}",
                f"--language={language}",
                f"--beautify={beautify}",
                f"--beautify_backend={beautify_backend}",
                f"--config_file={config_file}",
                f"--env_file={env_file}",
                f"--llm={llm_module.spec_text(llm)}",
                f"--strict={strict}",
                f"--beautify_language={beautify_language}",
                f"--fps={fps}",
            ]
            if diar_backend != "auto":
                command.extend(
                    [f"--diar_backend={diar_backend}", f"--max_speakers={max_speakers}"]
                )
            if video in prompts:
                command.append(f"--prompt_file={prompts[video]}")
            try:
                subprocess.run(command, check=True, timeout=14400)
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                failed.append(video.name)
        if failed:
            raise RuntimeError(json.dumps({"failed": failed}))
        return {"processed": len(videos), "failures": []}

    def verify(
        self,
        folder: str = ".",
        source_dir: str = "",
        pattern: str = "*.mp4",
        strict: bool = False,
    ) -> dict:
        """Check receipt hashes and speaker styling for every generated artifact set."""
        reports = []
        expected = (
            {p.name: p for p in Path(source_dir).glob(pattern)} if source_dir else {}
        )
        for path in sorted(Path(folder).glob("*.vexy-subs.json")):
            data = json.loads(path.read_text())
            if source_dir:
                source = expected.get(data["source_filename"])
                if not source or sha256(source) != data["settings"]["input_sha256"]:
                    raise ValueError("Source input hash or expected filename differs")
            stem = path.parent / path.name.removesuffix(".vexy-subs.json")
            for ext, digest in data["outputs"].items():
                if sha256(Path(str(stem) + ext)) != digest:
                    raise ValueError(f"Changed output: {stem.name}{ext}")
            reports.append(
                {"video": data["source_filename"], **verify(stem, data["duration"])}
            )
            import pysubs2

            words = json.loads(Path(str(stem) + ".words.json").read_text())["words"]
            spoken = " ".join(w["text"].replace("<unk>", "[unk]") for w in words)
            displayed = " ".join(s.plaintext for s in pysubs2.load(str(stem) + ".ass"))
            if re.sub(r"\s+", "", spoken) != re.sub(r"\s+", "", displayed):
                raise ValueError("Caption layout lost transcript characters")
            beauty = data.get("beautification", {})
            if "audit" in beauty:
                from .beautify import audit
                from .types import Cue

                events = pysubs2.load(str(stem) + ".srt", format_="srt")
                fresh = audit(
                    [
                        Cue(
                            e.start / 1000,
                            e.end / 1000,
                            html.unescape(e.plaintext),
                            "unassigned",
                        )
                        for e in events
                    ],
                    data["duration"],
                    beauty["audit"]["fps"],
                    beauty["language_detection"]["language"],
                )
                reports[-1]["numeric_violations"] = len(fresh["violations"])
                if strict and (
                    not fresh["numeric_rules_pass"] or beauty["audit"]["violations"]
                ):
                    raise ValueError(f"Unresolved subtitle constraints: {stem.name}")
        if not reports:
            raise ValueError("No completed subtitles found")
        if source_dir and set(expected) != {r["video"] for r in reports}:
            raise ValueError("Missing subtitles for expected source videos")
        return {"verified": len(reports), "videos": reports}


def main() -> None:
    import fire

    fire.Fire(
        CLI(), serialize=lambda value: json.dumps(value, ensure_ascii=False, indent=2)
    )


if __name__ == "__main__":
    main()
