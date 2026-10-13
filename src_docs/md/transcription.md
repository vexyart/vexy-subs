<!-- this_file: src_docs/md/transcription.md -->
# Transcription

`transcribe` turns one video into speaker-coloured subtitles. `batch` does the
same for every matching video in a folder. Both need the `apple` extra.

## Recognition hints

Hints tell the recogniser which names and terms to expect.

- `--prompt_file` takes a non-empty UTF-8 file with the extension `.md` or `.txt`.
- `--prompt` adds hints inline. If you give both, the inline text comes first.

The whole hint text is passed to Whisper's initial prompt. If the text contains
lines that start with `Names:` or `Terms:`, only the comma-separated entries on
those lines are passed to Whisper instead, so Markdown instructions or programme
prose do not reach the recogniser. The same entries also keep their casing when
punctuation is restored.

```text
Names: Anna Kowalska, Ben Okafor.
Terms: QuasarAPI, OpenType, Python.
This talk discusses font shaping.
```

With this file, Whisper receives `Anna Kowalska, Ben Okafor, QuasarAPI,
OpenType, Python`.

A hint is context for recognition. It does not guarantee a replacement, and
Whisper's prompt context is finite. With the supported mlx-whisper runtime and
`condition_on_previous_text=False`, the initial prompt applies to the first
decoding window; it is not persistent glossary context for a long recording.
The receipt records the hint file's name and SHA-256, not its contents.

## Readable transcripts and model choice

Recognition hints provide spelling context; instructions such as “remove fillers”
do not make an ASR model an editor. `transcribe` already runs punctuation restoration
and conservative editorial cleanup after recognition. Use `--beautify=False` to
retain verbatim words, or `beautify` to revise existing timed captions. Retained
word timings are preserved apart from recorded timing repairs; deleted fillers
are recorded in the receipt.
Immediate repeated phrase starts are removed even when the punctuation model
puts a period after an unfinished article (for example, “That’s a. That’s a good
lesson”). Complete repeated sentences, questions, pauses and speaker handoffs
remain protected. This produces readable captions without free paraphrasing or
summarization; punctuation predictions still need editorial review.

A local comparison of Whisper turbo, Parakeet Ultra and Qwen3-ASR 1.7B found that
metadata prompts did not improve every excerpt, and an editorial instruction to
Qwen left repetitions intact. Recognition speed alone does not establish better
technical vocabulary or editorial quality. Whisper remains the supported ASR
backend; `--asr_model` selects a compatible Whisper checkpoint, not another family.

Timing contracts also differ. Whisper supplies word estimates. Parakeet's tested
MLX runtime supplies sentence intervals and subword tokens. Qwen's tested MLX
runtime supplies audio-chunk bounds, which cannot be treated as sentence timings.
Qwen offers a separate forced aligner, but it must be exercised before that route
can deliver aligned captions. An alignment estimate is not a native word timestamp.

