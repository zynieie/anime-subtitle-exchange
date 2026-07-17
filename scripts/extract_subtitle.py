#!/usr/bin/env python3
"""Extract subtitle tracks from video files and convert to ASS format.

This module provides functions for probing video streams, selecting the
best subtitle track by priority, and extracting it to ASS format using ffmpeg.

Functions:
    ffprobe_streams: Probe all streams from a video file.
    choose_best_subtitle: Select the highest-priority subtitle track.
    extract_subtitle_to_ass: Extract a subtitle track to ASS format.

CLI Usage:
    python scripts/extract_subtitle.py <video_path> --stream-index 0 --output output.ass

Dependencies:
    - ffmpeg/ffprobe (external binaries)
    - Python 3.8+ standard library
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def _resolve_ffprobe_path(ffmpeg_bin=None):
    """Derive ffprobe path from ffmpeg binary path.

    If ffmpeg_bin is provided, assumes ffprobe resides in the same directory.
    Otherwise falls back to FFMPEG_BIN environment variable, then to 'ffprobe'
    on the system PATH.

    Args:
        ffmpeg_bin: Path to ffmpeg executable, or None.

    Returns:
        Path string to the ffprobe executable.
    """
    if ffmpeg_bin is not None:
        ffmpeg_path = Path(ffmpeg_bin)
        ffprobe_name = "ffprobe.exe" if ffmpeg_path.suffix.lower() == ".exe" else "ffprobe"
        ffprobe_path = ffmpeg_path.parent / ffprobe_name
        return str(ffprobe_path)

    env_bin = os.environ.get("FFMPEG_BIN")
    if env_bin is not None:
        return _resolve_ffprobe_path(env_bin)

    return "ffprobe"


def ffprobe_streams(video_path, ffmpeg_bin=None):
    """Probe all stream objects from a video file.

    Invokes ffprobe with JSON output and parses the result into a list of
    stream dictionaries, each containing codec_type, index, tags, etc.

    Args:
        video_path: Path to the video file to probe.
        ffmpeg_bin: Path to ffmpeg executable. If None, uses FFMPEG_BIN env
                     var or falls back to 'ffprobe' on PATH.

    Returns:
        List of stream dictionaries as returned by ffprobe.

    Raises:
        FileNotFoundError: If the video file does not exist.
        RuntimeError: If ffprobe fails to execute or returns invalid JSON.
    """
    if not Path(video_path).is_file():
        raise FileNotFoundError("Video file not found: {}".format(video_path))

    ffprobe_bin = _resolve_ffprobe_path(ffmpeg_bin)
    cmd = [ffprobe_bin, "-v", "error", "-show_streams", "-of", "json", video_path]
    result = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )

    if result.returncode != 0:
        raise RuntimeError("ffprobe failed: {}".format(result.stderr[:500]))

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise RuntimeError("ffprobe returned invalid JSON: {}".format(e))

    return data.get("streams", [])


def choose_best_subtitle(streams, source_filename=""):
    """Return the subtitle-relative index of the highest-priority subtitle track.

    Selection logic:
      1. Filter streams by codec_type == 'subtitle'.
      2. Match stream tags.title against SUBTITLE_TYPE_PRIORITY in ascending
         priority order.
      3. Return the subtitle-relative index (0-based among subtitle streams)
         of the first match.
      4. Fall back to 0 (first subtitle stream) if no tags match.

    The literal source tags are preserved verbatim because they are emitted
    by fansub groups and consumed by the matcher.

    Args:
        streams: List of stream dictionaries from ffprobe.
        source_filename: Optional filename for logging context.

    Returns:
        Subtitle-relative index (0-based among subtitle streams) of the best
        subtitle track, or None if no subtitle streams are found.
    """
    subtitles = [s for s in streams if s.get("codec_type") == "subtitle"]

    if not subtitles:
        return None

    # Tier mapping: S=1-3, A=4-5, B=6, C=7-8, fallback=99
    SUBTITLE_TYPE_PRIORITY = {
        "简日双语": 1,
        "繁日双语": 2,
        "简繁日内封": 3,
        "简繁日内封字幕": 3,
        "简日内嵌": 4,
        "繁日内嵌": 5,
        "简繁内封": 6,
        "简繁内封字幕": 6,
        "简体内嵌": 7,
        "繁体内嵌": 8,
        "简体双语": 99,
    }

    for tag, _priority in sorted(SUBTITLE_TYPE_PRIORITY.items(), key=lambda x: x[1]):
        for i, sub in enumerate(subtitles):
            tags = sub.get("tags", {})
            if tag in tags.get("title", ""):
                return i

    # Fallback: return the first subtitle stream
    return 0


def extract_subtitle_to_ass(video_path, stream_index, output_ass, ffmpeg_bin=None):
    """Extract a subtitle track and convert it to ASS while preserving source styles.

    Uses ffmpeg to remux the specified subtitle stream into ASS format.  The
    source styles and timecodes are preserved verbatim.

    Args:
        video_path: Path to the source video file.
        stream_index: Subtitle-relative index (0-based among subtitle streams).
        output_ass: Path for the output ASS file.
        ffmpeg_bin: Path to ffmpeg executable. If None, uses FFMPEG_BIN env
                    var or falls back to 'ffmpeg' on PATH.

    Returns:
        Absolute path to the created ASS file.

    Raises:
        FileNotFoundError: If the video file does not exist.
        RuntimeError: If ffmpeg fails to execute.
    """
    if not Path(video_path).is_file():
        raise FileNotFoundError("Video file not found: {}".format(video_path))

    if ffmpeg_bin is None:
        ffmpeg_bin = os.environ.get("FFMPEG_BIN", "ffmpeg")

    cmd = [
        ffmpeg_bin,
        "-y",
        "-i", video_path,
        "-map", "0:s:{}".format(stream_index),
        "-c:s", "ass",
        output_ass,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError("ffmpeg failed: {}".format(result.stderr[:500]))

    return str(Path(output_ass).resolve())


def main():
    """Command-line entry point for subtitle extraction."""
    parser = argparse.ArgumentParser(
        description="Extract a subtitle track from a video file and convert to ASS."
    )
    parser.add_argument("video_path", help="Path to the source video file")
    parser.add_argument(
        "--stream-index",
        type=int,
        default=0,
        help="Subtitle stream index to extract, 0-based among subtitle streams (default: 0)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output ASS file path (default: <video_stem>.ass in current directory)",
    )
    parser.add_argument(
        "--ffmpeg-bin",
        default=None,
        help="Path to ffmpeg executable (overrides FFMPEG_BIN env var)",
    )

    args = parser.parse_args()

    if not Path(args.video_path).is_file():
        print("Error: Video file not found: {}".format(args.video_path), file=sys.stderr)
        sys.exit(1)

    output = args.output
    if output is None:
        output = Path(args.video_path).stem + ".ass"

    try:
        result_path = extract_subtitle_to_ass(
            video_path=args.video_path,
            stream_index=args.stream_index,
            output_ass=output,
            ffmpeg_bin=args.ffmpeg_bin,
        )
        print("Subtitle extracted: {}".format(result_path))
    except RuntimeError as e:
        print("Error: {}".format(e), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
