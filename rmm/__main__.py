"""CLI entry point.

  python -m rmm trade-sheet                      query Neon (DATABASE_URL) and write today's sheet
  python -m rmm trade-sheet --board B.json --preflight P.json
                                                 render from saved query results instead (the
                                                 Neon connector path the Trade Sheet task uses)
  python -m rmm trade-sheet ... --date YYYY-MM-DD --now "YYYY-MM-DD HH:MM"
                                                 override the sheet date / generated time (tests)

Writes outputs/trade-sheets/YYYY-MM/YYYY-MM-DD_trade-sheet.{md,csv,html} and prints the
status line, so a scheduled task can pass it straight to the notification.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from . import db, paths, trade_sheet

ET = ZoneInfo("America/New_York")


def cmd_trade_sheet(a: argparse.Namespace) -> None:
    if a.board:
        board, pre = db.load_rows(Path(a.board)), db.load_rows(Path(a.preflight)) if a.preflight else []
    else:
        board = db.run_query(paths.query("trade_sheet"))
        pre = db.run_query(paths.query("trade_sheet_preflight"))
    now = datetime.strptime(a.now, "%Y-%m-%d %H:%M") if a.now else datetime.now(ET).replace(tzinfo=None)
    day = date.fromisoformat(a.date) if a.date else now.date()
    sheet = trade_sheet.build(board, pre, day, now)
    for ext, text in (("md", trade_sheet.render_md(sheet)), ("csv", trade_sheet.render_csv(sheet)),
                      ("html", trade_sheet.render_html(sheet))):
        p = paths.trade_sheet(day, ext)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
        print(f"wrote {p.relative_to(paths.ROOT)}")
    print(f"{sheet.status} · {sheet.headline}")


def main() -> None:
    ap = argparse.ArgumentParser(prog="rmm")
    sub = ap.add_subparsers(dest="cmd", required=True)
    ts = sub.add_parser("trade-sheet", help="today's trade sheet")
    ts.add_argument("--board", help="saved trade_sheet.sql results (JSON)")
    ts.add_argument("--preflight", help="saved trade_sheet_preflight.sql results (JSON)")
    ts.add_argument("--date", help="sheet date, default today in New York")
    ts.add_argument("--now", help="generated-at time in New York, default now")
    ts.set_defaults(fn=cmd_trade_sheet)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
