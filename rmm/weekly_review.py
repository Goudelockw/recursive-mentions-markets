"""The Weekly Review: one page for the week's pipeline health, what was fixed automatically, what
needs the owner, live results and the model status.

    python -m rmm weekly-review [--page]

Reads the latest ops run (written by the Railway batch), the fix queue, the model versions and, if the
Ops task has written it, outputs/weekly/YYYY-Www_ops-proposals.json: the items that need a decision,
each with its evidence and the exact change to make. Proposals are never applied here; the owner
approves them by id ("approve W44-2") in a Claude session that can write to Neon.
"""
from __future__ import annotations

import html
import json
from dataclasses import dataclass
from datetime import date, datetime

from . import db, paths

e = html.escape
MARK = {"ok": ("ok", "p-ok"), "warn": ("warn", "p-warn"), "fail": ("fail", "p-bad")}
FIX_CLS = {"done": "p-ok", "queued": "p-you", "running": "p-you", "failed": "p-bad", "rejected": "p-n"}


@dataclass
class Review:
    week: str
    generated: datetime
    run: dict | None
    checks: list[dict]
    metrics: list[dict]
    fixes: list[dict]
    versions: list[dict]
    proposals: list[dict]


def proposals_path(day: date):
    return paths.weekly(day, "ops-proposals", "json")


def load(now: datetime) -> Review:
    q = db.query
    run = (q("select run_id, started_at::text, ok, summary::text from ops.runs where job = 'weekly' "
             "order by run_id desc limit 1") or [None])[0]
    checks = q("select check_name, status, value::float, detail from ops.health_checks where run_id = $1 "
               "order by case status when 'fail' then 0 when 'warn' then 1 else 2 end, check_name", [run["run_id"]]) if run else []
    metrics = q("select metric, segment, value::float, n from ops.weekly_metrics where run_id = $1", [run["run_id"]]) if run else []
    fixes = q("""select id, created_at::date::text as created, check_name, command, array_to_string(args, ' ') as args, reason,
                        status, finished_at::text as finished, left(coalesce(output, ''), 4000) as output
                 from ops.fix_requests where created_at > now() - interval '14 days' order by id desc""")
    versions = q("""select version, status, trained_through::text, promoted_at::date::text as promoted,
                           review->>'verdict' as verdict, (review->>'against')::int as against
                    from kalshi.model_versions order by version desc""")
    p = proposals_path(now.date())
    proposals = json.loads(p.read_text()) if p.exists() else []
    year, wk, _ = now.isocalendar()
    return Review(f"{year}-W{wk:02d}", now, run, checks, metrics, fixes, versions, proposals)


def _metric(r: Review, metric: str, seg: str):
    return next((m for m in r.metrics if m["metric"] == metric and m["segment"] == seg), None)


def _tail(text: str, n: int = 6) -> str:
    lines = [ln for ln in (text or "").splitlines() if ln.strip()]
    return "\n".join(lines[-n:])


def headline(r: Review) -> str:
    fails = sum(c["status"] == "fail" for c in r.checks)
    warns = sum(c["status"] == "warn" for c in r.checks)
    fixed = sum(f["status"] == "done" for f in r.fixes)
    queued = sum(f["status"] in ("queued", "running") for f in r.fixes)
    parts = [f"{fails} failing" if fails else "nothing failing", f"{warns} warnings",
             f"{fixed} fixes done, {queued} queued", f"{len(r.proposals)} need you"]
    return " · ".join(parts)


