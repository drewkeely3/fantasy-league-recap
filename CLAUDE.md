# Fantasy League Recap

## Status
Design phase complete (schedule, content scope, transaction mechanics all verified against real data). Data-pull layer built and verified against real 2025 season data (see "Data-pull layer" under Architecture). Recap content generation not yet built. This file is the handoff from a scoping conversation done in Cowork; continue building from here.

## What this is
An automated, scheduled system that generates a recurring fantasy football league recap for a Sleeper league, built as a Claude Code Routine (scheduled task). Shared with the whole league, not just the user.

Follow-on project to the fantasy draft board (see `draft-board-CLAUDE.md` in this folder if present) but scoped separately. Distinct from a personal season dashboard project that will be built later.

## Hard constraint: informational only, no strategic edge
This is the most important rule for this project. The recap must never contain advice, recommendations, or anything that gives any manager (including the user) an edge over others. No "you should target X," no "Team Y is weak at Z," no commentary implying a transaction was good or bad. Purely factual, retrospective, and schedule-oriented content. If in doubt whether something crosses into advice, leave it out.

This applies to every checkpoint below, not just the main weekly recap.

## Data source
Sleeper's public, read-only API, no auth needed. Key endpoints:
- `GET /league/<league_id>` — league settings, season, previous_league_id
- `GET /league/<league_id>/matchups/<leg>` — weekly matchups and scores
- `GET /league/<league_id>/rosters` — rosters, records
- `GET /league/<league_id>/transactions/<leg>` — trades, waiver moves (cumulative for that leg, see Transaction mechanics below)
- `GET /league/<league_id>/users` — map user_id/roster_id to display names
- `players/nfl` payload — player metadata if needed, same pattern as the draft board project

### Test league (use before the 2026 season has real data, and for ongoing dev/testing)
- Current (2026) league_id: `1389464113716957184` ("Fratlee", 12 teams, status pre_draft as of Aug 2026)
- Previous (2025, completed) league_id: `1258884514919223296` (same league lineage via `previous_league_id`, status complete, last_scored_leg 17)
- Verified 2026-08-13: both seasons' settings are identical (waiver_day_of_week: 2, waiver_clear_days: 2, waiver_type: 1, playoff_week_start: 15, playoff_teams: 6, trade_deadline: 11, num_teams: 12, same roster_positions). Anything verified against 2025 data applies unchanged to 2026.
- Sleeper leagues get a new league_id every season, chained via `previous_league_id` (no "next" pointer). The current season's league_id needs to be supplied/updated once per season, not auto-discovered.

## Architecture
Build as a Claude Code Routine (scheduled task), not a bare script with a separate API key. Draws from the existing Claude subscription's usage allowance. Note: a missed scheduled run does not queue up and fire late, it is simply skipped for that day.

A Routine is not a static script. Each firing spins up a fresh Claude agent session with a configured prompt, and that agent does the work live (pulling data via tool calls, reasoning over it, writing it up, publishing). Design the Routine's prompt accordingly, as instructions for an agent, not as a spec for a script.

### Network access note (RESOLVED: direct HTTP blocked in the real Routine environment)
In the Cowork sandbox this project was scoped in, direct `curl`/HTTP client calls to `api.sleeper.app` were blocked by a network allowlist (confirmed empirically, got a 403 at the proxy). The WebFetch tool worked as a workaround there. Locally, confirmed working: plain `curl`/`requests` calls to `api.sleeper.app` succeed (200), no proxy issues (verified 2026-08-13 building `sleeper_api.py`).

**Verified 2026-08-13 via a real one-off Routine firing** (not local, not Cowork): direct `curl` to `api.sleeper.app` from inside the actual deployed Routine cloud environment fails (`curl` exit 56, connection error, HTTP status `000`, i.e. the connection itself is refused/unreachable, not just a proxy 403). So `sleeper_api.py`'s plain `requests`-based calls will **not** work unmodified inside the real Routine. The pipeline's data-pull step needs a WebFetch-based path (or equivalent fetch-tool) for the Routine to actually reach Sleeper's API, matching the Cowork sandbox behavior. Local dev/testing can keep using `sleeper_api.py` as-is (direct HTTP works fine on the dev machine); only the in-Routine execution path needs the fetch-tool fallback. Not yet designed how `sleeper_api.py` should expose both paths (e.g. an injectable fetch function vs. two parallel implementations) — decide when building the actual pipeline step.

### Git push access note (RESOLVED: sources give read-only clone; plain `git push` does NOT work, on any branch)
Tested 2026-08-13 via two one-off Routine firings. `session_context.sources[].git_repository.url` clones fine (read-only), but a plain `git push origin main` from inside that session fails with `403`. Anthropic's Routines docs (code.claude.com/docs/en/routines) state Claude can always push to `claude/`-prefixed branches, so a second probe created a real `claude/publish` branch on GitHub first (repointed GitHub Pages at it too, see below) and retried the exact same push against that branch instead of `main`. **Same 403, verbatim**, even on a `claude/`-prefixed branch. So this is not a branch-naming/protection issue as the docs describe; plain `git push` over the repo's HTTPS remote appears to have no write credential at all inside a Routine session, regardless of target branch. (The connectors list at claude.ai/customize/connectors is empty on this account, only an internal Anthropic connector auto-attaches to routines by default, so there is currently no GitHub write-scoped connector attached either.)

