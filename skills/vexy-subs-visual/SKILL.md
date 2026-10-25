---
name: vexy-subs-visual
description: Detect shots and in-shot content changes in a video, save timestamped head/tail keyframes with simple visual analysis, and build a Basecoat HTML page with keyframes left and subtitles right. Use when asked for shot detection, keyframes, a visual index, or to illustrate a transcript quote with the matching frame.
---
<!-- this_file: skills/vexy-subs-visual/SKILL.md -->

# vexy-subs visual

Needs the `video` extra (OpenCV, NumPy) and FFmpeg. No models, no network.

```bash
vexy-subs visual talk.mp4 --output_dir=pack            # uses pack/talk.ass|vtt|srt
vexy-subs visual talk.mp4 --subtitles=other.vtt --force
```

Outputs in `--output_dir`:

- `<stem>.shots.json`: `shots` (camera cuts, motion label), `segments`
  (cuts plus in-shot `change` boundaries such as slide changes, with `analysis`:
  kind `close-up|person|graphic|scene`, faces, brightness, palette) and
  `keyframes` (`id`, `segment`, `shot`, `position` head/tail, `frame`, `time`,
  `timecode`, `image`).
- `<stem>.keyframes/kNNNNN-HH-MM-SS.mmm.jpg`: full-resolution frames taken
  `--keyframe_offset` seconds (default 0.25) after a cut, or after a change has
  settled, and the same distance before the next boundary. The tail is dropped
  when less than `--keyframe_threshold` (3%) of the frame differs from the head.
- `<stem>.html`: one row per keyframe; the right column holds the cues that start
  before the next keyframe. Timecodes link to YouTube `&t=` or `video.mp4#t=`.
  The search box filters cues. Works from `file://`.

Illustrating a quote: find the cue time in `<stem>.words.json` or the `.vtt`,
then take the last keyframe whose `time` is not later than the quote start
(or the segment containing it) from `shots.json`. Open the JPEG to confirm it
shows what you claim. Labels are heuristics: say "slide/graphic" or "speaker",
never identify people from faces.

Unchanged input and settings reuse `shots.json`; `--force` rebuilds. Dissolves,
flashes and animated slides can over- or under-split; inspect the page.
