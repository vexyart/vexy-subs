# this_file: tests/test_llm.py
"""Provider/profile config, env discovery, spec resolution and the chat client."""

import json
import tomllib

import fire
import httpx
import pytest

from vexy_subs import llm

CONFIG = {
    "model_providers": {
        "cerebras": {
            "name": "cerebras",
            "base_url": "https://api.cerebras.ai/v1",
            "env_key": "CEREBRAS_API_KEY",
        }
    },
    "profiles": {
        "cerebras-code": {
            "model": "zai-glm-4.7",
            "model_provider": "cerebras",
            "model_context_window": 131000,
            "model_reasoning_effort": "high",
        },
        "orphan": {"model": "m", "model_provider": "nowhere"},
    },
}

REAL_CLIENT = httpx.Client


def mock_http(monkeypatch, handler):
    monkeypatch.setattr(
        httpx,
        "Client",
        lambda **kw: REAL_CLIENT(transport=httpx.MockTransport(handler), **kw),
    )


def reply(content) -> httpx.Response:
    text = content if isinstance(content, str) else json.dumps(content)
    return httpx.Response(200, json={"choices": [{"message": {"content": text}}]})


def test_discover_providers_when_key_and_endpoint_pair_then_provider():
    env = {
        "TESTPROV_API_KEY": "k",
        "TESTPROV_API_ENDPOINT": "https://api.test.com/v1/",
        "MYPROV_API_KEY": "k",
        "MYPROV_API_OPENAI": "https://api.my.com/v1",
        "LONELY_API_KEY": "k",
        "BAD_API_KEY": "k",
        "BAD_API_ENDPOINT": "not-a-url",
    }
    found = llm.discover_providers(env)
    assert set(found) == {"testprov", "myprov"}, found
    assert found["testprov"] == {
        "name": "testprov",
        "base_url": "https://api.test.com/v1",
        "env_key": "TESTPROV_API_KEY",
        "wire_api": "chat",
    }


def test_resolve_when_explicit_spec_then_endpoint_reads_key_from_env():
    endpoint = llm.resolve(
        "gpt-4::OPENAI_API_KEY::https://api.openai.com/v1/",
        {},
        {"OPENAI_API_KEY": "sk-x"},
    )
    assert (endpoint.model, endpoint.base_url, endpoint.env_key, endpoint.api_key) == (
        "gpt-4",
        "https://api.openai.com/v1",
        "OPENAI_API_KEY",
        "sk-x",
    )
    assert "sk-x" not in repr(endpoint) and "sk-x" not in json.dumps(endpoint.receipt())


def test_resolve_when_profile_then_provider_fields_and_codex_extras_ignored():
    endpoint = llm.resolve("cerebras-code", CONFIG, {})
    assert (endpoint.model, endpoint.base_url, endpoint.env_key, endpoint.api_key) == (
        "zai-glm-4.7",
        "https://api.cerebras.ai/v1",
        "CEREBRAS_API_KEY",
        "",
    )


def test_resolve_when_profile_uses_discovered_provider_then_found():
    data = {"profiles": {"p": {"model": "m", "model_provider": "local"}}}
    env = {"LOCAL_API_KEY": "k", "LOCAL_API_ENDPOINT": "http://127.0.0.1:1234/v1"}
    assert llm.resolve("p", data, env).base_url == "http://127.0.0.1:1234/v1"


@pytest.mark.parametrize(
    ("spec", "message"),
    [
        ("a::b", "model::ENV_KEY::base_url"),
        ("m::K::ftp://x", "HTTP"),
        ("missing", "Unknown LLM profile"),
        ("orphan", "nowhere"),
    ],
)
def test_resolve_when_invalid_then_value_error(spec, message):
    with pytest.raises(ValueError, match=message):
        llm.resolve(spec, CONFIG, {})


def test_resolve_all_when_comma_list_then_ordered_and_empty_rejected():
    endpoints = llm.resolve_all("cerebras-code, m::K::http://h/v1", CONFIG, {})
    assert [e.model for e in endpoints] == ["zai-glm-4.7", "m"]
    with pytest.raises(ValueError, match="Require an LLM spec"):
        llm.resolve_all(" , ", CONFIG, {})


def test_read_config_when_explicit_missing_then_error_and_default_missing_empty(
    tmp_path, monkeypatch
):
    with pytest.raises(FileNotFoundError):
        llm.read_config(tmp_path / "none.toml")
    monkeypatch.setattr(llm, "config_path", lambda: tmp_path / "absent.toml")
    assert llm.read_config() == {}
    assert llm.config_path().name == "absent.toml"


def test_append_providers_when_existing_config_then_comments_kept_and_no_duplicates(
    tmp_path,
):
    path = tmp_path / "config.toml"
    path.write_text(
        '# keep me\n[beautify]\nbackend = "auto"\n\n[model_providers.old]\nbase_url = "http://o/v1"\n'
    )
    found = llm.discover_providers(
        {
            "OLD_API_KEY": "s",
            "OLD_API_ENDPOINT": "http://x/v1",
            "NEW_API_KEY": "s3cret",
            "NEW_API_ENDPOINT": "http://n/v1",
        }
    )
    assert llm.append_providers(found, path) == ["new"]
    text = path.read_text()
    assert text.startswith("# keep me\n[beautify]") and "s3cret" not in text
    data = tomllib.loads(text)
    assert data["model_providers"]["new"]["env_key"] == "NEW_API_KEY"
    assert data["model_providers"]["old"] == {"base_url": "http://o/v1"}
    assert llm.append_providers(found, path) == []


