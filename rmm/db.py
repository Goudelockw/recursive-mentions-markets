"""Read-only access to the kalshi Neon database."""
from __future__ import annotations

import json
import os
from decimal import Decimal
from pathlib import Path


def run_query(path: Path) -> list[dict]:
    """Run one .sql file and return its rows as dicts. Needs DATABASE_URL."""
    import psycopg
    from psycopg.rows import dict_row

    url = os.environ.get("DATABASE_URL")
    if not url:
        raise SystemExit("DATABASE_URL is not set; run the queries through the Neon connector "
                         "and pass the results with --board / --preflight instead")
    with psycopg.connect(url, row_factory=dict_row) as c:
        c.execute("set transaction read only")
        return [_plain(r) for r in c.execute(path.read_text()).fetchall()]


def load_rows(path: Path) -> list[dict]:
    """Rows saved as JSON: a list of objects, or the Neon connector's
    [{"json_agg": [...]}] wrapper."""
    data = json.loads(path.read_text())
    if len(data) == 1 and isinstance(data[0], dict) and len(data[0]) == 1:
        (only,) = data[0].values()
        if isinstance(only, list):
            data = only
    return [_plain(r) for r in data]


INT_COLS = {"avoid_points", "no_hist", "markets_on_call", "max_hours"}
FLOAT_COLS = {"hours_since_ok"}


def _plain(row: dict) -> dict:
    """Decimals and numeric strings (the Neon connector returns numerics as text) to numbers."""
    out = {}
    for k, v in row.items():
        if isinstance(v, Decimal):
            v = float(v)
        if v is not None and k in INT_COLS:
            v = int(float(v))
        elif isinstance(v, str) and (k in FLOAT_COLS or k.endswith(("_c", "_pct", "_h"))):
            v = float(v)
        out[k] = v
    return out
