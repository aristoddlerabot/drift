#!/usr/bin/env python3
"""drift — CLI energy & fatigue tracker.

Log energy levels throughout the day, tag activities, and spot patterns
over time. Built for managing post-concussion fatigue, chronic illness,
or just understanding your productive rhythms.

Zero dependencies beyond Python 3.8+ stdlib.
Data stored as JSON in ~/.drift/ (one file per day).

Usage:
    drift log <level> [note]       Log energy (1-10) with optional note
    drift log <level> -t tag1,tag2 Log with activity tags
    drift today                    Show today's entries
    drift yesterday                Show yesterday's entries
    drift week                     7-day summary with sparkline
    drift report [--days N]        Detailed report with patterns
    drift tags                     List all tags used
    drift export [--days N]        Export to markdown
    drift edit <index>             Edit today's entry by index
    drift delete <index>           Delete today's entry by index
    drift streak                   Show logging streak
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from collections import Counter, defaultdict

__version__ = "0.1.0"

# ── Config ──────────────────────────────────────────────────────────────

DATA_DIR = Path(os.environ.get("DRIFT_DATA_DIR", Path.home() / ".drift"))
SPARKLINE_CHARS = "▁▂▃▄▅▆▇█"


# ── Data Layer ──────────────────────────────────────────────────────────

def ensure_data_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def day_file(date_str: str) -> Path:
    """Return path to the JSON file for a given date (YYYY-MM-DD)."""
    return DATA_DIR / f"{date_str}.json"


def load_day(date_str: str) -> list:
    """Load entries for a given date. Returns empty list if no file."""
    path = day_file(date_str)
    if not path.exists():
        return []
    with open(path, "r") as f:
        return json.load(f)


def save_day(date_str: str, entries: list):
    """Save entries for a given date."""
    ensure_data_dir()
    path = day_file(date_str)
    with open(path, "w") as f:
        json.dump(entries, f, indent=2)


def today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def yesterday_str() -> str:
    return (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")


def date_range(days: int) -> list:
    """Return list of date strings for the last N days (most recent last)."""
    today = datetime.now().date()
    return [(today - timedelta(days=i)).isoformat() for i in range(days - 1, -1, -1)]


# ── Sparkline ───────────────────────────────────────────────────────────

def sparkline(values: list) -> str:
    """Render a list of 1-10 values as a Unicode sparkline."""
    if not values:
        return ""
    result = []
    for v in values:
        if v is None:
            result.append(" ")
        else:
            idx = min(int((v - 1) / 9 * (len(SPARKLINE_CHARS) - 1)), len(SPARKLINE_CHARS) - 1)
            result.append(SPARKLINE_CHARS[idx])
    return "".join(result)


# ── Display Helpers ─────────────────────────────────────────────────────

def level_bar(level: int, width: int = 10) -> str:
    """Render energy level as a colored bar."""
    filled = level
    empty = width - filled
    if level <= 3:
        color = "\033[91m"  # red
    elif level <= 6:
        color = "\033[93m"  # yellow
    else:
        color = "\033[92m"  # green
    reset = "\033[0m"
    return f"{color}{'█' * filled}{'░' * empty}{reset} {level}/10"


def format_time(iso_time: str) -> str:
    """Format ISO timestamp to readable time."""
    try:
        dt = datetime.fromisoformat(iso_time)
        return dt.strftime("%I:%M %p").lstrip("0")
    except (ValueError, TypeError):
        return "??:??"


def format_entry(entry: dict, index: int = None) -> str:
    """Format a single log entry for display."""
    parts = []
    if index is not None:
        parts.append(f"  [{index}]")
    parts.append(f"  {format_time(entry['time'])}")
    parts.append(f"  {level_bar(entry['level'])}")
    if entry.get("tags"):
        tag_str = " ".join(f"#{t}" for t in entry["tags"])
        parts.append(f"  {tag_str}")
    if entry.get("note"):
        parts.append(f"  💬 {entry['note']}")
    return "\n".join(parts)


def day_summary(date_str: str, entries: list) -> dict:
    """Calculate summary stats for a day's entries."""
    if not entries:
        return {"date": date_str, "count": 0, "avg": None, "min": None, "max": None, "tags": []}
    levels = [e["level"] for e in entries]
    all_tags = []
    for e in entries:
        all_tags.extend(e.get("tags", []))
    return {
        "date": date_str,
        "count": len(entries),
        "avg": round(sum(levels) / len(levels), 1),
        "min": min(levels),
        "max": max(levels),
        "tags": list(set(all_tags)),
    }


# ── Commands ────────────────────────────────────────────────────────────

