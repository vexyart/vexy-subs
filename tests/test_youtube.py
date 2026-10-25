# this_file: tests/test_youtube.py
"""yt-dlp metadata contracts without network access."""

import json
import sys
from pathlib import Path

import pytest

from vexy_subs import hints, qwen, youtube
from vexy_subs.cli import CLI


def test_manual_english_when_only_automatic_then_none():
    info = {"subtitles": {"live_chat": [], "de": []}, "automatic_captions": {"en": []}}
    assert youtube.manual_english(info) == "", "Automatic captions never qualify"
    assert youtube.manual_english({"subtitles": {"en-GB": [], "en": []}}) == "en"
    assert youtube.manual_english({"subtitles": {"en-US": []}}) == "en-US"


def test_hints_when_description_noisy_then_tagged_and_cleaned():
    text = youtube.hints(
        {
            "title": " Type  talk ",
            "description": "Intro https://x.y/z #fonts\n00:12 Chapter\nEnd",
        }
    )
    assert text == "Title: Type talk\nDescription: Intro Chapter End"
    long = youtube.clean("word " * 1000)
    assert len(long) <= youtube.DESCRIPTION_CHARS + 2 and long.endswith("…")


def test_sidecars_when_manual_captions_downloaded_then_reference_found(tmp_path):
    video = tmp_path / "abc.mp4"
    video.write_bytes(b"")
    assert youtube.sidecars(video) == ("", "")
    (tmp_path / "abc.info.json").write_text(
        json.dumps(
            {"title": "T", "subtitles": {"en": []}, "automatic_captions": {"en": []}}
        )
    )
    (tmp_path / "abc.en.vtt").write_text("WEBVTT\n")
    meta, reference = youtube.sidecars(video)
    assert meta == "Title: T" and reference == str(tmp_path / "abc.en.vtt")


def test_read_list_when_comments_then_urls_only(tmp_path):
    listing = tmp_path / "urls.txt"
    listing.write_text("# talks\nhttps://youtu.be/a\n\nhttps://youtu.be/b\n")
    assert youtube.read_list(str(listing)) == [
        "https://youtu.be/a",
        "https://youtu.be/b",
    ]
    listing.write_text("not a url\n")
    with pytest.raises(ValueError):
        youtube.read_list(str(listing))


def test_expand_when_playlist_then_entries_in_order(monkeypatch):
    class Client:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def extract_info(self, url, download):
            if "list" in url:
                return {
                    "_type": "playlist",
                    "entries": [{"id": "a", "url": "https://y/a"}, None, {"id": "b"}],
                }
            return {"webpage_url": url}

    monkeypatch.setattr(youtube, "client", lambda options: Client())
    found = youtube.expand("https://y/list")
    assert found == ["https://y/a", "https://www.youtube.com/watch?v=b"]


def test_download_when_ytdlp_fails_or_no_file_then_clear_errors(tmp_path, monkeypatch):
    utils = pytest.importorskip("yt_dlp.utils")
    seen = {}

    class Client:
        def __init__(self, outcome):
            self.outcome = outcome

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def extract_info(self, url, download):
            if isinstance(self.outcome, Exception):
                raise self.outcome
            return self.outcome

    def failing(options):
        seen.update(options)
        return Client(utils.DownloadError("gone"))

    monkeypatch.setattr(youtube, "client", failing)
    with pytest.raises(RuntimeError, match="yt-dlp failed"):
        youtube.download("https://y/x", tmp_path)
    assert seen["writesubtitles"] and not seen["writeautomaticsub"], (
        "Only uploader captions may be requested"
    )
    monkeypatch.setattr(youtube, "client", lambda options: Client({"id": "x"}))
    with pytest.raises(FileNotFoundError):
        youtube.download("https://y/x", tmp_path)
    (tmp_path / "x.mp4").write_bytes(b"")
    assert youtube.download("https://y/x", tmp_path) == tmp_path / "x.mp4"


def test_context_when_glossary_then_metadata_and_chunk_reference_kept():
    prompt = "Names: David Berlow\nTitle: Talk\nDescription: About fonts\nfree note"
    text = qwen.context(prompt, "Hello there")
    assert (
        "David Berlow" in text
        and "Title: Talk" in text
        and "Description: About fonts" in text
    )
    assert "free note" not in text, (
        "Untagged free-form text stays out when a glossary exists"
    )
    assert "Hello there" in text
    assert qwen.context("plain hints") == "plain hints", (
        "Existing prompts are unchanged"
    )


def test_excerpt_when_reference_then_only_overlapping_text():
    reference = [
        (0, 5, "one"),
        (29, 31, "two"),
        (40, 45, "three"),
        (62, 63, "four"),
        (58, 61, "edge"),
    ]
    assert hints.excerpt(reference, 30, 60) == "two three edge"


def test_read_reference_when_srt_then_timed_text(tmp_path):
    srt = tmp_path / "ref.srt"
    srt.write_text("1\n00:00:01,000 --> 00:00:02,000\nHello <i>world</i>\n")
    events, receipt = hints.read_reference(str(srt))
    assert events == [(1.0, 2.0, "Hello world")] and receipt["filename"] == "ref.srt"


def test_batch_when_url_list_then_downloads_hints_reference_and_visual(
    tmp_path, monkeypatch
):
    downloads = tmp_path / "sources"
    downloads.mkdir()
    video = downloads / "abc.mp4"
    video.write_bytes(b"")
    (downloads / "abc.info.json").write_text(
        json.dumps(
            {"title": "Talk", "description": "About type", "subtitles": {"en": []}}
        )
    )
    (downloads / "abc.en.vtt").write_text("WEBVTT\n")
    listing = tmp_path / "urls.txt"
    listing.write_text("https://y/abc\n")
    monkeypatch.setattr(youtube, "expand", lambda source: ["https://y/abc"])
    monkeypatch.setattr(youtube, "download", lambda url, folder: video)
    commands, visuals, indexed = [], [], []
    monkeypatch.setattr(
        "vexy_subs.cli.subprocess.run", lambda command, **kw: commands.append(command)
    )
    monkeypatch.setattr(
        CLI, "visual", lambda self, video, **kw: visuals.append((video, kw))
    )
    monkeypatch.setattr(
        "vexy_subs.cli.page.index", lambda folder, videos: indexed.append(videos)
    )
    out = tmp_path / "pack"
    result = CLI().batch(str(listing), output_dir=str(out), visual=True)
    assert result == {"processed": 1, "failures": []}
    command = commands[0]
    assert command[:4] == [sys.executable, "-m", "vexy_subs.cli", "transcribe"]
    assert f"--prompt_file={out / 'abc.hints.md'}" in command
    assert f"--reference_file={downloads / 'abc.en.vtt'}" in command
    assert (
        out / "abc.hints.md"
    ).read_text() == "Title: Talk\nDescription: About type\n"
    assert visuals == [(str(video), {"output_dir": str(out), "force": False})]
    assert indexed == [[Path(video)]]
