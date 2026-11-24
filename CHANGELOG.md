<!-- this_file: CHANGELOG.md -->
# Changelog

## Unreleased

- Site now uses the fly-january 0.2.1 theme (chrome: none).
- Local releases hand off to GitHub Actions for PyPI Trusted Publishing. The PyPI project owner must keep the trusted publisher configured for repository `vexyart/vexy-subs`, workflow `release.yml`, environment `pypi`.

## 1.0.7

- PyPI published the wheel and source archive for tag `v1.0.7` (`179e269`). Both SHA-256 hashes match the GitHub release, and both PyPI attestations identify `release.yml` in the `pypi` environment.
- Verified the deployed documentation in November 2026. The home, installation and development pages returned HTTP 200, and the installation page states the Audioflexy 1.0.3 minimum.

## 1.0.6

- Ported speech and editorial model APIs to Audioflexy. The final provider suite passed 586 tests and its example (`645ee87`).
- Preserved shared word and turn types, legacy imports, backend routing and cache reuse. Consumer integration tests passed (`645ee87`).
- Checked the exact archives, strict docs and a clean base installation. Synthetic exports, offline commands and resume passed with the 149-test consumer suite (`645ee87`).
- Ran the installed CLI on PATH with real MLX inference, verified two cues in three formats and resumed in a separate process with a byte-identical receipt (`645ee87`).
- Completed independent integration review and rechecked offline NLTK cache reuse with downloads disabled (`645ee87`).
- Tagged v1.0.6, verified the GitHub release archive hashes and tested the stable 1.0.6/1.0.3 wheel pair outside the checkouts (`d44fba6`).
- Keep optional FullStop package-version changes confined to punctuation cache
  identity, preserving recognition/alignment/diarization stage reuse.
- Delegate speech, alignment, diarization, punctuation, language identification
  and POS tagging to Audioflexy >=1.0.3; preserve legacy imports and shared
  Word/Turn identity. Keep subtitle editing/rendering local and model imports lazy.
- Delegate inference extras to the provider, identify it in `doctor`/`models`,
  and support both native environment prefixes and installed workspace adapters.
- Fingerprint provider source/runtime changes in stage caches; keep language/POS
  identity confined to editorial receipts so presentation changes reuse ASR.
- Document published-package installation and optional local source/wheel installs.
- `batch` accepts a YouTube video or playlist URL or a `.txt` URL list; yt-dlp
  downloads video, info.json and uploader-supplied English captions only.
  Titles and cleaned descriptions become tagged hints that reach every Qwen chunk.
- `--reference_file` (and batch, from caption sidecars) gives each 30 s ASR chunk
  the overlapping human caption text for spelling.
- `visual` command and `batch --visual`: camera cuts and in-shot content changes,
  head/tail keyframes with timestamps, motion/face/palette heuristics,
  `<stem>.shots.json`, a Basecoat keyframe/subtitle page and `index.html`.
- New `video` and `youtube` extras; agent skills `vexy-subs-batch` and
  `vexy-subs-visual`.
- Fixed forced alignment rejecting whole recordings when the aligner extrapolated
  a chunk's final word past the 30-second chunk end; the end is now clamped, while
  starts outside the chunk (beyond one 80 ms step) and disorder are still rejected.
- Qwen chunks whose text is implausible for their length (more than 7 words/s:
  the model reciting a long prompt over a short or quiet tail), that hit the token
  cap, or that fail alignment are retried once without a prompt; if the retry
  also fails, that chunk alone is dropped and listed in `alignment.dropped_chunks`
  instead of failing the recording.
- YouTube URLs whose `<id>.mp4` and `.info.json` are already in the download
  folder are reused offline (YouTube may demand sign-in on repeat requests);
  single-video URLs skip the playlist lookup.
- Visual change detector v5: 6% changed area plus the 2 s hold check, so
  text-only slide changes on dark backgrounds register while gestures do not.
- Use Qwen3-ASR 1.7B MLX as the primary recognizer, with automatic Qwen audio.cpp
  selection when MLX is unavailable. Forward concise recognition vocabulary to
  every bounded MLX chunk; retain an explicit Whisper cross-check route.
