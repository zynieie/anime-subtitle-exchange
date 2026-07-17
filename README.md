# Anime-subtitle-exchange.SKILL — Technical Documentation

> **Language policy.** English is the normative language of this document. Chinese text is retained only when it is a machine-matched subtitle tag, a proper name, a literal trigger alias, or a localized sample.

## 1. Overview

This Skill extracts a subtitle track from a streaming release and places it beside a target video using PotPlayer's same-name loading rule. The target video and subtitle source may reside in different subdirectories under the same directory tree.

This workflow is particularly useful for mounted-drive environments — for example, a CloudDrive2 mount exposed as `L:` — because it avoids repeatedly transferring large video files over the network.

## 2. Trigger Keywords

**English (primary):** subtitle bridge, subtitle mounting, subtitle extraction, subtitle transfer, subtitle interoperability.

**Chinese (literal aliases, required for exact-match trigger detection):** 字幕桥接、字幕挂载、字幕提取、字幕搬家、字幕互通.

## 3. Applicable Scenarios

- The target video is a high-quality release such as BD, REMUX, or RAW that lacks an external subtitle file.
- A subtitle-bearing streaming release is available locally or on a mounted drive. Common source patterns include `WebRip`, `WEB-DL`, `ABEMA`, `B-Global`.

## 4. Workflow

```
[1] Enter the target video path
[2] Search for a matching streaming subtitle source locally or on a mounted drive
[3] Probe subtitle streams with ffprobe
[4] Select the highest-priority subtitle track
[5] Extract the track with ffmpeg and convert it to ASS
[6] Rename the ASS file to <target_video_stem>.ass and copy it beside the target video
[7] Report the mount result for automatic player loading
```

## 5. Subtitle Type Priority

The following literal source tags are matched against the subtitle stream's `tags.title` field. Tags MUST be retained verbatim because they are emitted by fansub groups and consumed by the matcher.

| Tier | Literal Source Tags (Preserve) | Interpretation |
|---|---|---|
| S | `简日双语`, `繁日双语`, `简繁日内封`, `简繁日内封字幕` | Chinese–Japanese bilingual external subtitles |
| A | `简日内嵌`, `繁日内嵌` | Chinese–Japanese bilingual muxed-in subtitles |
| B | `简繁内封`, `简繁内封字幕` | Chinese-only external subtitles |
| C | `简体内嵌`, `繁体内嵌` | Chinese-only muxed-in subtitles |

## 6. Subtitle-Group Priority

The internal priority model for fansub groups is **intentionally not published** in this specification. The ranking would invite community friction between groups and adds no actionable information for users invoking the Skill. The implementation lives in `bangumi_magnet.py`'s `SUBGROUP_PRIORITY` constant and is consulted only when multiple candidate streams tie on type priority.

## 7. Naming Rules

- The ASS file MUST use the name `<target_video_stem>.ass`.
- The ASS file MUST be placed in the same directory as the target video.
- PotPlayer SHOULD load the subtitle automatically through the same-name rule.

## 8. API Reference

### 8.1 `ffprobe_streams(video_path)`

Probe all stream objects of a video file.

```python
import subprocess, json

def ffprobe_streams(video_path: str) -> list:
    """Return all stream objects."""
    ffprobe = '<FFPROBE_BIN>'
    cmd = [ffprobe, '-v', 'error', '-show_streams', '-of', 'json', video_path]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    return json.loads(result.stdout)['streams']
```

### 8.2 `choose_best_subtitle(streams, source_filename)`

Return the index of the highest-priority subtitle track.

