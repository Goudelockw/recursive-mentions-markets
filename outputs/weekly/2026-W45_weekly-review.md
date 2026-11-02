# Weekly Review · 2026-W45

**nothing failing · 5 warnings · 11 fixes done, 0 queued · 4 need you**

_Generated 2026-11-02 02:42 UTC._

## Needs you

### W45-1 · Word matching misses Roman numerals and dotted abbreviations (Basel III, U.K.)

Kalshi settled WFC and C "Basel 3" YES; our transcripts say "Basel III" (WFC 3 times, C 2 times, said by executives). HOOD "UK / United Kingdom" settled YES; the executive said "U.K.". The counting views (mv_word_counts / mkt_word_hits in Neon) treat these as different words, so history features and the label audit undercount them. Fix: when building the match pattern for a market word, accept 1-10 as Roman numerals and allow periods between capital letters. This is a migration to those views; I can draft it once you approve the approach.

- Evidence: transcript 2036 (WFC Oct 13): "Basel III" x3
- Evidence: transcript 2022 (C Oct 13): "Basel III" x2
- Evidence: transcript 2105 (HOOD Oct 27): "U.K."

To apply: reply `approve W45-1` to Claude.

### W45-2 · Three transcripts look incomplete or from the wrong call (BB, EBAY, UAL)

BB "Alloy Kore" (event 26DEC31) is checked against a June 25 Equibles transcript, so it's the wrong call. EBAY "Goldin" (Oct 28) and UAL "Coastliner" (Oct 21) settled YES with zero hits in our Fool transcripts, which suggests those transcripts are missing part of the call. Next step: re-fetch EBAY and UAL from Fortune, and stop matching BB's December event to an old transcript.

- Evidence: transcript 1388 (BB, 2026-06-25, equibles)
- Evidence: transcript 2116 (EBAY, Oct 28, fool): 0 hits
- Evidence: transcript 2055 (UAL, Oct 21, fool): 0 hits

To apply: reply `approve W45-2` to Claude.

### W45-3 · Speaker or call mismatches: BA "F-47" and SPCX "Colossus"

Rules count only company representatives (including the operator). BA "F-47" settled YES but our transcript has it only from an analyst, so the speaker is probably misattributed. SPCX "Colossus" settled NO, yet our SPCX transcript has an executive saying "Colossus II" about the Memphis supercomputer cluster, which may be another company's call matched to SPCX. Check the SPCX transcript's source page and the BA speaker labels before trusting either call's history.

- Evidence: transcript 2093 (BA Oct 27): F-47 in an analyst turn only
- Evidence: transcript 2048 (SPCX, Oct 21): "Colossus II" in an exec turn

To apply: reply `approve W45-3` to Claude.

### W45-4 · Transcript-gap check flags filings that have no earnings call (LUCID, PGR, RACE)

All four gaps come from filings, not Kalshi calls. LUCID (Oct 5), PGR (Oct 14, Progressive's monthly results) and RACE (Oct 16) have no mentions markets within a week of those dates, so there's no call to transcribe. EBAY's gap date (Oct 22) is a week before its real call (Oct 28), and that call's transcript exists. Each week this sends Fortune and Equibles looking for transcripts that don't exist. Fix: have v_transcript_gaps count a filing only when a mentions event closes within 7 days of it.

- Evidence: 0 KXEARNINGSMENTION markets for LUCID/PGR/RACE within 7 days of the gap date
- Evidence: EBAY transcript 2116 dated Oct 28

To apply: reply `approve W45-4` to Claude.

## Fixed automatically

| # | Queued | Command | Status |
|--:|---|---|---|
| 11 | 2026-10-28 | `news --backfill` | done |
| 10 | 2026-10-28 | `reactions --days 35` | done |
| 9 | 2026-10-27 | `filings --backfill-symbol INTC` | done |
| 8 | 2026-10-27 | `equibles ` | done |
| 7 | 2026-10-27 | `fortune --symbol VZ` | done |
| 6 | 2026-10-27 | `fortune --symbol TSLA` | done |
| 5 | 2026-10-27 | `fortune --symbol RACE` | done |
| 4 | 2026-10-27 | `fortune --symbol PGR` | done |
| 3 | 2026-10-27 | `fortune --symbol NIO` | done |
| 2 | 2026-10-27 | `fortune --symbol LUCID` | done |
| 1 | 2026-10-27 | `fortune --symbol EBAY` | done |

## Health checks

- **warn** job:sync: sync: last ok 1.0h ago, 167 runs this week, 2 cut off mid-run
- **warn** settled_without_transcript_30d: 24 settled markets in 30 days have no transcript to check against
- **warn** settlement_vs_transcript:kalshi_no_we_count: 1 markets in 30 days: Kalshi settled NO but our transcript counts the word: SPCX "Colossus"
- **warn** settlement_vs_transcript:kalshi_yes_we_miss: 8 markets in 30 days: Kalshi settled YES but our transcript doesn't count the word: BB "Alloy Kore"; EBAY "Goldin"; BA "F-47"; HOOD "UK / United Kingdom"; DPZ "Andrew Gregory"; UAL "Coastliner"; WFC "Basel 3"; C "Basel 3"
- **warn** transcript_gaps_30d: 4 calls in the last 30 days with no transcript: EBAY 2026-10-22, RACE 2026-10-16, PGR 2026-10-14, LUCID 2026-10-05
- **ok** call_start_without_first_lock_14d: 1 of 39 settled calls in 14 days have no 1-minute lock time, so their call start is an estimate: ALK
- **ok** check_date_calls: 0 calls passed their estimated time with no release
- **ok** job:filings: filings: last ok 50.5h ago, 131 runs this week
- **ok** job:news: news: last ok 13.4h ago, 7 runs this week
- **ok** job:reconcile: reconcile: last ok 20.8h ago, 7 runs this week
- **ok** job:transcripts: transcripts: last ok 20.0h ago, 7 runs this week
- **ok** jobs_writing_nothing: 0 jobs ran fine all week but wrote nothing
- **ok** live_model_age: live model v2 trained through 7 days ago
- **ok** low_confidence_call_times_7d: 0 calls in the next 7 days with a default or one-call estimate of the time
- **ok** score_log: 616 scores logged this week (last 0.1 days ago)
- **ok** settlement_lag: 0 markets closed 3+ days ago without a result
- **ok** unlabeled_open_words: 0 words on open markets have no category label
