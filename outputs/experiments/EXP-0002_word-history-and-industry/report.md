# EXP-0002 · Cross-company word history and industry

Oct 28, 2026 · Owner's questions: (1) does a word's history at *other* companies (how long ago it
first appeared, how often it was said) change the odds it comes up on this call? (2) do industries
mention certain words more or less? Data: every settled mentions market. All features are point in
time: only other companies' markets from before the call count. Tests are out of sample (v2
walk-forward, each month predicted by a model trained only on earlier months).

## Short answer

1. **Word history: no.** The model already gets it right. Its gaps are within ±1–3 points in
   almost every bucket, and adding the features to the model leaves out-of-sample Brier unchanged.
2. **Industry: real differences, but they don't stay put.** Within a season some sectors are
   clearly mispriced: payments companies rarely say external words (12.5% vs a 39% market price),
   while banks and telecom say them more than predicted. But which sectors are off changes over
   time. Corrections learned month by month helped a lot in Sep–Oct and were neutral over the full
   history.
3. **Neither is ready for trading.** Industry corrections go into shadow scoring as a challenger.

## 1. Word history (24h before, out of sample)

By how long ago the word first appeared at another company:

| Scope | First seen | Markets | Said | Market | Model | Said − model |
|---|---|---|---|---|---|---|
| External | first time anywhere | 402 | 32.8% | 40.4% | 32.4% | +0.4 |
| External | 1–3 months | 71 | 42.3% | 44.1% | 36.7% | +5.6 |
| External | 6–12 months | 409 | 40.6% | 48.0% | 41.6% | −1.0 |
| External | over a year | 515 | 45.6% | 49.5% | 44.9% | +0.7 |
| Own business | first time anywhere | 1,646 | 57.7% | 59.8% | 57.2% | +0.5 |
| Own business | over a year | 412 | 58.7% | 63.7% | 62.6% | −3.9 |

- Older words get said more (external: 33% when brand new, 46% after a year). The model already
  captures this; the market overprices them at every age.
- **One signal:** own-business words said at most other companies in the last 30 days came up 64%
  of the time against the model's 59% (246 markets).
- Added to the model as six terms, out-of-sample Brier was 0.1676 → 0.1676 at 24h and
  0.1588 → 0.1587 at call start. No gain.

## 2. Industry

Model misses by sector (24h, all periods):

| Sector | Markets | Said | Market | Model | Said − model |
|---|---|---|---|---|---|
| Payments & fintech | 72 | 26.4% | 46.9% | 40.9% | −14.5 |
| Software & internet | 823 | 50.8% | 56.9% | 53.1% | −2.3 |
| Healthcare | 168 | 58.9% | 64.4% | 60.6% | −1.6 |
| Telecom & media | 342 | 57.3% | 57.5% | 53.9% | +3.4 |
| Banks & finance | 630 | 56.5% | 56.7% | 52.3% | +4.2 |
| Aerospace & defense | 96 | 50.0% | 51.0% | 45.7% | +4.3 |

The biggest gaps are on external words. Payments companies say them 12.5% of the time (model
32%); telecom & media 43% (model 34%); healthcare 32% (model 40%).

Two out-of-sample tests:

- **As model terms** (industry × word-category rate, industry rate for the word): no gain.
- **As walk-forward offsets** (each sector's average miss from earlier months, shrunk toward 0):

| Entry | Period | Brier now → with offsets | Better in | Bankroll ¢ total now → with offsets |
|---|---|---|---|---|
| 24h | all history | 0.1676 → 0.1679 | 23% | 9,857 → 10,316 |
| 24h | Sep–Oct | 0.1607 → 0.1595 | 95% | 874 → 1,402 |
| Call start | all history | 0.1588 → 0.1588 | 40% | 9,471 → 9,757 |
| Call start | Sep–Oct | 0.1489 → 0.1473 | 99.8% | −842 → −38 |

"Better in" is the share of 1,000 by-call bootstrap resamples where the offsets lower Brier. Eight
variants were tried, so the best Sep–Oct row is partly luck.

**The skip-rule version doesn't survive an honest check.** Skipping external NO trades in the
sectors that look worst (I-003) gains +20% of bankroll over the season. But those sectors were
chosen with hindsight. Before July, external NO trades in Banks, Telecom and Aerospace were
profitable. Chosen from pre-July data alone, the rule keeps only Autos: +6.4% over 26 trades.

## 3. Correction to EXP-0001

Re-scored with the real trading rules and stakes (`v_mentions_history`, TRADE / TRADE+), both of
EXP-0001's rules help in the last 30 days and hurt over the season:

| Idea | Last 30 days | Season (Jul 1 on) | All history |
|---|---|---|---|
| I-001 skip call-start NO fading a late jump | +5.0% | −19.7% | −87.5% |
| I-002 halve external NO stakes | +8.1% | −23.9% | −98.8% |

EXP-0001 called I-001 costless in Jan–Aug. That came from a simpler trade rule (any 2¢ edge, no
risk tiers). **Neither rule should be adopted.** Both stay in the daily Loss Review, scored in shadow.

## Next

- Shadow-score sector offsets as a challenger model (scored daily, never traded) until the
  forward test has 300+ markets.
- News volume, after the backfill, is still the most direct test for why external words came up
  more this autumn.
- Every new idea goes into `rmm/loss_review.py` `IDEAS` so the daily review scores it from day one.
