"""The Models page: the latest release and whether it beats the live model, the release history,
what drives each model (strength and effect of every variable), the risk model, backtest charts,
and plain-English definitions of every variable.

    python -m rmm models --page     writes outputs/models/index.html and outputs/models/README.md

Read-only (rmm_ro is enough). The Sunday Model Review task republishes it after each weekly refit.
"""
from __future__ import annotations

import html
import json
import math
from dataclasses import dataclass
from datetime import datetime

import numpy as np
import pandas as pd

from . import db, review
from .variables import DEFS, MODELS, RISK_POINTS, label

STAGES = {"call_start": "At call start (after the release)", "early_24h": "24h before the call"}
e = html.escape


@dataclass
class Data:
    versions: list[dict]
    coefs: pd.DataFrame
    monthly: list[dict]
    calibration: list[dict]
    live_results: dict
    risk_perf: list[dict]
    risk: dict
    typical: dict
    generated: datetime


def load(now: datetime) -> Data:
    q = db.query
    versions = q("""select version, status, trained_through::text, fitted_at::date::text as fitted, source, metrics::text,
                           notes, promoted_at::date::text as promoted, retired_at::date::text as retired,
                           review::text, risk_rules::text
                    from kalshi.model_versions order by version desc""")
    for v in versions:
        for k in ("metrics", "review", "risk_rules"):
            v[k] = json.loads(v[k]) if v.get(k) else {}
    coefs = pd.DataFrame(q("""select version, model, term, coef::float, se::float, p_value::float, sd::float
                              from kalshi.model_version_coefficients"""))
    monthly = q("""select stage, month, count(*) filter (where action in ('TRADE', 'TRADE+')) as trades,
                          avg(pnl_c) filter (where action in ('TRADE', 'TRADE+')) as pnl_c
                   from kalshi.v_mentions_history where source = 'backtest' group by 1, 2 order by 1, 2""")
    calibration = q("""select stage, floor(least(model_c, 99.9) / 10) * 10 as bucket, count(*) as n,
                              avg(model_c) as predicted, 100 * avg((result = 'YES')::int) as actual
                       from kalshi.v_mentions_history
                       where source = 'backtest' and result in ('YES', 'NO') group by 1, 2 order by 1, 2""")
    live_results = q("""select count(*) filter (where action in ('TRADE', 'TRADE+')) as trades,
                               avg(pnl_c) filter (where action in ('TRADE', 'TRADE+')) as pnl_c,
                               count(*) filter (where result in ('YES', 'NO')) as graded,
                               avg(power(model_c / 100.0 - (result = 'YES')::int, 2)) filter (where result in ('YES', 'NO')) as brier_model,
                               avg(power((bid_c + ask_c) / 200.0 - (result = 'YES')::int, 2)) filter (where result in ('YES', 'NO')) as brier_market,
                               min(call_date)::text as since
                        from kalshi.v_mentions_history where source = 'live'""")[0]
    risk_perf = q("""select stage, action, coalesce(avoid_tier, 'none') as tier, count(*) as n, avg(pnl_c) as pnl_c
                     from kalshi.v_mentions_history where source = 'backtest' and side is not null
                     group by 1, 2, 3 order by 1, 2, 3""")
    train = review.training()
    typical = {}
    for t in DEFS:
        if t in train.columns and pd.api.types.is_numeric_dtype(train[t]):
            s = train[t].dropna()
            if len(s):
                typical[t] = (float(s.quantile(.1)), float(s.median()), float(s.quantile(.9)), float(s.mean()))
    return Data(versions, coefs, monthly, calibration, live_results, risk_perf, review.risk_rules(), typical, now)


# ---------------------------------------------------------------- small helpers

def _f(v, fmt="{:.4f}", dash="–"):
    return dash if v is None or (isinstance(v, float) and math.isnan(v)) else fmt.format(float(v))


def _pill(text: str, cls: str) -> str:
    return f'<span class="pill {cls}">{e(text)}</span>'


STATUS_CLS = {"live": "p-ok", "challenger": "p-you", "retired": "p-n"}
VERDICT_CLS = {"Better": "p-ok", "Worse": "p-bad", "No clear difference": "p-n", "Not enough evidence": "p-warn"}


def evidence(p) -> str:
    if p is None or (isinstance(p, float) and math.isnan(p)):
        return "–"
    return "very strong" if p < 0.001 else "strong" if p < 0.01 else "moderate" if p < 0.05 else "weak"