```python
def choose_best_subtitle(streams: list, source_filename: str) -> int:
    """Return the index of the highest-priority subtitle track."""
    subtitles = [s for s in streams if s['codec_type'] == 'subtitle']
    # Literal source tags MUST be preserved verbatim; they are matched
    # against the stream's `tags.title` field emitted by fansub groups.
    SUBTITLE_TYPE_PRIORITY = {
        '简日双语': 1,
        '繁日双语': 2,
        '简繁日内封': 3,
        '简繁日内封字幕': 3,
        '简日内嵌': 4,
        '繁日内嵌': 5,
        '简繁内封': 6,
        '简体双语': 99,
    }
    for st_name, st_prio in sorted(SUBTITLE_TYPE_PRIORITY.items(), key=lambda x: x[1]):
        for sub in subtitles:
            tags = sub.get('tags', {})
            if st_name in tags.get('title', ''):
                return sub['index']
    return subtitles[0]['index'] if subtitles else None
```

### 8.3 `extract_subtitle_to_ass(video_path, stream_index, output_ass)`

Extract a subtitle track to ASS while preserving source styles.

```python
def extract_subtitle_to_ass(video_path: str, stream_index: int, output_ass: str):
    """Extract a subtitle track to ASS while preserving source styles."""
    ffmpeg = '<FFMPEG_BIN>'
    cmd = [
        ffmpeg, '-y',
        '-i', video_path,
        '-map', f'0:s:{stream_index}',
        '-c:s', 'ass',
        output_ass
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f'ffmpeg failed: {result.stderr[:500]}')
    return output_ass
```

### 8.4 `mount_ass_to_target(target_video, ass_path)`

Copy an ASS file beside the target video using the same-name rule.

```python
import shutil
from pathlib import Path

def mount_ass_to_target(target_video: str, ass_path: str):
    """Copy an ASS file beside the target video using the same-name rule."""
    target_dir = Path(target_video).parent
    target_stem = Path(target_video).stem
    dest = target_dir / f'{target_stem}.ass'
    shutil.copy(ass_path, dest)
    return str(dest)
```

## 9. Failure Handling

| Scenario | Handling Strategy |
|---|---|
| Target video does not exist | Abort because the prerequisite is not satisfied. |
| Subtitle source does not exist | Ask the user to select another source. |
| Subtitle source is RAW | Ask the user to select another source because RAW releases generally contain no subtitle track. |
| Source contains hard subtitles | Ask the user to select another source because OCR is out of scope. |
| Duration difference exceeds 30 seconds | Emit a warning without blocking the workflow. |
| Multiple subtitle candidates exist | List the candidates and request a user selection. |
| `ffprobe` fails | Report the error and skip the current file. |
| `ffmpeg` conversion fails | Preserve the original file and report the failure reason. |

## 10. Known Limitations

- The source subtitle style is preserved verbatim and is not normalized.
- Hard-subtitle OCR is not supported.
- The target video is not re-muxed or transcoded.
- Subtitle sources are not automatically searched on the public network.
- External font files referenced by ASS `{\fn...}` tags are not collected automatically; the user must place required fonts beside the target video.

## 11. Dependencies

| Dependency | Version | Purpose |
|---|---|---|
| `ffmpeg` | 7.0.2 or later | Video / subtitle processing |
| `ffprobe` | 7.0.2 or later | Stream information probe |
| Python | 3.8+ | Automation script runtime |
| Python standard library | bundled | `subprocess`, `shutil`, `re`, `json`, `pathlib` |

Path placeholders:

- `<FFMPEG_BIN>` — absolute path to the `ffmpeg` executable.
- `<FFPROBE_BIN>` — absolute path to the `ffprobe` executable.
- `<BANGUMI_DIR>` — root directory holding target video and subtitle sources.

## 12. Cross-Platform Notes

- **Windows**: use absolute paths in `r'C:\path\to\bin\ffmpeg.exe'` form.
- **macOS / Linux**: use `/usr/local/bin/ffmpeg` or `which ffmpeg` to locate.

## 13. Project Layout

```
Anime-subtitle-exchange.SKILL/
├── SKILL.md                  # Trigger prompt + abstract
├── README.md                 # This document
└── examples/
    └── default_workflow.md   # Worked example
```

## 14. References

- Worked example and validation data: `examples/default_workflow.md`
- Trigger prompt: `SKILL.md`
- Subtitle type priority implementation: see `SUBTITLE_TYPE_PRIORITY` constant in the source code.