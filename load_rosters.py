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
    SELECT DISTINCT team_id
    FROM nfl_team_standings
    WHERE season = 2026
    ORDER BY team_id;
    """
)

team_ids = [row[0] for row in cursor.fetchall()]

print(f"Found {len(team_ids)} teams")

for team_id in team_ids:

    url = (
        f"https://site.api.espn.com/apis/site/v2/"
        f"sports/football/nfl/teams/{team_id}/roster"
    )

    response = requests.get(
        url,
        params={"season": 2026},
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    athletes = data["athletes"]

    player_count = 0

    for group in athletes:

        position_group = group["position"]

        for athlete in group["items"]:

            position = athlete.get("position", {})

            cursor.execute(
                """
                INSERT INTO nfl_players (
                    player_id,
                    team_id,
                    player_name,
                    first_name,
                    last_name,
                    jersey,
                    position,
                    position_name,
                    position_group,
                    status,
                    experience_years,
                    height_inches,
                    weight_lbs,
                    college,
                    headshot
                )
                VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s
                )
                ON CONFLICT (player_id)
                DO UPDATE SET
                    team_id = EXCLUDED.team_id,
                    player_name = EXCLUDED.player_name,
                    first_name = EXCLUDED.first_name,
                    last_name = EXCLUDED.last_name,
                    jersey = EXCLUDED.jersey,
                    position = EXCLUDED.position,
                    position_name = EXCLUDED.position_name,
                    position_group = EXCLUDED.position_group,
                    status = EXCLUDED.status,
                    experience_years = EXCLUDED.experience_years,
                    height_inches = EXCLUDED.height_inches,
                    weight_lbs = EXCLUDED.weight_lbs,
                    college = EXCLUDED.college,
                    headshot = EXCLUDED.headshot
                """,
                (
                    athlete["id"],
                    team_id,
                    athlete["displayName"],
                    athlete.get("firstName"),
                    athlete.get("lastName"),
                    athlete.get("jersey"),
                    position.get("abbreviation"),
                    position.get("displayName"),
                    position_group,
                    athlete.get("status", {}).get("name"),
                    athlete.get("experience", {}).get("years"),
                    athlete.get("height"),
                    athlete.get("weight"),
                    athlete.get("college", {}).get("shortName"),
                    athlete.get("headshot", {}).get("href")
                )
            )

            player_count += 1

    connection.commit()

    print(
        f"Loaded {player_count} players "
        f"for team {team_id}"
    )

cursor.close()
connection.close()

print("Finished loading 2026 NFL rosters")