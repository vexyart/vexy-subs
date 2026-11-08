<!-- this_file: WORK.md -->
# Work record

Rebuilt the original script as a src-layout package with a Fire entry point.
Optional Apple Silicon inference uses MLX Whisper (contextual initial prompt),
MLX Nemotron 3 (continuous arrival-order speaker cache), and FullStop multilingual
punctuation (one label per timed lexical word). Inference fixtures and real-video
evidence stay outside this public repository.

Initial independent tests: six passed for prompt files, lexical preservation,
speaker ambiguity, speaker-boundary cue splitting, colour/voice/format retention.
Expanded pipeline tests: nine passed, 82% coverage. The integration fixture uses
real FFmpeg decoding and synthetic inference, not a claimed real diarization test.

Real inference found Transformers 5 incompatibility in the older punctuation
wrapper. Reused its predictor with the documented current token-classification
pipeline, and bounded its input with overlapping windows. A short live example
restored declarative sentences and a question without lexical changes.
The first full-video attempt retained ASR/diarization stages but failed on a
version-specific punctuation method argument; corrected against installed source.
The retry reuses completed stages. Full-video quality and corpus completion remain
unproven until real output is inspected.

Completed a full real-video pilot: two speaker IDs with distinct ASS/WebVTT/SRT
colours, 254 sentence-aware cues, and no unassigned or ambiguous words. Inspected
actual rendered colour changes at the presenter and returning host; punctuation
includes declarative sentences, commas, and questions. Conservative sentence case
and whole-phrase hint casing avoid inappropriate mid-sentence capitalisation.

Exact wheel/sdist passed private-data and secret checks and Twine; a clean
base-only install works outside the checkout. Installed the Apple inference CLI
on PATH. Added offline rendering for user-edited timed words. The updated tests
currently pass with coverage above the 80% gate.

A many-speaker recording exhausted Nemotron's eight-speaker slots. Added an
optional CPU clustering backend and external-turn input; colours no longer cycle
after eight IDs. Full recording and short reference checks stay in the private
parent workspace. Full corpus completion still awaits the running batch and
speaker-limit remediation; distribution checks must repeat after final edits.

Full corpus inference completed. Independent caption-to-word audit exposed six
mixed-speaker cues caused by instantaneous tokens at handoffs. Corrected nearest
timed-word attribution with explicit ambiguity, carried those tokens into timed
context of the same voice, and added regression tests. Re-exported all caption
sets from unchanged inference with original model punctuation labels preserved;
no cue contains multiple speaker IDs. Final hash/source/text checks and resume
are running. Tests: 21 passed, 83% coverage; installed combined Apple/cluster extras
also passed an actual end-to-end inference smoke test outside the checkout.

Final corpus checks pass for every expected input: 24 complete styled artifact
sets, identical text across formats, source/output hashes, transcript retention,
and zero mixed-speaker cues. A fresh batch skipped every completed input.
No recordings, conference names, prompt files, screenshots or secrets are included
in either distribution. Original plain outputs remain archived privately.

## Subtitle post-fix, 2026-10-12

Added an integrated/default beautification stage and a standalone Fire command.
The local route uses bundled langid Naive Bayes language detection, a small NLTK
English POS model, conservative filler/restart removal, per-language Unicode
typography, measured proportional-font wrapping and dynamic cue segmentation.
The optional HTTPX LLM route accepts dotenv/environment/platformdirs TOML settings
and validates token IDs/lexical content before any output replacement.

Preserved inference cache keys, so changing beautification does not rerun ASR,
alignment, diarization or punctuation. Existing captions are staged and verified,
with immutable first-run backups and updated hash receipts. Strict mode checks
cached results as well as newly generated ones. Empty post-fix output is valid.
Repaired two existing out-of-order instantaneous-token cases without lexical
reordering; every timing adjustment/deletion is recorded.

