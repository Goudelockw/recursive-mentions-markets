"""The Models page: every model version, which one is live, how the live model does in its
walk-forward backtest and live, and how the coefficients moved between versions.

    python -m rmm models --page     writes outputs/models/index.html and outputs/models/README.md

Read-only (rmm_ro is enough). The Sunday Cost Report task republishes the page each week.
"""
from __future__ import annotations

import html
import json
from dataclasses import dataclass
from datetime import datetime

from . import db

STAGES = {"call_start": "At call start (after the release)", "early_24h": "24h before the call"}


@dataclass
class Data:
    versions: list[dict]
    coefs: list[dict]
    monthly: list[dict]
    calibration: list[dict]
    live: list[dict]
    generated: datetime


def load(now: datetime) -> Data:
    q = db.query
    versions = q("""select version, status, trained_through::text, fitted_at::date::text as fitted, source, metrics::text,
                           notes, promoted_at::date::text as promoted, retired_at::date::text as retired
                    from kalshi.model_versions order by version desc""")
    coefs = q("select version, model, term, coef from kalshi.model_version_coefficients order by model, term, version")
    monthly = q("""select stage, month, count(*) filter (where action in ('TRADE', 'TRADE+')) as trades,
                          avg(pnl_c) filter (where action in ('TRADE', 'TRADE+')) as pnl_c
                   from kalshi.v_mentions_history where source = 'backtest' group by 1, 2 order by 1, 2""")
    calibration = q("""select stage, floor(least(model_c, 99.9) / 10) * 10 as bucket, count(*) as n,
                              avg(model_c) as predicted, 100 * avg((result = 'YES')::int) as actual
                       from kalshi.v_mentions_history
                       where source = 'backtest' and result in ('YES', 'NO') group by 1, 2 order by 1, 2""")
    live = q("""select count(*) filter (where action in ('TRADE', 'TRADE+')) as trades,
                       avg(pnl_c) filter (where action in ('TRADE', 'TRADE+')) as pnl_c,
                       count(*) filter (where result in ('YES', 'NO')) as graded,
                       avg(power(model_c / 100.0 - (result = 'YES')::int, 2)) filter (where result in ('YES', 'NO')) as brier_model,
                       avg(power((bid_c + ask_c) / 200.0 - (result = 'YES')::int, 2)) filter (where result in ('YES', 'NO')) as brier_market,
                       min(call_date)::text as since
                from kalshi.v_mentions_history where source = 'live'""")
    for v in versions:
        v["metrics"] = json.loads(v["metrics"]) if v.get("metrics") else {}
    return Data(versions, coefs, monthly, calibration, live, now)


# ---------------------------------------------------------------- pieces

def _f(v, fmt="{:.4f}", dash="–"):
    return dash if v is None else fmt.format(float(v))


def _pill(status: str) -> str:
    cls = {"live": "p-ok", "challenger": "p-you", "retired": "p-n"}[status]
    return f'<span class="pill {cls}">{status}</span>'