def plain_effect(term: str, coef: float, sd) -> str:
    d = DEFS.get(term)
    if d and d.binary:
        return f"odds ×{math.exp(coef):.2f} when 1"
    if sd is None or (isinstance(sd, float) and math.isnan(sd)):
        return "–"
    return f"odds ×{math.exp(coef * sd):.2f} per typical change ({sd:.2f})"


def std_effect(term: str, coef: float, sd) -> float:
    """Log-odds change for 0 -> 1 on a binary term, or for one standard deviation otherwise."""
    d = DEFS.get(term)
    if d and d.binary:
        return coef
    return coef * sd if sd is not None and not (isinstance(sd, float) and math.isnan(sd)) else float("nan")


# ---------------------------------------------------------------- charts (inline SVG)

def forest_svg(rows: list[dict]) -> str:
    """Effect of each term with a 95% interval, strongest first. Blue raises the odds of YES, red
    lowers them; grey rows are fill-ins (corrections for missing data, not findings)."""
    rows = [r for r in rows if not math.isnan(r["eff"])]
    if not rows:
        return ""
    lim = max(max(abs(r["eff"]) + 1.96 * r["se_eff"] for r in rows if not math.isnan(r["se_eff"])) if any(
        not math.isnan(r["se_eff"]) for r in rows) else 0, max(abs(r["eff"]) for r in rows), 0.5) * 1.05
    W, LBL, R, rh, top = 640, 210, 16, 22, 22
    H = top + rh * len(rows) + 22
    x = lambda v: LBL + (v + lim) / (2 * lim) * (W - LBL - R)
    out = [f'<svg viewBox="0 0 {W} {H}" class="chart forest" role="img" aria-label="Variable effects">']
    for t in sorted({-round(lim, 1), -round(lim / 2, 1), 0.0, round(lim / 2, 1), round(lim, 1)}):
        out.append(f'<line x1="{x(t):.1f}" x2="{x(t):.1f}" y1="{top - 6}" y2="{H - 20}" class="{"zero" if t == 0 else "grid"}"/>'
                   f'<text x="{x(t):.1f}" y="{H - 6}" class="tick" text-anchor="middle">{t:+.1f}</text>')
    out.append(f'<text x="{x(-lim):.1f}" y="12" class="tick">← lowers the odds of YES</text>'
               f'<text x="{x(lim):.1f}" y="12" class="tick" text-anchor="end">raises the odds →</text>')
    for i, r in enumerate(rows):
        y = top + i * rh + rh / 2
        cls = "fill" if r["kind"] == "fill-in" else ("gain" if r["eff"] >= 0 else "loss")
        lo, hi = r["eff"] - 1.96 * r["se_eff"], r["eff"] + 1.96 * r["se_eff"]
        tip = f"{r['label']}: {r['plain']}; evidence {r['evidence']} (p = {_f(r['p'], '{:.2g}')})"
        out.append(f'<g class="row"><title>{e(tip)}</title>'
                   f'<rect x="0" y="{y - rh / 2:.1f}" width="{W}" height="{rh}" class="hit"/>'
                   f'<text x="{LBL - 8}" y="{y + 4:.1f}" class="lbl" text-anchor="end">{e(r["label"][:30])}</text>')
        if not math.isnan(r["se_eff"]):
            out.append(f'<line x1="{x(max(lo, -lim)):.1f}" x2="{x(min(hi, lim)):.1f}" y1="{y:.1f}" y2="{y:.1f}" class="ci {cls}"/>')
        out.append(f'<circle cx="{x(r["eff"]):.1f}" cy="{y:.1f}" r="4.5" class="pt {cls}"/></g>')
    out.append("</svg>")
    return "".join(out)


