# Loss review · Tue Nov 3, 2026

Nov 3: 15 trades, 67% won, +0.2% of bankroll · last 30 days -3.8% on 319 trades

## Results

| Window | Trades | Won | ¢ / trade | Bankroll |
|---|---|---|---|---|
| day | 15 | 67% | +0.4 | +0.17% |
| last 30 days | 319 | 58% | -0.5 | -3.75% |
| season | 1497 | 66% | +5.1 | +163.95% |
| all history | 3328 | 66% | +6.4 | +441.88% |

## Biggest losses on Nov 3

| Call | Word | Entry | Side | Paid | Model | Scope | Sector | Late jump | Bankroll |
|---|---|---|---|---|---|---|---|---|---|
| AMD | Healthcare | 24h before | NO | 24¢ | 68% YES | external | Semis & hardware |  | -1.79% |
| TOST | Resy | 24h before | NO | 75¢ | 21% YES | external | Software & internet |  | -1.31% |
| TOST | Resy | call start | NO | 72¢ | 24% YES | external | Software & internet |  | -1.24% |
| AMD | Healthcare | call start | NO | 24¢ | 71% YES | external | Semis & hardware |  | -1.00% |
| YUM | LongRange Capital | 24h before | NO | 31¢ | 64% YES | external | Restaurants |  | -0.99% |

## Where the last 30 days' losses came from

Each table is sorted worst first. A slice that keeps showing up at the top is a candidate idea.

### Entry

| Entry | Trades | Won | ¢ / trade | Bankroll |
|---|---|---|---|---|
| call start | 133 | 55% | -3.5 | -21.26% |
| 24h before | 186 | 61% | +1.7 | +17.50% |

### Side

| Side | Trades | Won | ¢ / trade | Bankroll |
|---|---|---|---|---|
| NO | 275 | 55% | -2.7 | -17.96% |
| YES | 44 | 77% | +13.4 | +14.20% |

### Word scope

| Word scope | Trades | Won | ¢ / trade | Bankroll |
|---|---|---|---|---|
| external | 169 | 57% | -3.9 | -14.85% |
| own business | 150 | 59% | +3.4 | +11.09% |

### Words in the market

| Words in the market | Trades | Won | ¢ / trade | Bankroll |
|---|---|---|---|---|
| 2+ alternatives | 75 | 49% | -13.9 | -25.21% |
| 1 word | 244 | 61% | +3.6 | +21.45% |

### Late jump (call start)

| Late jump (call start) | Trades | Won | ¢ / trade | Bankroll |
|---|---|---|---|---|
| True | 26 | 46% | -7.3 | -7.45% |
| False | 293 | 59% | +0.1 | +3.70% |

### Risk tier

| Risk tier | Trades | Won | ¢ / trade | Bankroll |
|---|---|---|---|---|
| OK | 239 | 62% | -2.6 | -13.86% |
| Thin history | 5 | 60% | -5.8 | -0.60% |
| AVOID | 74 | 46% | +7.8 | +12.70% |

### Sector

| Sector | Trades | Won | ¢ / trade | Bankroll |
|---|---|---|---|---|
| Banks & finance | 80 | 49% | -10.6 | -23.33% |
| Software & internet | 40 | 50% | -9.7 | -11.94% |
| Aerospace & defense | 10 | 40% | -29.7 | -7.26% |
| Semis & hardware | 15 | 40% | -18.2 | -6.56% |
| Telecom & media | 22 | 59% | -3.5 | -2.56% |
| Travel & leisure | 1 | 0% | -43.7 | -2.00% |
| Payments & fintech | 6 | 67% | -5.3 | -0.39% |
| Internet platforms | 4 | 75% | +3.2 | +0.68% |
| Energy & utilities | 7 | 86% | +11.2 | +2.61% |
| Restaurants | 25 | 72% | +13.2 | +2.99% |
| Retail | 15 | 87% | +19.9 | +4.79% |
| Healthcare | 16 | 50% | +5.0 | +5.23% |
| Autos & machinery | 26 | 65% | +10.8 | +5.33% |
| Transport | 23 | 61% | +9.1 | +5.84% |
| Consumer goods | 29 | 72% | +17.7 | +22.82% |

## Test ideas, scored in shadow

What each idea would have changed, in % of bankroll (positive = it would have helped). Nothing here changes trading; adopting an idea is your call.

| Idea | Effect | day | last 30 days | season | all history |
|---|---|---|---|---|---|
| **I-001** Call start: skip NO trades that bet against a late jump (price up 0.3+ log-odds since 24h) (EXP-0001) | skip | – | +8.83% (24) | -12.29% (221) | -80.07% (450) |
| **I-002** Halve the stake on NO trades on external (news) words (EXP-0001) | half | +1.41% (12) | +7.83% (164) | -21.10% (654) | -95.95% (1403) |
| **I-003** Skip NO trades on external words in Banks, Telecom & media, Autos, Aerospace (picked after the fact) (EXP-0002) | skip | – | +36.91% (85) | +27.60% (187) | +14.16% (397) |
| **I-004** Skip NO trades on external words with 2+ alternatives ("Iran / Middle East") (EXP-0003) | skip | -0.39% (1) | +19.78% (56) | +7.41% (183) | -3.97% (279) |
| **I-005** I-004, but only plain TRADE (keep TRADE+, where the risk model agrees) (EXP-0004) | skip | -0.39% (1) | +23.76% (44) | +16.96% (160) | +17.60% (242) |
| **I-006** Halve the stake on plain TRADE (keep TRADE+ as is) (EXP-0004) | half | -0.91% (11) | +8.23% (245) | -34.63% (1216) | -100.36% (2595) |
| **I-007** Give TRADE+ the documented 1.5x stake (it averages 1.03% vs 1.08% for TRADE) (EXP-0004) | 1.5x | -0.83% (4) | +6.35% (74) | +47.34% (281) | +120.58% (733) |

In brackets: trades the idea touches in that window.
