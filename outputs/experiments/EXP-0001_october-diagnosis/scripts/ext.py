import contextlib, io
with contextlib.redirect_stdout(io.StringIO()):
    from where import trades
from lib import *
for lab, lo, hi in [("2025 H2", "2025-07-01", "2026-01-01"), ("Jan-Apr", "2026-01-01", "2026-05-01"), ("May-Aug", "2026-05-01", "2026-09-01"), ("Sep-Oct", "2026-09-01", "2026-11-01")]:
    t = trades(a[(a.stage == "call_start") & (a.call_date >= lo) & (a.call_date < hi)])
    t["jump"] = np.where(t.move24.astype(float) > 0.3, "late jump", "no jump")
    t["scope"] = np.where(t.ext.astype(float) > 0, "external", "own business")
    t = t[t.side == "NO"]
    g = t.groupby(["jump", "scope"]).agg(trades=("pnl","size"), c_trade=("pnl","mean"), yes=("y","mean"), mkt=("p_mkt","mean"))
    print(f"\n== NO trades at call start, {lab}"); print(g.round(3).to_string())
