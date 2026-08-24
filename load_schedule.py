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
        venue_info = competition.get("venue", {})

        venue = venue_info.get("fullName")
        venue_id = venue_info.get("id")

        venue_address = venue_info.get("address", {})

        venue_city = venue_address.get("city")
        venue_state = venue_address.get("state")
        venue_zip = venue_address.get("zipCode")
        venue_country = venue_address.get("country")

        home_team = ""
        away_team = ""
        home_logo = ""
        away_logo = ""

        home_team_record = ""
        away_team_record = ""

        home_team_home_record = ""
        home_team_road_record = ""

        away_team_home_record = ""
        away_team_road_record = ""

        home_team_id = ""
        away_team_id = ""

        home_score = 0
        away_score = 0

        game_state = event["status"]["type"]["state"]
        game_status = event["status"]["type"]["description"]
        completed = event["status"]["type"]["completed"]

        for competitor in competitors:
            team_name = competitor["team"]["displayName"]
            team_logo = competitor["team"]["logo"]
            team_score = int(competitor["score"])
            team_id = competitor["team"]["id"]
            records = competitor["records"]

            overall_record = ""
            home_record = ""
            road_record = ""

            for record in records:
                if record["type"] == "total":
                    overall_record = record["summary"]

                if record["type"] == "home":
                    home_record = record["summary"]

                if record["type"] == "road":
                    road_record = record["summary"]


            if competitor["homeAway"] == "home":
                home_team = team_name
                home_team_id = team_id
                home_logo = team_logo
                home_score = team_score

                home_team_record = overall_record
                home_team_home_record = home_record
                home_team_road_record = road_record

            if competitor["homeAway"] == "away":
                away_team = team_name
                away_team_id = team_id
                away_logo = team_logo
                away_score = team_score

                away_team_record = overall_record
                away_team_home_record = home_record
                away_team_road_record = road_record

        game = {
            "game_id": game_id,
            "season": 2026,
            "week": week,
            "date": game_date,
            "home_team": home_team,
            "away_team": away_team,
            "home_logo": home_logo,
            "away_logo": away_logo,
            "home_team_id": home_team_id,
            "away_team_id": away_team_id,
            "home_score": home_score,
            "away_score": away_score,
            "game_state": game_state,
            "game_status": game_status,
            "completed": completed,
            "home_record": home_team_record,
            "away_record": away_team_record,
            "home_home_record": home_team_home_record,
            "home_road_record": home_team_road_record,
            "away_home_record": away_team_home_record,
            "away_road_record": away_team_road_record,
            "venue": venue,
            "venue_id": venue_id,
            "venue_city": venue_city,
            "venue_state": venue_state,
            "venue_zip": venue_zip,
            "venue_country": venue_country
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
            home_team_id,
            away_team_id,
            home_team,
            away_team,
            home_logo,
            away_logo,
            home_record,
            away_record,
            home_home_record,
            home_road_record,
            away_home_record,
            away_road_record,
            home_score,
            away_score,
            game_state,
            game_status,
            completed,
            venue,
            venue_id,
            venue_city,
            venue_state,
            venue_zip,
            venue_country
        )
        VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s
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
            home_record = EXCLUDED.home_record,
            away_record = EXCLUDED.away_record,
            home_home_record = EXCLUDED.home_home_record,
            home_road_record = EXCLUDED.home_road_record,
            away_home_record = EXCLUDED.away_home_record,
            away_road_record = EXCLUDED.away_road_record,
            home_score = EXCLUDED.home_score,
            away_score = EXCLUDED.away_score,
            game_state = EXCLUDED.game_state,
            game_status = EXCLUDED.game_status,
            completed = EXCLUDED.completed,
            venue = EXCLUDED.venue,
            venue_id = EXCLUDED.venue_id,
            venue_city = EXCLUDED.venue_city,
            venue_state = EXCLUDED.venue_state,
            venue_zip = EXCLUDED.venue_zip,
            venue_country = EXCLUDED.venue_country
        """,
        (
            game["game_id"],
            game["season"],
            game["week"],
            game["date"],
            game["home_team_id"],
            game["away_team_id"],
            game["home_team"],
            game["away_team"],
            game["home_logo"],
            game["away_logo"],
            game["home_record"],
            game["away_record"],
            game["home_home_record"],
            game["home_road_record"],
            game["away_home_record"],
            game["away_road_record"],
            game["home_score"],
            game["away_score"],
            game["game_state"],
            game["game_status"],
            game["completed"],
            game["venue"],
            game["venue_id"],
            game["venue_city"],
            game["venue_state"],
            game["venue_zip"],
            game["venue_country"]
        )
    )

connection.commit()

cursor.close()
connection.close()

print("Loaded NFL schedule into PostgreSQL")