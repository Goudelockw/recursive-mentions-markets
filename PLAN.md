# Plan

The living checklist. Updated whenever something ships or the plan changes; the reasons behind
changes are in [`docs/decisions/`](docs/decisions/). The visual version is
[`docs/blueprint.html`](docs/blueprint.html).

*Last updated: 2026-10-27 (phase 2 built).*

## Now

- [ ] **Verify the first scheduled Trade Sheet** (Tue Oct 27, 06:41 ET): notification arrives, sheet committed under `outputs/trade-sheets/`, page updated.
- [x] First mentions-only sync verified (03:04 UTC Oct 27): about 2.5 min instead of about 9; refresh 85s instead of 205s
- [x] v2 promoted to live (Oct 27, 03:25 UTC); v1 retired. Models page: `python -m rmm models --page`, refreshed Sundays by the Cost Report task
- [ ] Verify the first `research-weekly` run (Mon Nov 2, 01:00 UTC)
- [x] Railway services `kalshi-worker` (snapshot) and `backfill` deleted (Oct 27). Remaining: `sync`, `reconcile`, `filings`, `transcripts`, `news`
- [x] `refit_models.R` and `mentions_model.R` shared (Oct 27)

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
- [x] Refresh chain: sync skips the 7 transcript-only steps (205s → 85s); filings refreshes only when it stored something new
- [ ] Drop leftover objects (`mv_word_counts_old3/4/5`, `wc_snapshot_20260928`) once the cost report confirms nothing reads them

## Phase 2 · Python research service

- [x] Port `refit_models.R` to Python (`python -m rmm refit`), including R's own random folds (`rmm/rrng.py`)
- [x] Parity: identical coefficients and all 9,130 backtest probabilities vs. `Rscript refit_models.R` on the same data; kept as a test
- [x] First Python refit saved as challenger `v2` (through Oct 26), not promoted
- [ ] Port the research parts of `mentions_model.R` (feature tests, scorecard, bankroll simulation) into the phase 4 scoring harness
- [x] Model versions: `kalshi.model_versions`, `kalshi.promote_model(N)` (owner only), frozen non-challengers; v1 = R fit (live), v2 = Python challenger
- [x] Roles: `rmm_ro` reads; `rmm_rw` stores challengers and `ops` rows, can't touch the live model
- [x] Live grading: `sync` and `filings` call `kalshi.log_model_scores()` after each refresh (the database is awake then anyway)
- [x] `ops` schema and `python -m rmm weekly`: job freshness, transcript gaps, settlement-vs-transcript audit, labels, CHECK DATE, call-time confidence, settlement lag, score logging, model age; live grading; calibration
- [x] Railway service `research-weekly` (Mon 01:00 UTC): `weekly --save --refit`
- [x] Retire R: `refit_models.R` kept only as the parity reference
- [x] Models page: latest release vs. live (forward test + walk-forward head-to-head, Brier and ¢/trade), release history, variable strength and effects (forest charts with 95% intervals), risk model (rules matrix and what it adds), backtest, definitions
- [x] `python -m rmm review`; every weekly challenger is reviewed against the live model and the review is stored with it
- [x] Model Review task (Sundays 22:11 ET): sends the release to you before anything is promoted
- [x] Leading into the call: model vs. market from 14 days to call start (`rmm/horizons.py`, line charts on the Models page)
- [ ] **Test an earlier entry window**: the model's edge over the market is widest 7–14 days out and ¢/trade peaks 2–3 days out (+6.0–6.1¢ vs +5.6¢ at 24h). Check liquidity and spreads that far out before changing ENTRY 1. Phase 4
- [x] **Look into October** (`outputs/experiments/EXP-0001_october-diagnosis/report.md`): news-driven words started getting said far more (28.5% → 39.8% at 24h) and the model kept fading them; at call start, fading late price jumps lost −27¢/trade. Found and fixed two silent pipeline gaps (daily news never ran; no 1-minute candles since Sep 25) and added checks for both
- [ ] **Decide** (owner): skip call-start NO trades that fade a late jump; halve NO stakes on external words until a news feature exists
- [ ] **Test news volume as a feature** for external words once the news backfill lands. Phase 4
- [x] EXP-0002 cross-company word history and industry: no gain as model terms; sector offsets help Sep–Oct but not over the full history (mispriced sectors shift). Shadow-score
- [x] Daily Loss Review (`python -m rmm loss-review`, in the weekday Trade Sheet run): yesterday's trades, loss slices, test ideas I-001…I-003 scored in shadow
- [ ] Retracted: EXP-0001's two rules hurt over the season under the real trading rules (I-001 −19.7%, I-002 −23.9% of bankroll). Keep them in shadow; don't adopt
- [ ] Shadow-score walk-forward sector offsets (EXP-0002) as a model challenger
- [x] Fixed: live Brier and calibration graded on `result = 'YES'` (`won` in `v_mentions_history` means the trade won)

## Phase 3 · Sunday batch

- [x] `ops.fix_requests` + kalshi-worker `ops-fixes` (Railway, daily 03:30 UTC): the weekly batch queues safe re-fetches (transcript gaps, CHECK DATE filings, settlement sweep); `ops-fixes` runs only allowlisted commands and logs each outcome
- [x] Ops task (Sundays 21:41 ET): investigates what needs judgment, drafts proposals with SQL and sources, code fixes on `ops/*` branches, publishes the Weekly Review; you approve with "approve W44-n"
- [x] Weekly Review page (`python -m rmm weekly-review --page`)
- [x] Librarian task (Sundays 22:41 ET) and `python -m rmm librarian`: naming rules, 90-day archive, docs checked against the code, database and Railway job runs, leftover tables as PR-tier migrations, the librarian log
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

- ~~`NEON_API_KEY` for the cost report~~: not now. The report estimates from job runs.
- ~~Rotate the `neondb_owner` password~~: not now.
- ~~Stale Neon branch cleanup in the Librarian~~: needs `NEON_API_KEY` too; nothing creates branches yet. Revisit with phase 4 experiments.

- ~~Grafana board~~: replaced by the Trade Sheet page and the weekly reports.
- ~~15-minute `score-log` cron~~: replaced by logging at Trade Sheet time.
- ~~Daily full-exchange sync~~: the database holds only the markets being traded.
