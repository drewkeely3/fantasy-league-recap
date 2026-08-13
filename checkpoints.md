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
anything shared with the league).

Tone update (2026-08-13): humor, mockery, and roasting are encouraged, casual and a
little mean, not corny. See CLAUDE.md's "Tone clarification" under the Hard
constraint section for the exact boundary: retrospective roasting of what already
happened is fine ("started a guy on bye, got zero, rough"), forward-looking advice
framing is not ("check the injury report next time"). The test is time direction,
not niceness.

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

6. Publish: write the content, categorized by type (added 2026-08-13, per user
   request - so a future UI can slice content by category, e.g. a persistent
   "transactions this week" view, without needing to re-parse old chronological
   entries): tag each piece of what you write as one of `recap_narrative`,
   `transactions`, `standings`, `schedule`, or `awards` (streaks/boom-bust/
   inactive-player callouts). Exact file/page structure under docs/ on the
   claude/publish branch not finalized yet (see CLAUDE.md's Publishing section),
   but whatever you write, keep these categories distinguishable in the output
   (e.g. separate sections/fields) rather than one undifferentiated blob of
   prose, so the categorization survives regardless of what the final page
   layout ends up being.

7. Update state/<season>.json: add today's date to `published_dates`, and add any
   newly-reported transaction_ids to `reported_transaction_ids`. Commit and push
   both the published output and the state update together.
```

## Optional content enhancements (added 2026-08-13, use in any content block that recaps completed games)

Not required every checkpoint, use when there's real material for them (don't force
a streak mention if nobody's actually on one):

- **Streaks**: win/loss streaks, or a manager being the highest/lowest scorer N
  weeks running. Needs pulling multiple weeks of matchup history (loop
  `get_matchups` across this season's completed weeks so far), not just the
  current week.
- **Boom/bust callouts**: a player who went off or cratered, and how it affected
  their manager (e.g. "X went off for [NFL team], didn't matter, Y still lost").
  Source: each matchup row's `players_points` (per-player score) and `starters`
  (who was actually in the lineup) - already pulled, no new data source needed.
- **Started-an-inactive-player callouts**: a manager started someone on bye,
  injured, or otherwise inactive, and got 0 from that slot. Strictly retrospective
  framing only (see Tone update above). A player scoring 0 isn't proof they didn't
  play, a legitimately bad game also scores near 0, so cross-reference against
  bye_weeks.py and the player's `injury_status` in the players/nfl payload before
  flagging this, don't flag on the 0 alone. Not yet verified against real data
  which signal reliably distinguishes "didn't play" from "played badly" - test
  before trusting this in a real checkpoint (see CLAUDE.md Content scope note).

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
- Use the optional content enhancements above where there's real material:
  streaks especially belong here since this checkpoint already has full-season
  context; boom/bust and inactive-player callouts too if applicable to this week.

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
- Boom/bust or inactive-player callouts if applicable to Thursday's game(s) (see
  optional content enhancements above)
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
- Boom/bust or inactive-player callouts if applicable to Saturday's game(s)
```

### Monday — Sunday games recap + MNF preview
```
- Recap Sunday's games (early window, late window, SNF)
- Preview tonight's Monday Night Football matchup
- Transactions since the last checkpoint
- Boom/bust or inactive-player callouts if applicable to Sunday's games (likely
  the richest day for this, most games happen Sunday)
```
