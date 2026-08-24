import requests
from db import get_connection

url = (
    "https://site.api.espn.com/apis/site/v2/"
    "sports/football/nfl/scoreboard"
)

SEASONS = [2021, 2022, 2023, 2024]

connection = get_connection()

cursor = connection.cursor()

insert_sql = """
    INSERT INTO nfl_games (
        game_id,
        season,
        week,
        game_date,
        home_team_id,
        away_team_id,
        home_team,
        away_team,
        home_logo,
        away_logo,
        home_score,
        away_score,
        game_state,
        game_status,
        completed,
        venue
    )
    VALUES (
        %s, %s, %s, %s, %s, %s,
        %s, %s, %s, %s, %s, %s,
        %s, %s, %s, %s
    )
    ON CONFLICT (game_id)
    DO UPDATE SET
        season = EXCLUDED.season,
        week = EXCLUDED.week,
        game_date = EXCLUDED.game_date,
        home_team_id = EXCLUDED.home_team_id,
        away_team_id = EXCLUDED.away_team_id,
        home_team = EXCLUDED.home_team,
        away_team = EXCLUDED.away_team,
        home_logo = EXCLUDED.home_logo,
        away_logo = EXCLUDED.away_logo,
        home_score = EXCLUDED.home_score,
        away_score = EXCLUDED.away_score,
        game_state = EXCLUDED.game_state,
        game_status = EXCLUDED.game_status,
        completed = EXCLUDED.completed,
        venue = EXCLUDED.venue;
"""


for season in SEASONS:

    print(f"\nLoading {season}")

    for week in range(1, 19):

        response = requests.get(
            url,
            params={
                "dates": str(season),
                "seasontype": 2,
                "week": week
            },
            timeout=30
        )

        response.raise_for_status()

        data = response.json()

        events = data.get("events", [])

        print(
            f"{season} Week {week}: "
            f"{len(events)} games"
        )

        for event in events:

            competition = event["competitions"][0]
            competitors = competition["competitors"]

            game_id = event["id"]
            game_date = event["date"]

            venue_info = competition.get(
                "venue",
                {}
            )

            venue = venue_info.get("fullName")

            home_team_id = None
            away_team_id = None

            home_team = None
            away_team = None

            home_logo = None
            away_logo = None

            home_score = None
            away_score = None

            for competitor in competitors:

                team = competitor["team"]

                if competitor["homeAway"] == "home":
                    home_team_id = team["id"]
                    home_team = team["displayName"]
                    home_logo = team.get("logo")
                    home_score = int(
                        competitor.get("score", 0)
                    )

                else:
                    away_team_id = team["id"]
                    away_team = team["displayName"]
                    away_logo = team.get("logo")
                    away_score = int(
                        competitor.get("score", 0)
                    )

            game_state = (
                event["status"]["type"]["state"]
            )

            game_status = (
                event["status"]["type"]["description"]
            )

            completed = (
                event["status"]["type"]["completed"]
            )

            cursor.execute(
                insert_sql,
                (
                    game_id,
                    season,
                    week,
                    game_date,
                    home_team_id,
                    away_team_id,
                    home_team,
                    away_team,
                    home_logo,
                    away_logo,
                    home_score,
                    away_score,
                    game_state,
                    game_status,
                    completed,
                    venue
                )
            )

        connection.commit()


cursor.close()
connection.close()

print("\nFinished loading historical NFL games")
