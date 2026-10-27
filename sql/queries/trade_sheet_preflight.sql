-- Trade sheet preflight: is the data behind the board current?
-- One row per check. Read-only.
with runs as (
  select job,
         max(started_at) filter (where ok)  as last_ok,
         max(started_at)                    as last_run,
         bool_or(not ok) filter (where started_at > now() - interval '24 hours') as failed_24h
  from kalshi.ingest_runs
  where started_at > now() - interval '7 days'
  group by job
)
select 'job:' || j.job                                         as check_name,
       r.last_ok,
       round(extract(epoch from now() - r.last_ok) / 3600.0, 1) as hours_since_ok,
       j.max_hours,
       coalesce(r.failed_24h, false)                            as failed_24h
from (values ('sync', 3), ('filings', 30), ('reconcile', 30), ('transcripts', 30)) j(job, max_hours)
left join runs r using (job)
union all
select 'quotes',
       max(updated_at),
       round(extract(epoch from now() - max(updated_at)) / 3600.0, 1),
       3,
       false
from kalshi.markets
where status in ('active', 'open') and ticker like 'KXEARNINGSMENTION%'
union all
select 'model:' || model,
       max(fitted_at),
       round(extract(epoch from now() - max(fitted_at)) / 3600.0, 1),
       24 * 120,
       false
from kalshi.model_coefficients
group by model;
