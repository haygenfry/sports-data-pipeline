import requests
import json
import psycopg2

url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"

schedule = []

for week in range(1, 19):

    params = {
        "dates": "2026",
        "seasontype": 2,
        "week": week
    }

    response = requests.get(url, params=params, timeout=30)
    data = response.json()

    events = data["events"]

    for event in events:
        competition = event["competitions"][0]
        competitors = competition["competitors"]
        game_id = event["id"]
        game_date = event["date"]
        venue = competition["venue"]["fullName"]

        home_team = ""
        away_team = ""
        home_logo = ""
        away_logo = ""

        for competitor in competitors:
            team_name = competitor["team"]["displayName"]
            team_logo = competitor["team"]["logo"]

            if competitor["homeAway"] == "home":
                home_team = team_name
                home_logo = team_logo

            if competitor["homeAway"] == "away":
                away_team = team_name
                away_logo = team_logo

        game = {
            "game_id": game_id,
            "season": 2026,
            "week": week,
            "date": game_date,
            "home_team": home_team,
            "away_team": away_team,
            "home_logo": home_logo,
            "away_logo": away_logo,
            "venue": venue
        }

        schedule.append(game)

with open("2026_schedule.json", "w") as file:
    json.dump(schedule, file, indent=4)

connection = psycopg2.connect(
    host="localhost",
    port=5432,
    database="nfl_data",
    user="nfl_user",
    password="nfl_password"
)

cursor = connection.cursor()

for game in schedule:
    cursor.execute(
        """
        INSERT INTO nfl_games (
            game_id,
            season,
            week,
            game_date,
            home_team,
            away_team,
            home_logo,
            away_logo,
            venue
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (game_id)
        DO UPDATE SET
            season = EXCLUDED.season,
            week = EXCLUDED.week,
            game_date = EXCLUDED.game_date,
            home_team = EXCLUDED.home_team,
            away_team = EXCLUDED.away_team,
            home_logo = EXCLUDED.home_logo,
            away_logo = EXCLUDED.away_logo,
            venue = EXCLUDED.venue
        """,
        (
            game["game_id"],
            game["season"],
            game["week"],
            game["date"],
            game["home_team"],
            game["away_team"],
            game["home_logo"],
            game["away_logo"],
            game["venue"]
        )
    )

connection.commit()

cursor.close()
connection.close()

print("Loaded NFL schedule into PostgreSQL")