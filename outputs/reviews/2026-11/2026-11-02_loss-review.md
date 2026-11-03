# Loss review · Mon Nov 2, 2026

Nov 2: 14 trades, 57% won, -0.7% of bankroll · last 30 days -3.9% on 304 trades

## Results

| Window | Trades | Won | ¢ / trade | Bankroll |
|---|---|---|---|---|
| day | 14 | 57% | -10.2 | -0.72% |
| last 30 days | 304 | 58% | -0.5 | -3.92% |
| season | 1482 | 66% | +5.2 | +163.78% |
| all history | 3313 | 66% | +6.4 | +441.71% |

## Biggest losses on Nov 2

| Call | Word | Entry | Side | Paid | Model | Scope | Sector | Late jump | Bankroll |
|---|---|---|---|---|---|---|---|---|---|
| AAPL | Mac Studio | call start | NO | 34¢ | 60% YES | own business | Semis & hardware |  | -1.43% |
| ON | NIO | 24h before | NO | 75¢ | 22% YES | external | Semis & hardware |  | -1.08% |
| GRAB | Robot / Robotic / Robotics | 24h before | NO | 74¢ | 22% YES | own business | Internet platforms |  | -1.07% |
| AAPL | Apple Pay | call start | NO | 43¢ | 53% YES | own business | Semis & hardware |  | -0.77% |
| ON | Nvidia | 24h before | YES | 43¢ | 48% YES | own business | Semis & hardware |  | -0.77% |
| PLTR | Nvidia | 24h before | NO | 47¢ | 49% YES | external | Software & internet |  | -0.57% |

## Where the last 30 days' losses came from

Each table is sorted worst first. A slice that keeps showing up at the top is a candidate idea.

### Entry

| Entry | Trades | Won | ¢ / trade | Bankroll |
|---|---|---|---|---|
| call start | 129 | 55% | -3.2 | -20.14% |
| 24h before | 175 | 60% | +1.4 | +16.22% |

### Side

| Side | Trades | Won | ¢ / trade | Bankroll |
|---|---|---|---|---|
| NO | 260 | 55% | -2.9 | -18.12% |
| YES | 44 | 77% | +13.4 | +14.20% |

### Word scope

| Word scope | Trades | Won | ¢ / trade | Bankroll |
|---|---|---|---|---|
| external | 157 | 57% | -3.6 | -12.03% |
| own business | 147 | 59% | +2.8 | +8.10% |

### Words in the market

| Words in the market | Trades | Won | ¢ / trade | Bankroll |
|---|---|---|---|---|
| 2+ alternatives | 74 | 49% | -14.4 | -25.60% |
| 1 word | 230 | 61% | +3.9 | +21.68% |

### Late jump (call start)

| Late jump (call start) | Trades | Won | ¢ / trade | Bankroll |
|---|---|---|---|---|
| True | 26 | 46% | -7.3 | -7.45% |
| False | 278 | 59% | +0.1 | +3.53% |

### Risk tier

| Risk tier | Trades | Won | ¢ / trade | Bankroll |
|---|---|---|---|---|
| OK | 228 | 61% | -2.8 | -15.68% |
| Thin history | 5 | 60% | -5.8 | -0.60% |
| AVOID | 70 | 47% | +8.5 | +14.36% |

### Sector

| Sector | Trades | Won | ¢ / trade | Bankroll |
|---|---|---|---|---|
| Banks & finance | 80 | 49% | -10.6 | -23.33% |
| Software & internet | 33 | 45% | -10.6 | -12.36% |
| Aerospace & defense | 10 | 40% | -29.7 | -7.26% |
| Semis & hardware | 13 | 46% | -17.1 | -3.77% |
| Telecom & media | 22 | 59% | -3.5 | -2.56% |
| Travel & leisure | 1 | 0% | -43.7 | -2.00% |
| Payments & fintech | 6 | 67% | -5.3 | -0.39% |
| Internet platforms | 4 | 75% | +3.2 | +0.68% |
| Energy & utilities | 5 | 80% | +9.7 | +1.90% |
| Autos & machinery | 25 | 64% | +8.8 | +3.21% |
| Restaurants | 22 | 73% | +15.0 | +3.28% |
| Retail | 15 | 87% | +19.9 | +4.79% |
| Healthcare | 16 | 50% | +5.0 | +5.23% |
| Transport | 23 | 61% | +9.1 | +5.84% |
| Consumer goods | 29 | 72% | +17.7 | +22.82% |

## Test ideas, scored in shadow

What each idea would have changed, in % of bankroll (positive = it would have helped). Nothing here changes trading; adopting an idea is your call.

| Idea | Effect | day | last 30 days | season | all history |
|---|---|---|---|---|---|
| **I-001** Call start: skip NO trades that bet against a late jump (price up 0.3+ log-odds since 24h) (EXP-0001) | skip | – | +8.83% (24) | -12.29% (221) | -80.07% (450) |
| **I-002** Halve the stake on NO trades on external (news) words (EXP-0001) | half | -1.52% (9) | +6.42% (152) | -22.50% (642) | -97.36% (1391) |
| **I-003** Skip NO trades on external words in Banks, Telecom & media, Autos, Aerospace (picked after the fact) (EXP-0002) | skip | – | +36.91% (85) | +27.60% (187) | +14.16% (397) |
| **I-004** Skip NO trades on external words with 2+ alternatives ("Iran / Middle East") (EXP-0003) | skip | -1.95% (3) | +20.17% (55) | +7.80% (182) | -3.58% (278) |
| **I-005** I-004, but only plain TRADE (keep TRADE+, where the risk model agrees) (EXP-0004) | skip | -1.95% (3) | +24.16% (43) | +17.35% (159) | +17.99% (241) |
| **I-006** Halve the stake on plain TRADE (keep TRADE+ as is) (EXP-0004) | half | +0.15% (11) | +9.14% (234) | -33.72% (1205) | -99.45% (2584) |
| **I-007** Give TRADE+ the documented 1.5x stake (it averages 1.03% vs 1.08% for TRADE) (EXP-0004) | 1.5x | -0.21% (3) | +7.18% (70) | +48.17% (277) | +121.40% (729) |

In brackets: trades the idea touches in that window.
