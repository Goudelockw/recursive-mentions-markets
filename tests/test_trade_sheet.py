"""python -m unittest discover tests"""
import unittest
from datetime import date, datetime
from pathlib import Path

from rmm import db, paths, trade_sheet as ts

FIX = Path(__file__).parent / "fixtures"


def sheet():
    board = db.load_rows(FIX / "board_2026-10-27.json")
    pre = db.load_rows(FIX / "preflight_2026-10-27.json")
    return ts.build(board, pre, date(2026, 10, 27), datetime(2026, 10, 27, 6, 41))


class TradeSheetTest(unittest.TestCase):
    def test_counts_and_status(self):
        s = sheet()
        self.assertEqual(len(s.trades), 11)
        self.assertEqual(len(s.skips), 2)
        self.assertEqual(s.status, "CHECK")  # INTC check-date, a stale quote and HOOD over its cap
        self.assertEqual([c.symbol for c in s.calls], ["KO", "HLT", "V", "HOOD"])

    def test_risk_reads(self):
        s = sheet()
        by = {t["word"]: t for t in s.trades + s.skips}
        self.assertEqual(by["Pibb"].risk, "Aligned")
        self.assertEqual(by["Waymo (test)"].risk, "Conflict")
        self.assertEqual(by["Holiday (test)"].risk, "Rule skip")
        self.assertEqual(by["Inyo"].risk, "No read")
        self.assertEqual(by["Acquired / Acquisition"].risk_note, "fading the favorite (2 pts)")
        self.assertEqual(by["Kalshi"].risk_note, "backing the favorite (1 pt)")

    def test_cost_is_the_side_you_buy(self):
        by = {t["word"]: t for t in sheet().trades}
        self.assertEqual(by["Pibb"].cost_c, 40)          # NO at 100 - yes bid 60
        self.assertEqual(by["Graduate / Undergraduate"].cost_c, 60)  # YES at the ask

    def test_data_issues_block(self):
        by = {t["word"]: t for t in sheet().trades}
        self.assertEqual(by["Bitcoin (test: stale)"].issues, ["quote 7h old", "no incentive label"])

    def test_failed_preflight_is_stop(self):
        board = db.load_rows(FIX / "board_2026-10-27.json")
        pre = [{"check_name": "job:sync", "hours_since_ok": 9.0, "max_hours": 3, "failed_24h": True}]
        self.assertEqual(ts.build(board, pre, date(2026, 10, 27), datetime(2026, 10, 27, 6, 41)).status, "STOP")

    def test_renders(self):
        s = sheet()
        self.assertIn("## Risk map", ts.render_md(s))
        self.assertEqual(len(ts.render_csv(s).strip().splitlines()), 1 + 11 + 2)
        self.assertIn("Trade Sheet · Tue Oct 27, 2026", ts.render_html(s))


class NamingTest(unittest.TestCase):
    def test_paths_follow_the_convention(self):
        p = paths.trade_sheet(date(2026, 10, 27), "md")
        self.assertEqual(p.relative_to(paths.OUTPUTS).as_posix(), "trade-sheets/2026-10/2026-10-27_trade-sheet.md")
        self.assertRegex(p.name, paths.DAILY_NAME)
        w = paths.weekly(date(2026, 10, 27), "weekly-review")
        self.assertEqual(w.name, "2026-W44_weekly-review.md")
        self.assertRegex(w.name, paths.WEEKLY_NAME)


if __name__ == "__main__":
    unittest.main()
