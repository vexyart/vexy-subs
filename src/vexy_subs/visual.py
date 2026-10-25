# this_file: src/vexy_subs/visual.py
"""Shot boundaries, per-shot visual measurements and timestamped keyframes.

Detection transplants reelpack's adaptive histogram/edge/pixel selector (with its
talking-head guard) and framecheck's sparse-flow motion estimate. Frames are
decoded through an FFmpeg raw pipe at proxy size; keyframes come from the source.
"""

import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path

from . import __version__
from .io import save, sha256

PROXY_WIDTH = 256
MOTION_INTERVAL = 0.5
MIN_SHOT_SECONDS = 0.4
KEYFRAME_OFFSET = 0.25
KEYFRAME_THRESHOLD = 0.03
CHANGE_AREA = 0.06
CHANGE_PIXEL = 0.08
MIN_SEGMENT_SECONDS = 2.0
THUMB_SIZE = (64, 36)


def libraries():
    try:
        import cv2
        import numpy
    except ImportError as exc:
        raise RuntimeError(
            "Visual analysis needs OpenCV and NumPy: install the 'video' extra, "
            "e.g. uv tool install 'vexy-subs[apple,cluster,video,youtube]'"
        ) from exc
    return cv2, numpy


def probe_video(path: Path) -> dict:
    data = json.loads(
        subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=width,height,avg_frame_rate:format=duration",
                "-of",
                "json",
                str(path),
            ],
            timeout=60,
        )
    )
    stream = data["streams"][0]
    top, bottom = stream["avg_frame_rate"].split("/")
    fps = float(top) / float(bottom or 1)
    if not (stream["width"] and stream["height"] and math.isfinite(fps) and fps > 0):
        raise ValueError(f"No decodable video stream in {path.name}")
    return {
        "width": stream["width"],
        "height": stream["height"],
        "fps": fps,
        "duration": float(data["format"]["duration"]),
    }


def frames(path: Path, width: int, height: int):
    """Yield BGR proxy frames in decode order; never holds more than one frame."""
    _, np = libraries()
    command = [
        "ffmpeg",
        "-nostdin",
        "-v",
        "error",
        "-i",
        str(path),
        "-map",
        "0:v:0",
        "-vf",
        f"scale={width}:{height}:flags=area",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "bgr24",
        "pipe:1",
    ]
    process = subprocess.Popen(command, stdout=subprocess.PIPE)
    size = width * height * 3
    try:
        while len(data := process.stdout.read(size)) == size:
            yield np.frombuffer(data, np.uint8).reshape(height, width, 3)
        if process.wait() != 0:
            raise RuntimeError(f"FFmpeg could not decode {path.name}")
    finally:
        process.stdout.close()
        if process.poll() is None:
            process.kill()
        process.wait()


def features(previous, current) -> tuple[float, float, float]:
    """Histogram distance, edge-change ratio and mean pixel change (reelpack)."""
    cv2, np = libraries()
    a, b = previous, current
    edges = b["edges"] > 0
    old = a["edges"] > 0
    ecr = max(
        float((edges & (a["dilated"] == 0)).sum() / max(edges.sum(), 1)),
        float((old & (b["dilated"] == 0)).sum() / max(old.sum(), 1)),
    )
    histogram = cv2.compareHist(b["hist"], a["hist"], cv2.HISTCMP_CHISQR_ALT) / 4
    pixel = float(np.abs(b["image"] - a["image"]).mean() / 255)
    return float(histogram), ecr, pixel


def describe(image) -> dict:
    cv2, np = libraries()
    small = image.astype(np.float32)
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    hist = cv2.calcHist([hsv], [0, 1, 2], None, [16, 8, 8], [0, 180, 0, 256, 0, 256])
    hist /= max(float(hist.sum()), 1)
    edges = cv2.Canny(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY), 70, 140)
    dilated = cv2.dilate(edges, np.ones((3, 3), np.uint8))
    return {"image": small, "hist": hist, "edges": edges, "dilated": dilated}


def select_cuts(scores: list, fps: float, min_shot: float = MIN_SHOT_SECONDS) -> list:
    """Adaptive local threshold; ignore edge/colour twitches of a talking head."""
    _, np = libraries()
    f = np.asarray(scores, dtype=float)
    if len(f) < 3:
        return []
    combined = 0.5 * f[:, 0] + 0.3 * f[:, 1] + 0.2 * f[:, 2]
    base = combined[combined <= np.percentile(combined, 80)]
    floor = max(0.045, float(base.mean() + 3 * base.std()))
    radius = max(2, round(fps * 0.6))
    candidates = []
    for i in range(1, len(combined)):
        local = combined[max(1, i - radius) : i + radius + 1]
        quiet = local[local <= np.percentile(local, 70)]
        limit = max(floor, float(quiet.mean() + 3 * quiet.std()))
        if combined[i] < limit or combined[i] < combined[max(1, i - 2) : i + 3].max():
            continue
        if f[i, 2] < 0.035 or (f[i, 0] < 0.055 and f[i, 2] < 0.14):
            continue
        candidates.append((i, float(combined[i]), float(combined[i] / limit)))
    gap = max(2, round(fps * min_shot))
    chosen = []
    for cut in sorted(candidates, key=lambda c: -c[1]):
        if all(abs(cut[0] - other[0]) >= gap for other in chosen):
            chosen.append(cut)
    return sorted(chosen)


