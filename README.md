<!-- this_file: README.md -->
# vexy-subs

Generate local video subtitles with a consistent colour for each diarized voice,
sentence punctuation, and your own recognition vocabulary.

```bash
uv tool install 'vexy-subs[apple,cluster]'
# From a checkout before the first release:
uv tool install './[apple,cluster]'
vexy-subs doctor
vexy-subs transcribe clip.mp4 --prompt_file=hints.md --output_dir=subtitles
vexy-subs batch videos --prompt_dir=hints --output_dir=subtitles
vexy-subs beautify subtitles
vexy-subs verify subtitles --source_dir=videos
```

The base package installs without inference libraries. Install the `apple` extra
for local inference on Apple Silicon, plus FFmpeg and ffprobe on PATH. The first
run downloads open model weights. No API key or paid inference service is needed.
The base package can render manually edited timed words without model inference:
`vexy-subs render edited.words.json subtitles/edited`.

`--prompt_file` accepts a nonempty UTF-8 `.md` or `.txt` file. Free-form hints are
forwarded to Whisper's initial prompt. Optional `Names:` and `Terms:` lines also
preserve vocabulary casing during punctuation restoration:
When those lines are present, their concise vocabulary is used as the recognition
context instead of sending Markdown instructions or programme prose to Whisper.

```text
Terms: QuasarAPI, OpenType, Python.
This talk discusses font shaping. Preserve the terminology when it is spoken.
```

`--prompt` adds inline hints. `--language=en` is the default; pass an empty string
for recognition language detection. FullStop punctuation supports English,
German, French, Italian and Dutch; other languages need an appropriate
`--punctuation_model`. A hint is recognition context, not a guaranteed replacement
or instruction following mechanism. Whisper has a finite prompt context.

Outputs are `.srt`, `.vtt`, `.ass`, `.words.json` and `.vexy-subs.json`.
ASS stores named per-speaker colour styles. WebVTT stores voice spans, cue
classes and CSS `STYLE` rules. SRT uses `<font color>` tags; players may ignore
them. Use ASS for reliable desktop styling and WebVTT for browser playback.

The pipeline recognizes timed words, diarizes a continuous recording, attributes
words to speaker activity, restores punctuation one label per lexical word,
then detects language, removes disfluencies and lays out balanced captions.
Normal cues have at most two 42-character lines and seven seconds;
indivisible long words are retained rather than rewritten. Raw recognition and
speaker turns remain in the local `.work` directory for inspection and recovery.
Failed stages can resume without repeating successful model inference.
Collapsed word timestamps are checked against an audio aligner; reliable native
neighbour timings are preserved. Unresolved instantaneous words stay with
adjacent caption text, and uncertain speaker activity uses a neutral white colour.
Instantaneous-word speaker assignments are marked ambiguous and inherit the
nearest timed word's voice; they never merge two speaker IDs into one coloured cue.

Speaker labels are anonymous session-local IDs. Programme names cannot establish
voice identity. If you have verified who each speaker is, pass
`--speaker_map=labels.json` with a mapping such as `{"speaker_0": "Presenter"}`.
Nemotron tracks up to eight speakers; larger meetings require a different
diarization backend. Default `--diar_backend=auto` switches to CPU clustering
when all eight slots are filled; it fails with setup guidance if that extra is
missing. Install the `cluster` extra and use `--diar_backend=cluster`
for CPU WeSpeaker/spectral clustering with `--max_speakers=40` (default). This
estimates the actual count rather than assigning a fixed list of names.
An externally verified JSON turn file can be supplied with `--turns_file`; it
contains `turns` with `start`, `end`, `speaker` fields and a `capacity` value.
Colours remain distinct beyond eight voices. Automatic clustering can merge or
split voices, particularly in short or noisy turns. Overlapping speech is marked ambiguous in `.words.json`;
mono audio cannot reliably isolate simultaneously spoken words. Punctuation and
diarization are model predictions and still benefit from editorial review.