def cmd_log(args):
    """Log an energy level with optional note and tags."""
    level = args.level
    if level < 1 or level > 10:
        print("Error: level must be between 1 and 10", file=sys.stderr)
        return 1

    tags = []
    if args.tags:
        tags = [t.strip().lstrip("#") for t in args.tags.split(",") if t.strip()]

    # Note comes from extra args (remaining positional words after flags)
    note = " ".join(getattr(args, "_extra", []))

    entry = {
        "time": datetime.now().isoformat(),
        "level": level,
        "tags": tags,
        "note": note,
    }

    date_str = today_str()
    entries = load_day(date_str)
    entries.append(entry)
    save_day(date_str, entries)

    print(f"\n  ⚡ Logged energy level {level}/10")
    if tags:
        print(f"  🏷️  {', '.join(f'#{t}' for t in tags)}")
    if note:
        print(f"  💬 {note}")
    print(f"  📊 Entry #{len(entries)} for {date_str}")
    print()
    return 0


def cmd_show_day(args, date_str: str, label: str):
    """Show entries for a specific day."""
    entries = load_day(date_str)
    if not entries:
        print(f"\n  No entries for {label} ({date_str})")
        print(f"  Log one: drift log <1-10> [note]\n")
        return 0

    summary = day_summary(date_str, entries)
    print(f"\n  📅 {label} — {date_str}")
    print(f"  {'─' * 40}")

    for i, entry in enumerate(entries):
        print(format_entry(entry, index=i))
        if i < len(entries) - 1:
            print()

    print(f"\n  {'─' * 40}")
    print(f"  📊 {summary['count']} entries | avg {summary['avg']} | range {summary['min']}-{summary['max']}")
    if summary["tags"]:
        print(f"  🏷️  {', '.join(f'#{t}' for t in sorted(summary['tags']))}")
    print()
    return 0


def cmd_today(args):
    return cmd_show_day(args, today_str(), "Today")


def cmd_yesterday(args):
    return cmd_show_day(args, yesterday_str(), "Yesterday")


def cmd_week(args):
    """Show 7-day summary with sparkline."""
    dates = date_range(7)
    daily_avgs = []
    rows = []

    for d in dates:
        entries = load_day(d)
        s = day_summary(d, entries)
        daily_avgs.append(s["avg"])
        rows.append(s)

    # Header
    print(f"\n  📊 Last 7 Days")
    print(f"  {'─' * 50}")

    # Day-by-day
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    for s in rows:
        dt = datetime.fromisoformat(s["date"])
        day_name = day_names[dt.weekday()]
        date_short = dt.strftime("%m/%d")

        if s["avg"] is None:
            print(f"  {day_name} {date_short}  {'·' * 10}  —")
        else:
            bar = level_bar(round(s["avg"]))
            count_str = f"({s['count']} log{'s' if s['count'] != 1 else ''})"
            print(f"  {day_name} {date_short}  {bar}  {count_str}")

    # Sparkline
    spark_vals = [v if v is not None else None for v in daily_avgs]
    print(f"\n  Trend: {sparkline(spark_vals)}")

    # Overall stats
    valid_avgs = [v for v in daily_avgs if v is not None]
    if valid_avgs:
        overall = round(sum(valid_avgs) / len(valid_avgs), 1)
        days_logged = len(valid_avgs)
        print(f"  Overall avg: {overall}/10 across {days_logged} day{'s' if days_logged != 1 else ''}")
    else:
        print("  No data yet — start logging with: drift log <1-10>")

    print()
    return 0


