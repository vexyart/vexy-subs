---
name: vexy-subs-batch
description: Batch-subtitle a folder of videos, a YouTube video or playlist, or a text file of YouTube URLs with vexy-subs and yt-dlp, optionally adding shot keyframes and a scan page per video. Use when asked to transcribe, caption or "pack" several videos or a YouTube list.
---
<!-- this_file: skills/vexy-subs-batch/SKILL.md -->

# vexy-subs batch

Requires `vexy-subs[apple,cluster,video,youtube]` (or `audiocpp` setup) plus
FFmpeg/ffprobe. Check with `vexy-subs doctor`.

```bash
# A text file: one URL per line, # comments allowed; playlists expand in order.
vexy-subs batch urls.txt --output_dir=pack --download_dir=pack/sources --visual
vexy-subs batch "https://www.youtube.com/playlist?list=..." --output_dir=pack --visual
vexy-subs batch videos --pattern='*.mp4' --output_dir=pack --visual
```

What happens per video:

1. yt-dlp downloads `<id>.mp4` (≤1080p), `<id>.info.json` and only
   uploader-supplied English captions (`<id>.en*.vtt`). Automatic captions are
   never requested or used. Completed downloads are reused.
2. `<id>.hints.md` gets `Title:` and `Description:` lines (links, chapter stamps
   and hashtags removed, description capped). These reach every Qwen ASR chunk.
   With `--prompt_dir`, the user's own hint file is prepended.
3. A human caption file, when present, is passed as `--reference_file`; each 30 s
   ASR chunk sees only the caption text overlapping it.
4. Normal transcription, diarization, punctuation and beautification follow.
5. `--visual` adds shots, keyframes, `<stem>.shots.json` and `<stem>.html`, and
   writes `index.html` for the output folder.

A local folder works the same way when yt-dlp sidecars sit next to the videos.
Completed sets are verified and skipped; changed hints or references re-run ASR.
Failures are reported after the remaining videos have been attempted; rerun the
same command to resume. Progress goes to stderr, the JSON result to stdout.

Downloaded media, descriptions and transcripts are third-party content: keep them
outside public repositories. Do not claim speaker identities from titles;
use `--speaker_map` only after verifying who speaks.
