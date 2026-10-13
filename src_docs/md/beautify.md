# Beautification

Beautification turns timed words into captions that are easier to read. It runs
by default in `transcribe`, `batch` and `render`. Add `--beautify=False` to get
the plain, verbatim layout instead.

The `beautify` command applies the same clean-up to subtitles you already have,
without repeating recognition, diarization or punctuation.

## What it changes

1. **Language.** langid's bundled 97-language model detects the language from a
   sample across the whole recording. `--language` (or `--beautify_language` in
   the integrated commands) overrides it, which helps for short or mixed-language
   recordings.
2. **Disfluencies.** Hesitation tokens such as `uhm`, `err`, `ähm` and `euh` are
   removed. Accidental restarts next to each other within one speaker turn are
   collapsed. English padding such as hedging `kind of`, `basically`, and marked
   `you know` or `I mean` is removed. Literal uses such as `a special kind of
   font`, `works well` and `what you know` are kept, as are deliberate emphasis,
   negation, valid repeats such as `had had` or `that that`, names and numbers.
3. **Sentences.** Sentence capitalisation and the punctuation of standalone
   responses are repaired.
4. **Typography.** Unicode normalisation, curly apostrophes, ellipses and the
   language's quotation marks are applied across the text as a whole, not line
   by line. French gets non-breaking spaces before punctuation.
5. **Cue boundaries.** Dynamic programming chooses where cues break. It strongly
   penalises short cues and fast reading speeds. For English, a part-of-speech
   tagger keeps articles with their nouns, pronouns with their verbs, auxiliaries
   and names together. Other languages use explicit grammatical boundary rules.
6. **Line balance.** Pillow measures real font advances, preferring an installed
   Arial, so each two-line cue is optically balanced and avoids orphan lines.
7. **Timing.** Cues are retimed to the frame grid, as described below.

Every deletion is recorded in the receipt with its original text, times and
reason. These are grammatical predictions, not a guarantee of perfect editorial
phrasing.

## Timing rules

The frame rate comes from the video next to the subtitles when there is one.
Otherwise it is 25 fps; `--fps` overrides it.

| Rule | Value |
| --- | --- |
| Start snapping | within one frame |
| End extension | up to 0.5 seconds of free space |
| Minimum duration | 5/6 second |
| Maximum duration | 7 seconds |
| Gap between cues | two frames, or at least half a second |
| Line length | 42 characters, at most two lines |

Reading speed targets, in visible characters per second:

| Language | Characters per second |
| --- | --- |
| English | 20 |
| German, French, Polish | 17 |
| Other languages | 17 (unverified fallback) |

Formatting tags do not count towards these lengths. Long single words and fast
speaker changes can make some rules impossible to meet without changing the
meaning; such cues are kept and reported.

## The audit

The receipt holds `beautification.audit`. Its `violations` list names every cue
that still breaks a numeric rule. With `--strict`, a set with unresolved
violations is not written.

Passing the numeric checks does not certify a delivery for a streaming platform.
Shot changes, dialogue sync, glyph coverage, regional editorial rules and
playback still need review. The rules are based on the Netflix timed-text style
guides (general requirements, timing, English, German, French and Polish), but
the speaker colours are a project convention, not Netflix's white-text delivery
style.

## Beautify existing subtitles

`beautify` accepts a folder, an SRT, WebVTT or ASS file, a `.words.json` file or
a `.vexy-subs.json` receipt.

```bash
# Every subtitle set under a folder tree, local route only
vexy-subs beautify /path/to/videos --recursive --backend=local

# Timed words, with the language and frame rate given
vexy-subs beautify talk.words.json --language=en --fps=25

# Write cleaned files to another folder
vexy-subs beautify captions.srt --output_dir=cleaned

# Refuse to replace a set that still has violations
vexy-subs beautify captions.ass --strict
```

What happens to the files:

- By default the set is replaced in place. The original captions, timed words
  and receipt are saved once in `<stem>.work/beautify-original/`.
- `--output_dir` writes the result elsewhere and leaves the originals alone.
- A repeat run with the same settings checks the hashes and skips.
- `--force` processes again from the saved originals, so edits never pile up.
- With `--recursive`, folders named `private`, `.venv`, `.git`,
  `beautify-original` and any `.work` folder are skipped.
- `--verbose` adds debug detail on the error stream.

When the input is a caption file without timed words, word times are estimated in
proportion to the text. The receipt marks them as estimates. Original word times
are always used when they are available.

## Local and LLM routes

The **local** route uses only bundled or cached models. Caption text stays on
your machine.

The **LLM** route sends batches of caption words with anonymous speaker IDs to an
OpenAI-compatible endpoint. The model may delete unnecessary words and fix casing
and punctuation. Its reply is rejected if it inserts or reorders words, rewrites
a word, deletes a number or an acronym, or deletes more than 30% of a batch.
Timestamps and speaker IDs never leave your machine and are never changed by the
model. API keys never appear in receipts or on standard output.

The route is chosen by `--backend` (`beautify`) or `--beautify_backend`
(`transcribe`, `batch`, `render`):

| Value | Route |
| --- | --- |
| `local` | always local |
| `llm` | always the LLM; fails if no model is configured |
| `auto` (default) | the LLM when a model is configured, otherwise local |

[Configuration](configuration.md) explains how to configure the model.
