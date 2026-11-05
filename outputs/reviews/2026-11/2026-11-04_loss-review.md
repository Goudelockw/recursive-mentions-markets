# Loss review · Wed Nov 4, 2026

Nov 4: 46 trades, 61% won, +3.2% of bankroll · last 30 days -0.5% on 365 trades

## Results

| Window | Trades | Won | ¢ / trade | Bankroll |
|---|---|---|---|---|
| day | 46 | 61% | +0.8 | +3.24% |
| last 30 days | 365 | 59% | -0.3 | -0.52% |
| season | 1543 | 66% | +5.0 | +167.19% |
| all history | 3374 | 66% | +6.3 | +445.11% |

## Biggest losses on Nov 4

| Call | Word | Entry | Side | Paid | Model | Scope | Sector | Late jump | Bankroll |
|---|---|---|---|---|---|---|---|---|---|
| CRCL | Traffic | 24h before | NO | 41¢ | 47% YES | external | Banks & finance |  | -2.00% |
| CRCL | Traffic | call start | NO | 36¢ | 53% YES | external | Banks & finance |  | -2.00% |
| UBER | DoorDash | call start | NO | 69¢ | 24% YES | external | Internet platforms |  | -1.95% |
| MCD | Revenue | 24h before | NO | 43¢ | 47% YES | own business | Restaurants |  | -1.86% |
| CAVA | Cyclospora / Cyclosporiasis | 24h before | NO | 45¢ | 46% YES | external | Restaurants |  | -1.65% |
| CAVA | Cyclospora / Cyclosporiasis | call start | NO | 46¢ | 45% YES | external | Restaurants |  | -1.64% |
| CRCL | Kraken | call start | NO | 76¢ | 20% YES | external | Banks & finance |  | -1.54% |
| UBER | DoorDash | 24h before | NO | 63¢ | 26% YES | external | Internet platforms |  | -1.22% |

## Where the last 30 days' losses came from

Each table is sorted worst first. A slice that keeps showing up at the top is a candidate idea.

### Entry

| Entry | Trades | Won | ¢ / trade | Bankroll |
|---|---|---|---|---|
| call start | 153 | 55% | -3.4 | -22.83% |
| 24h before | 212 | 61% | +1.9 | +22.31% |

### Side

| Side | Trades | Won | ¢ / trade | Bankroll |
|---|---|---|---|---|
| NO | 317 | 56% | -2.0 | -14.15% |
| YES | 48 | 75% | +10.8 | +13.64% |

### Word scope

| Word scope | Trades | Won | ¢ / trade | Bankroll |
|---|---|---|---|---|
| external | 196 | 58% | -3.9 | -18.62% |
| own business | 169 | 60% | +3.8 | +18.11% |

### Words in the market

| Words in the market | Trades | Won | ¢ / trade | Bankroll |
|---|---|---|---|---|
| 2+ alternatives | 85 | 51% | -13.3 | -26.60% |
| 1 word | 280 | 61% | +3.6 | +26.08% |

### Late jump (call start)

| Late jump (call start) | Trades | Won | ¢ / trade | Bankroll |
|---|---|---|---|---|
| True | 30 | 47% | -6.2 | -7.67% |
| False | 335 | 60% | +0.2 | +7.16% |

### Risk tier

| Risk tier | Trades | Won | ¢ / trade | Bankroll |
|---|---|---|---|---|
| OK | 277 | 62% | -2.4 | -10.83% |
| Thin history | 5 | 60% | -5.8 | -0.60% |
| AVOID | 81 | 46% | +7.3 | +11.76% |

### Sector

| Sector | Trades | Won | ¢ / trade | Bankroll |
|---|---|---|---|---|
| Banks & finance | 84 | 48% | -11.1 | -27.73% |
| Semis & hardware | 19 | 37% | -21.9 | -8.47% |
| Software & internet | 50 | 56% | -4.7 | -7.60% |
| Aerospace & defense | 10 | 40% | -29.7 | -7.26% |
| Travel & leisure | 2 | 50% | -7.6 | -1.27% |
| Internet platforms | 19 | 58% | -5.9 | -0.62% |
| Payments & fintech | 6 | 67% | -5.3 | -0.39% |
| Telecom & media | 24 | 62% | -0.1 | -0.20% |
| Energy & utilities | 7 | 86% | +11.2 | +2.61% |
| Retail | 15 | 87% | +19.9 | +4.79% |
| Healthcare | 16 | 50% | +5.0 | +5.23% |
| Autos & machinery | 26 | 65% | +10.8 | +5.33% |
| Transport | 23 | 61% | +9.1 | +5.84% |
| Restaurants | 35 | 71% | +13.3 | +6.40% |
| Consumer goods | 29 | 72% | +17.7 | +22.82% |

## Test ideas, scored in shadow

What each idea would have changed, in % of bankroll (positive = it would have helped). Nothing here changes trading; adopting an idea is your call.

| Idea | Effect | day | last 30 days | season | all history |
|---|---|---|---|---|---|
| **I-001** Call start: skip NO trades that bet against a late jump (price up 0.3+ log-odds since 24h) (EXP-0001) | skip | +0.53% (3) | +9.35% (27) | -11.77% (224) | -79.54% (453) |
| **I-002** Halve the stake on NO trades on external (news) words (EXP-0001) | half | +1.89% (27) | +9.71% (191) | -19.21% (681) | -94.07% (1430) |
| **I-003** Skip NO trades on external words in Banks, Telecom & media, Autos, Aerospace (picked after the fact) (EXP-0002) | skip | +2.03% (6) | +38.94% (91) | +29.63% (193) | +16.19% (403) |
| **I-004** Skip NO trades on external words with 2+ alternatives ("Iran / Middle East") (EXP-0003) | skip | +0.58% (9) | +20.36% (65) | +7.99% (192) | -3.39% (288) |
| **I-005** I-004, but only plain TRADE (keep TRADE+, where the risk model agrees) (EXP-0004) | skip | +0.58% (9) | +24.35% (53) | +17.55% (169) | +18.18% (251) |
| **I-006** Halve the stake on plain TRADE (keep TRADE+ as is) (EXP-0004) | half | -2.09% (39) | +6.14% (284) | -36.72% (1255) | -102.45% (2634) |
| **I-007** Give TRADE+ the documented 1.5x stake (it averages 1.03% vs 1.08% for TRADE) (EXP-0004) | 1.5x | -0.47% (7) | +5.88% (81) | +46.88% (288) | +120.11% (740) |

In brackets: trades the idea touches in that window.
