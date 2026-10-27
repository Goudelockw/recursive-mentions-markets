import unittest
from datetime import datetime, timedelta, timezone

from rmm import cost_report as cr

T0 = datetime(2026, 10, 19, tzinfo=timezone.utc)


def runs_old_pipeline():
    """A week shaped like the pipeline before Oct 27: a 5-minute snapshot, a 9-minute hourly sync
    and a 3-hour nightly reconcile."""
    out = []
    for i in range(7 * 24 * 12):
        s = T0 + timedelta(minutes=5 * i)
        out.append({"job": "snapshot", "started_at": s, "finished_at": s + timedelta(seconds=1), "ok": True})
    for h in range(7 * 24):
        s = T0 + timedelta(hours=h)
        out.append({"job": "sync", "started_at": s, "finished_at": s + timedelta(minutes=9), "ok": True})
    for d in range(5):
        for k in range(26):
            s = T0 + timedelta(days=d, hours=14, minutes=30 * k)
            out.append({"job": "filings", "started_at": s, "finished_at": s + timedelta(minutes=1), "ok": True})
    for d in range(7):
        s = T0 + timedelta(days=d, hours=4)
        out.append({"job": "reconcile", "started_at": s, "finished_at": s + timedelta(hours=3), "ok": True})
    out.append({"job": "sync", "started_at": T0 + timedelta(days=6, hours=23, minutes=30), "finished_at": None, "ok": None})
    return out


RELS = [
    {"schema_name": "kalshi", "name": "markets", "kind": "table", "bytes": 24 * 1024**3, "reads": 10},
    {"schema_name": "kalshi", "name": "mv_word_counts_old3", "kind": "matview", "bytes": 8 * 1024**2, "reads": 0},
    {"schema_name": "kalshi", "name": "model_predictions", "kind": "table", "bytes": 22 * 1024**2, "reads": 0},
    {"schema_name": "kalshi", "name": "candles", "kind": "table", "bytes": 700 * 1024**2, "reads": 5},
]


class CostReportTest(unittest.TestCase):
    def test_union_of_awake_windows(self):
        s = T0
        iv = [(s, s + timedelta(minutes=10)), (s + timedelta(minutes=5), s + timedelta(minutes=20)),
              (s + timedelta(hours=1), s + timedelta(hours=1, minutes=6))]
        self.assertAlmostEqual(cr._union_hours(iv), (20 + 6) / 60)

    def test_snapshot_keeps_it_awake_all_week(self):
        jobs, awake = cr.job_costs(runs_old_pipeline())
        self.assertEqual(jobs[0].job, "snapshot")
        self.assertGreater(jobs[0].awake_hours, 167)
        self.assertGreater(awake, 167)
        sync = next(j for j in jobs if j.job == "sync")
        self.assertEqual(sync.cut_off, 1)
        self.assertAlmostEqual(sync.awake_hours, 168 * 14 / 60, delta=0.5)

    def test_suggestions_name_the_causes(self):
        r = cr.build(runs_old_pipeline(), RELS, None, [], T0 + timedelta(days=7))
        text = "\n".join(r.suggestions)
        self.assertIn("`snapshot` ran 2016 times", text)
        self.assertIn("`reconcile` spent 21.0h running", text)
        self.assertIn("refresh chain", text)
        self.assertIn("`kalshi.markets` is 24.0 GB", text)
        self.assertIn("`mv_word_counts_old3`", text)
        self.assertIn("`model_predictions` (22 MB)", text)
        self.assertIn("NEON_API_KEY", text)

    def test_week_from_ledger(self):
        prev = cr.Usage(T0, "2026-10-01", 2_000_000, 1_600_000, 0)
        now = cr.Usage(T0 + timedelta(days=7), "2026-10-01", 2_000_000 + 7 * 3600 * 4, 1_600_000 + 7 * 3600 * 6, 0,
                       0.25, 8, 0)
        r = cr.build([], [], now, [prev], now.taken_at)
        w = r.week
        self.assertAlmostEqual(w["cu_hours"], 28)
        self.assertAlmostEqual(w["awake_pct"], 25)
        self.assertIn("Autoscaling goes up to 8 CU", "\n".join(r.suggestions))
        md = cr.render_md(r)
        self.assertIn("28.0 CU-hours", md)
        self.assertIn("suspends after 5 min", md)

    def test_new_billing_period_has_no_week(self):
        prev = cr.Usage(T0, "2026-10-01", 9, 9, 0)
        now = cr.Usage(T0 + timedelta(days=7), "2026-11-01", 1, 1, 0)
        self.assertIsNone(cr.build([], [], now, [prev], now.taken_at).week)


if __name__ == "__main__":
    unittest.main()
