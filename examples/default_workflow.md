# Default Workflow — Worked Example

> Version: v1 · 2026-07-17
> Validation: A correctly named `.ass` file appearing in the target video directory constitutes a successful mount.

---

## 1. Scenario

This case study demonstrates a complete subtitle-bridge operation: extract a subtitle track from a streaming release and attach it beside a BD target video.

### 1.1 Inputs

**Target video** (user-supplied BD resource):

```
<BANGUMI_DIR>/
├── [<RELEASE_GROUP>][<TITLE>][<EP>][1080P][BDRip][HEVC-10bit][FLAC][MKV]
└── ...
```

**Subtitle source** (auto-located streaming release):

```
<BANGUMI_DIR>/
├── [<SUBGROUP>] <TITLE> [01-24][WebRip 1080p HEVC-10bit AAC][SRTx2]
└── ...
```

### 1.2 Key Dependencies

| Dependency | Path |
|---|---|
| `<FFMPEG_BIN>` | Absolute path to `ffmpeg` executable |
| `<FFPROBE_BIN>` | Absolute path to `ffprobe` executable |

---

## 2. Execution Steps

### 2.1 Probe Subtitle Source

Call `ffprobe` to enumerate all streams of the subtitle source file:

```python
def ffprobe_streams(video_path: str) -> list:
    """Return all stream objects from a video file."""
    ffprobe = '<FFPROBE_BIN>'
    cmd = [ffprobe, '-v', 'error', '-show_streams', '-of', 'json', video_path]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    return json.loads(result.stdout)['streams']
```

Output example (streaming release, episode 1):
```
[0] video      hevc
[1] audio      aac     lang=jpn
[2] subtitle   subrip  lang=chi  title=简体    ← [Chinese subtitle sample]
[3] subtitle   subrip  lang=chi  title=繁体    ← [Chinese subtitle sample]
```

### 2.2 Select Best Subtitle Track

Select the highest-priority track by matching literal source tags against the stream's `tags.title` field:

| Candidate | Subtitle Type | Priority |
|---|---|---|
| Stream 2 (Simplified Chinese) | subrip / `简体` | B tier (Chinese only) |
| Stream 3 (Traditional Chinese) | subrip / `繁体` | C tier |

This example selects stream 2 (Simplified Chinese).

### 2.3 Extract and Convert to ASS

```python
def extract_subtitle_to_ass(video_path: str, subtitle_stream_index: int, output_ass: str):
    """Extract a subtitle track and convert it to ASS while preserving source styles."""
    ffmpeg = '<FFMPEG_BIN>'
    cmd = [
        ffmpeg, '-y',
        '-i', video_path,
        '-map', f'0:s:{subtitle_stream_index}',
        '-c:s', 'ass',
        output_ass
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f'ffmpeg failed: {result.stderr[:500]}')
    return output_ass
```

Output: 37.9 KB ASS file.

```ass
[Script Info]
ScriptType: v4.00+
PlayResX: 384
PlayResY: 288

[V4+ Styles]
Style: Default, Arial, 16, &Hffffff, ...

[Events]
Dialogue: 0,0:00:11.20,0:00:13.12,Default,,0,0,0,,[Chinese subtitle sample]
...
```

### 2.4 Mount to Target Video Directory

Rename the ASS file to match the target video's stem and copy it to the same directory:

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

Mount result:

```
<BANGUMI_DIR>/
├── [<RELEASE_GROUP>][<TITLE>][<EP>][1080P][BDRip][HEVC-10bit][FLAC][MKV]   # original
└── [<RELEASE_GROUP>][<TITLE>][<EP>][1080P][BDRip][HEVC-10bit][FLAC].ass    # mounted
```

---

## 3. Validation

### 3.1 File Existence Check

```bash
ls -la <BANGUMI_DIR>/<target_video_stem>.ass
```

Expected: an `.ass` file whose name matches the target video stem.

### 3.2 ASS Format Legality

```python
from pathlib import Path

ass_path = '<BANGUMI_DIR>/<target_video_stem>.ass'
content = Path(ass_path).read_text(encoding='utf-8')

assert '[Script Info]' in content
assert '[V4+ Styles]' in content
assert '[Events]' in content
assert 'Dialogue:' in content
```

### 3.3 Player Auto-Load Verification

Open the target video in PotPlayer and confirm that the subtitle is loaded automatically and displayed correctly.

---

## 4. Generalization Notes

### 4.1 Placeholders

| Placeholder | Meaning | Example |
|---|---|---|
| `<TARGET_DIR>` | Target video directory | `<BANGUMI_DIR>/anime_BD` |
| `<STREAM_DIR>` | Subtitle source directory | `<BANGUMI_DIR>/anime_WebRip` |
| `<RELEASE_GROUP>` | Target video release group | `[<GROUP>]` |
| `<SUBGROUP>` | Streaming release subtitle group | `[<GROUP>]` |
| `<TITLE>` | Anime title | `<TITLE>` |
| `<EP>` | Episode number | `01` |

### 4.2 Reuse Steps

1. Replace placeholders with concrete values for the target anime.
2. Call `ffprobe` to select the best subtitle track.
3. Call `ffmpeg` to extract and convert to ASS.
4. Call `mount_ass_to_target` to copy beside the target video.
5. Validate that the `.ass` file exists and its format is legal.

### 4.3 Scope Limitations

This worked example demonstrates a single-episode mount. Batch processing across all episodes requires looping over `mount_ass_to_target` for each episode pair.

---

## 5. Known Issues

- When the subtitle source is SRT, `ffmpeg` adds a default ASS `Style` block (e.g. `Arial 16`) that may not match the target video's canvas resolution. Use Aegisub or a similar editor if precise style control is needed.
- If the ASS file references external fonts via `{\fn...}` tags, the corresponding font files must be placed in the target video directory; otherwise PotPlayer falls back to a default font at render time.