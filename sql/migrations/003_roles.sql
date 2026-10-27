-- Roles used by this repo (passwords are set outside the repo).
--   rmm_ro  read-only: the Trade Sheet and Cost Report tasks (cloud sessions).
--   rmm_rw  reads everything; writes only challenger model versions and ops rows. Cannot touch
--           the live model: promotion is kalshi.promote_model(N), which only the owner may run.
grant usage on schema ops to rmm_ro;
grant select on all tables in schema ops to rmm_ro;
alter default privileges for role neondb_owner in schema ops grant select on tables to rmm_ro;

-- create role rmm_rw login password '...';
alter role rmm_rw set statement_timeout = '10min';
grant connect on database neondb to rmm_rw;
grant usage on schema kalshi, ops to rmm_rw;
grant select on all tables in schema kalshi, ops to rmm_rw;
alter default privileges for role neondb_owner in schema kalshi grant select on tables to rmm_rw;
grant insert, update, delete on kalshi.model_versions, kalshi.model_version_coefficients,
  kalshi.model_version_backtest to rmm_rw;
grant insert, update on ops.runs, ops.health_checks, ops.weekly_metrics to rmm_rw;
grant usage on all sequences in schema ops to rmm_rw;
