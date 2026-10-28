# Loss review · Tue Oct 27, 2026

Oct 27: 9 trades, 33% won, -9.7% of bankroll · last 30 days +3.1% on 261 trades

## Results

| Window | Trades | Won | ¢ / trade | Bankroll |
|---|---|---|---|---|
| day | 9 | 33% | -31.2 | -9.73% |
| last 30 days | 261 | 56% | -0.9 | +3.06% |
| season | 1401 | 66% | +5.3 | +161.82% |
| all history | 3232 | 66% | +6.5 | +439.75% |

## Biggest losses on Oct 27

| Call | Word | Entry | Side | Paid | Model | Scope | Sector | Late jump | Bankroll |
|---|---|---|---|---|---|---|---|---|---|
| BA | Starliner | call start | NO | 50¢ | 42% YES | own business | Aerospace & defense |  | -2.00% |
| HLT | Competition | call start | NO | 42¢ | 48% YES | own business | Travel & leisure |  | -2.00% |
| HOOD | Anthropic / Claude | call start | NO | 67¢ | 25% YES | external | Banks & finance |  | -2.00% |
| V | Inyo | call start | NO | 79¢ | 16% YES | own business | Payments & fintech |  | -2.00% |
| V | Regulation / Regulatory | call start | NO | 60¢ | 33% YES | external | Payments & fintech |  | -2.00% |
| KO | Pibb | call start | NO | 54¢ | 41% YES | own business | Consumer goods |  | -1.43% |

## Where the last 30 days' losses came from

Each table is sorted worst first. A slice that keeps showing up at the top is a candidate idea.

### Entry

| Entry | Trades | Won | ¢ / trade | Bankroll |
|---|---|---|---|---|
| call start | 125 | 51% | -5.1 | -19.42% |
| 24h before | 136 | 60% | +2.9 | +22.48% |

### Side

| Side | Trades | Won | ¢ / trade | Bankroll |
|---|---|---|---|---|
| NO | 205 | 52% | -4.5 | -19.59% |
| YES | 56 | 71% | +12.2 | +22.65% |

### Word scope

| Word scope | Trades | Won | ¢ / trade | Bankroll |
|---|---|---|---|---|
| external | 129 | 53% | -6.4 | -16.95% |
| own business | 132 | 59% | +4.4 | +20.01% |

### Words in the market

| Words in the market | Trades | Won | ¢ / trade | Bankroll |
|---|---|---|---|---|
| 2+ alternatives | 61 | 41% | -19.5 | -24.79% |
| 1 word | 200 | 60% | +4.7 | +27.85% |

### Late jump (call start)

| Late jump (call start) | Trades | Won | ¢ / trade | Bankroll |
|---|---|---|---|---|
| True | 26 | 38% | -12.8 | -10.92% |
| False | 235 | 58% | +0.4 | +13.98% |

### Risk tier

| Risk tier | Trades | Won | ¢ / trade | Bankroll |
|---|---|---|---|---|
| OK | 192 | 57% | -4.5 | -16.05% |
| Thin history | 8 | 75% | +7.2 | +1.47% |
| AVOID | 54 | 50% | +10.9 | +20.49% |

### Sector

| Sector | Trades | Won | ¢ / trade | Bankroll |
|---|---|---|---|---|
| Banks & finance | 80 | 49% | -10.6 | -23.33% |
| Software & internet | 15 | 33% | -23.9 | -11.15% |
| Aerospace & defense | 10 | 40% | -29.7 | -7.26% |
| Payments & fintech | 4 | 50% | -24.4 | -2.82% |
| Retail | 2 | 0% | -24.2 | -2.81% |
| Semis & hardware | 10 | 50% | -9.6 | -2.24% |
| Travel & leisure | 1 | 0% | -43.7 | -2.00% |
| Telecom & media | 26 | 65% | +1.1 | -0.60% |
| Healthcare | 11 | 36% | -2.4 | +0.84% |
| Restaurants | 15 | 87% | +25.1 | +5.66% |
| Transport | 31 | 58% | +6.4 | +7.17% |
| Autos & machinery | 15 | 73% | +19.5 | +7.53% |
| Consumer goods | 41 | 68% | +16.6 | +34.07% |

## Test ideas, scored in shadow

What each idea would have changed, in % of bankroll (positive = it would have helped). Nothing here changes trading; adopting an idea is your call.

| Idea | Effect | day | last 30 days | season | all history |
|---|---|---|---|---|---|
| **I-001** Call start: skip NO trades that bet against a late jump (price up 0.3+ log-odds since 24h) (EXP-0001) | skip | -0.38% (1) | +11.92% (25) | -12.72% (218) | -80.50% (447) |
| **I-002** Halve the stake on NO trades on external (news) words (EXP-0001) | half | +1.41% (4) | +10.35% (122) | -21.65% (604) | -96.51% (1353) |
| **I-003** Skip NO trades on external words in Banks, Telecom & media, Autos, Aerospace (picked after the fact) (EXP-0002) | skip | +2.00% (1) | +32.81% (78) | +23.50% (180) | +10.06% (390) |
| **I-004** Skip NO trades on external words with 2+ alternatives ("Iran / Middle East") (EXP-0003) | skip | +3.62% (3) | +25.98% (43) | +10.70% (168) | -0.68% (264) |
| **I-005** I-004, but only plain TRADE (keep TRADE+, where the risk model agrees) (EXP-0004) | skip | +1.62% (2) | +31.51% (34) | +21.80% (148) | +22.44% (230) |
| **I-006** Halve the stake on plain TRADE (keep TRADE+ as is) (EXP-0004) | half | +1.15% (5) | +8.71% (207) | -31.92% (1144) | -97.65% (2523) |
| **I-007** Give TRADE+ the documented 1.5x stake (it averages 1.03% vs 1.08% for TRADE) (EXP-0004) | 1.5x | -3.71% (4) | +10.24% (54) | +48.99% (257) | +122.22% (709) |

In brackets: trades the idea touches in that window.
