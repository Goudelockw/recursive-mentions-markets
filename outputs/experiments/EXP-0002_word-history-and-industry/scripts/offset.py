"""Walk-forward sector x scope offsets on top of the current model's out-of-sample predictions."""
import sys, numpy as np, pandas as pd
sys.path.insert(0, "/home/user/recursive-mentions-markets")
from scipy.special import logit, expit
from rmm import review
rng = np.random.default_rng(3)
preds = pd.read_pickle("wf_preds.pkl"); d = pd.read_pickle("train_feats.pkl")
def run(stage, keys, shrink):
    bid, ask = review.QUOTES[stage]
    bt = preds[(stage, "current model")].merge(d[["ticker", "sector", "ext", "month"]], on="ticker")
    bt["scope"] = np.where(bt.ext.astype(float) > 0, "ext", "own")
    bt["g"] = bt[keys].astype(str).agg("|".join, axis=1)
    lp = logit(np.clip(bt.p_model.to_numpy(float), .01, .99)); y = bt.y.to_numpy(float)
    adj = lp.copy()
    for mo in sorted(bt.month.unique()):
        past = (bt.month < mo).to_numpy(); now = (bt.month == mo).to_numpy()
        if past.sum() < 500: continue
        r = pd.DataFrame({"g": bt.g[past], "res": (y[past] - bt.p_model[past]) / np.maximum(bt.p_model[past] * (1 - bt.p_model[past]), .05)})
        s = r.groupby("g").res.agg(["sum", "count"]); off = (s["sum"] / (s["count"] + shrink)).clip(-1, 1)
        adj[now] = lp[now] + bt.g[now].map(off).fillna(0).to_numpy()
    p_new = expit(adj); p_old = expit(lp)
    out = []
    for lab, m in [("all", np.ones(len(bt), bool)), ("Sep–Oct", (bt.call_date >= "2026-09-01").to_numpy())]:
        b = bt[m]; tr_o, pn_o = review.pnl(p_old[m], y[m], b[bid].to_numpy(float), b[ask].to_numpy(float))
        tr_n, pn_n = review.pnl(p_new[m], y[m], b[bid].to_numpy(float), b[ask].to_numpy(float))
        # paired bootstrap by call on Brier
        dB = pd.DataFrame({"e": b.event_ticker, "d": (p_new[m] - y[m]) ** 2 - (p_old[m] - y[m]) ** 2}).groupby("e").d.agg(["sum", "count"])
        ids = np.arange(len(dB)); better = np.mean([dB.iloc[i]["sum"].sum() < 0 for i in (rng.choice(ids, len(ids)) for _ in range(1000))])
        out.append({"stage": stage, "groups": "+".join(keys), "shrink": shrink, "period": lab, "brier_old": np.mean((p_old[m]-y[m])**2), "brier_new": np.mean((p_new[m]-y[m])**2),
                    "better_in": better, "c_old": np.nanmean(pn_o)*100, "c_new": np.nanmean(pn_n)*100, "c_total_old": np.nansum(pn_o)*100, "c_total_new": np.nansum(pn_n)*100, "trades_new": int(tr_n.sum())})
    return out
rows = []
for stage in ["early_24h", "call_start"]:
    for keys in (["sector"], ["sector", "scope"]):
        for shrink in (50, 150):
            rows += run(stage, keys, shrink)
print(pd.DataFrame(rows).round(4).to_string(index=False))
