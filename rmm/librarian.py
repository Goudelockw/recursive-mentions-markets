"""The Librarian: keeps outputs/, the docs and the database tidy.

    python -m rmm librarian            what it would do (no changes)
    python -m rmm librarian --apply    move what breaks the naming rules or is over 90 days old,
                                       and write outputs/weekly/YYYY-Www_librarian-log.md

What it checks:
  outputs    every file against the naming rules in rmm.paths; misfiled trade sheets (wrong month
             folder) are moved, anything else that breaks a rule is listed for a person to rename
  archive    trade sheets and weekly files over 90 days old, and model folders over 90 days old that
             are neither live nor among the newest three, move to outputs/archive/<area>/
  docs       paths, `python -m rmm` commands and kalshi./ops. objects the docs mention must exist;
             every Railway service in SYSTEM.md 4.1 must have run in the last 8 days and every job
             that ran must be in that table; each agents/ task has its PROMPT.md and PAGE_URL;
             migrations are numbered without gaps
  neon       leftover copies and large relations nothing reads (the PR tier drops them, with this
             as the evidence)

Moves use `git mv` so the file's history follows it. Nothing here deletes anything.
"""
from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

from . import cost_report, db, paths

ARCHIVE_DAYS = 90
KEEP_MODELS = 3
SERVICE_STALE_DAYS = 8
DOCS = ["README.md", "SYSTEM.md", "PLAN.md", "agents/README.md", *sorted(str(p.relative_to(paths.ROOT))
        for p in (paths.ROOT / "agents").glob("*/PROMPT.md"))]
REPO_DIRS = ("rmm/", "sql/", "agents/", "outputs/", "docs/", "tests/")
PLACEHOLDER = re.compile(r"YYYY|Www|<|\*|\{|vN|EXP-NNNN|\.\.\.|…")
TRADE_SHEET = re.compile(r"^(\d{4}-\d{2})-\d{2}_trade-sheet\.(md|csv|html)$")
MODEL_DIR = re.compile(r"^v(\d+)_(\d{4}-\d{2}-\d{2})$")
EXPERIMENT_DIR = re.compile(r"^EXP-\d{4}_[a-z0-9]+(-[a-z0-9]+)*$")


@dataclass
class Move:
    src: Path
    dst: Path
    why: str


@dataclass
class Report:
    today: date
    moves: list[Move] = field(default_factory=list)
    misnamed: list[tuple[str, str]] = field(default_factory=list)   # (path, rule it breaks)
    docs: list[tuple[str, str]] = field(default_factory=list)       # (where, problem)
    neon: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    applied: bool = False

    @property
    def headline(self) -> str:
        parts = [f"{len(self.moves)} {'move' if len(self.moves) == 1 else 'moves'}",
                 f"{len(self.misnamed)} misnamed", f"{len(self.docs)} doc {'issue' if len(self.docs) == 1 else 'issues'}",
                 f"{len(self.neon)} Neon {'item' if len(self.neon) == 1 else 'items'}"]
        return " · ".join(parts)


def _rel(p: Path) -> str:
    return str(p.relative_to(paths.ROOT))


def _week_monday(name: str) -> date | None:
    m = re.match(r"^(\d{4})-W(\d{2})_", name)
    return date.fromisocalendar(int(m.group(1)), int(m.group(2)), 1) if m else None


# ---------------------------------------------------------------- outputs

def check_outputs(r: Report, live_versions: set[int] | None) -> None:
    cutoff = r.today - timedelta(days=ARCHIVE_DAYS)
    out = paths.OUTPUTS
    for p in sorted(out.rglob("*")):
        if p.is_dir() or p.name == ".gitkeep" or "__pycache__" in p.parts:
            continue
        parts = p.relative_to(out).parts
        area = parts[0]
        if area == "archive":
            continue
        if area == "trade-sheets":
            m = TRADE_SHEET.match(p.name)
            if not m:
                r.misnamed.append((_rel(p), "trade sheets are YYYY-MM-DD_trade-sheet.{md,csv,html}"))
                continue
            day = date.fromisoformat(p.name[:10])
            home = out / "trade-sheets" / m.group(1) / p.name
            if day < cutoff:
                r.moves.append(Move(p, out / "archive" / "trade-sheets" / m.group(1) / p.name, f"over {ARCHIVE_DAYS} days old"))
            elif p != home:
                r.moves.append(Move(p, home, f"belongs in trade-sheets/{m.group(1)}/"))
        elif area == "weekly":
            if len(parts) != 2 or not paths.WEEKLY_NAME.match(p.name):
                r.misnamed.append((_rel(p), "weekly files are YYYY-Www_<kind>.<ext>, directly in weekly/"))
                continue
            monday = _week_monday(p.name)
            if monday and monday < cutoff:
                r.moves.append(Move(p, out / "archive" / "weekly" / p.name[:4] / p.name, f"over {ARCHIVE_DAYS} days old"))
        elif area == "models":
            if len(parts) == 2 and p.name in ("index.html", "README.md"):
                continue
            if len(parts) < 3 or not MODEL_DIR.match(parts[1]):
                r.misnamed.append((_rel(p), "model files go in models/vN_YYYY-MM-DD/"))
        elif area == "experiments":
            if len(parts) < 3 or not EXPERIMENT_DIR.match(parts[1]):
                r.misnamed.append((_rel(p), "experiments go in experiments/EXP-NNNN_<slug>/"))
        elif area == "costs":
            if p != paths.costs_ledger():
                r.misnamed.append((_rel(p), "costs/ holds only the neon-usage.csv ledger"))
        else:
            r.misnamed.append((_rel(p), f"outputs/{area}/ is not one of the output areas"))
    _archive_models(r, live_versions, cutoff)