def motion(previous, current, elapsed: float) -> dict:
    """framecheck's RANSAC similarity fit on tracked corners; 2D image motion only."""
    cv2, _ = libraries()
    a, b = (cv2.cvtColor(x, cv2.COLOR_BGR2GRAY) for x in (previous, current))
    points = cv2.goodFeaturesToTrack(
        a, maxCorners=200, qualityLevel=0.01, minDistance=6
    )
    if points is None or len(points) < 12:
        return {"valid": False}
    moved, status, _ = cv2.calcOpticalFlowPyrLK(a, b, points, None)
    good = status.ravel() == 1
    if good.sum() < 12:
        return {"valid": False}
    matrix, mask = cv2.estimateAffinePartial2D(
        points[good], moved[good], method=cv2.RANSAC, ransacReprojThreshold=2.0
    )
    if matrix is None or mask is None or mask.mean() < 0.6:
        return {"valid": False}
    height, width = a.shape
    scale = math.hypot(matrix[0, 0], matrix[1, 0])
    if not 0.75 < scale < 1.3:
        return {"valid": False}
    return {
        "valid": True,
        "x": float(matrix[0, 2] / width * 100 / elapsed),
        "y": float(matrix[1, 2] / height * 100 / elapsed),
        "zoom": float(math.log(scale) * 100 / elapsed),
    }


def summarize(samples: list) -> str:
    """static / pan / tilt / zoom / mixed / uncertain from the median motion."""
    _, np = libraries()
    valid = [s for s in samples if s["valid"]]
    if len(valid) < 2 or len(valid) < len(samples) / 2:
        return "uncertain"
    values = np.array([[s["x"], s["y"], s["zoom"]] for s in valid])
    median, strength = np.median(values, axis=0), np.median(np.abs(values), axis=0)
    active = np.flatnonzero(strength > np.array([1.5, 1.5, 2.0]))
    if not len(active):
        return "static"
    if len(active) > 1 or abs(median[active[0]]) < strength[active[0]] * 0.5:
        return "mixed"
    names = (
        ("pan_right", "pan_left"),
        ("tilt_down", "tilt_up"),
        ("zoom_out", "zoom_in"),
    )
    return names[active[0]][int(median[active[0]] > 0)]


def scan(path: Path, info: dict, min_shot: float = MIN_SHOT_SECONDS) -> tuple:
    """One decode pass: cut features per frame; motion and thumbnails every 0.5 s."""
    width = PROXY_WIDTH
    height = max(2, round(width * info["height"] / info["width"] / 2) * 2)
    step = max(1, round(info["fps"] * MOTION_INTERVAL))
    scores, samples, thumbs = [], [], []
    previous = anchor = None
    count = 0
    for count, image in enumerate(frames(path, width, height), 1):
        current = describe(image)
        scores.append(
            (0.0, 0.0, 0.0) if previous is None else features(previous, current)
        )
        previous = current
        if (count - 1) % step == 0:
            if anchor is not None:
                samples.append(
                    (anchor[0], count - 1, motion(anchor[1], image, step / info["fps"]))
                )
            anchor = (count - 1, image.copy())
            thumbs.append((count - 1, thumb(image)))
        if count % 20000 == 0:
            print(f"VISUAL {path.name}: {count} frames", file=sys.stderr, flush=True)
    if not count:
        raise ValueError(f"No video frames decoded from {path.name}")
    cuts = select_cuts(scores, info["fps"], min_shot)
    return (
        cuts,
        changes(thumbs, [c[0] for c in cuts], count, info["fps"]),
        samples,
        count,
    )


def thumb(image):
    """Blurred 64×36 greyscale in 0..1 for content-change comparison."""
    cv2, np = libraries()
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    small = cv2.resize(gray, THUMB_SIZE, interpolation=cv2.INTER_AREA)
    return cv2.GaussianBlur(small, (3, 3), 0).astype(np.float32) / 255


def changed(a, b) -> float:
    """Share of the frame whose brightness moved by more than CHANGE_PIXEL."""
    _, np = libraries()
    return float((np.abs(a - b) > CHANGE_PIXEL).mean())


