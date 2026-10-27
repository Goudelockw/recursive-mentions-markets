# Weekly Review · 2026-W44

**nothing failing · 7 warnings · 0 fixes done, 9 queued · 0 need you**

_Generated 2026-10-27 03:59 UTC._

## Needs you

Nothing needs you this week.

## Fixed automatically

| # | Queued | Command | Status |
|--:|---|---|---|
| 9 | 2026-10-27 | `filings --backfill-symbol INTC` | queued |
| 8 | 2026-10-27 | `equibles ` | queued |
| 7 | 2026-10-27 | `fortune --symbol VZ` | queued |
| 6 | 2026-10-27 | `fortune --symbol TSLA` | queued |
| 5 | 2026-10-27 | `fortune --symbol RACE` | queued |
| 4 | 2026-10-27 | `fortune --symbol PGR` | queued |
| 3 | 2026-10-27 | `fortune --symbol NIO` | queued |
| 2 | 2026-10-27 | `fortune --symbol LUCID` | queued |
| 1 | 2026-10-27 | `fortune --symbol EBAY` | queued |

## Health checks

- **warn** check_date_calls: 1 calls passed their estimated time with no release: INTC
- **warn** low_confidence_call_times_7d: 7 calls in the next 7 days with a default or one-call estimate of the time: HLT Tue 08:49 am, SFM Wed 05:00 pm, EBAY Wed 05:30 pm, AC Thu 08:30 am, MA Thu 08:44 am, RIVN Thu 05:00 pm, GRAB Mon 08:30 am
- **warn** score_log: 0 scores logged this week (last 13.6 days ago)
- **warn** settled_without_transcript_30d: 29 settled markets in 30 days have no transcript to check against
- **warn** settlement_vs_transcript:kalshi_no_we_count: 1 markets in 30 days: Kalshi settled NO but our transcript counts the word: SPCX "Colossus"
- **warn** settlement_vs_transcript:kalshi_yes_we_miss: 5 markets in 30 days: Kalshi settled YES but our transcript doesn't count the word: BB "Alloy Kore"; DPZ "Andrew Gregory"; UAL "Coastliner"; C "Basel 3"; WFC "Basel 3"
- **warn** transcript_gaps_30d: 7 calls in the last 30 days with no transcript: VZ 2026-10-26, EBAY 2026-10-22, RACE 2026-10-16, PGR 2026-10-14, LUCID 2026-10-05, NIO 2026-10-02, TSLA 2026-10-02
- **ok** job:filings: filings: last ok 5.4h ago, 123 runs this week
- **ok** job:news: news: last ok 16.4h ago, 7 runs this week
- **ok** job:reconcile: reconcile: last ok 23.7h ago, 7 runs this week
- **ok** job:sync: sync: last ok 0.9h ago, 163 runs this week
- **ok** job:transcripts: transcripts: last ok 22.9h ago, 7 runs this week
- **ok** live_model_age: live model v2 trained through 1 days ago
- **ok** settlement_lag: 0 markets closed 3+ days ago without a result
- **ok** unlabeled_open_words: 0 words on open markets have no category label
