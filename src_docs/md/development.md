# Development

## Set up

1. Clone the repository:

    ```bash
    git clone https://github.com/vexyart/vexy-subs.git
    cd vexy-subs
    ```

2. Run the tests. uv creates the environment with the `test` extra:

    ```bash
    ./test.sh
    ```

    `test.sh` runs `pytest` with coverage of `vexy_subs` and fails below 80%
    coverage. It then runs `ruff check` on `src` and `tests`.

The tests use synthetic fixtures only. They do not need the `apple` extra.

## Source layout

| Module | Responsibility |
| --- | --- |
| `cli.py` | Fire commands: `render`, `batch`, `verify`, `doctor`, `llm` |
| `pipeline.py` | the `transcribe` pipeline and its resumable stages |
| `inference.py` | MLX Whisper recognition and diarization |
| `alignment.py` | timestamp repair with a forced aligner |
| `punctuation.py` | punctuation restoration |
| `speakers.py` | assigning words to speakers |
| `hints.py` | reading hint files and `Names:`/`Terms:` vocabulary |
| `cues.py` | the plain cue layout used with `--beautify=False` |
| `beautify.py`, `editorial.py`, `typography.py`, `layout.py`, `syntax.py` | beautification |
| `beautify_config.py`, `beautify_llm.py` | beautification settings and the LLM route |
| `postprocess.py` | the `beautify` command |
| `formats.py` | writing and checking ASS, WebVTT and SRT |
| `translate.py` | the `translate` command and the Python API |
| `llm.py` | providers, profiles, specs and validated JSON chat calls |
| `io.py`, `types.py` | decoding, hashing, stage caching and data classes |

## Build

```bash
./build.sh            # documentation and package
./build.sh docs       # documentation only
./build.sh package    # package only
```

The package step removes `dist/`, runs `uv build` and checks the result with
`twine check`. The version comes from the git tag through hatch-vcs and is
written to `src/vexy_subs/__version__.py`, which git ignores. An untagged commit
builds a development version, which PyPI does not accept.

## Documentation

The documentation source is in `src_docs/md/`, and `src_docs/mkdocs.yml`
configures ProperDocs with the MaterialX theme:

```bash
src_docs/build.sh          # strict build into docs/
src_docs/build.sh serve    # live preview on http://127.0.0.1:8000
```

GitHub Pages serves `docs/` at <https://vexy.dev/vexy-subs/>. A push to `main`
that changes `src_docs/` rebuilds `docs/` through the `Docs` workflow.

## Release

```bash
./publish.sh
```

`publish.sh` runs `uvx gitnextver`, which commits pending changes, creates the
next `vX.Y.Z` tag and pushes. It stops if `HEAD` then carries no such tag. It
then builds the package from that tag and uploads it with `uv publish`. A
credential such as `UV_PUBLISH_TOKEN` must be set.

Run `./test.sh` before you publish; `publish.sh` does not run the tests.

## Sources

[MLX Whisper](https://github.com/ml-explore/mlx-examples/tree/main/whisper),
[Nemotron diarization](https://github.com/Blaizzy/mlx-audio/tree/main/mlx_audio/vad/models/nemotron_diarization),
[FullStop punctuation](https://github.com/oliverguhr/deepmultilingualpunctuation),
[CPU diarization](https://github.com/notch-up/diarize),
[WebVTT](https://developer.mozilla.org/en-US/docs/Web/API/WebVTT_API).
