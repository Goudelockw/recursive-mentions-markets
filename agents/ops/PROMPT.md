# Ops task

Scheduled: Sundays 21:41 America/New_York, after the `research-weekly` Railway batch (Mon 01:00 UTC =
Sun 21:00 EDT / 20:00 EST) has run the health checks and queued the fixes it may make on its own.
A fresh Claude session each run, on the Claude subscription. Push notification on finish.

The batch already handled what's mechanical: safe re-fetches go into `ops.fix_requests` and
kalshi-worker's `ops-fixes` runs them daily. This task does what needs judgment, and writes the
Weekly Review.

## Permissions (see agents/README.md for the tiers)

- **Read only** on Neon (`DATABASE_URL` is `rmm_ro`). Never write to the database; never apply a proposal.
- **PR tier:** code fixes go on a branch named `ops/YYYY-MM-DD-<slug>` in the repo they belong to,
  pushed, never merged and never to `main`. Run that repo's checks first (`python -m py_compile` on
  changed files at least; `python -m unittest discover tests` where tests exist).
- **Ask tier:** anything that changes data (call-time overrides, word synonyms, risk overrides,
  labels) is written up as a proposal with the exact SQL. The owner applies it by replying
  "approve <id>" in a Claude session.
- May commit only `outputs/weekly/YYYY-Www_ops-proposals.json` and `outputs/weekly/YYYY-Www_weekly-review.{md,html}`
  to `recursive-mentions-markets` `main`.
- Don't re-queue or run pipeline commands yourself; the batch's fix rules do that.

## Steps

1. In the `recursive-mentions-markets` checkout, on `main`: `pip install -q -r requirements.txt`.
2. `python -m rmm weekly-review` prints the week's headline. Read the latest checks and fixes:
   `python -c "from rmm import db; [print(r) for r in db.query(\"select check_name, status, detail from ops.health_checks where run_id = (select max(run_id) from ops.runs)\")]"`
   and the same for `ops.fix_requests` (last 14 days: command, args, status, output). If the latest
   `ops.runs` row isn't from the last 24 hours, the batch didn't run: that is the first proposal
   (kind `other`, no SQL), and work from the newest data there is.
3. Work through every `warn` / `fail` that needs judgment. For each, either write a proposal or
   note in one line why none is needed. Proposals go in `outputs/weekly/YYYY-Www_ops-proposals.json`
   (a JSON list; ids `W<week>-1`, `W<week>-2`, …):

   ```json
   {"id": "W44-1", "kind": "call_time_override", "check": "check_date_calls",
    "title": "INTC: call is Thu Oct 29, 5:00pm ET, not Oct 22",
    "why": "Intel's IR page lists Q3 results on Oct 29 at 2:00pm PT. The ticker date (Oct 22) is wrong, which hid the release.",
    "evidence": ["https://www.intc.com/news-events/..."],
    "sql": "insert into kalshi.call_time_overrides (event_ticker, call_start, note) values ('KXEARNINGSMENTIONINTC-26OCT22', timestamptz '2026-10-29 17:00 America/New_York', 'IR page, ops W44');"}
   ```

   What to do per check:
   - `check_date_calls`, `low_confidence_call_times_7d`: find the official call date and time on the
     company's investor-relations page or its earnings-date press release (web search, then open
     the page). Only propose an override from a primary source; put the URL in `evidence`. If the
     estimate is already right, say so in the review instead of proposing.
   - `settlement_vs_transcript:*`: look at our transcript for that call
     (`kalshi.transcript_segments` / `kalshi.transcripts`, via `db.query`) and the market's rules
     (`kalshi.markets.rules_primary`). Decide whether it's a spelling or phrasing variant (propose a
     `kalshi.word_synonyms` row, kind `word_synonym`), a wrong or partial transcript (kind `data_fix`,
     say which source), or a word-matching bug in the code (PR tier, kind `code_fix`).
   - `job:*` failures and cut-off runs: read `kalshi.ingest_runs.error` for the failed runs. A code
     bug gets a branch in `kalshi-worker` (kind `code_fix`, with `branch` and `compare_url`
     `https://github.com/Goudelockw/kalshi-worker/compare/main...<branch>`); anything else is a
     proposal saying what to check.
   - `unlabeled_open_words`: list the words in one proposal (kind `label`) for the labeler.
   - Failed or rejected rows in `ops.fix_requests`: say why from the output, and propose the next step.
4. `python -m rmm weekly-review --page` (it reads the proposals file), then Artifact publish with
   `url` = the URL in `agents/ops/PAGE_URL` and `file_path` = `outputs/weekly/YYYY-Www_weekly-review.html`.
   If `PAGE_URL` is empty, publish a new page and write its URL there in the same commit.
5. Commit the proposals file and the review files with the message `weekly review YYYY-Www: <headline>`,
   then `git pull --rebase` (another Sunday task may have pushed) and push to `main`.
6. End with this message and nothing else (it becomes the notification):

   ```
   Weekly review YYYY-Www: <headline from step 2, updated>
   <each proposal: "<id>: <title>">, or "Nothing needs you."
   <the Weekly Review page URL>
   ```
