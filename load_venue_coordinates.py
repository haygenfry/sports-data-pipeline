import requests
from db import get_connection

geocoding_url = (
    "https://geocoding-api.open-meteo.com/v1/search"
)

connection = get_connection()

cursor = connection.cursor()

cursor.execute(
    """
    SELECT DISTINCT
        venue,
        venue_city,
        venue_state,
        venue_country
    FROM nfl_games
    WHERE season = 2026
      AND venue_city IS NOT NULL
      AND venue_country IS NOT NULL
      AND (
          venue_latitude IS NULL
          OR venue_longitude IS NULL
          OR venue_timezone IS NULL
      )
    ORDER BY venue;
    """
)

venues = cursor.fetchall()

print(f"Found {len(venues)} venues needing coordinates")


for index, (
    venue,
    city,
    state,
    country
) in enumerate(venues, start=1):

    search_name = city

    response = requests.get(
        geocoding_url,
        params={
            "name": search_name,
            "count": 10,
            "language": "en",
            "format": "json"
        },
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    results = data.get("results", [])

    if not results:
        print(
            f"[{index}/{len(venues)}] "
            f"No geocoding result for "
            f"{venue} ({city}, {state}, {country})"
        )
        continue

    best_match = None

    for result in results:

        result_country = result.get("country")
        result_admin1 = result.get("admin1")

        country_matches = (
            result_country
            and result_country.lower()
            == country.lower()
        )

        state_matches = True

        if state and result_admin1:
            state_matches = (
                state.lower() in result_admin1.lower()
                or result_admin1.lower() in state.lower()
            )

        if country_matches and state_matches:
            best_match = result
            break

    if best_match is None:
        for result in results:
            result_country = result.get("country")

            if (
                result_country
                and result_country.lower()
                == country.lower()
            ):
                best_match = result
                break

    if best_match is None:
        best_match = results[0]

    latitude = best_match.get("latitude")
    longitude = best_match.get("longitude")
    timezone = best_match.get("timezone")

    cursor.execute(
        """
        UPDATE nfl_games
        SET
            venue_latitude = %s,
            venue_longitude = %s,
            venue_timezone = %s
        WHERE season = 2026
          AND venue = %s
          AND venue_city = %s
          AND venue_country = %s;
        """,
        (
            latitude,
            longitude,
            timezone,
            venue,
            city,
            country
        )
    )

    connection.commit()

    print(
        f"[{index}/{len(venues)}] "
        f"{venue}: "
        f"{latitude}, {longitude} "
        f"({timezone})"
    )


cursor.close()
connection.close()

print("Finished loading venue coordinates")
