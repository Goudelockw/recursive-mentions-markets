"""Access to the kalshi Neon database: reads as rmm_ro, and the few writes this repo makes as rmm_rw."""
from __future__ import annotations

import json
import os
from decimal import Decimal
from pathlib import Path


def run_query(path: Path) -> list[dict]:
    """Run one read-only .sql file and return its rows as dicts. Needs DATABASE_URL."""
    return query(path.read_text())


def query(sql: str, params: list | None = None) -> list[dict]:
    """One statement; placeholders are $1, $2, ... Read-only unless it is part of transaction()."""
    return [_plain(r) for r in _run([(sql, params or [])], read_only=True)[0]]


def transaction(statements: list[tuple[str, list]]) -> list[list[dict]]:
    """Several statements in one transaction (all or nothing). Pass rows as one JSON parameter and
    unpack them in SQL with jsonb_to_recordset($1::jsonb), so it works the same over both transports.
    Needs a DATABASE_URL whose role may write (rmm_rw); rmm_ro is refused by Postgres."""
    return [[_plain(r) for r in rows] for rows in _run(statements, read_only=False)]


def _url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise SystemExit("DATABASE_URL is not set; run the queries through the Neon connector "
                         "and pass the results with --board / --preflight instead")
    return url


def _run(statements: list[tuple[str, list]], read_only: bool) -> list[list[dict]]:
    """Transport: Postgres wire protocol, or Neon's SQL-over-HTTPS endpoint, which works through
    the HTTPS proxy of a Claude cloud session where port 5432 is unreachable. RMM_DB_TRANSPORT
    picks one; the default is https when an HTTPS proxy is set, postgres otherwise."""
    url = _url()
    statements = [(sql.strip().rstrip(";"), params) for sql, params in statements]
    default = "https" if os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy") else "postgres"
    if os.environ.get("RMM_DB_TRANSPORT", default) == "https":
        return _run_https(url, statements, read_only)

    import re

    import psycopg
    from psycopg.rows import dict_row

    out = []
    with psycopg.connect(url, row_factory=dict_row) as c:
        if read_only:
            c.execute("set transaction read only")
        for sql, params in statements:
            cur = c.execute(re.sub(r"\$\d+", "%s", sql.replace("%", "%%")), params)
            out.append(cur.fetchall() if cur.description else [])
    return out


def _run_https(url: str, statements: list[tuple[str, list]], read_only: bool) -> list[list[dict]]:
    """POST https://<endpoint host>/sql: one query, or a batch run as one transaction.
    Numerics come back as text."""
    import urllib.request
    from urllib.parse import urlsplit

    headers = {"Neon-Connection-String": url, "Content-Type": "application/json"}
    if len(statements) == 1:
        body = {"query": statements[0][0], "params": statements[0][1]}
    else:
        body = {"queries": [{"query": q, "params": p} for q, p in statements]}
        headers |= {"Neon-Batch-Isolation-Level": "ReadCommitted",
                    "Neon-Batch-Read-Only": "true" if read_only else "false"}
    req = urllib.request.Request(f"https://{urlsplit(url).hostname}/sql", data=json.dumps(body, default=str).encode(),
                                 headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            res = json.load(r)
    except urllib.error.HTTPError as e:
        raise SystemExit(f"Neon HTTP query failed ({e.code}): {e.read().decode()[:500]}") from None
    return [x["rows"] for x in res["results"]] if "results" in res else [res["rows"]]


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
