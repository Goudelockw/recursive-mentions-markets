# Librarian task

Scheduled: Sundays 22:41 America/New_York, the last task of the Sunday batch (after the cost report,
the Ops task and Model Review have committed their outputs). A fresh Claude session each run, on the
Claude subscription. Push notification on finish.

The job: keep `outputs/`, the docs and the database tidy, so anyone can open the repo and find
things where the naming rules say they are, and `README.md` / `SYSTEM.md` describe what actually runs.

## Permissions (see agents/README.md for the tiers)

- **Read only** on Neon (`DATABASE_URL` is `rmm_ro`).
- **Auto, straight to `main`:**
  - the moves `python -m rmm librarian --apply` makes (renames into the naming rules, 90-day archive);
  - renaming a misnamed output by hand when the right name is clear from the file (`git mv`);
  - doc fixes in `README.md`, `SYSTEM.md`, `PLAN.md` and `agents/README.md` that make them describe
    what already exists (a renamed command, a new service, a stale path). Docs only: never change
    what a rule, threshold or schedule *is* by editing its description.
- **PR tier:** on a branch named `librarian/YYYY-MM-DD-<slug>`, pushed, never merged:
  - dropping leftover copies and relations nothing reads: a new numbered migration in
    `sql/migrations/` with `drop ... if exists` for each, and the evidence (size, reads) as comments;
  - removing dead code or duplicate scripts; consolidating overlapping docs.
  Include the compare link `https://github.com/Goudelockw/<repo>/compare/main...<branch>` in the log.
  One open branch per kind: if last week's `librarian/` branch for the same thing is still unmerged,
  don't open another; mention it again.
- **Ask:** deleting data that isn't a leftover copy, anything in Railway or secrets, closing anyone
  else's branches. Put these under *Needs you* in the log.

## Steps

1. In the `recursive-mentions-markets` checkout, on `main`: `git pull`, then `pip install -q -r requirements.txt`.
2. `python -m rmm librarian` (dry run) and read it. Then `python -m rmm librarian --apply`: it makes
   the moves and writes `outputs/weekly/YYYY-Www_librarian-log.md`.
3. Work through the log:
   - **Breaks the naming rules:** rename with `git mv` when the right name is clear; otherwise leave it
     and say why.
   - **Docs out of date:** fix the doc (Auto tier above). For a service that stopped running or a job
     missing from the services table, check the code in `kalshi-worker` (`kalshi_worker/__main__.py`,
     `README.md`) before editing; if a service looks broken rather than retired, say so under
     *Needs you* instead of editing it out.
   - **Database:** for leftovers, open (or keep) the PR-tier migration branch.
   - Also read the week's commits (`git log --since="8 days ago" --stat` in both repos). If one added
     a job, view, check or rule that `SYSTEM.md` doesn't describe yet, add it.
4. Append to the log, under these headings: `## Done by hand` (each rename and doc fix, one line),
   `## Branches` (each PR-tier branch with its compare link), `## Needs you` (Ask items, or "Nothing.").
5. Run `python -m unittest discover tests`. If it fails, undo your doc or rename changes that caused it.
6. Commit everything with the message `librarian YYYY-Www: <headline line from the log>`, then
   `git pull --rebase` (another Sunday task may have pushed) and push to `main`.
7. End with this message and nothing else (it becomes the notification):

   ```
   Librarian YYYY-Www: <headline>
   <one line per branch opened or Needs-you item, or "Nothing needs you.">
   https://github.com/Goudelockw/recursive-mentions-markets/blob/main/outputs/weekly/YYYY-Www_librarian-log.md
   ```
