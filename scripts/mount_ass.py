#!/usr/bin/env python3
"""Mount an ASS subtitle file beside a target video using the same-name rule.

This module copies an ASS file to the same directory as the target video,
renaming it to match the video's stem so that media players (e.g. PotPlayer)
can auto-load it via the same-name matching convention.

Functions:
    mount_ass_to_target: Copy ASS file beside the target video.

CLI Usage:
    python scripts/mount_ass.py <target_video> <ass_path>

Dependencies:
    - Python 3.8+ standard library (shutil, pathlib)
"""

import argparse
import shutil
import sys
from pathlib import Path


def mount_ass_to_target(target_video, ass_path):
    """Copy an ASS file beside the target video using the same-name rule.

    The ASS file is renamed to <target_video_stem>.ass and placed in the
    same directory as the target video, enabling PotPlayer auto-loading.

    Args:
        target_video: Path to the target video file.
        ass_path: Path to the source ASS file.

    Returns:
        Absolute path to the mounted ASS file.

    Raises:
        FileNotFoundError: If target_video or ass_path does not exist.
    """
    target = Path(target_video)
    source = Path(ass_path)

    if not target.is_file():
        raise FileNotFoundError("Target video not found: {}".format(target_video))
    if not source.is_file():
        raise FileNotFoundError("ASS file not found: {}".format(ass_path))

    dest = target.parent / "{}.ass".format(target.stem)
    shutil.copy(str(source), str(dest))
    return str(dest.resolve())


def main():
    """Command-line entry point for ASS mounting."""
    parser = argparse.ArgumentParser(
        description="Mount an ASS subtitle file beside a target video."
    )
    parser.add_argument("target_video", help="Path to the target video file")
    parser.add_argument("ass_path", help="Path to the ASS subtitle file")

    args = parser.parse_args()

    try:
        result_path = mount_ass_to_target(args.target_video, args.ass_path)
        print("Mounted: {}".format(result_path))
    except FileNotFoundError as e:
        print("Error: {}".format(e), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
