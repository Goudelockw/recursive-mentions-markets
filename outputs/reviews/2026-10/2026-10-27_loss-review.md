# Loss review · Tue Oct 27, 2026

Oct 27: 9 trades, 33% won, -9.7% of bankroll · last 30 days -12.9% on 237 trades

## Results

| Window | Trades | Won | ¢ / trade | Bankroll |
|---|---|---|---|---|
| day | 9 | 33% | -31.2 | -9.73% |
| last 30 days | 237 | 57% | -2.0 | -12.91% |
| season | 1377 | 66% | +5.2 | +145.85% |
| all history | 3208 | 67% | +6.5 | +423.78% |

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
| call start | 105 | 53% | -5.4 | -19.21% |
| 24h before | 132 | 59% | +0.6 | +6.30% |

### Side

| Side | Trades | Won | ¢ / trade | Bankroll |
|---|---|---|---|---|
| NO | 205 | 56% | -2.4 | -11.83% |
| YES | 32 | 62% | +0.2 | -1.08% |

### Word scope

| Word scope | Trades | Won | ¢ / trade | Bankroll |
|---|---|---|---|---|
| external | 137 | 53% | -6.2 | -19.13% |
| own business | 100 | 61% | +3.6 | +6.22% |

### Words in the market

| Words in the market | Trades | Won | ¢ / trade | Bankroll |
|---|---|---|---|---|
| 2+ alternatives | 64 | 45% | -15.1 | -22.96% |
| 1 word | 173 | 61% | +2.8 | +10.05% |

### Late jump (call start)

| Late jump (call start) | Trades | Won | ¢ / trade | Bankroll |
|---|---|---|---|---|
| False | 226 | 58% | -1.3 | -7.95% |
| True | 11 | 36% | -16.2 | -4.96% |

### Risk tier

| Risk tier | Trades | Won | ¢ / trade | Bankroll |
|---|---|---|---|---|
| OK | 173 | 58% | -5.2 | -25.78% |
| Thin history | 8 | 75% | +6.1 | +1.32% |
| AVOID | 54 | 48% | +7.9 | +13.15% |

### Sector

| Sector | Trades | Won | ¢ / trade | Bankroll |
|---|---|---|---|---|
| Banks & finance | 76 | 50% | -11.1 | -21.84% |
| Aerospace & defense | 10 | 40% | -29.7 | -7.26% |
| Semis & hardware | 5 | 40% | -23.5 | -4.70% |
| Payments & fintech | 4 | 50% | -24.4 | -2.82% |
| Healthcare | 12 | 33% | -10.6 | -2.38% |
| Travel & leisure | 1 | 0% | -43.7 | -2.00% |
| Telecom & media | 22 | 59% | -3.2 | -1.44% |
| Software & internet | 17 | 65% | +1.0 | +0.86% |
| Autos & machinery | 16 | 69% | +13.9 | +4.42% |
| Restaurants | 17 | 82% | +21.6 | +6.05% |
| Transport | 28 | 61% | +9.9 | +7.53% |
| Consumer goods | 29 | 62% | +8.0 | +10.66% |

## Test ideas, scored in shadow

What each idea would have changed, in % of bankroll (positive = it would have helped). Nothing here changes trading; adopting an idea is your call.

| Idea | Effect | day | last 30 days | season | all history |
|---|---|---|---|---|---|
| **I-001** Call start: skip NO trades that bet against a late jump (price up 0.3+ log-odds since 24h) (EXP-0001) | skip | -0.38% (1) | +4.96% (11) | -19.69% (204) | -87.46% (433) |
| **I-002** Halve the stake on NO trades on external (news) words (EXP-0001) | half | +1.41% (4) | +10.07% (131) | -21.93% (613) | -96.79% (1362) |
| **I-003** Skip NO trades on external words in Banks, Telecom & media, Autos, Aerospace (picked after the fact) (EXP-0002) | skip | +2.00% (1) | +31.64% (81) | +22.33% (183) | +8.89% (393) |
| **I-004** Skip NO trades on external words with 2+ alternatives ("Iran / Middle East") (EXP-0003) | skip | +3.62% (3) | +25.40% (48) | +10.12% (173) | -1.27% (269) |
| **I-005** I-004, but only plain TRADE (keep TRADE+, where the risk model agrees) (EXP-0004) | skip | +1.62% (2) | +25.60% (40) | +15.89% (154) | +16.52% (236) |
| **I-006** Halve the stake on plain TRADE (keep TRADE+ as is) (EXP-0004) | half | +1.15% (5) | +13.03% (183) | -27.60% (1120) | -93.33% (2499) |
| **I-007** Give TRADE+ the documented 1.5x stake (it averages 1.03% vs 1.08% for TRADE) (EXP-0004) | 1.5x | -3.71% (4) | +6.58% (54) | +45.32% (257) | +118.55% (709) |

In brackets: trades the idea touches in that window.
