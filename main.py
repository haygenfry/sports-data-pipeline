import requests
import json

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