import contextlib, io
with contextlib.redirect_stdout(io.StringIO()):
    from where import trades
from lib import *
for lab, lo, hi in [("Jan-Aug", "2026-01-01", "2026-09-01"), ("Sep-Oct", "2026-09-01", "2026-11-01")]:
    t = trades(a[(a.stage == "early_24h") & (a.call_date >= lo) & (a.call_date < hi)])
    t["scope"] = np.where(t.ext.astype(float) > 0, "external", "own business")
    print(f"\n== 24h entry {lab}"); print(t.groupby(["scope", "side"]).agg(trades=("pnl","size"), c_trade=("pnl","mean"), yes=("y","mean"), mkt=("p_mkt","mean")).round(3).to_string())
# what a "don't fade late jumps at call start" rule would have done
for lab, lo, hi in [("2025 H2", "2025-07-01", "2026-01-01"), ("Jan-Aug", "2026-01-01", "2026-09-01"), ("Sep-Oct", "2026-09-01", "2026-11-01")]:
    t = trades(a[(a.stage == "call_start") & (a.call_date >= lo) & (a.call_date < hi)])
    skip = (t.side == "NO") & (t.move24.astype(float) > 0.3)
    print(f"call start {lab}: all {len(t)} @ {t.pnl.mean():+.1f}c; skipping {skip.sum()} late-jump fades -> {(~skip).sum()} @ {t[~skip].pnl.mean():+.1f}c (skipped ones averaged {t[skip].pnl.mean():+.1f}c)")
