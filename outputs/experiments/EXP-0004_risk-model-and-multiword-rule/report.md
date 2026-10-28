# EXP-0004 · Does the risk model make sense? Where does the multi-word rule belong?

Oct 28, 2026 · Data: every market in `v_mentions_history` (the live model's walk-forward backtest),
at each entry's quote, per-contract P&L after fees.

## 1. The risk model adds real information

Favorites priced 50–98¢. A logistic regression of "favorite won" on its price, the model's estimate
and the AVOID flag:

| Period | Markets | AVOID beyond price | AVOID beyond price **and** model |
|---|---|---|---|
| All | 9,088 | −0.71 (p < 0.001) | **−0.46** (p < 0.001) |
| Before Sep | 7,552 | −0.72 | −0.45 |
| Sep–Oct | 1,536 | −0.62 | **−0.54** (p = 0.001) |

AVOID favorites lose much more often than both the market and the fundamental model expect. The
avoid markers (not central, no reason to say it, skipped last call, one speaker…) capture something
the model doesn't.

**Caveat:** the rules were chosen on this history ("4+ extra losses per 100 in both periods"), so
part of this is in-sample. That it held in Sep–Oct, when the rest of the model broke, is the best
evidence it's real.

## 2. It's the part of the system that held up this autumn

| Strategy | ¢/trade all | ¢/trade Sep–Oct | Total ¢ |
|---|---|---|---|
| A: model only (2¢ edge) | +5.3 | +0.2 | 19,398 |
| B: A + basic rules | +6.0 | +0.1 | 20,163 |
| C: B + risk model skips (the trade sheet) | +6.6 | +1.0 | 21,080 |
| D: TRADE+ only (fade AVOID favorites) | +12.9 | **+14.4** | 9,045 |

The risk skips add profit in every period. In Sep–Oct, TRADE+ made +1,078¢ and plain TRADE lost
about −740¢.

## 3. Where the multi-word rule belongs

- **Not the fundamental model.** As a term it lowers out-of-sample accuracy (EXP-0003, better in only
  2–6% of resamples). The market already prices multi-word markets right; the problem is which trades
  we take, not the probability.
- **Not the risk model as built.** The risk model finds favorites that lose more than priced. On
  multi-word markets the TRADE+ trades (where the risk model agrees) are fine. The damage is all in
  plain TRADE:

| External, NO, 2+ alternatives | Trades | ¢/trade | Bankroll |
|---|---|---|---|
| TRADE, before Sep | 184 | +8.5 | +12.5% |
| **TRADE, Sep–Oct** | **52** | **−22.1** | **−29.0%** |
| TRADE+, before Sep | 24 | +25.3 | +18.4% |
| TRADE+, Sep–Oct | 9 | −4.5 | −0.6% |

- **A trading rule**, narrow: skip plain TRADE NO bets on external words with 2+ alternatives, and
  keep TRADE+. That's I-005: +25.6% of bankroll over 30 days, +15.9% over the season, +16.5% over all
  history. It's a bet that this autumn's pattern continues. It would have cost about 12.5% before
  September and saved 29% since. It's cheap to reverse, and the daily Loss Review shows its running
  score.

## 4. What it means for the trading strategy

- **The edge is two views agreeing.** TRADE+ (the model fades a favorite the risk model marks AVOID) is 22% of
  trades and about 43% of the profit. It's positive at every edge size in both periods. Plain TRADE was positive
  at every edge size before September (+3.6¢ to +11.5¢, rising with edge) and negative at every edge size in
  Sep–Oct, so a higher edge bar wouldn't have saved it.
- **Sizing is backwards.** SYSTEM.md says TRADE+ gets 1.5× stake, but in the backtest it averages 1.03% of
  bankroll against 1.08% for plain TRADE (median 0.94% vs 1.00%), and only 8% of TRADE+ trades hit the 2% cap.
  Giving TRADE+ 1.5× (I-007) is +118.6% of bankroll over all history, +45.3% over the season and +6.6% over 30 days.
- **Don't shrink plain TRADE.** Halving it (I-006) is +13.0% over 30 days but −27.6% over the season and −93.3%
  over all history.
- **The risk model only covers favorites priced 50–98¢.** Most plain TRADE trades fall where it has no view. New
  avoid markers (multi-word, outside topic, late price jumps, underdogs) are the most valuable research to do next.
