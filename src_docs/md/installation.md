---
this_file: src_docs/md/installation.md
tags: [Installation]
---

<!-- this_file: src_docs/md/installation.md -->
# Installation

## Prerequisites

- Python 3.12 or later.
- [uv](https://docs.astral.sh/uv/) to install the command-line tool.
- For transcription: FFmpeg with `ffprobe` on `PATH`; Apple Silicon for MLX,
  or an installed audio.cpp binary and GGUF models on other hosts.

The base package installs the shared `vexy-audioflexy[editorial]>=1.0.3` APIs
without GPU or speech model runtimes. It can beautify,
translate, render and verify subtitles on any platform that runs Python 3.12.

## Choose the extras

| Extra | Installs | Needed for |
| --- | --- | --- |
| `apple` | `mlx-whisper`, `mlx-audio`, `deepmultilingualpunctuation`, `torch`, `transformers`, `soundfile` | `transcribe` and `batch` |
| `native` | FullStop punctuation dependencies; audio.cpp itself is installed separately | optional model punctuation on native hosts |
| `cluster` | `diarize` | CPU speaker clustering for recordings with more than eight speakers |
| `test` | `pytest`, `pytest-cov`, `ruff`, `build`, `twine` | development |

## Install the tool

1. Install the package with the extras you need. For local transcription with
   both diarization back-ends:

    ```bash
    uv tool install 'vexy-subs[apple,cluster]'
    ```

    To install from sibling source checkouts instead, run this in the repository folder:

    ```bash
    uv tool install --with ../vexy-audioflexy-project/vexy-audioflexy './[apple,cluster]'
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

    `inference_installed` is `true` when MLX is usable or the native executable is found.
    This does not certify installed model weights or native model-family support.
    `inference_provider` and `inference_provider_version` identify Audioflexy;
    `punctuation_installed` reports the separate optional FullStop package.
    `mlx_available` checks the actual MLX runtime; `asr_backend` reports the
    automatic route, and `audiocpp_installed` checks the native executable. `cluster_installed` is `true`
    when the `diarize` package is installed.

## Model downloads

The first transcription downloads open model weights from Hugging Face:

| Stage | Default model |
| --- | --- |
| Speech recognition | `mlx-community/Qwen3-ASR-1.7B-8bit` |
| Diarization | `mlx-community/Nemotron-3-Diarization-8bit` |
| Punctuation | Preserve Qwen punctuation (`auto` → `asr`); FullStop is optional |
| Word alignment | `mlx-community/Qwen3-ForcedAligner-0.6B-8bit` |

The forced aligner runs on every Qwen speech chunk. Recognition vocabulary is
forwarded to each chunk; word times are acoustic estimates, not interpolated
chunk bounds. MLX weights download on first use. `vexy-subs models` shows the stack.

## Native Qwen setup

Build or install [audio.cpp](https://github.com/0xShug0/audio.cpp), with the
`qwen3_asr`, `qwen3_forced_aligner` and, if required, `nemotron_3_diar` families.
The adapter uses the documented 0.9.1-compatible CLI. Install models with the
upstream manager, then set their actual paths:

```bash
audiocpp_model_manager install qwen3_asr_1_7b_q8_0 --models-dir models
audiocpp_model_manager install qwen3_forced_aligner_0_6b_q8_0 --models-dir models
audiocpp_model_manager install nemotron_3_diar_bf16 --models-dir models
export VEXY_SUBS_QWEN_MODEL=/absolute/path/to/qwen3-asr-1.7b-q8_0.gguf
export VEXY_SUBS_QWEN_ALIGNER=/absolute/path/to/qwen3-forced-aligner-0.6b-q8_0.gguf
export VEXY_SUBS_NEMOTRON_MODEL=/absolute/path/to/nemotron-3-diarization-bf16.gguf
vexy-subs transcribe talk.mp4 --asr_backend=audiocpp --diar_backend=audiocpp
```

Install the base package for Qwen punctuation plus native diarization, `[cluster]`
for CPU speaker clustering, and `[native]` only if you need model punctuation.
Pass `--audiocpp_bin` or set `VEXY_SUBS_AUDIOCPP_BIN` if the executable is outside
PATH. Native model flags override the environment. Model weights remain external;
no private model workspace is required. Automatic ASR selection chooses MLX when
available, otherwise native Qwen. Missing native prerequisites produce setup
errors; inference errors do not trigger an unrelated ASR fallback.

For English, beautification also uses NLTK's small averaged-perceptron
part-of-speech tagger. Its weights download once into the user cache folder.

## Local build installation

The published package requires Audioflexy 1.0.3 or later for shared speech APIs.
To test local builds, install the exact wheels from both source repositories:

```bash
uv tool install --with ./wheels/vexy_audioflexy-VERSION-py3-none-any.whl ./wheels/vexy_subs-VERSION-py3-none-any.whl
```

Replace both filenames with the built artifacts. For Apple inference and CPU
clustering, quote the consumer wheel filename with an `[apple,cluster]` suffix. The `apple`, `native` and `cluster` extras delegate their model
runtimes to Audioflexy's matching extras. Existing `VEXY_SUBS_*` settings remain
supported; matching `VEXY_AUDIOFLEXY_*` settings take precedence. Model files and
the native executable stay external. Some audio.cpp builds reject
`nemotron_3_diar`; that error propagates without changing ASR families.
An empty workspace root uses installed Audioflexy adapters; an explicit legacy
workspace remains supported.
