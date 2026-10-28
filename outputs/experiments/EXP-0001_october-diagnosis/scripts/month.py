from lib import *
for st in ["call_start", "early_24h"]:
    x = a[a.stage == st].copy(); x["m"] = x["call_date"].dt.strftime("%Y-%m")
    print(st); print(table(x, "m", min_n=30).tail(14))
