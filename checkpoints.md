# Checkpoint prompts

Rough drafts (per user, 2026-08-13: "get rough drafts in there now" and iterate once
the UI exists). Each of the 7 weekday Routines needs a fully self-contained prompt
(a Routine session has zero memory of this file or this conversation), so at wiring
time (#6) each real prompt is: PIPELINE PREAMBLE + that day's CONTENT BLOCK below +
PIPELINE FOOTER, concatenated into one prompt. Written separately here only to avoid
repeating shared boilerplate seven times inconsistently.

Tone (confirmed with user against a real hand-drafted sample, 2026-08-13): casual
newsletter voice for the highlights/narrative, terse bullet points for the data-heavy
parts (scores, standings, matchups). No em dashes (repo-wide convention, applies to
anything shared with the league). No advice or commentary implying a transaction or
lineup decision was good/bad (the hard constraint).

## PIPELINE PREAMBLE (every checkpoint)

```
You are running a scheduled checkpoint for an automated fantasy football league
recap. League: <LEAGUE_ID> (Sleeper). This runs unattended, no human is watching -
follow these steps exactly and do not skip any.

1. Fetch the league via GET /league/<LEAGUE_ID>. If `status` is not exactly
   "in_season", stop here. Do not publish anything, do not update state. This is
   expected and not an error (pre-season, draft, or off-season).

2. Read state/<season>.json from the claude/publish branch (checkout that branch
   first; it is the live branch for both state and published output, not main).
   If today's date (America/New_York) is already in `published_dates`, stop here.
   This is the idempotency check, a safety-net firing must not double-post.

3. Pull whatever Sleeper data this checkpoint needs (see the content block below).
   Use api.sleeper.app directly if reachable; if not, note that and use WebFetch
   as a fallback (see CLAUDE.md's network access note).

4. If this checkpoint needs to know actual NFL game days/times (Thu/Fri/Sat/Sun/
   Mon, already played or not - Sleeper has no per-game schedule data, only weekly
   fantasy totals), pull it from ESPN's public scoreboard API (espn_api.py,
   games_by_et_weekday). Verified 2026-08-13 against real 2025 weeks 10 (no
   Saturday game, the common case) and 16/17 (has Saturday games, confirming both
   the empty and non-empty cases work).
```

## PIPELINE FOOTER (every checkpoint)

```
After drafting the content per the instructions above:

4. Re-read the hard constraint: this recap must never contain advice,
   recommendations, or anything implying a transaction, lineup, or roster decision
   was good or bad. Purely factual and retrospective. Reread your own draft now and
   revise anything that crosses this line before continuing.

5. [Placeholder until #5 is built: an independent subagent re-checks the draft
   against the no-advice rule with fresh context before publishing. Do not skip
   this once it exists.]

6. Publish: write the content into the appropriate page under docs/ on the
   claude/publish branch (exact page/section structure not finalized yet, see
   CLAUDE.md's Publishing section - for now, append to today's entry on the
   current week's page).

7. Update state/<season>.json: add today's date to `published_dates`, and add any
   newly-reported transaction_ids to `reported_transaction_ids`. Commit and push
   both the published output and the state update together.
```

## Content blocks, per day

### Tuesday — Post-Week Recap (the main recap)
```
Recap the week that just finished (through Monday Night Football):
- Final scores for every matchup
- Closest matchup of the week
- Biggest blowout of the week
- Top scorer and lowest scorer
- Bad beat of the week (highest score that still lost)
- Current standings (all teams, win-loss record)
- Transactions since the last checkpoint (cleared waiver claims and the resulting
  adds/drops only, not failed claims; any trades), reported neutrally
- Next week's matchups
- Next week's byes: which NFL teams are on bye, and for each, which owned players
  on this league's rosters are affected, grouped by owner (not just bare team
  codes - see bye_weeks.py and cross-reference against roster player lists)

Tone: casual newsletter voice for the narrative/highlights, terse bullets for
scores/standings/matchups. Confirmed sample on file, 2026-08-13.
```

### Wednesday — Waiver Wire Update
```
Recap transactions only, nothing else:
- Which contested waiver claims cleared and the resulting adds/drops (not failed
  claims, those are noise)
- Any trades
- All transactions since the last checkpoint's `reported_transaction_ids`, not
  the whole week's list again

If there is nothing new to report, say so briefly and stop (skip cleanly, do not
pad with filler). This is expected most weeks per CLAUDE.md's schedule notes.
```

### Thursday — Wednesday recap + pregame check-in
```
- Recap Wednesday's games, if any (usually none per CLAUDE.md - most weeks this
  section is empty, skip it cleanly rather than noting "no games")
- This week's full matchup slate
- Current standings snapshot
- Transactions since the last checkpoint
```

### Friday — Thursday game recap + Friday preview
```
- Recap Thursday night's game(s)
- Preview any Friday game (rare; most weeks none - skip cleanly)
- Transactions since the last checkpoint
```

### Saturday — Friday game recap + Saturday preview
```
- Recap Friday's game(s), if any
- Preview any Saturday game (mostly weeks 15-18 only)
- Transactions since the last checkpoint

Usually nothing to report on either side. Per CLAUDE.md: skip cleanly rather than
posting filler - this is expected, not a bug, most of the season.
```

### Sunday — Saturday recap + main slate pregame + standings
```
- Recap Saturday's game(s), if any
- Pregame check-in for today's main slate (matchups happening today)
- Current standings snapshot
- Transactions since the last checkpoint
```

### Monday — Sunday games recap + MNF preview
```
- Recap Sunday's games (early window, late window, SNF)
- Preview tonight's Monday Night Football matchup
- Transactions since the last checkpoint
```