def render_html(r: Review) -> str:
    live = next((v for v in r.versions if v["status"] == "live"), None)
    newest = r.versions[0] if r.versions else None
    model_line = (f"Live model v{live['version']}, trained through {live['trained_through']}, live since {live['promoted']}."
                  if live else "No live model.")
    if newest and newest["status"] == "challenger":
        model_line += f" Newest challenger v{newest['version']}: {newest['verdict'] or 'not reviewed'} vs v{newest['against']}."

    props = "".join(
        f"""<div class='card prop'><div class='rel-h'><span class='pill p-you'>{e(p.get('id', '?'))}</span><b>{e(p.get('title', ''))}</b>
<span class='meta'>{e(p.get('kind', ''))}{' · from ' + e(p['check']) if p.get('check') else ''}</span></div>
<p class='note'>{e(p.get('why', ''))}</p>
{''.join(f"<div class='meta'>Evidence: <a href='{e(u)}'>{e(u)}</a></div>" for u in p.get('evidence', []))}
{f"<pre>{e(p['sql'])}</pre>" if p.get('sql') else ''}
{f"<div class='meta'>Branch: <code>{e(p['branch'])}</code> · <a href='{e(p.get('compare_url', ''))}'>compare</a></div>" if p.get('branch') else ''}
<div class='meta'>To apply: reply <code>approve {e(p.get('id', '?'))}</code> to Claude. Nothing changes until you do.</div></div>"""
        for p in r.proposals) or "<p class='meta'>Nothing needs you this week.</p>"

    fixes = "".join(
        f"<tr><td class='num'>#{f['id']}</td><td>{f['created']}</td><td><code>{e(f['command'])} {e(f['args'] or '')}</code>"
        f"<div class='meta'>{e(f['reason'] or '')}</div></td><td><span class='pill {FIX_CLS.get(f['status'], 'p-n')}'>{f['status']}</span></td>"
        f"<td><pre class='out'>{e(_tail(f['output']))}</pre></td></tr>" for f in r.fixes) or \
        "<tr><td colspan='5' class='meta'>No fixes queued in the last 14 days.</td></tr>"

    checks = "".join(
        f"<tr><td><span class='pill {MARK[c['status']][1]}'>{MARK[c['status']][0]}</span></td><td>{e(c['check_name'])}</td>"
        f"<td>{e(c['detail'] or '')}</td></tr>" for c in r.checks) or "<tr><td colspan='3' class='meta'>No weekly run yet.</td></tr>"

    live_rows = []
    for seg, name in (("live_7d", "Last 7 days"), ("live_30d", "Last 30 days"), ("live_90d", "Last 90 days")):
        t, c, w = (_metric(r, m, seg) for m in ("trades", "pnl_c_per_trade", "win_rate"))
        bm, bk = _metric(r, "brier_model", seg), _metric(r, "brier_market", seg)
        f = lambda m, fmt: "–" if not m or m["value"] is None else fmt.format(m["value"])
        live_rows.append(f"<tr><td>{name}</td><td class='num'>{f(t, '{:.0f}')}</td><td class='num'>{f(c, '{:+.1f}¢')}</td>"
                         f"<td class='num'>{f(w, '{:.0%}')}</td><td class='num'>{f(bm, '{:.4f}')}</td><td class='num'>{f(bk, '{:.4f}')}</td>"
                         f"<td class='num'>{bm['n'] if bm else '–'}</td></tr>")

    return TEMPLATE.format(week=r.week, headline=e(headline(r)), generated=f"{r.generated:%Y-%m-%d %H:%M} UTC",
                           run=(f"Checks from the weekly batch run of {r.run['started_at'][:16]} UTC." if r.run else "No weekly batch run yet."),
                           props=props, fixes=fixes, checks=checks, live="".join(live_rows), model=e(model_line))


def render_md(r: Review) -> str:
    out = [f"# Weekly Review · {r.week}", "", f"**{headline(r)}**", "", f"_Generated {r.generated:%Y-%m-%d %H:%M} UTC._", "",
           "## Needs you", ""]
    for p in r.proposals:
        out += [f"### {p.get('id')} · {p.get('title')}", "", p.get("why", ""), ""]
        out += [f"- Evidence: {u}" for u in p.get("evidence", [])]
        if p.get("sql"):
            out += ["", "```sql", p["sql"], "```"]
        if p.get("branch"):
            out += ["", f"Branch `{p['branch']}`: {p.get('compare_url', '')}"]
        out += ["", f"To apply: reply `approve {p.get('id')}` to Claude.", ""]
    if not r.proposals:
        out += ["Nothing needs you this week.", ""]
    out += ["## Fixed automatically", "", "| # | Queued | Command | Status |", "|--:|---|---|---|"]
    out += [f"| {f['id']} | {f['created']} | `{f['command']} {f['args'] or ''}` | {f['status']} |" for f in r.fixes]
    out += ["", "## Health checks", ""] + [f"- **{c['status']}** {c['check_name']}: {c['detail']}" for c in r.checks] + [""]
    return "\n".join(out)


