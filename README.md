# drift ⚡

CLI energy & fatigue tracker — log levels throughout the day, spot patterns over time, and manage recovery.

Built for anyone managing post-concussion fatigue, chronic illness, or just wanting to understand their productive rhythms. Zero dependencies beyond Python 3.8+ stdlib.

## Quick Start

```bash
# Clone and use directly
git clone https://github.com/aristoddlerabot/drift.git
cd drift
python3 drift.py log 7 "feeling good this morning"

# Or install with pip
pip install -e .
drift log 7 "feeling good this morning"
```

## Usage

### Log energy levels (1-10)

```bash
drift log 6                          # Quick log
drift log 4 "drained after VT"      # With a note
drift log 3 -t vt,fatigue "rough"   # With tags
drift log 8 -t exercise,walk        # Tag activities
```

**Energy scale:**
| Level | Meaning |
|-------|---------|
| 1-3   | 🔴 Low — rest, recovery mode |
| 4-6   | 🟡 Medium — light tasks, pacing needed |
| 7-8   | 🟢 Good — normal capacity |
| 9-10  | 🟢 Peak — full send |

### View your data

```bash
drift today              # Today's entries with colored bars
drift yesterday          # Yesterday's entries
drift week               # 7-day summary with sparkline chart
drift report             # 14-day deep analysis (patterns, correlations)
drift report --days 30   # Custom range
```

### Manage entries

```bash
drift edit 0             # Edit today's first entry
drift delete 2           # Delete today's third entry
drift tags               # See all tags you've used
drift streak             # Check your logging streak 🔥
```

### Export

```bash
drift export             # Last 7 days as markdown
drift export --days 30   # Custom range
drift export > report.md # Save to file
```

## What You Get

### Weekly Summary
```
  📊 Last 7 Days
  ──────────────────────────────────────────────
  Mon 02/17  ████████░░ 8/10  (3 logs)
  Tue 02/18  ██████░░░░ 6/10  (4 logs)
  Wed 02/19  ████░░░░░░ 4/10  (2 logs)  ← VT day
  Thu 02/20  █████░░░░░ 5/10  (3 logs)
  Fri 02/21  ███████░░░ 7/10  (3 logs)
  Sat 02/22  ████████░░ 8/10  (2 logs)
  Sun 02/23  ████████░░ 8/10  (1 log)

  Trend: ▆▅▃▄▅▆▆
  Overall avg: 6.6/10 across 7 days
```

### Detailed Report
The `drift report` command shows:
- **Energy distribution** — histogram of your levels
- **Time-of-day patterns** — morning vs afternoon vs evening energy
- **Tag correlations** — which activities correlate with high/low energy
- **Day-of-week averages** — find your best/worst days
- **Trend direction** — are you improving over time?

## Data Storage

All data is stored as plain JSON in `~/.drift/`:

```
~/.drift/
├── 2026-02-23.json
├── 2026-02-24.json
└── 2026-02-25.json
```

Each file is a simple array of entries:

```json
[
  {
    "time": "2026-02-25T09:30:00",
    "level": 7,
    "tags": ["morning", "coffee"],
    "note": "good start to the day"
  }
]
```

**Override data directory:** Set `DRIFT_DATA_DIR` environment variable.

## Use Cases

- **Post-concussion recovery** — Track energy dips after therapy sessions, correlate with activities
- **Chronic fatigue management** — Find your peak hours, pace activities accordingly
- **ADHD energy tracking** — Know when you're most focused vs scattered
- **General productivity** — Understand your circadian patterns and plan work accordingly
- **Medication tracking** — Tag doses and correlate with energy changes

## Tips

1. **Log 2-4 times/day** — morning, midday, afternoon, evening gives good coverage
2. **Use consistent tags** — `vt`, `exercise`, `nap`, `meds`, `work` etc.
3. **Check `drift week` on Sundays** — spot weekly patterns
4. **Run `drift report --days 30` monthly** — look for trends
5. **Export before doctor visits** — `drift export --days 30 > energy-report.md`

## Philosophy

- **Zero dependencies** — Python stdlib only, runs anywhere
- **Plain text storage** — JSON files you own, easy to backup/grep/process
- **Terminal native** — fast, no browser needed, works over SSH
- **Privacy first** — all data stays on your machine

## License

MIT
