<!-- this_file: PLAN.md -->
# Delivery plan

Status: complete. Public source includes package tests and distribution metadata;
private recordings, prompt inventories and generated evidence remain outside it.

1. Implement contextual prompt-file input, continuous speaker diarization,
   word-aligned punctuation restoration, and sentence/speaker-aware cue layout.
2. Export and independently verify speaker-coloured ASS, WebVTT and SRT.
3. Exercise complete real recordings outside this public source tree; inspect
   speaker changes and punctuation rather than claiming quality from parser checks.
4. Build wheel and source distribution, install the wheel in a clean environment,
   exercise CLI from another directory, and audit exact distribution contents.
5. Keep recordings, hint files, names, screenshots, logs, receipts and model caches
   outside this repository and distribution allowlist.

Subtitle post-fix delivery: implemented language detection, optional configured
LLM editing, language typography, grammatical/optical line layout, quantitative
timing checks, standalone processing and integration without invalidating ASR.
Applied the pass to the local corpus and retained originals and unresolved-review
records. Automatic numeric checks are separate from full editorial certification.

English editorial refinement delivered: context-sensitive discourse padding and
phrase-restart removal, sentence/response punctuation repair and stronger phrase
boundaries. Verified all active corpus sets and delivery mirrors directly.


## Issue 201 follow-up (complete)

Delivered adjacent metadata for the private recordings, the controlled middle
excerpt comparison, and a final private report. Integrated the observed
punctuated-article restart fix and documented ASR prompt/timing limits. Released
v1.0.3 from a clean tagged checkout; exact distributions passed content checks,
clean installation and remote PyPI hash verification. Final tests: 106 passed,
90.42% coverage, Ruff clean; strict documentation build passed.

## Qwen production integration (complete)

1. Default to Qwen3-ASR 1.7B MLX with vocabulary, Qwen audio.cpp on hosts without MLX.
2. Preserve recognised text through Qwen forced alignment; configure native models/binary without private paths.
3. Connect Nemotron diarization and cluster fallback, punctuation, audited editing and exports.
4. Remove rejected recognition families from package choices; preserve historical private evidence.
5. Verify failure/fallback/cache contracts, real MLX/native pipelines, docs and clean distributions.
