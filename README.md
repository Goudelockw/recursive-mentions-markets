# recursive-mentions-markets

The decision and research layer on top of [`kalshi-worker`](https://github.com/Goudelockw/kalshi-worker).
`kalshi-worker` collects the data into Neon (schema `kalshi`); this repo turns it into a daily
trade sheet, checks the pipeline and the model's inputs every week, and runs the research loop
that proposes, tests and promotes model changes.

What is done and what is next is in [`PLAN.md`](PLAN.md). How the whole system works today is in [`SYSTEM.md`](SYSTEM.md). Why things changed is in
[`docs/decisions/`](docs/decisions/).

## What runs when (Eastern time)

| When | What | Who | Output |
|---|---|---|---|
| Weekdays 06:41 | Trade Sheet | Claude scheduled task, runs `python -m rmm trade-sheet` | `outputs/trade-sheets/YYYY-MM/YYYY-MM-DD_trade-sheet.{md,csv,html}`, the pinned Trade Sheet page, push + email |
| Sunday 20:41 | Cost Report: what Neon costs, which jobs drive it, what to change | Claude scheduled task, runs `python -m rmm cost-report` | `outputs/weekly/YYYY-Www_cost-report.md`, `outputs/costs/neon-usage.csv`, push |
| Sunday ~21:00 (Mon 01:00 UTC) | Weekly checks, live grading, calibration, challenger refit | Railway `research-weekly`: `python -m rmm weekly --save --refit` | `ops.*` tables, a challenger in `kalshi.model_versions` |
| Sunday 21:41 | Ops: fix data gaps, write the Weekly Review | Claude scheduled task | `outputs/weekly/YYYY-Www_weekly-review.md` *(phase 3)* |
| Sunday 22:41 | Librarian: keep the repo, outputs and Neon tidy | Claude scheduled task | `outputs/weekly/YYYY-Www_librarian-log.md` *(phase 3)* |
| 1st Monday | Research: diagnose misses, test ideas, open one PR | Claude scheduled task | `outputs/experiments/EXP-NNNN_<slug>/report.md` *(phase 4)* |

The scheduled tasks run on the Claude subscription. No API key is used anywhere.

## Layout

```
rmm/                 Python package (python -m rmm <command>)
  paths.py           the output naming convention; nothing else builds output paths
  trade_sheet.py     daily trade sheet: classify, check, render md / csv / html
  cost_report.py     weekly Neon cost breakdown and rule-based suggestions
  db.py              read-only Neon access
sql/queries/         the read-only queries the code and the scheduled tasks run
agents/<task>/       one folder per scheduled task: its prompt and its permissions
outputs/             everything the system produces, dated, committed
  trade-sheets/YYYY-MM/
  weekly/
  models/vN_YYYY-MM-DD/
  experiments/EXP-NNNN_<slug>/
  costs/neon-usage.csv   Neon usage ledger, one row per cost report
  archive/           outputs older than 90 days (moved by the Librarian)
docs/decisions/      one dated note per decision
tests/               DATABASE_URL=... NEON_API_KEY=... python -m rmm cost-report   # weekly cost report

python -m rmm refit [--save]          # Python port of refit_models.R; --save stores a challenger (rmm_rw)
python -m rmm models                  # model versions; promote with: select kalshi.promote_model(N);
python -m rmm weekly [--save]         # health checks, live grading, calibration

python -m unittest discover tests
```

## Naming rules

- Dates first, ISO: `2026-10-27_` for daily outputs, `2026-W44_` for weekly ones.
- Then the kind of output in lowercase kebab-case: `_trade-sheet`, `_weekly-review`.
- Experiments get a permanent ID and a slug: `EXP-0007_news-volume/`.
- Models are named by version and fit date: `v8_2026-11-01/`, matching `model_version` in Neon.
- Build paths with `rmm.paths`, never by hand. The Librarian checks `outputs/` against it.

## Commands

```
pip install -r requirements.txt
DATABASE_URL=... python -m rmm trade-sheet          # query Neon and write today's sheet

# without DATABASE_URL: run sql/queries/trade_sheet.sql and trade_sheet_preflight.sql
# elsewhere (e.g. the Neon connector), save the results as JSON, then
python -m rmm trade-sheet --board board.json --preflight preflight.json

python -m unittest discover tests
```

## The trade sheet

Read from `kalshi.v_mentions_board` for calls today and tomorrow, so it always matches the board.

- **Status:** `READY`, `CHECK` (something in *Needs you*) or `STOP` (a pipeline job or the quotes are
  stale: don't trade off the sheet until the board is checked).
- **Trades,** grouped by call in time order, with the entry window, cost of the side to buy, spread,
  market vs. model probability, edge after fees, stake and the call's total against the 6% cap.
- **vs. risk model:** `Aligned` (TRADE+: fading an AVOID favorite), `Neutral` (backing or fading a
  favorite the risk model has no view on), `No read` (thin history), `Conflict` (skipped because the
  model wanted the side the risk model distrusts).
- **Data checks per market:** transcript history, fundamental score, quote age, valence and incentive
  labels. A trade that fails one is marked `DATA ISSUE` and listed under *Needs you*.
- **Needs you:** calls whose estimated time passed with no release (`CHECK DATE`), data issues, calls
  over their cap, and estimated call times in the current entry window.
- **Risk map:** each trade placed by the favorite's price range and avoid points.
