"""
Thin wrapper over ESPN's public, read-only NFL scoreboard API. No auth needed.

Sleeper's API (see sleeper_api.py) only has fantasy week-level score totals, no
per-game schedule/kickoff-time data, which several checkpoints need (e.g. "recap
Thursday's game" or "is there a Saturday game this week"). This fills that gap.
"""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import requests

BASE_URL = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
TIMEOUT = 15
ET = ZoneInfo("America/New_York")

_session = requests.Session()


def get_scoreboard(season, week, season_type=2):
    """
    Raw scoreboard for one week. season_type: 1=preseason, 2=regular, 3=postseason.
    Returns ESPN's parsed JSON (event list with kickoff time, teams, status).
    """
    params = {"week": week, "seasontype": season_type, "dates": season}
    resp = _session.get(BASE_URL, params=params, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


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