Batch processing isolates models in a subprocess per video. When `--prompt_dir`
is supplied, every video must have exactly one matching `<video-stem>.md` or
`.txt` before processing starts. Existing outputs are verified and skipped;
changed inputs/settings require `--force`. Failures are reported after attempting
the remaining inputs. Verification checks hashes, text, timelines, colour styles
and voice tags. JSON results go to stdout; progress goes to stderr.
`verify --source_dir=videos` also checks every expected input hash and rejects
missing video outputs; without it, verification audits the completed output sets.

Recordings, prompt files, personal names, models and run artifacts are user-owned
private data. They are excluded from the source/wheel allowlists. The package
contains synthetic test fixtures only and does not upload videos or prompts.

## Subtitle post-fix

Beautification runs by default in `transcribe`, `batch` and `render`. Disable it
with `--beautify=False` to retain the old verbatim rendering. Existing captions
can be improved without repeating ASR, diarization or punctuation inference:

```bash
vexy-subs beautify /path/to/videos --recursive --backend=local
vexy-subs beautify talk.words.json --language=en --fps=25
vexy-subs beautify captions.srt --output_dir=cleaned
vexy-subs beautify captions.ass --strict
```

`beautify` accepts a folder, SRT, WebVTT, ASS, `.words.json` or a completion
receipt; `--verbose` adds debug detail on stderr. It writes grouped SRT/VTT/ASS
with consistent text and speaker styles. Default replacement is in place;
original captions, timed words and receipts are saved once in
`<stem>.work/beautify-original/`. `--output_dir` writes elsewhere. Repeat runs
with unchanged settings verify hashes and skip; `--force` reprocesses the saved
original words, so edits never accumulate. Archive folders named `private`,
inference `.work` directories and environments are excluded from recursion.
For caption-only imports, proportional word timing is an estimate and is marked
as such in the receipt. Original word timing is always preferred when available.

The default local route uses langid's bundled 97-language Naive Bayes model;
no language-model service is needed. For English, NLTK's small averaged-perceptron
POS tagger protects article/adjective/noun groups, pronoun/verb groups, auxiliaries
and names. Its JSON weights download once into the platformdirs user cache.
Other languages use explicit grammatical boundary rules. Pillow measures the
actual font advances, preferring installed Arial. Dynamic programming chooses
cue boundaries and penalizes short cues and excessive reading speed strongly;
each two-line candidate also minimizes optical imbalance and avoids orphan lines.
These are grammatical predictions, not a guarantee of perfect editorial phrasing.

Language-specific hesitation tokens such as `uhm`, `err`, `ähm` and `euh` are
removed. Adjacent accidental restarts are collapsed within a speaker turn;
English discourse padding such as hedging `kind of`, `basically` and marked
`you know`/`I mean` is also removed. Literal expressions such as `a special kind
of font`, `works well` and `what you know` are protected. Sentence capitalization
and standalone-response punctuation are repaired before caption layout.
intentional emphasis, negation, valid `had had`/`that that`, names and numbers
are retained conservatively. Every deletion has its original text, times and reason
in the receipt; out-of-order instantaneous tokens get logged timing repairs.
Unicode normalization, curly apostrophes, smart ellipses and
language-specific quotation marks are applied across runs, not separately to
each display line. French typography uses nonbreaking punctuation spacing.
Use `--language` to override detection for a short or multilingual recording.

Timing uses the source frame rate when a neighboring video is present; standalone
captions/audio default to 25 fps, overridable with `--fps`. Starts snap within one
frame; endings can borrow up to 0.5 seconds of available space. Cues target a
minimum of 5/6 second, maximum seven seconds, a two-frame gap and either a
two-frame or at-least-half-second inter-cue gap. English adult subtitles target
20 visible characters/second; German, French and Polish target 17. Other
languages currently use a conservative, explicitly unverified 42/17 fallback.
Tags do not count toward visible lengths. Long indivisible tokens and dense
speaker changes can make these constraints impossible without changing meaning.
The receipt's `beautification.audit.violations` lists unresolved cues;
`--strict` refuses to replace a set unless its supported numeric rules pass.
Passing numeric checks does not certify Netflix delivery: shot changes, dialogue
sync, glyph coverage, regional editorial rules and full playback need review.
The existing speaker colours are retained; they are a project convention rather
than Netflix's white-text delivery style.

