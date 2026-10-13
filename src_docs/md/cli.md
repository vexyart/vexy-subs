# Command reference

`vexy-subs` is a [Fire](https://github.com/google/python-fire) command-line tool.
Flags use underscores, as in `--output_dir`, and Boolean flags take an explicit
value, as in `--beautify=False`. Results are printed as JSON on standard output;
progress goes to standard error. Add `--help` after a command to print its flags:

```bash
vexy-subs transcribe --help
```

| Command | Purpose |
| --- | --- |
| `transcribe` | make subtitles for one video |
| `batch` | make subtitles for every matching video in a folder |
| `render` | render edited timed words without any model |
| `beautify` | clean up existing subtitles |
| `translate` | translate a subtitle file with an LLM |
| `verify` | check completed subtitle sets against their receipts |
| `llm` | manage LLM providers and profiles |
| `doctor` | report local prerequisites |
| `version` | print the installed package version |

## `transcribe`

```bash
vexy-subs transcribe VIDEO [flags]
```

| Flag | Default | Meaning |
| --- | --- | --- |
| `--output_dir` | the video's folder | where outputs and the `.work` folder go |
| `--prompt_file` | empty | UTF-8 `.md` or `.txt` hint file |
| `--prompt` | empty | inline hints |
| `--language` | `en` | recognition language; `""` detects it |
| `--asr_model` | `mlx-community/whisper-large-v3-turbo` | Whisper model |
| `--diar_model` | `mlx-community/Nemotron-3-Diarization-8bit` | Nemotron diarization model |
| `--punctuation_model` | `oliverguhr/fullstop-punctuation-multilang-large` | punctuation model |
| `--alignment_model` | `mlx-community/Qwen3-ForcedAligner-0.6B-8bit` | forced aligner for timestamp repair |
| `--diar_backend` | `auto` | `auto`, `nemotron` or `cluster` |
| `--turns_file` | empty | verified speaker turns instead of diarization |
| `--max_speakers` | `40` | upper limit for `cluster` |
| `--speaker_map` | empty | JSON object mapping speaker IDs to names |
| `--force` | `False` | regenerate existing outputs |
| `--beautify` | `True` | apply beautification |
| `--beautify_backend` | from configuration | `local`, `llm` or `auto` |
| `--beautify_language` | detected | language for beautification |
| `--config_file` | platform config file | `config.toml` to use |
| `--env_file` | empty | `.env` file to load |
| `--llm` | empty | LLM spec for beautification |
| `--fps` | `0` | frame rate; `0` reads it from the video |
| `--strict` | `False` | fail if numeric caption rules are not met |

See [Transcription](transcription.md).

## `batch`

```bash
vexy-subs batch [FOLDER] [flags]
```

`FOLDER` defaults to the current folder.

| Flag | Default | Meaning |
| --- | --- | --- |
| `--output_dir` | each video's folder | where outputs go |
| `--prompt_dir` | empty | folder with one `<stem>.md` or `<stem>.txt` per video |
| `--pattern` | `*.mp4` | which files to process |
| `--force` | `False` | regenerate existing outputs |
| `--language` | `en` | recognition language |
| `--diar_backend` | `auto` | diarization back-end |
| `--max_speakers` | `40` | upper limit for `cluster` |
| `--beautify` | `True` | apply beautification |
| `--beautify_backend` | from configuration | `local`, `llm` or `auto` |
| `--beautify_language` | detected | language for beautification |
| `--config_file`, `--env_file`, `--llm` | empty | as for `transcribe` |
| `--strict` | `False` | fail if numeric caption rules are not met |
| `--fps` | `0` | frame rate; `0` reads it from each video |

Each video runs in its own process. Failures are collected and reported at the
end as an error that lists the failed file names.

## `render`

```bash
vexy-subs render WORDS_FILE OUTPUT_STEM [flags]
```

Renders a `.words.json` file to `OUTPUT_STEM.ass`, `.vtt` and `.srt` without
loading any model. Use it after you edit the words by hand.

| Flag | Default | Meaning |
| --- | --- | --- |
| `--speaker_map` | empty | JSON object mapping speaker IDs to names |
| `--force` | `False` | replace existing caption files |
| `--beautify` | `True` | apply beautification |
| `--language` | detected | language for beautification |
| `--fps` | `25` | frame rate |
| `--backend` | from configuration | `local`, `llm` or `auto` |
| `--config_file`, `--env_file`, `--llm` | empty | as for `transcribe` |

## `beautify`

```bash
vexy-subs beautify [PATH] [flags]
```

`PATH` is a folder, an SRT, WebVTT or ASS file, a `.words.json` file or a
`.vexy-subs.json` receipt. It defaults to the current folder.

| Flag | Default | Meaning |
| --- | --- | --- |
| `--language` | detected | language |
| `--fps` | `0` | frame rate; `0` reads it from a neighbouring video, else 25 |
| `--backend` | from configuration | `local`, `llm` or `auto` |
| `--config_file`, `--env_file`, `--llm` | empty | as for `transcribe` |
| `--recursive` | `False` | search subfolders |
| `--output_dir` | empty | write results here instead of replacing in place |
| `--force` | `False` | reprocess from the saved originals |
| `--strict` | `False` | do not replace a set with unresolved violations |
| `--verbose` | `False` | debug output on standard error |

See [Beautification](beautify.md).

## `translate`

```bash
vexy-subs translate SRC DST LLM SOURCE_LANG TARGET_LANG [flags]
```

| Flag | Default | Meaning |
| --- | --- | --- |
| `--vocab` | empty | JSON glossary of exact term translations |
| `--config_file` | platform config file | `config.toml` to use |
| `--env_file` | empty | `.env` file to load |
| `--chunk_size` | `40` | cues per request |
| `--refine` | `True` | run the refining pass |
| `--timeout` | `60` | seconds per request |
| `--force` | `False` | replace an existing output |

See [Translation](translation.md).

## `verify`

```bash
vexy-subs verify [FOLDER] [flags]
```

Checks every `*.vexy-subs.json` receipt in `FOLDER` (default: the current
folder).

| Flag | Default | Meaning |
| --- | --- | --- |
| `--source_dir` | empty | folder with the source videos |
| `--pattern` | `*.mp4` | which source files to expect |
| `--strict` | `False` | fail on unresolved caption rule violations |

For each set, `verify`:

1. compares the hash of each output with the receipt,
2. parses the SRT, ASS and WebVTT files and checks cue counts, text, timeline and
   speaker styling,
3. checks that the captions contain every character of the timed words,
4. reruns the numeric caption audit and reports `numeric_violations`.

With `--source_dir`, it also checks each source video's hash and fails if a
matching video has no subtitles. Without it, only the completed sets are checked.
A folder with no completed set is an error.

## `llm`

```bash
vexy-subs llm path
vexy-subs llm profiles [--config_file=FILE] [--env_file=FILE]
vexy-subs llm discover [--save] [--config_file=FILE] [--env_file=FILE]
vexy-subs llm check SPEC [--config_file=FILE] [--env_file=FILE]
```

See [Configuration](configuration.md#the-llm-commands).

## `doctor`

```bash
vexy-subs doctor
```

Prints the version, platform, architecture, whether `ffmpeg` and `ffprobe` are
on `PATH`, and whether the `apple` and `cluster` extras are installed.

## `version`

```bash
vexy-subs version
```

Prints the installed package version.
