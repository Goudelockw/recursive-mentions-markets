from lib import *
def trades(x, p="p_v2wf"):
    x = x[x[p].notna()].copy()
    pm, y, b, k = x[p].to_numpy(), x["y"].to_numpy(), x["qbid"].to_numpy(), x["qask"].to_numpy()
    tr, pnl = review.pnl(pm, y, b, k)
    x["traded"], x["pnl"] = tr, pnl*100
    x["side"] = np.where(pm > (b+k)/2, "YES", "NO")
    return x[x.traded]
for st in ["call_start", "early_24h"]:
    for lab, lo, hi in [("Sep-Oct", "2026-09-01", "2026-11-01"), ("Jan-Aug", "2026-01-01", "2026-09-01")]:
        t = trades(a[(a.stage == st) & (a.call_date >= lo) & (a.call_date < hi)])
        t["mkt_bucket"] = pd.cut(t.p_mkt, [0, .2, .4, .6, .8, 1])
        t["in_release"] = np.where(t.filing_said.astype(float) > 0, "word in release", "not in release")
        print(f"\n== {st} {lab}: {len(t)} trades, {t.pnl.mean():+.1f}c")
        for col in ["side", "mkt_bucket", "in_release"]:
            g = t.groupby(col, observed=True).agg(trades=("pnl", "size"), c_trade=("pnl", "mean"), yes=("y", "mean"), mkt=("p_mkt", "mean"), model=("p_v2wf", "mean"))
            print(g.round(3).to_string())
