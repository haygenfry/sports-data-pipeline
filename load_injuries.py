import requests
from db import get_connection

SEASON = 2026
WEEK = 2

summary_url = (
    "https://site.api.espn.com/apis/site/v2/"
    "sports/football/nfl/summary"
)

connection = get_connection()

cursor = connection.cursor()

cursor.execute(
    """
    SELECT
        game_id
    FROM nfl_games
    WHERE season = %s
      AND week = %s
      AND completed = FALSE
    ORDER BY game_date;
    """,
    (SEASON, WEEK)
)

game_ids = [row[0] for row in cursor.fetchall()]

print(
    f"Found {len(game_ids)} upcoming games "
    f"for {SEASON} Week {WEEK}"
)


snapshot_insert_sql = """
    INSERT INTO nfl_injury_snapshots (
        game_id,
        team_id
    )
    VALUES (%s, %s)
    RETURNING snapshot_id;
"""

injury_insert_sql = """
    INSERT INTO nfl_injuries (
        snapshot_id,
        game_id,
        team_id,
        player_id,
        player_name,
        jersey,
        position,
        headshot,
        status,
        injury_type,
        injury_location,
        injury_detail,
        injury_side,
        injury_date,
        return_date
    )
    VALUES (
        %s, %s, %s, %s, %s,
        %s, %s, %s, %s, %s,
        %s, %s, %s, %s, %s
    );
"""


for index, game_id in enumerate(game_ids, start=1):

    response = requests.get(
        summary_url,
        params={"event": game_id},
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    injury_groups = data.get("injuries", [])

    loaded_count = 0

    # Build a map so we can still snapshot teams with zero injuries
    injury_group_map = {
        team_group.get("team", {}).get("id"): team_group
        for team_group in injury_groups
    }

    # Get both teams for this game
    cursor.execute(
        """
        SELECT
            away_team_id,
            home_team_id
        FROM nfl_games
        WHERE game_id = %s;
        """,
        (game_id,)
    )

    game_teams = cursor.fetchone()

    if not game_teams:
        continue

    away_team_id, home_team_id = game_teams

    for team_id in (away_team_id, home_team_id):

        cursor.execute(
            snapshot_insert_sql,
            (game_id, team_id)
        )

        snapshot_id = cursor.fetchone()[0]

        team_group = injury_group_map.get(team_id)

        if not team_group:
            print(
                f"Game {game_id} team {team_id}: "
                f"0 injuries"
            )
            continue

        injuries = team_group.get("injuries", [])

        for injury in injuries:

            athlete = injury.get("athlete", {})
            details = injury.get("details", {})

            player_id = athlete.get("id")

            if not player_id:
                continue

            position = (
                athlete.get("position", {})
                .get("abbreviation")
            )

            headshot = (
                athlete.get("headshot", {})
                .get("href")
            )

            cursor.execute(
                injury_insert_sql,
                (
                    snapshot_id,
                    game_id,
                    team_id,
                    player_id,
                    athlete.get("displayName"),
                    athlete.get("jersey"),
                    position,
                    headshot,
                    injury.get("status"),
                    details.get("type"),
                    details.get("location"),
                    details.get("detail"),
                    details.get("side"),
                    injury.get("date"),
                    details.get("returnDate")
                )
            )

            loaded_count += 1

    connection.commit()

    print(
        f"[{index}/{len(game_ids)}] "
        f"Loaded {loaded_count} injuries "
        f"for game {game_id}"
    )


cursor.close()
connection.close()

print("Finished loading injury snapshots")
