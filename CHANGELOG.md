<!-- this_file: CHANGELOG.md -->
# Changelog

## 1.0.3
- Remove immediate English phrase restarts when punctuation restoration puts a
  period after an unfinished article, preserving the completed phrase's timing,
  complete repeated sentences, questions, pauses and speaker handoffs.
- Advance the beautification policy to 8 so old editorial receipts are refreshed
  without repeating recognition, alignment, diarization or punctuation inference.
- Documented recognition-context limits, the timed editorial workflow, and the
  distinction between Whisper word estimates, Parakeet subword/sentence timing
  and Qwen audio-chunk bounds after a local multi-model comparison.
- Clarified that `--asr_model` selects compatible Whisper checkpoints and that
  spelling hints do not provide instruction-following editorial cleanup.

## 1.0.1
- Added `translate`, ported from the retired vttrix package: two-pass (translate,
  refine) LLM subtitle translation for SRT/VTT/ASS/SSA with a JSON glossary,
  previous-chunk context, timing and ASS speaker styles preserved, and the output
  format taken from the destination extension. Cues are exchanged as numbered
  JSON; dropped, merged or reordered cues are retried and then fail loudly
  instead of shifting timestamps (vttrix silently misaligned them).
- Added Codex-style `[model_providers.*]`/`[profiles.*]` config, provider
  discovery from `{PREFIX}_API_KEY` + `{PREFIX}_API_ENDPOINT`/`_API_OPENAI`,
  `model::ENV_KEY::base_url` specs and comma-separated fallback lists, plus the
  `llm` command group (`path`, `profiles`, `discover --save`, `check`).
- Beautification can pick its LLM by spec: `--llm`, `VEXY_SUBS_LLM` or
  `[llm] profile`.
- Exported the vttrix library API: `Subtitle`, `SubtitleFile`,
  `load_subtitles`, `save_subtitles`, `translate_subtitles`,
  `translate_subtitles_sync`. A missing `--vocab` file is now an error.
- Differences from vttrix: an existing output needs `--force`; input that
  holds text but no cues is an error; discovery only matches upper-case
  `{PREFIX}_API_KEY` names with an HTTP(S) endpoint; keys may also come from
  `--env_file` or `.env` files. A rejected reply is retried with the reason,
  then a failing chunk is halved down to single cues; 401/403 skip to the next
  model and 429/5xx back off. `<think>` blocks and prose around the JSON reply
  are tolerated. `{...}` in translated text is read as an ASS tag by pysubs2.

## 1.0.0
- Added `build.sh` (test, build, twine check) and `publish.sh` (test,
  gitnextver tag, build, `uv publish` with retry on rate limits).
- Versions now come from git tags through hatch-vcs, matching vexy-speakup;
  the generated `__version__.py` is ignored by git. Added a `version` command.
- Remove unnecessary English discourse phrases such as hedging `kind of`,
  marked `you know`/`I mean`, and repeated phrase starts while protecting literal
  uses, complete responses, names, numbers and meaningful emphasis.
- Normalize English sentence capitalization and standalone response punctuation;
  strengthen caption boundaries around articles, conjunctions and contractions.
- Added automatic and standalone subtitle beautification with language detection.
- Added grammatical and measured-font line balancing, frame-aware retiming,
  filler/restart removal and language-specific Unicode typography.
- Added optional validated LLM editing configured through dotenv/env or
  platformdirs TOML, keeping credentials out of output receipts.
- Added original-caption backups, repeat-run hash checks and explicit numeric
  subtitle-rule audits with strict refusal for unresolved constraints.

## 0.1.0
- Added speaker-coloured ASS, styled WebVTT and coloured SRT exports.
- Added continuous diarization and speaker-aware sentence/cue segmentation.
- Added model punctuation restoration that preserves timed lexical tokens.
- Added UTF-8 Markdown/text prompt files forwarded to Whisper recognition.
- Added an installable Fire CLI, recoverable inference stages and hash verification.