def _archive_models(r: Report, live_versions: set[int] | None, cutoff: date) -> None:
    if live_versions is None:
        r.notes.append("Model folders: not checked for archiving (no database connection to see which is live).")
        return
    dirs = [(int(m.group(1)), date.fromisoformat(m.group(2)), d) for d in (paths.OUTPUTS / "models").iterdir()
            if d.is_dir() and (m := MODEL_DIR.match(d.name))]
    newest = {v for v, _, _ in sorted(dirs, reverse=True)[:KEEP_MODELS]}
    for v, trained, d in dirs:
        if trained < cutoff and v not in newest and v not in live_versions:
            r.moves.append(Move(d, paths.OUTPUTS / "archive" / "models" / d.name,
                                f"trained over {ARCHIVE_DAYS} days ago, not live, not among the newest {KEEP_MODELS}"))


# ---------------------------------------------------------------- docs

def _subcommands() -> set[str]:
    from . import __main__ as cli
    return set(re.findall(r'add_parser\("([a-z-]+)"', Path(cli.__file__).read_text()))


def check_docs(r: Report, objects: set[str] | None, runs: dict[str, datetime] | None) -> None:
    cmds = _subcommands()
    for doc in DOCS:
        f = paths.ROOT / doc
        if not f.exists():
            r.docs.append((doc, "missing"))
            continue
        text = f.read_text()
        for ref in sorted(set(re.findall(r"`([^`\s]+)`", text))):
            path = ref.split("#")[0].rstrip("/:")
            if path.startswith(REPO_DIRS) and not PLACEHOLDER.search(path) and not (paths.ROOT / path).exists():
                r.docs.append((doc, f"`{ref}` does not exist"))
        for cmd in sorted(set(re.findall(r"python -m rmm ([a-z][a-z-]*)", text))):
            if cmd not in cmds:
                r.docs.append((doc, f"`python -m rmm {cmd}` is not a command"))
        if objects is not None:
            for obj in sorted(set(re.findall(r"`((?:kalshi|ops)\.[a-z_][a-z0-9_]*)", text))):
                if obj not in objects:
                    r.docs.append((doc, f"`{obj}` is not in the database"))
    readme = (paths.ROOT / "README.md").read_text()
    for cmd in sorted(cmds - set(re.findall(r"python -m rmm ([a-z][a-z-]*)", readme))):
        r.docs.append(("README.md", f"`python -m rmm {cmd}` is not documented"))
    _check_agents(r)
    _check_migrations(r)
    if runs is not None:
        _check_services(r, runs)


def _check_agents(r: Report) -> None:
    table = (paths.ROOT / "agents" / "README.md").read_text()
    for d in sorted(p for p in (paths.ROOT / "agents").iterdir() if p.is_dir()):
        name = d.name
        if not (d / "PROMPT.md").exists():
            r.docs.append((f"agents/{name}/", "has no PROMPT.md"))
        if f"{name}/" not in table:
            r.docs.append(("agents/README.md", f"`{name}/` is not in the task table"))
        if (d / "PAGE_URL").exists() and not (d / "PAGE_URL").read_text().strip():
            r.docs.append((f"agents/{name}/PAGE_URL", "is empty"))
    for name, status in re.findall(r"^\|\s*\[?`([a-z-]+)/`.*\|\s*([^|]+?)\s*\|\s*$", table, re.M):
        if status == "Live" and not (paths.ROOT / "agents" / name / "PROMPT.md").exists():
            r.docs.append(("agents/README.md", f"`{name}/` is marked Live but has no PROMPT.md"))


def _check_migrations(r: Report) -> None:
    nums = sorted(int(m.group(1)) for p in (paths.SQL / "migrations").glob("*.sql") if (m := re.match(r"(\d{3})_", p.name)))
    if nums != list(range(1, len(nums) + 1)):
        r.docs.append(("sql/migrations/", f"numbers are not 001…{len(nums):03d} without gaps or repeats: {nums}"))


