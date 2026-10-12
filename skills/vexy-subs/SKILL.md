---
name: vexy-subs
description: Generate and verify local speaker-coloured video subtitles using private recognition hints.
---
<!-- this_file: skills/vexy-subs/SKILL.md -->

# vexy-subs

Check `command -v vexy-subs`, then run `vexy-subs doctor`. Local inference requires
the Apple extra plus FFmpeg/ffprobe; no API keys are required. Keep recordings,
per-talk prompt files and generated artifacts outside the public source tree.

Use a UTF-8 `.md` or `.txt` prompt file for names and terms. Optional `Names:` and
`Terms:` lines provide concise recognition vocabulary and phrase casing.
Speaker IDs are anonymous; only use a speaker map after verifying the identities.

```bash
vexy-subs transcribe clip.mp4 --prompt_file=hints.md --output_dir=subtitles
vexy-subs batch videos --prompt_dir=hints --output_dir=subtitles
vexy-subs beautify subtitles --recursive --backend=local
vexy-subs verify subtitles
```

Inspect actual caption text and rendered speaker changes as well as parser checks.
ASS is the reliable desktop colour format; WebVTT styles browser captions; SRT
colour tags depend on the player. Never upload private prompts or recordings,
or publish the package, without explicit authorization.

Beautification is enabled during transcription and offline rendering. Existing
sets can be post-fixed without redoing model inference; originals are retained in
`<stem>.work/beautify-original`. Inspect `beautification.audit.violations` and use
`--strict` to reject unresolved quantitative constraints. Configuration follows
the README's platformdirs TOML and dotenv/env contract. The local route keeps
caption text on the machine; only an explicitly configured LLM endpoint receives
caption tokens. Do not call numerical checks a Netflix editorial certification.
