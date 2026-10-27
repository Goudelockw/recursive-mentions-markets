"""Daily trade sheet: today's and tomorrow's TRADE / TRADE+ rows from kalshi.v_mentions_board,
where each one sits in the risk model, the skips worth knowing about, and the data checks
behind them. Pure formatting: every number comes from the board; nothing is re-modelled here.
"""
from __future__ import annotations

import csv
import html
import io
from dataclasses import dataclass, field
from datetime import date, datetime

PER_CALL_CAP_PCT = 6.0
CAP_TOLERANCE_PCT = 0.05   # board stakes are rounded; ignore overages smaller than this
MAX_QUOTE_AGE_H = 3.0
PRICE_BANDS = [(90, 98), (80, 89), (70, 79), (60, 69), (50, 59)]
POINT_COLS = ["0", "1", "2", "3", "4+"]


@dataclass
class Line:
    row: dict
    issues: list[str]
    risk: str        # Aligned | Conflict | Neutral | No read
    risk_note: str

    def __getitem__(self, k):
        return self.row[k]

    @property
    def cost_c(self) -> float | None:
        """What one contract costs on the side the board says to buy."""
        r = self.row
        if r["side"] == "NO" and r["yes_bid_c"] is not None:
            return 100 - r["yes_bid_c"]
        if r["side"] == "YES":
            return r["yes_ask_c"]
        return None

    @property
    def spread_c(self) -> float | None:
        r = self.row
        if r["yes_bid_c"] is None or r["yes_ask_c"] is None:
            return None
        return r["yes_ask_c"] - r["yes_bid_c"]


@dataclass
class Call:
    symbol: str
    event_ticker: str
    call_date: date
    call_time_et: str
    source: str
    verified: bool
    phase: str
    markets: int
    trades: list[Line] = field(default_factory=list)

    @property
    def stake_pct(self) -> float:
        return round(sum(t["stake_pct"] or 0 for t in self.trades), 2)

    @property
    def window(self) -> str:
        p = self.phase.lower()
        if p.startswith("entry 1"):
            return "ENTRY 1: place now"
        if p.startswith("entry 2"):
            return "ENTRY 2: release is out, re-check and place within caps"
        if p.startswith("hold"):
            return "Dead zone: hold, don't add"
        if p.startswith("upcoming"):
            return "Upcoming: Entry 1 opens 30h before the call"
        return self.phase


@dataclass
class Check:
    name: str
    ok: bool
    text: str


@dataclass
class Sheet:
    day: date
    generated_at: datetime
    status: str      # READY | CHECK | STOP
    headline: str
    checks: list[Check]
    calls: list[Call]
    skips: list[Line]
    check_dates: list[dict]
    data_issues: list[Line]

    @property
    def trades(self) -> list[Line]:
        return [t for c in self.calls for t in c.trades]


# ---------------------------------------------------------------- classification

def data_issues(r: dict) -> list[str]:
    out = []
    if r.get("no_hist"):
        out.append("no transcript history")
    if r.get("no_fund_score"):
        out.append("no fundamental score")
    if r.get("quote_age_h") is not None and r["quote_age_h"] > MAX_QUOTE_AGE_H:
        out.append(f"quote {r['quote_age_h']:.0f}h old")
    if r.get("has_valence") is False:
        out.append("no valence label")
    if r.get("has_incentive") is False:
        out.append("no incentive label")
    return out


def risk_read(r: dict) -> tuple[str, str]:
    reason = r.get("reason") or ""
    pts = r.get("avoid_points")
    if r["action"] == "TRADE+":
        return "Aligned", f"fading an AVOID favorite ({_pts(pts)})"
    if r["action"] == "SKIP":
        if "AVOID favorite" in reason or "avoid points" in reason:
            return "Conflict", reason
        return "Rule skip", reason
    if r.get("avoid_tier") == "Thin history":
        return "No read", "thin history in this price range"
    if r.get("side") and r["side"] == r.get("fav_side"):
        return "Neutral", f"backing the favorite ({_pts(pts)})"
    return "Neutral", f"fading the favorite ({_pts(pts)})"


def _pts(n) -> str:
    return f"{n} pt" if n == 1 else f"{n} pts"


def _day(v) -> date:
    if isinstance(v, date):
        return v
    return date.fromisoformat(str(v)[:10])