- Attach acoustic Qwen forced alignment to recognised text, preserving punctuation,
  spelling and numbers; reject lexical changes or invalid timelines.
- Add direct native Qwen and continuous Nemotron adapters, configurable executable,
  GGUF paths and compute backend, native cache fingerprints and batch forwarding.
- Preserve Qwen punctuation by default; keep FullStop as an explicit alternative.
  Retain existing audited local/optional LLM editing and speaker-coloured exports.
- Exclude Voxtral, Granite and Kroko from recognition selections. Add `models`
  and backend diagnostics, native installation guidance and integration tests.

## 1.0.5 verification

- Checked video, playlist and URL-list input with uploader captions in `tests/test_youtube.py` (`99ca70b`).
- Verified title, description and timed reference forwarding for Qwen chunks in `tests/test_youtube.py` (`99ca70b`).
- Checked shot and in-shot changes, keyframes and visual analysis on 13 recordings totalling 11.2 hours (`99ca70b`).
- Added the scan page, batch index and agent skills. The visual and YouTube tests passed in the 144-test suite (`99ca70b`).

## 1.0.4 verification

- Exercised the default Qwen MLX route and verified automatic audio.cpp selection separately in a clean installation without MLX (`b0ceb8c`).
- Ran forced alignment and diarization through both real pipelines. Each emitted 40 matching cues across three formats (`b0ceb8c`).
- Checked rejected recognizers and documented supported model and installation choices, including native configuration (`b0ceb8c`).
- Passed 124 tests, the strict docs build and wheel/sdist checks. The installed native CLI also verified and resumed its real output (`b0ceb8c`).

## 1.0.3

- Created adjacent source-grounded metadata for all 26 private recordings (`94a9dd3`).
- Extracted the 180-second middle excerpt and completed fresh Whisper and Parakeet runs with and without prompts (`94a9dd3`).
- Compared recognition prompts, timing and editorial output, including three Qwen runs, and delivered the private report (`94a9dd3`).
- Applied the benchmark’s phrase-restart fix and verified the tagged release with 106 tests, a clean install and matching PyPI hashes (`d8464fe`, `94a9dd3`).
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

- Checked integrated and standalone language-aware beautification in the 36-test post-fix suite (WORK.md history).
- Verified dotenv, environment and platformdirs TOML configuration for the optional LLM route (WORK.md history).
- Verified grammatical and measured-font wrapping, frame rounding, strict rejection and first-run backups (WORK.md history).
- Processed all 26 active subtitle sets and recorded outstanding reading-speed and timing cases for editorial review (WORK.md history).
- Checked English discourse cleanup, casing and phrasing against 14,733 cues and 24 delivery mirrors. The 46-test suite passed (WORK.md history).

## 0.1.0
- Added speaker-coloured ASS, styled WebVTT and coloured SRT exports.
- Added continuous diarization and speaker-aware sentence/cue segmentation.
- Added model punctuation restoration that preserves timed lexical tokens.
- Added UTF-8 Markdown/text prompt files forwarded to Whisper recognition.
- Added an installable Fire CLI, recoverable inference stages and hash verification.

- Reviewed upstream inference and packaging guidance and cited the caption guidelines in the README (WORK.md history).
- Verified UTF-8 Markdown and plain-text prompt forwarding to Whisper with pipeline fixtures (WORK.md history).
- Checked continuous speaker attribution and sentence-aware cue boundaries across handoffs. The corpus audit found zero mixed-speaker cues (WORK.md history).
- Verified word-preserving model punctuation and matching text in speaker-coloured ASS, styled WebVTT and coloured SRT exports (WORK.md history).
- Inspected the two-speaker real-video pilot for rendered colour changes and punctuation across 254 cues (WORK.md history).
- Built and privacy-audited the wheel and sdist, ran Twine checks and installed the wheel in a clean environment (WORK.md history).
- Documented the Fire CLI, exercised real inference through the installed command and verified hashes and resume across 24 corpus outputs (WORK.md history).

## 2026-10-18: documentation plugins

- Use MaterialX search, inherited metadata and a topic index; keep ordered navigation in awesome-nav.
- The documentation wrapper installs the plugins required by this site.
- Strict documentation build and rendered output checks passed.
