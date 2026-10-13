# Translation

`translate` translates an SRT, VTT, ASS or SSA file with any OpenAI-compatible
chat model. Every cue keeps its timing, and an ASS input keeps its speaker
styles and colours. The extension of the output file chooses its format.

```bash
vexy-subs translate SRC DST LLM SOURCE_LANG TARGET_LANG [flags]
```

Subtitle text is sent to the endpoint you name. Confirm that this is acceptable
before you use a remote provider.

## Examples

```bash
# A configured profile, ASS to ASS
vexy-subs translate talk.ass talk.pl.ass cerebras-code English Polish

# An explicit model spec and a glossary, SRT to WebVTT
vexy-subs translate talk.srt talk.de.vtt \
  "gpt-4o::OPENAI_API_KEY::https://api.openai.com/v1" en de --vocab=glossary.json

# Try the "fast" profile first, then "careful"
vexy-subs translate talk.srt talk.fr.srt fast,careful en fr
```

`LLM` is a profile name, an explicit `model::ENV_KEY::base_url` spec, or a
comma-separated list of either. See
[Configuration](configuration.md#llm-providers-and-profiles).

`SOURCE_LANG` and `TARGET_LANG` are passed to the model as written, so `en` and
`English` both work.

## Flags

| Flag | Default | Meaning |
| --- | --- | --- |
| `--vocab` | empty | JSON glossary of exact term translations |
| `--config_file` | platform config file | `config.toml` to read profiles from |
| `--env_file` | empty | `.env` file to load keys from |
| `--chunk_size` | `40` | cues per request |
| `--refine` | `True` | run the second, refining pass |
| `--timeout` | `60` | seconds per request |
| `--force` | `False` | replace an existing output |

## How a file is translated

1. The input is parsed. Comment events in ASS files are dropped. A file that
   contains text but no parsable cue is an error.
2. Cues are sent in chunks of `--chunk_size`. Each request contains the glossary
   and the previous chunk's translation as context.
3. Each cue travels as numbered JSON, `{"id", "text"}`, so a cue with several
   lines stays whole.
4. The reply must contain exactly the same cue IDs in the same order. A reply that
   drops, merges or reorders a cue is rejected.
5. With `--refine=True`, a second pass rewrites stiff phrasing in the
   translated chunk, under the same checks.
6. The translated text is written back into the original cues, so start and end
   times never change.

## When a reply is rejected

1. The same model is asked again, with the reason for the rejection.
2. If it fails again, the next model in the list is tried.
3. If every model fails, the chunk is split in half and each half is tried
   again, down to single cues.
4. If a single cue still fails, the command stops. It never shifts timestamps to
   make a bad reply fit.

HTTP 401 and 403 errors skip straight to the next model. HTTP 408, 429 and 5xx
errors, and network errors, wait and retry. A `<think>` block before the reply,
code fences and prose around the JSON object are tolerated.

## Glossary

`--vocab` names a JSON object that maps source terms to their required
translations:

```json
{"kerning": "kerning", "typeface": "krój pisma"}
```

A missing glossary file is an error.

## Limits

- An existing output needs `--force`, and the output cannot be the input file.
- Text in braces, `{...}`, is read as an ASS override tag when the file is saved,
  and is lost.
- To keep speaker colours, translate from ASS to ASS.

## Migrating from vttrix

`vexy-subs translate` replaces the retired `vttrix` package:

| vttrix | vexy-subs |
| --- | --- |
| `vttrix translate a b llm src dst --vocab=v.json` | `vexy-subs translate a b llm src dst --vocab=v.json` |
| `from vttrix import ...` | `from vexy_subs import ...` |
| `[model_providers.*]`, `[profiles.*]` in vttrix's `config.toml` | the same tables in the vexy-subs `config.toml` |

Differences: an existing output needs `--force`, input with text but no cues is
an error, and provider discovery matches only upper-case `{PREFIX}_API_KEY` names
with an HTTP(S) endpoint.
