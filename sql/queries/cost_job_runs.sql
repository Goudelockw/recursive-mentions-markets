-- Cost report: every pipeline run in the last 7 days. Read-only.
-- A run with no finished_at was cut off (crash or redeploy); the report counts it as 1 minute.
select job, started_at, finished_at, ok
from kalshi.ingest_runs
where started_at > now() - interval '7 days'
order by started_at;