Implementation references: [MLX Whisper](https://github.com/ml-explore/mlx-examples/tree/main/whisper),
[Parakeet MLX](https://github.com/senstella/parakeet-mlx), and
[Qwen3-ASR](https://github.com/QwenLM/Qwen3-ASR).

## Language

`--language` defaults to `en`. Pass an empty string, `--language=""`, to let
Whisper detect the language.

The default punctuation model supports English, German, French, Italian and
Dutch. For other languages, pass a suitable model with `--punctuation_model`.

## Speakers

### Diarization back-ends

| `--diar_backend` | Behaviour |
| --- | --- |
| `auto` (default) | Nemotron; switches to `cluster` when all eight Nemotron slots are filled |
| `nemotron` | Nemotron only; tracks up to eight speakers |
| `cluster` | CPU WeSpeaker embeddings with spectral clustering; estimates the speaker count up to `--max_speakers` (default 40) |

`cluster` needs the `cluster` extra. If `auto` needs to switch and the extra is
missing, the run stops with setup guidance.

Nemotron processes the whole recording with one continuous speaker cache, so
speaker IDs do not restart partway through. Automatic clustering can merge or
split voices, especially in short or noisy turns.

### Supplied turns

`--turns_file` skips diarization and uses turns that you have verified. The file
is JSON with a `turns` array and a `capacity` value:

```json
{
  "capacity": 2,
  "turns": [
    {"start": 0.0, "end": 14.2, "speaker": "speaker_0"},
    {"start": 14.2, "end": 31.8, "speaker": "speaker_1"}
  ]
}
```

### How words get a speaker

Each word goes to the speaker whose turns overlap it most. If several speakers
overlap a word, it is marked `ambiguous` in `.words.json`. Mono audio cannot
reliably separate words spoken at the same time.

A word that no turn overlaps takes the nearest turn's speaker if that turn starts
or ends within 0.5 seconds of the word's midpoint. Otherwise it stays
`unassigned` and is shown in white.

A word with zero duration takes the speaker of the nearest timed word and is
marked ambiguous. It never merges two speakers into one coloured cue.

### Speaker names

Speaker IDs are anonymous and local to one recording. A programme listing cannot
tell which voice belongs to whom. Once you have verified the identities, map IDs
to names with `--speaker_map`:

```json
{"speaker_0": "Presenter", "speaker_1": "Guest"}
```

Every value must be a non-empty string. The names appear as ASS event names and
WebVTT voice names.

## Output files

For an input `talk.mp4`, the outputs go to `--output_dir`, or beside the video if
it is empty.

| File | Contents |
| --- | --- |
| `talk.ass` | one style per speaker (Arial 46, outline 3, shadow 1, 1920 × 1080 script resolution); the event name is the speaker label |
| `talk.vtt` | each cue as `<v Name><c.speakerN>…</c></v>`, with a `STYLE` rule per speaker class |
| `talk.srt` | each cue wrapped in `<font color="#RRGGBB">`; some players ignore the tag |
| `talk.words.json` | `words`: `text`, `start`, `end`, `speaker`, `ambiguous` |
| `talk.vexy-subs.json` | settings, hashes, checks and stage information |

Use ASS for reliable desktop styling and WebVTT for browser playback.

The first eight speakers get these colours: `#7DD3FC`, `#FDE047`, `#86EFAC`,
`#FDA4AF`, `#C4B5FD`, `#FDBA74`, `#67E8F9` and `#F0ABFC`. Further speakers get
distinct generated colours. Unassigned words are `#FFFFFF`.

After writing, all three caption files are parsed again and compared: they must
have the same number of cues, the same text, matching times and a speaker style
on every cue.

## The work folder

Model results are saved in `talk.work/` in the output folder:

| File | Stage |
| --- | --- |
| `asr.json` | recognised words and the raw Whisper result |
| `alignment.json` | words after timestamp repair |
| `diarization.json` | speaker turns |
| `punctuation.json` | punctuated words |

Each file is keyed to the input hash and the settings that affect it. If a run
fails, the next run reuses every stage whose key still matches. Changing only the
beautification settings reuses all four stages.

## Re-running

If the receipt exists, its settings match and every output still has the
recorded hash, `transcribe` prints `SKIP talk.mp4: verified` and returns the old
receipt. If the settings or outputs differ, the run stops; add `--force` to
regenerate. Caption files that have no receipt are never overwritten without
`--force`.

## Batch processing

```bash
vexy-subs batch videos --prompt_dir=hints --output_dir=subtitles
```

- `--pattern` selects the videos; the default is `*.mp4`.
- With `--prompt_dir`, every video must have exactly one hint file named
  `<video stem>.md` or `<video stem>.txt`. This is checked for all videos before
  any processing starts.
- Each video runs `transcribe` in its own process, with a limit of four hours, so
  models are released between videos.
- Existing verified outputs are skipped. A failed video does not stop the batch;
  the failures are reported together at the end.

`batch` forwards `--force`, `--language`, the beautification options, `--llm`,
`--strict` and `--fps`. It forwards `--diar_backend` and `--max_speakers` only
when `--diar_backend` is not `auto`.

## Privacy

Recordings, hint files, personal names, models and run artefacts are your
private data. They are excluded from the package's source and wheel builds,
which contain only synthetic test fixtures. Nothing is uploaded unless you use
`translate` or the LLM route of beautification.
