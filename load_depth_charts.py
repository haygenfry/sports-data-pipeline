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
        f"sports/football/nfl/teams/{team_id}/depthcharts"
    )

    response = requests.get(
        url,
        params={"season": 2026},
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    depthchart = data["depthchart"]

    player_count = 0

    for unit in depthchart:

        unit_name = unit["name"]
        positions = unit["positions"]
        position_slots = set(positions.keys())

        if "qb" in position_slots:
            position_group = "OFF"

        elif "pk" in position_slots or "p" in position_slots or "ls" in position_slots:
            position_group = "ST"

        else:
            position_group = "DEF"

        for position_slot, position_data in positions.items():

            position_info = position_data["position"]
            athletes = position_data["athletes"]

            for depth_order, athlete in enumerate(
                athletes,
                start=1
            ):

                cursor.execute(
                    """
                    INSERT INTO nfl_depth_chart (
                        team_id,
                        unit,
                        position_slot,
                        position,
                        position_group,
                        player_id,
                        player_name,
                        depth_order
                    )
                    VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (
                        team_id,
                        position_slot,
                        player_id
                    )
                    DO UPDATE SET
                        unit = EXCLUDED.unit,
                        position = EXCLUDED.position,
                        position_group = EXCLUDED.position_group,
                        player_name = EXCLUDED.player_name,
                        depth_order = EXCLUDED.depth_order
                    """,
                    (
                        team_id,
                        unit_name,
                        position_slot,
                        position_info["abbreviation"],
                        position_group,
                        athlete["id"],
                        athlete["displayName"],
                        depth_order
                    )
                )

                player_count += 1

    connection.commit()

    print(
        f"Loaded {player_count} depth chart rows "
        f"for team {team_id}"
    )

cursor.close()
connection.close()

print("Finished loading 2026 NFL depth charts")