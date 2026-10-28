# Models

_Generated 2026-10-28 03:03 UTC from `kalshi.model_versions`. Promote with `select kalshi.promote_model(N);` (database owner only); promote the previous version to roll back._

## Release history

### v3 · challenger · trained through 2026-10-27

**Better vs v2.** Lower Brier at both entry points in the walk-forward head-to-head, better in up to 100% of resamples.

| Entry point | Test | Markets | Price | Old | New | Better in | Old ¢/trade | New ¢/trade |
|---|---|--:|--:|--:|--:|--:|--:|--:|
| early_24h | forward | 66 | 0.1028 | 0.1067 | 0.1084 | 9% | -10.4 | -6.8 |
| early_24h | walk_forward | 4854 | 0.1726 | 0.1684 | 0.1680 | 100% | +5.5 | +6.2 |
| call_start | forward | 66 | 0.0953 | 0.1010 | 0.1026 | 2% | -19.8 | -11.7 |
| call_start | walk_forward | 5070 | 0.1626 | 0.1595 | 0.1592 | 99% | +5.2 | +5.6 |

Pruned spec (EXP-0003): drops r4, corpus_rare, analysts_n, said_yoy/has_yoy, ext/politics, and filing_said in the call-start fundamental model; dropped terms stored at 0.

### v2 · live · trained through 2026-10-26 · live 2026-10-27

**No clear difference vs v1.** Mixed or small differences in the forward test (better in 15%–59% of resamples).

| Entry point | Test | Markets | Price | Old | New | Better in | Old ¢/trade | New ¢/trade |
|---|---|--:|--:|--:|--:|--:|--:|--:|
| early_24h | forward | 392 | 0.1707 | 0.1715 | 0.1714 | 59% | +1.7 | +0.2 |
| early_24h | walk_forward | 145 | 0.1786 | 0.1705 | 0.1704 | 94% | +3.7 | +3.7 |
| call_start | forward | 402 | 0.1595 | 0.1620 | 0.1622 | 15% | -4.4 | -5.6 |
| call_start | walk_forward | 160 | 0.1559 | 0.1543 | 0.1543 | 71% | -0.3 | -0.3 |

First Python refit (exact port of refit_models.R).

### v1 · retired · trained through 2026-10-09 · live 2026-10-27 → retired 2026-10-27

The live model before versioning: R fit of 2026-10-13, trained through 2026-10-09. model_backtest held a 305-row sample.
