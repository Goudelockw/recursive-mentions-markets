# Cost Report · 2026-W46

_Generated 2026-11-09 01:43 UTC. Neon Launch rates: $0.106/CU-hour, $0.35/GB-month. Neon suspends after 5 min without queries._

## Summary

- **Billed compute:** not available (no `NEON_API_KEY`). The figures below are estimates from job runs.
- **Job runs keep the database awake about 32h a week** (19% of the week)
- **Storage:** 1.81 GB, about $0.63/month

## What to change

1. The 18-step refresh chain ran about 305 times (44 a day) after sync, filings and transcripts. Most steps only change when transcripts or filings do. Refreshing them only then would cut about 3 minutes from every other run.
2. `kalshi.candles` is 0.8 GB. Check it holds only what the models use.
3. 5 leftover copies (`role_snapshot_20260928`, `mv_word_counts_old5`, `mv_word_counts_old4`, `mv_word_counts_old3`, `wc_snapshot_20260928`, 11 MB in all). The Librarian can open a PR to drop them.
4. Add `NEON_API_KEY` (a project-scoped Neon API key) to the cloud environment so the report can show billed compute instead of estimating it from job runs.

## Jobs, last 7 days

Awake hours: how long the job alone would keep the database awake, counting 5 min after each run.

| Job | Runs | Running (h) | Awake alone (h) | Failed | Cut off |
|---|--:|--:|--:|--:|--:|
| sync | 168 | 6.9 | 20.9 | 0 | 0 |
| filings | 130 | 2.5 | 13.4 | 0 | 0 |
| news | 7 | 2.4 | 3.0 | 0 | 0 |
| fortune | 7 | 0.1 | 0.7 | 0 | 0 |
| reconcile | 7 | 0.1 | 0.7 | 0 | 0 |
| transcripts | 7 | 0.1 | 0.6 | 0 | 0 |
| equibles | 7 | 0.0 | 0.6 | 0 | 0 |
| reactions | 7 | 0.0 | 0.6 | 0 | 0 |
| ops-fixes | 7 | 0.0 | 0.6 | 0 | 0 |

## Largest tables

| Table | Kind | Size | Reads |
|---|---|--:|--:|
| kalshi.candles | table | 844 MB | 599,214,458 |
| kalshi.transcripts | table | 301 MB | 614,438 |
| kalshi.transcript_segments | table | 203 MB | 1,425,667 |
| kalshi.mv_segment_tsv | matview | 95 MB | 3,195,468 |
| kalshi.filings | table | 59 MB | 311,818 |
| kalshi.mv_word_corpus_hits | matview | 54 MB | 18,041,015 |
| kalshi.markets | table | 33 MB | 287,558,068 |
| kalshi.mkt_word_hits | table | 27 MB | 40,761 |
| kalshi.news_articles | table | 27 MB | 84,286 |
| kalshi.stock_prices | table | 23 MB | 287,560 |
| kalshi.model_predictions | table | 22 MB | 22 |
| kalshi.cleanup_log | table | 19 MB | 17 |

## Recommendations

Compared with W45: awake time fell from about 53 h to 32 h a week, as last week predicted. `snapshot` (24.4 h)
dropped out of the window after it was shut off on Oct 27. Storage grew from 1.71 GB to 1.81 GB, adding about
$0.03/month. Average compute size (CU) isn't in the report without `NEON_API_KEY`, so savings are in awake hours.
Each awake hour costs $0.106 × CU.

1. **Pause the hourly `sync` from midnight to 6am ET** (Railway `sync` cron, kalshi-worker). This was recommended
   last week and **not acted on**: there were still 168 runs this week. `sync` is now the largest item at 20.9 awake h
   a week. Skipping 6 of 24 hours saves about 20.9 × 6/24 ≈ **5.2 awake h a week (≈ 22 h/month ≈ $2.40 × CU a month)**.
2. **Refresh the 18-step chain only after transcripts or filings change** (kalshi-worker `db.refresh_word_counts`
   callers). The report says this cuts about 3 minutes from most of the chain's 305 runs a week. That doesn't square
   with `sync` averaging only 2.5 minutes a run (6.9 h / 168), so check the figure before relying on it. The saving
   **can't be estimated reliably** from this report.
3. **Drop the 5 leftover copies** (11 MB, about $0.004/month). This was recommended last week and **not acted on**,
   because the Librarian's Nov 2 run didn't happen. Its run tonight should open the migration branch.
