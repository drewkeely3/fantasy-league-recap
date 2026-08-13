"""
Thin wrapper over ESPN's public, read-only NFL scoreboard API. No auth needed.

Sleeper's API (see sleeper_api.py) only has fantasy week-level score totals, no
per-game schedule/kickoff-time data, which several checkpoints need (e.g. "recap
Thursday's game" or "is there a Saturday game this week"). This fills that gap.
"""

import re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import requests

BASE_URL = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
SUMMARY_URL = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/summary"
TIMEOUT = 15
ET = ZoneInfo("America/New_York")

_session = requests.Session()

# Verified against 4 real 2025 games (GB@PHI, MIA@BUF, TB@NE, CHI@NYG, week 10):
# this exact phrasing is consistent, "during the play" is the only variant seen,
# no "on the play" or other wording found despite checking broadly.
_INJURED_RE = re.compile(r"([A-Z]{2,3}-[A-Z]\.[A-Za-z'\-]+) was injured during the play")
_RETURNED_RE = re.compile(r"Injury Update: ([A-Z]{2,3}-[A-Z]\.[A-Za-z'\-]+) has returned to the game")


def get_scoreboard(season, week, season_type=2):
    """
    Raw scoreboard for one week. season_type: 1=preseason, 2=regular, 3=postseason.
    Returns ESPN's parsed JSON (event list with kickoff time, teams, status).
    """
    params = {"week": week, "seasontype": season_type, "dates": season}
    resp = _session.get(BASE_URL, params=params, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def get_summary(event_id):
    """
    Full per-game data: boxscore (real per-game player stats), drives (play-by-
    play, has real-time injury events), injuries (that game's pre-game injury
    report), and article.story (full recap text, ~8000 chars). event_id comes
    from get_scoreboard's event list.
    """
    resp = _session.get(SUMMARY_URL, params={"event": event_id}, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def injury_exits(event_id):
    """
    Players tagged as injured during this game's play-by-play with no later
    "has returned to the game" update - real evidence they left and didn't come
    back, not just a bad game. Keyed as "<TEAM>-<F.Lastname>" (ESPN's own
    play-text format, avoids same-surname collisions between the two teams).
    Tracked in chronological play order, so a player hurt twice (left, came
    back, got hurt again and didn't return) resolves correctly off their last
    event, not just "were they ever tagged injured."

    Verified 2026-08-13 against 4 real games (2025 week 10): correctly found
    known real exits (e.g. GB's E.Jenkins, BUF's L.Jackson) with no return tag.

    Known gap, confirmed across multiple real games: ESPN sometimes logs a
    "has returned" update with no matching "was injured" tag ever appearing for
    that player (a data completeness issue on ESPN's side, not a bug here).
    This makes the function under-count (a real injury exit can go undetected
    if never tagged) but never over-count - a player only appears in this
    function's output if they have an explicit injury tag AND no subsequent
    return tag, so failures lean toward "miss it" not "wrongly flag it",
    consistent with this project's "if in doubt, leave it out" rule.
    """
    data = get_summary(event_id)
    drives = data.get("drives", {}).get("previous", [])
    last_event = {}
    for drive in drives:
        for play in drive.get("plays", []):
            text = play.get("text", "")
            for player in _INJURED_RE.findall(text):
                last_event[player] = "injured"
            for player in _RETURNED_RE.findall(text):
                last_event[player] = "returned"
    return [player for player, event in last_event.items() if event == "injured"]


def games_by_et_weekday(season, week, season_type=2):
    """
    Groups this week's games by the weekday (America/New_York) they kick off on,
    e.g. {"Thursday": [...], "Sunday": [...], "Monday": [...]}. Each game dict has
    kickoff_et, teams, and finished (bool, from ESPN's STATUS_FINAL state).
    """
    data = get_scoreboard(season, week, season_type)
    by_weekday = {}
    for event in data.get("events", []):
        kickoff_utc = datetime.fromisoformat(event["date"].replace("Z", "+00:00"))
        kickoff_et = kickoff_utc.astimezone(ET)
        comp = event["competitions"][0]
        teams = [c["team"]["abbreviation"] for c in comp["competitors"]]
        finished = comp.get("status", {}).get("type", {}).get("name") == "STATUS_FINAL"
        weekday = kickoff_et.strftime("%A")
        by_weekday.setdefault(weekday, []).append({
            "kickoff_et": kickoff_et.isoformat(),
            "teams": teams,
            "finished": finished,
        })
    return by_weekday
