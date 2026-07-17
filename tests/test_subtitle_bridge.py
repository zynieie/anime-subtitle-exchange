#!/usr/bin/env python3
"""Unit tests for the subtitle bridge skill.

All tests use mocking to avoid dependencies on real video files or ffmpeg
binaries.  Run with:  python -m pytest tests/ -v

Test cases:
    TestFfprobeStreams     -- mock ffprobe output, verify JSON parsing.
    TestChooseBestSubtitle -- verify priority selection logic.
    TestMountAssToTarget   -- verify file copy and naming.
    TestExtractSubtitleToAss -- verify ffmpeg command construction.
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Ensure project root is in path for imports
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from scripts.extract_subtitle import (
    ffprobe_streams,
    choose_best_subtitle,
    extract_subtitle_to_ass,
)
from scripts.mount_ass import mount_ass_to_target


# ---------------------------------------------------------------------------
# Test: ffprobe_streams
# ---------------------------------------------------------------------------
class TestFfprobeStreams(unittest.TestCase):
    """Test ffprobe_streams with mocked subprocess output."""

    @patch("scripts.extract_subtitle.subprocess.run")
    def test_ffprobe_streams_returns_stream_list(self, mock_run):
        """Verify that ffprobe_streams correctly parses JSON output."""
        mock_output = {
            "streams": [
                {"index": 0, "codec_type": "video", "codec_name": "hevc"},
                {"index": 1, "codec_type": "audio", "codec_name": "aac"},
                {
                    "index": 2,
                    "codec_type": "subtitle",
                    "codec_name": "subrip",
                    "tags": {"language": "chi", "title": "简体"},
                },
            ]
        }
        mock_run.return_value = MagicMock(
            returncode=0, stdout=json.dumps(mock_output), stderr=""
        )

        with tempfile.NamedTemporaryFile(suffix=".mkv", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            result = ffprobe_streams(tmp_path, ffmpeg_bin="/usr/bin/ffmpeg")
            self.assertEqual(len(result), 3)
            self.assertEqual(result[0]["codec_type"], "video")
            self.assertEqual(result[1]["codec_type"], "audio")
            self.assertEqual(result[2]["codec_type"], "subtitle")
            self.assertEqual(result[2]["tags"]["title"], "简体")
        finally:
            os.unlink(tmp_path)

    @patch("scripts.extract_subtitle.subprocess.run")
    def test_ffprobe_streams_raises_on_failure(self, mock_run):
        """Verify that RuntimeError is raised when ffprobe returns non-zero."""
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="No such file or directory"
        )

        with tempfile.NamedTemporaryFile(suffix=".mkv", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            with self.assertRaises(RuntimeError):
                ffprobe_streams(tmp_path, ffmpeg_bin="/usr/bin/ffmpeg")
        finally:
            os.unlink(tmp_path)

    @patch("scripts.extract_subtitle.subprocess.run")
    def test_ffprobe_streams_raises_on_invalid_json(self, mock_run):
        """Verify that RuntimeError is raised on malformed JSON output."""
        mock_run.return_value = MagicMock(
            returncode=0, stdout="not valid json", stderr=""
        )

        with tempfile.NamedTemporaryFile(suffix=".mkv", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            with self.assertRaises(RuntimeError):
                ffprobe_streams(tmp_path, ffmpeg_bin="/usr/bin/ffmpeg")
        finally:
            os.unlink(tmp_path)

    def test_ffprobe_streams_raises_on_missing_file(self):
        """Verify that FileNotFoundError is raised for non-existent video."""
        with self.assertRaises(FileNotFoundError):
            ffprobe_streams("/nonexistent/video.mkv", ffmpeg_bin="/usr/bin/ffmpeg")


# ---------------------------------------------------------------------------
# Test: choose_best_subtitle
# ---------------------------------------------------------------------------
class TestChooseBestSubtitle(unittest.TestCase):
    """Test choose_best_subtitle priority selection logic."""

    def test_simplified_japanese_bilingual_highest_priority(self):
        """S-tier: 简日双语 should have highest priority."""
        streams = [
            {"index": 0, "codec_type": "video"},
            {"index": 1, "codec_type": "subtitle", "tags": {"title": "简体内嵌"}},
            {"index": 2, "codec_type": "subtitle", "tags": {"title": "简日双语"}},
        ]
        # 简日双语 is subtitle index 1 (second subtitle stream, 0-based among subtitles)
        self.assertEqual(choose_best_subtitle(streams), 1)

    def test_traditional_japanese_bilingual_over_lower_tier(self):
        """S-tier: 繁日双语 should be selected over B-tier."""
        streams = [
            {"index": 0, "codec_type": "subtitle", "tags": {"title": "简繁内封"}},
            {"index": 1, "codec_type": "subtitle", "tags": {"title": "繁日双语"}},
        ]
        # 繁日双语 is subtitle index 1
        self.assertEqual(choose_best_subtitle(streams), 1)

    def test_same_tier_first_match_wins(self):
        """When both streams match the same tag, the first one in iteration order wins."""
        streams = [
            {"index": 0, "codec_type": "subtitle", "tags": {"title": "简繁日内封"}},
            {"index": 1, "codec_type": "subtitle", "tags": {"title": "简繁日内封字幕"}},
        ]
        # Both match tier 3 via "简繁日内封" (substring match).
        # The first subtitle stream (index 0) is checked first.
        self.assertEqual(choose_best_subtitle(streams), 0)

    def test_fallback_to_first_subtitle_when_no_tags_match(self):
        """When no tags match, return 0 (first subtitle stream)."""
        streams = [
            {"index": 0, "codec_type": "video"},
            {"index": 1, "codec_type": "subtitle", "tags": {"title": "Unknown"}},
            {"index": 2, "codec_type": "subtitle", "tags": {"title": "Another"}},
        ]
        self.assertEqual(choose_best_subtitle(streams), 0)

    def test_no_subtitles_returns_none(self):
        """Return None when no subtitle streams exist."""
        streams = [
            {"index": 0, "codec_type": "video"},
            {"index": 1, "codec_type": "audio"},
        ]
        self.assertIsNone(choose_best_subtitle(streams))

    def test_empty_streams_returns_none(self):
        """Return None for an empty stream list."""
        self.assertIsNone(choose_best_subtitle([]))

    def test_subtitle_relative_index_not_absolute(self):
        """Verify the returned index is relative to subtitle streams, not absolute."""
        streams = [
            {"index": 0, "codec_type": "video"},
            {"index": 1, "codec_type": "audio"},
            {"index": 2, "codec_type": "subtitle", "tags": {"title": "简体内嵌"}},
            {"index": 3, "codec_type": "subtitle", "tags": {"title": "简日双语"}},
        ]
        # 简日双语 is absolute index 3, but subtitle-relative index 1
        self.assertEqual(choose_best_subtitle(streams), 1)


# ---------------------------------------------------------------------------
# Test: mount_ass_to_target
# ---------------------------------------------------------------------------
class TestMountAssToTarget(unittest.TestCase):
    """Test mount_ass_to_target file copy and naming."""

    def test_creates_correctly_named_file(self):
        """Verify ASS file is copied with target video stem name."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_video = os.path.join(tmpdir, "[BD] Anime [01][1080P].mkv")
            ass_source = os.path.join(tmpdir, "source_sub.ass")

            Path(target_video).touch()
            Path(ass_source).write_text(
                "[Script Info]\nTitle: Test\n", encoding="utf-8"
            )

            result = mount_ass_to_target(target_video, ass_source)

            expected = os.path.join(tmpdir, "[BD] Anime [01][1080P].ass")
            self.assertTrue(Path(expected).exists())
            self.assertEqual(Path(result).resolve(), Path(expected).resolve())

            # Verify content was copied
            content = Path(expected).read_text(encoding="utf-8")
            self.assertIn("[Script Info]", content)

    def test_overwrites_existing_ass(self):
        """Verify that an existing ASS file is overwritten."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_video = os.path.join(tmpdir, "video.mkv")
            ass_source = os.path.join(tmpdir, "new.ass")
            existing_ass = os.path.join(tmpdir, "video.ass")

            Path(target_video).touch()
            Path(ass_source).write_text("[New Content]", encoding="utf-8")
            Path(existing_ass).write_text("[Old Content]", encoding="utf-8")

            mount_ass_to_target(target_video, ass_source)

            content = Path(existing_ass).read_text(encoding="utf-8")
            self.assertEqual(content, "[New Content]")

    def test_raises_on_missing_target_video(self):
        """Verify FileNotFoundError when target video does not exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ass_source = os.path.join(tmpdir, "test.ass")
            Path(ass_source).touch()

            with self.assertRaises(FileNotFoundError):
                mount_ass_to_target("/nonexistent/video.mkv", ass_source)

    def test_raises_on_missing_ass_file(self):
        """Verify FileNotFoundError when ASS file does not exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_video = os.path.join(tmpdir, "video.mkv")
            Path(target_video).touch()

            with self.assertRaises(FileNotFoundError):
                mount_ass_to_target(target_video, "/nonexistent/sub.ass")


# ---------------------------------------------------------------------------
# Test: extract_subtitle_to_ass
# ---------------------------------------------------------------------------
class TestExtractSubtitleToAss(unittest.TestCase):
    """Test extract_subtitle_to_ass ffmpeg command construction."""

    @patch("scripts.extract_subtitle.subprocess.run")
    def test_constructs_correct_ffmpeg_command(self, mock_run):
        """Verify ffmpeg is invoked with the correct arguments."""
        mock_run.return_value = MagicMock(returncode=0, stderr="")

        with tempfile.NamedTemporaryFile(suffix=".mkv", delete=False) as tmp:
            video_path = tmp.name

        try:
            output = "/tmp/output.ass"
            result = extract_subtitle_to_ass(
                video_path=video_path,
                stream_index=1,
                output_ass=output,
                ffmpeg_bin="/usr/bin/ffmpeg",
            )

            mock_run.assert_called_once()
            cmd = mock_run.call_args[0][0]

            self.assertEqual(cmd[0], "/usr/bin/ffmpeg")
            self.assertIn("-y", cmd)
            self.assertEqual(cmd[cmd.index("-i") + 1], video_path)
            self.assertIn("0:s:1", cmd)
            self.assertIn("ass", cmd)
            self.assertIn(output, cmd)
        finally:
            os.unlink(video_path)

    @patch("scripts.extract_subtitle.subprocess.run")
    def test_raises_on_ffmpeg_failure(self, mock_run):
        """Verify RuntimeError when ffmpeg returns non-zero exit code."""
        mock_run.return_value = MagicMock(
            returncode=1, stderr="Conversion failed: invalid codec"
        )

        with tempfile.NamedTemporaryFile(suffix=".mkv", delete=False) as tmp:
            video_path = tmp.name

        try:
            with self.assertRaises(RuntimeError):
                extract_subtitle_to_ass(
                    video_path=video_path,
                    stream_index=0,
                    output_ass="/tmp/output.ass",
                    ffmpeg_bin="/usr/bin/ffmpeg",
                )
        finally:
            os.unlink(video_path)

    @patch("scripts.extract_subtitle.subprocess.run")
    def test_returns_resolved_output_path(self, mock_run):
        """Verify the returned path is an absolute, resolved path."""
        mock_run.return_value = MagicMock(returncode=0, stderr="")

        with tempfile.NamedTemporaryFile(suffix=".mkv", delete=False) as tmp:
            video_path = tmp.name

        with tempfile.TemporaryDirectory() as tmpdir:
            output = os.path.join(tmpdir, "test.ass")
            try:
                result = extract_subtitle_to_ass(
                    video_path=video_path,
                    stream_index=0,
                    output_ass=output,
                    ffmpeg_bin="/usr/bin/ffmpeg",
                )
                self.assertTrue(Path(result).is_absolute())
            finally:
                os.unlink(video_path)

    def test_raises_on_missing_video_file(self):
        """Verify FileNotFoundError for non-existent video file."""
        with self.assertRaises(FileNotFoundError):
            extract_subtitle_to_ass(
                video_path="/nonexistent/video.mkv",
                stream_index=0,
                output_ass="/tmp/output.ass",
                ffmpeg_bin="/usr/bin/ffmpeg",
            )


# ---------------------------------------------------------------------------
# Test: subtitle_bridge (integration with mocks)
# ---------------------------------------------------------------------------
class TestSubtitleBridge(unittest.TestCase):
    """Test the full subtitle_bridge workflow with mocked dependencies."""

    @patch("scripts.subtitle_bridge.mount_ass_to_target")
    @patch("scripts.subtitle_bridge.extract_subtitle_to_ass")
    @patch("scripts.subtitle_bridge.ffprobe_streams")
    def test_full_workflow_succeeds(self, mock_probe, mock_extract, mock_mount):
        """Verify the complete workflow executes without errors."""
        mock_probe.return_value = [
            {"index": 0, "codec_type": "video"},
            {"index": 1, "codec_type": "audio"},
            {
                "index": 2,
                "codec_type": "subtitle",
                "tags": {"title": "简日双语"},
            },
        ]
        mock_extract.return_value = "/tmp/extracted.ass"
        mock_mount.return_value = "/mounted/[BD] Anime.ass"

        with tempfile.TemporaryDirectory() as tmpdir:
            target = os.path.join(tmpdir, "[BD] Anime.mkv")
            source = os.path.join(tmpdir, "[Web] Anime.mkv")
            Path(target).touch()
            Path(source).touch()

            from scripts.subtitle_bridge import subtitle_bridge

            result = subtitle_bridge(target, source, ffmpeg_bin="/usr/bin/ffmpeg")

            self.assertEqual(result["mounted_path"], "/mounted/[BD] Anime.ass")
            self.assertEqual(result["stream_index"], 0)  # subtitle-relative
            self.assertEqual(result["source_title"], "简日双语")

    @patch("scripts.subtitle_bridge.ffprobe_streams")
    def test_raises_when_no_subtitles_found(self, mock_probe):
        """Verify RuntimeError when source has no subtitle streams."""
        mock_probe.return_value = [
            {"index": 0, "codec_type": "video"},
            {"index": 1, "codec_type": "audio"},
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            target = os.path.join(tmpdir, "target.mkv")
            source = os.path.join(tmpdir, "source.mkv")
            Path(target).touch()
            Path(source).touch()

            from scripts.subtitle_bridge import subtitle_bridge

            with self.assertRaises(RuntimeError):
                subtitle_bridge(target, source, ffmpeg_bin="/usr/bin/ffmpeg")

    def test_raises_on_missing_target_video(self):
        """Verify FileNotFoundError when target video is missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source = os.path.join(tmpdir, "source.mkv")
            Path(source).touch()

            from scripts.subtitle_bridge import subtitle_bridge

            with self.assertRaises(FileNotFoundError):
                subtitle_bridge("/nonexistent/target.mkv", source)

    def test_raises_on_missing_subtitle_source(self):
        """Verify FileNotFoundError when subtitle source is missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target = os.path.join(tmpdir, "target.mkv")
            Path(target).touch()

            from scripts.subtitle_bridge import subtitle_bridge

            with self.assertRaises(FileNotFoundError):
                subtitle_bridge(target, "/nonexistent/source.mkv")


if __name__ == "__main__":
    unittest.main()
