from lib import *
from where import trades
import contextlib, io
for lab, lo, hi in [("Sep-Oct", "2026-09-01", "2026-11-01"), ("Jan-Aug", "2026-01-01", "2026-09-01")]:
    t = trades(a[(a.stage == "call_start") & (a.call_date >= lo) & (a.call_date < hi)])
    t["mv"] = pd.cut(t.move24.astype(float), [-9, -0.3, -0.05, 0.05, 0.3, 9], labels=["fell a lot", "fell", "flat", "rose", "rose a lot"])
    print(f"\n== call_start {lab}, by price move from 24h to call start (log-odds)")
    print(t.groupby("mv", observed=True).agg(trades=("pnl","size"), c_trade=("pnl","mean"), yes=("y","mean"), mkt=("p_mkt","mean"), model=("p_v2wf","mean"), side_no=("side", lambda s:(s=="NO").mean())).round(3).to_string())
t = trades(a[(a.stage == "call_start") & (a.call_date >= "2026-09-01")])
g = t.groupby("event_ticker").agg(trades=("pnl","size"), c_total=("pnl","sum"), c_trade=("pnl","mean"), yes=("y","mean"), mkt=("p_mkt","mean"), date=("call_date","first")).sort_values("c_total")
print("\n== call_start Sep-Oct by call (worst first)"); print(g.round(2).head(12).to_string()); print("...best:"); print(g.round(2).tail(5).to_string())
print("\nshare of total loss from worst 5 calls:", round(g.c_total.head(5).sum() / g.c_total.sum(), 2), " total c:", round(g.c_total.sum()))
