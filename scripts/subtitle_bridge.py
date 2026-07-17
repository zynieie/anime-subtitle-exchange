#!/usr/bin/env python3
"""Subtitle Bridge -- Extract and mount subtitles from streaming releases to BD videos.

This is the main entry point that orchestrates the full subtitle bridging
workflow:

  1. Probe subtitle streams from the subtitle source.
  2. Select the highest-priority subtitle track.
  3. Extract and convert to ASS format via ffmpeg.
  4. Mount the ASS file beside the target video for player auto-loading.

Functions:
    subtitle_bridge: Execute the full bridge workflow.

CLI Usage:
    python scripts/subtitle_bridge.py <target_video> <subtitle_source> [--ffmpeg-bin PATH]

Dependencies:
    - ffmpeg/ffprobe (external binaries)
    - Python 3.8+ standard library
"""

import argparse
import os
import sys
import tempfile
from pathlib import Path

# Ensure project root is in path for sibling module imports when executed
# as a standalone script rather than via the installed entry point.
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from scripts.extract_subtitle import (
    ffprobe_streams,
    choose_best_subtitle,
    extract_subtitle_to_ass,
)
from scripts.mount_ass import mount_ass_to_target


def subtitle_bridge(target_video, subtitle_source, ffmpeg_bin=None):
    """Execute the full subtitle bridge workflow.

    Steps:
      1. Probe subtitle streams from subtitle_source via ffprobe.
      2. Select the best subtitle track by priority model.
      3. Extract the track to a temporary ASS file via ffmpeg.
      4. Copy the ASS file beside target_video with the same-name convention.

    Args:
        target_video: Path to the target video (e.g. BD / REMUX release).
        subtitle_source: Path to the subtitle-bearing source video
                         (e.g. WebRip / WEB-DL release).
        ffmpeg_bin: Path to ffmpeg executable.  If None, uses FFMPEG_BIN env
                    var or falls back to 'ffmpeg' on PATH.

    Returns:
        Dictionary containing workflow results:
          mounted_path  -- Path to the mounted ASS file.
          stream_index  -- Subtitle-relative index of the extracted track.
          source_title  -- Title tag of the selected stream (or 'N/A').

    Raises:
        FileNotFoundError: If target_video or subtitle_source does not exist.
        RuntimeError: If no subtitle streams are found or ffmpeg fails.
    """
    target = Path(target_video)
    source = Path(subtitle_source)

    if not target.is_file():
        raise FileNotFoundError("Target video not found: {}".format(target_video))
    if not source.is_file():
        raise FileNotFoundError("Subtitle source not found: {}".format(subtitle_source))

    # Step 1: Probe subtitle streams
    streams = ffprobe_streams(str(source), ffmpeg_bin)
    subtitle_streams = [s for s in streams if s.get("codec_type") == "subtitle"]

    if not subtitle_streams:
        raise RuntimeError("No subtitle streams found in: {}".format(subtitle_source))

    # Step 2: Select best subtitle track (subtitle-relative index)
    best_index = choose_best_subtitle(streams, source.name)

    # Resolve the selected stream's title for reporting
    source_title = "N/A"
    if best_index is not None and best_index < len(subtitle_streams):
        source_title = subtitle_streams[best_index].get("tags", {}).get("title", "N/A")

    # Step 3: Extract to ASS via a temporary file
    fd, tmp_ass = tempfile.mkstemp(suffix=".ass")
    os.close(fd)

    try:
        extract_subtitle_to_ass(
            video_path=str(source),
            stream_index=best_index,
            output_ass=tmp_ass,
            ffmpeg_bin=ffmpeg_bin,
        )

        # Step 4: Mount to target
        mounted_path = mount_ass_to_target(str(target), tmp_ass)
    finally:
        # Clean up temporary file
        try:
            Path(tmp_ass).unlink()
        except OSError:
            pass

    return {
        "mounted_path": mounted_path,
        "stream_index": best_index,
        "source_title": source_title,
    }


def main():
    """Command-line entry point for subtitle bridge."""
    parser = argparse.ArgumentParser(
        description=(
            "Extract subtitles from a source video and mount them "
            "beside the target video."
        )
    )
    parser.add_argument(
        "target_video",
        help="Path to the target video (e.g. BD / REMUX release)",
    )
    parser.add_argument(
        "subtitle_source",
        help="Path to the subtitle-bearing source video (e.g. WebRip)",
    )
    parser.add_argument(
        "--ffmpeg-bin",
        default=None,
        help="Path to ffmpeg executable (overrides FFMPEG_BIN env var)",
    )

    args = parser.parse_args()

    try:
        result = subtitle_bridge(
            target_video=args.target_video,
            subtitle_source=args.subtitle_source,
            ffmpeg_bin=args.ffmpeg_bin,
        )
        print("Subtitle bridge completed successfully.")
        print("  Mounted:      {}".format(result["mounted_path"]))
        print("  Stream index: {}".format(result["stream_index"]))
        print("  Source title: {}".format(result["source_title"]))
    except (FileNotFoundError, RuntimeError) as e:
        print("Error: {}".format(e), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