def _sort_key(call_date: date, call_time_et: str) -> datetime:
    try:
        t = datetime.strptime(call_time_et.split(" ", 3)[3], "%I:%M %p").time()
    except (IndexError, ValueError):
        t = datetime.min.time()
    return datetime.combine(call_date, t)


def preflight_checks(rows: list[dict]) -> list[Check]:
    out = []
    for r in rows:
        name, h, max_h = r["check_name"], r.get("hours_since_ok"), r["max_hours"]
        label = name.split(":", 1)[-1]
        if name.startswith("model:"):
            continue
        if h is None:
            out.append(Check(label, False, f"{label}: no successful run in 7 days"))
        elif r.get("failed_24h") and name.startswith("job:"):
            out.append(Check(label, h <= max_h, f"{label}: last ok {h:.1f}h ago, a run failed in the last 24h"))
        else:
            out.append(Check(label, h <= max_h, f"{label}: {h:.1f}h ago"))
    models = [r for r in rows if r["check_name"].startswith("model:")]
    if models:
        h = max(r["hours_since_ok"] or 0 for r in models)
        out.append(Check("model", h <= models[0]["max_hours"], f"model fitted {h / 24:.0f} days ago"))
    return out


def build(board: list[dict], preflight: list[dict], day: date, now: datetime) -> Sheet:
    calls: dict[str, Call] = {}
    skips, check_rows, issues_all = [], [], []
    for r in board:
        if r["action"] == "CHECK DATE":
            check_rows.append(r)
            continue
        risk, note = risk_read(r)
        line = Line(r, data_issues(r), risk, note)
        if r["action"] == "SKIP":
            skips.append(line)
            continue
        if line.issues:
            issues_all.append(line)
        cd = _day(r["call_date"])
        c = calls.setdefault(r["event_ticker"], Call(
            r["symbol"], r["event_ticker"], cd, r["call_time_et"], r.get("call_start_source") or "",
            bool(r.get("call_time_override")), r["phase"], r.get("markets_on_call") or 0))
        c.trades.append(line)
    ordered = sorted(calls.values(), key=lambda c: _sort_key(c.call_date, c.call_time_et))
    for c in ordered:
        c.trades.sort(key=lambda t: (t["action"] != "TRADE+", -(t["edge_c"] or 0)))

    checks = preflight_checks(preflight)
    check_dates = _check_date_events(check_rows)
    n = sum(len(c.trades) for c in ordered)
    staked = round(sum(c.stake_pct for c in ordered), 2)
    if any(not c.ok for c in checks):
        status = "STOP"
    elif check_dates or issues_all or any(c.stake_pct > PER_CALL_CAP_PCT + CAP_TOLERANCE_PCT for c in ordered):
        status = "CHECK"
    else:
        status = "READY"
    plus = sum(1 for t in (t for c in ordered for t in c.trades) if t["action"] == "TRADE+")
    headline = (f"{n} trades ({plus} TRADE+) on {len(ordered)} calls, {staked:.1f}% of bankroll"
                if n else "No trades on the board for today or tomorrow")
    return Sheet(day, now, status, headline, checks, ordered, skips, check_dates, issues_all)


def _check_date_events(rows: list[dict]) -> list[dict]:
    by: dict[str, dict] = {}
    for r in rows:
        e = by.setdefault(r["event_ticker"], {"symbol": r["symbol"], "event_ticker": r["event_ticker"],
                                              "call_time_et": r["call_time_et"], "markets": 0})
        e["markets"] += 1
    return list(by.values())


def risk_map(lines: list[Line]) -> list[tuple[str, list[list[Line]]]]:
    """Favorite price band x avoid points, holding the trades and conflict skips."""
    grid = [(f"{lo}–{hi}¢", [[] for _ in POINT_COLS]) for lo, hi in PRICE_BANDS]
    for t in lines:
        p, pts = t["fav_price_c"], t["avoid_points"]
        if p is None or pts is None:
            continue
        for i, (lo, hi) in enumerate(PRICE_BANDS):
            if lo <= p < hi + 1:
                grid[i][1][min(pts, 4)].append(t)
                break
    return grid


# ---------------------------------------------------------------- rendering

def _c(v, digits=0, suffix="¢"):
    return "–" if v is None else f"{v:.{digits}f}{suffix}"


