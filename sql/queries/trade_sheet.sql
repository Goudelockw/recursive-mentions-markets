-- Trade sheet: the board rows that need a decision (TRADE, TRADE+, SKIP) for calls
-- today and tomorrow (New York), plus CHECK DATE rows from the last 7 days, with the
-- data checks the sheet runs per market. Read-only. Used by
-- `python -m rmm trade-sheet` and by the Trade Sheet task when it queries
-- through the Neon connector instead.
with d as (
  select (now() at time zone 'America/New_York')::date as today
),
w as (
  select v.*, count(*) over (partition by v.event_ticker) as markets_on_call
  from kalshi.v_mentions_board v, d
  where v.call_date between d.today - 7 and d.today + 1
),
b as (
  select w.* from w, d
  where (w.action in ('TRADE', 'TRADE+', 'SKIP') and w.call_date >= d.today)
     or w.action = 'CHECK DATE'
)
select
  b.markets_on_call,
  b.call_date, b.call_time_et, b.call_start_source, b.phase,
  b.symbol, b.word, b.ticker, b.event_ticker,
  b.yes_bid_c, b.yes_ask_c, b.model_stage, b.fundamental_c, b.model_c,
  b.side, b.edge_c, b.stake_pct, b.action, b.reason,
  b.fav_side, b.fav_price_c, b.avoid_points, b.avoid_tier,
  s.no_hist,
  s.release_out,
  s.p_fund is null                                              as no_fund_score,
  round(extract(epoch from now() - m.updated_at) / 3600.0, 1)  as quote_age_h,
  exists (select 1 from kalshi.word_valence v where v.ticker = b.ticker)   as has_valence,
  exists (select 1 from kalshi.word_incentive i where i.ticker = b.ticker) as has_incentive,
  (exists (select 1 from kalshi.call_time_overrides o where o.event_ticker = b.event_ticker)
   or b.call_start_source = 'calendar (IR confirmed)')          as call_time_override
from b
left join kalshi.v_model_scores_open s using (ticker)
left join kalshi.markets m using (ticker)
order by b.call_date, b.call_time_et, b.symbol, b.edge_c desc nulls last;
