# EXP-0001 · Why the model trails the market since October 9

Oct 28, 2026 · Data: every settled mentions market, Jan 2025 – Oct 27 2026 (`v_model_training`),
scored by v2's walk-forward backtest (out of sample every month) and by v1 frozen. Trades use the
sheet's rule: edge of 2¢+ after fees at that entry's quote. Bootstrap ranges resample whole calls.

## Short answer

1. **News-driven ("external") words started getting said much more often, and the model kept
   betting NO on them.** Fading external words was the model's best trade all year. In September
   and October it stopped working at both entry points.
2. **At call start, the worst losses are trades against a late price jump.** When a word's price
   jumped in the final 24 hours, the market knew something. The model bet against it and lost
   −27¢ a trade (26 trades, 88% of those words were said). Skipping those trades would have cost
   nothing from January to August.
3. **Two pipeline gaps** were found along the way and fixed. Neither caused the losses, but both
   left the model and the call-time estimates working with less than they should have.

## 1. It's a September–October change, mostly at call start

| | Jan–Aug 2026 | Sep–Oct 2026 |
|---|---|---|
| Call start: ¢ per trade (90% range) | **+5.0** (+3.1 to +7.0) | **−4.8** (−11.8 to +2.3) |
| Call start: market overprices YES by (pts) | +2.9 (+1.8 to +4.1) | −1.5 (−3.8 to +0.9) |
| 24h before: ¢ per trade | +5.5 (+3.3 to +7.4) | +4.0 (−1.5 to +8.9) |
| 24h before: market overprices YES by (pts) | +3.7 (+2.4 to +4.9) | +1.6 (−0.9 to +3.9) |

The model's edge comes from the market overpricing YES (words get said less than the price
implies). In Sep–Oct that overpricing shrank at 24h and disappeared at call start.

## 2. External words broke; own-business words are fine

24h entry, NO trades (the sheet's main entry):

| Word scope | Jan–Aug ¢/trade | Jan–Aug said | Sep–Oct ¢/trade | Sep–Oct said |
|---|---|---|---|---|
| External (macro, politics, other companies) | **+7.2** (593) | 28.5% | **−0.4** (118) | 39.8% |
| Own business | +3.9 (618) | 41.7% | **+10.3** (84) | 38.1% |

External words went from said 28.5% of the time to 39.8%. The market moved only part of the way
(38.8% → 42.7%), and the model, which leans on how often a word came up on past calls, barely
moved. The losers are this autumn's news topics: Iran / Middle East, tariffs, Anthropic / Claude,
OpenAI, Google, mergers, air traffic control.

## 3. At call start, don't bet against a late jump

NO trades at call start where the price rose more than 0.3 log-odds in the final 24h:

| Period | Trades | ¢/trade | Rest of call-start trades |
|---|---|---|---|
| 2025 H2 | 75 | +18.4 | +10.2 |
| Jan–Aug 2026 | 463 | +5.1 | +5.0 |
| **Sep–Oct 2026** | **26** | **−27.3** | **−0.2** |

These 26 trades are 711¢ of the 737¢ lost at call start in Sep–Oct. None of the words was in the
earnings release, and the price lookup uses only candles that end before the call. So this is the
market pricing in real pre-call news, not a data leak.

## 4. Pipeline gaps found (fixed Oct 28)

- **Daily news counts never ran.** `news` read upcoming calls from `mv_call_times`, which only
  holds settled events, so every daily run since Sep 29 found 0 markets and wrote 0 rows, while
  reporting success. Everything in `news_counts` came from one backfill on Sep 29. Fixed in
  kalshi-worker `f477632` (reads `v_upcoming_call_times`); October backfill queued.
- **No 1-minute candles since Sep 25.** They came only from hand-run `reactions` backfills.
  `mv_call_times` needs them for `first_lock`, the most reliable call-start time, so all 24
  calls settled in the last 14 days have an estimated start. `reconcile` now runs `reactions`
  nightly; October backfill queued.
- **New weekly checks** catch both kinds of silent failure: a job that runs fine all week but
  writes nothing, and settled calls with no 1-minute lock time (which also queues `reactions`).

## What to decide (owner)

These change how money is traded, so they are yours to approve:

1. **Call start: skip NO trades that fade a late jump** (price up 0.3+ log-odds in the last 24h).
   Costless from January to August, and it would have avoided almost all of Sep–Oct's call-start
   loss. Cost: it gave up edge in 2025 H2, when those trades were the best ones.
2. **External words: halve the stake on NO trades until the model has a news feature.** This is a
   judgment call. Two months (118 trades at 24h) is a short run, and the 90% range still includes
   a positive edge. But the cause is plausible and still going (a heavy news cycle).

## Next (phase 4 research)

- Once the news backfill lands, test news volume ("company + word" articles in the 14 days before
  the call) as a feature for external words. That is the direct fix for finding 2.
- Add "price move since 24h" to the call-start model. The model already has it (`move24`), but its
  effect looks regime-dependent; test an interaction with scope.
- Re-run this report after November's calls to see whether the external-word shift holds.
