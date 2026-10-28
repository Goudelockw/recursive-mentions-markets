# EXP-0003 · Variable audit: what doesn't make sense, and what to drop

Oct 28, 2026 · Owner's question: is there anything in the model that doesn't make sense and is
worth excluding? Four checks on every variable: what it means, whether it can see the future,
whether it duplicates another variable, and the out-of-sample evidence. The evidence is a
**drop-one ablation**: remove the variable, re-run the month-by-month walk-forward, and compare
Brier and cents per trade with a paired by-call bootstrap (500–1,000 resamples).

## Result: drop 8, keep 13, watch 1

Built as **challenger v3**. Review verdict vs live v2: **Better.** In the walk-forward head-to-head
it has lower Brier at both entries (better in 99–100% of resamples) and +5.6¢ vs +5.2¢ a trade at
call start, +6.2¢ vs +5.5¢ at 24h. The forward test is only one day (66 markets) so far.
Not promoted: that's the owner's call.

### Dropped

| Variable | Why |
|---|---|
| `r4` hit rate, last 4 calls | Duplicates `said_prev` + `avg_count`. Dropping it improves Brier in 100% (24h) and 98.8% (call start) of resamples, +645¢ at call start. |
| `filing_said` in the call-start **fundamental** model | Already in the combined model, where it matters (−1,516¢ if removed). The second copy is redundant; dropping it is better in 85% of resamples. |
| `corpus_rare` rare word | No effect either way (p = 0.76). |
| `analysts_n` analysts per call | No effect (p = 0.65); cents mixed. |
| `said_yoy`, `has_yoy` year-ago pair | No effect on Brier; +733¢ at 24h without them. |
| `ext`, `politics` outside-topic labels | No effect (p = 0.72 / 0.15). The outside-topic signal is carried by `inc`, `story0` and the corpus rates. |

Dropped all together (variant B):

| Entry | Period | Brier now → pruned | Pruned better in | Cents now → pruned |
|---|---|---|---|---|
| 24h | all | 0.1676 → 0.1672 | 99.7% | 9,857 → 11,638 |
| 24h | 2025 | 0.1635 → 0.1628 | 81% | 1,845 → 2,169 |
| 24h | Jan–Aug 2026 | 0.1698 → 0.1693 | 99.7% | 7,138 → 8,831 |
| 24h | Sep–Oct | 0.1607 → 0.1607 | 51% | 874 → 638 |
| Call start | all | 0.1588 → 0.1585 | 98.9% | 9,471 → 10,569 |
| Call start | 2025 | 0.1607 → 0.1598 | 92% | 2,884 → 2,878 |
| Call start | Jan–Aug 2026 | 0.1609 → 0.1607 | 98% | 7,429 → 8,572 |
| Call start | Sep–Oct | 0.1489 → 0.1490 | 44% | −842 → −882 |

It's better in every period but Sep–Oct, where it's even. Pruning doesn't fix this autumn's problem
(EXP-0001); it makes the model cleaner and a little better in normal conditions.

### Kept (dropping each makes the model worse)

`avg_count`, `said_prev`, `multi`, `no_hist`, `corpus_spike_z`, the peer pair, the valence trio,
`analyst_rate4`, `inc`, `story0`, `rel_head`; and in the combined models `lp`/`lp24`, `lA`, `move24`
+ `has24`, `filing_said`, `inc`.

Two that look odd but are right:

- **`no_hist` (+1.44)** looks huge. It's a correction: with no transcripts every history feature reads
  "never said", and `no_hist` cancels that.
- **`inc` appears twice** (fundamental and combined). Not double counting: the combined model learns
  what incentive adds *on top of* the market price, and removing it there costs −908¢ at call start.

### Watch: `story0` may be hindsight

91% of the incentive / valence / story labels (5,792 of 6,346 settled markets) were made on or after
Oct 2, after those calls happened. The labeling rubric is point-in-time, but the labeler may know
what came later.

- **`inc` passes:** on the 512 markets labeled *before* the call, it still adds to the market price
  (+0.40, p = 0.044), as strongly as on the retroactive labels (+0.29).
- **`story0` fails:** −0.40 on retroactive labels, **+0.49** on forward ones (p = 0.08). A sign flip is
  what hindsight looks like.

The backtest can't settle this, because it's scored on the same retroactive labels. `story0` stays in
v3 for now. Re-test it on forward-labeled markets only once there are ~1,500 (about two months).

### Checked and fine

The corpus, peer and call-history features are point in time: they only use calls ending 2+ days
before the call.

## Changes made

- `rmm/refit.py`: the model spec is explicit. `SPEC_R` is the R spec (the parity test still checks
  it); `SPEC_V3` is now the default, so Sunday's refit fits v3's spec. Dropped terms are stored with
  coefficient 0, because the board's SQL multiplies every term by name and a missing one would make
  every board score NULL on promotion.
- `rmm/review.py`: a version is scored with its own terms, not the current spec's.
- Challenger v3 saved and reviewed; the Models page is updated.
