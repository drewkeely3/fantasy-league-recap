# Fantasy League Recap

## Status
Design phase complete (schedule, content scope, transaction mechanics all verified against real data). Data-pull layer built and verified against real 2025 season data (see "Data-pull layer" under Architecture). Recap content generation not yet built. This file is the handoff from a scoping conversation done in Cowork; continue building from here.

## What this is
An automated, scheduled system that generates a recurring fantasy football league recap for a Sleeper league, built as a Claude Code Routine (scheduled task). Shared with the whole league, not just the user.

Follow-on project to the fantasy draft board (see `draft-board-CLAUDE.md` in this folder if present) but scoped separately. Distinct from a personal season dashboard project that will be built later.

## Hard constraint: informational only, no strategic edge
This is the most important rule for this project. The recap must never contain advice, recommendations, or anything that gives any manager (including the user) an edge over others. No "you should target X," no "Team Y is weak at Z," no commentary implying a transaction was good or bad. Purely factual, retrospective, and schedule-oriented content. If in doubt whether something crosses into advice, leave it out.

This applies to every checkpoint below, not just the main weekly recap.

**Tone clarification (decided with user 2026-08-13):** humor, mockery, and roasting are fine and encouraged (casual, a little mean, not corny) - this is a tone/style choice, not a hard-constraint violation by itself. The hard constraint is about *time direction*, not about being nice. Content must stay strictly retrospective (jokes about what already happened and can't be changed, e.g. "started a guy on bye and got zero, rough week") and never slide into forward-looking framing (e.g. "remember to check the injury report next time," anything implying what a manager should do differently going forward). The test isn't "is this mean," it's "does this help anyone make a better decision going forward." Retrospective roasting doesn't hand anyone a competitive edge since the game already happened; forward-looking advice does, regardless of how nicely or meanly it's phrased. The no-advice-check subagent (see Pipeline shape) needs to apply this exact distinction, not a blanket "no negativity" filter.

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

### Git push access note (RESOLVED: needed the Claude GitHub App installed on the repo, not just "connect GitHub account")
Tested 2026-08-13 via three one-off Routine firings. `session_context.sources[].git_repository.url` clones fine (read-only) regardless. First two probes found `git push` failing with `403` on both `main` and a `claude/`-prefixed branch (`claude/publish`), even after doing the claude.ai "connect your GitHub account" step that's required just to reference a repo by URL when creating a routine. Root cause, found by checking the routine's repository picker in the web UI: it showed "No repositories found" — the "connect GitHub account" step only links identity, it does **not** install anything that grants write access. Cloning worked anyway only because the repo is public (anonymous read access, no auth needed).

**Fix:** installed the actual Claude GitHub App (github.com/apps/claude → Install), explicitly scoped to "Only select repositories" → `drewkeely3/fantasy-league-recap` only (not "All repositories", no reason to grant it access to other repos). This grants real read/write permission on code, PRs, actions, etc. A third probe after installing pushed to `claude/publish` cleanly, no 403. **Confirmed working end to end 2026-08-13.**

If this project (or any other repo) ever needs a Routine to push again, the checklist is: 1) repo added to the routine's sources, 2) GitHub account connected at claude.ai (identity only), 3) **the Claude GitHub App actually installed on that specific repo** (github.com/apps/claude) — step 3 is the one that's easy to skip since nothing in the routine-creation flow forces it, and its absence fails silently as a plain 403 that looks like a generic permissions error rather than "app not installed."

### Publishing branch (RESOLVED, working)
`claude/publish` branch on the repo is the live branch for both state and published output — NOT `main`. GitHub Pages is repointed to serve `/docs` from `claude/publish` (`gh api repos/drewkeely3/fantasy-league-recap/pages -X PUT`). Chosen because Anthropic's Routines docs say `claude/`-prefixed branches are always push-accepted (avoiding the branch-protection/PR-review path non-`claude/` branches can hit), letting the routine update state + published output every firing with no human merging a PR each time — a plain PR-per-run workflow would defeat the "fully unattended daily checkpoint" requirement. `main` still exists and is kept roughly in sync during setup, but going forward the routine's prompt should explicitly check out `claude/publish` first thing after cloning (sources clone the default branch, `main`, unless told otherwise) and do all its work there.

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