def _do(t: Line) -> str:
    return f"{t['action']} Buy {t['side']}" if t["side"] else t["action"]


def render_md(s: Sheet) -> str:
    out = [f"# Trade Sheet · {s.day:%a %b %-d, %Y}", "",
           f"**{s.status}** · {s.headline}", "",
           f"_Generated {s.generated_at:%Y-%m-%d %H:%M} ET from `kalshi.v_mentions_board`. "
           f"Limit orders about 1¢ better than the quote; post at the midpoint if the spread is 10¢+._", "",
           "## Preflight", ""]
    out += [f"- {'OK  ' if c.ok else 'FAIL'} {c.text}" for c in s.checks]
    out += ["", "## Needs you", ""]
    needs = _needs(s)
    out += [f"- {n}" for n in needs] or ["- Nothing."]
    out += ["", "## Trades", ""]
    if not s.calls:
        out.append("No TRADE or TRADE+ rows for today or tomorrow.")
    for c in s.calls:
        when = "verified" if c.verified else f"estimated: {c.source}"
        out += [f"### {c.symbol} · {c.call_time_et} ET ({when})", "",
                f"**{c.window}** · {len(c.trades)} of {c.markets} markets · "
                f"{c.stake_pct:.2f}% of the {PER_CALL_CAP_PCT:.0f}% call cap", "",
                "| Word | Do | Cost | Spread | Market YES | Model YES | Edge | Stake | Favorite | Avoid pts | Tier | vs. risk model |",
                "|---|---|--:|--:|--:|--:|--:|--:|---|--:|---|---|"]
        for t in c.trades:
            mid = None if t.spread_c is None else t["yes_bid_c"] + t.spread_c / 2
            flag = f" **DATA ISSUE: {', '.join(t.issues)}**" if t.issues else ""
            out.append(f"| {_md(t['word'])}{flag} | {_do(t)} | {_c(t.cost_c)} | {_c(t.spread_c)} | {_c(mid, 1)} "
                       f"| {_c(t['model_c'], 1)} | {_c(t['edge_c'], 1)} | {t['stake_pct']:.2f}% "
                       f"| {t['fav_side']} {_c(t['fav_price_c'], 1)} | {t['avoid_points']} | {t['avoid_tier']} "
                       f"| {t.risk}: {t.risk_note} |")
        out.append("")
    if s.skips:
        out += ["## Skipped by the rules", "",
                "| Call | Word | Would have | Favorite | Avoid pts | Tier | Why |", "|---|---|---|---|--:|---|---|"]
        for t in s.skips:
            out.append(f"| {t['symbol']} {t['call_time_et']} | {_md(t['word'])} | "
                       f"{'Buy ' + t['side'] if t['side'] else '–'} | {t['fav_side']} {_c(t['fav_price_c'], 1)} "
                       f"| {t['avoid_points']} | {t['avoid_tier']} | {t.risk}: {_md(t.risk_note)} |")
        out.append("")
    out += ["## Risk map", "", "Favorite's price against avoid points. `+` TRADE+, `x` skipped conflict, `·` TRADE.", "",
            "| Favorite price | " + " | ".join(f"{p} pts" for p in POINT_COLS) + " |",
            "|---|" + "---|" * len(POINT_COLS)]
    for band, cols in risk_map(s.trades + [t for t in s.skips if t.risk == "Conflict"]):
        cells = [", ".join(_mark(t) for t in cell) for cell in cols]
        out.append(f"| {band} | " + " | ".join(cells) + " |")
    out.append("")
    return "\n".join(out)


def _mark(t: Line) -> str:
    sym = {"TRADE+": "+", "SKIP": "x"}.get(t["action"], "·")
    return f"{sym} {t['symbol']} {t['word']}"


def _md(s: str) -> str:
    return (s or "").replace("|", "\\|")


def _needs(s: Sheet) -> list[str]:
    out = []
    for e in s.check_dates:
        out.append(f"{e['symbol']}: the estimated call time ({e['call_time_et']}) has passed with no release "
                   f"filed, {e['markets']} {'market' if e['markets'] == 1 else 'markets'} still open. Confirm the real date and add a "
                   f"`call_time_overrides` row for `{e['event_ticker']}`.")
    for t in s.data_issues:
        out.append(f"{t['symbol']} \"{t['word']}\": {', '.join(t.issues)}. Don't trade it until fixed.")
    for c in s.calls:
        if c.stake_pct > PER_CALL_CAP_PCT + CAP_TOLERANCE_PCT:
            out.append(f"{c.symbol}: board stakes add to {c.stake_pct:.2f}%, over the {PER_CALL_CAP_PCT:.0f}% "
                       f"call cap. Trim the smallest edges.")
    est = [c.symbol for c in s.calls if not c.verified and c.window.startswith("ENTRY")]
    if est:
        out.append(f"Call times are estimated for {', '.join(est)}. Check the IR pages before placing.")
    return out


