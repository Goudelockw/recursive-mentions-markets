-- Model versions: every fit is kept; exactly one is live. The board keeps reading
-- kalshi.model_coefficients / kalshi.model_backtest, which kalshi.promote_model(N) rewrites from a
-- stored version in one transaction. Rolling back is promoting the previous version again.

create table kalshi.model_versions (
  version          int primary key,
  status           text not null check (status in ('live', 'challenger', 'retired')),
  trained_through  date not null,
  fitted_at        timestamptz not null,
  source           text not null,           -- 'refit_models.R' or 'rmm refit'
  metrics          jsonb,                   -- walk-forward Brier, k, markets per stage
  notes            text,
  created_at       timestamptz not null default now(),
  promoted_at      timestamptz,
  retired_at       timestamptz
);
create unique index model_versions_one_live on kalshi.model_versions (status) where status = 'live';

create table kalshi.model_version_coefficients (
  version  int not null references kalshi.model_versions on delete cascade,
  model    text not null,
  term     text not null,
  coef     numeric not null,
  primary key (version, model, term)
);

create table kalshi.model_version_backtest (
  version  int not null references kalshi.model_versions on delete cascade,
  ticker   text not null,
  stage    text not null check (stage in ('call_start', 'early_24h')),
  p_model  numeric not null,
  primary key (version, ticker, stage)
);

-- Only kalshi.promote_model (which runs as the owner) may mark a version live, and a live
-- version's stored coefficients and backtest can't be edited.
create or replace function kalshi.guard_model_versions() returns trigger language plpgsql as $$
begin
  if tg_table_name = 'model_versions' then
    if (tg_op = 'INSERT' and new.status <> 'challenger')
       or (tg_op = 'UPDATE' and new.status is distinct from old.status
           and current_setting('kalshi.promoting', true) is distinct from 'on') then
      raise exception 'model versions start as challengers; use kalshi.promote_model(version) to change status';
    end if;
    return new;
  end if;
  if exists (select 1 from kalshi.model_versions v
             where v.version = coalesce(new.version, old.version) and v.status <> 'challenger') then
    raise exception 'v% is not a challenger; its coefficients and backtest are frozen', coalesce(new.version, old.version);
  end if;
  return coalesce(new, old);
end $$;
create trigger guard before insert or update on kalshi.model_versions
  for each row execute function kalshi.guard_model_versions();
create trigger guard before insert or update or delete on kalshi.model_version_coefficients
  for each row execute function kalshi.guard_model_versions();
create trigger guard before insert or update or delete on kalshi.model_version_backtest
  for each row execute function kalshi.guard_model_versions();

create or replace function kalshi.promote_model(p_version int) returns text
language plpgsql security definer set search_path = kalshi, pg_temp as $$
declare v kalshi.model_versions; old_live int;
begin
  select * into v from kalshi.model_versions where version = p_version for update;
  if not found then raise exception 'model version % does not exist', p_version; end if;
  if v.status = 'live' then return format('v%s is already live', p_version); end if;
  if not exists (select 1 from kalshi.model_version_coefficients where version = p_version) then
    raise exception 'v% has no coefficients', p_version;
  end if;
  perform set_config('kalshi.promoting', 'on', true);
  select version into old_live from kalshi.model_versions where status = 'live' for update;
  update kalshi.model_versions set status = 'retired', retired_at = now() where status = 'live';
  delete from kalshi.model_coefficients;
  insert into kalshi.model_coefficients (model, term, coef, trained_through, fitted_at)
    select model, term, coef, v.trained_through, v.fitted_at
    from kalshi.model_version_coefficients where version = p_version;
  delete from kalshi.model_backtest;
  insert into kalshi.model_backtest (ticker, stage, p_model)
    select ticker, stage, p_model from kalshi.model_version_backtest where version = p_version;
  update kalshi.model_versions set status = 'live', promoted_at = now(), retired_at = null
    where version = p_version;
  perform set_config('kalshi.promoting', 'off', true);
  return format('v%s is live (was %s)', p_version, coalesce('v' || old_live, 'none'));
end $$;
revoke all on function kalshi.promote_model(int) from public;
