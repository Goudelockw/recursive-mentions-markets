-- 006: the board's upcoming call times use the calendar sync's IR-confirmed times (kalshi.call_calendar,
-- time_confirmed) after manual overrides, and the release window follows the real call date instead of the
-- Kalshi ticker date. Before this, 33 upcoming calls had wrong times on the board (GOOGL a day late, AAPL and
-- HIMS a week off) and INTC sat in CHECK DATE because its ticker said Oct 22. Applied 2026-10-28.
CREATE OR REPLACE VIEW kalshi.v_upcoming_call_times AS
WITH ev AS (
         SELECT DISTINCT m.event_ticker,
            replace(m.series_ticker, 'KXEARNINGSMENTION'::text, ''::text) AS symbol,
            kalshi.event_date(e.sub_title, m.event_ticker) AS ev_date
           FROM kalshi.markets m
             LEFT JOIN kalshi.events e ON e.event_ticker = m.event_ticker
          WHERE m.status = 'active'::text AND m.series_ticker ~~ 'KXEARNINGSMENTION%'::text
        ), usual AS (
         SELECT mv_call_times.symbol,
            percentile_disc(0.5::double precision) WITHIN GROUP (ORDER BY ((mv_call_times.call_start_est AT TIME ZONE 'America/New_York'::text)::time without time zone)) AS usual_time,
            count(*) AS n_calls
           FROM kalshi.mv_call_times
          WHERE (mv_call_times.call_start_source = ANY (ARRAY['release_text'::text, 'first_lock_minus_20m'::text, 'manual_override'::text])) AND mv_call_times.call_start_est IS NOT NULL
          GROUP BY mv_call_times.symbol
        ), known AS (
         SELECT ev_1.event_ticker,
            COALESCE(o.call_start, cal.call_start) AS call_start,
                CASE
                    WHEN o.call_start IS NOT NULL THEN 'manual_override'::text
                    WHEN cal.call_start IS NOT NULL THEN 'calendar (IR confirmed)'::text
                    ELSE NULL::text
                END AS source,
            COALESCE((COALESCE(o.call_start, cal.call_start) AT TIME ZONE 'America/New_York'::text)::date, ev_1.ev_date) AS d
           FROM ev ev_1
             LEFT JOIN kalshi.call_time_overrides o ON o.event_ticker = ev_1.event_ticker
             LEFT JOIN kalshi.call_calendar cal ON cal.event_ticker = ev_1.event_ticker AND cal.time_confirmed AND cal.call_start IS NOT NULL
        ), rel AS (
         SELECT k_1.event_ticker,
            max(f.filed_at) AS release_at
           FROM known k_1
             JOIN ev ev_1 ON ev_1.event_ticker = k_1.event_ticker
             JOIN kalshi.filings f ON f.symbol = ev_1.symbol AND ('2.02'::text = ANY (f.items)) AND (f.filed_at AT TIME ZONE 'America/New_York'::text)::date >= (k_1.d - 1) AND (f.filed_at AT TIME ZONE 'America/New_York'::text)::date <= k_1.d
          GROUP BY k_1.event_ticker
        )
 SELECT ev.event_ticker,
    ev.symbol,
    ev.ev_date,
    rel.release_at,
    COALESCE(k.call_start, ((ev.ev_date + COALESCE(u.usual_time, '08:30:00'::time without time zone)) AT TIME ZONE 'America/New_York'::text)) AS call_start_est,
        CASE
            WHEN k.source IS NOT NULL THEN k.source
            WHEN u.usual_time IS NOT NULL THEN ('event date + usual time ('::text || u.n_calls) || ' past calls)'::text
            ELSE 'event date + 8:30am default'::text
        END AS call_start_source
   FROM ev
     LEFT JOIN usual u ON u.symbol = ev.symbol
     LEFT JOIN known k ON k.event_ticker = ev.event_ticker
     LEFT JOIN rel ON rel.event_ticker = ev.event_ticker
  WHERE ev.ev_date IS NOT NULL;
