import unittest

from rmm import weekly as w


class WeeklyRenderTest(unittest.TestCase):
    def test_failures_first_and_live_lines(self):
        checks = [w.Check("job:sync", "ok", 1, "sync: last ok 1.0h ago"),
                  w.Check("score_log", "warn", 0, "0 scores logged this week"),
                  w.Check("job:news", "fail", None, "news: no successful run in 7 days")]
        metrics = []
        for seg in ("live_7d", "live_30d", "live_90d"):
            metrics += [w.Metric("trades", seg, 2, 2), w.Metric("pnl_c_per_trade", seg, 28.9, 2),
                        w.Metric("win_rate", seg, 0.5, 2), w.Metric("brier_model", seg, 0.35, 2),
                        w.Metric("brier_market", seg, 0.39, 2)]
        text = w.render(checks, metrics)
        lines = text.splitlines()
        self.assertTrue(lines[1].startswith("  FAIL"))
        self.assertTrue(lines[2].startswith("  WARN"))
        self.assertIn("2 trades, +28.9c/trade, 50% won; Brier 0.3500 vs market 0.3900 on 2 markets", text)


if __name__ == "__main__":
    unittest.main()
