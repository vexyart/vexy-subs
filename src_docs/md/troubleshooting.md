<!-- this_file: src_docs/md/troubleshooting.md -->
# Troubleshooting

Start with `vexy-subs doctor`. It shows whether FFmpeg, `ffprobe` and the
optional extras are installed.

## `ModuleNotFoundError` for `mlx_whisper` or `mlx_audio`

The `apple` extra is not installed. Reinstall with it:

```bash
uv tool install 'vexy-subs[apple,cluster]' --force
```

The extra needs a Mac with Apple Silicon.

## `Existing output differs; use --force to regenerate`

A receipt exists for this video, but the settings or the output files differ from
it. Add `--force` to regenerate. Model results in the `.work` folder are reused
where their settings still match.

## `Unmanaged subtitles exist; choose output_dir or --force`

Caption files with the same name exist but have no receipt. Write elsewhere with
`--output_dir`, or replace them with `--force`.

## `Existing captions; use --force to render edited words`

`render` found existing `.srt`, `.vtt` or `.ass` files at the output stem. Choose
another stem or add `--force`.

## `Eight speaker slots filled; install vexy-subs[cluster] or supply verified turns_file`

Nemotron found eight speakers, its maximum, and the `cluster` extra is not
installed. Install the extra, use `--diar_backend=cluster`, or supply verified
turns with `--turns_file`.

## `Require a supported diar_backend and positive max_speakers`

`--diar_backend` must be `auto`, `nemotron`, `audiocpp`, `workspace` or `cluster`, and `--max_speakers`
must be at least 1.

## `speaker_map must be a JSON object mapping IDs to nonempty labels`

The `--speaker_map` file must be a JSON object whose values are non-empty
strings.

## `prompt_file must be a UTF-8 .md or .txt file` or `prompt_file is empty`

Use a non-empty file with the extension `.md` or `.txt`.

## `Require exactly one prompt for ...`

With `--prompt_dir`, `batch` needs exactly one hint file per video:
`<stem>.md` or `<stem>.txt`, not both and not neither.

## `No matching videos`

`batch` found no file that matches `--pattern` (default `*.mp4`) in the folder.

## `Unresolved subtitle constraints`

`--strict` is set and some cues still break a numeric caption rule. Read
`beautification.audit.violations` in the receipt to see which cues. Run without
`--strict` to keep the best available layout.

## Punctuation is missing or wrong

The default punctuation model supports English, German, French, Italian and
Dutch. For another language, pass a suitable model with `--punctuation_model`.
Punctuation and diarization are model predictions and still benefit from review.

## Speakers are merged or split

Automatic diarization can merge or split voices, especially in short or noisy
turns. `diarization.json` in the `.work` folder stores the turns under its
`data` key. Copy that `data` object, which holds `turns` and `capacity`, to a new
file, correct the `speaker` values, and run again with `--turns_file` and
`--force`.

## `LLM backend requires model and HTTP(S) base_url`

The LLM route is selected but no model is configured, or the base URL does not
start with `http://` or `https://`. Configure `[llm]` or a profile, or use
`--backend=local`. See [Configuration](configuration.md).

## `Unknown LLM profile ...` or `Provider ... is not configured`

The profile or its provider is missing from `config.toml`. Check with:

```bash
vexy-subs llm profiles
vexy-subs llm check PROFILE
```

## `... exists; use --force to overwrite` (translate)

The translation output already exists. Add `--force`.

## `No subtitle cues could be parsed from ...`

The input to `translate` contains text but no recognisable SRT, VTT, ASS or SSA
cues.

## `Caption layout lost transcript characters` (verify)

The captions no longer contain every character of the timed words, usually
because a caption file was edited by hand after it was generated. Edit
`.words.json` instead and use `render`.

## `Changed output: ...` (verify)

An output file no longer matches the hash in its receipt. Regenerate it, or
render it again from edited words.


## Native Qwen prerequisites

When MLX is unavailable, automatic ASR selects Qwen audio.cpp. Install
`audiocpp_cli` and configure `VEXY_SUBS_QWEN_MODEL` and
`VEXY_SUBS_QWEN_ALIGNER`, or pass their model flags. A repository ID cannot be
used as a native GGUF path. For native diarization, configure
`VEXY_SUBS_NEMOTRON_MODEL`; otherwise install `[cluster]` or supply verified turns.
See [native setup](installation.md#native-qwen-setup).

## Alignment changed recognised words

The package refuses an aligner result that omits, adds or rewrites lexical text.
Native Qwen uses independent bounded requests in one loaded session to avoid
internal long-audio word filtering. Use the documented compatible audio.cpp CLI
and matching model family. Do not replace failed alignment with proportional
word timings. Acoustic zero-duration words are marked ambiguous in final output.
