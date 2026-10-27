# Plan

The living checklist. Updated whenever something ships or the plan changes; the reasons behind
changes are in [`docs/decisions/`](docs/decisions/). The visual version is
[`docs/blueprint.html`](docs/blueprint.html).

*Last updated: 2026-10-27.*

## Now

- [ ] **Verify the first scheduled Trade Sheet** (Tue Oct 27, 06:41 ET): notification arrives, sheet committed under `outputs/trade-sheets/`, page updated.
- [ ] **Verify the first mentions-only sync** (03:00 UTC Oct 27). A check is scheduled for 03:20 UTC.
- [ ] **Delete the `kalshi-worker` and `backfill` Railway services** (both already disabled). *Owner: you. Railway's delete confirmation hasn't reached you through Claude, so delete them in the dashboard.*
- [ ] **Share `refit_models.R` and `mentions_model.R`**, which phase 2 ports to Python. They aren't in either repo. *Owner: you.*
- [ ] Optional: add `NEON_API_KEY` (project-scoped) so the cost report shows billed dollars. *Owner: you.*
- [ ] Rotate the `neondb_owner` password: it was shared in chat earlier (SYSTEM.md open item). Railway's `DATABASE_URL` must be updated in the same step.

## Phase 1 · Repo and the daily Trade Sheet

- [x] Repo layout, naming rules (`rmm/paths.py`), README, SYSTEM.md, decision log
- [x] `python -m rmm trade-sheet`: md / csv / html, per-market data checks, risk-model reads, call caps, risk map
- [x] Trade Sheet page, live
- [x] `main` branch, read-only `rmm_ro` role, Neon over HTTPS from cloud sessions
- [x] Weekday 06:41 ET scheduled task
- [ ] First run verified (see *Now*)

## Cost and data cleanup (added Oct 27)

- [x] Sync and reconcile limited to earnings mentions (`kalshi-worker` `main`)
- [x] Order-book snapshot and finished backfill disabled; Atlanta watchlist entry removed
- [x] Non-mention data deleted: 34 GB → 2.3 GB
- [x] Weekly Cost Report (`python -m rmm cost-report`), Sundays 20:41 ET
- [ ] First cost report reviewed (Sun Nov 1)
- [ ] Refresh chain: refresh the transcript and filing steps only when those change (~3.5 min a run today)
- [ ] Drop leftover objects (`mv_word_counts_old3/4/5`, `wc_snapshot_20260928`) once the cost report confirms nothing reads them

## Phase 2 · Python research service

- [ ] Port `refit_models.R` to Python; parity test against the current coefficients and backtest
- [ ] `model_version` on `model_coefficients`; refits write challengers, never the live model
- [ ] Live grading: log the board's scores when the Trade Sheet runs (replaces the planned 15-minute `score-log` cron; needs a role that may write `model_score_log` only)
- [ ] `ops` schema and `research weekly`: health checks, grading, calibration, transcript-vs-settlement accuracy check
- [ ] Railway service for `research` (Sunday batch)
- [ ] Retire R

## Phase 3 · Sunday batch

- [ ] Ops task: fixes data gaps (Auto / PR / Ask tiers), writes the Weekly Review
- [ ] Librarian task: naming, archive, stale Neon branches, SYSTEM.md upkeep
- [ ] Daily labeling for markets listed mid-week (SYSTEM.md open item)
- [ ] Release-window fix for wrong ticker dates (SYSTEM.md open item)

## Phase 4 · Research loop

- [ ] Fixed scoring rules, sealed holdout, multiple-testing bar
- [ ] Experiment ledger, backfilled with ideas already tested
- [ ] Monthly Research task (pricing, fundamental, combined, risk, rules, sizing)
- [ ] Shadow scoring, end-of-season switches, fast track with half stake and auto-rollback

## Phase 5 · Other markets

- [ ] Market-type plug-in: universe, features, label, price prior, rules
- [ ] Widen `FOCUS_SERIES_PREFIXES` for the new type

## Dropped

- ~~Grafana board~~: replaced by the Trade Sheet page and the weekly reports.
- ~~15-minute `score-log` cron~~: replaced by logging at Trade Sheet time.
- ~~Daily full-exchange sync~~: the database holds only the markets being traded.