## Optional LLM and configuration

Configuration lives at `platformdirs.user_config_path("vexy-subs", appauthor=False)`
plus `config.toml`. On macOS this is
`~/Library/Application Support/vexy-subs/config.toml`; Linux uses the XDG config
directory and Windows the user's local application-data directory.

```toml
[beautify]
backend = "auto" # local, llm, or auto: llm only when a model is configured
# font = "/absolute/path/to/Arial.ttf"
[llm]
model = "your-loaded-model"
base_url = "http://localhost:1234/v1" # OpenAI-compatible chat completions
api_key_env = "VEXY_SUBS_LLM_API_KEY"
timeout = 60
```

Environment equivalents are `VEXY_SUBS_BEAUTIFY_BACKEND`, `VEXY_SUBS_LLM_MODEL`,
`VEXY_SUBS_LLM_BASE_URL`, `VEXY_SUBS_LLM_API_KEY`, `VEXY_SUBS_LLM_TIMEOUT` and
`VEXY_SUBS_FONT`. python-dotenv loads a discovered working-directory `.env`
and then `.env` beside the canonical TOML, without overriding existing variables.
Explicit CLI choices take precedence over environment, then TOML, then defaults.
Use `--env_file` / `--config_file` for explicit paths. The integrated commands use
`--beautify_backend` and `--beautify_language`; standalone `beautify` uses
`--backend` and `--language`. `batch` forwards backend/config/env/strict choices.

An LLM receives batches of subtitle tokens and anonymous speaker IDs. It may
remove unnecessary tokens and correct casing/punctuation; validation rejects
inserted/reordered tokens, lexical rewrites, deleted numbers/acronyms or deletion
of more than 30% of a batch. Timestamps and speaker IDs stay local and unchanged.
The LLM route does send caption text to the configured endpoint, including a
remote provider if you choose one. API keys never enter receipts or stdout.
Use `--backend=local` / `--beautify_backend=local` for fully local post-fix.

Rules are based on Netflix's [general requirements](https://partnerhelp.netflixstudios.com/hc/en-us/articles/215758617-Timed-Text-Style-Guide-General-Requirements),
[timing guidelines](https://partnerhelp.netflixstudios.com/hc/en-us/articles/360051554394-Timed-Text-Style-Guide-Subtitle-Timing-Guidelines),
[English](https://partnerhelp.netflixstudios.com/hc/en-us/articles/217350977-English-USA-Timed-Text-Style-Guide),
[German](https://partnerhelp.netflixstudios.com/hc/en-us/articles/217351587-German-Timed-Text-Style-Guide),
[French](https://partnerhelp.netflixstudios.com/hc/en-us/articles/217351577-French-France-Timed-Text-Style-Guide)
and [Polish](https://partnerhelp.netflixstudios.com/hc/en-us/articles/216787928-Polish-Timed-Text-Style-Guide)
style guides, consulted on 2026-10-12.

```bash
./test.sh
./build.sh      # tests, uv build, twine check
./publish.sh    # tag, build, uv publish to PyPI
```

Versions come from git tags through hatch-vcs: tag releases with
`uvx gitnextver`. Untagged commits build as development versions with a local
segment, which PyPI rejects. The generated `src/vexy_subs/__version__.py` is ignored by git.

`./publish.sh` runs the tests, then `uvx gitnextver`, which commits all
changes, creates the next `vX.Y.Z` tag (`v1.0.0` when none exists) and pushes.
It then builds and runs `uv publish`. A rerun on a clean, already tagged HEAD
skips gitnextver.

Implementation sources: [MLX Whisper](https://github.com/ml-explore/mlx-examples/tree/main/whisper),
[Nemotron diarization](https://github.com/Blaizzy/mlx-audio/tree/main/mlx_audio/vad/models/nemotron_diarization),
[FullStop punctuation](https://github.com/oliverguhr/deepmultilingualpunctuation),
[CPU diarization](https://github.com/notch-up/diarize),
[WebVTT](https://developer.mozilla.org/en-US/docs/Web/API/WebVTT_API).
