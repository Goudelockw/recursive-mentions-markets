"""Release review: is a model version better than the one it would replace, and what changed?

    python -m rmm review                      newest challenger vs. the live model (print)
    python -m rmm review --version 3 --save   store the review on v3 (rmm_rw)

Two head-to-heads, both out of sample, per entry point:
  forward test   markets settled after the old version's training data ends. The old version is
                 scored with its frozen coefficients (exactly what the board traded), the new one with
                 its walk-forward predictions (each month from a model trained only on earlier months).
  walk-forward   the two versions' walk-forward backtests on the markets both cover.
Each reports Brier for both, the share of call-level resamples in which the new one is better, and
cents per trade trading at the real quote after fees (the board's rule: edge >= 2c after fees).
"""
from __future__ import annotations

import hashlib
import json

import numpy as np
import pandas as pd
from scipy.special import expit, logit

from . import db, paths, refit
from .variables import label

FEE_RATE, MIN_EDGE = 0.07, 0.02
QUOTES = {"call_start": ("bid", "ask"), "early_24h": ("bid_24h", "ask_24h")}
MIN_FORWARD, MIN_COMMON = 100, 300


def training() -> pd.DataFrame:
    d = refit.prepare(db.run_query(paths.query("model_training")))
    for c in ("bid_24h", "ask_24h"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    return d


def coefficients(version: int) -> pd.DataFrame:
    return pd.DataFrame(db.query(
        "select model, term, coef::float, se::float, p_value::float, sd::float from kalshi.model_version_coefficients "
        "where version = $1", [version]))


def backtest(version: int) -> pd.DataFrame:
    return pd.DataFrame(db.query("select ticker, stage, p_model::float as p from kalshi.model_version_backtest "
                                 "where version = $1", [version]))


def versions() -> list[dict]:
    return db.query("select version, status, trained_through::text from kalshi.model_versions order by version")


# ---------------------------------------------------------------- scoring

def score(co: pd.DataFrame, d: pd.DataFrame, stage: str) -> np.ndarray:
    """P(YES) from frozen coefficients, built the way the walk-forward backtest builds it."""
    Ff, Bf, pcol, (fname, cname) = refit.STAGES[stage]

    def lin(model: str, x: pd.DataFrame, terms: list[str]) -> np.ndarray:
        c = co[co["model"] == model].set_index("term")["coef"]
        return expit(c["(Intercept)"] + x[terms].to_numpy(float) @ c[terms].to_numpy(float))

    x = d.copy()
    x["lA"] = logit(refit.clip(lin(fname, x, Ff)))
    pB = refit.clip(lin(cname, x, Bf))
    k = float(co[(co["model"] == cname) & (co["term"] == "calibration_k")]["coef"].iloc[0])
    pr = expit(x[pcol].to_numpy(float))
    return refit.clip(expit(logit(pr) + k * (logit(pB) - logit(pr))))


def fee(p):
    return FEE_RATE * p * (1 - p)


def pnl(p: np.ndarray, y: np.ndarray, bid: np.ndarray, ask: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Per market: whether it trades and the profit per $1 contract (buy YES at the ask or NO at 1 - bid)."""
    ev_yes = p - ask - fee(ask)
    ev_no = (1 - p) - (1 - bid) - fee(1 - bid)
    yes = (ask > 0) & (ask < 1) & (ev_yes >= MIN_EDGE) & (ev_yes >= ev_no)
    no = ~yes & (bid > 0) & (bid < 1) & (ev_no >= MIN_EDGE)
    out = np.where(yes, y - ask - fee(ask), np.where(no, (1 - y) - (1 - bid) - fee(1 - bid), np.nan))
    return yes | no, out


def head_to_head(old: np.ndarray, new: np.ndarray, x: pd.DataFrame, stage: str, seed: int = 1) -> dict:
    ok = ~np.isnan(old) & ~np.isnan(new) & x["won"].notna().to_numpy()
    old, new, x = old[ok], new[ok], x[ok]
    y = x["won"].to_numpy(float)
    if not len(y):
        return {"markets": 0}
    d = (new - y) ** 2 - (old - y) ** 2
    rng = np.random.default_rng(seed)
    groups = pd.Series(np.arange(len(y))).groupby(x["event_ticker"].to_numpy()).apply(list).tolist()
    boot = []
    for _ in range(1000):
        pick = rng.integers(0, len(groups), len(groups))
        idx = np.concatenate([groups[i] for i in pick])
        boot.append(d[idx].mean())
    bid_c, ask_c = QUOTES[stage]
    bid, ask = x[bid_c].to_numpy(float), x[ask_c].to_numpy(float)
    t_old, p_old = pnl(old, y, bid, ask)
    t_new, p_new = pnl(new, y, bid, ask)
    price = refit.clip((bid + ask) / 2)
    return {"markets": int(len(y)), "calls": len(groups),
            "brier_old": float(np.mean((old - y) ** 2)), "brier_new": float(np.mean((new - y) ** 2)),
            "brier_price": float(np.nanmean((price - y) ** 2)), "diff": float(d.mean()),
            "share_better": float(np.mean(np.array(boot) < 0)),
            "trades_old": int(t_old.sum()), "cents_old": float(np.nanmean(p_old) * 100) if t_old.any() else None,
            "trades_new": int(t_new.sum()), "cents_new": float(np.nanmean(p_new) * 100) if t_new.any() else None}


# ---------------------------------------------------------------- risk model snapshot

def risk_rules() -> dict:
    rules = db.query("select side, zone_lo, point from kalshi.avoid_point_rules order by side, zone_lo, point")
    tests = db.query("""select side, point, zone_lo, extra_losses_all::float as all_, extra_losses_early::float as early,
                               extra_losses_late::float as late, markets_with, counts
                        from kalshi.avoid_point_tests order by side, zone_lo, point""")
    h = hashlib.sha256(json.dumps(rules, sort_keys=True).encode()).hexdigest()[:12]
    return {"hash": h, "rules": len(rules), "items": rules, "tests": tests}


# ---------------------------------------------------------------- the review

def compare(new_v: int, old_v: int, d: pd.DataFrame | None = None) -> dict:
    d = training() if d is None else d
    vs = {v["version"]: v for v in versions()}
    old_tt = vs[old_v]["trained_through"]
    co_old, co_new = coefficients(old_v), coefficients(new_v)
    bt_new, bt_old = backtest(new_v), backtest(old_v)
    out = {"version": new_v, "against": old_v, "trained_through": vs[new_v]["trained_through"],
           "against_trained_through": old_tt,
           "new_markets": int((d["call_date"] > pd.Timestamp(old_tt)).sum()), "stages": {}}

    for stage in refit.STAGES:
        pcol = refit.STAGES[stage][2]
        x = d[d[pcol].notna()].reset_index(drop=True)
        pn = x["ticker"].map(bt_new[bt_new["stage"] == stage].set_index("ticker")["p"]).to_numpy(float)
        po = x["ticker"].map(bt_old[bt_old["stage"] == stage].set_index("ticker")["p"]).to_numpy(float)
        fwd = (x["call_date"] > pd.Timestamp(old_tt)).to_numpy()
        frozen = np.where(fwd, score(co_old, x, stage), np.nan)
        out["stages"][stage] = {"forward": head_to_head(frozen, np.where(fwd, pn, np.nan), x, stage),
                                "walk_forward": head_to_head(po, pn, x, stage)}

    # coefficient movers, in log-odds per unit of the term's spread (binary: per 0 -> 1)
    m = co_new.merge(co_old, on=["model", "term"], how="outer", suffixes=("_new", "_old"))
    m = m[m["term"] != "(Intercept)"]
    m["delta"] = m["coef_new"] - m["coef_old"]
    m["scale"] = m["sd_new"].where(m["sd_new"].notna() & (m["term"] != "calibration_k"), 1.0)
    m["std_delta"] = m["delta"] * m["scale"]
    movers = m.reindex(m["std_delta"].abs().sort_values(ascending=False).index).head(8)
    out["movers"] = [{"model": r["model"], "term": r["term"], "label": label(r["term"]),
                      "old": None if pd.isna(r["coef_old"]) else float(r["coef_old"]),
                      "new": None if pd.isna(r["coef_new"]) else float(r["coef_new"]),
                      "std_delta": None if pd.isna(r["std_delta"]) else float(r["std_delta"])} for _, r in movers.iterrows()]
    terms_old = set(zip(co_old["model"], co_old["term"]))
    terms_new = set(zip(co_new["model"], co_new["term"]))
    out["terms_added"] = sorted(f"{a}.{b}" for a, b in terms_new - terms_old)
    out["terms_removed"] = sorted(f"{a}.{b}" for a, b in terms_old - terms_new)
    out["risk_rules_hash"] = risk_rules()["hash"]
    out["verdict"], out["reason"] = verdict(out)
    return out


def verdict(r: dict) -> tuple[str, str]:
    """Better / Worse / No clear difference / Not enough evidence, from the forward test when it
    has enough markets, else the walk-forward head-to-head."""
    basis, used = None, []
    for which, need in (("forward", MIN_FORWARD), ("walk_forward", MIN_COMMON)):
        st = [r["stages"][s][which] for s in refit.STAGES]
        if all(x.get("markets", 0) >= need for x in st):
            basis, used = which, st
            break
    if not basis:
        return "Not enough evidence", (f"Fewer than {MIN_FORWARD} new markets since v{r['against']}'s data ends "
                                       f"and fewer than {MIN_COMMON} markets both backtests cover.")
    name = "forward test" if basis == "forward" else "walk-forward head-to-head"
    diffs = [x["diff"] for x in used]
    best = max(x["share_better"] for x in used)
    worst = min(x["share_better"] for x in used)
    if all(dd < 0 for dd in diffs) and best >= 0.8:
        return "Better", f"Lower Brier at both entry points in the {name}, better in up to {best:.0%} of resamples."
    if all(dd > 0 for dd in diffs) and worst <= 0.2:
        return "Worse", f"Higher Brier at both entry points in the {name}."
    return "No clear difference", f"Mixed or small differences in the {name} (better in {worst:.0%}–{best:.0%} of resamples)."


def save(version: int, review: dict) -> None:
    rr = risk_rules()
    db.transaction([("update kalshi.model_versions set review = $2::jsonb, risk_rules = $3::jsonb where version = $1",
                     [version, json.dumps(review), json.dumps({"hash": rr["hash"], "rules": rr["rules"]})])])


def summary(r: dict) -> str:
    lines = [f"v{r['version']} vs v{r['against']}: {r['verdict']}. {r['reason']}",
             f"  data: trained through {r['trained_through']} vs {r['against_trained_through']} "
             f"({r['new_markets']:,} settled markets after v{r['against']}'s data ends)"]
    for stage, st in r["stages"].items():
        for which in ("forward", "walk_forward"):
            x = st[which]
            if not x.get("markets"):
                continue
            c = lambda v: "–" if v is None else f"{v:+.1f}c"
            lines.append(f"  {stage:<10} {which:<12} {x['markets']:>5} mkts  Brier v{r['against']} {x['brier_old']:.4f} "
                         f"v{r['version']} {x['brier_new']:.4f} (price {x['brier_price']:.4f}), better in {x['share_better']:.0%}; "
                         f"c/trade {c(x['cents_old'])} ({x['trades_old']}) -> {c(x['cents_new'])} ({x['trades_new']})")
    return "\n".join(lines)