def cmd_report(args):
    """Detailed report with patterns and tag correlations."""
    days = args.days or 14
    dates = date_range(days)

    all_entries = []
    daily_summaries = []
    for d in dates:
        entries = load_day(d)
        for e in entries:
            e["_date"] = d
        all_entries.extend(entries)
        daily_summaries.append(day_summary(d, entries))

    if not all_entries:
        print(f"\n  No data in the last {days} days.")
        print(f"  Start logging: drift log <1-10> [note]\n")
        return 0

    # Overall stats
    levels = [e["level"] for e in all_entries]
    valid_days = [s for s in daily_summaries if s["avg"] is not None]

    print(f"\n  📊 Drift Report — Last {days} Days")
    print(f"  {'═' * 50}")
    print(f"  Total entries:  {len(all_entries)}")
    print(f"  Days logged:    {len(valid_days)}/{days}")
    print(f"  Average energy: {round(sum(levels) / len(levels), 1)}/10")
    print(f"  Range:          {min(levels)} – {max(levels)}")

    # Distribution
    print(f"\n  Energy Distribution:")
    dist = Counter(levels)
    for level in range(1, 11):
        count = dist.get(level, 0)
        bar = "█" * count
        if count > 0:
            print(f"    {level:2d} │ {bar} ({count})")

    # Time-of-day patterns
    hour_levels = defaultdict(list)
    for e in all_entries:
        try:
            hour = datetime.fromisoformat(e["time"]).hour
            bucket = "Morning (6-12)" if 6 <= hour < 12 else \
                     "Afternoon (12-17)" if 12 <= hour < 17 else \
                     "Evening (17-22)" if 17 <= hour < 22 else \
                     "Night (22-6)"
            hour_levels[bucket].append(e["level"])
        except (ValueError, KeyError):
            pass

    if hour_levels:
        print(f"\n  ⏰ Time-of-Day Patterns:")
        for bucket in ["Morning (6-12)", "Afternoon (12-17)", "Evening (17-22)", "Night (22-6)"]:
            if bucket in hour_levels:
                vals = hour_levels[bucket]
                avg = round(sum(vals) / len(vals), 1)
                print(f"    {bucket:20s}  avg {avg}/10  ({len(vals)} entries)")

    # Tag analysis
    tag_levels = defaultdict(list)
    for e in all_entries:
        for tag in e.get("tags", []):
            tag_levels[tag].append(e["level"])

    if tag_levels:
        print(f"\n  🏷️  Tag Correlations:")
        sorted_tags = sorted(tag_levels.items(), key=lambda x: sum(x[1]) / len(x[1]))
        for tag, vals in sorted_tags:
            avg = round(sum(vals) / len(vals), 1)
            print(f"    #{tag:20s}  avg {avg}/10  ({len(vals)} entries)")

    # Day-of-week patterns
    dow_levels = defaultdict(list)
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    for s in daily_summaries:
        if s["avg"] is not None:
            dt = datetime.fromisoformat(s["date"])
            dow_levels[day_names[dt.weekday()]].append(s["avg"])

    if dow_levels:
        print(f"\n  📅 Day-of-Week Averages:")
        for name in day_names:
            if name in dow_levels:
                vals = dow_levels[name]
                avg = round(sum(vals) / len(vals), 1)
                print(f"    {name:12s}  avg {avg}/10  ({len(vals)} week{'s' if len(vals) != 1 else ''})")

    # Trend (first half vs second half)
    if len(valid_days) >= 4:
        mid = len(valid_days) // 2
        first_half = [s["avg"] for s in valid_days[:mid]]
        second_half = [s["avg"] for s in valid_days[mid:]]
        first_avg = round(sum(first_half) / len(first_half), 1)
        second_avg = round(sum(second_half) / len(second_half), 1)
        diff = round(second_avg - first_avg, 1)
        arrow = "📈" if diff > 0 else "📉" if diff < 0 else "➡️"
        print(f"\n  {arrow} Trend: {first_avg} → {second_avg} ({'+' if diff > 0 else ''}{diff})")

    print()
    return 0


def cmd_tags(args):
    """List all tags used with frequency."""
    # Scan all files
    ensure_data_dir()
    tag_counts = Counter()

    for path in sorted(DATA_DIR.glob("*.json")):
        try:
            with open(path) as f:
                entries = json.load(f)
            for e in entries:
                for tag in e.get("tags", []):
                    tag_counts[tag] += 1
        except (json.JSONDecodeError, KeyError):
            continue

    if not tag_counts:
        print("\n  No tags found yet.")
        print("  Use: drift log <level> -t tag1,tag2 [note]\n")
        return 0

    print(f"\n  🏷️  All Tags")
    print(f"  {'─' * 30}")
    for tag, count in tag_counts.most_common():
        print(f"  #{tag:20s}  {count} use{'s' if count != 1 else ''}")
    print()
    return 0


def cmd_export(args):
    """Export data to markdown."""
    days = args.days or 7
    dates = date_range(days)

    print(f"# Drift Energy Log — Last {days} Days\n")

    for d in dates:
        entries = load_day(d)
        if not entries:
            continue

        s = day_summary(d, entries)
        dt = datetime.fromisoformat(d)
        print(f"## {dt.strftime('%A, %B %d, %Y')}")
        print(f"**Avg: {s['avg']}/10 | Range: {s['min']}-{s['max']} | Entries: {s['count']}**\n")

        print("| Time | Level | Tags | Note |")
        print("|------|-------|------|------|")
        for e in entries:
            time = format_time(e["time"])
            level = f"{e['level']}/10"
            tags = ", ".join(f"#{t}" for t in e.get("tags", []))
            note = e.get("note", "")
            print(f"| {time} | {level} | {tags} | {note} |")
        print()

    return 0


