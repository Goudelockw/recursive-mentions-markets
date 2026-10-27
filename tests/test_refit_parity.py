"""The Python refit must reproduce refit_models.R exactly.

Fixtures (tests/fixtures/parity/): v_model_training as of 2026-10-27, cut to calls through
2026-10-09, in refit_models.R's CSV format (tickers without the KXEARNINGSMENTION prefix), and the
model_coefficients / model_backtest that `Rscript refit_models.R <that csv>` wrote from it.
"""
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from rmm import refit
from rmm.rrng import RRandom

FIX = Path(__file__).parent / "fixtures" / "parity"


def training():
    d = pd.read_csv(FIX / "v_model_training_through_2026-10-09.csv.gz", keep_default_na=True)
    for c in ("ticker", "event_ticker"):
        d[c] = "KXEARNINGSMENTION" + d[c].astype(str)
    return d


class RRandomTest(unittest.TestCase):
    def test_matches_r_sample(self):
        lines = (FIX / "r_sample_seed2024.txt").read_text().split("\n")
        for line, n in zip(lines, (23, 301)):
            want = [int(v) for v in line.split()]
            got = [int(v) for v in RRandom(2024).sample(list(np.resize(np.arange(1, 6), n)))]
            self.assertEqual(got, want)


class RefitParityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = refit.run(training())

    def test_coefficients_match_r(self):
        want = pd.read_csv(FIX / "r_model_coefficients.csv")
        c = refit.compare(self.r.coefficients, want)
        self.assertFalse(c[["coef_new", "coef_live"]].isna().any().any(), "same terms in both")
        self.assertLess(c["diff"].abs().max(), 1e-6)
        self.assertEqual(self.r.trained_through, "2026-10-09")

    def test_backtest_matches_r(self):
        want = pd.read_csv(FIX / "r_model_backtest.csv.gz")
        m = self.r.backtest.merge(want, on=["ticker", "stage"], suffixes=("_py", "_r"))
        self.assertEqual(len(m), len(want))
        self.assertEqual(len(m), len(self.r.backtest))
        self.assertLess((m["p_model_py"] - m["p_model_r"]).abs().max(), 1e-9)

    def test_backtest_summary(self):
        cs = next(s for s in self.r.stages if s.stage == "call_start")
        self.assertEqual(len(cs.backtest), 4668)
        self.assertAlmostEqual(cs.brier_model, 0.1592, places=4)
        self.assertAlmostEqual(cs.brier_price, 0.1629, places=4)


if __name__ == "__main__":
    unittest.main()
