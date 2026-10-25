# this_file: src/vexy_subs/page.py
"""Static Basecoat UI pages: timestamped keyframes left, subtitles right."""

import html
import json
import os
from pathlib import Path

from . import youtube

BASECOAT = "https://cdn.jsdelivr.net/npm/basecoat-css@1.1.0/dist/basecoat.cdn.min.css"
STYLE = """
body{max-width:1280px;margin:0 auto;padding:1.5rem 1rem 4rem}
.top{position:sticky;top:0;z-index:5;background:var(--background);padding:.75rem 0;border-bottom:1px solid var(--border)}
.top h1{font-size:1.5rem;font-weight:650;line-height:1.2;margin:0 0 .35rem}
.meta{display:flex;flex-wrap:wrap;gap:.4rem;align-items:center;color:var(--muted-foreground);font-size:.875rem}
.row{display:grid;grid-template-columns:minmax(220px,40%) 1fr;gap:1.25rem;padding:1rem 0;border-bottom:1px solid var(--border)}
.row figure{margin:0;position:sticky;top:8.5rem;align-self:start}
.row img{width:100%;height:auto;border-radius:.5rem;border:1px solid var(--border);background:var(--muted)}
figcaption{display:flex;flex-wrap:wrap;gap:.35rem;align-items:center;margin-top:.4rem;font-size:.8rem}
.cue{margin:0 0 .55rem;line-height:1.5;padding-left:.65rem;border-left:3px solid var(--c,var(--border))}
.t{font-variant-numeric:tabular-nums;font-size:.75rem;color:var(--muted-foreground);text-decoration:none;margin-right:.4rem}
.t:hover{text-decoration:underline}
.who{font-size:.75rem;font-weight:600;margin-right:.35rem;color:var(--muted-foreground)}
.empty{color:var(--muted-foreground);font-style:italic;font-size:.875rem;text-align:left}
.row>div{text-align:left}
.row.silent{grid-template-columns:minmax(160px,22%) 1fr;padding:.5rem 0}
.hidden{display:none}
details{margin:.5rem 0 0;font-size:.875rem;color:var(--muted-foreground);white-space:pre-wrap}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:1rem}
.grid img{width:100%;border-radius:.5rem .5rem 0 0}
@media (max-width:720px){.row{grid-template-columns:1fr}.row figure{position:static}}
"""
SCRIPT = """
if(matchMedia('(prefers-color-scheme: dark)').matches)document.documentElement.classList.add('dark');
const q=document.getElementById('q');
if(q)q.addEventListener('input',()=>{const s=q.value.trim().toLowerCase();
document.querySelectorAll('.row').forEach(r=>{let any=!s;r.querySelectorAll('.cue').forEach(c=>{
const hit=!s||c.textContent.toLowerCase().includes(s);c.classList.toggle('hidden',!hit);any=any||hit});
r.classList.toggle('hidden',!any)})});
"""


def esc(text) -> str:
    return html.escape(str(text), quote=True)


def clock(seconds: float) -> str:
    whole = int(seconds)
    return f"{whole // 3600}:{whole % 3600 // 60:02}:{whole % 60:02}"


def load_cues(stem: Path, subtitles: str = "") -> list[dict]:
    """Prefer ASS (speaker styles and names), then WebVTT, then SubRip."""
    import pysubs2

    candidates = (
        [Path(subtitles)]
        if subtitles
        else [Path(str(stem) + ext) for ext in (".ass", ".vtt", ".srt")]
    )
    path = next((p for p in candidates if p.is_file()), None)
    if path is None:
        return []
    subs = pysubs2.load(str(path))
    result = []
    for event in subs.events:
        text = " ".join(event.plaintext.split())
        if not text or event.is_comment:
            continue
        style = subs.styles.get(event.style)
        colour = (
            f"#{style.primarycolor.r:02x}{style.primarycolor.g:02x}{style.primarycolor.b:02x}"
            if path.suffix == ".ass" and style and event.style != "Default"
            else ""
        )
        result.append(
            {
                "start": event.start / 1000,
                "end": event.end / 1000,
                "text": text,
                "speaker": event.name if path.suffix == ".ass" else "",
                "colour": colour,
            }
        )
    return result


def link(info: dict, video: Path, folder: Path, seconds: float) -> str:
    if info.get("webpage_url"):
        joiner = "&" if "?" in info["webpage_url"] else "?"
        return f"{info['webpage_url']}{joiner}t={int(seconds)}s"
    return f"{os.path.relpath(video, folder)}#t={seconds:.1f}"


