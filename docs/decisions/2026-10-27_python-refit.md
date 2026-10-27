# 2026-10-27 · R refit ported to Python

`refit_models.R` is now `python -m rmm refit` (`rmm/refit.py`).

- **Parity is exact.** On the same data (v_model_training through 2026-10-09), the Python refit gives
  the same coefficients as `Rscript refit_models.R` (largest difference 1e-7, from R's 8-digit
  rounding) and the same backtest probability for all 9,130 markets. To get there, `rmm/rrng.py`
  reproduces R's `set.seed` / `sample`, so the out-of-fold folds are R's. The data and R's outputs
  are kept in `tests/fixtures/parity/` and checked on every test run.
- **The live coefficients no longer match a refit through Oct 9** (differences up to ~0.05). R and
  Python agree with each other on today's data, so this is the data changing since the Oct 13 fit
  (transcripts, labels), not the code.
- **A refit never writes to the database.** It is a challenger saved under
  `outputs/models/vN_<trained through>/`. The R script deleted and rewrote `model_coefficients`;
  promotion is now its own step (phase 2: `model_version`).
- `v_model_training` names its date column `call_date_est`, so the R script would fail against it
  today. The port reads either name.
- First Python refit: `v2`, trained through 2026-10-26 on 6,222 markets. Walk-forward Brier at call
  start 0.1595 vs. 0.1626 for the price; k 0.669 (call start) and 0.758 (early), down from 0.711 and
  0.796. Not promoted.
