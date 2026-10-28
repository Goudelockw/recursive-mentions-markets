-- Loss review: every graded trade (TRADE / TRADE+) with what's needed to slice it. Read-only.
-- One row per market and entry: the live score when there is one, else the walk-forward backtest.
with h as (
  select distinct on (h.ticker, h.stage) h.*
  from kalshi.v_mentions_history h
  where h.action in ('TRADE', 'TRADE+')
  order by h.ticker, h.stage, (h.source = 'live') desc
)
select h.source, h.stage, h.call_date::text as call_date, h.symbol, h.word, h.ticker, h.event_ticker,
       h.side, h.fav_side, h.avoid_tier, h.action, h.bid_c::float as bid_c, h.ask_c::float as ask_c,
       h.model_c::float as model_c, h.result, h.won, h.pnl_c::float as pnl_c, h.stake_pct::float as stake_pct,
       h.bankroll_return_pct::float as ret_pct,
       mi.word_scope, mi.word_category, mi.move_24h::float as move_24h,
       mi.theme_cos_before, mi.new_for_company,
       cm.sic
from h
left join kalshi.mv_model_input mi on mi.ticker = h.ticker
left join kalshi.company_map cm on cm.symbol = h.symbol;
