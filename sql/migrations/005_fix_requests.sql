-- Fix queue: safe, repeatable pipeline commands queued by the weekly batch (rmm weekly --save, role
-- rmm_rw) and run by kalshi-worker's `ops-fixes` command, which only runs an allowlist of commands
-- and records the outcome here. The Weekly Review reports what was queued and how it went.
create table ops.fix_requests (
  id           bigserial primary key,
  created_at   timestamptz not null default now(),
  created_by   text not null,                 -- 'weekly' or a person
  check_name   text,                          -- the health check that asked for it
  command      text not null,                 -- e.g. 'fortune'
  args         text[] not null default '{}',  -- e.g. {--symbol,VZ}
  reason       text,
  status       text not null default 'queued' check (status in ('queued', 'running', 'done', 'failed', 'rejected')),
  started_at   timestamptz,
  finished_at  timestamptz,
  output       text
);
create index fix_requests_status on ops.fix_requests (status, created_at);
grant select on ops.fix_requests to rmm_ro;
grant select, insert on ops.fix_requests to rmm_rw;
grant usage on sequence ops.fix_requests_id_seq to rmm_rw;
