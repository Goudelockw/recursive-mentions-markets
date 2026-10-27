# Cost Report task

Scheduled: Sundays 20:41 America/New_York, a fresh Claude session each run, on the Claude
subscription. Push notification on finish.

## Permissions

- **Read only.** Never change Neon settings, Railway services, schedules or data. Every suggestion is
  for the owner to approve (or for the Ops / Librarian tasks to turn into a PR).
- May commit only `outputs/weekly/YYYY-Www_cost-report.md`, `outputs/costs/neon-usage.csv` and
  `outputs/models/index.html` / `outputs/models/README.md`.

## Steps

1. In the `recursive-mentions-markets` checkout, on `main`: `pip install -q -r requirements.txt`.
2. `python -m rmm cost-report`. It needs `DATABASE_URL` (read-only `rmm_ro`) and, for billed figures,
   `NEON_API_KEY`. If it fails, end with `Cost report failed: <error>` and stop.
3. Read the report it wrote. Add a section at the end, `## Recommendations`, with at most three
   changes, most valuable first. For each: what to change, in which repo or service, and the rough
   saving per month, worked out only from numbers in the report (awake hours × average CU ×
   $0.106, or GB × $0.35). Say plainly when a saving can't be estimated from the report. Compare with
   last week's report in `outputs/weekly/` when there is one: say what changed and whether last
   week's recommendations were acted on.
4. Refresh the Models page: `python -m rmm models --page`, then Artifact publish with `url` = the URL in
   `agents/models/PAGE_URL` and `file_path` = `outputs/models/index.html`. If a challenger beats the live
   model's call-start Brier by more than 0.002, add one line saying so to the end message (never promote).
5. Commit the files with the message `cost report YYYY-Www: <the command's last line>` and push to `main`.
6. End with this message and nothing else (it becomes the notification):

   ```
   <the command's last line>
   1. <first recommendation, one line, with its saving>
   2. ...
   ```
