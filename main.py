import requests

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

    home_team = ""
    away_team = ""

    for competitor in competitors:
        team_name = competitor["team"]["displayName"]

        if competitor["homeAway"] == "home":
            home_team = team_name

        if competitor["homeAway"] == "away":
            away_team = team_name

    game = {
        "home_team": home_team,
        "away_team": away_team
    }

    schedule.append(game)

print(schedule)