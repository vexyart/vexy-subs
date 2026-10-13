# Quickstart

This walk-through makes subtitles for a talk, `talk.mp4`, in which the speakers
mention the product names QuasarAPI and OpenType.

## Before you start

- `vexy-subs` is installed with the `apple` extra, and `vexy-subs doctor` reports
  `"inference_installed": true`. See [Installation](installation.md).
- `ffmpeg` and `ffprobe` are on `PATH`.

## Make subtitles for one video

1. Write a hint file, `talk.md`, with the names and terms used in the talk:

    ```text
    Terms: QuasarAPI, OpenType, Python.
    This talk discusses font shaping. Preserve the terminology when it is spoken.
    ```

    The terms on the `Terms:` line are sent to Whisper as recognition context,
    and keep their casing when punctuation is restored.

2. Run `transcribe`:

    ```bash
    vexy-subs transcribe talk.mp4 --prompt_file=talk.md --output_dir=subtitles
    ```

    Progress goes to the terminal's error stream:

    ```text
    ASR talk.mp4
    DIARIZATION talk.mp4
    PUNCTUATION talk.mp4
    DONE talk.mp4: 212 cues, 2 speakers
    ```

    The receipt is printed as JSON on standard output.

3. Open `subtitles/talk.ass` in a desktop player such as mpv or VLC, next to the
   video. Each speaker has their own colour.

The result is five files in `subtitles/`: `talk.ass`, `talk.vtt`, `talk.srt`,
`talk.words.json` and `talk.vexy-subs.json`. The model results are kept in
`subtitles/talk.work/`.

## Name the speakers

Speaker IDs are anonymous, such as `speaker_0`. Once you have checked who each
speaker is, you can show names instead.

1. Write `labels.json`:

    ```json
    {"speaker_0": "Presenter", "speaker_1": "Guest"}
    ```

2. Render the existing timed words with the map, under a new name:

    ```bash
    vexy-subs render subtitles/talk.words.json subtitles/talk.named \
      --speaker_map=labels.json
    ```

    This writes `subtitles/talk.named.ass`, `.vtt` and `.srt` without running
    any model. Keep the new name: overwriting `talk.ass` would no longer match
    the hashes in `talk.vexy-subs.json`, and `verify` would fail.

To have names from the start, pass `--speaker_map` to `transcribe`. The map is
part of the run settings, so changing it later with `transcribe --force` runs
every model stage again.

## Correct the words and render again

If a word is wrong, edit the timed words and render them without any model.

1. Copy `subtitles/talk.words.json` to `edited.words.json` and correct the
   `text` of the wrong words.
2. Render the edited words:

    ```bash
    vexy-subs render edited.words.json subtitles/edited
    ```

    This writes `subtitles/edited.ass`, `.vtt` and `.srt`.

## Process a folder of videos

1. Put one hint file per video in `hints/`, named after the video:
   `hints/talk.md` for `videos/talk.mp4`.
2. Run `batch`:

    ```bash
    vexy-subs batch videos --prompt_dir=hints --output_dir=subtitles
    ```

3. Check every result against its source video:

    ```bash
    vexy-subs verify subtitles --source_dir=videos
    ```

    The command prints the number of verified sets and a summary per video.

## Translate the result

With an LLM profile configured (see [Configuration](configuration.md)):

```bash
vexy-subs translate subtitles/talk.ass subtitles/talk.pl.ass PROFILE English Polish
```

The Polish file keeps every cue's timing and the speaker colours. See
[Translation](translation.md).
