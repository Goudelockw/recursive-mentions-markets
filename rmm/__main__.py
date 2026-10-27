"""CLI entry point.

  python -m rmm trade-sheet                      query Neon (DATABASE_URL) and write today's sheet
  python -m rmm trade-sheet --board B.json --preflight P.json
                                                 render from saved query results instead (the
                                                 Neon connector path the Trade Sheet task uses)
  python -m rmm trade-sheet ... --date YYYY-MM-DD --now "YYYY-MM-DD HH:MM"
                                                 override the sheet date / generated time (tests)

  python -m rmm cost-report                      weekly cost breakdown: job runs and table sizes from
                                                 Neon (DATABASE_URL), billed usage from the Neon API
                                                 (NEON_API_KEY, optional); writes
                                                 outputs/weekly/YYYY-Www_cost-report.md and appends
                                                 outputs/costs/neon-usage.csv

  python -m rmm refit [--through YYYY-MM-DD]     Python port of refit_models.R (same results): walk-forward
                                                 backtest, k, final fit; writes outputs/models/vN_<date>/
                                                 and compares with kalshi.model_coefficients. Never writes
                                                 to the database; promotion is a separate step

trade-sheet writes outputs/trade-sheets/YYYY-MM/YYYY-MM-DD_trade-sheet.{md,csv,html} and prints the
status line, so a scheduled task can pass it straight to the notification.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from . import cost_report, db, paths, trade_sheet

ET = ZoneInfo("America/New_York")


def cmd_trade_sheet(a: argparse.Namespace) -> None:
    if a.board:
        board, pre = db.load_rows(Path(a.board)), db.load_rows(Path(a.preflight)) if a.preflight else []
    else:
        board = db.run_query(paths.query("trade_sheet"))
        pre = db.run_query(paths.query("trade_sheet_preflight"))
    now = datetime.strptime(a.now, "%Y-%m-%d %H:%M") if a.now else datetime.now(ET).replace(tzinfo=None)
    day = date.fromisoformat(a.date) if a.date else now.date()
    sheet = trade_sheet.build(board, pre, day, now)
    for ext, text in (("md", trade_sheet.render_md(sheet)), ("csv", trade_sheet.render_csv(sheet)),
                      ("html", trade_sheet.render_html(sheet))):
        p = paths.trade_sheet(day, ext)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
        print(f"wrote {p.relative_to(paths.ROOT)}")
    print(f"{sheet.status} · {sheet.headline}")


def cmd_cost_report(a: argparse.Namespace) -> None:
    if a.runs:
        runs, rels = db.load_rows(Path(a.runs)), db.load_rows(Path(a.relations))
    else:
        runs = db.run_query(paths.query("cost_job_runs"))
        rels = db.run_query(paths.query("cost_relations"))
    now = cost_report.utcnow()
    usage = None if a.no_api else cost_report.neon_usage(now)
    ledger_path = paths.costs_ledger()
    report = cost_report.build(runs, rels, usage, cost_report.read_ledger(ledger_path), now)
    out = paths.weekly(now.date(), "cost-report")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(cost_report.render_md(report))
    print(f"wrote {out.relative_to(paths.ROOT)}")
    if usage:
        cost_report.append_ledger(ledger_path, usage)
        print(f"appended {ledger_path.relative_to(paths.ROOT)}")
    week = report.week
    head = (f"${week['compute_usd']:.2f} compute this week, awake {week['awake_pct']:.0f}%" if week
            else f"job runs keep Neon awake ~{report.awake_hours:.0f}h/week")
    print(f"{head} · {len(report.suggestions)} suggestions")


def cmd_refit(a: argparse.Namespace) -> None:
    import pandas as pd

    from . import refit
    if a.input:
        rows = pd.read_json(a.input) if a.input.endswith(".json") else pd.read_csv(a.input)
    else:
        rows = db.run_query(paths.query("model_training"))
    r = refit.run(rows, through=a.through)
    live = pd.DataFrame(db.run_query(paths.query("model_coefficients_live"))) if not a.input else None
    version = paths.next_model_version()
    out = paths.model_dir(version, r.trained_through)
    out.mkdir(parents=True, exist_ok=True)
    r.coefficients.to_csv(out / "coefficients.csv", index=False)
    r.backtest.to_csv(out / "backtest.csv", index=False)
    cmp = refit.compare(r.coefficients, live) if live is not None and len(live) else None
    (out / "fit-report.md").write_text(refit.render_md(r, f"v{version}", cmp))
    print(f"wrote {out.relative_to(paths.ROOT)}/ (coefficients.csv, backtest.csv, fit-report.md)")
    cs = {s.stage: s for s in r.stages}
    print(f"v{version} trained through {r.trained_through}: call-start Brier {cs['call_start'].brier_model:.4f} "
          f"vs price {cs['call_start'].brier_price:.4f}, k {cs['call_start'].k_final:.3f} / "
          f"{cs['early_24h'].k_final:.3f}")


def main() -> None:
    ap = argparse.ArgumentParser(prog="rmm")
    sub = ap.add_subparsers(dest="cmd", required=True)
    ts = sub.add_parser("trade-sheet", help="today's trade sheet")
    ts.add_argument("--board", help="saved trade_sheet.sql results (JSON)")
    ts.add_argument("--preflight", help="saved trade_sheet_preflight.sql results (JSON)")
    ts.add_argument("--date", help="sheet date, default today in New York")
    ts.add_argument("--now", help="generated-at time in New York, default now")
    ts.set_defaults(fn=cmd_trade_sheet)
    cr = sub.add_parser("cost-report", help="weekly Neon cost breakdown and suggestions")
    cr.add_argument("--runs", help="saved cost_job_runs.sql results (JSON)")
    cr.add_argument("--relations", help="saved cost_relations.sql results (JSON)")
    cr.add_argument("--no-api", action="store_true", help="skip the Neon API even if NEON_API_KEY is set")
    cr.set_defaults(fn=cmd_cost_report)
    rf = sub.add_parser("refit", help="refit the four mentions models as a challenger (no database writes)")
    rf.add_argument("--through", help="only calls on or before this date (YYYY-MM-DD)")
    rf.add_argument("--input", help="v_model_training as CSV or JSON instead of querying Neon")
    rf.set_defaults(fn=cmd_refit)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
