"""Point-in-time cross-company word history and industry features for every settled mentions market."""
import re
from collections import defaultdict
import numpy as np, pandas as pd

S = "/tmp/claude-0/-home-user/85a95fd0-89d0-5eac-ac11-88fd8e926ac6/scratchpad/xf/"
SECTORS = [  # (name, SIC ranges)
    ("Healthcare", [(2830, 2836), (3841, 3851), (8000, 8099), (5047, 5047), (5122, 5122), (6324, 6324)]),
    ("Telecom & media", [(4800, 4899), (2700, 2799), (7810, 7849), (7900, 7999)]),
    ("Banks & finance", [(6000, 6299), (6700, 6799)]),
    ("Insurance", [(6300, 6323), (6325, 6499)]),
    ("Software & internet", [(7370, 7379)]),
    ("Semis & hardware", [(3570, 3579), (3660, 3679), (3820, 3829)]),
    ("Aerospace & defense", [(3720, 3729), (3760, 3769), (3812, 3812)]),
    ("Autos & machinery", [(3510, 3569), (3580, 3599), (3700, 3719), (3730, 3759), (3790, 3799)]),
    ("Transport", [(4000, 4799)]),
    ("Restaurants", [(5812, 5813)]),
    ("Retail", [(5200, 5811), (5814, 5999)]),
    ("Consumer goods", [(2000, 2399), (2840, 2844), (3140, 3149), (3940, 3949)]),
    ("Energy & utilities", [(1300, 1399), (2900, 2999), (4900, 4999)]),
]

# SIC 7389 ("Business Services, NEC") and missing codes lump unlike companies together
OVERRIDES = {**dict.fromkeys(["V", "MA", "PYPL"], "Payments & fintech"),
             **dict.fromkeys(["UBER", "LYFT", "DASH", "GRAB", "ABNB", "EBAY", "MELI", "ALIBABA"], "Internet platforms"),
             **dict.fromkeys(["ACN", "ADOBE"], "Software & internet"), "MCO": "Banks & finance",
             **dict.fromkeys(["HLT", "CAR"], "Travel & leisure"), "NKE": "Consumer goods", "CALM": "Consumer goods",
             "DPZ": "Restaurants", "GEV": "Energy & utilities", **dict.fromkeys(["VSCO", "ARITZIA"], "Retail"),
             "AC": "Transport", "EA": "Telecom & media", "TOL": "Other"}


def sector(sic) -> str:
    try:
        s = int(float(sic))
    except (TypeError, ValueError):
        return "Unknown"
    for name, rng in SECTORS:
        if any(lo <= s <= hi for lo, hi in rng):
            return name
    return "Other"

def aliases(word: str) -> frozenset:
    w = re.sub(r"\(.*?\)", "", str(word).lower())
    return frozenset(a.strip(" .'\"") for a in w.split("/") if a.strip(" .'\""))

def build(m: pd.DataFrame, c: pd.DataFrame) -> pd.DataFrame:
    m = m.copy()
    m["date"] = pd.to_datetime(m["call_date"].fillna(m["close_time"].str[:10]))
    m["y"] = (m["result"] == "yes").astype(int)
    m["sector"] = m["symbol"].map(OVERRIDES).fillna(m["symbol"].map(c.set_index("symbol")["sic"].map(sector))).fillna("Unknown")
    m["al"] = m["word"].map(aliases)
    m["cat"] = m["word_category"].fillna("unlabeled")
    by_alias = defaultdict(list)
    for i, r in enumerate(m.itertuples()):
        for a in r.al:
            by_alias[a].append(i)
    dates, syms, ys, secs = list(m["date"]), m["symbol"].to_numpy(), m["y"].to_numpy(), m["sector"].to_numpy()
    # sector x category history, for the industry-category rate
    out = []
    for i, r in enumerate(m.itertuples()):
        prior = {j for a in r.al for j in by_alias[a]}
        prior = [j for j in prior if dates[j] < dates[i] and syms[j] != syms[i]]
        n = len(prior); yes = int(ys[prior].sum()) if n else 0
        recent = [j for j in prior if (dates[i] - dates[j]).days <= 30]
        same = [j for j in prior if secs[j] == secs[i]]
        first = min((dates[j] for j in prior), default=None)
        out.append({"xc_n": n, "xc_yes": yes, "xc_rate": (yes + 1) / (n + 2),
                    "xc_age_days": (dates[i] - first).days if first is not None else np.nan,
                    "xc_n30": len(recent), "xc_rate30": (ys[recent].sum() + 1) / (len(recent) + 2),
                    "ind_n": len(same), "ind_rate": (ys[same].sum() + 1) / (len(same) + 2) if same else np.nan})
    f = pd.concat([m.reset_index(drop=True), pd.DataFrame(out)], axis=1)
    # sector x word-category YES rate from earlier calls of other companies (point in time)
    f = f.sort_values("date").reset_index(drop=True)
    rates = []
    hist = defaultdict(list)  # (sector, cat) -> list of (date, symbol, y)
    for r in f.itertuples():
        h = [x for x in hist[(r.sector, r.cat)] if x[0] < r.date and x[1] != r.symbol]
        rates.append(((sum(x[2] for x in h) + 1) / (len(h) + 2), len(h)))
        hist[(r.sector, r.cat)].append((r.date, r.symbol, r.y))
    f["indcat_rate"], f["indcat_n"] = [x[0] for x in rates], [x[1] for x in rates]
    return f

if __name__ == "__main__":
    f = build(pd.read_pickle(S + "markets.pkl"), pd.read_pickle(S + "companies.pkl"))
    f.to_pickle(S + "features.pkl")
    print(f.shape); print(f.sector.value_counts().to_string())
    print(f[["xc_n", "xc_age_days", "xc_rate", "ind_n", "indcat_n"]].describe().round(2).to_string())
