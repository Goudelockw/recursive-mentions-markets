import sys, numpy as np, pandas as pd
sys.path.insert(0, "/home/user/recursive-mentions-markets")
from rmm import refit, review
from ablate import score, d
rng = np.random.default_rng(5)
VARIANTS = {"A: drop r4, corpus_rare, analysts_n, filing_said (fund.)": ["r4", "corpus_rare", "analysts_n", "filing_said"],
            "B: A + year-ago pair + ext/politics": ["r4", "corpus_rare", "analysts_n", "filing_said", "said_yoy", "has_yoy", "ext", "politics"],
            "C: B + story0 (hindsight-labeled)": ["r4", "corpus_rare", "analysts_n", "filing_said", "said_yoy", "has_yoy", "ext", "politics", "story0"]}
rows = []
for stage in ["early_24h", "call_start"]:
    Ff, Bf, pcol, _ = refit.STAGES[stage]
    base = score(refit.walk_forward_spec(d, Ff, Bf, pcol, stage), stage)
    for name, drop in VARIANTS.items():
        new = score(refit.walk_forward_spec(d, [t for t in Ff if t not in drop], Bf, pcol, stage), stage)
        m = base[["ticker", "event_ticker", "call_date", "sq", "pnl"]].merge(new[["ticker", "sq", "pnl"]], on="ticker", suffixes=("_b", "_n"))
        for lab, msk in [("all", m.call_date.notna()), ("2025", m.call_date < "2026-01-01"), ("Jan–Aug 2026", (m.call_date >= "2026-01-01") & (m.call_date < "2026-09-01")), ("Sep–Oct", m.call_date >= "2026-09-01")]:
            x = m[msk]; g = x.assign(dsq=x.sq_n - x.sq_b).groupby("event_ticker").dsq.sum(); ids = np.arange(len(g))
            better = np.mean([g.iloc[rng.choice(ids, len(ids))].sum() < 0 for _ in range(1000)])
            rows.append({"stage": stage, "variant": name[:2], "period": lab, "markets": len(x), "brier_now": x.sq_b.mean(), "brier_pruned": x.sq_n.mean(),
                         "pruned_better_in": better, "cents_now": x.pnl_b.sum() * 100, "cents_pruned": x.pnl_n.sum() * 100})
pd.set_option("display.width", 220)
print(pd.DataFrame(rows).round(4).to_string(index=False))