def cmd_edit(args):
    """Edit an entry by index."""
    date_str = today_str()
    entries = load_day(date_str)

    if not entries:
        print(f"\n  No entries today to edit.\n")
        return 1

    idx = args.index
    if idx < 0 or idx >= len(entries):
        print(f"\n  Invalid index {idx}. Valid range: 0-{len(entries) - 1}\n", file=sys.stderr)
        return 1

    entry = entries[idx]
    print(f"\n  Current entry [{idx}]:")
    print(format_entry(entry, index=idx))

    # Interactive edit
    new_level = input(f"\n  New level (1-10) [{entry['level']}]: ").strip()
    if new_level:
        new_level = int(new_level)
        if 1 <= new_level <= 10:
            entry["level"] = new_level

    new_tags = input(f"  New tags (comma-sep) [{','.join(entry.get('tags', []))}]: ").strip()
    if new_tags:
        entry["tags"] = [t.strip().lstrip("#") for t in new_tags.split(",") if t.strip()]

    new_note = input(f"  New note [{entry.get('note', '')}]: ").strip()
    if new_note:
        entry["note"] = new_note

    entries[idx] = entry
    save_day(date_str, entries)
    print(f"\n  ✅ Entry [{idx}] updated.\n")
    return 0


def cmd_delete(args):
    """Delete an entry by index."""
    date_str = today_str()
    entries = load_day(date_str)

    if not entries:
        print(f"\n  No entries today to delete.\n")
        return 1

    idx = args.index
    if idx < 0 or idx >= len(entries):
        print(f"\n  Invalid index {idx}. Valid range: 0-{len(entries) - 1}\n", file=sys.stderr)
        return 1

    entry = entries[idx]
    print(f"\n  Deleting entry [{idx}]:")
    print(format_entry(entry, index=idx))

    entries.pop(idx)
    save_day(date_str, entries)
    print(f"\n  🗑️  Entry deleted. {len(entries)} entries remaining.\n")
    return 0


def cmd_streak(args):
    """Show logging streak."""
    ensure_data_dir()
    today = datetime.now().date()
    streak = 0
    longest = 0
    current = 0

    # Check backwards from today
    for i in range(365):
        d = (today - timedelta(days=i)).isoformat()
        entries = load_day(d)
        if entries:
            current += 1
            if i == streak:
                streak = current
        else:
            if current > longest:
                longest = current
            current = 0

    if current > longest:
        longest = current

    # Total days ever logged
    total_files = len(list(DATA_DIR.glob("*.json")))

    print(f"\n  🔥 Logging Streak")
    print(f"  {'─' * 30}")
    print(f"  Current streak:  {streak} day{'s' if streak != 1 else ''}")
    print(f"  Longest streak:  {longest} day{'s' if longest != 1 else ''}")
    print(f"  Total days logged: {total_files}")
    print()
    return 0


def cmd_version(args):
    print(f"drift v{__version__}")
    return 0


# ── CLI Parser ──────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="drift",
        description="⚡ CLI energy & fatigue tracker — log levels, spot patterns, manage recovery",
    )
    parser.add_argument("-v", "--version", action="store_true", help="Show version")
    sub = parser.add_subparsers(dest="command")

    # log — uses parse_known_args to handle intermixed -t and free-text note
    p_log = sub.add_parser("log", help="Log energy level (1-10)")
    p_log.add_argument("level", type=int, help="Energy level 1-10")
    p_log.add_argument("-t", "--tags", help="Comma-separated tags (e.g., vt,fatigue,walk)")

    # today
    sub.add_parser("today", help="Show today's entries")

    # yesterday
    sub.add_parser("yesterday", help="Show yesterday's entries")

    # week
    sub.add_parser("week", help="7-day summary with sparkline")

    # report
    p_report = sub.add_parser("report", help="Detailed report with patterns")
    p_report.add_argument("--days", type=int, default=14, help="Number of days (default: 14)")

    # tags
    sub.add_parser("tags", help="List all tags")

    # export
    p_export = sub.add_parser("export", help="Export to markdown")
    p_export.add_argument("--days", type=int, default=7, help="Number of days (default: 7)")

    # edit
    p_edit = sub.add_parser("edit", help="Edit today's entry by index")
    p_edit.add_argument("index", type=int, help="Entry index")

    # delete
    p_delete = sub.add_parser("delete", help="Delete today's entry by index")
    p_delete.add_argument("index", type=int, help="Entry index")

    # streak
    sub.add_parser("streak", help="Show logging streak")

    return parser


def main():
    parser = build_parser()

    # First pass: figure out the subcommand
    args, extra = parser.parse_known_args()

    if args.version:
        return cmd_version(args)

    # For the log command, extra args become the free-text note
    if args.command == "log":
        args._extra = extra
    elif extra:
        parser.parse_args()  # re-parse to trigger proper error message
        return 1

    commands = {
        "log": cmd_log,
        "today": cmd_today,
        "yesterday": cmd_yesterday,
        "week": cmd_week,
        "report": cmd_report,
        "tags": cmd_tags,
        "export": cmd_export,
        "edit": cmd_edit,
        "delete": cmd_delete,
        "streak": cmd_streak,
    }

    if args.command in commands:
        return commands[args.command](args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
