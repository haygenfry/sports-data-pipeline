import requests
import psycopg2

url = "https://site.api.espn.com/apis/v2/sports/football/nfl/standings"

params = {
    "season": 2026
}

response = requests.get(url, params=params, timeout=30)
data = response.json()

standings = []

for conference in data["children"]:

    conference_name = conference["abbreviation"]

    entries = conference["standings"]["entries"]

    for entry in entries:

        team = entry["team"]
        stats = entry["stats"]

        stat_values = {}

        for stat in stats:
            stat_values[stat["type"]] = stat.get("displayValue")

        team_standing = {
            "team_id": team["id"],
            "team_name": team["displayName"],
            "conference": conference_name,
            "overall_record": stat_values.get("total"),
            "home_record": stat_values.get("home"),
            "road_record": stat_values.get("road"),
            "division_record": stat_values.get("vsdiv"),
            "conference_record": stat_values.get("vsconf"),
            "streak": stat_values.get("streak"),
            "conference_seed": stat_values.get("playoffseed"),
            "points_for": stat_values.get("pointsfor"),
            "points_against": stat_values.get("pointsagainst"),
            "point_differential": stat_values.get("pointdifferential")
        }

        standings.append(team_standing)

connection = psycopg2.connect(
    host="localhost",
    port=5432,
    database="nfl_data",
    user="nfl_user",
    password="nfl_password"
)

cursor = connection.cursor()

for team in standings:
    cursor.execute(
        """
        INSERT INTO nfl_team_standings (
            season,
            team_id,
            team_name,
            conference,
            overall_record,
            home_record,
            road_record,
            division_record,
            conference_record,
            streak,
            conference_seed,
            points_for,
            points_against,
            point_differential
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (season, team_id)
        DO UPDATE SET
            team_name = EXCLUDED.team_name,
            conference = EXCLUDED.conference,
            overall_record = EXCLUDED.overall_record,
            home_record = EXCLUDED.home_record,
            road_record = EXCLUDED.road_record,
            division_record = EXCLUDED.division_record,
            conference_record = EXCLUDED.conference_record,
            streak = EXCLUDED.streak,
            conference_seed = EXCLUDED.conference_seed,
            points_for = EXCLUDED.points_for,
            points_against = EXCLUDED.points_against,
            point_differential = EXCLUDED.point_differential
        """,
        (
            2026,
            team["team_id"],
            team["team_name"],
            team["conference"],
            team["overall_record"],
            team["home_record"],
            team["road_record"],
            team["division_record"],
            team["conference_record"],
            team["streak"],
            team["conference_seed"],
            team["points_for"],
            team["points_against"],
            team["point_differential"]
        )
    )

connection.commit()

cursor.close()
connection.close()

print("Loaded NFL standings into PostgreSQL")