def test_append_providers_when_no_file_then_created(tmp_path):
    path = tmp_path / "sub" / "config.toml"
    llm.append_providers(
        {
            "p": {
                "name": "p",
                "base_url": "http://p/v1",
                "env_key": "P_API_KEY",
                "wire_api": "chat",
            }
        },
        path,
    )
    assert (
        tomllib.loads(path.read_text())["model_providers"]["p"]["base_url"]
        == "http://p/v1"
    )


def test_chat_when_fenced_reply_then_unwrapped_and_bearer_sent(monkeypatch):
    seen = []

    def handler(request):
        seen.append(request)
        return reply('```json\n{"ok": 1}\n```')

    mock_http(monkeypatch, handler)
    endpoint = llm.Endpoint("m", "http://h/v1", "K", "secret")
    assert llm.chat(endpoint, "sys", "user") == '{"ok": 1}'
    assert seen[0].url.path == "/v1/chat/completions"
    assert seen[0].headers["authorization"] == "Bearer secret"
    body = json.loads(seen[0].content)
    assert body["model"] == "m" and body["temperature"] == 0


def test_chat_when_no_key_then_no_authorization_header(monkeypatch):
    seen = []

    def handler(request):
        seen.append(request)
        return reply("{}")

    mock_http(monkeypatch, handler)
    llm.chat(llm.Endpoint("m", "http://h/v1"), "s", "u")
    assert "authorization" not in seen[0].headers


def test_ask_json_when_first_endpoint_fails_then_falls_back(monkeypatch):
    calls = []

    def handler(request):
        calls.append(request.url.host)
        if request.url.host == "bad":
            return httpx.Response(500)
        return reply({"value": 2})

    mock_http(monkeypatch, handler)
    endpoints = [
        llm.Endpoint("a", "http://bad/v1"),
        llm.Endpoint("b", "http://good/v1"),
    ]
    assert llm.ask_json(endpoints, "s", {"x": 1}, lambda r: r["value"]) == 2
    assert calls == ["bad", "bad", "good"]


def test_ask_json_when_all_invalid_then_last_error_raised(monkeypatch):
    mock_http(monkeypatch, lambda request: reply("not json"))
    with pytest.raises(ValueError):
        llm.ask_json([llm.Endpoint("a", "http://h/v1")], "s", {}, lambda r: r)
    with pytest.raises(ValueError, match="No LLM endpoints"):
        llm.ask_json([], "s", {}, lambda r: r)


