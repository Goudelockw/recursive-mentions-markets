"""Weekly batch: health checks, live grading and calibration, saved to ops.* for the Sunday Ops task.

    python -m rmm weekly            print the checks and metrics (read-only, rmm_ro is enough)
    python -m rmm weekly --save     also write them to ops.runs / ops.health_checks / ops.weekly_metrics, and
                                    queue the fixes it may make on its own in ops.fix_requests (rmm_rw)

Every check is one read-only query plus a rule that turns its result into ok / warn / fail and a
one-line detail naming what to look at. queue_fixes() turns some findings into safe, repeatable
pipeline commands (FIX_RULES) that kalshi-worker's `ops-fixes` runs; everything that needs judgment
is left to the Sunday Ops task.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Callable

from . import db

# job -> hours without a successful run before it counts as stale (filings and news skip weekends)
JOB_LIMITS = {"sync": 3, "reconcile": 30, "transcripts": 30, "filings": 72, "news": 72}
LOW_CONF_CALL_TIME = "source like '%default%' or source like '%(1 past calls)%'"


@dataclass
class Check:
    name: str
    status: str          # ok | warn | fail
    value: float | None
    detail: str


@dataclass
class Metric:
    metric: str
    segment: str
    value: float | None
    n: int | None


def _one(sql: str) -> dict:
    rows = db.query(sql)
    return rows[0] if rows else {}


def _int(v) -> int:
    return int(float(v)) if v is not None else 0


def check_jobs() -> list[Check]:
    rows = {r["job"]: r for r in db.query("""
        select job,
               round(extract(epoch from now() - max(started_at) filter (where ok)) / 3600, 1) as hours_since_ok,
               count(*) filter (where ok is false) as failed,
               count(*) filter (where finished_at is null and started_at < now() - interval '2 hours') as cut_off,
               count(*) as runs
        from kalshi.ingest_runs where started_at > now() - interval '7 days' group by job""")}
    out = []
    for job, limit in JOB_LIMITS.items():
        r = rows.get(job)
        if not r or r["hours_since_ok"] is None:
            out.append(Check(f"job:{job}", "fail", None, f"{job}: no successful run in 7 days"))
            continue
        h, failed, cut = float(r["hours_since_ok"]), _int(r["failed"]), _int(r["cut_off"])
        status = "fail" if h > limit else "warn" if failed or cut else "ok"
        extra = (f", {failed} failed" if failed else "") + (f", {cut} cut off mid-run" if cut else "")
        out.append(Check(f"job:{job}", status, h, f"{job}: last ok {h:.1f}h ago, {_int(r['runs'])} runs this week{extra}"))
    return out


def check_transcript_gaps() -> Check:
    r = _one("""select count(*) as n, string_agg(symbol || ' ' || target_date, ', ' order by target_date desc) as list
                from kalshi.v_transcript_gaps where target_date >= current_date - 30""")
    n = _int(r.get("n"))
    return Check("transcript_gaps_30d", "warn" if n else "ok", n,
                 f"{n} calls in the last 30 days with no transcript" + (f": {r['list']}" if n else ""))


def check_label_audit() -> list[Check]:
    rows = db.query("""select audit, count(*) as n,
                              string_agg(symbol || ' \"' || word || '\"', '; ' order by call_date_est desc) as list
                       from kalshi.v_label_audit
                       where call_date_est >= current_date - 30 and audit <> 'agree' group by audit""")
    by = {r["audit"]: r for r in rows}
    out = []
    for audit, what in (("kalshi_yes_we_miss", "Kalshi settled YES but our transcript doesn't count the word"),
                        ("kalshi_no_we_count", "Kalshi settled NO but our transcript counts the word")):
        n = _int(by.get(audit, {}).get("n"))
        out.append(Check(f"settlement_vs_transcript:{audit}", "warn" if n else "ok", n,
                         f"{n} markets in 30 days: {what}" + (f": {by[audit]['list'][:400]}" if n else "")))
    n = _int(by.get("no_transcript", {}).get("n"))
    out.append(Check("settled_without_transcript_30d", "warn" if n > 10 else "ok", n,
                     f"{n} settled markets in 30 days have no transcript to check against"))
    return out


def check_simple(name: str, sql: str, describe: Callable[[dict], str], warn_if: Callable[[dict], bool]) -> Check:
    r = _one(sql)
    n = _int(r.get("n"))
    return Check(name, "warn" if warn_if(r) else "ok", n, describe(r))


def run_checks() -> list[Check]:
    checks = check_jobs()
    checks.append(check_transcript_gaps())
    checks += check_label_audit()
    checks.append(check_simple(
        "unlabeled_open_words",
        "select count(*) as n, string_agg(symbol || ' ' || word_key, ', ') as list from kalshi.v_unlabeled_words where has_open_market",
        lambda r: f"{_int(r['n'])} words on open markets have no category label" + (f": {r['list'][:300]}" if _int(r['n']) else ""),
        lambda r: _int(r["n"]) > 0))
    checks.append(check_simple(
        "check_date_calls",
        "select count(distinct event_ticker) as n, string_agg(distinct symbol, ', ') as list from kalshi.v_mentions_board where action = 'CHECK DATE'",
        lambda r: f"{_int(r['n'])} calls passed their estimated time with no release" + (f": {r['list']}" if _int(r['n']) else ""),
        lambda r: _int(r["n"]) > 0))
    checks.append(check_simple(
        "low_confidence_call_times_7d",
        f"""select count(*) as n, string_agg(symbol || ' ' || to_char(call_start_est at time zone 'America/New_York', 'Dy HH12:MI am'), ', ' order by call_start_est) as list
            from (select *, call_start_source as source from kalshi.v_upcoming_call_times) t
            where call_start_est between now() and now() + interval '7 days' and ({LOW_CONF_CALL_TIME})""",
        lambda r: f"{_int(r['n'])} calls in the next 7 days with a default or one-call estimate of the time"
                  + (f": {r['list']}" if _int(r['n']) else ""),
        lambda r: _int(r["n"]) > 0))
    checks.append(check_simple(
        "settlement_lag",
        "select count(*) as n from kalshi.markets where close_time < now() - interval '3 days' and status not in ('settled', 'finalized')",
        lambda r: f"{_int(r['n'])} markets closed 3+ days ago without a result",
        lambda r: _int(r["n"]) > 0))
    checks.append(check_simple(
        "score_log",
        """select count(*) filter (where logged_at > now() - interval '7 days') as n,
                  round(extract(epoch from now() - max(logged_at)) / 86400, 1) as days
           from kalshi.model_score_log""",
        lambda r: f"{_int(r['n'])} scores logged this week (last {r['days']} days ago)",
        lambda r: _int(r["n"]) == 0))
    checks.append(check_simple(
        "live_model_age",
        """select (current_date - trained_through) as n, version from kalshi.model_versions where status = 'live'""",
        lambda r: f"live model v{r.get('version')} trained through {_int(r.get('n'))} days ago",
        lambda r: _int(r.get("n")) > 120))
    return checks


def run_metrics() -> list[Metric]:
    """Live results from v_mentions_history. Its `won` is whether the trade won (empty without a
    trade); whether the word was said is `result` = 'YES', which Brier and calibration use."""
    out = []
    for days in (7, 30, 90):
        r = _one(f"""
            select count(*) filter (where action in ('TRADE', 'TRADE+')) as trades,
                   avg(pnl_c) filter (where action in ('TRADE', 'TRADE+')) as pnl_c,
                   avg((pnl_c > 0)::int) filter (where action in ('TRADE', 'TRADE+')) as win_rate,
                   count(*) filter (where result in ('YES', 'NO')) as graded,
                   avg(power(model_c / 100.0 - (result = 'YES')::int, 2)) filter (where result in ('YES', 'NO')) as brier_model,
                   avg(power((bid_c + ask_c) / 200.0 - (result = 'YES')::int, 2)) filter (where result in ('YES', 'NO')) as brier_market
            from kalshi.v_mentions_history where source = 'live' and call_date >= current_date - {days}""")
        seg = f"live_{days}d"
        trades, graded = _int(r.get("trades")), _int(r.get("graded"))
        for name, n in (("trades", trades), ("pnl_c_per_trade", trades), ("win_rate", trades),
                        ("brier_model", graded), ("brier_market", graded)):
            key = {"trades": "trades"}.get(name, name if name != "pnl_c_per_trade" else "pnl_c")
            v = r.get(key)
            out.append(Metric(name, seg, float(v) if v is not None else None, n))
    for r in db.query("""
            select floor(least(model_c, 99.9) / 10) * 10 as bucket, count(*) as n,
                   avg(model_c) / 100 as predicted, avg((result = 'YES')::int) as actual
            from kalshi.v_mentions_history
            where source = 'live' and result in ('YES', 'NO') and call_date >= current_date - 90
            group by 1 order by 1"""):
        b = int(float(r["bucket"]))
        out.append(Metric("calibration_predicted", f"{b}-{b + 10}c", float(r["predicted"]), _int(r["n"])))
        out.append(Metric("calibration_actual", f"{b}-{b + 10}c", float(r["actual"]), _int(r["n"])))
    return out


def save(checks: list[Check], metrics: list[Metric]) -> int:
    summary = {s: sum(c.status == s for c in checks) for s in ("ok", "warn", "fail")}
    run_id = int(db.transaction([("insert into ops.runs (job, ok, finished_at, summary) values ('weekly', $1, now(), $2::jsonb) "
                                  "returning run_id", [summary["fail"] == 0, json.dumps(summary)])])[0][0]["run_id"])
    db.transaction([
        ("insert into ops.health_checks (run_id, check_name, status, value, detail) "
         "select $1, check_name, status, value, detail from jsonb_to_recordset($2::jsonb) "
         "as x(check_name text, status text, value numeric, detail text)",
         [run_id, json.dumps([{"check_name": c.name, "status": c.status, "value": c.value, "detail": c.detail} for c in checks])]),
        ("insert into ops.weekly_metrics (run_id, metric, segment, value, n) "
         "select $1, metric, segment, value, n from jsonb_to_recordset($2::jsonb) "
         "as x(metric text, segment text, value numeric, n int)",
         [run_id, json.dumps([m.__dict__ for m in metrics])]),
    ])
    return run_id


def render(checks: list[Check], metrics: list[Metric]) -> str:
    mark = {"ok": "ok  ", "warn": "WARN", "fail": "FAIL"}
    lines = ["Health checks"] + [f"  {mark[c.status]} {c.detail}" for c in sorted(checks, key=lambda c: "fwo".index(c.status[0]))]
    lines.append("Live results")
    for seg in ("live_7d", "live_30d", "live_90d"):
        m = {x.metric: x for x in metrics if x.segment == seg}
        t = m["trades"]
        pnl = m["pnl_c_per_trade"].value
        bm, bk = m["brier_model"].value, m["brier_market"].value
        lines.append(f"  {seg[5:]:>4}: {int(t.value or 0)} trades"
                     + (f", {pnl:+.1f}c/trade, {100 * (m['win_rate'].value or 0):.0f}% won" if pnl is not None else "")
                     + (f"; Brier {bm:.4f} vs market {bk:.4f} on {m['brier_model'].n} markets" if bm is not None else ""))
    return "\n".join(lines)


# ---------------------------------------------------------------- fixes the batch may queue on its own

# (check, why, SQL returning one row per fix with columns command and args (text[])). Every rule must
# map to a command on kalshi-worker's ops_fixes.ALLOWED list; anything else would be rejected there.
FIX_RULES = [
    ("transcript_gaps_30d", "No transcript for a call in the last 30 days: try Fortune for that company",
     """select distinct 'fortune' as command, array['--symbol', symbol] as args
        from kalshi.v_transcript_gaps where target_date >= current_date - 30"""),
    ("transcript_gaps_30d", "Calls without a transcript: one Equibles pass",
     """select 'equibles' as command, array[]::text[] as args
        where exists (select 1 from kalshi.v_transcript_gaps where target_date >= current_date - 30)"""),
    ("check_date_calls", "The estimated call time passed with no release found: re-fetch that company's filings",
     """select distinct 'filings' as command, array['--backfill-symbol', symbol] as args
        from kalshi.v_mentions_board where action = 'CHECK DATE'"""),
    ("settlement_lag", "Markets closed 3+ days ago without a result: re-fetch them",
     """select 'sweep' as command, array[]::text[] as args
        where exists (select 1 from kalshi.markets where close_time < now() - interval '3 days'
                      and status not in ('settled', 'finalized'))"""),
]


def plan_fixes() -> list[dict]:
    """The fixes the rules ask for now, minus any queued or run in the last 7 days."""
    recent = {(r["command"], tuple(r["args"] or [])) for r in db.query(
        "select command, args from ops.fix_requests where created_at > now() - interval '7 days' and status <> 'rejected'")}
    out, seen = [], set()
    for check, why, sql in FIX_RULES:
        for r in db.query(sql):
            args = r["args"] if isinstance(r["args"], list) else _pg_array(r["args"])
            key = (r["command"], tuple(args))
            if key in recent or key in seen:
                continue
            seen.add(key)
            out.append({"check_name": check, "command": r["command"], "args": args, "reason": why})
    return out


def _pg_array(v) -> list[str]:
    """'{--symbol,VZ}' (how the HTTPS transport returns text[]) -> ['--symbol', 'VZ']."""
    v = (v or "").strip("{}")
    return [x.strip('"') for x in v.split(",")] if v else []


def queue_fixes(fixes: list[dict]) -> int:
    if not fixes:
        return 0
    db.transaction([("insert into ops.fix_requests (created_by, check_name, command, args, reason) "
                     "select 'weekly', check_name, command, array(select jsonb_array_elements_text(args))::text[], reason "
                     "from jsonb_to_recordset($1::jsonb) as x(check_name text, command text, args jsonb, reason text)",
                     [json.dumps(fixes)])])
    return len(fixes)
