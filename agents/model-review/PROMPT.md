# Model Review task

Scheduled: Sundays 22:11 America/New_York, after the `research-weekly` Railway batch (Mon 01:00 UTC)
has refit and reviewed a new challenger. A fresh Claude session each run, on the Claude subscription.
Push notification on finish. Its job is to put the release in front of the owner **before** anything
is promoted.

## Permissions

- **Read only** on Neon. Never promote, retire or edit a model version. Promotion is the owner's call:
  `select kalshi.promote_model(N);`.
- May commit only `outputs/models/index.html`, `outputs/models/README.md` and `outputs/models/v*/`.

## Steps

1. In the `recursive-mentions-markets` checkout, on `main`: `pip install -q -r requirements.txt`.
2. `python -m rmm models`. If the newest version wasn't fitted in the last 2 days, the weekly batch
   didn't run: say so in the message and still do steps 4–5.
3. `python -m rmm review` prints the newest challenger against the live model.
4. `python -m rmm models --page`, then Artifact publish with `url` = the URL in
   `agents/model-review/PAGE_URL` and `file_path` = `outputs/models/index.html`.
5. Commit the page files with the message `model review YYYY-MM-DD: vN <verdict>` and push to `main`.
6. End with this message and nothing else (it becomes the notification):

   ```
   Model review: vN vs live vM: <verdict>.
   <forward test, one line per entry point: Brier vN / vM / price, better in X%, ¢/trade vM -> vN>
   <one line: the biggest coefficient change, or "same variables, more data">
   To promote: reply "promote vN" to Claude. Nothing changes until you do.
   <the Models page URL>
   ```
