#!/usr/bin/env python3
"""Tests for drift CLI."""

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch
from io import StringIO

# Add parent dir to path
sys.path.insert(0, str(Path(__file__).parent.parent))
import drift


class TestDataLayer(unittest.TestCase):
    """Test data storage functions."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.orig_data_dir = drift.DATA_DIR
        drift.DATA_DIR = Path(self.tmpdir)

    def tearDown(self):
        drift.DATA_DIR = self.orig_data_dir
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_ensure_data_dir(self):
        import shutil
        shutil.rmtree(self.tmpdir)
        drift.DATA_DIR = Path(self.tmpdir) / "sub" / "dir"
        drift.ensure_data_dir()
        self.assertTrue(drift.DATA_DIR.exists())

    def test_day_file_path(self):
        path = drift.day_file("2026-02-25")
        self.assertEqual(path.name, "2026-02-25.json")

    def test_load_empty_day(self):
        entries = drift.load_day("2026-01-01")
        self.assertEqual(entries, [])

    def test_save_and_load(self):
        entries = [{"time": "2026-02-25T09:00:00", "level": 7, "tags": ["test"], "note": "hello"}]
        drift.save_day("2026-02-25", entries)
        loaded = drift.load_day("2026-02-25")
        self.assertEqual(loaded, entries)

    def test_date_range(self):
        dates = drift.date_range(3)
        self.assertEqual(len(dates), 3)
        # Last element should be today
        self.assertEqual(dates[-1], datetime.now().date().isoformat())

    def test_today_str(self):
        self.assertEqual(drift.today_str(), datetime.now().strftime("%Y-%m-%d"))


class TestSparkline(unittest.TestCase):
    """Test sparkline rendering."""

    def test_empty(self):
        self.assertEqual(drift.sparkline([]), "")

    def test_single_value(self):
        result = drift.sparkline([5])
        self.assertEqual(len(result), 1)
        self.assertIn(result, drift.SPARKLINE_CHARS)

    def test_range(self):
        result = drift.sparkline([1, 5, 10])
        self.assertEqual(len(result), 3)
        # First char should be lowest, last should be highest
        self.assertEqual(result[0], drift.SPARKLINE_CHARS[0])
        self.assertEqual(result[-1], drift.SPARKLINE_CHARS[-1])

    def test_none_values(self):
        result = drift.sparkline([5, None, 8])
        self.assertEqual(len(result), 3)
        self.assertEqual(result[1], " ")


class TestLevelBar(unittest.TestCase):
    """Test visual level bar."""

    def test_low_level(self):
        bar = drift.level_bar(2)
        self.assertIn("2/10", bar)

    def test_high_level(self):
        bar = drift.level_bar(9)
        self.assertIn("9/10", bar)

    def test_max_level(self):
        bar = drift.level_bar(10)
        self.assertIn("10/10", bar)


class TestDaySummary(unittest.TestCase):
    """Test summary calculation."""

    def test_empty_entries(self):
        s = drift.day_summary("2026-02-25", [])
        self.assertEqual(s["count"], 0)
        self.assertIsNone(s["avg"])

    def test_single_entry(self):
        entries = [{"level": 7, "tags": ["test"]}]
        s = drift.day_summary("2026-02-25", entries)
        self.assertEqual(s["count"], 1)
        self.assertEqual(s["avg"], 7.0)
        self.assertEqual(s["min"], 7)
        self.assertEqual(s["max"], 7)

    def test_multiple_entries(self):
        entries = [
            {"level": 3, "tags": ["vt"]},
            {"level": 7, "tags": ["walk"]},
            {"level": 5, "tags": []},
        ]
        s = drift.day_summary("2026-02-25", entries)
        self.assertEqual(s["count"], 3)
        self.assertEqual(s["avg"], 5.0)
        self.assertEqual(s["min"], 3)
        self.assertEqual(s["max"], 7)
        self.assertIn("vt", s["tags"])
        self.assertIn("walk", s["tags"])

    def test_tags_deduped(self):
        entries = [
            {"level": 5, "tags": ["a", "b"]},
            {"level": 6, "tags": ["b", "c"]},
        ]
        s = drift.day_summary("2026-02-25", entries)
        self.assertEqual(sorted(s["tags"]), ["a", "b", "c"])


class TestFormatTime(unittest.TestCase):
    def test_valid_time(self):
        result = drift.format_time("2026-02-25T14:30:00")
        self.assertIn("2:30 PM", result)

    def test_morning_time(self):
        result = drift.format_time("2026-02-25T09:05:00")
        self.assertIn("9:05 AM", result)

    def test_invalid_time(self):
        result = drift.format_time("bad")
        self.assertEqual(result, "??:??")


class TestCmdLog(unittest.TestCase):
    """Test the log command."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.orig_data_dir = drift.DATA_DIR
        drift.DATA_DIR = Path(self.tmpdir)

    def tearDown(self):
        drift.DATA_DIR = self.orig_data_dir
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _log_args(self, level, note_words=None, tags=None):
        """Helper to create args for cmd_log with _extra note words."""
        args = argparse.Namespace(level=level, tags=tags)
        args._extra = note_words or []
        return args

    def test_basic_log(self):
        args = self._log_args(7)
        with patch("sys.stdout", new_callable=StringIO):
            result = drift.cmd_log(args)
        self.assertEqual(result, 0)
        entries = drift.load_day(drift.today_str())
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["level"], 7)

    def test_log_with_note(self):
        args = self._log_args(5, ["feeling", "tired"])
        with patch("sys.stdout", new_callable=StringIO):
            drift.cmd_log(args)
        entries = drift.load_day(drift.today_str())
        self.assertEqual(entries[0]["note"], "feeling tired")

    def test_log_with_tags(self):
        args = self._log_args(3, tags="vt,fatigue")
        with patch("sys.stdout", new_callable=StringIO):
            drift.cmd_log(args)
        entries = drift.load_day(drift.today_str())
        self.assertEqual(entries[0]["tags"], ["vt", "fatigue"])

    def test_log_strips_hash_from_tags(self):
        args = self._log_args(6, tags="#walk,#coffee")
        with patch("sys.stdout", new_callable=StringIO):
            drift.cmd_log(args)
        entries = drift.load_day(drift.today_str())
        self.assertEqual(entries[0]["tags"], ["walk", "coffee"])

    def test_log_invalid_level_too_low(self):
        args = self._log_args(0)
        with patch("sys.stderr", new_callable=StringIO):
            result = drift.cmd_log(args)
        self.assertEqual(result, 1)

    def test_log_invalid_level_too_high(self):
        args = self._log_args(11)
        with patch("sys.stderr", new_callable=StringIO):
            result = drift.cmd_log(args)
        self.assertEqual(result, 1)

    def test_multiple_logs_same_day(self):
        for level in [3, 5, 8]:
            args = self._log_args(level)
            with patch("sys.stdout", new_callable=StringIO):
                drift.cmd_log(args)
        entries = drift.load_day(drift.today_str())
        self.assertEqual(len(entries), 3)
        self.assertEqual([e["level"] for e in entries], [3, 5, 8])