def changes(thumbs: list, cuts: list, count: int, fps: float) -> dict[int, int]:
    """In-shot content changes (slides, dissolves, reframing) that then hold still.

    Maps each change onset frame to the frame where the new view has settled,
    so head keyframes never land inside a dissolve.
    """
    edges = [0, *cuts, count]
    gap = MIN_SEGMENT_SECONDS * fps
    found, anchor, last = {}, None, 0
    for k, (frame, image) in enumerate(thumbs):
        shot = max(i for i, edge in enumerate(edges[:-1]) if edge <= frame)
        start, end = edges[shot], edges[shot + 1]
        if anchor is None or anchor[0] < start:
            anchor, last = (frame, image), max(last, start)
            continue
        if k + 2 >= len(thumbs) or thumbs[k + 2][0] >= end:
            continue
        if (
            changed(image, anchor[1]) > CHANGE_AREA
            and frame - last >= gap
            and end - frame >= gap
        ):
            stop = k
            while (
                stop + 1 < min(len(thumbs), k + 8)
                and thumbs[stop + 1][0] < end
                and changed(thumbs[stop + 1][1], thumbs[stop][1]) >= CHANGE_AREA / 4
            ):
                stop += 1
            if (
                stop + 1 < len(thumbs)
                and changed(thumbs[stop + 1][1], thumbs[stop][1]) < CHANGE_AREA / 2
            ):
                # Walk back to the last still view, so the previous tail precedes a fade.
                onset = k
                while (
                    k - onset < 8
                    and thumbs[onset - 1][0] > last
                    and changed(thumbs[onset - 1][1], thumbs[onset][1])
                    >= CHANGE_AREA / 4
                ):
                    onset -= 1
                found[thumbs[onset][0]] = thumbs[stop][0]
                anchor, last = thumbs[stop], thumbs[onset][0]
    return found


def timecode(seconds: float) -> str:
    milliseconds = round(seconds * 1000)
    whole, fraction = divmod(milliseconds, 1000)
    return f"{whole // 3600:02}:{whole % 3600 // 60:02}:{whole % 60:02}.{fraction:03}"


def extract(path: Path, seconds: float, target: Path) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-nostdin",
            "-v",
            "error",
            "-y",
            "-ss",
            f"{seconds:.3f}",
            "-i",
            str(path),
            "-map",
            "0:v:0",
            "-frames:v",
            "1",
            "-q:v",
            "3",
            str(target),
        ],
        check=True,
        timeout=120,
    )
    if not target.is_file() or not target.stat().st_size:
        raise ValueError(f"No frame extracted at {seconds:.3f}s")


def difference(first: Path, second: Path) -> float:
    """Changed share of two keyframes, measured like in-shot content changes."""
    cv2, _ = libraries()
    a, b = (thumb(cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)) for p in (first, second))
    return changed(a, b)