TEMPLATE = """<title>Weekly Review</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@700;800&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
:root{{--bg:#f6f7f9;--surface:#fff;--fg:#17202b;--muted:#5b6675;--line:#dde2e8;
--ok:#1d7a4a;--ok-bg:#e4f3ea;--you:#6a3fb0;--you-bg:#f1ebfb;--warn:#a86a00;--warn-bg:#fbf1dc;--bad:#b3261e;--bad-bg:#fbe5e3;
--display:"Archivo","Helvetica Neue",Arial,sans-serif;--body:"IBM Plex Sans",system-ui,sans-serif;--mono:"IBM Plex Mono",ui-monospace,Menlo,monospace}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--bg:#0f141a;--surface:#161d26;--fg:#e6ebf1;--muted:#9aa6b4;--line:#2a3440;
--ok:#5fcf91;--ok-bg:#15301f;--you:#b897f0;--you-bg:#2a1f40;--warn:#e6b04d;--warn-bg:#352812;--bad:#f08079;--bad-bg:#3a1714;color-scheme:dark}}}}
:root[data-theme="dark"]{{--bg:#0f141a;--surface:#161d26;--fg:#e6ebf1;--muted:#9aa6b4;--line:#2a3440;
--ok:#5fcf91;--ok-bg:#15301f;--you:#b897f0;--you-bg:#2a1f40;--warn:#e6b04d;--warn-bg:#352812;--bad:#f08079;--bad-bg:#3a1714;color-scheme:dark}}
*{{box-sizing:border-box}}
body{{background:var(--bg);color:var(--fg);font-family:var(--body);font-size:14.5px;line-height:1.5}}
.wrap{{max-width:1080px;margin:0 auto;padding-block:28px 56px;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));display:flex;flex-direction:column;gap:28px}}
h1,h2{{font-family:var(--display);margin:0;text-wrap:balance}} h1{{font-size:clamp(24px,4vw,34px);font-weight:800}} h2{{font-size:19px}}
section{{display:flex;flex-direction:column;gap:10px}}
.meta{{font-size:12.5px;color:var(--muted)}} .note{{margin:0;font-size:14px}} .sub{{margin:0;font-size:16px;font-weight:500}}
.pill{{font-family:var(--mono);font-size:11px;padding:2px 8px;border-radius:999px;white-space:nowrap;display:inline-block}}
.p-ok{{background:var(--ok-bg);color:var(--ok)}} .p-you{{background:var(--you-bg);color:var(--you)}} .p-warn{{background:var(--warn-bg);color:var(--warn)}}
.p-bad{{background:var(--bad-bg);color:var(--bad)}} .p-n{{background:var(--bg);color:var(--muted);border:1px solid var(--line)}}
.card{{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:14px 16px;display:flex;flex-direction:column;gap:8px;min-width:0}}
.rel-h{{display:flex;flex-wrap:wrap;gap:6px 10px;align-items:baseline}}
pre{{font-family:var(--mono);font-size:12.5px;background:var(--bg);border:1px solid var(--line);border-radius:6px;padding:8px 10px;overflow-x:auto;margin:0;white-space:pre}}
pre.out{{font-size:11px;max-width:420px;white-space:pre-wrap;word-break:break-word;border:0;padding:0;background:transparent;color:var(--muted)}}
a{{color:inherit}} code{{font-family:var(--mono);font-size:.9em}}
.tbl{{overflow-x:auto;background:var(--surface);border:1px solid var(--line);border-radius:10px}}
table{{border-collapse:collapse;width:100%;min-width:680px;font-size:13.5px}}
th,td{{text-align:left;padding:8px 10px;border-bottom:1px solid var(--line);vertical-align:top}}
th{{font-family:var(--mono);font-size:11px;letter-spacing:.05em;text-transform:uppercase;color:var(--muted);font-weight:500;background:var(--bg);white-space:nowrap}}
tr:last-child td{{border-bottom:0}} .num{{text-align:right;font-family:var(--mono);font-variant-numeric:tabular-nums;white-space:nowrap}}
</style>
<div class="wrap">
<header style="display:flex;flex-direction:column;gap:6px">
  <div class="meta">Mentions pipeline · Weekly Review · generated {generated}</div>
  <h1>Week {week}</h1>
  <p class="sub">{headline}</p>
  <p class="meta" style="margin:0">{run} {model}</p>
</header>
<section><h2>Needs you</h2>{props}</section>
<section><h2>Fixed automatically</h2>
<p class="meta" style="margin:0">Safe, repeatable commands the weekly batch queued and kalshi-worker's ops-fixes ran (daily at 03:30 UTC). Last 14 days.</p>
<div class="tbl"><table><thead><tr><th class="num">#</th><th>Queued</th><th>Command</th><th>Status</th><th>Log (last lines)</th></tr></thead><tbody>{fixes}</tbody></table></div></section>
<section><h2>Health checks</h2><div class="tbl"><table><thead><tr><th>Status</th><th>Check</th><th>Detail</th></tr></thead><tbody>{checks}</tbody></table></div></section>
<section><h2>Live results</h2><div class="tbl"><table><thead><tr><th>Window</th><th class="num">Trades</th><th class="num">¢ per trade</th>
<th class="num">Won</th><th class="num">Model Brier</th><th class="num">Market Brier</th><th class="num">Graded markets</th></tr></thead><tbody>{live}</tbody></table></div></section>
</div>
"""