CSV_COLS = ["sheet_date", "call_date", "call_time_et", "symbol", "word", "ticker", "phase", "action", "side",
            "cost_c", "yes_bid_c", "yes_ask_c", "model_c", "fundamental_c", "edge_c", "stake_pct",
            "fav_side", "fav_price_c", "avoid_points", "avoid_tier", "risk_read", "risk_note", "data_issues"]


def render_csv(s: Sheet) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=CSV_COLS, lineterminator="\n")
    w.writeheader()
    for t in s.trades + s.skips:
        w.writerow({**{k: t.row.get(k) for k in CSV_COLS}, "sheet_date": s.day.isoformat(),
                    "call_date": str(t["call_date"])[:10], "cost_c": t.cost_c, "risk_read": t.risk,
                    "risk_note": t.risk_note, "data_issues": "; ".join(t.issues)})
    return buf.getvalue()


def render_html(s: Sheet) -> str:
    e = html.escape
    pill = {"READY": "ok", "CHECK": "warn", "STOP": "bad"}[s.status]
    risk_pill = {"Aligned": "ok", "Conflict": "bad", "Rule skip": "n", "Neutral": "n", "No read": "n"}

    def trade_row(t: Line) -> str:
        act = "ok" if t["action"].startswith("TRADE") else "you"
        issue = (f'<div class="issue">DATA ISSUE: {e(", ".join(t.issues))}</div>' if t.issues else "")
        mid = None if t.spread_c is None else t["yes_bid_c"] + t.spread_c / 2
        return (f'<tr><td><b>{e(t["word"])}</b>{issue}</td>'
                f'<td class="nw"><span class="pill p-{act}">{e(t["action"])}</span> Buy {e(t["side"] or "")}</td>'
                f'<td class="num">{_c(t.cost_c)}</td><td class="num">{_c(t.spread_c)}</td>'
                f'<td class="num">{_c(mid, 1)}</td><td class="num">{_c(t["model_c"], 1)}</td>'
                f'<td class="num">{_c(t["edge_c"], 1)}</td><td class="num">{t["stake_pct"]:.2f}%</td>'
                f'<td class="nw">{e(t["fav_side"] or "")} {_c(t["fav_price_c"], 1)}</td><td class="num">{t["avoid_points"]}</td>'
                f'<td><span class="pill p-{"bad" if t["avoid_tier"] == "AVOID" else "n"}">{e(t["avoid_tier"])}</span></td>'
                f'<td><span class="pill p-{risk_pill[t.risk]}">{e(t.risk)}</span> <span class="sub">{e(t.risk_note)}</span></td></tr>')

    head = ('<tr><th>Word</th><th>Do</th><th class="num">Cost</th><th class="num">Spread</th>'
            '<th class="num">Mkt YES</th><th class="num">Model YES</th><th class="num">Edge</th><th class="num">Stake</th>'
            '<th>Favorite</th><th class="num">Avoid pts</th><th>Tier</th><th>vs. risk model</th></tr>')
    body = []
    for c in s.calls:
        when = "verified" if c.verified else f"estimated: {c.source}"
        cap = "over" if c.stake_pct > PER_CALL_CAP_PCT + CAP_TOLERANCE_PCT else ""
        body.append(f'<tr class="grp"><td colspan="12"><b>{e(c.symbol)}</b> · {e(c.call_time_et)} ET '
                    f'<span class="sub">({e(when)})</span> · <b>{e(c.window)}</b> · {len(c.trades)} of {c.markets} markets · '
                    f'<span class="{cap}">{c.stake_pct:.2f}% of {PER_CALL_CAP_PCT:.0f}% cap</span></td></tr>')
        body += [trade_row(t) for t in c.trades]
    trades_html = (f'<div class="tbl"><table><thead>{head}</thead><tbody>{"".join(body)}</tbody></table></div>'
                   if s.calls else '<p class="empty">No TRADE or TRADE+ rows for today or tomorrow.</p>')

    skips_html = ""
    if s.skips:
        rows = "".join(
            f'<tr><td>{e(t["symbol"])} <span class="sub">{e(t["call_time_et"])}</span></td><td><b>{e(t["word"])}</b></td>'
            f'<td>{"Buy " + e(t["side"]) if t["side"] else "–"}</td><td>{e(t["fav_side"] or "")} {_c(t["fav_price_c"], 1)}</td>'
            f'<td class="num">{t["avoid_points"]}</td><td>{e(t["avoid_tier"])}</td>'
            f'<td><span class="pill p-{risk_pill[t.risk]}">{e(t.risk)}</span> <span class="sub">{e(t.risk_note)}</span></td></tr>'
            for t in s.skips)
        skips_html = ('<section><h2>Skipped by the rules</h2><div class="tbl"><table><thead><tr><th>Call</th><th>Word</th>'
                      '<th>Would have</th><th>Favorite</th><th class="num">Avoid pts</th><th>Tier</th><th>Why</th></tr></thead>'
                      f'<tbody>{rows}</tbody></table></div></section>')

    grid = ['<div></div>'] + [f'<div class="h">{p} pts</div>' for p in POINT_COLS]
    for band, cols in risk_map(s.trades + [t for t in s.skips if t.risk == "Conflict"]):
        grid.append(f'<div class="rl">{band}</div>')
        for cell in cols:
            tags = "".join(f'<span class="mk {"al" if t["action"] == "TRADE+" else "cf" if t["action"] == "SKIP" else ""}">'
                           f'{e(t["symbol"])} {e(t["word"])}</span>' for t in cell)
            grid.append(f'<div class="cell">{tags}</div>')

    checks = "".join(f'<span class="{"" if c.ok else "w"}">{e(c.text)}</span>' for c in s.checks)
    needs = "".join(f"<li>{_inline(n)}</li>" for n in _needs(s)) or "<li>Nothing.</li>"
    return TEMPLATE.format(
        title="Trade Sheet", day=f"{s.day:%a %b %-d, %Y}", status=s.status, pill=pill,
        headline=e(s.headline), generated=f"{s.generated_at:%Y-%m-%d %H:%M} ET", checks=checks, needs=needs,
        trades=trades_html, skips=skips_html, grid="".join(grid))


