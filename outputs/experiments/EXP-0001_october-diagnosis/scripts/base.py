import numpy as np, pandas as pd, sys
sys.path.insert(0, "/home/user/recursive-mentions-markets")
from scipy.special import expit
from rmm import review, refit
S = "/tmp/claude-0/-home-user/85a95fd0-89d0-5eac-ac11-88fd8e926ac6/scratchpad/"
d = pd.read_pickle(S + "train.pkl")
co1 = review.coefficients(1); bt2 = review.backtest(2)
rows = []
for stage, (bid, ask) in review.QUOTES.items():
    pcol = refit.STAGES[stage][2]
    x = d[d[pcol].notna()].reset_index(drop=True).copy()
    x["stage"] = stage
    x["p_v1"] = review.score(co1, x, stage)
    x["p_v2wf"] = x["ticker"].map(bt2[bt2["stage"] == stage].set_index("ticker")["p"])
    x["p_mkt"] = refit.clip((x[bid].astype(float) + x[ask].astype(float)) / 2)
    x["qbid"], x["qask"] = x[bid].astype(float), x[ask].astype(float)
    rows.append(x)
a = pd.concat(rows, ignore_index=True)
a["y"] = a["won"].astype(float)
a.to_pickle(S + "oct/all.pkl")
print(a.groupby("stage").size())
