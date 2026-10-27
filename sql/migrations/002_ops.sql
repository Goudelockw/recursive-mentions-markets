-- ops: what the weekly batch found. One row per run in ops.runs; health checks and metrics hang off it.
create schema ops;

create table ops.runs (
  run_id       bigserial primary key,
  job          text not null,                 -- 'weekly'
  started_at   timestamptz not null default now(),
  finished_at  timestamptz,
  ok           boolean,
  summary      jsonb
);

create table ops.health_checks (
  run_id      bigint not null references ops.runs on delete cascade,
  check_name  text not null,
  status      text not null check (status in ('ok', 'warn', 'fail')),
  value       numeric,
  detail      text,
  primary key (run_id, check_name)
);

create table ops.weekly_metrics (
  run_id   bigint not null references ops.runs on delete cascade,
  metric   text not null,
  segment  text not null default '',
  value    numeric,
  n        int,
  primary key (run_id, metric, segment)
);
