# Python API

The `vexy_subs` package exports the subtitle translation API, which is
compatible with the retired `vttrix` package.

```python
from vexy_subs import load_subtitles, save_subtitles, translate_subtitles_sync

subs = load_subtitles("talk.srt")
save_subtitles(translate_subtitles_sync(subs, "cerebras-code", "en", "pl"), "talk.pl.vtt")
```

This loads `talk.srt`, translates it with the `cerebras-code` profile from
`config.toml`, and saves the result as WebVTT.

## Exports

| Name | Kind |
| --- | --- |
| `Subtitle` | data class for one cue |
| `SubtitleFile` | data class for a parsed file |
| `load_subtitles` | function |
| `save_subtitles` | function |
| `translate_subtitles` | coroutine function |
| `translate_subtitles_sync` | function |
| `__version__` | string |

## `Subtitle`

```python
@dataclass
class Subtitle:
    start_ms: int
    end_ms: int
    text: str
```

Times are whole milliseconds, which avoids floating-point drift. `text` is plain
text with `\n` between lines.

## `SubtitleFile`

```python
@dataclass
class SubtitleFile:
    events: list[Subtitle]
    format: str = "srt"
    source_path: str | None = None
    ssa: pysubs2.SSAFile | None = None
    recognized: bool = True
```

`ssa` keeps the original parsed file so that styles survive a save. `recognized`
is `False` when the file could not be parsed as subtitles.

## `load_subtitles(path)`

Loads an SRT, VTT, ASS or SSA file and returns a `SubtitleFile`. Comment events
are dropped. An empty or unrecognisable file loads with no cues and
`recognized=False`.

## `save_subtitles(subtitle_file, path, fmt=None)`

Writes the cues to `path`. The format is `fmt` if given, otherwise taken from the
extension of `path` (`.srt`, `.vtt`, `.ass` or `.ssa`), otherwise the file's own
format.

If the file came from `load_subtitles` and still has the same number of cues, its
styles and the per-cue style and speaker fields are kept by position; only times
and text change. After you reorder or replace cues, set `ssa=None` so that styles
are not applied to the wrong cues.

Text in braces, `{...}`, is read as an ASS override tag and is lost.

## `translate_subtitles_sync(subtitle_file, llm_spec, source_lang, target_lang, vocab_path=None)`

Translates every cue and returns a new `SubtitleFile` with the same timing and
the same `ssa` styles.

- `llm_spec` is a profile name, `model::ENV_KEY::base_url`, or a comma-separated
  fallback list. See [Configuration](configuration.md#llm-specs).
- `vocab_path` names an optional JSON glossary.

The translation follows the process described in
[Translation](translation.md#how-a-file-is-translated).

## `translate_subtitles(...)`

The awaitable form of `translate_subtitles_sync`, with the same arguments. The
blocking HTTP calls run in a worker thread.

```python
import asyncio
from vexy_subs import load_subtitles, save_subtitles, translate_subtitles

async def main() -> None:
    subs = load_subtitles("talk.ass")
    result = await translate_subtitles(subs, "fast,careful", "English", "German")
    save_subtitles(result, "talk.de.ass")

asyncio.run(main())
```
