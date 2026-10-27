"""Weekly cost report: what the pipeline costs in Neon, which jobs drive it, and what to change.

Two sources:
  - the database itself (rmm_ro): every pipeline run in the last 7 days, and every table's size and
    read count;
  - the Neon API, when NEON_API_KEY is set: the billing period's compute and active time and the
    compute settings. Each run appends a row to outputs/costs/neon-usage.csv, so the week's usage
    is the difference from the previous row.

Neon bills compute for every second the database is awake, at its current size, and suspends it
after SUSPEND_MIN minutes without queries. So the report models each job run as keeping the
database awake from its start until SUSPEND_MIN after it ends, and shows which jobs alone would keep
it awake longest. Rule-based suggestions follow; the Sunday task adds its own judgment on top.
"""
from __future__ import annotations

import csv
import json
import os
import re
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_ID = "mute-sun-75653323"
COMPUTE_RATE = 0.106      # $ per CU-hour, Neon Launch
STORAGE_RATE = 0.35       # $ per GB-month, Neon Launch
SUSPEND_MIN = 5           # Neon's default scale-to-zero delay
CUT_OFF_RUN_MIN = 1       # a run with no finished_at (crashed or redeployed) counts as this long
LEFTOVER_NAME = re.compile(r"((_old\d*|_bak|_backup|_tmp|_snapshot_?\d+)$|^wc_snapshot)", re.I)
BIG_TABLE_BYTES = 500 * 1024**2


@dataclass
class JobCost:
    job: str
    runs: int
    run_hours: float       # time spent running
    awake_hours: float     # hours this job alone would keep the database awake
    failed: int
    cut_off: int


@dataclass
class Usage:
    taken_at: datetime
    period_start: str
    compute_seconds: int
    active_seconds: int
    storage_bytes: int
    min_cu: float | None = None
    max_cu: float | None = None
    suspend_seconds: int | None = None


@dataclass
class Report:
    now: datetime
    jobs: list[JobCost]
    awake_hours: float                  # all jobs together
    relations: list[dict]
    usage: Usage | None
    prev: Usage | None
    suggestions: list[str] = field(default_factory=list)

    @property
    def week(self) -> dict | None:
        """This week's compute and active hours from the ledger, when there is a previous row in
        the same billing period."""
        if not self.usage or not self.prev or self.prev.period_start != self.usage.period_start:
            return None
        days = (self.usage.taken_at - self.prev.taken_at).total_seconds() / 86400
        cu_h = (self.usage.compute_seconds - self.prev.compute_seconds) / 3600
        act_h = (self.usage.active_seconds - self.prev.active_seconds) / 3600
        return {"days": days, "cu_hours": cu_h, "active_hours": act_h,
                "awake_pct": 100 * act_h / (days * 24) if days else 0,
                "avg_cu": cu_h / act_h if act_h else 0, "compute_usd": cu_h * COMPUTE_RATE,
                "monthly_usd": cu_h * COMPUTE_RATE * 30.4 / days if days else 0}


# ---------------------------------------------------------------- inputs

