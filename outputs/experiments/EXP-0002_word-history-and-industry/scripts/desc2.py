import numpy as np, pandas as pd
pd.set_option("display.width", 220); pd.set_option("display.max_rows", 100)
x = pd.read_pickle("joined24.pkl")
x["scope"] = np.where(x.ext.astype(float) > 0, "external", "own business")
x["period"] = np.where(x.call_date >= "2026-09-01", "Sep–Oct", "before")
def tab(d, by, min_n=0):
    g = d.groupby(by, observed=True).agg(n=("y", "size"), said=("y", "mean"), market=("p_mkt", "mean"), model=("p_v2wf", "mean"))
    g["said−market"] = g.said - g.market; g["said−model"] = g.said - g.model
    return g[g.n >= min_n].round(3)
e = x[x.scope == "external"].copy()
e["hot"] = np.where(e.xc_n30 >= 3, np.where(e.xc_rate30 > 0.6, "hot (said at most cos, last 30d)", "listed, said <60%"), "quiet last 30d")
print("== External words, by recent cross-company activity, before vs Sep–Oct"); print(tab(e, ["period", "hot"]).to_string())
print("\n== By sector (all periods, n>=60)"); print(tab(x, ["sector"], 60).sort_values("said−model").to_string())
print("\n== Sector x scope, biggest model misses (n>=40)")
t = tab(x, ["sector", "scope"], 40); print(t.reindex(t["said−model"].abs().sort_values(ascending=False).index).head(12).to_string())
