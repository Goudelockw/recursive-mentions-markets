from lib import *
rng = np.random.default_rng(7)
def boot(x, p="p_v2wf", B=2000):
    x = x[x[p].notna()].copy()
    tr, pnl = review.pnl(x[p].to_numpy(), x["y"].to_numpy(), x["qbid"].to_numpy(), x["qask"].to_numpy())
    x["pnl"] = np.where(tr, pnl, np.nan); x["bias"] = x["p_mkt"] - x["y"]
    g = x.groupby("event_ticker").agg(s=("pnl", "sum"), n=("pnl", "count"), b=("bias", "sum"), m=("bias", "count"))
    ids = np.arange(len(g)); cs, bs = [], []
    for _ in range(B):
        i = rng.choice(ids, len(ids)); s = g.iloc[i]
        cs.append(s.s.sum()/max(s.n.sum(),1)*100); bs.append(s.b.sum()/s.m.sum()*100)
    return np.percentile(cs, [5, 50, 95]).round(1), np.percentile(bs, [5, 50, 95]).round(1)
for st in ["call_start", "early_24h"]:
    for lab, lo, hi in [("Sep-Oct", "2026-09-01", "2026-11-01"), ("Jan-Aug", "2026-01-01", "2026-09-01")]:
        x = a[(a.stage == st) & (a.call_date >= lo) & (a.call_date < hi)]
        c, b = boot(x)
        print(f"{st:11} {lab}: c/trade 90% CI {c}   market YES overpricing (pts) 90% CI {b}")