def bars_svg(rows: list[dict]) -> str:
    """Cents per trade by month, one stage. Blue months made money, red months lost it."""
    W, H, L, R, T, B = 560, 200, 44, 8, 12, 28
    vals = [float(r["pnl_c"]) if r["pnl_c"] is not None else 0.0 for r in rows]
    top = max(5.0, max(vals + [0])) * 1.15
    bot = min(0.0, min(vals + [0])) * 1.15
    y = lambda v: T + (top - v) / (top - bot) * (H - T - B)
    n = len(rows)
    step = (W - L - R) / max(n, 1)
    bw = min(28.0, step * 0.62)
    ticks = [t for t in range(int(bot // 5) * 5, int(top) + 1, 5) if bot <= t <= top]
    out = [f'<svg viewBox="0 0 {W} {H}" class="chart" role="img" aria-label="Cents per trade by month">']
    for t in ticks:
        out.append(f'<line x1="{L}" x2="{W - R}" y1="{y(t):.1f}" y2="{y(t):.1f}" class="{"zero" if t == 0 else "grid"}"/>'
                   f'<text x="{L - 6}" y="{y(t) + 4:.1f}" class="tick" text-anchor="end">{t:+d}¢</text>')
    for i, (r, v) in enumerate(zip(rows, vals)):
        x = L + i * step + (step - bw) / 2
        y0, y1 = y(0), y(v)
        h = max(abs(y1 - y0), 1.0)
        cls = "gain" if v >= 0 else "loss"
        tip = f"{r['month']}: {v:+.1f}¢ per trade on {int(float(r['trades']))} trades"
        out.append(f'<g class="bar"><title>{html.escape(tip)}</title>'
                   f'<rect x="{x - (step - bw) / 2:.1f}" y="{T}" width="{step:.1f}" height="{H - T - B}" class="hit"/>'
                   f'<rect x="{x:.1f}" y="{min(y0, y1):.1f}" width="{bw:.1f}" height="{h:.1f}" rx="2" class="{cls}"/></g>')
        if i % 2 == 0 or i == n - 1:
            out.append(f'<text x="{x + bw / 2:.1f}" y="{H - 8}" class="tick" text-anchor="middle">{r["month"][2:]}</text>')
    out.append("</svg>")
    return "".join(out)


def calib_svg(rows: list[dict]) -> str:
    """Predicted P(YES) against how often the word was said, by 10¢ bucket."""
    S, L, B, T, R = 220, 34, 26, 8, 8
    span = S - L - R
    px = lambda v: L + v / 100 * span
    py = lambda v: T + (100 - v) / 100 * (S - T - B)
    out = [f'<svg viewBox="0 0 {S} {S}" class="chart calib" role="img" aria-label="Calibration">',
           f'<line x1="{px(0)}" y1="{py(0)}" x2="{px(100)}" y2="{py(100)}" class="diag"/>']
    for t in (0, 50, 100):
        out.append(f'<text x="{px(t):.1f}" y="{S - 8}" class="tick" text-anchor="middle">{t}</text>'
                   f'<text x="{L - 5}" y="{py(t) + 4:.1f}" class="tick" text-anchor="end">{t}</text>')
    for r in rows:
        p, a, n = float(r["predicted"]), float(r["actual"]), int(float(r["n"]))
        tip = f"model said {p:.0f}%, said {a:.0f}% of the time ({n} markets)"
        out.append(f'<g class="dot"><title>{tip}</title><circle cx="{px(p):.1f}" cy="{py(a):.1f}" r="9" class="hit"/>'
                   f'<circle cx="{px(p):.1f}" cy="{py(a):.1f}" r="4.5" class="pt"/></g>')
    out.append("</svg>")
    return "".join(out)


def coef_table(d: Data) -> str:
    shown = [v["version"] for v in d.versions][:4]
    live = next((v["version"] for v in d.versions if v["status"] == "live"), None)
    prev = next((v["version"] for v in d.versions if v["status"] == "retired"), None)
    by = {}
    for c in d.coefs:
        by.setdefault((c["model"], c["term"]), {})[int(c["version"])] = float(c["coef"])
    head = "".join(f"<th class='num'>v{v}{' · live' if v == live else ''}</th>" for v in shown)
    rows, last_model = [], None
    for (model, term), vals in by.items():
        if model != last_model:
            rows.append(f'<tr class="grp"><td colspan="{len(shown) + 2}">{html.escape(model)}</td></tr>')
            last_model = model
        cells = "".join(f"<td class='num'>{_f(vals.get(v), '{:+.3f}')}</td>" for v in shown)
        chg = ""
        if live in vals and prev in vals:
            dlt = vals[live] - vals[prev]
            chg = f"<span class='{'big' if abs(dlt) >= 0.05 else ''}'>{dlt:+.3f}</span>"
        rows.append(f"<tr><td>{html.escape(term)}</td>{cells}<td class='num'>{chg}</td></tr>")
    return (f"<div class='tbl'><table><thead><tr><th>Term</th>{head}<th class='num'>Live vs v{prev}</th></tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table></div>")


def render_html(d: Data) -> str:
    e = html.escape
    live = next((v for v in d.versions if v["status"] == "live"), None)
    lm = live["metrics"] if live else {}

    def kpi(stage):
        m = lm.get(stage, {})
        if not m:
            return f"<div class='kpi'><span class='k'>{STAGES[stage]}</span><span class='v'>–</span></div>"
        diff = m["brier_model"] - m["brier_price"]
        return (f"<div class='kpi'><span class='k'>{STAGES[stage]}</span>"
                f"<span class='v'>{m['brier_model']:.4f}</span>"
                f"<span class='s'>Brier vs {m['brier_price']:.4f} for the price ({diff:+.4f}) · k {m['k']:.3f} · "
                f"{m['markets']:,} markets over {m['months']} months</span></div>")

    vrows = "".join(
        f"<tr><td><b>v{v['version']}</b></td><td>{_pill(v['status'])}</td><td>{e(v['source'])}</td>"
        f"<td>{v['trained_through']}</td><td>{v['fitted']}</td><td>{v['promoted'] or '–'}</td><td>{v['retired'] or '–'}</td>"
        f"<td class='num'>{_f(v['metrics'].get('call_start', {}).get('brier_model'))}</td>"
        f"<td class='num'>{_f(v['metrics'].get('call_start', {}).get('brier_price'))}</td>"
        f"<td class='num'>{_f(v['metrics'].get('call_start', {}).get('k'), '{:.3f}')}</td>"
        f"<td class='num'>{_f(v['metrics'].get('early_24h', {}).get('k'), '{:.3f}')}</td>"
        f"<td class='note'>{e(v['notes'] or '')}</td></tr>" for v in d.versions)

    charts = []
    for stage, label in STAGES.items():
        rows = [r for r in d.monthly if r["stage"] == stage]
        tot = sum(int(float(r["trades"])) for r in rows)
        avg = (sum(float(r["pnl_c"] or 0) * int(float(r["trades"])) for r in rows) / tot) if tot else 0
        charts.append(f"<figure class='card'><figcaption><b>{label}</b><span>{avg:+.1f}¢ per trade over {tot:,} "
                      f"backtest trades</span></figcaption>{bars_svg(rows)}</figure>")
    calib = []
    for stage, label in STAGES.items():
        rows = [r for r in d.calibration if r["stage"] == stage]
        calib.append(f"<figure class='card small'><figcaption><b>{label}</b><span>predicted vs. said, %</span></figcaption>"
                     f"{calib_svg(rows)}</figure>")
    lv = d.live[0] if d.live else {}
    live_line = (f"{int(float(lv['trades'] or 0))} live trades since {lv['since']}"
                 + (f", {float(lv['pnl_c']):+.1f}¢ per trade" if lv.get("pnl_c") is not None else "")
                 + (f"; Brier {float(lv['brier_model']):.4f} vs {float(lv['brier_market']):.4f} for the market on "
                    f"{int(float(lv['graded']))} graded markets" if lv.get("brier_model") is not None else "")
                 ) if lv.get("since") else "No live trades graded yet."

    title = f"v{live['version']} is live" if live else "No live model"
    sub = (f"Trained through {live['trained_through']}, live since {live['promoted']}. {live_line}"
           if live else live_line)
    return TEMPLATE.format(title=e(title), sub=e(sub), kpis=kpi("call_start") + kpi("early_24h"), versions=vrows,
                           charts="".join(charts), calib="".join(calib), coefs=coef_table(d),
                           generated=f"{d.generated:%Y-%m-%d %H:%M} UTC")


def render_md(d: Data) -> str:
    out = ["# Models", "", f"_Generated {d.generated:%Y-%m-%d %H:%M} UTC from `kalshi.model_versions`. "
           "Promote with `select kalshi.promote_model(N);` (database owner only); promote the previous version to roll back._", "",
           "| Version | Status | Source | Trained through | Promoted | Call-start Brier | Price Brier | k (call start / 24h) |",
           "|---|---|---|---|---|--:|--:|--:|"]
    for v in d.versions:
        cs, ea = v["metrics"].get("call_start", {}), v["metrics"].get("early_24h", {})
        out.append(f"| v{v['version']} | {v['status']} | {v['source']} | {v['trained_through']} | {v['promoted'] or '–'} "
                   f"| {_f(cs.get('brier_model'))} | {_f(cs.get('brier_price'))} "
                   f"| {_f(cs.get('k'), '{:.3f}')} / {_f(ea.get('k'), '{:.3f}')} |")
    out.append("")
    return "\n".join(out)


TEMPLATE = """<title>Models</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@700;800&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
:root{{--bg:#f6f7f9;--surface:#fff;--fg:#17202b;--muted:#5b6675;--line:#dde2e8;--gain:#2a78d6;--loss:#e34948;
--ok:#1d7a4a;--ok-bg:#e4f3ea;--you:#6a3fb0;--you-bg:#f1ebfb;--warn:#a86a00;
--display:"Archivo","Helvetica Neue",Arial,sans-serif;--body:"IBM Plex Sans",system-ui,sans-serif;--mono:"IBM Plex Mono",ui-monospace,Menlo,monospace}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--bg:#0f141a;--surface:#161d26;--fg:#e6ebf1;--muted:#9aa6b4;--line:#2a3440;
--gain:#3987e5;--loss:#e66767;--ok:#5fcf91;--ok-bg:#15301f;--you:#b897f0;--you-bg:#2a1f40;--warn:#e6b04d;color-scheme:dark}}}}
:root[data-theme="dark"]{{--bg:#0f141a;--surface:#161d26;--fg:#e6ebf1;--muted:#9aa6b4;--line:#2a3440;
--gain:#3987e5;--loss:#e66767;--ok:#5fcf91;--ok-bg:#15301f;--you:#b897f0;--you-bg:#2a1f40;--warn:#e6b04d;color-scheme:dark}}
*{{box-sizing:border-box}}
body{{background:var(--bg);color:var(--fg);font-family:var(--body);font-size:14.5px;line-height:1.5}}
.wrap{{max-width:1120px;margin:0 auto;padding-block:28px 56px;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));display:flex;flex-direction:column;gap:30px}}
h1,h2{{font-family:var(--display);margin:0;text-wrap:balance}} h1{{font-size:clamp(26px,4vw,36px);font-weight:800}} h2{{font-size:19px}}
section{{display:flex;flex-direction:column;gap:12px}}
.sub,.meta{{color:var(--muted)}} .meta{{font-size:12.5px}}
.kpis{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}}
@media (max-width:760px){{.kpis{{grid-template-columns:1fr}}}}
.kpi{{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:14px 16px;display:flex;flex-direction:column;gap:2px}}
.kpi .k{{font-size:12.5px;color:var(--muted)}} .kpi .v{{font-family:var(--mono);font-size:26px;font-variant-numeric:tabular-nums}} .kpi .s{{font-size:13px;color:var(--muted)}}
.pill{{font-family:var(--mono);font-size:11px;padding:2px 8px;border-radius:999px;white-space:nowrap}}
.p-ok{{background:var(--ok-bg);color:var(--ok)}} .p-you{{background:var(--you-bg);color:var(--you)}} .p-n{{background:var(--bg);color:var(--muted)}}
.tbl{{overflow-x:auto;background:var(--surface);border:1px solid var(--line);border-radius:10px}}
table{{border-collapse:collapse;width:100%;min-width:760px;font-size:13.5px}}
th,td{{text-align:left;padding:8px 10px;border-bottom:1px solid var(--line);vertical-align:top}}
th{{font-family:var(--mono);font-size:11px;letter-spacing:.05em;text-transform:uppercase;color:var(--muted);font-weight:500;background:var(--bg);white-space:nowrap}}
.num{{text-align:right;font-family:var(--mono);font-variant-numeric:tabular-nums;white-space:nowrap}}
tr.grp td{{background:var(--bg);font-family:var(--mono);font-size:12px;color:var(--muted)}}
td.note{{color:var(--muted);font-size:12.5px;min-width:200px}}
.big{{color:var(--warn);font-weight:600}}
.grid2{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}}
.grid4{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr)) ;gap:14px}}
@media (max-width:760px){{.grid2,.grid4{{grid-template-columns:1fr}}}}
figure{{margin:0}}
.card{{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:12px 14px;display:flex;flex-direction:column;gap:6px;min-width:0}}
figcaption{{display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap;font-size:13.5px}} figcaption span{{color:var(--muted)}}
.chart{{width:100%;height:auto;display:block}} .calib{{max-width:260px}}
.chart .grid{{stroke:var(--line);stroke-width:1}} .chart .zero{{stroke:var(--muted);stroke-width:1}}
.chart .tick{{fill:var(--muted);font-family:var(--mono);font-size:10px}}
.chart .gain{{fill:var(--gain)}} .chart .loss{{fill:var(--loss)}} .chart .hit{{fill:transparent}}
.chart .bar:hover rect:not(.hit){{opacity:.8}}
.chart .diag{{stroke:var(--muted);stroke-dasharray:3 3;stroke-width:1}}
.chart .pt{{fill:var(--gain);stroke:var(--surface);stroke-width:2}}
.legend{{display:flex;gap:14px;font-size:12.5px;color:var(--muted)}} .legend i{{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:5px;vertical-align:-1px}}
code{{font-family:var(--mono);font-size:.9em}}
</style>
<div class="wrap">
<header style="display:flex;flex-direction:column;gap:6px">
  <div class="meta">Mentions models · generated {generated} from kalshi.model_versions</div>
  <h1>{title}</h1>
  <p class="sub" style="margin:0">{sub}</p>
</header>
<section><h2>Walk-forward backtest of the live model</h2><div class="kpis">{kpis}</div>
<p class="meta" style="margin:0">Each month scored by a model trained only on earlier months. Lower Brier is better; the price column is the market alone.</p></section>
<section><h2>Cents per trade by month</h2>
<div class="legend"><span><i style="background:var(--gain)"></i>made money</span><span><i style="background:var(--loss)"></i>lost money</span><span>Hover a bar for the month's trades.</span></div>
<div class="grid2">{charts}</div></section>
<section><h2>Calibration</h2><p class="meta" style="margin:0">Each dot is a 10¢ bucket of the model's probability. On the dashed line, a 30% prediction comes true 30% of the time.</p>
<div class="grid4">{calib}</div></section>
<section><h2>Versions</h2>
<div class="tbl"><table><thead><tr><th>Version</th><th>Status</th><th>Source</th><th>Trained through</th><th>Fitted</th><th>Promoted</th><th>Retired</th>
<th class="num">Brier</th><th class="num">Price</th><th class="num">k call start</th><th class="num">k 24h</th><th>Notes</th></tr></thead>
<tbody>{versions}</tbody></table></div>
<p class="meta" style="margin:0">Brier and price are call-start walk-forward figures. To switch: <code>select kalshi.promote_model(N);</code> (database owner). Promoting the previous version rolls back.</p></section>
<section><h2>Coefficients</h2><p class="meta" style="margin:0">Latest versions side by side. Changes of 0.05 or more are highlighted.</p>{coefs}</section>
</div>
"""
