# 2026-10-27 · Operating plan

## Decisions

1. **Daily output is only the trade sheet.** About a dozen markets settle each week, so a daily
   evaluation repeats itself and keeps Neon awake. The sheet is one board read on weekdays.
2. **Everything else runs once a week, on Sunday night,** back to back: health checks, grading,
   refit, Ops fixes, Weekly Review, Librarian.
3. **Refit weekly, switch the live model only on evidence.** The Sunday refit is saved as a
   challenger. The Weekly Review shows how far coefficients and k moved. The live model changes at the
   end of a season, when drift is material, or through the fast track. The backtest was walk-forward by
   month, so weekly live switching would be an untested procedure.
4. **Fast track for a clearly better model.** A challenger may go live without waiting when it beats the
   live model on the sealed holdout by more than the multiple-testing bar, holds in both periods and in
   90%+ of resamples, passes the leakage review and has a plausible mechanism. It then trades at half
   stake for its first weeks and rolls back automatically if live results leave the backtest's range.
   Bug fixes are not model changes and ship as fixes.
5. **Research covers every layer,** each with its own score: pricing (how to read the price), fundamental
   (Brier / log loss without price), combined (Brier vs. market, ¢/trade), risk (extra losses per 100 in
   both periods, plus re-validating existing rules), trading rules and timing (¢/trade on affected trades,
   higher bar), sizing (shown as a trade-off; always the owner's call).
6. **Two levels of checks.** Daily, the trade sheet checks each market it lists (transcript history,
   fundamental score, quote age, labels, call-time source) and marks failures `DATA ISSUE`. Weekly, the
   Sunday batch checks that the pipeline ran, the data is complete, and the data is accurate, including
   settled results against our own transcript counts.
7. **R is retired** once the Python refit reproduces the current coefficients and backtest (phase 2).
8. **AI runs as Claude scheduled tasks on the subscription.** Heavy computation stays in Python so the
   tasks only read summaries.
9. **Outputs are dated files committed to this repo,** named by `rmm/paths.py`, and kept tidy by a
   weekly Librarian task.