**Not yet resolved. Next thing to test, do not build on an assumption here:** the diagnostic run itself, unprompted, flagged that a GitHub MCP tool like `push_files`/`create_or_update_file` might exist as the actual intended write path (i.e. writing via GitHub's REST contents API through an MCP connector, not raw git), separate from the read-only `sources` git checkout. Need to check claude.ai/customize/connectors for a GitHub connector, attach it to the routine, and retest a push/file-write through that path before finalizing the state/publishing design. Until this is confirmed, do not assume the routine can persist state or publish output at all.

### Publishing branch (set up, pending the write-access fix above)
`claude/publish` branch created and pushed from local dev machine (2026-08-13), GitHub Pages repointed to serve `/docs` from `claude/publish` instead of `main` (`gh api repos/drewkeely3/fantasy-league-recap/pages -X PUT`). Chosen because Routines docs say `claude/`-prefixed branches are always push-accepted, intended to let the routine update state + published output on this branch every firing without needing a human to merge a PR each time (a plain PR-per-run workflow would defeat the "fully unattended daily checkpoint" requirement). Still only usable once the underlying write-access mechanism above is actually confirmed working, since branch naming alone did not fix the 403.

### GitHub repo/privacy note
Repo `drewkeely3/fantasy-league-recap` is public (decided 2026-08-13): GitHub Pages does not support serving from a private repo on the free plan, and the alternatives (paid GitHub Pro, or Cloudflare Pages requiring a connector) weren't worth it once it was confirmed that sharing the Pages URL (`https://drewkeely3.github.io/fantasy-league-recap/`) does not expose or link to the repo itself, only a plain rendered page. Local git identity for this repo is scoped (not global) to `drewkeely3`/`drewkeely3@gmail.com` to match the GitHub account, not the machine's default identity.

### Data-pull layer (built)
`sleeper_api.py` is a thin wrapper over the endpoints above: `get_league`, `get_rosters`, `get_users`, `get_matchups`, `get_transactions`, `get_players_nfl` (return raw parsed JSON), plus one join helper `build_roster_owner_names` (roster_id -> display_name, since raw matchups/transactions only carry IDs). No recap/content logic in this layer, deliberately, that's a separate step built on top.

`get_players_nfl` disk-caches the ~15-16MB payload to `players_nfl_cache.json` (24hr TTL) since it barely changes and is too big to refetch every checkpoint firing.

Verified 2026-08-13 against the real completed 2025 season (league_id `1258884514919223296`, week 10): 12 rosters correctly mapped to display names, 6 matchups paired with correct scores, full transactions list resolved including DEF pseudo-players (Sleeper keys defenses as player_ids like "NO", "DAL", resolves fine through the same players/nfl lookup as regular players). Verification script: `pull_week.py <league_id> <week>`, prints readable structured output for eyeballing, not meant to be the final recap format.

Two things learned from that verification, relevant to later steps:
- The `/rosters` endpoint's `wins`/`losses`/`fpts` fields are always the *current* cumulative totals as of whenever you call it, not a point-in-time snapshot for a given week. Fine for the live Routine (checkpoints always pull "current" standings during an in-progress season), but means you can't retroactively ask "what were standings through week N" for a past week, that data isn't preserved by Sleeper's API.
- `get_transactions` returns failed waiver claims in the raw list (expected, matches "cumulative for the leg" behavior already noted below). Filtering those out is writeup-layer responsibility (per Content scope: "not failed claims, decided those are noise"), not something the pull layer should do, so it can stay a dumb, reusable mirror of the API.

### Pipeline shape (per checkpoint firing)
1. Check persisted state: has this checkpoint already published for the current period? If yes, stop (idempotent, avoids duplicate posts from a safety-net/backup firing). See "Persisted state" below.
2. Pull relevant data from the Sleeper endpoints above (deterministic).
3. Draft the content for this checkpoint (see Content scope and Weekly schedule below), enforcing the no-advice constraint in the draft itself.
4. Run an independent subagent whose only job is to check the draft against the hard no-advice rule (fresh context, not the same reasoning thread that wrote it) and flag or revise anything that crosses the line. Do not publish until this passes.
5. Publish the result.
6. Update persisted state (mark this checkpoint published, record which transaction_ids were included so future checkpoints know what is already reported).

### Persisted state (not yet built)
Two things need small persisted state, likely the same mechanism:
- Whether a given checkpoint has already published for its current period (for idempotency and the safety-net logic).
- Which transaction_ids have already been reported (so the writeup can lead with what is new since last time, rather than repeating the full week's list verbatim every checkpoint).

Sleeper's `/transactions/<leg>` endpoint returns the whole leg's list, not a "since X" delta, so it is inherently cumulative through the week already. No need to manually track "since last checkpoint" at the data-pull level, only at the writeup/presentation level.

## Weekly schedule: 7 checkpoints, all 8:00am ET

Every checkpoint runs at the same time, every day. Each one does two things: recap whatever games finished the day before, and preview today's matchups if any games are happening today.

Cron shape for each: `0 12 * * N` (12:00 UTC = 8am EDT, N = day of week). Not adjusted for DST; after DST ends (Nov 1, 2026) all seven drift together to 7am ET, still safe on both edges. This was deliberately not fixed, the drift is cosmetic only.

Verified safe on both edges: latest realistic game finish (~1am ET, primetime OT) leaves 8am with 7+ hours buffer; earliest realistic same-day kickoff found (NFL London games, 9:30am ET) still leaves 8am comfortably ahead of it.

- **Tuesday** — Post-Week Recap: full close-out of the week including MNF (final scores, closest matchup, blowout, top/worst scorer, bad beat), standings, next week's matchups + byes. The main recap.
- **Wednesday** — Waiver Wire Update: which contested waiver claims cleared and who got added/dropped as a result (not failed claims, decided those are noise, not informative), plus any trades, plus transactions since Tuesday.
- **Thursday** — recap Wednesday (usually nothing) + pregame check-in: this week's matchups + standings, ahead of that night's game.
- **Friday** — recap Thursday's game(s) + preview any Friday game.
- **Saturday** — recap Friday's game(s) if any + preview any Saturday game. Usually nothing to report (Saturday games mostly only happen weeks 15-18ish); skip cleanly rather than post filler, this is expected, not a bug.
- **Sunday** — recap Saturday's game(s) if any + pregame check-in for the main slate + standings snapshot.
- **Monday** — recap Sunday's games (early/late/SNF) + preview tonight's MNF.

Transactions are folded into every checkpoint as a "since last update" section, not a standalone routine.

### Why this shape (do not re-litigate without re-testing)
- Original plan was a single Tuesday trigger. Testing against real 2025 transaction data showed this league's waivers actually clear ~3:10am ET Wednesday (`waiver_day_of_week: 2` decodes to Wednesday, confirmed by matching real batch-processing timestamps, not documented anywhere by Sleeper). A Tuesday-only trigger would have silently omitted waiver results every week.
- Waiver clears are not Wednesday-only either. Real data showed a secondary waiver batch clearing early Friday, consistent with `waiver_clear_days: 2` (a dropped player's own 2-day clock, independent of the league's fixed weekly waiver day). The pipeline does not hardcode "waivers only show up Wednesday", every checkpoint reports whatever is new in that leg's transaction list, whatever day it cleared.
- An earlier draft of the 7-checkpoint schedule used different times per day (morning for some, night for others, trying to catch Friday/Saturday games same-day). This broke on real schedule facts: the 2026 Melbourne game (nominally "Friday" in Australia) actually kicks off 8:35pm ET Thursday because of the date-line crossing, so no single "Friday night" time reliably catches every irregular game. The uniform "recap yesterday, preview today, always 8am" pattern avoids needing to guess same-day kickoff times at all.

## Content scope

**Looking back:**
- Final scores for every matchup
- Closest matchup of the week
- Biggest blowout of the week
- Top scorer, worst scorer
- Bad beat of the week (highest score that still lost)
- Transactions: cleared waiver claims and resulting adds/drops (not failed claims), trades, reported neutrally, what happened not whether it was smart

**Looking forward:**
- Next week's matchups
- Current standings
- Upcoming bye weeks league-wide

## Season boundary (not yet implemented)
Recommended approach: check the league's `playoff_week_start` and bracket size (playoff_teams) each run and skip cleanly once the season is done, rather than manually disabling the Routine. Confirmed via the 2025 league that `last_scored_leg` was 17, matching `playoff_week_start: 15` + a 6-team/3-round bracket, so this league's season is effectively weeks 1-17, not 18. Not yet confirmed as final with the user, revisit when building.

## Publishing (not yet decided)
Push to a free static host (GitHub Pages or Cloudflare Pages under consideration), kept intentionally separate from wherever the Routine itself runs, so the public page stays plain, read-only, no login, no backend. Mechanics of the Routine publishing to it (e.g. committing to a repo that auto-deploys) not yet designed.

## Backlog / future ideas (not building yet)
- Head-to-head history in the "next week's matchups" section ("last time these two played, Team A won 112-98"), purely factual. Straightforward within a single season. If extended across seasons, must match by manager/user_id, not roster_id, since Sleeper reassigns roster_ids fresh each season.
- Seasonal UI theming (Halloween, Thanksgiving, Christmas) for the published page, purely cosmetic, does not touch the no-advice rule, can be date-driven off the recap's own publish date.

## Conventions
- No em dashes in documentation, commit messages, or anything shared with others (inherited from the draft board project's convention).
- Test and verify assumptions against real API data before locking in a design, rather than assuming. This project has already caught two real bugs this way (the Wednesday waiver timing, the Melbourne game's actual US kickoff time). Keep doing that.
