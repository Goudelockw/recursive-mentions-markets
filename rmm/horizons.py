"""How the model does leading into the call: 30 days out down to call start.

At each horizon the market price is the quote at that time (sql/queries/horizon_prices.sql), and the
model is the 24h-before specification (fundamental model without the release + that horizon's price +
management incentive), refit walk-forward with that horizon's price so every point is out of sample.
Call start uses the call-start model (release information and the 24h price move).

For each horizon: markets with a quote, Brier of the market price and of the model on the same
markets, and cents per trade trading at that horizon's quote after fees (edge >= 2c).
"""
from __future__ import annotations

from dataclasses import dataclass

import math

import numpy as np
import pandas as pd
from scipy.special import logit

from . import db, paths, refit, review

ORDER = ["30d", "14d", "7d", "3d", "2d", "24h", "12h", "6h", "3h", "1h"]
NAMES = {"30d": "30 days", "14d": "14 days", "7d": "7 days", "3d": "3 days", "2d": "2 days", "24h": "24 hours",
         "12h": "12 hours", "6h": "6 hours", "3h": "3 hours", "1h": "1 hour", "start": "Call start"}


@dataclass
class Point:
    horizon: str
    markets: int          # markets with a quote at this horizon
    scored: int           # of those, scored out of sample (needs 60+ earlier calls)
    brier_market: float | None
    brier_model: float | None
    trades: int
    cents: float | None


def _point(label: str, sr: refit.StageResult, x: pd.DataFrame, bid: str, ask: str, markets: int) -> Point:
    bt = sr.backtest.merge(x[["ticker", bid, ask]], on="ticker")
    if bt.empty:
        return Point(label, markets, 0, None, None, 0, None)
    y = bt["won"].to_numpy(float)
    traded, pnl = review.pnl(bt["p_model"].to_numpy(float), y, bt[bid].to_numpy(float), bt[ask].to_numpy(float))
    mid = refit.clip((bt[bid].to_numpy(float) + bt[ask].to_numpy(float)) / 2)
    return Point(label, markets, len(bt), float(np.mean((mid - y) ** 2)), float(np.mean((bt["p_model"] - y) ** 2)),
                 int(traded.sum()), float(np.nanmean(pnl) * 100) if traded.any() else None)


def analyze(train: pd.DataFrame | None = None, prices: list[dict] | None = None) -> list[Point]:
    d = review.training() if train is None else train
    px = pd.DataFrame(db.run_query(paths.query("horizon_prices")) if prices is None else prices)
    for c in ("bid", "ask"):
        px[c] = pd.to_numeric(px[c], errors="coerce")
    out = []
    for h in ORDER:
        q = px[px["label"] == h][["ticker", "bid", "ask"]].rename(columns={"bid": "bid_h", "ask": "ask_h"})
        x = d.merge(q, on="ticker", how="inner")
        x = x[(x["bid_h"] > 0) | (x["ask_h"] < 1)].reset_index(drop=True)
        x["lph"] = logit(refit.clip((x["bid_h"] + x["ask_h"]) / 2))
        sr = refit.walk_forward_spec(x, refit.F_EARLY, ["lph", "lA", "inc"], "lph", h)
        out.append(_point(h, sr, x, "bid_h", "ask_h", len(x)))
    x = d[d["lp"].notna()].reset_index(drop=True)
    out.append(_point("start", refit.walk_forward(x, "call_start"), x, "bid", "ask", len(x)))
    return out


# ---------------------------------------------------------------- charts

def _x(i: int, n: int, L: int, W: int, R: int) -> float:
    inset = 28   # keeps the first point clear of the y-axis labels
    return L + inset + i * (W - L - R - inset) / (n - 1)


def _nice_ticks(lo: float, hi: float, n: int = 5) -> list[float]:
    raw = (hi - lo) / (n - 1)
    mag = 10 ** math.floor(math.log10(raw))
    step = next(m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw)
    start = math.floor(lo / step) * step
    return [start + i * step for i in range(int(math.ceil((hi - start) / step)) + 1)]


