# Trade Sheet task

Scheduled: weekdays 06:41 America/New_York, a fresh Claude session each run, on the Claude
subscription. Push notification on finish. This file is the task's instructions; the scheduled
task's own prompt only says to follow it.

## Permissions

- **Read only** on Neon. Never write to any table, never refresh views, never run a backfill.
  Problems go in the sheet's *Needs you* section; the Sunday Ops task fixes them.
- Never place, change or cancel orders. Never change stakes, rules or overrides.
- May commit only files under `outputs/trade-sheets/`.

## Steps

1. In the `recursive-mentions-markets` checkout, on `main`: `pip install -q -r requirements.txt`.
2. Build the sheet.
   - If `DATABASE_URL` is set (the read-only `rmm_ro` role): `python -m rmm trade-sheet`. In a cloud
     session it queries over Neon's HTTPS endpoint, so `*.neon.tech` must be an allowed domain.
     If it fails with a network error, fall back to the next bullet.
   - Otherwise use the Neon connector (project `mute-sun-75653323`, database `neondb`). Run
     `sql/queries/trade_sheet.sql` wrapped as `select json_agg(t) from (<query without the final ;>) t`
     and save the result exactly as returned to `/tmp/board.json`. Do the same with
     `sql/queries/trade_sheet_preflight.sql` into `/tmp/preflight.json`. Then
     `python -m rmm trade-sheet --board /tmp/board.json --preflight /tmp/preflight.json`.
     Never edit the saved results by hand.
3. Commit the three files it wrote (`outputs/trade-sheets/YYYY-MM/YYYY-MM-DD_trade-sheet.{md,csv,html}`)
   with the message `trade sheet YYYY-MM-DD: <status line>` and push to `main`.
4. Republish the Trade Sheet page: Artifact publish with `url` = the URL in `agents/trade-sheet/PAGE_URL`
   and `file_path` = the `.html` file. If `PAGE_URL` is empty, publish a new page and write its URL there
   in the same commit.
5. End with this message and nothing else (it becomes the notification):

   ```
   <STATUS> · <headline from the command's last line>
   <each "Needs you" bullet from the .md, one line each, or "Nothing needs you.">
   <the Trade Sheet page URL>
   ```

If any step fails, still end with a message: `STOP · trade sheet failed at step N: <error>`. Don't retry
more than once, and don't work around a failing query by writing your own.
