"""Read-only access to the kalshi Neon database."""
from __future__ import annotations

import json
import os
from decimal import Decimal
from pathlib import Path


def run_query(path: Path) -> list[dict]:
    """Run one .sql file and return its rows as dicts. Needs DATABASE_URL (the rmm_ro role).

    Transport: Postgres wire protocol, or Neon's SQL-over-HTTPS endpoint, which works through
    the HTTPS proxy of a Claude cloud session where port 5432 is unreachable. RMM_DB_TRANSPORT
    picks one; the default is https when an HTTPS proxy is set, postgres otherwise.
    """
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise SystemExit("DATABASE_URL is not set; run the queries through the Neon connector "
                         "and pass the results with --board / --preflight instead")
    sql = path.read_text().strip().rstrip(";")
    default = "https" if os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy") else "postgres"
    if os.environ.get("RMM_DB_TRANSPORT", default) == "https":
        return [_plain(r) for r in _query_https(url, sql)]

    import psycopg
    from psycopg.rows import dict_row

    with psycopg.connect(url, row_factory=dict_row) as c:
        c.execute("set transaction read only")
        return [_plain(r) for r in c.execute(sql).fetchall()]


def _query_https(url: str, sql: str) -> list[dict]:
    """Neon's HTTP query endpoint: POST https://<endpoint host>/sql. Numerics come back as text."""
    import urllib.request
    from urllib.parse import urlsplit

    req = urllib.request.Request(
        f"https://{urlsplit(url).hostname}/sql",
        data=json.dumps({"query": sql, "params": []}).encode(),
        headers={"Neon-Connection-String": url, "Content-Type": "application/json"},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.load(r)["rows"]
    except urllib.error.HTTPError as e:
        raise SystemExit(f"Neon HTTP query failed ({e.code}): {e.read().decode()[:500]}") from None


def load_rows(path: Path) -> list[dict]:
    """Rows saved as JSON: a list of objects, or the Neon connector's
    [{"json_agg": [...]}] wrapper."""
    data = json.loads(path.read_text())
    if len(data) == 1 and isinstance(data[0], dict) and len(data[0]) == 1:
        (only,) = data[0].values()
        if isinstance(only, list):
            data = only
    return [_plain(r) for r in data]


INT_COLS = {"avoid_points", "no_hist", "markets_on_call", "max_hours", "bytes", "reads", "live_rows"}
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
