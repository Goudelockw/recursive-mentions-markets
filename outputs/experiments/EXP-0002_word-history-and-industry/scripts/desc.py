import numpy as np, pandas as pd
pd.set_option("display.width", 220)
f = pd.read_pickle("features.pkl")
a = pd.read_pickle("../oct/all.pkl")
x = a[a.stage == "early_24h"].merge(f.drop(columns=["event_ticker", "symbol", "word", "call_date", "y", "result"]), on="ticker", how="left")
x = x[x.p_v2wf.notna()]
x.to_pickle("joined24.pkl")
x["scope"] = np.where(x.ext.astype(float) > 0, "external", "own business")
def tab(by):
    g = x.groupby(by, observed=True).agg(n=("y", "size"), said=("y", "mean"), market=("p_mkt", "mean"), model=("p_v2wf", "mean"))
    g["said−market"] = g.said - g.market; g["said−model"] = g.said - g.model
    return g.round(3)
x["age"] = pd.cut(x.xc_age_days.fillna(-1), [-2, 0, 30, 90, 180, 365, 9999], labels=["first time anywhere", "≤30d", "31–90d", "91–180d", "181–365d", ">1 year"])
print("== by how long ago the word first appeared at ANOTHER company"); print(tab(["scope", "age"]).to_string())
x["xc_bucket"] = pd.cut(x.xc_rate.where(x.xc_n >= 3), [0, .25, .45, .65, 1], labels=["said ≤25% elsewhere", "25–45%", "45–65%", ">65%"])
print("\n== by how often it was said at other companies (3+ earlier markets)"); print(tab(["scope", "xc_bucket"]).to_string())
x["hot"] = np.where(x.xc_n30 >= 3, np.where(x.xc_rate30 > 0.6, "hot: said at most companies last 30d", "listed a lot, said <60%"), "not listed much last 30d")
print("\n== last 30 days at other companies"); print(tab(["scope", "hot"]).to_string())
