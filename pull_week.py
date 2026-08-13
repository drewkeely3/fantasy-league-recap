"""
Verification script for sleeper_api.py. Pulls one week's worth of data from a real
completed season and prints it in a readable, structured form so the pull/parse
can be eyeballed for correctness before any recap content is built on top of it.

Usage: python3 pull_week.py <league_id> <week>
"""

import sys

import sleeper_api


def print_header(title):
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


def print_users_and_rosters(league_id):
    print_header("USERS / ROSTERS")
    rosters = sleeper_api.get_rosters(league_id)
    owner_names = sleeper_api.build_roster_owner_names(league_id)

    for roster in sorted(rosters, key=lambda r: r["roster_id"]):
        rid = roster["roster_id"]
        settings = roster.get("settings", {})
        record = f"{settings.get('wins', 0)}-{settings.get('losses', 0)}-{settings.get('ties', 0)}"
        fpts = settings.get("fpts", 0) + settings.get("fpts_decimal", 0) / 100
        print(f"  roster_id {rid:>2}  {owner_names[rid]:<20}  record {record:<8}  fpts {fpts}")


def print_matchups(league_id, week):
    print_header(f"WEEK {week} MATCHUPS")
    matchups = sleeper_api.get_matchups(league_id, week)
    owner_names = sleeper_api.build_roster_owner_names(league_id)

    by_matchup_id = {}
    for row in matchups:
        by_matchup_id.setdefault(row["matchup_id"], []).append(row)

    for matchup_id, rows in sorted(by_matchup_id.items()):
        rows = sorted(rows, key=lambda r: -r["points"])
        parts = [f"{owner_names[r['roster_id']]} ({r['points']})" for r in rows]
        print(f"  matchup {matchup_id}: " + "  vs  ".join(parts))


def print_transactions(league_id, week):
    print_header(f"WEEK {week} TRANSACTIONS")
    transactions = sleeper_api.get_transactions(league_id, week)
    owner_names = sleeper_api.build_roster_owner_names(league_id)
    players = sleeper_api.get_players_nfl()

    def player_label(player_id):
        p = players.get(player_id)
        if not p:
            return f"player_id={player_id}"
        return f"{p.get('full_name', player_id)} ({p.get('position', '?')})"

    if not transactions:
        print("  (none)")
        return

    for tx in transactions:
        rosters_involved = ", ".join(owner_names.get(rid, str(rid)) for rid in tx.get("roster_ids", []))
        print(f"  [{tx['type']}/{tx['status']}] rosters: {rosters_involved}")
        for player_id, roster_id in (tx.get("adds") or {}).items():
            print(f"      + add  {player_label(player_id):<28} -> {owner_names.get(roster_id, roster_id)}")
        for player_id, roster_id in (tx.get("drops") or {}).items():
            print(f"      - drop {player_label(player_id):<28} <- {owner_names.get(roster_id, roster_id)}")


def main():
    if len(sys.argv) != 3:
        print("Usage: python3 pull_week.py <league_id> <week>")
        sys.exit(1)

    league_id, week = sys.argv[1], int(sys.argv[2])

    league = sleeper_api.get_league(league_id)
    print_header("LEAGUE")
    print(f"  name: {league['name']}")
    print(f"  season: {league['season']}  status: {league['status']}")
    print(f"  previous_league_id: {league.get('previous_league_id')}")

    print_users_and_rosters(league_id)
    print_matchups(league_id, week)
    print_transactions(league_id, week)


if __name__ == "__main__":
    main()
