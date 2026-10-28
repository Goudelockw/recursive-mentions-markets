"""Drop-one ablation of the mentions model: walk-forward Brier, cents per trade, paired bootstrap by call."""
import sys, numpy as np, pandas as pd
sys.path.insert(0, "/home/user/recursive-mentions-markets")
from rmm import refit, review
rng = np.random.default_rng(11)
d = pd.read_pickle("../train.pkl")
FUND = {"r4": ["r4"], "said_prev": ["said_prev"], "avg_count": ["avg_count"], "no_hist": ["no_hist"], "multi": ["multi"],
        "ext+politics": ["ext", "politics"], "analyst_rate4": ["analyst_rate4"], "corpus_spike_z": ["corpus_spike_z"],
        "corpus_rare": ["corpus_rare"], "analysts_n": ["analysts_n"], "yoy pair": ["said_yoy", "has_yoy"],
        "peer pair": ["peer_rate", "has_peer"], "valence trio": ["val", "val_neutral", "val_strong"], "inc": ["inc"],
        "story0": ["story0"], "filing_said (fund)": ["filing_said"], "rel_head": ["rel_head"]}
COMB = {"move24+has24": ["move24", "has24"], "inc (combined)": ["inc"], "filing_said (combined)": ["filing_said"]}
def score(sr, stage):
    bid, ask = review.QUOTES[stage]
    bt = sr.backtest.merge(d[["ticker", "event_ticker", "call_date", bid, ask]], on="ticker")
    tr, pnl = review.pnl(bt.p_model.to_numpy(float), bt.won.to_numpy(float), bt[bid].to_numpy(float), bt[ask].to_numpy(float))
    bt["pnl"] = np.where(tr, pnl, 0.0); bt["sq"] = (bt.p_model - bt.won) ** 2
    return bt
def compare(base, new):
    m = base[["ticker", "event_ticker", "call_date", "sq", "pnl"]].merge(new[["ticker", "sq", "pnl"]], on="ticker", suffixes=("_b", "_n"))
    g = m.assign(dsq=m.sq_n - m.sq_b, dp=m.pnl_n - m.pnl_b).groupby("event_ticker")[["dsq", "dp"]].sum()
    ids = np.arange(len(g)); B = [g.iloc[rng.choice(ids, len(ids))].sum() for _ in range(500)]
    return {"brier_change_x1e4": (m.sq_n.mean() - m.sq_b.mean()) * 1e4, "worse_in": np.mean([b.dsq > 0 for b in B]),
            "cents_change": (m.pnl_n.sum() - m.pnl_b.sum()) * 100, "sepoct_cents_change": (m[m.call_date >= "2026-09-01"].pnl_n.sum() - m[m.call_date >= "2026-09-01"].pnl_b.sum()) * 100}
rows = []
for stage in ["early_24h", "call_start"]:
    Ff, Bf, pcol, _ = refit.STAGES[stage]
    base = score(refit.walk_forward_spec(d, Ff, Bf, pcol, stage), stage)
    rows.append({"stage": stage, "dropped": "(none: current model)", "brier": base.sq.mean(), "cents": base.pnl.sum() * 100})
    for name, terms in FUND.items():
        if not set(terms) & set(Ff): continue
        new = score(refit.walk_forward_spec(d, [t for t in Ff if t not in terms], Bf, pcol, stage), stage)
        rows.append({"stage": stage, "dropped": name, "brier": new.sq.mean(), "cents": new.pnl.sum() * 100, **compare(base, new)})
    for name, terms in COMB.items():
        if not set(terms) & set(Bf): continue
        new = score(refit.walk_forward_spec(d, Ff, [t for t in Bf if t not in terms], pcol, stage), stage)
        rows.append({"stage": stage, "dropped": name, "brier": new.sq.mean(), "cents": new.pnl.sum() * 100, **compare(base, new)})
    print(stage, "done", flush=True)
r = pd.DataFrame(rows); r.to_pickle("ablation.pkl")
pd.set_option("display.width", 220)
print(r.round(4).to_string(index=False))
