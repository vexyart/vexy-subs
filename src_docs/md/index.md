# vexy-subs

`vexy-subs` generates subtitles for a video on your own machine, with one colour
per speaker. It recognises the words, works out who said each one, restores
sentence punctuation, cleans up hesitations and lays the text out as readable
captions. You can give it the names and terms used in the recording so that they
are recognised and spelled correctly.

```bash
vexy-subs transcribe clip.mp4 --prompt_file=hints.md --output_dir=subtitles
```

For `clip.mp4`, this writes five files into `subtitles/`:

| File | Contents |
| --- | --- |
| `clip.ass` | captions with a named, coloured style per speaker |
| `clip.vtt` | WebVTT with voice spans, cue classes and CSS colour rules |
| `clip.srt` | SubRip with `<font color>` tags |
| `clip.words.json` | every recognised word with its times and speaker |
| `clip.vexy-subs.json` | a receipt with settings, hashes and checks |

The recognition, diarization and punctuation models run locally on Apple
Silicon. No API key is needed. Only `translate`, and the optional LLM route of
the caption clean-up, send text to an endpoint that you configure.

## What it can do

- **Transcribe** a video or a folder of videos into speaker-coloured subtitles.
  See [Transcription](transcription.md).
- **Beautify** existing captions: remove fillers, balance lines and fix timing,
  without repeating recognition. See [Beautification](beautify.md).
- **Translate** SRT, VTT, ASS or SSA files with any OpenAI-compatible model,
  keeping every cue's timing and the ASS speaker styles. See
  [Translation](translation.md).
- **Verify** a folder of results against their receipts. See
  [Command reference](cli.md#verify).

## How a video becomes subtitles

1. FFmpeg decodes the audio.
2. MLX Whisper recognises timed words, using your hints as context.
3. Collapsed word timestamps are repaired with a forced aligner.
4. A diarizer finds who speaks when across the whole recording.
5. Each word is assigned to the speaker active at that time.
6. A punctuation model adds one punctuation label per word.
7. Beautification detects the language, removes disfluencies, and builds
   balanced, well-timed cues.
8. The cues are written as ASS, WebVTT and SRT, then parsed again and checked.

Each model stage saves its result in a `.work` folder, so a failed run can
resume without repeating the stages that succeeded.

## Where to go next

| Page | Read it when you want to |
| --- | --- |
| [Installation](installation.md) | install the tool and its optional extras |
| [Quickstart](quickstart.md) | make subtitles for a first video |
| [Transcription](transcription.md) | understand hints, speakers, outputs and batches |
| [Beautification](beautify.md) | clean up captions and read the audit |
| [Translation](translation.md) | translate a subtitle file with an LLM |
| [Configuration](configuration.md) | set up `config.toml`, `.env` and LLM profiles |
| [Command reference](cli.md) | look up every command and flag |
| [Python API](api.md) | load, translate and save subtitles from Python |
| [Troubleshooting](troubleshooting.md) | fix a failed run |
| [Development](development.md) | test, build and release the package |
