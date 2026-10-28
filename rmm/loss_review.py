"""Daily loss review: grade the previous day's trades, slice where the losses came from, and
score the standing test ideas in shadow.

    python -m rmm loss-review [--date YYYY-MM-DD]   writes outputs/reviews/YYYY-MM/YYYY-MM-DD_loss-review.md

Trades are every TRADE / TRADE+ row in kalshi.v_mentions_history (sql/queries/loss_review.sql):
the live score where one was logged, else the live model's walk-forward backtest, so the history
is long enough to judge an idea against. Money is bankroll return (stake x return, in % of
bankroll); cents are per contract.

An idea is a rule that would change trading: skip a kind of trade, or halve its stake. Each one
is scored against every window (the day, the last 30 days, the season, all history) as the change
in bankroll return had it been in force. Ideas are only scored here; changing the trading rules
is the owner's decision.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Callable

import re

import numpy as np
import pandas as pd

from . import sectors

JUMP = 0.3          # log-odds rise from 24h before to call start that counts as a late jump
SEASON_START = "2026-07-01"


@dataclass
class Idea:
    id: str
    title: str
    source: str
    effect: str                                   # skip | half
    applies: Callable[[pd.DataFrame], pd.Series]


IDEAS = [
    Idea("I-001", "Call start: skip NO trades that bet against a late jump (price up 0.3+ log-odds since 24h)",
         "EXP-0001", "skip", lambda d: (d.stage == "call_start") & (d.side == "NO") & d.late_jump),
    Idea("I-002", "Halve the stake on NO trades on external (news) words", "EXP-0001", "half",
         lambda d: (d.side == "NO") & (d.scope == "external")),
    # I-003's sectors were picked from all history including Jul-Oct; chosen from pre-July data alone
    # the rule keeps only Autos. Scored here to see whether the pattern holds from now on.
    Idea("I-003", "Skip NO trades on external words in Banks, Telecom & media, Autos, Aerospace (picked after the fact)",
         "EXP-0002", "skip", lambda d: (d.side == "NO") & (d.scope == "external")
         & d.sector.isin(["Banks & finance", "Telecom & media", "Autos & machinery", "Aerospace & defense"])),
    Idea("I-004", "Skip NO trades on external words with 2+ alternatives (\"Iran / Middle East\")", "EXP-0003", "skip",
         lambda d: (d.side == "NO") & (d.scope == "external") & (d.alternatives >= 2)),
    Idea("I-005", "I-004, but only plain TRADE (keep TRADE+, where the risk model agrees)", "EXP-0004", "skip",
         lambda d: (d.side == "NO") & (d.scope == "external") & (d.alternatives >= 2) & (d.action == "TRADE")),
]


def alternatives(word: str) -> int:
    """How many words count for the market: "Iran / Middle East" is 2. Qualifiers like "(2+ times)" don't count."""
    return len([w for w in re.sub(r"\(.*?\)", "", str(word)).split("/") if w.strip()])


@dataclass
class Review:
    day: date
    trades: pd.DataFrame
    windows: dict[str, pd.DataFrame] = field(default_factory=dict)


