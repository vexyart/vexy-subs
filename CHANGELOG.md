<!-- this_file: CHANGELOG.md -->
# Changelog

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