Direct tests: 36 passed, 87.43% coverage; Ruff passed. Synthetic real-FFmpeg
integration, optional HTTP API contracts, invalid model edits, standalone imports,
backup/resume, strict rejection and frame rounding are covered. Applied the local
pass to 26 user-owned sets outside this source tree; all styled exports verify.
Production line counts, line lengths, maximum durations and two-frame gaps pass.
Unresolved reading speeds, brief turns and edit-boundary cases are recorded for
editorial review; this is not a claim of complete Netflix delivery conformance.
Actual before/after ASS renders were inspected with FFmpeg/libass. Private corpus
reports and screenshots remain in the parent private workspace.

## Stronger English editorial cleanup, 2026-10-12

Added context-sensitive discourse deletion, longer phrase-restart detection,
sentence capitalization and standalone-response punctuation. Literal kinds,
adverbial `well`, knowledge/complement clauses and intentional negation/emphasis
have regression coverage. Increased penalties for cue and line breaks after
articles, conjunctions and common contractions. Policy 7 invalidates older
beautification receipts without touching source inference.

Direct tests: 46 passed, 88.31% coverage; Ruff passed. Reprocessed 26 active
private corpus sets and their 24 delivery mirrors, preserving original backups.
Independent parser/text audit covers 14,733 cues with original lexical order,
unchanged retained speaker IDs and exact SRT delivery mirrors. Private reports
retain unresolved quantitative reading-speed/short-turn/timing cases.

## Issue 201 model benchmark, 2026-10-13

Created source-grounded metadata beside 26 private recordings (24 programme
recordings and two advanced recording variants); missing programme participants
and filename-derived identity are explicitly marked. Extracted a 180-second
middle excerpt of the requested recording into its delivery `.work` directory,
with provenance/hash receipt and private reproduction scripts.

Fresh prompted/unprompted Whisper turbo and Parakeet Ultra runs completed.
Existing vocabulary produced identical Whisper text on this excerpt; timings
contain 395 words and zero collapsed intervals. Parakeet retained more fillers
and misrecognized a technical panel name, so speed alone cannot select it.
Local timed editorial processing retained 380 words in 38 verified cues.
Qwen cached metadata initially lacked weights; downloaded the pinned checkpoint
and completed three comparisons. Its metadata prompt left output unchanged,
editorial instructions retained repetitions, and chunk bounds supplied no sentence
alignment. A complete punctuation/cleanup run exported 36 verified cues.
The final report is in the requested private work directory.

The benchmark exposed an article-fragment restart surviving model-added periods.
Added failing tests first, then extended existing phrase detection narrowly;
completed phrases retain their original timing. Complete sentences, questions,
pauses and speaker handoffs remain protected. Policy 8 refreshes editorial
receipts without invalidating inference caches. Public guidance now describes
initial-prompt limits, editorial stages and model timing contracts. Final direct cleanup and code/spec review passed. Released v1.0.3 from a clean
tagged checkout, preserving unrelated pre-existing worktree state. Exact wheel
and source archive passed Twine and privacy checks. Clean base-only install
verified version 1.0.3, the restart fix, retained timing and policy 8. Published
both artifacts to PyPI and GitHub; independent downloads from PyPI match local
SHA-256 hashes. Documentation and Pages workflows succeeded.

Final verification: 106 passed, 90.42% coverage, Ruff clean; strict documentation
build passed. Native word/chunk timing and qualitative editorial limits remain
explicit in the private final report and public guidance. Private evidence is in the
requested work directory; no recordings or names were added to public source.

Fresh baseline `./test.sh`: 96 passed, 90.41% coverage; Ruff clean.

## Qwen production integration — 2026-10-13

Baseline: 109 tests passed, 89.14% coverage, Ruff clean. Default remains Whisper; private workspace routing is preserved while direct Qwen MLX/native support is added. Authorised scope: primary Qwen ASR, native fallback, real forced alignment, existing best diarization and editorial stages; exclude Voxtral/Granite/Kroko from selectable recognition.

Delivered direct Qwen3-ASR 1.7B MLX (compatible community 8-bit conversion) and
Qwen audio.cpp adapters with actual forced alignment. Vocabulary reaches every
chunk. Native recognition uses independent bounded requests in one loaded session:
real testing found that upstream internal long-audio merging filters aligned words
while retaining them in punctuated text. The package rejects such loss; batching
avoids that merge. Native speaker IDs retain existing labels without double prefixes.
Default punctuation preserves Qwen output; explicit FullStop and audited editing
remain available. Added native model/binary fingerprints, automatic native Nemotron
when configured, cluster fallback, model listing, diagnostics and batch flags.
Rejected Voxtral/Granite/Kroko selection is tested, including workspace requests.