def analyse(image_path: Path, faces) -> dict:
    """Coarse content description of one keyframe; heuristics, not recognition."""
    cv2, np = libraries()
    image = cv2.imread(str(image_path))
    small = cv2.resize(image, (160, 90), interpolation=cv2.INTER_AREA)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    scale = 480 / max(gray.shape)
    detected = faces.detectMultiScale(
        cv2.resize(gray, None, fx=scale, fy=scale),
        scaleFactor=1.1,
        minNeighbors=6,
        minSize=(24, 24),
    )
    area = sum(w * h for _, _, w, h in detected) / (
        gray.shape[0] * gray.shape[1] * scale * scale
    )
    pixels = small.reshape(-1, 3).astype(np.float32)
    _, labels, centres = cv2.kmeans(
        pixels,
        3,
        None,
        (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0),
        2,
        cv2.KMEANS_PP_CENTERS,
    )
    shares = np.bincount(labels.ravel(), minlength=3) / len(labels)
    order = np.argsort(-shares)
    palette = ["#" + "".join(f"{int(c):02x}" for c in centres[i][::-1]) for i in order]
    quantized = (small // 32).reshape(-1, 3)
    _, counts = np.unique(quantized, axis=0, return_counts=True)
    flat = float(counts.max() / len(quantized))
    hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
    if len(detected):
        kind = "close-up" if area > 0.06 else "person"
    else:
        kind = "graphic" if flat > 0.35 else "scene"
    return {
        "kind": kind,
        "faces": len(detected),
        "face_area": round(float(area), 4),
        "brightness": round(float(hsv[:, :, 2].mean() / 255), 3),
        "saturation": round(float(hsv[:, :, 1].mean() / 255), 3),
        "flat_share": round(flat, 3),
        "palette": palette,
        "palette_share": [round(float(shares[i]), 3) for i in order],
    }


def keyframe_times(
    first: int, last: int, fps: float, offset: float, settled: int = 0
) -> list[int]:
    """Frames a little after the cut (or settled change) and a little before the next."""
    gap = max(1, round(offset * fps))
    head, tail = max(first + gap, settled), last - 1 - gap
    if tail <= head:
        return [(first + last - 1) // 2]
    return [head, tail]


def run(
    video: str,
    output_dir: str = "",
    force: bool = False,
    min_shot: float = MIN_SHOT_SECONDS,
    keyframe_offset: float = KEYFRAME_OFFSET,
    keyframe_threshold: float = KEYFRAME_THRESHOLD,
) -> dict:
    """Detect shots, measure them and save timestamped head/tail keyframes."""
    cv2, _ = libraries()
    source = Path(video).resolve()
    if min_shot <= 0 or keyframe_offset < 0 or not 0 <= keyframe_threshold <= 1:
        raise ValueError(
            "Require positive min_shot, nonnegative offset, threshold 0..1"
        )
    folder = Path(output_dir).resolve() if output_dir else source.parent
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / f"{source.stem}.shots.json"
    settings = {
        "version": __version__,
        "input_sha256": sha256(source),
        "detector": "reelpack-adaptive-hist-ecr-pixel-v1+content-change-v3",
        "min_shot": min_shot,
        "keyframe_offset": keyframe_offset,
        "keyframe_threshold": keyframe_threshold,
    }
    key = hashlib.sha256(json.dumps(settings, sort_keys=True).encode()).hexdigest()
    if target.exists() and not force:
        old = json.loads(target.read_text())
        images = [folder / k["image"] for k in old["keyframes"]]
        if old.get("key") == key and all(p.is_file() for p in images):
            print(f"SKIP {source.name}: visual analysis verified", file=sys.stderr)
            return old
    info = probe_video(source)
    fps = info["fps"]
    print(f"VISUAL {source.name}", file=sys.stderr, flush=True)
    cuts, content, samples, count = scan(source, info, min_shot)
    starts = [0] + [c[0] for c in cuts]
    strength = {c[0]: round(c[2], 3) for c in cuts}
    images = folder / f"{source.stem}.keyframes"
    images.mkdir(exist_ok=True)
    for stale in images.glob("*.jpg"):
        stale.unlink()
    faces = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
    shots = []
    for number, first in enumerate(starts, 1):
        last = starts[number] if number < len(starts) else count
        moves = [m for a, b, m in samples if first <= a and b < last]
        shots.append(
            {
                "shot": number,
                "start": round(first / fps, 3),
                "end": round(last / fps, 3),
                "start_frame": first,
                "end_frame": last,
                "start_timecode": timecode(first / fps),
                "boundary_strength": strength.get(first),
                "motion": summarize(moves),
            }
        )
    bounds = sorted({*starts, *content})
    segments, keyframes = [], []
    for number, first in enumerate(bounds, 1):
        last = bounds[number] if number < len(bounds) else count
        shot = sum(start <= first for start in starts)
        chosen, paths = [], []
        for position, frame in zip(
            ("head", "tail"),
            keyframe_times(first, last, fps, keyframe_offset, content.get(first, 0)),
        ):
            seconds = frame / fps
            name = f"k{len(keyframes) + 1:05}-{timecode(seconds).replace(':', '-')}.jpg"
            extract(source, seconds, images / name)
            item = {
                "id": f"k{len(keyframes) + 1:05}",
                "segment": number,
                "shot": shot,
                "position": position,
                "frame": frame,
                "time": round(seconds, 3),
                "timecode": timecode(seconds),
                "image": f"{images.name}/{name}",
            }
            if paths:
                item["difference"] = round(difference(paths[0], images / name), 4)
                if item["difference"] < keyframe_threshold:
                    (images / name).unlink()
                    break
            chosen.append(item)
            paths.append(images / name)
            keyframes.append(item)
        segments.append(
            {
                "segment": number,
                "shot": shot,
                "boundary": "start"
                if not first
                else "cut"
                if first in strength
                else "change",
                "start": round(first / fps, 3),
                "end": round(last / fps, 3),
                "start_timecode": timecode(first / fps),
                "analysis": analyse(paths[0], faces),
                "keyframes": [k["id"] for k in chosen],
            }
        )
    data = {
        "key": key,
        "settings": settings,
        "source_filename": source.name,
        "video": info,
        "frames": count,
        "shots": shots,
        "segments": segments,
        "keyframes": keyframes,
        "limitations": [
            "Cuts are heuristic: dissolves, flashes and slide animations need review.",
            "Motion labels describe 2D image motion, not verified camera movement.",
            "Content kinds come from face detection and colour flatness heuristics.",
            "Times assume constant frame rate (frame index / average fps).",
        ],
    }
    save(target, data)
    print(
        f"DONE {source.name}: {len(shots)} shots, {len(segments)} segments, {len(keyframes)} keyframes",
        file=sys.stderr,
        flush=True,
    )
    return data
