# Anime-subtitle-exchange.SKILL — Technical Specification

> **Language policy.** English is the normative language of this document. Chinese text is retained only when it is a machine-matched subtitle tag, a proper name, a literal trigger alias, or a localized sample.
>
> **语言策略**：英文为主；中文仅用于机器匹配的字幕标签、专名、字面触发别名和本地化样例。

## 1. Overview

### 1.1 Background

High-quality anime releases — such as BD BDRips, REMUXes, and raw disc images — often lack external subtitle tracks. Streaming releases (WebRip / WEB-DL) more commonly include fansub tracks. This Skill bridges the two sources by extracting a subtitle track from the streaming release and attaching it to the target video.

### 1.2 Design Goals

- **Lossless.** Source subtitle styles and timecodes are preserved verbatim.
- **Compatible.** PotPlayer's same-name loading rule picks up the attached subtitle without manual configuration.
- **Portable.** Dependencies are limited to `ffmpeg` and the Python standard library.
- **Low overhead.** The Skill operates entirely on locally mounted paths (e.g. CloudDrive2 mounted to `L:`), avoiding round-trips to remote storage.

### 1.3 Scope

This Skill covers: subtitle-track discovery, track selection by priority model, ASS conversion, and same-name mounting.

This Skill does NOT cover: subtitle translation, subtitle editing, hard-subtitle OCR, or video transcoding.

## 2. Workflow

```
[1] Target video path
[2] Locate subtitle source under <BANGUMI_DIR>
[3] Probe subtitle streams via ffprobe
[4] Select the highest-priority track
[5] Extract the track and convert to ASS via ffmpeg
[6] Rename to <target_video_stem>.ass and copy beside the target video
[7] Player auto-loads via same-name matching
```

## 3. Trigger Words

**English (primary):** subtitle bridge, subtitle mounting, subtitle extraction, subtitle transfer.

**Chinese (literal aliases, required for exact-match trigger detection):** 字幕桥接、字幕挂载、字幕提取、字幕搬家、字幕互通.

## 4. Subtitle Type Priority

The following literal source tags are matched against the subtitle stream's `tags.title` field. Tags MUST be retained verbatim because they are emitted by fansub groups and consumed by the matcher.

| Tier | Literal source tags (preserve) | Interpretation |
|---|---|---|
| S | `简日双语`, `繁日双语`, `简繁日内封`, `简繁日内封字幕` | Simplified / Traditional Chinese + Japanese (external) |
| A | `简日内嵌`, `繁日内嵌` | Simplified / Traditional Chinese + Japanese (muxed-in) |
| B | `简繁内封`, `简繁内封字幕` | Chinese only (external) |
| C | `简体内嵌`, `繁体内嵌` | Chinese only (muxed-in) |

The full source-tag dictionary is part of the Skill's internal implementation and is intentionally not enumerated in the public specification.

## 5. Subtitle Group Priority

The internal priority model for fansub groups is intentionally **not published** in this specification. The ranking would invite community friction between groups and adds no actionable information for users invoking the Skill. The implementation lives in `bangumi_magnet.py`'s `SUBGROUP_PRIORITY` constant and is consulted only when multiple candidate streams tie on type priority.

## 6. Naming Convention

- Output ASS file: `<target_video_stem>.ass`
- Location: same directory as the target video
- Player compatibility: PotPlayer loads via same-name matching

## 7. Failure Semantics

| Scenario | Strategy |
|---|---|
| Target video missing | Halt (precondition not met) |
| Subtitle source missing | Prompt user to switch source |
| Subtitle source is RAW | Prompt user to switch source (no subtitle track) |
| Subtitle source has hardcoded subtitles | Prompt user to switch source (OCR out of scope) |
| Duration mismatch > 30s | Emit warning, do not abort |
| Multiple candidates | List candidates and request user selection |
| `ffprobe` invocation failure | Emit error and skip current file |
| `ffmpeg` conversion failure | Preserve source file and report failure cause |

## 8. Limitations

This Skill does NOT perform:

- Video download
- Subtitle-style modification (source `Style` blocks and timecodes are preserved)
- Hardcoded-subtitle OCR
- Target video re-muxing or transcoding
- Web crawling for subtitle sources
- Auto-collection of external fonts referenced by ASS `{\fn...}` tags

## 9. Dependencies

| Dependency | Version | Purpose |
|---|---|---|
| `ffmpeg` | 7.0.2 or later | Video / subtitle processing |
| `ffprobe` | 7.0.2 or later | Stream information probe |
| Python | 3.8+ | Automation script runtime |
| Python standard library | bundled | `subprocess`, `shutil`, `re`, `json`, `pathlib` |

Path placeholders used throughout this specification:

- `<FFMPEG_BIN>` — absolute path to the `ffmpeg` executable
- `<FFPROBE_BIN>` — absolute path to the `ffprobe` executable
- `<BANGUMI_DIR>` — root directory holding target video and subtitle sources

## 10. Cross-Platform Notes

- **Windows**: use absolute paths in `r'C:\path\to\bin\ffmpeg.exe'` form
- **macOS / Linux**: use `/usr/local/bin/ffmpeg` or `which ffmpeg` to locate

## 11. Project Structure

```
Anime-subtitle-exchange.SKILL/
├── SKILL.md                  # Trigger prompt + abstract (this file)
├── README.md                 # Technical documentation
└── examples/
    └── default_workflow.md   # Worked example
```

## 12. See Also

- Full technical documentation: `README.md`
- Worked example: `examples/default_workflow.md`