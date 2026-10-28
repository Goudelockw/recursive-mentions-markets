# Kalshi Mentions System: How It Works

*As of October 26, 2026, with the Oct 27 pipeline changes in section 4.1 (see `docs/decisions/2026-10-27_mentions-only-data.md`). Owner: William. The database now holds only earnings-mention markets.*

---

## 1. What we're trying to do

We trade Kalshi **earnings-call mentions markets** (`KXEARNINGSMENTION*`). Each one asks whether a company representative will say a given word on its next earnings call.

The approach is insurance-style. We take small, steady edges on mispriced markets and avoid the setups where "sure things" blow up.

The system answers three questions for every open market:

1. **What's the right price?** The **pricing model** (the market itself), plus the **fundamental model** (our own data), gives the **combined model**.
2. **Is this a market to avoid?** The **risk model**: avoid points and skip rules.
3. **When, and how much?** The entry windows and sizing rules.

Everything runs in **Neon Postgres**. **Railway** collects the data, **SQL views** score the markets live, **R** refits the models, and **Grafana** shows the results.

```
Kalshi API ─┐
SEC EDGAR ──┤
Motley Fool ┼─► Railway worker (kalshi-data) ─► Neon Postgres (schema kalshi) ─► Grafana / CSV exports
Fortune ────┤                                     │
Equibles ───┤                                     ├─ SQL views score every open market live
Serper news ┘                                     └─ R script refits the models (after each season)
```

---

## 2. The models

### 2.1 Pricing model
- **What it is:** the market's own price, the bid/ask midpoint. On average it's well calibrated, so everything starts from it.
- **Known bias:** YES settles about 3–4¢ below its call-start price on average, so the model's trades are mostly NO.

### 2.2 Fundamental model
A logistic regression that uses only our data, never the price. It estimates the chance the word gets said.

| Variable | Plain English |
|---|---|
| r4 | Share of the last 4 calls where the word was said |
| said_prev | Said on the most recent call |
| avg_count | Average number of mentions per call |
| multi | Market needs several mentions ("3+ times") |
| ext | Outside topic, not the company's own business |
| politics | Politics / government word |
| analyst_rate4 | Share of the last 4 calls where analysts used it |
| corpus_spike_z | Spiking on other companies' calls right now |
| corpus_rare | Rare word across all calls |
| analysts_n | Number of analysts on the last call |
| said_yoy | Said on the same quarter last year |
| peer_rate | How often industry peers said it |
| val / val_neutral / val_strong | Is the topic good or bad news for the company (−2 to +2)? Neutral flag, strongly positive flag |
| inc | Management incentive (0–2): would management bring it up unprompted? |
| story0 | Not central to the company's story this quarter |
| filing_said | In this quarter's earnings press release *(call-start version only)* |
| rel_head | In the release's headline or highlights *(call-start version only)* |

Fill-in flags such as `no_hist`, `has_yoy` and `has_peer` only mark missing data. They are not predictors.

- **Labels made by Claude:** valence, incentive, story centrality and word category are Claude-labeled and refreshed weekly by scheduled agents. Two raters agreed about 90% of the time.
- **Two versions:**
  - **Early:** no release information, used about 24h before the call.
  - **Call start:** used once the 8-K release is filed.

### 2.3 Combined model (the one we trade)
A second logistic regression that starts from the market price and adds what the market misses:

- **Call-start version:** market price + fundamental model + 24h price move + in the release + management incentive.
- **Early version:** 24h-before price + early fundamental model + management incentive.

The model's difference from the market price is scaled back by **k**, so it only moves part of the way from the price toward what the fundamental model says. k is learned walk-forward:
- call start: k = 0.711
- early: k = 0.796

