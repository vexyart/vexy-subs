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

## Visual scan pages and YouTube batches (task 101a)

Source analysis (four local reference projects, read in full where relevant):

- reelpack-alpha (Swift app + Python core): TransNetV2 with a recorded fallback to
  an adaptive OpenCV selector (HSV histogram χ², edge-change ratio, pixel change,
  local mean+3σ threshold, talking-head guard), exclusive shot ends, evidence
  frames and contact boards. Transplanted: the adaptive selector and its guard,
  exclusive-end sampling, full-resolution `-ss` frame extraction.
- framecheck (Python CLI/GUI): FFmpeg raw-pipe decoding, HSV cut score with a
  minimum shot length, sparse optical flow + RANSAC similarity for 2D motion
  labels, keyframe per shot, offline report. Transplanted: raw-pipe decoding,
  minimum shot length, motion estimate and label summary, honest limitations.
- video-breakdown (Python): TransNetV2/PySceneDetect, transition classification,
  K-means colour fingerprint, yt-dlp input, Claude-vision prompts. Transplanted:
  K-means palette and the yt-dlp source idea. Rejected: cloud vision, pose models.
- shotgun (C++ PySceneDetect port, TransNetV2 ONNX weights). Not transplanted:
  a compiled dependency and 90 MB weights for camera cuts that conference
  recordings rarely have; documented as a possible optional backend.

Plan and outcome:

1. `youtube.py`: expand URL/playlist/list, download with yt-dlp, keep only
   uploader English captions, derive tagged Title/Description hints. Done.
2. `qwen.context`: always forward tagged metadata; per-chunk human caption
   excerpt via `--reference_file` (MLX and audio.cpp). Done; receipt gains the
   reference digest only when used, so existing caches stay valid.
3. `visual.py`: one decode pass for cuts, 0.5 s motion samples and thumbnails;
   in-shot content changes (slides) with onset/settle refinement; head/tail
   keyframes with a changed-area similarity rule. Done.
4. `page.py`: Basecoat CDN page, keyframes left, cues right, filter, deep links;
   batch index page. Done.
5. `batch` folder/URL/list sources and `--visual`; `visual` command; skills
   `vexy-subs-batch` and `vexy-subs-visual`; tests without network. Done.
6. Fixed a pre-existing forced-alignment bound: the aligner extrapolates a
   chunk's final word up to ~0.4 s past the 30 s chunk; the end is clamped
   instead of failing the recording. Done with regression test.

## Qwen production integration (complete)

1. Default to Qwen3-ASR 1.7B MLX with vocabulary, Qwen audio.cpp on hosts without MLX.
2. Preserve recognised text through Qwen forced alignment; configure native models/binary without private paths.
3. Connect Nemotron diarization and cluster fallback, punctuation, audited editing and exports.
4. Remove rejected recognition families from package choices; preserve historical private evidence.
5. Verify failure/fallback/cache contracts, real MLX/native pipelines, docs and clean distributions.

## Audioflexy integration

See `docs/plans/audioflexy-integration.md`.

Reusable APIs and consumer source integration are implemented. Source regression
suite: 149 passed, 91.68% coverage, Ruff clean. Both exact wheels/source archives
and strict docs build pass; clean base-only installed synthetic inference/export,
resume and offline CLI checks pass. Controller real source smoke also passes.
Controller installed real-model/PATH verification passed, including separate-process
resume with an unchanged receipt. Independent combined review and the scoped offline-cache correction
review passed. Existing native Nemotron runtime rejection remains
explicit; no publication is included.

## 1.0.6 publication

Stable dependency requirements and published-package installation guidance are
ready. Publish Audioflexy 1.0.3 first, then vexy-subs 1.0.6; verify registry
artifacts, installed commands and deployed documentation before marking done.