class TestCmdDelete(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.orig_data_dir = drift.DATA_DIR
        drift.DATA_DIR = Path(self.tmpdir)

    def tearDown(self):
        drift.DATA_DIR = self.orig_data_dir
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_delete_entry(self):
        entries = [
            {"time": "2026-02-25T09:00:00", "level": 5, "tags": [], "note": "first"},
            {"time": "2026-02-25T12:00:00", "level": 7, "tags": [], "note": "second"},
        ]
        drift.save_day(drift.today_str(), entries)

        args = argparse.Namespace(index=0)
        with patch("sys.stdout", new_callable=StringIO):
            result = drift.cmd_delete(args)
        self.assertEqual(result, 0)

        remaining = drift.load_day(drift.today_str())
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0]["note"], "second")

    def test_delete_invalid_index(self):
        entries = [{"time": "2026-02-25T09:00:00", "level": 5, "tags": [], "note": "only"}]
        drift.save_day(drift.today_str(), entries)

        args = argparse.Namespace(index=5)
        with patch("sys.stderr", new_callable=StringIO):
            result = drift.cmd_delete(args)
        self.assertEqual(result, 1)

    def test_delete_empty_day(self):
        args = argparse.Namespace(index=0)
        with patch("sys.stdout", new_callable=StringIO):
            result = drift.cmd_delete(args)
        self.assertEqual(result, 1)