### Persisted state (mechanism confirmed working 2026-08-13, schema built, pipeline usage not yet wired up)
Two things need small persisted state, both via the same mechanism:
- Whether a given checkpoint has already published for its current period (for idempotency and the safety-net logic).
- Which transaction_ids have already been reported (so the writeup can lead with what is new since last time, rather than repeating the full week's list verbatim every checkpoint).

Sleeper's `/transactions/<leg>` endpoint returns the whole leg's list, not a "since X" delta, so it is inherently cumulative through the week already. No need to manually track "since last checkpoint" at the data-pull level, only at the writeup/presentation level.

**Mechanism:** a JSON file per season under `state/` (e.g. `state/2026.json`, see `state/README.md` for the exact schema) committed directly to the `claude/publish` branch of this same repo — no separate database, no second credential, just `git add`/`commit`/`push` from inside the routine session, confirmed working per the git push access note above. Every checkpoint firing: clone repo, checkout `claude/publish`, read the season's state file, do the pipeline work, write the updated state file back, commit, push. Not yet wired into an actual end-to-end checkpoint prompt — that's the next build step, not this one.

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

## League economics (buy-in/payouts, PENDING confirmation)
This is a buy-in league; user wants to reference standing-relative-to-the-money-pot
in jokes (e.g. a manager on a losing streak "made a $25 donation, thanks"), added
2026-08-13. Strictly retrospective framing only, same rule as other roasting per
the Tone clarification above. Tentative numbers per user, **not confirmed, do not
hardcode into any real checkpoint yet**: $25 entry/team, payouts $250 to 1st, $25
to 2nd, $25 to regular season champion (12 teams x $25 = $300 pot, matches the
$250+$25+$25 payout total). User will confirm or correct these after this season's
draft (2026-08-25). Revisit before building this content feature for real.

## Content scope

**Looking back:**
- Final scores for every matchup
- Closest matchup of the week
- Biggest blowout of the week
- Top scorer, worst scorer
- Bad beat of the week (highest score that still lost)
- Transactions: cleared waiver claims and resulting adds/drops (not failed claims), trades, reported neutrally, what happened not whether it was smart
- Streaks (added 2026-08-13): win/loss streaks, or a manager being the highest/lowest scorer N weeks running. Needs pulling multiple weeks of matchup history, not just the current week.
- Boom/bust player callouts (added 2026-08-13): a player who went off or cratered relative to what's typical, and how it affected their fantasy manager (e.g. "X went off for [NFL team], didn't matter, Y still lost"). Sourced from the per-player points already in each matchup's `players_points`/`starters` fields, no new data pull needed.
- Started-an-inactive-player callouts (added 2026-08-13, mechanism verified against real data, see below): a manager who started someone on bye, injured, or otherwise inactive, who scored 0 as a result. Must stay strictly retrospective per the tone clarification above.

  **Reliability tiers, most to least certain** (tested against real 2025 week 10 data):
  1. On bye that week (bye_weeks.py) - 100% certain, deterministic.
  2. On that specific game's injury report as Out/Doubtful (ESPN's per-game `summary?event=<id>` endpoint has this, historically tied to that exact game - NOT Sleeper's `injury_status`/`status` fields, which only reflect current state, confirmed unreliable for historical weeks, see below).
  3. Zero stats across every box score category for that game (ESPN summary endpoint again) - decent evidence of minimal involvement but not certain, use softer language ("quiet week," "didn't factor in") rather than claiming they didn't play, unless also confirmed via tier 1 or 2.

  Only use confident "started an inactive player" language for tiers 1-2. For tier 3 alone, don't claim certainty.

  **Sleeper's players/nfl payload is current-only, not historical - confirmed three separate ways** while testing this feature against real 2025 data (2026-08-13): (a) already known for standings/records, (b) `injury_status`/`status` reflect current state only, found 4 real week-10-2025 zero-point starters all showing "no injury, Active" today regardless of what was true then, (c) even `team` is current-only - tested "DJ Moore" assuming his current team (BUF), got zero stats, looked like a DNP; he was actually traded from Chicago to Buffalo after the 2025 season, so week 10 2025 needed to be checked against his real team at the time (CHI), where he shows a real, legitimate bad game (0 REC on 4 TGTS), not an inactive one at all.

  **Practical implication:** this means the detection logic itself is sound and will work correctly during the live 2026 season (current team/status is always accurate for a same-week checkpoint, no trade-lag problem exists in real time), but it **cannot be reliably validated against 2025 historical data** the way everything else in this project has been tested, since old team/injury state isn't preserved anywhere queryable. Validate this specific feature for real once actual 2026 games are being played, not before. Match players between Sleeper and ESPN by name (normalized, no shared ID between the two systems, same category of problem the draft board project solved for PDF-to-Sleeper name matching) - always resolve team/roster context from the specific historical game being checked, never from a player's current Sleeper record, when doing any retroactive analysis.

**Looking forward:**
- Next week's matchups
- Current standings
- Upcoming bye weeks league-wide

## Season boundary (RESOLVED, confirmed with user 2026-08-13)
Check the league's `status` field each run and only proceed if it's exactly `"in_season"`; skip cleanly (no publish, no state update) for any other value. Simpler than an earlier draft that proposed computing from `playoff_week_start` + bracket size: `status` already encodes the answer directly, confirmed against real data (2025 league: `status: "complete"` correlates exactly with `last_scored_leg: 17`, matching `playoff_week_start: 15` + a 6-team/3-round bracket). This single check also covers the *other* boundary the bracket-math approach didn't: `status` is `"pre_draft"` before the draft happens and presumably `"drafting"` during it (the 2026 league showed `pre_draft` as of Aug 2026), so checkpoints that fire before the season starts skip cleanly too, not just ones after it ends.

## Publishing
RESOLVED, see "Publishing branch" under Architecture above: GitHub Pages, `claude/publish` branch, `/docs` folder, plain read-only public page, no login, no backend.

### UI navigation (not yet designed, notes only)
Deferred until a real design/mockup pass with the user, but two decisions already made shape it: page structure is one continuously-updated page per week (current week on top, archive of past weeks below/linked), and checkpoint output is tagged by content category (`recap_narrative`, `transactions`, `standings`, `schedule`, `awards`, see Content scope) specifically so a tabbed or sectioned layout (user suggested something like "NFL team report / fantasy report / transactions" tabs, 2026-08-13) can be built later without re-parsing old published content. Don't build the actual tabs/nav yet, just keep output categorized so the option stays open.

## Backlog / future ideas (not building yet)
- Head-to-head history in the "next week's matchups" section ("last time these two played, Team A won 112-98"), purely factual. Straightforward within a single season. If extended across seasons, must match by manager/user_id, not roster_id, since Sleeper reassigns roster_ids fresh each season.
- Seasonal UI theming (Halloween, Thanksgiving, Christmas) for the published page, purely cosmetic, does not touch the no-advice rule, can be date-driven off the recap's own publish date.
- Money/buy-in jokes tied to standing relative to the payout structure, see "League economics" above, blocked on the user confirming real numbers after the 2026-08-25 draft.

## Conventions
- No em dashes in documentation, commit messages, or anything shared with others (inherited from the draft board project's convention).
- Test and verify assumptions against real API data before locking in a design, rather than assuming. This project has already caught two real bugs this way (the Wednesday waiver timing, the Melbourne game's actual US kickoff time). Keep doing that.
