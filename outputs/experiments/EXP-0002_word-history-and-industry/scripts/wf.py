"""Walk-forward test: add cross-company word history and industry features to the fundamental model."""
import sys, numpy as np, pandas as pd
sys.path.insert(0, "/home/user/recursive-mentions-markets")
from scipy.special import logit
from rmm import refit, review
pd.set_option("display.width", 220)
d = pd.read_pickle("../train.pkl")
f = pd.read_pickle("features.pkl")[["ticker", "xc_n", "xc_rate", "xc_n30", "xc_rate30", "xc_age_days", "ind_n", "ind_rate", "indcat_rate", "indcat_n", "sector"]]
d = d.merge(f, on="ticker", how="left").reset_index(drop=True)
L = lambda p: logit(np.clip(p, 0.02, 0.98))
d["has_xc"] = (d.xc_n >= 3).astype(float);  d["lxc"] = np.where(d.has_xc > 0, L(d.xc_rate), 0)
d["listed30"] = (d.xc_n30 >= 3).astype(float); d["lxc30"] = np.where(d.listed30 > 0, L(d.xc_rate30), 0)
d["first_any"] = d.xc_age_days.isna().astype(float); d["age_yrs"] = (d.xc_age_days.fillna(0) / 365).clip(0, 2)
d["has_indcat"] = (d.indcat_n >= 10).astype(float); d["lindcat"] = np.where(d.has_indcat > 0, L(d.indcat_rate), 0)
d["has_ind"] = (d.ind_n >= 2).astype(float); d["lind"] = np.where(d.has_ind > 0, L(d.ind_rate.fillna(.5)), 0)
d["ext_lindcat"] = d.ext.astype(float) * d.lindcat
d["ext_listed30"] = d.ext.astype(float) * d.listed30
WORD = ["has_xc", "lxc", "listed30", "lxc30", "first_any", "age_yrs"]
IND = ["has_indcat", "lindcat", "ext_lindcat", "has_ind", "lind"]
VARIANTS = {"current model": [], "+ word history": WORD, "+ industry": IND, "+ both": WORD + IND + ["ext_listed30"]}
rows, preds = [], {}
for stage in ["early_24h", "call_start"]:
    Ff, Bf, pcol, _ = refit.STAGES[stage]
    bid, ask = review.QUOTES[stage]
    for name, extra in VARIANTS.items():
        sr = refit.walk_forward_spec(d, Ff + extra, Bf, pcol, stage)
        bt = sr.backtest.merge(d[["ticker", "call_date", "event_ticker", bid, ask, "won"]].rename(columns={"won": "y"}), on="ticker")
        preds[(stage, name)] = bt
        for lab, msk in [("all", bt.call_date >= "2000-01-01"), ("Sep–Oct", bt.call_date >= "2026-09-01")]:
            b = bt[msk]; y = b.y.to_numpy(float); p = b.p_model.to_numpy(float)
            tr, pnl = review.pnl(p, y, b[bid].to_numpy(float), b[ask].to_numpy(float))
            rows.append({"stage": stage, "variant": name, "period": lab, "markets": len(b), "brier_model": np.mean((p - y) ** 2),
                         "brier_market": np.mean((b.price.to_numpy(float) - y) ** 2), "trades": int(tr.sum()),
                         "c_trade": np.nanmean(pnl) * 100, "c_total": np.nansum(pnl) * 100})
r = pd.DataFrame(rows)
print(r.round(4).to_string(index=False))
pd.to_pickle(preds, "wf_preds.pkl"); d.to_pickle("train_feats.pkl")