class TestCmdWeek(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.orig_data_dir = drift.DATA_DIR
        drift.DATA_DIR = Path(self.tmpdir)

    def tearDown(self):
        drift.DATA_DIR = self.orig_data_dir
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_week_no_data(self):
        args = argparse.Namespace()
        with patch("sys.stdout", new_callable=StringIO) as out:
            drift.cmd_week(args)
        self.assertIn("No data yet", out.getvalue())

    def test_week_with_data(self):
        # Add some data for today
        entries = [{"time": datetime.now().isoformat(), "level": 7, "tags": [], "note": ""}]
        drift.save_day(drift.today_str(), entries)

        args = argparse.Namespace()
        with patch("sys.stdout", new_callable=StringIO) as out:
            drift.cmd_week(args)
        output = out.getvalue()
        self.assertIn("Last 7 Days", output)
        self.assertIn("1 log", output)


class TestCmdReport(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.orig_data_dir = drift.DATA_DIR
        drift.DATA_DIR = Path(self.tmpdir)

    def tearDown(self):
        drift.DATA_DIR = self.orig_data_dir
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_report_no_data(self):
        args = argparse.Namespace(days=14)
        with patch("sys.stdout", new_callable=StringIO) as out:
            drift.cmd_report(args)
        self.assertIn("No data", out.getvalue())

    def test_report_with_data(self):
        # Populate several days
        today = datetime.now().date()
        for i in range(5):
            d = (today - timedelta(days=i)).isoformat()
            entries = [
                {"time": f"{d}T09:00:00", "level": 5 + i, "tags": ["test"], "note": ""},
                {"time": f"{d}T14:00:00", "level": 4 + i, "tags": ["work"], "note": ""},
            ]
            drift.save_day(d, entries)

        args = argparse.Namespace(days=7)
        with patch("sys.stdout", new_callable=StringIO) as out:
            drift.cmd_report(args)
        output = out.getvalue()
        self.assertIn("Drift Report", output)
        self.assertIn("Total entries:", output)
        self.assertIn("Tag Correlations", output)
        self.assertIn("Time-of-Day", output)


class TestCmdExport(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.orig_data_dir = drift.DATA_DIR
        drift.DATA_DIR = Path(self.tmpdir)

    def tearDown(self):
        drift.DATA_DIR = self.orig_data_dir
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_export_markdown(self):
        entries = [
            {"time": "2026-02-25T10:00:00", "level": 7, "tags": ["morning"], "note": "good"},
        ]
        drift.save_day(drift.today_str(), entries)

        args = argparse.Namespace(days=1)
        with patch("sys.stdout", new_callable=StringIO) as out:
            drift.cmd_export(args)
        output = out.getvalue()
        self.assertIn("# Drift Energy Log", output)
        self.assertIn("7/10", output)
        self.assertIn("#morning", output)


class TestCmdStreak(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.orig_data_dir = drift.DATA_DIR
        drift.DATA_DIR = Path(self.tmpdir)

    def tearDown(self):
        drift.DATA_DIR = self.orig_data_dir
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_streak_no_data(self):
        args = argparse.Namespace()
        with patch("sys.stdout", new_callable=StringIO) as out:
            drift.cmd_streak(args)
        self.assertIn("0 days", out.getvalue())

    def test_streak_with_data(self):
        today = datetime.now().date()
        for i in range(3):
            d = (today - timedelta(days=i)).isoformat()
            drift.save_day(d, [{"time": f"{d}T09:00:00", "level": 5, "tags": [], "note": ""}])

        args = argparse.Namespace()
        with patch("sys.stdout", new_callable=StringIO) as out:
            drift.cmd_streak(args)
        self.assertIn("3 days", out.getvalue())


class TestCmdTags(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.orig_data_dir = drift.DATA_DIR
        drift.DATA_DIR = Path(self.tmpdir)

    def tearDown(self):
        drift.DATA_DIR = self.orig_data_dir
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_tags_empty(self):
        args = argparse.Namespace()
        with patch("sys.stdout", new_callable=StringIO) as out:
            drift.cmd_tags(args)
        self.assertIn("No tags", out.getvalue())

    def test_tags_with_data(self):
        entries = [
            {"time": "2026-02-25T09:00:00", "level": 5, "tags": ["vt", "fatigue"], "note": ""},
            {"time": "2026-02-25T14:00:00", "level": 7, "tags": ["walk"], "note": ""},
            {"time": "2026-02-25T18:00:00", "level": 6, "tags": ["vt"], "note": ""},
        ]
        drift.save_day("2026-02-25", entries)

        args = argparse.Namespace()
        with patch("sys.stdout", new_callable=StringIO) as out:
            drift.cmd_tags(args)
        output = out.getvalue()
        self.assertIn("#vt", output)
        self.assertIn("2 uses", output)
        self.assertIn("#walk", output)


# Need argparse imported for test Namespace objects
import argparse

if __name__ == "__main__":
    unittest.main()
