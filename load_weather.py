import sys
import requests
from datetime import datetime, timezone
from db import get_connection

SEASON = 2026

if len(sys.argv) != 2:
    print("Usage: python load_weather.py <week>")
    sys.exit(1)

WEEK = int(sys.argv[1])

forecast_url = "https://api.open-meteo.com/v1/forecast"

connection = get_connection()

cursor = connection.cursor()

cursor.execute(
    """
    SELECT
        game_id,
        game_date,
        venue_latitude,
        venue_longitude,
        venue_timezone
    FROM nfl_games
    WHERE season = %s
      AND week = %s
      AND completed = FALSE
      AND venue_latitude IS NOT NULL
      AND venue_longitude IS NOT NULL
      AND venue_timezone IS NOT NULL
    ORDER BY game_date;
    """,
    (SEASON, WEEK)
)

games = cursor.fetchall()

print(
    f"Found {len(games)} upcoming games "
    f"for {SEASON} Week {WEEK}"
)


insert_sql = """
    INSERT INTO nfl_weather_snapshots (
        game_id,
        forecast_time,
        temperature_f,
        apparent_temperature_f,
        precipitation_probability,
        precipitation_inches,
        relative_humidity,
        wind_speed_mph,
        wind_gust_mph,
        wind_direction_degrees,
        weather_code
    )
    VALUES (
        %s, %s, %s, %s, %s,
        %s, %s, %s, %s, %s,
        %s
    );
"""


for index, (
    game_id,
    game_date,
    latitude,
    longitude,
    venue_timezone
) in enumerate(games, start=1):

    now = datetime.now(timezone.utc)

    days_until_game = (
        game_date.astimezone(timezone.utc) - now
    ).total_seconds() / 86400

    # Open-Meteo forecast horizon is limited.
    # Skip games too far away for useful forecast data.
    if days_until_game > 16:
        print(
            f"[{index}/{len(games)}] "
            f"Skipping {game_id}: "
            f"{days_until_game:.1f} days away"
        )
        continue

    response = requests.get(
        forecast_url,
        params={
            "latitude": float(latitude),
            "longitude": float(longitude),
            "hourly": ",".join([
                "temperature_2m",
                "apparent_temperature",
                "precipitation_probability",
                "precipitation",
                "relative_humidity_2m",
                "wind_speed_10m",
                "wind_gusts_10m",
                "wind_direction_10m",
                "weather_code"
            ]),
            "temperature_unit": "fahrenheit",
            "wind_speed_unit": "mph",
            "precipitation_unit": "inch",
            "timezone": venue_timezone,
            "forecast_days": 16
        },
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    hourly = data.get("hourly", {})

    times = hourly.get("time", [])

    if not times:
        print(
            f"[{index}/{len(games)}] "
            f"No hourly forecast for {game_id}"
        )
        continue

    game_local = game_date.astimezone(
        __import__("zoneinfo").ZoneInfo(
            venue_timezone
        )
    )

    target_hour = game_local.replace(
        minute=0,
        second=0,
        microsecond=0
    )

    best_index = None
    smallest_difference = None

    for i, time_string in enumerate(times):

        forecast_time = datetime.fromisoformat(
            time_string
        ).replace(
            tzinfo=__import__("zoneinfo").ZoneInfo(
                venue_timezone
            )
        )

        difference = abs(
            (
                forecast_time - target_hour
            ).total_seconds()
        )

        if (
            smallest_difference is None
            or difference < smallest_difference
        ):
            smallest_difference = difference
            best_index = i

    if best_index is None:
        continue

    forecast_time = datetime.fromisoformat(
        times[best_index]
    ).replace(
        tzinfo=__import__("zoneinfo").ZoneInfo(
            venue_timezone
        )
    )

    cursor.execute(
        insert_sql,
        (
            game_id,
            forecast_time,
            hourly["temperature_2m"][best_index],
            hourly["apparent_temperature"][best_index],
            hourly["precipitation_probability"][best_index],
            hourly["precipitation"][best_index],
            hourly["relative_humidity_2m"][best_index],
            hourly["wind_speed_10m"][best_index],
            hourly["wind_gusts_10m"][best_index],
            hourly["wind_direction_10m"][best_index],
            hourly["weather_code"][best_index]
        )
    )

    connection.commit()

    print(
        f"[{index}/{len(games)}] "
        f"Loaded weather for game {game_id} "
        f"at {forecast_time}"
    )


cursor.close()
connection.close()

print("Finished loading weather snapshots")