def test_beautify_config_when_llm_spec_then_profile_drives_backend(
    tmp_path, monkeypatch
):
    from vexy_subs.beautify_config import load_config

    for name in ("VEXY_SUBS_LLM", "VEXY_SUBS_LLM_MODEL", "VEXY_SUBS_BEAUTIFY_BACKEND"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("CEREBRAS_API_KEY", "sk-beauty")
    config = tmp_path / "config.toml"
    env = tmp_path / ".env"
    env.write_text("")
    text = """[model_providers.cerebras]
base_url = "https://api.cerebras.ai/v1"
env_key = "CEREBRAS_API_KEY"
[profiles.cerebras-code]
model = "zai-glm-4.7"
model_provider = "cerebras"
"""
    config.write_text(text)
    assert load_config(str(config), str(env)).backend == "local"
    chosen = load_config(str(config), str(env), llm_spec="cerebras-code")
    assert (chosen.backend, chosen.model, chosen.base_url, chosen.api_key) == (
        "llm",
        "zai-glm-4.7",
        "https://api.cerebras.ai/v1",
        "sk-beauty",
    )
    assert "sk-beauty" not in json.dumps(chosen.receipt())
    config.write_text('[llm]\nprofile = "cerebras-code"\n' + text + "\n")
    assert load_config(str(config), str(env)).model == "zai-glm-4.7"
    monkeypatch.setenv("VEXY_SUBS_LLM", "x::K::http://env/v1")
    assert load_config(str(config), str(env)).base_url == "http://env/v1"
    assert load_config(str(config), str(env), backend="local").backend == "local"
    with pytest.raises(ValueError, match="Unknown LLM profile"):
        load_config(str(config), str(env), llm_spec="nope")


@pytest.fixture(autouse=True)
def no_retry_delay(monkeypatch):
    monkeypatch.setattr(llm, "RETRY_DELAY", 0)


def test_spec_text_when_fire_tuple_or_number_then_string():
    assert llm.spec_text(("fast", "careful")) == "fast,careful"
    assert llm.spec_text(1.5) == "1.5" and llm.spec_text(None) == ""
    assert [
        e.model
        for e in llm.resolve_all(("a::K::http://h/v1", "b::K::http://h/v1"), {}, {})
    ] == ["a", "b"]


def test_fire_when_comma_list_then_reaches_resolver_as_list(tmp_path, monkeypatch):
    from vexy_subs.cli import CLI

    src = tmp_path / "in.srt"
    src.write_text("1\n00:00:01,000 --> 00:00:02,000\nHi\n")
    env = tmp_path / ".env"
    env.write_text("")
    seen = []
    monkeypatch.setattr(
        "vexy_subs.translate.translate_events",
        lambda events, endpoints, *a, **k: seen.append(endpoints) or events,
    )
    fire.Fire(
        CLI,
        [
            "translate",
            str(src),
            str(tmp_path / "out.srt"),
            "a::K::http://h/v1,b::K::http://h/v1",
            "en",
            "pl",
            f"--env_file={env}",
        ],
        serialize=lambda value: None,
    )
    assert [e.model for e in seen[0]] == ["a", "b"]


def test_reply_text_when_null_think_or_fence_then_handled():
    with pytest.raises(ValueError, match="no text content"):
        llm.reply_text(None)
    assert llm.reply_text('<think>hmm {"x"}</think>\n{"a": 1}') == '{"a": 1}'
    assert llm.parse_json('Sure! {"a": 1} Hope this helps.') == {"a": 1}
    with pytest.raises(json.JSONDecodeError):
        llm.parse_json("no json here")


def test_ask_json_when_null_content_then_next_endpoint(monkeypatch):
    def handler(request):
        if request.url.host == "null":
            return httpx.Response(
                200, json={"choices": [{"message": {"content": None}}]}
            )
        return reply({"v": 1})

    mock_http(monkeypatch, handler)
    endpoints = [llm.Endpoint("a", "http://null/v1"), llm.Endpoint("b", "http://ok/v1")]
    assert llm.ask_json(endpoints, "s", {}, lambda r: r["v"]) == 1


def test_ask_json_when_401_then_no_retry_and_429_then_waits(monkeypatch):
    calls, sleeps = [], []
    monkeypatch.setattr(llm.time, "sleep", sleeps.append)
    monkeypatch.setattr(llm, "RETRY_DELAY", 1.0)

    def handler(request):
        calls.append(request.url.host)
        return httpx.Response(401 if request.url.host == "auth" else 429)

    mock_http(monkeypatch, handler)
    endpoints = [
        llm.Endpoint("a", "http://auth/v1"),
        llm.Endpoint("b", "http://busy/v1"),
    ]
    with pytest.raises(httpx.HTTPStatusError):
        llm.ask_json(endpoints, "s", {}, lambda r: r)
    assert calls == ["auth", "busy", "busy"]
    assert len(sleeps) == 1 and all(s >= 1.0 for s in sleeps)


def test_append_providers_when_merge_invalid_then_file_untouched(tmp_path):
    path = tmp_path / "config.toml"
    original = 'model_providers = { old = { base_url = "http://o/v1" } }\n'
    path.write_text(original)
    found = {
        "new": {
            "name": "new",
            "base_url": "http://n/v1",
            "env_key": "N_API_KEY",
            "wire_api": "chat",
        }
    }
    with pytest.raises(tomllib.TOMLDecodeError):
        llm.append_providers(found, path)
    assert path.read_text() == original
    assert [p.name for p in tmp_path.iterdir()] == ["config.toml"]


def test_beautify_config_when_env_model_set_then_beats_toml_profile(
    tmp_path, monkeypatch
):
    from vexy_subs.beautify_config import load_config

    monkeypatch.delenv("VEXY_SUBS_LLM", raising=False)
    monkeypatch.delenv("VEXY_SUBS_BEAUTIFY_BACKEND", raising=False)
    env = tmp_path / ".env"
    env.write_text("")
    config = tmp_path / "config.toml"
    config.write_text(
        '[llm]\nprofile = "p"\n[profiles.p]\nmodel = "pm"\nmodel_provider = "x"\n'
        '[model_providers.x]\nbase_url = "http://x/v1"\nenv_key = "X_API_KEY"\n'
    )
    monkeypatch.setenv("VEXY_SUBS_LLM_MODEL", "envmodel")
    monkeypatch.setenv("VEXY_SUBS_LLM_BASE_URL", "http://envurl/v1")
    chosen = load_config(str(config), str(env))
    assert (chosen.model, chosen.base_url) == ("envmodel", "http://envurl/v1")
    assert load_config(str(config), str(env), llm_spec="p").model == "pm"


def test_beautify_config_when_local_backend_then_spec_ignored_and_list_uses_first(
    tmp_path, monkeypatch
):
    from vexy_subs.beautify_config import load_config

    env = tmp_path / ".env"
    env.write_text("")
    monkeypatch.setenv("VEXY_SUBS_LLM", "typo-profile")
    assert load_config(env_file=str(env), backend="local").backend == "local"
    chosen = load_config(
        env_file=str(env), llm_spec=("a::K::http://h/v1", "b::K::http://i/v1")
    )
    assert (chosen.model, chosen.base_url) == ("a", "http://h/v1")