def prepare(rows: list[dict]) -> pd.DataFrame:
    d = pd.DataFrame(rows)
    if d.empty:
        return d
    d["call_date"] = pd.to_datetime(d["call_date"])
    for c in ("pnl_c", "ret_pct", "stake_pct", "bid_c", "ask_c", "model_c", "move_24h"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d["won"] = pd.to_numeric(d["won"], errors="coerce")
    d["scope"] = np.where(d["word_scope"] == "external", "external", np.where(d["word_scope"].isna(), "unlabeled", "own business"))
    d["sector"] = [sectors.sector(s, sic) for s, sic in zip(d["symbol"], d["sic"])]
    d["late_jump"] = (d["stage"] == "call_start") & (d["move_24h"] > JUMP)
    d["alternatives"] = d["word"].map(alternatives)
    d["entry"] = d["stage"].map({"early_24h": "24h before", "call_start": "call start"})
    return d


def build(rows: list[dict], day: date) -> Review:
    d = prepare(rows)
    r = Review(day, d)
    if d.empty:
        return r
    t = pd.Timestamp(day)
    r.windows = {"day": d[d.call_date == t], "last 30 days": d[(d.call_date > t - timedelta(days=30)) & (d.call_date <= t)],
                 "season": d[(d.call_date >= SEASON_START) & (d.call_date <= t)], "all history": d[d.call_date <= t]}
    return r


def summary(w: pd.DataFrame) -> dict:
    if w.empty:
        return {"trades": 0, "won": None, "c_trade": None, "ret": 0.0}
    return {"trades": len(w), "won": float(w["won"].mean()), "c_trade": float(w["pnl_c"].mean()), "ret": float(w["ret_pct"].sum())}


def slices(w: pd.DataFrame, by: str) -> pd.DataFrame:
    if w.empty:
        return pd.DataFrame()
    g = w.groupby(by, observed=True).agg(trades=("pnl_c", "size"), won=("won", "mean"), c_trade=("pnl_c", "mean"), ret=("ret_pct", "sum"))
    return g.sort_values("ret")


def idea_effect(w: pd.DataFrame, idea: Idea) -> dict:
    if w.empty:
        return {"affected": 0, "c_trade": None, "delta_ret": 0.0}
    m = idea.applies(w).fillna(False).astype(bool)
    hit = w[m]
    delta = -hit["ret_pct"].sum() if idea.effect == "skip" else -0.5 * hit["ret_pct"].sum()
    return {"affected": int(m.sum()), "c_trade": float(hit["pnl_c"].mean()) if len(hit) else None, "delta_ret": float(delta)}


def losers(w: pd.DataFrame, n: int = 8) -> pd.DataFrame:
    return w[w["pnl_c"] < 0].sort_values("ret_pct").head(n)


def headline(r: Review) -> str:
    s = summary(r.windows.get("day", pd.DataFrame()))
    m = summary(r.windows.get("last 30 days", pd.DataFrame()))
    if not s["trades"]:
        return f"No graded trades on {r.day:%b %-d} · last 30 days {m['ret']:+.1f}% of bankroll on {m['trades']} trades"
    return (f"{r.day:%b %-d}: {s['trades']} trades, {s['won']:.0%} won, {s['ret']:+.1f}% of bankroll · "
            f"last 30 days {m['ret']:+.1f}% on {m['trades']} trades")


# ---------------------------------------------------------------- render

def _fmt(v, f="{:+.1f}"):
    return "–" if v is None or (isinstance(v, float) and np.isnan(v)) else f.format(v)


def _table(df: pd.DataFrame, label: str) -> list[str]:
    if df.empty:
        return ["Nothing to show."]
    out = [f"| {label} | Trades | Won | ¢ / trade | Bankroll |", "|---|---|---|---|---|"]
    for k, r in df.iterrows():
        out.append(f"| {k} | {int(r.trades)} | {r.won:.0%} | {_fmt(r.c_trade)} | {_fmt(r.ret, '{:+.2f}%')} |")
    return out


def render_md(r: Review) -> str:
    out = [f"# Loss review · {r.day:%a %b %-d, %Y}", "", headline(r), ""]
    if r.trades.empty:
        return "\n".join(out + ["No graded trades yet."]) + "\n"
    out += ["## Results", "", "| Window | Trades | Won | ¢ / trade | Bankroll |", "|---|---|---|---|---|"]
    for name, w in r.windows.items():
        s = summary(w)
        out.append(f"| {name} | {s['trades']} | {_fmt(s['won'], '{:.0%}')} | {_fmt(s['c_trade'])} | {s['ret']:+.2f}% |")
    day = r.windows["day"]
    out += ["", f"## Biggest losses on {r.day:%b %-d}", ""]
    lw = losers(day)
    if lw.empty:
        out.append("No losing trades.")
    else:
        out += ["| Call | Word | Entry | Side | Paid | Model | Scope | Sector | Late jump | Bankroll |", "|---|---|---|---|---|---|---|---|---|---|"]
        for _, x in lw.iterrows():
            paid = x.ask_c if x.side == "YES" else 100 - x.bid_c
            out.append(f"| {x.symbol} | {x.word} | {x.entry} | {x.side} | {paid:.0f}¢ | {x.model_c:.0f}% YES | {x.scope} | "
                       f"{x.sector} | {'yes' if x.late_jump else ''} | {x.ret_pct:+.2f}% |")
    w30 = r.windows["last 30 days"]
    out += ["", "## Where the last 30 days' losses came from", "",
            "Each table is sorted worst first. A slice that keeps showing up at the top is a candidate idea.", ""]
    w30 = w30.assign(words=np.where(w30["alternatives"] >= 2, "2+ alternatives", "1 word"))
    for by, label in (("entry", "Entry"), ("side", "Side"), ("scope", "Word scope"), ("words", "Words in the market"),
                      ("late_jump", "Late jump (call start)"),
                      ("avoid_tier", "Risk tier"), ("sector", "Sector")):
        out += [f"### {label}", ""] + _table(slices(w30, by), label) + [""]
    out += ["## Test ideas, scored in shadow", "",
            "What each idea would have changed, in % of bankroll (positive = it would have helped). "
            "Nothing here changes trading; adopting an idea is your call.", "",
            "| Idea | Effect | " + " | ".join(r.windows) + " |", "|---|---|" + "---|" * len(r.windows)]
    for idea in IDEAS:
        cells = []
        for w in r.windows.values():
            e = idea_effect(w, idea)
            cells.append(f"{e['delta_ret']:+.2f}% ({e['affected']})" if e["affected"] else "–")
        out.append(f"| **{idea.id}** {idea.title} ({idea.source}) | {idea.effect} | " + " | ".join(cells) + " |")
    out += ["", "In brackets: trades the idea touches in that window."]
    return "\n".join(out) + "\n"
