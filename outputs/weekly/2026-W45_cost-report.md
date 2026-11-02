# Cost Report · 2026-W45

_Generated 2026-11-02 01:41 UTC. Neon Launch rates: $0.106/CU-hour, $0.35/GB-month. Neon suspends after 5 min without queries._

## Summary

- **Billed compute:** not available (no `NEON_API_KEY`). The figures below are estimates from job runs.
- **Job runs keep the database awake about 53h a week** (32% of the week)
- **Storage:** 1.71 GB, about $0.60/month

## What to change

1. `sync` had 2 run(s) with no finish time (crashed or redeployed mid-run).
2. The 18-step refresh chain ran about 306 times (44 a day) after sync, filings and transcripts. Most steps only change when transcripts or filings do. Refreshing them only then would cut about 3 minutes from every other run.
3. `kalshi.candles` is 0.8 GB. Check it holds only what the models use.
4. 5 leftover copies (`role_snapshot_20260928`, `mv_word_counts_old5`, `mv_word_counts_old4`, `mv_word_counts_old3`, `wc_snapshot_20260928`, 11 MB in all). The Librarian can open a PR to drop them.
5. Add `NEON_API_KEY` (a project-scoped Neon API key) to the cloud environment so the report can show billed compute instead of estimating it from job runs.

## Jobs, last 7 days

Awake hours: how long the job alone would keep the database awake, counting 5 min after each run.

| Job | Runs | Running (h) | Awake alone (h) | Failed | Cut off |
|---|--:|--:|--:|--:|--:|
| snapshot | 293 | 0.0 | 24.4 | 0 | 0 |
| sync | 168 | 9.5 | 23.5 | 0 | 2 |
| filings | 131 | 2.5 | 13.4 | 0 | 0 |
| reconcile | 7 | 3.0 | 3.6 | 0 | 0 |
| ops-fixes | 6 | 2.5 | 3.0 | 0 | 0 |
| news_backfill | 1 | 2.2 | 2.3 | 0 | 0 |
| news | 7 | 1.0 | 1.5 | 0 | 0 |
| fortune | 14 | 0.2 | 1.0 | 0 | 0 |
| equibles | 8 | 0.0 | 0.7 | 0 | 0 |
| transcripts | 7 | 0.0 | 0.6 | 0 | 0 |
| reactions | 6 | 0.0 | 0.5 | 0 | 0 |

## Largest tables

| Table | Kind | Size | Reads |
|---|---|--:|--:|
| kalshi.candles | table | 783 MB | 562,924,883 |
| kalshi.transcripts | table | 292 MB | 604,451 |
| kalshi.transcript_segments | table | 202 MB | 1,411,052 |
| kalshi.mv_segment_tsv | matview | 93 MB | 2,766,922 |
| kalshi.filings | table | 58 MB | 266,042 |
| kalshi.mv_word_corpus_hits | matview | 53 MB | 13,237,166 |
| kalshi.markets | table | 33 MB | 287,257,387 |
| kalshi.mkt_word_hits | table | 27 MB | 40,761 |
| kalshi.stock_prices | table | 23 MB | 264,622 |
| kalshi.model_predictions | table | 22 MB | 22 |
| kalshi.news_articles | table | 22 MB | 60,690 |
| kalshi.mv_model_input | matview | 12 MB | 74,490 |

## Recommendations

This is the first cost report, so there's no earlier week to compare against. Average compute size (CU) isn't in
the report without `NEON_API_KEY`, which you've set aside for now, so savings are given in awake hours. Each awake
hour costs $0.106 × the endpoint's CU.

1. **Nothing to do about `snapshot`.** It's the largest single item (24.4 awake h on its own), but it stopped on
   Oct 27 at 02:05 when the Atlanta snapshot was shut off. It falls out of next week's window. Expect total awake time
   to drop well below this week's 53 h without any change.
2. **Pause the hourly `sync` from midnight to 6am ET** (Railway `sync` cron, kalshi-worker). It's now the main thing
   keeping Neon awake: 23.5 awake h a week, 168 runs averaging 3.4 min. No calls and few new markets happen
   overnight. Skipping 6 of 24 hours would save about 23.5 × 6/24 ≈ **5.9 awake h a week**.
3. **Drop the 5 leftover copies** (11 MB). Storage saving is negligible (about $0.004/month at $0.35/GB), but it
   tidies the schema. The Librarian will open the migration branch on its Sunday run.

Not a recommendation: the 2 cut-off `sync` runs line up with this week's kalshi-worker deploys (Oct 27–28), which
restart running services. They aren't a fault.
