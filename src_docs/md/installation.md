# Installation

## Prerequisites

- Python 3.12 or later.
- [uv](https://docs.astral.sh/uv/) to install the command-line tool.
- For transcription: a Mac with Apple Silicon, and FFmpeg with `ffprobe` on
  `PATH`.

The base package installs without any inference library. It can beautify,
translate, render and verify subtitles on any platform that runs Python 3.12.

## Choose the extras

| Extra | Installs | Needed for |
| --- | --- | --- |
| `apple` | `mlx-whisper`, `mlx-audio`, `deepmultilingualpunctuation`, `torch`, `transformers`, `soundfile` | `transcribe` and `batch` |
| `cluster` | `diarize` | CPU speaker clustering for recordings with more than eight speakers |
| `test` | `pytest`, `pytest-cov`, `ruff`, `build`, `twine` | development |

## Install the tool

1. Install the package with the extras you need. For local transcription with
   both diarization back-ends:

    ```bash
    uv tool install 'vexy-subs[apple,cluster]'
    ```

    To install from a source checkout instead, run this in the repository folder:

    ```bash
    uv tool install './[apple,cluster]'
    ```

    For beautification, translation and rendering only, the base package is
    enough:

    ```bash
    uv tool install vexy-subs
    ```

2. Check the installation:

    ```bash
    vexy-subs doctor
    ```

    The command prints JSON like this:

    ```json
    {
      "version": "1.0.1",
      "auth_required": false,
      "platform": "Darwin",
      "architecture": "arm64",
      "ffmpeg": true,
      "ffprobe": true,
      "inference_installed": true,
      "cluster_installed": true
    }
    ```

    `inference_installed` is `true` when `mlx_whisper`, `mlx_audio` and
    `deepmultilingualpunctuation` can be imported. `cluster_installed` is `true`
    when the `diarize` package is installed.

## Model downloads

The first transcription downloads open model weights from Hugging Face:

| Stage | Default model |
| --- | --- |
| Speech recognition | `mlx-community/whisper-large-v3-turbo` |
| Diarization | `mlx-community/Nemotron-3-Diarization-8bit` |
| Punctuation | `oliverguhr/fullstop-punctuation-multilang-large` |
| Timestamp repair | `mlx-community/Qwen3-ForcedAligner-0.6B-8bit` |

The forced aligner is loaded only when a recording has collapsed or out-of-order
word timestamps. Each model can be replaced with a flag; see
[Command reference](cli.md#transcribe).

For English, beautification also uses NLTK's small averaged-perceptron
part-of-speech tagger. Its weights download once into the user cache folder.
