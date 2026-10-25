# this_file: tests/test_visual.py
"""Real FFmpeg-decoded synthetic video; deterministic shot and keyframe checks."""

import json
import subprocess

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("cv2")

from vexy_subs import page, visual


def make_video(path, colours=("red", "blue", "green"), seconds=2):
    inputs, filters = [], []
    for index, colour in enumerate(colours):
        inputs += ["-f", "lavfi", "-i", f"color=c={colour}:s=320x180:r=25:d={seconds}"]
        filters.append(f"[{index}:v]")
    subprocess.run(
        [
            "ffmpeg",
            "-nostdin",
            "-v",
            "error",
            "-y",
            *inputs,
            "-filter_complex",
            "".join(filters) + f"concat=n={len(colours)}:v=1:a=0[v]",
            "-map",
            "[v]",
            "-pix_fmt",
            "yuv420p",
            str(path),
        ],
        check=True,
    )


def test_run_when_colour_cuts_then_shots_and_one_keyframe_per_static_shot(tmp_path):
    video = tmp_path / "clip.mp4"
    make_video(video)
    data = visual.run(str(video), str(tmp_path / "out"))
    starts = [s["start"] for s in data["shots"]]
    assert starts == [0.0, 2.0, 4.0], f"Expected cuts at 2 s and 4 s, got {starts}"
    assert [k["position"] for k in data["keyframes"]] == ["head"] * 3, (
        "Identical head/tail frames of a static shot must collapse to the head"
    )
    first = data["keyframes"][0]
    assert first["timecode"] == "00:00:00.240" and first["frame"] == 6
    assert (tmp_path / "out" / first["image"]).is_file()
    assert data["segments"][1]["boundary"] == "cut"
    again = visual.run(str(video), str(tmp_path / "out"))
    assert again == data, "Unchanged input and settings must reuse the analysis"


def test_changes_when_view_switches_then_holds_then_reports_onset_and_settle():
    blank, slide = np.zeros((36, 64), np.float32), np.zeros((36, 64), np.float32)
    slide[:, :32] = 1.0
    thumbs = [(i * 12, blank) for i in range(10)] + [
        (i * 12, slide) for i in range(10, 20)
    ]
    found = visual.changes(thumbs, [], 240, 24)
    assert found == {108: 120}, (
        f"Onset at the last still view, settled at the switch: {found}"
    )
    moving = [(i * 12, np.roll(slide, i * 3, axis=1)) for i in range(20)]
    assert visual.changes(moving, [], 240, 24) == {}, "Continuous motion never settles"


def test_keyframe_times_when_short_or_settled_then_bounded():
    assert visual.keyframe_times(0, 5, 25, 0.25) == [2], (
        "Short shots get one middle frame"
    )
    assert visual.keyframe_times(0, 100, 25, 0.25) == [6, 93]
    assert visual.keyframe_times(0, 100, 25, 0.25, settled=30) == [30, 93]


def test_timecode_when_milliseconds_round_up_then_carries_seconds():
    assert visual.timecode(59.9996) == "00:01:00.000"
    assert visual.timecode(3723.25) == "01:02:03.250"


def test_page_when_cues_then_each_row_holds_cues_until_next_keyframe(tmp_path):
    video = tmp_path / "talk.mp4"
    make_video(video)
    visual.run(str(video), str(tmp_path))
    (tmp_path / "talk.vtt").write_text(
        "WEBVTT\n\n00:00:00.500 --> 00:00:01.500\nOpening <b>words</b>\n\n"
        "00:00:04.500 --> 00:00:05.000\nLast & final\n",
        encoding="utf-8",
    )
    written = page.write(video, tmp_path)
    text = written.read_text(encoding="utf-8")
    assert "basecoat-css@1.1.0" in text
    rows = text.split('<section class="row')[1:]
    assert (
        len(rows) == 3 and "Opening words" in rows[0] and "Last &amp; final" in rows[2]
    )
    assert "No subtitles in this interval." in rows[1]
    assert "talk.mp4#t=0.5" in rows[0], "Local videos link with media fragments"
    index = page.index(tmp_path, [video]).read_text(encoding="utf-8")
    assert 'href="talk.html"' in index


def test_page_when_youtube_info_then_links_to_watch_url(tmp_path):
    video = tmp_path / "abc.mp4"
    make_video(video, ("red",))
    (tmp_path / "abc.info.json").write_text(
        json.dumps(
            {
                "id": "abc",
                "title": "A <talk>",
                "webpage_url": "https://www.youtube.com/watch?v=abc",
                "upload_date": "20170405",
                "duration": 2,
                "subtitles": {},
            }
        )
    )
    visual.run(str(video), str(tmp_path))
    text = page.write(video, tmp_path).read_text(encoding="utf-8")
    assert "<title>A &lt;talk&gt;</title>" in text and "watch?v=abc&amp;t=0s" in text
    assert "2017-04-05" in text