**Backtest** (walk-forward by month, never trained on the month it's tested on):
- Beats the market's Brier score in nearly every resample.
- About **+5.8¢ per trade** after fees.
- U-shaped timing: the most edge is about 24h before the call and again right after the release. The hours just before the call are a dead zone.

**Live (October):** mixed and small-sample. The Nike blowup was a normal tail loss, not a model failure.

### 2.4 Risk model (avoid points)
Built by William. It flags **favorites (50–98¢) that lose more often than their price says**.

**Avoid points:**
- Each marker earns a point only in the 10¢ price ranges where the data backs it up: 4+ extra losses per 100, in both periods, with 30+ markets.
- Rules are in `avoid_point_rules`; the tests behind them are in `avoid_point_tests`.

**Verdict:**

| Verdict | Meaning |
|---|---|
| **AVOID** | That side, price range and point count lost 5+ more per 100 than priced, in both periods |
| **OK** | Everything else |
| **Thin history** | Fewer than 30 settled markets in that group, so no call is made |

**How it combines with the model:**

| Situation | Backtest result |
|---|---|
| Model fades an AVOID favorite (aligned) | **+13.5¢** per trade |
| Model buys an AVOID favorite (conflict) | +0.1¢ |

So conflicts are skipped, and aligned trades get 1.5× stake.

Full detail is in the project doc `claude/mentions-risk-model.md`.

### 2.5 Trading rules (applied in order by `kalshi.mentions_action()`)

| # | Rule | Result |
|---|---|---|
| 1 | Manual override (`risk_overrides`) | SKIP |
| 2 | No transcript history for the company | SKIP |
| 3 | NO on an event word within 100 days of the event (`event_calendar`) | SKIP (backtest −15.6¢) |
| 4 | NO on a never-said word that is in this quarter's release | SKIP |
| 5 | NO on a never-said word priced 70¢+ | SKIP |
| 6 | Buying a favorite the risk model marks AVOID | SKIP |
| 7 | Fading a favorite with 0 avoid points | SKIP |
| 8 | Fading an AVOID favorite | **TRADE+** (1.5× stake) |
| 9 | Model edge ≥ 2¢ after fees | **TRADE** |
| – | Edge < 2¢ | NO EDGE |
| – | Call already started | CLOSED |
| – | Estimated call time passed, no release filed | CHECK DATE |

### 2.6 Sizing
- **Default (board):** 1/8 Kelly on the model probability, at most **2% of bankroll per market** and **6% per call**. TRADE+ gets 1.5×.
- **Quarter-Kelly option:** 2% per market and 10% per call. Expected profit is higher, with about twice the drawdown.
- **Fees:** 0.07 × P × (1 − P) per contract. Minimum edge 2¢ after fees.
- **Stake $** = portfolio × `stake_pct` / 100. Size from the whole portfolio, not from available cash.

### 2.7 When to enter

| Window | When | What to do |
|---|---|---|
| Upcoming | More than 30h before the call | Watch |
| **ENTRY 1** | 30h to 12h before (aim for about 24h) | Place TRADE / TRADE+ |
| Hold (dead zone) | 12h before until the release | Don't add |
| **ENTRY 2** | Release filed, call not started | Re-check. Sell never-said words that showed up in the release. Add new trades only within caps |
| Call started | | No new model entries |

**Call times:** check the board's call time against the company's IR page. The Kalshi ticker date can be wrong (BlackRock's said Oct 13; the call was Oct 14). Add any correction to `kalshi.call_time_overrides`.

---

## 3. Pulling the data

All objects are in Neon project **kalshi** (`mute-sun-75653323`), database `neondb`, schema **`kalshi`**. Run the queries in any of these:
- the Neon SQL editor, then **Export CSV** (how the board CSVs have been pulled);
- Grafana (Postgres data source);
- `psql "$DATABASE_URL"`.

### Live board: every open market
```sql
select call_time_et, phase, symbol, word, yes_bid_c, yes_ask_c,
       fundamental_c, model_c, side, edge_c,
       fav_side, fav_price_c, avoid_points, avoid_tier,
       action, reason, stake_pct
from kalshi.v_mentions_board
order by call_date, call_time_et, symbol, edge_c desc nulls last;
```

### Trades to place now
```sql
select * from kalshi.v_mentions_board
where phase like 'ENTRY%' and action in ('TRADE','TRADE+')
order by call_date, call_time_et, edge_c desc;
```

### One call
```sql
select * from kalshi.v_mentions_board where symbol in ('GM','ALLY') order by symbol, edge_c desc;
```

### Settled history: backtest and live
```sql
select month, count(*) trades, round(avg(pnl_c),1) c_per_trade
from kalshi.v_mentions_history
where source = 'backtest' and stage = 'call_start' and action in ('TRADE','TRADE+')
group by month order by month;
```

### Upcoming call times and where each came from
```sql
select event_ticker, symbol, call_start_est at time zone 'America/New_York' as call_et,
       call_start_source, release_at at time zone 'America/New_York' as release_et
from kalshi.v_upcoming_call_times order by call_start_est;
```

### Fix a call time
```sql
insert into kalshi.call_time_overrides (event_ticker, call_start, note)
values ('KXEARNINGSMENTIONXYZ-26OCT28', timestamptz '2026-10-28 08:30 America/New_York', 'IR page');
```

### Risk screen alone
```sql
select * from kalshi.v_open_risk_screen order by avoid_points desc;
```

### Pipeline health
```sql
select job, max(started_at) last_run, bool_and(ok) all_ok, count(*) runs
from kalshi.ingest_runs where started_at > now() - interval '24 hours' group by 1;
```

### Key objects

| Object | What it holds |
|---|---|
| `markets`, `events`, `series` | Every Kalshi market (the spine): rules, times, result, current quotes |
| `candles` | Price history: daily for every settled market, hourly around each mentions call, 1-minute around releases |
| `transcripts`, `transcript_segments`, `transcript_sources` | Earnings-call transcripts (about 2,070 calls, 169 companies), split by speaker |
| `filings`, `corporate_events`, `company_map` | 8-K / 6-K earnings releases (about 2,060), corporate-event 8-Ks, ticker/CIK/SIC per company |
| `word_categories`, `word_valence`, `word_incentive`, `word_synonyms` | Claude-labeled word features |
| `mv_word_counts`, `mv_word_features`, `mv_model_input`, `mv_call_times`, `mv_precall_prices` | Materialized feature views, refreshed by the worker |
| `v_model_features`, `v_model_fundamental`, `v_model_training` | Model inputs, scores and training set (same formulas as R) |
| `model_coefficients` | Fitted coefficients for all four models, plus k |
| `v_model_scores_open` | Combined-model probability for every open market |
| `v_fav_history`, `v_open_risk_screen`, `avoid_point_rules`, `event_calendar`, `risk_overrides` | Risk model |
| **`v_mentions_board`** | The live board: model + risk + rules + window + stake |
| **`v_mentions_history`** | Settled markets graded (backtest + live) |
| `model_backtest`, `model_score_log` | Backtest predictions and the live score snapshots used for grading |
| `call_time_overrides` | Hand-verified call times (always win) |
| `ingest_runs`, `sync_state` | One row per job run; job cursors and backfill markers (never edit by hand) |

---

## 4. The Railway pipeline

- **Railway project:** **kalshi-data** (production, us-west2).
- **Code:** one repo, `github.com/Goudelockw/kalshi-worker` (branch `main`). Every service runs the same code with a different start command: `python -m kalshi_worker <command>`.
- **Deploys:** pushing to `main` redeploys every service.
- **Variables:** shared across services (`DATABASE_URL`, `KALSHI_*`, `SEC_CONTACT_EMAIL`, `SERPER_API_KEY`, `EQUIBLES_API_KEY`). Cron services only pick up a changed variable **after a redeploy**.

### 4.1 Services

| Service | Schedule (UTC) | What it does |
|---|---|---|
| **sync** | Hourly (`0 * * * *`) | Pulls open events and markets for the 178 earnings-mention series only (new ones picked up from `/series`), with current quotes. `sync --full` covers the whole exchange. Refreshes only the price-dependent views (the transcript-only steps run with `transcripts`), then logs scores with `kalshi.log_model_scores()` for live grading. Hourly candles; for mentions markets with a call in the next 2 days, the last 3h of hourly candles. Watchlist trades and 1-minute candles. Then a "stale sweep" re-fetches markets that dropped out of the open list, and the refresh chain runs (4.2) |
| **reconcile** | Daily 04:15 | Locks in results and daily candles for earnings-mention markets settled in the last 3 days (`RECONCILE_ALL=1` for every series). Runs `precall` (hourly prices from 48h before to 3h after each settled mentions call), then a stale sweep |
| **filings** | Every 30 min, 10:00–22:59, weekdays | SEC EDGAR: new 8-K earnings releases (Item 2.02 / Exhibit 99.1) and foreign 6-K results for every mentions company, split into body vs. forward-looking boilerplate. Also corporate-event 8-Ks (deals, exec changes) and SIC codes. Ends with the refresh chain. **This is what switches the board to Entry 2** |
| **transcripts** | Daily 05:00 | Finds and parses new Motley Fool transcripts (monthly sitemaps; 36 months for new companies). Then runs **fortune** (Fortune/Quartr pages, second source) and **equibles** (Equibles API, only for calls nothing else has; at most 90 requests per run). Ends with the refresh chain |
| **news** | Daily 11:30 | Google News counts (Serper) for "company + word" over the 14 days before each call in the next 3 days. Every article's publish date is checked on its page (`news-dates`), so nothing after the cutoff counts. **Not used by the model** (Serper can't backfill history) |
| **research-weekly** | Mondays 01:00 UTC (Sun 9pm EDT / 8pm EST) | `python -m rmm weekly --save --refit` from `recursive-mentions-markets`: health checks, live grading and calibration into `ops.*`, plus a challenger refit. Queues safe fixes into `ops.fix_requests`. Role `rmm_rw`. Rebuilds only on code changes |
| **ops-fixes** | Daily 03:30 | `python -m kalshi_worker ops-fixes`: runs the queued `ops.fix_requests` one at a time and records done / failed with the log. Only the allowlisted commands below (`ops_fixes.ALLOWED`) run; anything else, or a request over 7 days old, is rejected. Idle (a few seconds) when nothing is queued |

On-demand commands (Railway shell, `nohup python -m kalshi_worker <cmd> > /tmp/x.log 2>&1 &`):
- `sweep`
- `precall --refetch-missing`
- `mentions-backfill`
- `reactions`
- `fortune --symbol SYM`
- `transcripts --backfill-symbol SYM`
- `filings --backfill-symbol SYM`

### 4.2 The refresh chain
**What triggers it:** the end of `sync`, `transcripts` and `filings`.

**What it does:** it first resolves speaker roles (CEO, CFO, analyst…). Then it refreshes these materialized views in order, each in its own transaction with a 10-minute timeout:

`mv_word_counts → mv_call_stats → mv_call_analysts → mv_call_analyst_stats → mv_analyst_features → mv_call_features → mv_call_execs → mv_earnings_dates → mv_exec_features → mv_segment_tsv → mv_word_corpus_hits → mv_word_corpus → mv_word_context → mv_call_times → mv_precall_prices → mv_word_features → mv_model_input`

**Failures:** a failed step is logged and the chain continues. The log ends with `refresh: N of 18 steps failed`.

### 4.3 How call times are worked out (`mv_call_times`)
The first source that applies wins:

1. A `call_time_overrides` row.
2. The call time in the release text.
3. The first 1-minute price lock after the release, minus 20 min (settled calls).
4. The event date + the company's usual call time (median of past calls).
5. The event date + 8:30am ET (release before the open) or 5:00pm ET.

**Weak spot:** 4 and 5 rely on the Kalshi event date. That's how the BlackRock day-off happened.

### 4.4 Scheduled Claude tasks (outside Railway)
- **Daily, 5:50am ET:** labels new mention words with a category and scope (`word-category-labeler` skill).
- **Mondays, 5:51am ET:** context features. Loads stock prices and EPS, labels valence / incentive / phrasing for markets with a call in the next 10 days, re-scores word tone, and refreshes `mv_market_context`, `mv_phrasing` and `mv_incentive_features`.
- **Exec-change check:** CEO/CFO changes from SEC filings into `exec_tenures`.

From `recursive-mentions-markets` (instructions in `agents/<task>/PROMPT.md`, read-only on Neon):
- **Weekdays, 6:41am ET, Trade Sheet:** the day's trades and where they sit in the risk model, then the Loss Review: yesterday's graded trades, where the losses came from, and the test ideas (`rmm/loss_review.py` `IDEAS`) scored in shadow.
- **Sundays, 8:41pm ET, Cost Report:** what Neon cost this week and what to change.
- **Sundays, 9:41pm ET, Ops:** after `research-weekly`; investigates warnings, drafts fixes for approval, publishes the Weekly Review.
- **Sundays, 10:11pm ET, Model Review:** the week's challenger vs. the live model, sent before anything is promoted.
- **Sundays, 10:41pm ET, Librarian:** naming, 90-day archive, docs checked against what runs, leftover tables.

---

## 5. Refitting the models (Python, versioned, since Oct 27)
A refit runs every Sunday on Railway (`research-weekly`) and is stored as a **challenger**. It never
changes what the board trades on. Every fit is kept in `kalshi.model_versions`; exactly one is live.

```
python -m rmm refit                 # fit + walk-forward backtest; writes outputs/models/vN_<date>/
python -m rmm refit --save          # ...and stores it as challenger vN (role rmm_rw)
python -m rmm models                # list versions and which one is live
select kalshi.promote_model(N);     # make vN live (database owner only); promote the old one to roll back
```

**What a refit does** (`rmm/refit.py`, an exact port of `refit_models.R`, checked by `tests/test_refit_parity.py`):
1. Reads `v_model_training`.
2. Re-runs the walk-forward backtest for both entry points.
3. Re-learns k.
4. Saves coefficients, backtest and a fit report; with `--save`, stores them as version N.

`kalshi.promote_model(N)` rewrites `model_coefficients` and `model_backtest` from version N in one
transaction, so the board picks it up right away. Roles: `rmm_ro` reads (Trade Sheet, Cost Report),
`rmm_rw` stores challengers and `ops.*` rows (`research-weekly`), the owner promotes.

`mentions_model.R` is the full research script, with charts and resampling tests. Its feature tests and scorecards move into the phase 4 research harness; `refit_models.R` is retired (kept only as the parity reference).

---

## 6. Weekly routine

1. **Monday:** export the board for the week's calls. Check call times against IR pages; add overrides where wrong.
2. **About 24h before each call (ENTRY 1):** place TRADE / TRADE+ rows at board size.
   - Use limit orders about 1¢ better than the quote.
   - Skip, or post at the midpoint, if the spread is 10¢+.
3. **After the release (ENTRY 2):** re-export.
   - Sell never-said words that showed up in the release.
   - Add only new TRADE+ rows within caps.
4. **After settlement:** compare against the model (results by call, wins vs. the model's expected wins, Brier vs. market).

---

## 7. Open items (as of Oct 26)

| Item | Status |
|---|---|
| **First full refit run** | Done Oct 27 in Python: challenger v2 (through Oct 26, 9,924 backtest rows). v1 (the Oct 13 R fit) is still live until promoted |
| **`score-log` cron** | Done Oct 27, differently: `sync` and `filings` call `kalshi.log_model_scores()` after each refresh |
| **Refresh release features when an 8-K lands** | In the same PR. Until then, release features for the call-start model refresh on the next refresh chain |
| **Grafana board** | 12 panel queries in `grafana_mentions_board.sql`; set up the panels |
| **Daily labeling for markets listed mid-week** | Weekly labeling misses markets with a call in under 3 days |
| **Release window on call times** | Fixed Oct 28 (migration 006): upcoming calls use IR-confirmed times from `call_calendar`, and the release is looked for around that date |
| **News volume** | Collected going forward only. Test it after a full season |
| **Rotate the Neon password** | It was shared in chat earlier |

---

## 8. Related: Project Ultra Sonic (live listener)
A separate tool that listens to the call live and trades the moment a word is said:

- **How it works:** NVIDIA NeMo streaming speech-to-text (about 0.13–0.35s delay), with Vosk as the backup transcript. Orders go to the Kalshi API.
- **Lead-in phrases:** it can fire on lead-ins from the transcript corpus. For example, "dividends and share" is followed by "repurchase" about 91% of the time.
- **Lessons so far:**
  - Bots sweep the book within about 0.1s, so keep the price cap at 90¢ or less.
  - Webcast-only calls (no phone dial-in) arrive about 20s late and can't be won.

Details are in the project doc `claude/ultra-sonic-findings.md`.
