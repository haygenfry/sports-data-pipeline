import requests
from db import get_connection


ESPN_SCOREBOARD_URL = (
    "https://site.api.espn.com/apis/site/v2/sports/"
    "football/nfl/scoreboard"
)


def fetch_schedule(season: int) -> list[dict]:
    schedule = []

    for week in range(1, 19):
        params = {
            "dates": str(season),
            "seasontype": 2,
            "week": week,
        }

        response = requests.get(
            ESPN_SCOREBOARD_URL,
            params=params,
            timeout=30,
        )
        response.raise_for_status()

        data = response.json()

        for event in data.get("events", []):
            competition = event["competitions"][0]
            competitors = competition["competitors"]

            venue_info = competition.get("venue", {})
            venue_address = venue_info.get("address", {})

            game = {
                "game_id": event["id"],
                "season": season,
                "week": week,
                "date": event["date"],
                "home_team": "",
                "away_team": "",
                "home_logo": "",
                "away_logo": "",
                "home_team_id": "",
                "away_team_id": "",
                "home_score": 0,
                "away_score": 0,
                "game_state": event["status"]["type"]["state"],
                "game_status": event["status"]["type"]["description"],
                "completed": event["status"]["type"]["completed"],
                "home_record": "",
                "away_record": "",
                "home_home_record": "",
                "home_road_record": "",
                "away_home_record": "",
                "away_road_record": "",
                "venue": venue_info.get("fullName"),
                "venue_id": venue_info.get("id"),
                "venue_city": venue_address.get("city"),
                "venue_state": venue_address.get("state"),
                "venue_zip": venue_address.get("zipCode"),
                "venue_country": venue_address.get("country"),
            }

            for competitor in competitors:
                records = {
                    record["type"]: record["summary"]
                    for record in competitor.get("records", [])
                }

                is_home = competitor["homeAway"] == "home"
                prefix = "home" if is_home else "away"

                game[f"{prefix}_team"] = competitor["team"]["displayName"]
                game[f"{prefix}_team_id"] = competitor["team"]["id"]
                game[f"{prefix}_logo"] = competitor["team"].get("logo")
                game[f"{prefix}_score"] = int(competitor.get("score") or 0)
                game[f"{prefix}_record"] = records.get("total", "")
                game[f"{prefix}_home_record"] = records.get("home", "")
                game[f"{prefix}_road_record"] = records.get("road", "")

            schedule.append(game)

    return schedule


def upsert_schedule(schedule: list[dict]) -> None:
    connection = get_connection()

    try:
        with connection:
            with connection.cursor() as cursor:
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
                            %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s, %s, %s
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
                            game["venue_country"],
                        ),
                    )
    finally:
        connection.close()


def main():
    season = 2026
    schedule = fetch_schedule(season)
    upsert_schedule(schedule)

    print(f"Loaded {len(schedule)} games for {season}")


if __name__ == "__main__":
    main()