Fresh final tests: 124 passed, 90.18% coverage; Ruff clean. A clean base-only wheel
installation without MLX also passed 124 tests and actual automatic Qwen/native
Nemotron inference, caption verification and cache resume outside the checkout.
Real 180-second MLX and native pipelines both exported 40 matching SRT/VTT/ASS
cues, two anonymous voices plus an unassigned style. One word is unassigned;
four caption-rule violations and acoustic zero-duration words remain explicit
review findings. This is integration evidence, not a claim of perfect timing or
editorial conformance. No original corpus captions were overwritten.

Strict docs build and wheel/sdist Twine checks passed; exact distributions contain
both adapters and exclude private paths/media/weights. Updated the installed CLI
from the checked wheel, preserving apple/cluster extras; installed source hashes
match the worktree. Built development artifacts locally; no release/push was made.

## 2026-10-18: documentation plugins

- Use MaterialX search, inherited metadata and a topic index; keep ordered navigation in awesome-nav.
- The documentation wrapper installs the plugins required by this site.
- Strict documentation build and rendered output checks passed.

## 2026-10-25: visual scan pages and YouTube batches (task 101a)

- Transplanted ideas from reelpack-alpha (adaptive hist/ECR/pixel cut selector), framecheck (LK flow + RANSAC motion labels, faces, palette) and video-breakdown (shot enrichment) into `visual.py`; added in-shot content-change detection for slide talks.
- Real corpus: 13 David Berlow talks (11.2 h). Tuning on Ec65 (slide talk) and S28 (gesturing speaker): detector v5 gives 73 and 416 segments; v1 over-split gestures (1858), v4 under-split slides (44).
- Found Qwen reciting the long YouTube description over a 5 s final chunk (120 words); added the plausibility guard, bare-prompt retry and `dropped_chunks`.
- YouTube began demanding sign-in for repeat lookups; already-downloaded videos are now reused offline.
- Full suite: 144 passed, 89.8% coverage, ruff clean.


## Audioflexy consumer integration — 2026-11-08

Replaced model execution with `vexy_audioflexy.speech` APIs. Seven legacy engine
modules remain identity-preserving compatibility imports so existing callers and
monkeypatches reach the actual provider globals. Words and turns are provider
classes; subtitle cues, source hint/reference parsing, editorial rules and exports
remain local. All prior backend signatures, reference chunk bounds, lexical and
timing validation, Qwen retry/drop behavior, native fingerprints and error
propagation are retained. Both environment prefixes work; Audioflexy settings
have precedence. Workspace mode defaults to installed provider resources while
explicit legacy roots remain supported.

Model extras delegate to the provider; the portable minimum is >=1.0.3.dev0
because published 1.0.2 lacks these APIs. Checkout uv uses a relative sibling
source override. Doctor/models identify the provider and distinguish optional
FullStop availability from the actual ASR route. Provider speech implementation
bytes and installed runtime versions identify stage caches. Punctuation has its
own identity; language/POS bytes plus langid/NLTK versions affect only editorial
receipts. Regression checks prove punctuation/editorial changes reuse ASR.

Baseline: 144 tests passed, 89.81% subs coverage, Ruff clean. Final source suite:
148 passed, 91.68% subs coverage, Ruff clean. Existing regression tests remain;
one obsolete unconfigured-workspace expectation now checks installed resources.
New engine-boundary integration uses actual library recognition, alignment and
diarization functions with only engine load/generate fakes, forwarding vocabulary,
metadata and per-chunk references through exports, verification, resume and offline
render. This is routing/type/cache evidence, not acoustic accuracy evidence.
Audioflexy's separate final suite passed 585 tests and its example (controller).