def line_svg(points: list[Point], series: list[tuple[str, str, str]], fmt: str, zero: bool = False,
             label: str = "") -> str:
    """One y-axis line chart over the horizons. series: (attribute, css class, legend name)."""
    W, H, L, R, T, B = 760, 250, 52, 92, 14, 46
    pts = [p for p in points if p.scored]
    n = len(pts)
    if n < 2:
        return "<p class='meta'>Not enough scored markets yet.</p>"
    vals = [getattr(p, a) for p in pts for a, _, _ in series if getattr(p, a) is not None]
    lo, hi = min(vals + ([0] if zero else [])), max(vals + ([0] if zero else []))
    pad = (hi - lo) * 0.08 or abs(hi) * 0.1 or 1
    ticks = _nice_ticks(lo - pad, hi + pad)
    lo, hi = ticks[0], ticks[-1]
    y = lambda v: T + (hi - v) / (hi - lo) * (H - T - B)
    xs = [_x(i, n, L, W, R) for i in range(n)]
    out = [f'<svg viewBox="0 0 {W} {H}" class="chart line" role="img" aria-label="{label}">']
    for v in ticks:
        out.append(f'<line x1="{L}" x2="{W - R}" y1="{y(v):.1f}" y2="{y(v):.1f}" class="grid"/>'
                   f'<text x="{L - 6}" y="{y(v) + 4:.1f}" class="tick" text-anchor="end">{fmt.format(v)}</text>')
    if zero and lo < 0 < hi:
        out.append(f'<line x1="{L}" x2="{W - R}" y1="{y(0):.1f}" y2="{y(0):.1f}" class="zero"/>')
    for i, p in enumerate(pts):
        out.append(f'<text x="{xs[i]:.1f}" y="{H - 26}" class="tick" text-anchor="middle">{p.horizon if p.horizon != "start" else "start"}</text>'
                   f'<text x="{xs[i]:.1f}" y="{H - 12}" class="tick sub" text-anchor="middle">{p.scored:,}</text>')
    out.append(f'<text x="{L - 6}" y="{H - 12}" class="tick sub" text-anchor="end">markets</text>')
    for a, cls, name in series:
        seg = [(xs[i], getattr(p, a)) for i, p in enumerate(pts) if getattr(p, a) is not None]
        if not seg:
            continue
        out.append(f'<polyline points="{" ".join(f"{px:.1f},{y(v):.1f}" for px, v in seg)}" class="ln {cls}"/>')
        out += [f'<circle cx="{px:.1f}" cy="{y(v):.1f}" r="4" class="mk {cls}"/>' for px, v in seg]
        lx, lv = seg[-1]
        out.append(f'<text x="{lx + 9:.1f}" y="{y(lv) + 4:.1f}" class="dl {cls}t">{name}</text>')
    step = xs[1] - xs[0]
    for i, p in enumerate(pts):
        tip = f"{NAMES[p.horizon]} before the call · {p.scored:,} markets: " + "; ".join(
            f"{name} {fmt.format(getattr(p, a))}" for a, _, name in series if getattr(p, a) is not None)
        if p.trades:
            tip += f" · {p.trades:,} trades"
        out.append(f'<g class="col"><title>{tip}</title><rect x="{xs[i] - step / 2:.1f}" y="{T}" width="{step:.1f}" '
                   f'height="{H - T - B}" class="hit"/><line x1="{xs[i]:.1f}" x2="{xs[i]:.1f}" y1="{T}" y2="{H - B}" class="cross"/></g>')
    out.append("</svg>")
    return "".join(out)


def table(points: list[Point]) -> str:
    rows = "".join(
        f"<tr><td>{NAMES[p.horizon]}</td><td class='num'>{p.markets:,}</td><td class='num'>{p.scored:,}</td>"
        f"<td class='num'>{'–' if p.brier_market is None else f'{p.brier_market:.4f}'}</td>"
        f"<td class='num'>{'–' if p.brier_model is None else f'{p.brier_model:.4f}'}</td>"
        f"<td class='num {('good' if (p.brier_market or 0) > (p.brier_model or 9) else 'bad') if p.brier_model is not None else ''}'>"
        f"{'–' if p.brier_model is None else f'{p.brier_model - p.brier_market:+.4f}'}</td>"
        f"<td class='num'>{p.trades:,}</td><td class='num'>{'–' if p.cents is None else f'{p.cents:+.1f}¢'}</td></tr>"
        for p in points)
    return ("<div class='tbl'><table><thead><tr><th>Before the call</th><th class='num'>With a quote</th><th class='num'>Scored</th>"
            "<th class='num'>Market Brier</th><th class='num'>Model Brier</th><th class='num'>Model − market</th>"
            f"<th class='num'>Trades</th><th class='num'>¢ per trade</th></tr></thead><tbody>{rows}</tbody></table></div>")
