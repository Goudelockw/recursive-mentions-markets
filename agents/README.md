# Scheduled tasks

Each folder is one Claude scheduled task: `PROMPT.md` is what it does and what it may touch.
All tasks run on the Claude subscription as fresh cloud sessions.

| Task | When (ET) | Status |
|---|---|---|
| [`trade-sheet/`](trade-sheet/PROMPT.md) | Weekdays 06:41 | Phase 1 |
| [`cost-report/`](cost-report/PROMPT.md) | Sunday 20:41 | Live |
| [`model-review/`](model-review/PROMPT.md) | Sunday 22:11 (after the Railway refit) | Live |
| [`ops/`](ops/PROMPT.md) | Sunday 21:41 (after the Railway batch) | Live |
| `librarian/` | Sunday 22:41 | Phase 3 |
| `research/` | 1st Monday 05:41 | Phase 4 |

## Permission tiers (all tasks)

| Tier | Meaning | Examples |
|---|---|---|
| **Auto** | Do it, then log it in the task's output | Re-run a failed job, idempotent backfills, rename or archive outputs |
| **PR** | Write the change, open a pull request, you merge | Code fixes, new checks, schema changes, model challengers |
| **Ask** | Draft it and put it under *Needs you* | Call-time overrides, risk overrides, trading rules, coefficients, k, sizing, deleting data, secrets |

Anything that changes how money is traded is always **Ask**.
