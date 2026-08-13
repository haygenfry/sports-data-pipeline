import requests
import psycopg2

connection = psycopg2.connect(
    host="localhost",
    port=5432,
    database="nfl_data",
    user="nfl_user",
    password="nfl_password"
)

cursor = connection.cursor()

cursor.execute(
    """
    SELECT game_id
    FROM nfl_games
    WHERE season = 2025
      AND completed = TRUE
    ORDER BY game_date;
    """
)

game_ids = [row[0] for row in cursor.fetchall()]

print(f"Found {len(game_ids)} completed games")

for game_id in game_ids:

    url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/summary"

    response = requests.get(
        url,
        params={"event": game_id},
        timeout=30
    )

    data = response.json()

    teams = data["boxscore"]["teams"]

    for team_entry in teams:

        team = team_entry["team"]

        stat_values = {}

        for stat in team_entry["statistics"]:
            stat_values[stat["name"]] = stat.get("displayValue")

        cursor.execute(
            """
            INSERT INTO nfl_team_game_stats (
                game_id,
                team_id,
                team_name,
                home_away,
                first_downs,
                third_down_eff,
                fourth_down_eff,
                total_plays,
                total_yards,
                yards_per_play,
                total_drives,
                passing_yards,
                completions_attempts,
                yards_per_pass,
                interceptions,
                sacks_yards_lost,
                rushing_yards,
                rushing_attempts,
                yards_per_rush,
                red_zone_eff,
                penalties_yards,
                turnovers,
                fumbles_lost,
                defensive_touchdowns,
                possession_time
            )
            VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s
            )
            ON CONFLICT (game_id, team_id)
            DO UPDATE SET
                team_name = EXCLUDED.team_name,
                home_away = EXCLUDED.home_away,
                first_downs = EXCLUDED.first_downs,
                third_down_eff = EXCLUDED.third_down_eff,
                fourth_down_eff = EXCLUDED.fourth_down_eff,
                total_plays = EXCLUDED.total_plays,
                total_yards = EXCLUDED.total_yards,
                yards_per_play = EXCLUDED.yards_per_play,
                total_drives = EXCLUDED.total_drives,
                passing_yards = EXCLUDED.passing_yards,
                completions_attempts = EXCLUDED.completions_attempts,
                yards_per_pass = EXCLUDED.yards_per_pass,
                interceptions = EXCLUDED.interceptions,
                sacks_yards_lost = EXCLUDED.sacks_yards_lost,
                rushing_yards = EXCLUDED.rushing_yards,
                rushing_attempts = EXCLUDED.rushing_attempts,
                yards_per_rush = EXCLUDED.yards_per_rush,
                red_zone_eff = EXCLUDED.red_zone_eff,
                penalties_yards = EXCLUDED.penalties_yards,
                turnovers = EXCLUDED.turnovers,
                fumbles_lost = EXCLUDED.fumbles_lost,
                defensive_touchdowns = EXCLUDED.defensive_touchdowns,
                possession_time = EXCLUDED.possession_time
            """,
            (
                game_id,
                team["id"],
                team["displayName"],
                team_entry["homeAway"],
                stat_values.get("firstDowns"),
                stat_values.get("thirdDownEff"),
                stat_values.get("fourthDownEff"),
                stat_values.get("totalOffensivePlays"),
                stat_values.get("totalYards"),
                stat_values.get("yardsPerPlay"),
                stat_values.get("totalDrives"),
                stat_values.get("netPassingYards"),
                stat_values.get("completionAttempts"),
                stat_values.get("yardsPerPass"),
                stat_values.get("interceptions"),
                stat_values.get("sacksYardsLost"),
                stat_values.get("rushingYards"),
                stat_values.get("rushingAttempts"),
                stat_values.get("yardsPerRushAttempt"),
                stat_values.get("redZoneAttempts"),
                stat_values.get("totalPenaltiesYards"),
                stat_values.get("turnovers"),
                stat_values.get("fumblesLost"),
                stat_values.get("defensiveTouchdowns"),
                stat_values.get("possessionTime")
            )
        )

    connection.commit()

    print(f"Loaded {game_id}")

cursor.close()
connection.close()

print("Finished loading team game stats")