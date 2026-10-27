# 2026-10-27 · Mentions-only data and a weekly cost report

## What was happening

Neon had been awake without a break since Sep 20: about 748 CU-hours (roughly $79) in the first 26
days of October, plus about 34 GB of storage.

- The order-book snapshot ran every 5 minutes for one Atlanta temperature series, which alone stopped
  Neon from ever suspending.
- The hourly sync pulled every open event on Kalshi (225s) and swept 20,000 stale markets (106s).
- The nightly reconcile pulled daily candles for ~294,000 settled markets (2.9h).
- `markets` held 7.8M rows (24 GB). 8,230 of them were earnings-mention markets.

## What changed

1. `kalshi-worker` sync and reconcile cover only `KXEARNINGSMENTION*` series (plus the watchlist,
   now empty). `sync --full` and `RECONCILE_ALL=1` still reach the whole exchange.
2. The snapshot (`kalshi-worker` service) and the finished `backfill` service were switched to no-op
   start commands. The `KXHIGHATL` watchlist row was deleted.
3. Everything but earnings-mention markets was deleted: `markets` 7.8M → 8,230 rows, `candles`
   8.2M → 1.15M, `events` 876k → 592, `series` 15k → 178, plus the empty `trades` and
   `book_snapshots`. The database went from about 34 GB to 2.3 GB. Rows were copied aside, the tables
   truncated and the kept rows re-inserted, all checked by count before and after.
4. A weekly Cost Report (`python -m rmm cost-report`, Sundays) tracks billed usage through a ledger
   and suggests the next savings.

## Not changed yet

The 18-step refresh chain (~3.5 min) still runs after every sync, filings and transcripts run. The
first cost report will show what it costs now that the rest is gone.