def _inline(s: str) -> str:
    """Escape, then turn `code` spans into <code>."""
    parts = html.escape(s).split("`")
    return "".join(f"<code>{p}</code>" if i % 2 else p for i, p in enumerate(parts))


TEMPLATE = """<title>{title}</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@700;800&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
:root{{--bg:#f6f7f9;--surface:#fff;--fg:#17202b;--muted:#5b6675;--line:#dde2e8;
--ok:#1d7a4a;--ok-bg:#e4f3ea;--warn:#a86a00;--warn-bg:#fbf1dc;--bad:#b3261e;--bad-bg:#fbe5e3;--you:#6a3fb0;--you-bg:#f1ebfb;
--display:"Archivo","Helvetica Neue",Arial,sans-serif;--body:"IBM Plex Sans",system-ui,sans-serif;--mono:"IBM Plex Mono",ui-monospace,Menlo,monospace}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--bg:#0f141a;--surface:#161d26;--fg:#e6ebf1;--muted:#9aa6b4;--line:#2a3440;
--ok:#5fcf91;--ok-bg:#15301f;--warn:#e6b04d;--warn-bg:#352812;--bad:#f08079;--bad-bg:#3a1714;--you:#b897f0;--you-bg:#2a1f40;color-scheme:dark}}}}
:root[data-theme="dark"]{{--bg:#0f141a;--surface:#161d26;--fg:#e6ebf1;--muted:#9aa6b4;--line:#2a3440;
--ok:#5fcf91;--ok-bg:#15301f;--warn:#e6b04d;--warn-bg:#352812;--bad:#f08079;--bad-bg:#3a1714;--you:#b897f0;--you-bg:#2a1f40;color-scheme:dark}}
*{{box-sizing:border-box}}
body{{background:var(--bg);color:var(--fg);font-family:var(--body);font-size:14.5px;line-height:1.5}}
.wrap{{max-width:1180px;margin:0 auto;padding-block:28px 56px;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));display:flex;flex-direction:column;gap:28px}}
h1,h2{{font-family:var(--display);margin:0;text-wrap:balance}} h1{{font-size:clamp(24px,4vw,34px);font-weight:800}} h2{{font-size:19px}}
section{{display:flex;flex-direction:column;gap:10px}}
.top{{display:flex;flex-direction:column;gap:8px}}
.status{{display:flex;gap:10px;align-items:center;flex-wrap:wrap;font-size:16px;font-weight:500}}
.meta{{font-size:12.5px;color:var(--muted)}}
.pre{{display:flex;flex-wrap:wrap;gap:6px 18px;font-size:13px;padding:10px 14px;background:var(--surface);border:1px solid var(--line);border-radius:8px}}
.pre span::before{{content:"";display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px;background:var(--ok)}}
.pre span.w::before{{background:var(--bad)}}
ul{{margin:0;padding-left:20px;display:flex;flex-direction:column;gap:4px}}
code{{font-family:var(--mono);font-size:.88em}}
.pill{{font-family:var(--mono);font-size:11px;font-weight:500;padding:2px 8px;border-radius:999px;white-space:nowrap;display:inline-block}}
.p-ok{{background:var(--ok-bg);color:var(--ok)}} .p-warn{{background:var(--warn-bg);color:var(--warn)}} .p-bad{{background:var(--bad-bg);color:var(--bad)}}
.p-you{{background:var(--you-bg);color:var(--you)}} .p-n{{background:var(--bg);color:var(--muted)}}
.tbl{{overflow-x:auto;background:var(--surface);border:1px solid var(--line);border-radius:10px}}
table{{border-collapse:collapse;width:100%;min-width:900px;font-size:13.5px}}
th,td{{text-align:left;padding:8px 10px;border-bottom:1px solid var(--line);vertical-align:top}}
th{{font-family:var(--mono);font-size:11px;letter-spacing:.05em;text-transform:uppercase;color:var(--muted);font-weight:500;background:var(--bg);white-space:nowrap}}
.num{{text-align:right;font-family:var(--mono);font-variant-numeric:tabular-nums;white-space:nowrap}}
tr.grp td{{background:var(--bg);font-size:13px}}
.nw{{white-space:nowrap}} .sub{{color:var(--muted);font-size:12.5px}} .over{{color:var(--bad);font-weight:600}}
.issue{{color:var(--bad);font-size:12px;font-weight:600}}
.empty{{color:var(--muted)}}
.rmap{{display:grid;grid-template-columns:70px repeat(5,minmax(0,1fr));gap:4px;font-size:12px;min-width:620px}}
.rmap .h{{font-family:var(--mono);font-size:11px;color:var(--muted);text-align:center}}
.rmap .rl{{font-family:var(--mono);font-size:11.5px;color:var(--muted);display:flex;align-items:center;justify-content:flex-end;padding-right:6px}}
.cell{{min-height:40px;border-radius:5px;padding:4px;display:flex;flex-wrap:wrap;gap:3px;align-content:flex-start;background:var(--surface);border:1px solid var(--line)}}
.mk{{font-family:var(--mono);font-size:10.5px;padding:1px 5px;border-radius:3px;background:var(--bg);border:1px solid var(--line)}}
.mk.al{{border-color:var(--ok);color:var(--ok)}} .mk.cf{{border-color:var(--bad);color:var(--bad);text-decoration:line-through}}
.scroll{{overflow-x:auto}}
</style>
<div class="wrap">
<div class="top">
  <h1>Trade Sheet · {day}</h1>
  <div class="status"><span class="pill p-{pill}">{status}</span> {headline}</div>
  <div class="meta">Generated {generated} from kalshi.v_mentions_board. Limit orders about 1¢ better than the quote; post at the midpoint if the spread is 10¢+.</div>
  <div class="pre">{checks}</div>
</div>
<section><h2>Needs you</h2><ul>{needs}</ul></section>
<section><h2>Trades</h2>{trades}</section>
{skips}
<section><h2>Risk map</h2><p class="meta">Favorite's price against avoid points. Green: TRADE+ (fading an AVOID favorite). Red, struck out: skipped conflict.</p>
<div class="scroll"><div class="rmap">{grid}</div></div></section>
</div>
"""
