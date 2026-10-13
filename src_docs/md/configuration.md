# Configuration

Configuration controls the beautification route, the optional LLM, and the LLM
providers and profiles used by `translate`. Recognition and diarization take
their settings from command-line flags only.

## Where settings come from

For each setting, the first source that provides it wins:

1. an explicit command-line flag,
2. an environment variable, including variables loaded from `.env` files,
3. `config.toml`,
4. the built-in default.

### `config.toml`

The file is `config.toml` in the platform's user configuration folder for
`vexy-subs`. On macOS this is:

```text
~/Library/Application Support/vexy-subs/config.toml
```

Linux uses the XDG configuration folder, and Windows the user's local
application-data folder. Print the exact path with:

```bash
vexy-subs llm path
```

`--config_file` uses another file; that file must exist.

### `.env` files

python-dotenv loads, in this order, without overriding variables that are already
set:

1. the file given with `--env_file`, or else a `.env` found from the working
   folder,
2. the `.env` file next to `config.toml`.

Keep API keys in the environment or a private `.env` file. `config.toml` stores
only the names of key variables.

## Beautification and LLM settings

```toml
[beautify]
backend = "auto" # local, llm, or auto: llm only when a model is configured
# font = "/absolute/path/to/Arial.ttf"

[llm]
model = "your-loaded-model"
base_url = "http://localhost:1234/v1" # OpenAI-compatible chat completions
api_key_env = "VEXY_SUBS_LLM_API_KEY"
timeout = 60
```

| Setting | Environment variable | Default |
| --- | --- | --- |
| `[beautify] backend` | `VEXY_SUBS_BEAUTIFY_BACKEND` | `auto` |
| `[beautify] font` | `VEXY_SUBS_FONT` | installed Arial |
| `[llm] model` | `VEXY_SUBS_LLM_MODEL` | none |
| `[llm] base_url` | `VEXY_SUBS_LLM_BASE_URL` | `http://localhost:1234/v1` |
| `[llm] api_key_env` | — | `OPENAI_API_KEY` |
| API key value | `VEXY_SUBS_LLM_API_KEY` | the variable named by `api_key_env` |
| `[llm] timeout` | `VEXY_SUBS_LLM_TIMEOUT` | `60` seconds |
| `[llm] profile` | `VEXY_SUBS_LLM` | none |

With `backend = "auto"`, the LLM route is used only when a model is configured.
The LLM route needs a model and an `http://` or `https://` base URL. The timeout
must be a positive number.

The flags for these settings differ by command:

| Command | Route flag | Language flag |
| --- | --- | --- |
| `beautify` | `--backend` | `--language` |
| `transcribe`, `batch` | `--beautify_backend` | `--beautify_language` |
| `render` | `--backend` | `--language` |

All of them accept `--config_file`, `--env_file` and `--llm`.

## LLM providers and profiles

Providers and profiles use the Codex CLI layout, in the same `config.toml`:

```toml
[model_providers.cerebras]
base_url = "https://api.cerebras.ai/v1"
env_key = "CEREBRAS_API_KEY"

[profiles.cerebras-code]
model = "zai-glm-4.7"
model_provider = "cerebras"
```

A provider names an endpoint and the environment variable that holds its key. A
profile names a model and a provider.

### LLM specs

Wherever a command takes an LLM, you can give:

| Spec | Example |
| --- | --- |
| a profile name | `cerebras-code` |
| an explicit spec, `model::ENV_KEY::base_url` | `gpt-4o::OPENAI_API_KEY::https://api.openai.com/v1` |
| a comma-separated fallback list | `fast,careful` |

`translate` takes the spec as a positional argument. `transcribe`, `render`,
`batch` and `beautify` take it as `--llm`. It can also come from `VEXY_SUBS_LLM`
or `[llm] profile`. A spec replaces the `[llm]` model, base URL and key.
Beautification uses only the first entry of a list. `VEXY_SUBS_LLM_MODEL` and
`VEXY_SUBS_LLM_BASE_URL` still take precedence over a `[llm] profile` in the
file. The local route never resolves a spec.

Name profiles with letters. Fire, the command-line library, turns values such as
`1e3` or `true` into numbers or Booleans before vexy-subs sees them.

### Discovered providers

A provider is also discovered from the environment when an upper-case
`{PREFIX}_API_KEY` variable is paired with `{PREFIX}_API_ENDPOINT` or
`{PREFIX}_API_OPENAI` holding an HTTP(S) URL. For example, `GROQ_API_KEY` and
`GROQ_API_ENDPOINT` give a provider named `groq`. A provider in `config.toml`
replaces a discovered one with the same name.

### The `llm` commands

| Command | Effect |
| --- | --- |
| `vexy-subs llm path` | print the location of `config.toml` |
| `vexy-subs llm profiles` | list profiles and providers, configured and discovered, and whether each key is set |
| `vexy-subs llm discover` | list discovered providers |
| `vexy-subs llm discover --save` | append discovered providers to `config.toml`, keeping existing text and comments |
| `vexy-subs llm check SPEC` | resolve a spec without calling the model |

None of these commands prints a key value. `discover --save` adds only providers
that are not already in the file, and refuses to write a file that would not
parse.

Check a spec before a long run:

```bash
vexy-subs llm check cerebras-code
```

The output lists the resolved model, base URL, key variable name and whether the
key is set.
