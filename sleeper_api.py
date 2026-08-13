"""
Thin data-pull layer over Sleeper's public read-only API. No auth needed.

Each get_* function returns the raw parsed JSON for one endpoint, as documented at
https://docs.sleeper.com/. The only extra behavior here is HTTP mechanics (session
reuse, timeout, raising on error) and, for players_nfl, disk caching since that
payload is ~15MB and does not change within a day.

No recap content, joining across weeks, or "what's newsworthy" logic belongs here.
That's a separate layer built on top of these raw pulls.
"""

import json
import time
from pathlib import Path

import requests

BASE_URL = "https://api.sleeper.app/v1"
TIMEOUT = 15

PLAYERS_CACHE_PATH = Path(__file__).parent / "players_nfl_cache.json"
PLAYERS_CACHE_MAX_AGE_SECONDS = 24 * 60 * 60  # players/nfl changes rarely; refetch at most daily

_session = requests.Session()


def _get(path):
    resp = _session.get(f"{BASE_URL}{path}", timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def get_league(league_id):
    """League settings, season, previous_league_id, roster_positions, etc."""
    return _get(f"/league/{league_id}")


def get_rosters(league_id):
    """List of roster objects: roster_id, owner_id, wins/losses/points settings."""
    return _get(f"/league/{league_id}/rosters")


def get_users(league_id):
    """List of user objects: user_id, display_name, metadata.team_name."""
    return _get(f"/league/{league_id}/users")


def get_matchups(league_id, week):
    """List of per-roster matchup rows for one week: roster_id, matchup_id, points."""
    return _get(f"/league/{league_id}/matchups/{week}")


def get_transactions(league_id, week):
    """
    Transactions for one leg (Sleeper's `week` param here is actually "leg", but for
    a standard league leg == week). Cumulative for the whole leg, not a delta.
    """
    return _get(f"/league/{league_id}/transactions/{week}")


def get_players_nfl(force_refresh=False):
    """
    Full NFL player metadata keyed by player_id. ~15MB; cached to disk since it's
    the same pattern used by the draft board project and this payload barely changes.
    """
    if not force_refresh and PLAYERS_CACHE_PATH.exists():
        age = time.time() - PLAYERS_CACHE_PATH.stat().st_mtime
        if age < PLAYERS_CACHE_MAX_AGE_SECONDS:
            with open(PLAYERS_CACHE_PATH) as f:
                return json.load(f)

    data = _get("/players/nfl")
    with open(PLAYERS_CACHE_PATH, "w") as f:
        json.dump(data, f)
    return data


def build_roster_owner_names(league_id):
    """
    Joins rosters + users into {roster_id: display_name}. Sleeper's raw matchup and
    transaction payloads only carry roster_id/user_id, not human-readable names.
    """
    rosters = get_rosters(league_id)
    users = get_users(league_id)
    display_name_by_user_id = {u["user_id"]: u["display_name"] for u in users}

    names = {}
    for roster in rosters:
        owner_id = roster.get("owner_id")
        names[roster["roster_id"]] = display_name_by_user_id.get(owner_id, f"(unknown owner_id={owner_id})")
    return names
