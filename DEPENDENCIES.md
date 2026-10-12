<!-- this_file: DEPENDENCIES.md -->
# Dependencies

Core: Fire (CLI), pysubs2 (ASS/SRT serialization and parsing), webvtt-py (WebVTT
voices/styles), intervaltree (efficient word-to-speaker activity lookup).

Apple extra: mlx-whisper 0.4.3 (hint-aware word-timed ASR), mlx-audio 0.5.7
(Nemotron diarization), torch/Transformers (FullStop token classification),
deepmultilingualpunctuation 1.0.1 (word-aligned punctuation prediction).
FFmpeg/ffprobe are external executables. No service authentication is required.

Runtime model weights are fetched from their authors' Hugging Face repositories;
they are not distributed with this package and retain their own licenses:
Whisper MIT, Nemotron OpenMDW 1.1, FullStop MIT. Normal inference stays local.
Names and terms in user-owned hint files are not package resources.
Qwen3 ForcedAligner (MLX, Apache-2.0 weights) checks degenerate word timestamps.
SoundFile reads local audio only for this optional repair stage.
Optional `cluster` extra: diarize 0.1.2 supplies Silero VAD, WeSpeaker ONNX
embeddings, speaker-count estimation and spectral clustering without account
registration. Its compatible torch/torchaudio bounds are declared upstream;
installing both extras selects a version satisfying both sets of constraints.

Build: hatchling with hatch-vcs (version from git tags).
Tests/build: pytest, pytest-cov, ruff, build and twine.

Subtitle post-fix: langid 1.1.6 (bundled lightweight Naive Bayes language model),
NLTK (small averaged-perceptron English POS model, cached outside the project),
Pillow (proportional font advances), python-dotenv (private environment files),
platformdirs (canonical config/cache paths), Loguru (optional debug logging), and HTTPX (optional configured
OpenAI-compatible LLM endpoint). No LLM, GPU or ASR libraries are needed to
beautify existing subtitles. NLTK weights download on first English post-fix.
