import requests
from db import get_connection

summary_url = (
    "https://site.api.espn.com/apis/site/v2/"
    "sports/football/nfl/summary"
)

connection = get_connection()

def clean_value(value):
    if value in ("--", "", None):
        return None
    return value

cursor = connection.cursor()

cursor.execute(
    """
    SELECT game_id
    FROM nfl_games
    WHERE season = 2026
      AND completed = TRUE
    ORDER BY game_date;
    """
)

game_ids = [row[0] for row in cursor.fetchall()]

print(f"Found {len(game_ids)} completed games")


column_mapping = {
    "game_id": "game_id",
    "team_id": "team_id",
    "team_name": "team_name",
    "player_id": "player_id",
    "player_name": "player_name",
    "jersey": "jersey",
    "headshot": "headshot",

    "completions_attempts": "completions/passingAttempts",
    "passing_yards": "passingYards",
    "yards_per_pass_attempt": "yardsPerPassAttempt",
    "passing_touchdowns": "passingTouchdowns",
    "passing_interceptions": "passingInterceptions",
    "sacks_sack_yards_lost": "sacks-sackYardsLost",
    "qbr": "adjQBR",
    "passer_rating": "QBRating",

    "rushing_attempts": "rushingAttempts",
    "rushing_yards": "rushingYards",
    "yards_per_rush_attempt": "yardsPerRushAttempt",
    "rushing_touchdowns": "rushingTouchdowns",
    "long_rushing": "longRushing",

    "receptions": "receptions",
    "receiving_yards": "receivingYards",
    "yards_per_reception": "yardsPerReception",
    "receiving_touchdowns": "receivingTouchdowns",
    "long_reception": "longReception",
    "receiving_targets": "receivingTargets",

    "fumbles": "fumbles",
    "fumbles_lost": "fumblesLost",
    "fumbles_recovered": "fumblesRecovered",

    "total_tackles": "totalTackles",
    "solo_tackles": "soloTackles",
    "sacks": "sacks",
    "tackles_for_loss": "tacklesForLoss",
    "passes_defended": "passesDefended",
    "qb_hits": "QBHits",
    "defensive_touchdowns": "defensiveTouchdowns",

    "defensive_interceptions": "defensiveInterceptions",
    "interception_yards": "interceptionYards",
    "interception_touchdowns": "interceptionTouchdowns",

    "kick_returns": "kickReturns",
    "kick_return_yards": "kickReturnYards",
    "yards_per_kick_return": "yardsPerKickReturn",
    "long_kick_return": "longKickReturn",
    "kick_return_touchdowns": "kickReturnTouchdowns",

    "punt_returns": "puntReturns",
    "punt_return_yards": "puntReturnYards",
    "yards_per_punt_return": "yardsPerPuntReturn",
    "long_punt_return": "longPuntReturn",
    "punt_return_touchdowns": "puntReturnTouchdowns",

    "field_goals_made_attempted": "fieldGoalsMade/fieldGoalAttempts",
    "field_goal_pct": "fieldGoalPct",
    "long_field_goal_made": "longFieldGoalMade",
    "extra_points_made_attempted": "extraPointsMade/extraPointAttempts",
    "total_kicking_points": "totalKickingPoints",

    "punts": "punts",
    "punt_yards": "puntYards",
    "gross_avg_punt_yards": "grossAvgPuntYards",
    "touchbacks": "touchbacks",
    "punts_inside_20": "puntsInside20",
    "long_punt": "longPunt"
}

columns = list(column_mapping.keys())

column_sql = ", ".join(columns)
placeholder_sql = ", ".join(["%s"] * len(columns))

update_columns = [
    column
    for column in columns
    if column not in ("game_id", "player_id")
]

update_sql = ", ".join(
    f"{column} = EXCLUDED.{column}"
    for column in update_columns
)

insert_sql = f"""
    INSERT INTO nfl_player_game_stats (
        {column_sql}
    )
    VALUES (
        {placeholder_sql}
    )
    ON CONFLICT (game_id, player_id)
    DO UPDATE SET
        {update_sql};
"""


for index, game_id in enumerate(game_ids, start=1):

    response = requests.get(
        summary_url,
        params={"event": game_id},
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    players = data["boxscore"]["players"]

    player_rows = {}

    for team_entry in players:
        team = team_entry["team"]

        for stat_group in team_entry["statistics"]:
            category = stat_group["name"]
            keys = stat_group["keys"]

            for athlete_entry in stat_group["athletes"]:
                athlete = athlete_entry["athlete"]
                stats = athlete_entry["stats"]

                player_id = athlete["id"]

                if player_id not in player_rows:
                    player_rows[player_id] = {
                        "game_id": game_id,
                        "team_id": team["id"],
                        "team_name": team["displayName"],
                        "player_id": player_id,
                        "player_name": athlete["displayName"],
                        "jersey": athlete.get("jersey"),
                        "headshot": athlete.get(
                            "headshot",
                            {}
                        ).get("href")
                    }

                stat_values = dict(zip(keys, stats))

                if category == "passing":
                    if "interceptions" in stat_values:
                        stat_values["passingInterceptions"] = (
                            stat_values.pop("interceptions")
                        )

                if category == "interceptions":
                    if "interceptions" in stat_values:
                        stat_values["defensiveInterceptions"] = (
                            stat_values.pop("interceptions")
                        )

                for stat_name, stat_value in stat_values.items():
                    player_rows[player_id][stat_name] = stat_value

    for row in player_rows.values():

        values = [
            clean_value(row.get(espn_field))
            for espn_field in column_mapping.values()
        ]

        cursor.execute(
            insert_sql,
            values
        )

    connection.commit()

    print(
        f"[{index}/{len(game_ids)}] "
        f"Loaded {len(player_rows)} players "
        f"for game {game_id}"
    )


cursor.close()
connection.close()

print("Finished loading player game stats")