Built both latest wheels and source archives; all four passed Twine and exact
archive privacy/portable-metadata checks. Fresh Python 3.12 base-only installation
outside both source trees passed the same actual-library synthetic integration,
resume, two-speaker SRT/VTT/ASS verification, CLI render, doctor, models and help.
MLX, Torch, Transformers, diarize and FullStop are absent in this base environment.
Strict documentation build passed. Private artifact paths, hashes and command
results are retained in the integration task report, outside distribution inputs.

Controller real source inference passed: two cues, one anonymous speaker, all
three formats verified; resume skipped inference. The local native audio.cpp
build rejects `nemotron_3_diar`; this existing runtime compatibility limit remains
an explicit error, not a successful native acceptance claim. Controller real installed CLI acceptance also passed outside both checkouts:
exact wheel pair with Apple/cluster extras installed on PATH, auto selected MLX,
two cues and one anonymous voice across ASS/VTT/SRT, CLI verify one set. A separate
CLI process resumed with verified SKIP in 1.826 s and a byte-identical receipt;
installed module paths and provider alias identity were checked. Durable evidence
is retained privately. Final independent combined review remains controller-owned.
No commit, push, publication or model-storage migration was performed.


Independent review found one cache-independence defect: the optional FullStop
package version was included in speech runtime identity. Restricted that package
to punctuation identity; shared speech runtimes remain. A version-only regression
failed before the fix and now passes, and engine-boundary integration proves
recognition/alignment/diarization stages remain reused. Focused provider suite:
5 passed in 2.23 s. Final full source suite: 149 passed in 24.49 s, 91.68% coverage,
Ruff clean. Refreshed consumer artifacts and installed synthetic acceptance are
recorded in the private task report. Final independent re-review remains pending.

## Final installed integration verification

The final exact consumer/provider wheels were installed on PATH with the existing
Apple and cluster extras. From outside both checkouts, every installed Python
file matched its wheel bytes. The real default MLX Qwen/forced-alignment/Nemotron
pipeline processed the synthetic short recording into two verified cues and one
anonymous voice in SRT, WebVTT and ASS. First run: 21.741 seconds; a separate CLI
resume: 0.950 seconds, verified SKIP and byte-identical receipt.

Final source evidence: 149 consumer tests, 91.68% coverage and Ruff; 585 provider
tests and its example. Exact wheel/sdist privacy, portable dependency metadata,
clean base-only installed synthetic engine-boundary/cache tests and strict docs
passed. Private exact artifacts and runtime receipts are retained outside public
distributions. Whole-scope independent review remains pending. Native Nemotron's
existing local binary compatibility limit remains; long-form quality is not
established by these short smoke checks. No publication was performed.

## Integration completion

Independent whole-goal review and the scoped correction review passed with no
material open findings. The final provider suite passes 586 tests and its example;
the unchanged consumer suite passes 149 tests with 91.68% coverage and Ruff clean.
The provider now searches existing subtitle NLTK caches before downloading. Real
installed NLTK succeeds with legacy-only weights and downloads forbidden, without
changing owner weights. Final installed Python bytes match the checked wheels.
An editorial-only provider update reused unchanged real recognition/alignment/
diarization caches; refreshed captions verify and a separate CLI resume skips
inference. Exact archives, clean base-installed synthetic integration and strict
docs passed. Recovery evidence and exact wheels are retained privately.

This completes the local integration. The required API remains an unpublished
development build; installation uses the documented local wheel pair. The local
native Nemotron binary remains incompatible with that model family. Short real
MLX smoke checks establish integration, not universal long-form model quality.
No commit, push, publication or model-storage migration was performed.

## 1.0.6 release preparation

Prepared stable Audioflexy >=1.0.3 requirements and published-package installation
guidance, retaining relative checkout overrides and local source/wheel options.
Earlier unpublished-build statements above describe the completed local phase.
Publication and installed registry artifact verification are pending.

Release-preparation checks: `uv lock` succeeded; `./test.sh` passed 149 tests
with 91.68% coverage and Ruff clean. Strict ProperDocs build passed into
`/tmp/vexy-subs-release-docs-20261108`. No executable feature changes were made
in this preparation pass. Registry publication remains pending.
