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
                                                 and compares with the live model; --save stores it as a
                                                 challenger version (needs rmm_rw). Never changes the live
                                                 model: promotion is select kalshi.promote_model(N)
  python -m rmm models                           list model versions and which one is live
  python -m rmm weekly [--save] [--refit]        weekly health checks, live grading, calibration; --save
                                                 writes ops.*, --refit stores a challenger (both rmm_rw)

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
        version = paths.next_model_version()
    else:
        rows = db.run_query(paths.query("model_training"))
        version = refit.next_version()
    r = refit.run(rows, through=a.through)
    live = pd.DataFrame(db.run_query(paths.query("model_coefficients_live"))) if not a.input else None
    out = paths.model_dir(version, r.trained_through)
    out.mkdir(parents=True, exist_ok=True)
    r.coefficients.to_csv(out / "coefficients.csv", index=False)
    r.backtest.to_csv(out / "backtest.csv", index=False)
    cmp = refit.compare(r.coefficients, live) if live is not None and len(live) else None
    (out / "fit-report.md").write_text(refit.render_md(r, f"v{version}", cmp))
    print(f"wrote {out.relative_to(paths.ROOT)}/ (coefficients.csv, backtest.csv, fit-report.md)")
    if a.save:
        refit.save(r, version, a.notes or "")
        print(f"saved v{version} to kalshi.model_versions as a challenger")
    cs = {s.stage: s for s in r.stages}
    print(f"v{version} trained through {r.trained_through}: call-start Brier {cs['call_start'].brier_model:.4f} "
          f"vs price {cs['call_start'].brier_price:.4f}, k {cs['call_start'].k_final:.3f} / "
          f"{cs['early_24h'].k_final:.3f}")


def cmd_models(a: argparse.Namespace) -> None:
    rows = db.query("select version, status, trained_through::text, fitted_at::date::text as fitted, source, "
                    "metrics->'call_start'->>'brier_model' as brier, metrics->'call_start'->>'brier_price' as price, "
                    "metrics->'call_start'->>'k' as k from kalshi.model_versions order by version")
    print(f"{'ver':<4} {'status':<11} {'through':<11} {'fitted':<11} {'source':<15} brier   price   k")
    for r in rows:
        print(f"v{r['version']:<3} {r['status']:<11} {r['trained_through']:<11} {r['fitted']:<11} {r['source']:<15} "
              f"{r['brier'] or '–':<7} {r['price'] or '–':<7} {r['k'] or '–'}")
    print("Promote with: select kalshi.promote_model(N);  (database owner only)")


def cmd_weekly(a: argparse.Namespace) -> None:
    from . import weekly
    checks, metrics = weekly.run_checks(), weekly.run_metrics()
    print(weekly.render(checks, metrics))
    if a.save:
        print(f"saved as ops run {weekly.save(checks, metrics)}")
    if a.refit:
        from . import refit
        r = refit.run(db.run_query(paths.query("model_training")))
        version = refit.next_version()
        refit.save(r, version, "Weekly refit (challenger).")
        cs = {s.stage: s for s in r.stages}["call_start"]
        print(f"saved challenger v{version}: call-start Brier {cs.brier_model:.4f} vs price {cs.brier_price:.4f}, k {cs.k_final:.3f}")


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
    rf.add_argument("--save", action="store_true", help="store it as a challenger in kalshi.model_versions (rmm_rw)")
    rf.add_argument("--notes", help="note stored with the version")
    rf.set_defaults(fn=cmd_refit)
    wk = sub.add_parser("weekly", help="health checks, live grading and calibration")
    wk.add_argument("--save", action="store_true", help="write them to ops.* (rmm_rw)")
    wk.add_argument("--refit", action="store_true", help="also refit and store a challenger version (rmm_rw)")
    wk.set_defaults(fn=cmd_weekly)
    sub.add_parser("models", help="list model versions and which one is live").set_defaults(fn=cmd_models)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
