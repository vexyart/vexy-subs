# this_file: src/vexy_subs/youtube.py
"""yt-dlp sources: one URL, a playlist or a URL list; human English captions only."""

import json
import re
from pathlib import Path

FORMAT = "bv*[height<=1080][ext=mp4]+ba[ext=m4a]/b[height<=1080]/b"
DESCRIPTION_CHARS = 1500


def is_url(text: str) -> bool:
    return re.match(r"https?://", text.strip()) is not None


def client(options: dict):
    try:
        import yt_dlp
    except ImportError as exc:
        raise RuntimeError(
            "YouTube input needs yt-dlp: install the 'youtube' extra, "
            "e.g. uv tool install 'vexy-subs[apple,cluster,video,youtube]'"
        ) from exc
    return yt_dlp.YoutubeDL(
        {"quiet": True, "no_warnings": True, "noprogress": True, **options}
    )


def read_list(source: str) -> list[str]:
    """A single URL, or a text file with one URL per line and # comments."""
    if is_url(source):
        return [source.strip()]
    lines = Path(source).read_text(encoding="utf-8").splitlines()
    found = [line.strip() for line in lines if line.strip()]
    found = [line for line in found if not line.startswith("#")]
    if not found or not all(is_url(line) for line in found):
        raise ValueError(f"Expected one http(s) URL per line in {source}")
    return found


def expand(source: str) -> list[str]:
    """Resolve playlists to their video URLs, preserving order without duplicates."""
    result = []
    with client({"extract_flat": "in_playlist"}) as ydl:
        for url in read_list(source):
            info = ydl.extract_info(url, download=False)
            if info.get("_type") != "playlist":
                result.append(info.get("webpage_url") or url)
                continue
            for entry in filter(None, info.get("entries") or []):
                result.append(
                    entry.get("url") or f"https://www.youtube.com/watch?v={entry['id']}"
                )
    return list(dict.fromkeys(result))


def manual_english(info: dict) -> str:
    """Key of an uploader-supplied English track; automatic captions never qualify."""
    keys = [
        key
        for key in info.get("subtitles") or {}
        if key == "en" or key.startswith("en-")
    ]
    return min(keys, key=lambda key: (key != "en", key)) if keys else ""


def download(url: str, folder: Path) -> Path:
    """Fetch video, info.json and human English captions; completed files are reused."""
    folder.mkdir(parents=True, exist_ok=True)
    options = {
        "format": FORMAT,
        "merge_output_format": "mp4",
        "outtmpl": str(folder / "%(id)s.%(ext)s"),
        "writeinfojson": True,
        "overwrites": False,
        "writesubtitles": True,
        "writeautomaticsub": False,
        "subtitleslangs": ["en", "en-.*"],
        "subtitlesformat": "vtt",
    }
    ydl = client(options)
    from yt_dlp.utils import DownloadError

    try:
        with ydl:
            info = ydl.extract_info(url, download=True)
    except DownloadError as exc:
        raise RuntimeError(f"yt-dlp failed for {url}: {exc}") from exc
    video = folder / f"{info['id']}.mp4"
    if not video.is_file():
        raise FileNotFoundError(f"yt-dlp did not produce {video.name}")
    return video


def clean(text: str) -> str:
    """Drop links, chapter stamps and hashtags; bound the remaining description."""
    text = re.sub(r"https?://\S+|www\.\S+", " ", text)
    text = re.sub(r"(?m)^\s*\(?\d{1,2}:\d{2}(?::\d{2})?\)?", " ", text)
    text = " ".join(re.sub(r"#\w+", " ", text).split())
    if len(text) > DESCRIPTION_CHARS:
        text = text[:DESCRIPTION_CHARS].rsplit(" ", 1)[0] + " …"
    return text


def hints(info: dict) -> str:
    """Tagged Title:/Description: lines, which qwen.context always forwards."""
    title = " ".join((info.get("title") or "").split())
    description = clean(info.get("description") or "")
    return "\n".join(
        filter(
            None,
            (
                f"Title: {title}" if title else "",
                f"Description: {description}" if description else "",
            ),
        )
    )


def read_info(video: Path) -> dict:
    """yt-dlp's adjacent <stem>.info.json, or an empty mapping."""
    path = video.with_suffix(".info.json")
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def sidecars(video: Path) -> tuple[str, str]:
    """Return (hint text, human-caption path) derived from yt-dlp sidecar files."""
    info = read_info(video)
    if not info:
        return "", ""
    language = manual_english(info)
    reference = ""
    if language:
        for extension in (".vtt", ".srt"):
            candidate = video.with_name(f"{video.stem}.{language}{extension}")
            if candidate.is_file():
                reference = str(candidate)
                break
    return hints(info), reference


def page_info(info: dict) -> dict:
    """The small public subset the HTML page displays."""
    keys = ("id", "title", "webpage_url", "uploader", "upload_date", "duration")
    data = {key: info[key] for key in keys if info.get(key)}
    if info.get("description"):
        data["description"] = info["description"]
    data["manual_english_captions"] = bool(manual_english(info))
    return data
