import numpy as np, pandas as pd, sys
sys.path.insert(0, "/home/user/recursive-mentions-markets")
from rmm import review
pd.set_option("display.width", 220); pd.set_option("display.max_rows", 200)
a = pd.read_pickle("/tmp/claude-0/-home-user/85a95fd0-89d0-5eac-ac11-88fd8e926ac6/scratchpad/oct/all.pkl")
def summ(g, p="p_v2wf"):
    g = g[g[p].notna()]
    y = g["y"].to_numpy(); pm = g[p].to_numpy(); mk = g["p_mkt"].to_numpy()
    tr, pnl = review.pnl(pm, y, g["qbid"].to_numpy(), g["qask"].to_numpy())
    return {"n": len(g), "calls": g["event_ticker"].nunique(), "yes": y.mean() if len(g) else np.nan,
            "mkt_mean": mk.mean() if len(g) else np.nan, "mod_mean": pm.mean() if len(g) else np.nan,
            "B_mkt": np.mean((mk-y)**2) if len(g) else np.nan, "B_mod": np.mean((pm-y)**2) if len(g) else np.nan,
            "trades": int(tr.sum()), "c_trade": np.nanmean(pnl)*100 if tr.any() else np.nan,
            "c_total": np.nansum(pnl)*100}
def table(x, by, p="p_v2wf", min_n=0):
    t = pd.DataFrame({k: summ(g, p) for k, g in x.groupby(by, observed=True)}).T
    t["d"] = t["B_mod"] - t["B_mkt"]
    return t[t.n >= min_n].round(4)
