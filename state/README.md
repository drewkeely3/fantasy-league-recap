# State

One JSON file per season (`state/<season>.json`), matching Sleeper's own pattern of a
new `league_id` each season. Read and updated by the routine on every checkpoint firing.

```json
{
  "league_id": "1389464113716957184",
  "season": "2026",
  "published_dates": ["2026-09-15", "2026-09-16"],
  "reported_transaction_ids": ["1234567890123456789"]
}
```

- `published_dates`: idempotency check. A checkpoint fires at most once per day, so
  "has this checkpoint already published" reduces to "is today's ISO date already in
  this list." Only append today's date *after* a successful publish (last pipeline
  step), never before, so a failed run can still be retried same day by a safety-net
  firing.
- `reported_transaction_ids`: cumulative across the whole season, not per-checkpoint.
  Each firing pulls the current leg's transactions, reports only the ones not yet in
  this list, then appends those ids here. This is what lets a checkpoint lead with
  "what's new since last time" instead of repeating the week's full transaction list.

No pruning/rotation logic; a season's file is small enough (one date per day, one id
per transaction) to just keep appending for the whole season.
