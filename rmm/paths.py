"""Where every output file goes, and what it is called.

This module is the naming convention: nothing else builds an output path by hand,
so the Librarian can check the outputs/ tree against these same functions.

    outputs/trade-sheets/2026-10/2026-10-27_trade-sheet.md      daily
    outputs/weekly/2026-W44_weekly-review.md                    weekly
    outputs/models/v8_2026-11-01/fit-report.md                  per fit
    outputs/experiments/EXP-0007_news-volume/report.md          per experiment
    outputs/costs/neon-usage.csv                                 ledger, appended weekly
"""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUTS = ROOT / "outputs"
SQL = ROOT / "sql"

# Daily: YYYY-MM-DD_<kind>.<ext>; weekly: YYYY-Www_<kind>.<ext>. Kinds are lowercase kebab-case.
DAILY_NAME = re.compile(r"^\d{4}-\d{2}-\d{2}_[a-z0-9]+(-[a-z0-9]+)*\.[a-z]+$")
WEEKLY_NAME = re.compile(r"^\d{4}-W\d{2}_[a-z0-9]+(-[a-z0-9]+)*\.[a-z]+$")


def trade_sheet(day: date, ext: str) -> Path:
    return OUTPUTS / "trade-sheets" / f"{day:%Y-%m}" / f"{day:%Y-%m-%d}_trade-sheet.{ext}"


def weekly(day: date, kind: str, ext: str = "md") -> Path:
    year, week, _ = day.isocalendar()
    return OUTPUTS / "weekly" / f"{year}-W{week:02d}_{kind}.{ext}"


def model_dir(version: int, trained_through: str) -> Path:
    """outputs/models/v<N>_<trained through>/ (v1 is the R fit trained through 2026-10-09)."""
    return OUTPUTS / "models" / f"v{version}_{trained_through}"


def next_model_version() -> int:
    found = [int(m.group(1)) for p in (OUTPUTS / "models").glob("v*_*") if (m := re.match(r"v(\d+)_", p.name))]
    return max(found + [1]) + 1


def costs_ledger() -> Path:
    """Running ledger of Neon usage, one row per cost report (not dated: it is appended to)."""
    return OUTPUTS / "costs" / "neon-usage.csv"


def query(name: str) -> Path:
    return SQL / "queries" / f"{name}.sql"