def services_in_system_md() -> list[str]:
    text = (paths.ROOT / "SYSTEM.md").read_text()
    section = text.split("### 4.1", 1)[-1].split("\n### ", 1)[0]
    return re.findall(r"^\|\s*\*\*([a-z-]+)\*\*\s*\|", section, re.M)


def _check_services(r: Report, runs: dict[str, datetime]) -> None:
    documented = services_in_system_md()
    now = max(runs.values(), default=datetime.now())
    for s in documented:
        last = runs.get(s)
        if last is None or now - last > timedelta(days=SERVICE_STALE_DAYS):
            when = f"last ran {last:%Y-%m-%d}" if last else "no runs in the last 30 days"
            r.docs.append(("SYSTEM.md 4.1", f"**{s}** is documented as a service but {when}"))
    sub_jobs = {"fortune", "equibles", "news-dates", "precall"}   # run inside another service
    for job, last in sorted(runs.items()):
        if job not in documented and job not in sub_jobs and now - last <= timedelta(days=SERVICE_STALE_DAYS):
            r.docs.append(("SYSTEM.md 4.1", f"job `{job}` ran (last {last:%Y-%m-%d}) but is not in the services table"))


# ---------------------------------------------------------------- neon

def check_neon(r: Report, relations: list[dict]) -> None:
    for rel in relations:
        name, size = f"{rel['schema_name']}.{rel['name']}", int(rel["bytes"] or 0) / 1024**2
        if cost_report.LEFTOVER_NAME.search(rel["name"]):
            r.neon.append(f"`{name}` ({size:.0f} MB) looks like a leftover copy: drop it (PR tier)")
        elif int(rel["reads"] or 0) == 0 and size >= 1:
            r.neon.append(f"`{name}` ({size:.0f} MB) has not been read since statistics were reset: check, then drop (PR tier)")
    r.notes.append("Neon branches: not checked (needs NEON_API_KEY, which is not set).")


# ---------------------------------------------------------------- run

def _load_db() -> tuple[set[int] | None, set[str] | None, dict[str, datetime] | None, list[dict]]:
    try:
        live = {int(x["version"]) for x in db.query("select version from kalshi.model_versions where status = 'live'")}
        objs = {f"{x['s']}.{x['n']}" for x in db.query(
            "select n.nspname s, c.relname n from pg_class c join pg_namespace n on n.oid = c.relnamespace "
            "where n.nspname in ('kalshi', 'ops') union select n.nspname, p.proname from pg_proc p "
            "join pg_namespace n on n.oid = p.pronamespace where n.nspname in ('kalshi', 'ops')")}
        runs = {x["job"]: datetime.fromisoformat(str(x["last"]).replace("Z", "+00:00")).replace(tzinfo=None) for x in db.query(
            "select job, max(started_at) as last from kalshi.ingest_runs where started_at > now() - interval '30 days' "
            "group by job union all select 'research-weekly', max(started_at) from ops.runs having count(*) > 0")}
        rels = db.run_query(paths.query("cost_relations"))
        return live, objs, runs, rels
    except Exception as e:  # noqa: BLE001  (the file checks still run without the database)
        print(f"database not reachable ({e}); running the file checks only")
        return None, None, None, []


def run(today: date, apply: bool = False, use_db: bool = True) -> Report:
    r = Report(today)
    live, objs, runs, rels = _load_db() if use_db else (None, None, None, [])
    if not use_db:
        r.notes.append("Database checks skipped.")
    check_outputs(r, live)
    check_docs(r, objs, runs)
    if use_db and objs is not None:
        check_neon(r, rels)
    if apply:
        for m in r.moves:
            _move(m.src, m.dst)
        r.applied = True
    return r


def _move(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    tracked = subprocess.run(["git", "ls-files", "--error-unmatch", str(src)], cwd=paths.ROOT,
                             capture_output=True).returncode == 0
    if tracked:
        subprocess.run(["git", "mv", str(src), str(dst)], cwd=paths.ROOT, check=True)
    else:
        src.rename(dst)


def render_md(r: Report) -> str:
    year, week, _ = r.today.isocalendar()
    out = [f"# Librarian log · {year}-W{week:02d}", "", f"{r.today:%a %b %-d, %Y} · {r.headline}", ""]
    out += ["## Moved" if r.applied else "## Would move", ""]
    out += [f"- `{_rel(m.src)}` → `{_rel(m.dst)}` ({m.why})" for m in r.moves] or ["Nothing."]
    out += ["", "## Breaks the naming rules (rename by hand)", ""]
    out += [f"- `{p}`: {why}" for p, why in r.misnamed] or ["Nothing."]
    out += ["", "## Docs out of date", ""]
    out += [f"- {where}: {what}" for where, what in r.docs] or ["Nothing."]
    out += ["", "## Database", ""]
    out += [f"- {x}" for x in r.neon] or ["Nothing to drop."]
    if r.notes:
        out += ["", "## Not checked", ""] + [f"- {n}" for n in r.notes]
    return "\n".join(out) + "\n"
