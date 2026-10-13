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
