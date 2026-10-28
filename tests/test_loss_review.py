import unittest
from datetime import date

from rmm import loss_review, sectors


def row(**k):
    base = {"source": "backtest", "stage": "early_24h", "call_date": "2026-10-27", "symbol": "KO", "word": "w",
            "ticker": "T", "event_ticker": "E", "side": "NO", "fav_side": "YES", "avoid_tier": "OK", "action": "TRADE",
            "bid_c": 40, "ask_c": 44, "model_c": 30, "result": "NO", "won": 1, "pnl_c": 10.0, "stake_pct": 2.0,
            "ret_pct": 1.0, "word_scope": "own_business", "word_category": "x", "move_24h": 0.0,
            "theme_cos_before": 0, "new_for_company": False, "sic": "2080"}
    base.update(k)
    return base


class LossReviewTest(unittest.TestCase):
    def test_windows_and_ideas(self):
        rows = [row(ticker="a", pnl_c=-50.0, ret_pct=-2.0, won=0, stage="call_start", move_24h=0.5),   # late-jump fade
                row(ticker="b", word_scope="external", pnl_c=-40.0, ret_pct=-1.5, won=0),
                row(ticker="c", call_date="2026-09-01"),
                row(ticker="d", call_date="2026-01-05", word_scope="external")]
        r = loss_review.build(rows, date(2026, 10, 27))
        self.assertEqual(len(r.windows["day"]), 2)
        self.assertEqual(len(r.windows["last 30 days"]), 2)
        self.assertEqual(len(r.windows["all history"]), 4)
        skip_jump = loss_review.idea_effect(r.windows["day"], loss_review.IDEAS[0])
        self.assertEqual((skip_jump["affected"], skip_jump["delta_ret"]), (1, 2.0))
        half_ext = loss_review.idea_effect(r.windows["all history"], loss_review.IDEAS[1])
        self.assertEqual(half_ext["affected"], 2)
        self.assertAlmostEqual(half_ext["delta_ret"], -0.5 * (-1.5 + 1.0))
        md = loss_review.render_md(r)
        self.assertIn("I-001", md)
        self.assertIn("Biggest losses", md)

    def test_no_trades(self):
        r = loss_review.build([], date(2026, 10, 27))
        self.assertIn("No graded trades", loss_review.render_md(r))

    def test_sectors(self):
        self.assertEqual(sectors.sector("V", "7389"), "Payments & fintech")
        self.assertEqual(sectors.sector("KO", "2080"), "Consumer goods")
        self.assertEqual(sectors.sector("ZZ", None), "Unknown")
        self.assertEqual(sectors.sector("JPM", "6021"), "Banks & finance")


if __name__ == "__main__":
    unittest.main()
