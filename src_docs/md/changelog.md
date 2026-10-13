# Changelog

## 1.0.1

- Added `translate`, ported from the retired vttrix package: two-pass
  (translate, refine) LLM subtitle translation for SRT, VTT, ASS and SSA, with a
  JSON glossary and the previous chunk as context. Timing and ASS speaker styles
  are kept, and the output format follows the destination extension. Cues travel
  as numbered JSON; a dropped, merged or reordered cue is retried and then fails,
  instead of shifting timestamps.
- Added Codex-style `[model_providers.*]` and `[profiles.*]` configuration,
  provider discovery from `{PREFIX}_API_KEY` with `{PREFIX}_API_ENDPOINT` or
  `_API_OPENAI`, `model::ENV_KEY::base_url` specs, comma-separated fallback
  lists, and the `llm` command group (`path`, `profiles`, `discover --save`,
  `check`).
- Beautification can pick its LLM by spec: `--llm`, `VEXY_SUBS_LLM` or
  `[llm] profile`.
- Exported the vttrix library API: `Subtitle`, `SubtitleFile`,
  `load_subtitles`, `save_subtitles`, `translate_subtitles`,
  `translate_subtitles_sync`. A missing `--vocab` file is now an error.

## 1.0.0

- Added `build.sh` and `publish.sh`.
- Versions come from git tags through hatch-vcs. Added a `version` command.
- Remove unnecessary English discourse phrases such as hedging `kind of`, marked
  `you know`/`I mean`, and repeated phrase starts, while protecting literal uses,
  complete responses, names, numbers and meaningful emphasis.
- Normalise English sentence capitalisation and standalone response punctuation.
- Added automatic and standalone subtitle beautification with language detection.
- Added grammatical and measured-font line balancing, frame-aware retiming,
  filler and restart removal, and language-specific Unicode typography.
- Added optional validated LLM editing configured through dotenv, environment
  variables or TOML, keeping credentials out of receipts.
- Added original-caption backups, repeat-run hash checks and numeric caption-rule
  audits with strict refusal.

## 0.1.0

- Added speaker-coloured ASS, styled WebVTT and coloured SRT exports.
- Added continuous diarization and speaker-aware cue segmentation.
- Added punctuation restoration that preserves timed words.
- Added UTF-8 Markdown and text hint files passed to Whisper.
- Added the Fire command-line tool, resumable model stages and hash verification.

The full history is in
[CHANGELOG.md](https://github.com/vexyart/vexy-subs/blob/main/CHANGELOG.md).