def neon_usage(now: datetime) -> Usage | None:
    key = os.environ.get("NEON_API_KEY")
    if not key:
        return None

    def get(path: str) -> dict:
        req = urllib.request.Request(f"https://console.neon.tech/api/v2{path}",
                                     headers={"Authorization": f"Bearer {key}", "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)

    p = get(f"/projects/{PROJECT_ID}")["project"]
    eps = get(f"/projects/{PROJECT_ID}/endpoints").get("endpoints", [])
    rw = next((e for e in eps if e.get("type") == "read_write"), eps[0] if eps else {})
    return Usage(now, str(p.get("consumption_period_start", ""))[:10], int(p.get("compute_time_seconds") or 0),
                 int(p.get("active_time_seconds") or 0), int(p.get("synthetic_storage_size") or 0),
                 rw.get("autoscaling_limit_min_cu"), rw.get("autoscaling_limit_max_cu"),
                 rw.get("suspend_timeout_seconds"))


def read_ledger(path: Path) -> list[Usage]:
    if not path.exists():
        return []
    with path.open() as f:
        return [Usage(datetime.fromisoformat(r["taken_at"]), r["period_start"], int(r["compute_seconds"]),
                      int(r["active_seconds"]), int(r["storage_bytes"])) for r in csv.DictReader(f)]


def append_ledger(path: Path, u: Usage) -> None:
    new = not path.exists()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        if new:
            w.writerow(["taken_at", "period_start", "compute_seconds", "active_seconds", "storage_bytes"])
        w.writerow([u.taken_at.isoformat(timespec="minutes"), u.period_start, u.compute_seconds,
                    u.active_seconds, u.storage_bytes])


# ---------------------------------------------------------------- analysis

def _ts(v) -> datetime | None:
    if v is None or isinstance(v, datetime):
        return v
    return datetime.fromisoformat(str(v).replace("Z", "+00:00"))


def _union_hours(intervals: list[tuple[datetime, datetime]]) -> float:
    total, cur_s, cur_e = 0.0, None, None
    for s, e in sorted(intervals):
        if cur_e is None or s > cur_e:
            if cur_e is not None:
                total += (cur_e - cur_s).total_seconds()
            cur_s, cur_e = s, e
        else:
            cur_e = max(cur_e, e)
    if cur_e is not None:
        total += (cur_e - cur_s).total_seconds()
    return total / 3600


def job_costs(runs: list[dict]) -> tuple[list[JobCost], float]:
    by: dict[str, list[tuple[datetime, datetime]]] = {}
    stats: dict[str, dict] = {}
    for r in runs:
        s, f = _ts(r["started_at"]), _ts(r.get("finished_at"))
        end = f or s + timedelta(minutes=CUT_OFF_RUN_MIN)
        by.setdefault(r["job"], []).append((s, end + timedelta(minutes=SUSPEND_MIN)))
        st = stats.setdefault(r["job"], {"runs": 0, "sec": 0.0, "failed": 0, "cut": 0})
        st["runs"] += 1
        st["sec"] += (end - s).total_seconds()
        st["failed"] += r.get("ok") is False
        st["cut"] += f is None
    jobs = [JobCost(j, st["runs"], st["sec"] / 3600, _union_hours(by[j]), st["failed"], st["cut"])
            for j, st in stats.items()]
    jobs.sort(key=lambda j: -j.awake_hours)
    return jobs, _union_hours([i for v in by.values() for i in v])


def suggest(r: Report) -> list[str]:
    out = []
    week = r.week
    awake_pct = week["awake_pct"] if week else 100 * r.awake_hours / (7 * 24)
    source = "Neon reports" if week else "job runs suggest"
    if awake_pct > 50:
        top = r.jobs[0] if r.jobs else None
        out.append(f"The database was awake {awake_pct:.0f}% of the week ({source}). "
                   + (f"`{top.job}` alone keeps it awake {top.awake_hours:.0f}h a week ({top.runs} runs). "
                      "Run it less often, or line it up with another job so they share one wake-up."
                      if top else ""))
    for j in r.jobs:
        if j.runs >= 7 * 24 * 2:
            out.append(f"`{j.job}` ran {j.runs} times ({j.runs / 7:.0f} a day). Anything more often than every "
                       f"{SUSPEND_MIN} minutes stops Neon from ever suspending.")
        elif j.run_hours > 7 and j.run_hours / max(j.runs, 1) > 0.5:
            out.append(f"`{j.job}` spent {j.run_hours:.1f}h running this week, {60 * j.run_hours / j.runs:.0f} min a run. "
                       "Check what it fetches that the mentions models don't use.")
        if j.cut_off:
            out.append(f"`{j.job}` had {j.cut_off} run(s) with no finish time (crashed or redeployed mid-run).")
        if j.failed:
            out.append(f"`{j.job}` failed {j.failed} time(s) this week. Failed runs still cost compute.")
    refreshers = [j for j in r.jobs if j.job in ("sync", "filings", "transcripts")]
    if sum(j.runs for j in refreshers) > 7 * 30:
        n = sum(j.runs for j in refreshers)
        out.append(f"The 18-step refresh chain ran about {n} times ({n / 7:.0f} a day) after sync, filings and "
                   "transcripts. Most steps only change when transcripts or filings do. Refreshing them only "
                   "then would cut about 3 minutes from every other run.")
    for rel in r.relations:
        if rel["bytes"] >= BIG_TABLE_BYTES:
            out.append(f"`{rel['schema_name']}.{rel['name']}` is {rel['bytes'] / 1024**3:.1f} GB. "
                       "Check it holds only what the models use.")
    leftovers = [rel for rel in r.relations if LEFTOVER_NAME.search(rel["name"])]
    if leftovers:
        size = sum(rel["bytes"] for rel in leftovers) / 1024**2
        out.append(f"{len(leftovers)} leftover {'copy' if len(leftovers) == 1 else 'copies'} ({', '.join('`' + rel['name'] + '`' for rel in leftovers)}, "
                   f"{size:.0f} MB in all). The Librarian can open a PR to drop them.")
    unread = [rel for rel in r.relations if rel["reads"] == 0 and rel["bytes"] > 1024**2
              and not LEFTOVER_NAME.search(rel["name"])]
    if unread:
        out.append("Never read since statistics were reset: "
                   + ", ".join(f"`{rel['name']}` ({rel['bytes'] / 1024**2:.0f} MB)" for rel in unread[:8])
                   + ". Candidates to drop after a check.")
    if r.usage and r.usage.max_cu and r.usage.max_cu > 4 and week and week["avg_cu"] < 1:
        out.append(f"Autoscaling goes up to {r.usage.max_cu:g} CU but averaged {week['avg_cu']:.2f} CU. "
                   "A lower ceiling (2–4 CU) caps the cost of a runaway query.")
    if not r.usage:
        out.append("Add `NEON_API_KEY` (a project-scoped Neon API key) to the cloud environment so the report can "
                   "show billed compute instead of estimating it from job runs.")
    return out


def build(runs: list[dict], relations: list[dict], usage: Usage | None, ledger: list[Usage], now: datetime) -> Report:
    jobs, awake = job_costs(runs)
    prev = ledger[-1] if ledger else None
    r = Report(now, jobs, awake, relations, usage, prev)
    r.suggestions = suggest(r)
    return r


# ---------------------------------------------------------------- rendering

def render_md(r: Report) -> str:
    year, wk, _ = r.now.isocalendar()
    out = [f"# Cost Report · {year}-W{wk:02d}", "",
           f"_Generated {r.now:%Y-%m-%d %H:%M} UTC. Neon Launch rates: ${COMPUTE_RATE}/CU-hour, "
           f"${STORAGE_RATE}/GB-month. Neon suspends after {SUSPEND_MIN} min without queries._", "",
           "## Summary", ""]
    week = r.week
    total_bytes = sum(rel["bytes"] for rel in r.relations)
    if week:
        out += [f"- **Compute this week:** {week['cu_hours']:.1f} CU-hours, about ${week['compute_usd']:.2f} "
                f"(${week['monthly_usd']:.0f}/month at this rate)",
                f"- **Awake:** {week['active_hours']:.0f}h of {week['days'] * 24:.0f}h ({week['awake_pct']:.0f}%), "
                f"averaging {week['avg_cu']:.2f} CU while awake"]
    elif r.usage:
        out.append(f"- **Billing period so far** (since {r.usage.period_start}): "
                   f"{r.usage.compute_seconds / 3600:.0f} CU-hours, about ${r.usage.compute_seconds / 3600 * COMPUTE_RATE:.0f}. "
                   "Weekly figures start with next week's report.")
    else:
        out.append("- **Billed compute:** not available (no `NEON_API_KEY`). The figures below are estimates from job runs.")
    out += [f"- **Job runs keep the database awake about {r.awake_hours:.0f}h a week** "
            f"({100 * r.awake_hours / 168:.0f}% of the week)",
            f"- **Storage:** {total_bytes / 1024**3:.2f} GB, about ${total_bytes / 1024**3 * STORAGE_RATE:.2f}/month"]
    if r.usage and r.usage.max_cu is not None:
        sus = r.usage.suspend_seconds
        after = "never" if sus == -1 else f"{(sus or SUSPEND_MIN * 60) // 60} min"
        out.append(f"- **Compute settings:** {r.usage.min_cu:g}–{r.usage.max_cu:g} CU, suspends after {after}")
    out += ["", "## What to change", ""]
    out += [f"{i}. {s}" for i, s in enumerate(r.suggestions, 1)] or ["Nothing stands out this week."]
    out += ["", "## Jobs, last 7 days", "",
            "Awake hours: how long the job alone would keep the database awake, counting "
            f"{SUSPEND_MIN} min after each run.", "",
            "| Job | Runs | Running (h) | Awake alone (h) | Failed | Cut off |", "|---|--:|--:|--:|--:|--:|"]
    out += [f"| {j.job} | {j.runs} | {j.run_hours:.1f} | {j.awake_hours:.1f} | {j.failed} | {j.cut_off} |" for j in r.jobs]
    out += ["", "## Largest tables", "", "| Table | Kind | Size | Reads |", "|---|---|--:|--:|"]
    out += [f"| {rel['schema_name']}.{rel['name']} | {rel['kind']} | {_size(rel['bytes'])} | {rel['reads']:,} |"
            for rel in r.relations[:12]]
    out.append("")
    return "\n".join(out)


def _size(b: int) -> str:
    return f"{b / 1024**3:.2f} GB" if b >= 1024**3 else f"{b / 1024**2:.0f} MB"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