def bars_svg(rows: list[dict]) -> str:
    W, H, L, R, T, B = 560, 200, 44, 8, 12, 28
    vals = [float(r["pnl_c"]) if r["pnl_c"] is not None else 0.0 for r in rows]
    top = max(5.0, max(vals + [0])) * 1.15
    bot = min(0.0, min(vals + [0])) * 1.15
    y = lambda v: T + (top - v) / (top - bot) * (H - T - B)
    n = len(rows)
    step = (W - L - R) / max(n, 1)
    bw = min(28.0, step * 0.62)
    out = [f'<svg viewBox="0 0 {W} {H}" class="chart" role="img" aria-label="Cents per trade by month">']
    for t in [t for t in range(int(bot // 5) * 5, int(top) + 1, 5) if bot <= t <= top]:
        out.append(f'<line x1="{L}" x2="{W - R}" y1="{y(t):.1f}" y2="{y(t):.1f}" class="{"zero" if t == 0 else "grid"}"/>'
                   f'<text x="{L - 6}" y="{y(t) + 4:.1f}" class="tick" text-anchor="end">{t:+d}¢</text>')
    for i, (r, v) in enumerate(zip(rows, vals)):
        x = L + i * step + (step - bw) / 2
        y0, y1 = y(0), y(v)
        tip = f"{r['month']}: {v:+.1f}¢ per trade on {int(float(r['trades']))} trades"
        out.append(f'<g class="bar"><title>{e(tip)}</title><rect x="{x - (step - bw) / 2:.1f}" y="{T}" width="{step:.1f}" '
                   f'height="{H - T - B}" class="hit"/><rect x="{x:.1f}" y="{min(y0, y1):.1f}" width="{bw:.1f}" '
                   f'height="{max(abs(y1 - y0), 1.0):.1f}" rx="2" class="{"gain" if v >= 0 else "loss"}"/></g>')
        if i % 2 == 0 or i == n - 1:
            out.append(f'<text x="{x + bw / 2:.1f}" y="{H - 8}" class="tick" text-anchor="middle">{r["month"][2:]}</text>')
    out.append("</svg>")
    return "".join(out)


def calib_svg(rows: list[dict]) -> str:
    S, L, B, T, R = 220, 34, 26, 8, 8
    px = lambda v: L + v / 100 * (S - L - R)
    py = lambda v: T + (100 - v) / 100 * (S - T - B)
    out = [f'<svg viewBox="0 0 {S} {S}" class="chart calib" role="img" aria-label="Calibration">',
           f'<line x1="{px(0)}" y1="{py(0)}" x2="{px(100)}" y2="{py(100)}" class="diag"/>']
    for t in (0, 50, 100):
        out.append(f'<text x="{px(t):.1f}" y="{S - 8}" class="tick" text-anchor="middle">{t}</text>'
                   f'<text x="{L - 5}" y="{py(t) + 4:.1f}" class="tick" text-anchor="end">{t}</text>')
    for r in rows:
        p, a, n = float(r["predicted"]), float(r["actual"]), int(float(r["n"]))
        out.append(f'<g class="dot"><title>model said {p:.0f}%, said {a:.0f}% of the time ({n} markets)</title>'
                   f'<circle cx="{px(p):.1f}" cy="{py(a):.1f}" r="9" class="hit"/>'
                   f'<circle cx="{px(p):.1f}" cy="{py(a):.1f}" r="4.5" class="pt gain"/></g>')
    out.append("</svg>")
    return "".join(out)


# ---------------------------------------------------------------- sections

def release_card(v: dict, versions: list[dict]) -> str:
    r = v.get("review") or {}
    head = (f"<div class='rel-h'><h3>v{v['version']}</h3>{_pill(v['status'], STATUS_CLS[v['status']])}"
            + (f"{_pill(r['verdict'], VERDICT_CLS.get(r['verdict'], 'p-n'))} <span class='meta'>vs v{r['against']}</span>" if r else "")
            + f"<span class='meta'>{e(v['source'])} · trained through {v['trained_through']} · fitted {v['fitted']}"
            + (f" · live {v['promoted']}" if v.get("promoted") else "")
            + (f" → retired {v['retired']}" if v.get("retired") else "") + "</span></div>")
    if not r:
        return (f"<div class='card rel'>{head}<p class='note'>{e(v.get('notes') or '')} "
                "No review: this is the first version on record.</p></div>")
    rows = []
    for stage, st in r["stages"].items():
        for which, name in (("forward", "Forward test"), ("walk_forward", "Walk-forward")):
            x = st.get(which) or {}
            if not x.get("markets"):
                continue
            c = lambda val: "–" if val is None else f"{val:+.1f}¢"
            better = x["diff"] < 0
            rows.append(f"<tr><td>{STAGES[stage]}</td><td>{name}</td><td class='num'>{x['markets']:,}</td>"
                        f"<td class='num'>{x['brier_price']:.4f}</td><td class='num'>{x['brier_old']:.4f}</td>"
                        f"<td class='num'><b>{x['brier_new']:.4f}</b></td>"
                        f"<td class='num {'good' if better else 'bad'}'>{x['diff']:+.4f}</td>"
                        f"<td class='num'>{x['share_better']:.0%}</td>"
                        f"<td class='num'>{c(x['cents_old'])} <span class='meta'>({x['trades_old']})</span></td>"
                        f"<td class='num'><b>{c(x['cents_new'])}</b> <span class='meta'>({x['trades_new']})</span></td></tr>")
    movers = "".join(
        f"<li><b>{e(m['label'])}</b> <span class='meta'>({e(m['model'])})</span>: "
        f"{_f(m['old'], '{:+.3f}')} → {_f(m['new'], '{:+.3f}')}</li>" for m in r.get("movers", [])[:6])
    spec = ("Same variables as v%d; differences come from the data." % r["against"]
            if not r.get("terms_added") and not r.get("terms_removed") else
            f"Added: {', '.join(r.get('terms_added') or ['none'])}. Removed: {', '.join(r.get('terms_removed') or ['none'])}.")
    prev_risk = next((x.get("risk_rules", {}).get("hash") for x in versions if x["version"] == r["against"]), None)
    risk = (f"Risk model: {v.get('risk_rules', {}).get('rules', '?')} avoid-point rules"
            + (" (unchanged)" if prev_risk in (None, r.get("risk_rules_hash")) else " (changed since v%d)" % r["against"]))
    return f"""<div class='card rel'>{head}
<p class='verdict'>{e(r['reason'])}</p>
<p class='meta'>{r['new_markets']:,} settled markets since v{r['against']}'s data ended ({r['against_trained_through']}). {e(spec)} {e(risk)}.</p>
<div class='tbl'><table><thead><tr><th>Entry point</th><th>Test</th><th class='num'>Markets</th><th class='num'>Price</th>
<th class='num'>v{r['against']}</th><th class='num'>v{r['version']}</th><th class='num'>Change</th><th class='num'>Better in</th>
<th class='num'>v{r['against']} ¢/trade</th><th class='num'>v{r['version']} ¢/trade</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<div class='cols'><div><h4>Biggest coefficient changes</h4><ul>{movers}</ul></div>
<div><h4>Notes</h4><p class='note'>{e(v.get('notes') or '–')}</p></div></div></div>"""


def drivers(d: Data, version: int, prev: int | None) -> str:
    co = d.coefs[d.coefs["version"] == version]
    pv = d.coefs[d.coefs["version"] == prev].set_index(["model", "term"])["coef"] if prev else pd.Series(dtype=float)
    out = []
    for model, desc in MODELS.items():
        m = co[(co["model"] == model) & ~co["term"].isin(["(Intercept)", "calibration_k"])]
        rows = []
        for _, x in m.iterrows():
            t = x["term"]
            sd = None if pd.isna(x["sd"]) else float(x["sd"])
            eff = std_effect(t, x["coef"], sd)
            scale = 1.0 if (DEFS.get(t) and DEFS[t].binary) else (sd or float("nan"))
            se_eff = float(x["se"]) * scale if not pd.isna(x["se"]) else float("nan")
            p = None if pd.isna(x["p_value"]) else float(x["p_value"])
            old = pv.get((model, t))
            rows.append({"term": t, "label": label(t), "eff": eff, "se_eff": se_eff, "p": p, "coef": float(x["coef"]),
                         "kind": DEFS[t].kind if t in DEFS else "predictor", "plain": plain_effect(t, float(x["coef"]), sd),
                         "evidence": evidence(p), "chg": None if old is None or pd.isna(old) else float(x["coef"]) - float(old)})
        rows.sort(key=lambda r: -abs(r["eff"]) if not math.isnan(r["eff"]) else 0)
        k = co[(co["model"] == model) & (co["term"] == "calibration_k")]["coef"]
        trs = "".join(
            f"<tr><td><b>{e(r['label'])}</b> <span class='meta'>{e(r['term'])}</span>"
            + (" <span class='pill p-n'>fill-in</span>" if r["kind"] == "fill-in" else "") + "</td>"
            f"<td>{e(r['plain'])}</td><td>{r['evidence']}</td><td class='num'>{_f(r['p'], '{:.2g}')}</td>"
            f"<td class='num'>{r['coef']:+.3f}</td><td class='num'>{_f(r['chg'], '{:+.3f}')}</td></tr>" for r in rows)
        has_se = any(not math.isnan(r["se_eff"]) for r in rows)
        out.append(f"""<details class='card' {'open' if model in ('combined', 'fundamental') else ''}><summary><b>{e(desc)}</b>
{f"<span class='meta'>k = {float(k.iloc[0]):.3f}</span>" if len(k) else ''}</summary>
{forest_svg(rows) if has_se else "<p class='meta'>No standard errors stored for this version.</p>"}
<div class='tbl'><table><thead><tr><th>Variable</th><th>Effect</th><th>Evidence</th><th class='num'>p</th><th class='num'>Coef</th>
<th class='num'>vs v{prev or '–'}</th></tr></thead><tbody>{trs}</tbody></table></div></details>""")
    return "".join(out)


def risk_section(d: Data) -> str:
    perf = []
    for stage, name in STAGES.items():
        rows = [r for r in d.risk_perf if r["stage"] == stage]
        def agg(f):
            sel = [r for r in rows if f(r)]
            n = sum(int(float(r["n"])) for r in sel)
            c = sum(float(r["pnl_c"] or 0) * int(float(r["n"])) for r in sel) / n if n else None
            return n, c
        groups = [("TRADE+: fading an AVOID favorite (1.5× stake)", lambda r: r["action"] == "TRADE+"),
                  ("TRADE: model edge, risk model neutral", lambda r: r["action"] == "TRADE"),
                  ("Skipped: buying an AVOID favorite (conflict)", lambda r: r["action"] == "SKIP" and r["tier"] == "AVOID"),
                  ("Skipped: other rules", lambda r: r["action"] == "SKIP" and r["tier"] != "AVOID")]
        for gname, f in groups:
            n, c = agg(f)
            good = (c or 0) < 0 if gname.startswith("Skipped") else (c or 0) > 0   # a skip is good when the trade would have lost
            perf.append(f"<tr><td>{name}</td><td>{e(gname)}</td><td class='num'>{n:,}</td>"
                        f"<td class='num {'good' if good else 'bad'}'>{_f(c, '{:+.1f}¢')}</td></tr>")
    tests = {(t["side"], t["point"], int(t["zone_lo"])): t for t in d.risk["tests"]}
    rules = {(r["side"], r["point"], int(r["zone_lo"])) for r in d.risk["items"]}
    zones = [50, 60, 70, 80, 90]
    mats = []
    for side in ("YES", "NO"):
        pts = sorted({p for s, p, z in tests if s == side} | {p for s, p, z in rules if s == side})
        trs = []
        for p in pts:
            cells = []
            for z in zones:
                t = tests.get((side, p, z))
                on = (side, p, z) in rules
                if not t:
                    cells.append("<td class='num cell'>–</td>")
                    continue
                tip = (f"{side} favorite {z}–{z + 9}¢, {RISK_POINTS.get(p, p)}: {float(t['all_']):+.1f} extra losses per 100 "
                       f"(early {float(t['early']):+.1f}, late {float(t['late']):+.1f}) on {t['markets_with']} markets"
                       + ("; counts as an avoid point" if on else "; doesn't count (not in both periods or too few markets)"))
                cells.append(f"<td class='num cell {'on' if on else ''}' title='{e(tip)}'>{float(t['all_']):+.0f}</td>")
            trs.append(f"<tr><td>{e(RISK_POINTS.get(p, p))} <span class='meta'>{e(p)}</span></td>{''.join(cells)}</tr>")
        mats.append(f"<div class='card'><h4>When the favorite is {side}</h4><div class='tbl'><table class='risk'><thead><tr><th>Marker</th>"
                    + "".join(f"<th class='num'>{z}–{z + 9}¢</th>" for z in zones)
                    + f"</tr></thead><tbody>{''.join(trs)}</tbody></table></div></div>")
    return f"""<p class='meta' style='margin:0'>The risk model flags favorites (50–98¢) that have lost more often than their price says.
Each marker earns an avoid point only in the price ranges where it cost 4+ extra losses per 100, in both periods, on 30+ markets.
Enough points make a favorite AVOID. Fading an AVOID favorite is TRADE+ (1.5× stake); buying one is skipped.
It is a rule set, not a fitted model, so it isn't refit weekly; each release records which rule set it was reviewed with
({d.risk['rules']} rules now, id {d.risk['hash']}).</p>
<div class='card'><h4>What the risk model adds, in the live model's backtest</h4><div class='tbl'><table><thead><tr><th>Entry point</th><th>Group</th>
<th class='num'>Markets</th><th class='num'>¢ per trade</th></tr></thead><tbody>{''.join(perf)}</tbody></table></div>
<p class='meta'>Skipped rows show what those trades would have made; green means skipping them saved money.</p></div>
<p class='meta' style='margin:0'>Extra losses per 100 markets for each marker and price range. Shaded cells count as avoid points. Hover for both periods.</p>
{''.join(mats)}"""


def definitions(d: Data) -> str:
    groups = {"Fundamental model (our data)": [t for t in DEFS if t not in ("lp", "lp24", "lA", "move24", "has24", "(Intercept)", "calibration_k")],
              "Combined model (price + fundamentals)": ["lp", "lp24", "lA", "move24", "has24", "calibration_k", "(Intercept)"]}
    out = []
    for g, terms in groups.items():
        trs = []
        for t in terms:
            v = DEFS[t]
            ty = d.typical.get(t)
            typ = ("share 1: " + f"{ty[3]:.0%}") if (ty and v.binary) else (f"{ty[0]:.2f} · {ty[1]:.2f} · {ty[2]:.2f}" if ty else "–")
            trs.append(f"<tr><td><b>{e(v.label)}</b><div class='meta'>{e(t)}</div></td><td>{e(v.meaning)}</td><td>{e(v.values)}</td>"
                       f"<td class='num'>{e(typ)}</td><td>{e(v.source)}</td><td>{e(v.kind)}</td></tr>")
        out.append(f"<h4>{e(g)}</h4><div class='tbl'><table class='defs'><thead><tr><th>Variable</th><th>What it measures</th>"
                   f"<th>Values</th><th class='num'>Typical (10% · median · 90%)</th><th>Source</th><th>Kind</th></tr></thead>"
                   f"<tbody>{''.join(trs)}</tbody></table></div>")
    return "".join(out)


def render_html(d: Data) -> str:
    live = next((v for v in d.versions if v["status"] == "live"), None)
    newest = d.versions[0] if d.versions else None
    prev_live = next((v["version"] for v in d.versions if v["status"] == "retired"), None)
    lr = d.live_results
    live_line = (f"Live so far: {int(float(lr['trades'] or 0))} trades since {lr['since']}"
                 + (f", {float(lr['pnl_c']):+.1f}¢ per trade" if lr.get("pnl_c") is not None else "")
                 + (f"; Brier {float(lr['brier_model']):.4f} vs {float(lr['brier_market']):.4f} for the market on "
                    f"{int(float(lr['graded']))} graded markets" if lr.get("brier_model") is not None else "")) if lr.get("since") else ""
    charts = []
    for stage, name in STAGES.items():
        rows = [r for r in d.monthly if r["stage"] == stage]
        tot = sum(int(float(r["trades"])) for r in rows)
        avg = (sum(float(r["pnl_c"] or 0) * int(float(r["trades"])) for r in rows) / tot) if tot else 0
        charts.append(f"<figure class='card'><figcaption><b>{name}</b><span>{avg:+.1f}¢ per trade over {tot:,} backtest trades"
                      f"</span></figcaption>{bars_svg(rows)}</figure>")
    calib = "".join(f"<figure class='card'><figcaption><b>{name}</b><span>predicted vs. said, %</span></figcaption>"
                    f"{calib_svg([r for r in d.calibration if r['stage'] == stage])}</figure>" for stage, name in STAGES.items())
    latest = release_card(newest, d.versions) if newest else ""
    history = "".join(release_card(v, d.versions) for v in d.versions[1:])
    title = f"v{live['version']} is live" if live else "No live model"
    sub = f"Trained through {live['trained_through']}, live since {live['promoted']}. {live_line}" if live else live_line
    cand = (f"Latest release: v{newest['version']} ({newest['status']})"
            + (f" · {newest['review']['verdict']}" if newest and newest.get("review") else "")) if newest else ""
    return TEMPLATE.format(title=e(title), sub=e(sub), cand=e(cand), latest=latest, history=history or "<p class='meta'>No earlier versions.</p>",
                           drivers=drivers(d, live["version"], prev_live) if live else "", risk=risk_section(d),
                           charts="".join(charts), calib=calib, defs=definitions(d),
                           generated=f"{d.generated:%Y-%m-%d %H:%M} UTC")


def render_md(d: Data) -> str:
    out = ["# Models", "", f"_Generated {d.generated:%Y-%m-%d %H:%M} UTC from `kalshi.model_versions`. "
           "Promote with `select kalshi.promote_model(N);` (database owner only); promote the previous version to roll back._", "",
           "## Release history", ""]
    for v in d.versions:
        r = v.get("review") or {}
        out.append(f"### v{v['version']} · {v['status']} · trained through {v['trained_through']}"
                   + (f" · live {v['promoted']}" if v.get("promoted") else "") + (f" → retired {v['retired']}" if v.get("retired") else ""))
        out.append("")
        if r:
            out.append(f"**{r['verdict']} vs v{r['against']}.** {r['reason']}")
            out.append("")
            out.append("| Entry point | Test | Markets | Price | Old | New | Better in | Old ¢/trade | New ¢/trade |")
            out.append("|---|---|--:|--:|--:|--:|--:|--:|--:|")
            for stage, st in r["stages"].items():
                for which in ("forward", "walk_forward"):
                    x = st.get(which) or {}
                    if x.get("markets"):
                        out.append(f"| {stage} | {which} | {x['markets']} | {x['brier_price']:.4f} | {x['brier_old']:.4f} | "
                                   f"{x['brier_new']:.4f} | {x['share_better']:.0%} | {_f(x['cents_old'], '{:+.1f}')} | "
                                   f"{_f(x['cents_new'], '{:+.1f}')} |")
            out.append("")
        if v.get("notes"):
            out += [v["notes"], ""]
    return "\n".join(out)


TEMPLATE = """<title>Models</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@700;800&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
:root{{--bg:#f6f7f9;--surface:#fff;--fg:#17202b;--muted:#5b6675;--line:#dde2e8;--gain:#2a78d6;--loss:#e34948;--fillc:#9aa3ad;
--ok:#1d7a4a;--ok-bg:#e4f3ea;--you:#6a3fb0;--you-bg:#f1ebfb;--warn:#a86a00;--warn-bg:#fbf1dc;--bad:#b3261e;--bad-bg:#fbe5e3;--shade:#fde7d7;
--display:"Archivo","Helvetica Neue",Arial,sans-serif;--body:"IBM Plex Sans",system-ui,sans-serif;--mono:"IBM Plex Mono",ui-monospace,Menlo,monospace}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--bg:#0f141a;--surface:#161d26;--fg:#e6ebf1;--muted:#9aa6b4;--line:#2a3440;
--gain:#3987e5;--loss:#e66767;--fillc:#6b7480;--ok:#5fcf91;--ok-bg:#15301f;--you:#b897f0;--you-bg:#2a1f40;--warn:#e6b04d;--warn-bg:#352812;--bad:#f08079;--bad-bg:#3a1714;--shade:#3a2416;color-scheme:dark}}}}
:root[data-theme="dark"]{{--bg:#0f141a;--surface:#161d26;--fg:#e6ebf1;--muted:#9aa6b4;--line:#2a3440;
--gain:#3987e5;--loss:#e66767;--fillc:#6b7480;--ok:#5fcf91;--ok-bg:#15301f;--you:#b897f0;--you-bg:#2a1f40;--warn:#e6b04d;--warn-bg:#352812;--bad:#f08079;--bad-bg:#3a1714;--shade:#3a2416;color-scheme:dark}}
*{{box-sizing:border-box}}
body{{background:var(--bg);color:var(--fg);font-family:var(--body);font-size:14.5px;line-height:1.5}}
.wrap{{max-width:1120px;margin:0 auto;padding-block:28px 56px;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));display:flex;flex-direction:column;gap:32px}}
h1,h2,h3,h4{{font-family:var(--display);margin:0;text-wrap:balance}} h1{{font-size:clamp(26px,4vw,36px);font-weight:800}} h2{{font-size:20px}} h3{{font-size:18px}} h4{{font-size:14.5px;margin-bottom:6px}}
section{{display:flex;flex-direction:column;gap:12px}}
.sub{{color:var(--muted);margin:0}} .meta{{font-size:12.5px;color:var(--muted)}} .note{{font-size:13.5px;margin:0}}
nav{{display:flex;flex-wrap:wrap;gap:6px 14px;font-size:13px}} nav a{{color:var(--muted)}}
.pill{{font-family:var(--mono);font-size:11px;padding:2px 8px;border-radius:999px;white-space:nowrap;display:inline-block}}
.p-ok{{background:var(--ok-bg);color:var(--ok)}} .p-you{{background:var(--you-bg);color:var(--you)}} .p-n{{background:var(--bg);color:var(--muted);border:1px solid var(--line)}}
.p-warn{{background:var(--warn-bg);color:var(--warn)}} .p-bad{{background:var(--bad-bg);color:var(--bad)}}
.card{{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:14px 16px;display:flex;flex-direction:column;gap:10px;min-width:0}}
.rel-h{{display:flex;flex-wrap:wrap;align-items:center;gap:8px 10px}}
.verdict{{font-size:15px;margin:0}}
.cols{{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:16px}} .cols ul{{margin:0;padding-left:18px;font-size:13.5px}}
@media (max-width:760px){{.cols{{grid-template-columns:1fr}}}}
.tbl{{overflow-x:auto;border:1px solid var(--line);border-radius:8px;background:var(--surface)}}
table{{border-collapse:collapse;width:100%;min-width:720px;font-size:13.5px}}
th,td{{text-align:left;padding:7px 10px;border-bottom:1px solid var(--line);vertical-align:top}}
th{{font-family:var(--mono);font-size:11px;letter-spacing:.05em;text-transform:uppercase;color:var(--muted);font-weight:500;background:var(--bg);white-space:nowrap}}
tr:last-child td{{border-bottom:0}}
.num{{text-align:right;font-family:var(--mono);font-variant-numeric:tabular-nums;white-space:nowrap}}
.good{{color:var(--ok)}} .bad{{color:var(--bad)}}
table.risk td.cell{{min-width:56px}} table.risk td.on{{background:var(--shade);font-weight:600}}
table.defs td:nth-child(2){{min-width:280px}}
details summary{{cursor:pointer;display:flex;flex-wrap:wrap;gap:6px 12px;align-items:baseline}}
.grid2{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}}
@media (max-width:760px){{.grid2{{grid-template-columns:1fr}}}}
figure{{margin:0}} figcaption{{display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap;font-size:13.5px}} figcaption span{{color:var(--muted)}}
.chart{{width:100%;height:auto;display:block}} .calib{{max-width:260px}} .forest{{max-width:680px}}
.chart .grid{{stroke:var(--line);stroke-width:1}} .chart .zero{{stroke:var(--muted);stroke-width:1}}
.chart .tick{{fill:var(--muted);font-family:var(--mono);font-size:10px}} .chart .lbl{{fill:var(--fg);font-size:11.5px;font-family:var(--body)}}
.chart .gain{{fill:var(--gain);stroke:var(--gain)}} .chart .loss{{fill:var(--loss);stroke:var(--loss)}} .chart .fill{{fill:var(--fillc);stroke:var(--fillc)}}
.chart .hit{{fill:transparent;stroke:none}} .chart .ci{{stroke-width:2;fill:none}} .chart .pt{{stroke:var(--surface);stroke-width:2}}
.chart .row:hover .hit{{fill:var(--bg)}} .chart .bar:hover rect:not(.hit){{opacity:.8}}
.chart .diag{{stroke:var(--muted);stroke-dasharray:3 3;stroke-width:1}}
.legend{{display:flex;flex-wrap:wrap;gap:14px;font-size:12.5px;color:var(--muted)}} .legend i{{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:5px;vertical-align:-1px}}
code{{font-family:var(--mono);font-size:.9em}}
</style>
<div class="wrap">
<header style="display:flex;flex-direction:column;gap:8px">
  <div class="meta">Mentions models · generated {generated} from kalshi.model_versions</div>
  <h1>{title}</h1>
  <p class="sub">{sub}</p>
  <p class="sub"><b>{cand}</b></p>
  <nav><a href="#latest">Latest release</a><a href="#history">Release history</a><a href="#drivers">What drives the model</a>
  <a href="#risk">Risk model</a><a href="#backtest">Backtest</a><a href="#definitions">Definitions</a></nav>
</header>
<section id="latest"><h2>Latest release: is it better?</h2>
<p class="meta" style="margin:0"><b>Forward test</b>: markets settled after the older version's data ended. The older version is scored with its frozen coefficients (what the board traded); the newer one with walk-forward predictions. <b>Walk-forward</b>: both versions' month-by-month backtests on the markets both cover. Brier: lower is better; <b>Price</b> is the market alone, the bar to beat. <b>Better in</b>: share of 1,000 call-level resamples where the newer version wins. ¢/trade: trading at the real quote after fees (trades in brackets).</p>
{latest}</section>
<section id="history"><h2>Release history</h2>{history}</section>
<section id="drivers"><h2>What drives the live model</h2>
<p class="meta" style="margin:0">Each dot is a variable's effect on the log-odds of YES: for a yes/no variable, switching it from 0 to 1; for a number, one typical change (its standard deviation). Lines are 95% intervals; a line crossing zero means the data can't tell the effect from nothing. Grey rows are fill-ins that only correct for missing data. Hover a row for the plain-English effect.</p>
<div class="legend"><span><i style="background:var(--gain)"></i>raises the odds of YES</span><span><i style="background:var(--loss)"></i>lowers them</span><span><i style="background:var(--fillc)"></i>fill-in</span></div>
{drivers}</section>
<section id="risk"><h2>Risk model</h2>{risk}</section>
<section id="backtest"><h2>Backtest of the live model</h2>
<div class="legend"><span><i style="background:var(--gain)"></i>month made money</span><span><i style="background:var(--loss)"></i>month lost money</span></div>
<div class="grid2">{charts}</div>
<p class="meta" style="margin:0">Calibration: each dot is a 10¢ bucket of the model's probability. On the dashed line, a 30% prediction comes true 30% of the time.</p>
<div class="grid2">{calib}</div></section>
<section id="definitions"><h2>Definitions</h2>
<p class="meta" style="margin:0">Typical values are from the training data: 10th percentile, median, 90th percentile (for yes/no variables, the share that are 1). Log-odds: 0 = 50%, ±1.1 ≈ 25% / 75%, ±2.2 ≈ 10% / 90%.</p>
{defs}</section>
</div>
"""
