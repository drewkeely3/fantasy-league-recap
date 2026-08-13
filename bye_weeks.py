"""
Hardcoded NFL bye weeks, per season. Not in Sleeper's API (same gap the draft
board project hit), user-supplied each season, not auto-updated.
"""

BYE_WEEKS = {
    "2025": {
        "ARI": 8, "ATL": 5, "BAL": 7, "BUF": 7, "CAR": 14, "CHI": 5,
        "CIN": 10, "CLE": 9, "DAL": 10, "DEN": 12, "DET": 8, "GB": 5,
        "HOU": 6, "IND": 11, "JAX": 8, "KC": 10, "LAC": 12, "LAR": 8,
        "LV": 8, "MIA": 12, "MIN": 6, "NE": 14, "NO": 11, "NYG": 14,
        "NYJ": 9, "PHI": 9, "PIT": 5, "SEA": 8, "SF": 14, "TB": 9,
        "TEN": 10, "WAS": 12,
    },
    "2026": {
        "ARI": 14, "ATL": 11, "BAL": 13, "BUF": 7, "CAR": 5, "CHI": 10,
        "CIN": 6, "CLE": 11, "DAL": 14, "DEN": 10, "DET": 6, "GB": 11,
        "HOU": 8, "IND": 13, "JAX": 7, "KC": 5, "LAC": 7, "LAR": 11,
        "LV": 13, "MIA": 6, "MIN": 6, "NE": 11, "NO": 8, "NYG": 8,
        "NYJ": 13, "PHI": 10, "PIT": 9, "SEA": 11, "SF": 8, "TB": 10,
        "TEN": 9, "WAS": 7,
    },
}


def teams_on_bye(season, week):
    return [team for team, bye_week in BYE_WEEKS[season].items() if bye_week == week]
