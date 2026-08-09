import requests
import json
import psycopg2

url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"

params = {
    "dates": "2026",
    "seasontype": 2,
    "week": 1
}

response = requests.get(url, params=params, timeout=30)
data = response.json()

events = data["events"]
schedule = []

print(len(events))

for event in events:
    competition = event["competitions"][0]
    competitors = competition["competitors"]
    game_id = event["id"]
    game_date = event["date"]
    venue = competition["venue"]["fullName"]

    home_team = ""
    away_team = ""

    for competitor in competitors:
        team_name = competitor["team"]["displayName"]

        if competitor["homeAway"] == "home":
            home_team = team_name

        if competitor["homeAway"] == "away":
            away_team = team_name

    game = {
        "game_id": game_id,
        "date": game_date,
        "home_team": home_team,
        "away_team": away_team,
        "venue": venue
    }

    schedule.append(game)

with open("week1_schedule.json", "w") as file:
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
            game_date,
            home_team,
            away_team,
            venue
        )
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (game_id) DO NOTHING
        """,
        (
            game["game_id"],
            game["date"],
            game["home_team"],
            game["away_team"],
            game["venue"]
        )
    )

connection.commit()

cursor.close()
connection.close()

print("Loaded NFL schedule into PostgreSQL")