from lib import *
from where import trades
t = trades(a[(a.stage == "call_start") & (a.call_date >= "2026-09-01")])
j = t[t.move24.astype(float) > 0.3].copy()
j["sym"] = j.symbol
print(j[["sym", "word", "call_date", "bid_24h", "ask_24h", "bid", "ask", "p_v2wf", "y", "filing_said", "rel_head", "pnl"]].sort_values("call_date").to_string())
j[["ticker", "event_ticker"]].to_csv("jump_tickers.csv", index=False)
print("filing_said counts:", j.filing_said.value_counts(dropna=False).to_dict())