def rows(data: dict, cues: list[dict], info: dict, video: Path, folder: Path) -> str:
    """One row per keyframe; cues starting before the next keyframe belong to it."""
    frames = data["keyframes"]
    segments = {s["segment"]: s for s in data.get("segments", [])}
    out = []
    for index, frame in enumerate(frames):
        start = 0.0 if index == 0 else frame["time"]
        end = frames[index + 1]["time"] if index + 1 < len(frames) else float("inf")
        mine = [c for c in cues if start <= c["start"] < end]
        segment = segments.get(frame.get("segment"), {})
        kind = segment.get("analysis", {}).get("kind", "")
        boundary = (
            segment.get("boundary", "") if frame["position"] == "head" else "later"
        )
        caption = (
            f'<a class="t" href="{esc(link(info, video, folder, frame["time"]))}" target="_blank">'
            f"{esc(frame['timecode'])}</a>"
            f'<span class="badge" data-variant="outline">shot {frame["shot"]}</span>'
            + (
                f'<span class="badge" data-variant="secondary">{esc(boundary)}</span>'
                if boundary
                else ""
            )
            + (
                f'<span class="badge" data-variant="outline">{esc(kind)}</span>'
                if kind
                else ""
            )
        )
        texts = (
            "".join(
                f'<p class="cue" style="--c:{esc(c["colour"] or "var(--border)")}">'
                f'<a class="t" href="{esc(link(info, video, folder, c["start"]))}" target="_blank">'
                f"{clock(c['start'])}</a>"
                + (
                    f'<span class="who">{esc(c["speaker"])}</span>'
                    if c["speaker"]
                    else ""
                )
                + f"{esc(c['text'])}</p>"
                for c in mine
            )
            or '<p class="empty">No subtitles in this interval.</p>'
        )
        out.append(
            f'<section class="row{"" if mine else " silent"}" id="{esc(frame["id"])}"><figure>'
            f'<img loading="lazy" src="{esc(frame["image"])}" alt="Keyframe at {esc(frame["timecode"])}">'
            f"<figcaption>{caption}</figcaption></figure><div>{texts}</div></section>"
        )
    return "\n".join(out)


def document(title: str, body: str) -> str:
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{esc(title)}</title>"
        f'<link rel="stylesheet" href="{BASECOAT}"><style>{STYLE}</style></head>'
        f"<body>{body}<script>{SCRIPT}</script></body></html>\n"
    )


def write(video: Path, folder: Path, subtitles: str = "") -> Path:
    """Write <stem>.html next to <stem>.shots.json; returns the page path."""
    stem = folder / video.stem
    data = json.loads(Path(str(stem) + ".shots.json").read_text(encoding="utf-8"))
    info = youtube.page_info(youtube.read_info(video))
    cues = load_cues(stem, subtitles)
    title = info.get("title") or video.stem
    date = info.get("upload_date", "")
    facts = [
        info.get("uploader", ""),
        f"{date[:4]}-{date[4:6]}-{date[6:]}" if len(date) == 8 else "",
        clock(data["video"]["duration"]),
    ]
    badges = "".join(
        f'<span class="badge" data-variant="secondary">{n} {label}</span>'
        for n, label in (
            (len(data["shots"]), "shots"),
            (len(data.get("segments", [])), "segments"),
            (len(data["keyframes"]), "keyframes"),
            (len(cues), "cues"),
        )
    )
    source = (
        f'<a class="btn" data-variant="outline" data-size="sm" href="{esc(info["webpage_url"])}" target="_blank">YouTube</a>'
        if info.get("webpage_url")
        else ""
    )
    description = (
        f"<details><summary>Description</summary>{esc(info['description'])}</details>"
        if info.get("description")
        else ""
    )
    body = (
        f'<header class="top"><h1>{esc(title)}</h1><div class="meta">'
        + " · ".join(esc(f) for f in facts if f)
        + f"{badges}{source}"
        + '<input id="q" class="input" type="search" placeholder="Filter subtitles…" '
        'style="max-width:16rem;margin-left:auto"></div>'
        + f"{description}</header><main>{rows(data, cues, info, video, folder)}</main>"
    )
    target = Path(str(stem) + ".html")
    target.write_text(document(title, body), encoding="utf-8")
    return target


def index(folder: Path, videos: list[Path]) -> Path:
    """A card per processed video, linking to its scan page."""
    cards = []
    for video in videos:
        stem = folder / video.stem
        data = json.loads(Path(str(stem) + ".shots.json").read_text(encoding="utf-8"))
        info = youtube.page_info(youtube.read_info(video))
        first = data["keyframes"][0]["image"] if data["keyframes"] else ""
        cards.append(
            f'<a class="card" href="{esc(video.stem)}.html" style="text-decoration:none;padding-top:0">'
            f'<img loading="lazy" src="{esc(first)}" alt="">'
            f"<header><h3>{esc(info.get('title') or video.stem)}</h3>"
            f"<p>{clock(data['video']['duration'])} · {len(data['keyframes'])} keyframes</p>"
            "</header></a>"
        )
    target = folder / "index.html"
    target.write_text(
        document(
            "Video scan index",
            f'<h1 class="text-2xl">Videos</h1><div class="grid">{"".join(cards)}</div>',
        ),
        encoding="utf-8",
    )
    return target
