"""Company sectors: SIC code ranges grouped into about fifteen sectors, plus hand fixes.

SIC 7389 ("Business Services, NEC") lumps Visa, Uber and Accenture together, and a few
companies have no SIC code, so OVERRIDES places those by hand.
"""
from __future__ import annotations

SECTORS = [  # (name, inclusive SIC ranges)
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

OVERRIDES = {**dict.fromkeys(["V", "MA", "PYPL"], "Payments & fintech"),
             **dict.fromkeys(["UBER", "LYFT", "DASH", "GRAB", "ABNB", "EBAY", "MELI", "ALIBABA"], "Internet platforms"),
             **dict.fromkeys(["ACN", "ADOBE"], "Software & internet"), "MCO": "Banks & finance",
             **dict.fromkeys(["HLT", "CAR"], "Travel & leisure"), "NKE": "Consumer goods", "CALM": "Consumer goods",
             "DPZ": "Restaurants", "GEV": "Energy & utilities", **dict.fromkeys(["VSCO", "ARITZIA"], "Retail"),
             "AC": "Transport", "EA": "Telecom & media", "TOL": "Other"}


def from_sic(sic) -> str:
    try:
        s = int(float(sic))
    except (TypeError, ValueError):
        return "Unknown"
    for name, ranges in SECTORS:
        if any(lo <= s <= hi for lo, hi in ranges):
            return name
    return "Other"


def sector(symbol: str, sic) -> str:
    return OVERRIDES.get(symbol) or from_sic(sic)
