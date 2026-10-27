-- The quote (bid / ask) of every settled mentions market at fixed times before its call: the last
-- candle at or before that time, from the finest period available (1-minute, hourly, daily), if it
-- is fresh enough (within 36h for the multi-day horizons, 3h otherwise) and the market was listed.
-- Read-only. Used by rmm/horizons.py for the "leading into the call" charts.
with h(label, hours, max_stale_h) as (
  values ('30d', 720, 36), ('14d', 336, 36), ('7d', 168, 36), ('3d', 72, 36), ('2d', 48, 36),
         ('24h', 24, 3), ('12h', 12, 3), ('6h', 6, 3), ('3h', 3, 3), ('1h', 1, 3)
),
m as (
  select t.ticker, t.call_start::timestamptz as call_start, mk.open_time
  from kalshi.v_model_training t join kalshi.markets mk using (ticker)
  where t.call_start is not null
)
select m.ticker, h.label, h.hours, q.yes_bid_close as bid, q.yes_ask_close as ask, q.period_minutes,
       round(extract(epoch from (m.call_start - interval '1 hour' * h.hours) - q.ts) / 3600.0, 2) as stale_h
from m cross join h
cross join lateral (
  select c.ts, c.yes_bid_close, c.yes_ask_close, c.period_minutes
  from kalshi.candles c
  where c.ticker = m.ticker and c.period_minutes in (1, 60, 1440)
    and c.ts <= m.call_start - interval '1 hour' * h.hours
    and c.ts >= m.call_start - interval '1 hour' * (h.hours + h.max_stale_h)
    and c.yes_bid_close is not null and c.yes_ask_close is not null
  order by c.ts desc, c.period_minutes
  limit 1
) q
where m.open_time is null or m.open_time <= m.call_start - interval '1 hour' * h.hours;
