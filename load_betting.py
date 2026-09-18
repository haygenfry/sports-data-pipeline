import requests
from datetime import datetime, timezone
from db import get_connection

SEASON = 2026
WEEK = 2

summary_url = (
    "https://site.api.espn.com/apis/site/v2/"
    "sports/football/nfl/summary"
)

connection = get_connection()

cursor = connection.cursor()


# -------------------------
# UPCOMING 2026 GAMES
# -------------------------

# -------------------------
# UPCOMING GAMES FOR WEEK
# -------------------------

cursor.execute(
    """
    SELECT game_id
    FROM nfl_games
    WHERE season = %s
      AND week = %s
      AND completed = FALSE
    ORDER BY game_date;
    """,
    (SEASON, WEEK)
)

game_ids = [row[0] for row in cursor.fetchall()]

print(
    f"Found {len(game_ids)} upcoming games "
    f"for {SEASON} Week {WEEK}"
)


# -------------------------
# INSERT
# -------------------------

insert_sql = """
    INSERT INTO nfl_betting_snapshots (
        game_id,
        provider_id,
        provider_name,

        away_team_id,
        home_team_id,

        away_moneyline,
        home_moneyline,

        away_spread,
        home_spread,

        away_spread_odds,
        home_spread_odds,

        total,
        over_odds,
        under_odds,

        opening_away_moneyline,
        opening_home_moneyline,

        opening_away_spread,
        opening_home_spread,

        opening_total,

        captured_at
    )
    VALUES (
        %s, %s, %s,
        %s, %s,
        %s, %s,
        %s, %s,
        %s, %s,
        %s, %s, %s,
        %s, %s,
        %s, %s,
        %s,
        %s
    );
"""


# -------------------------
# HELPER
# -------------------------

def get_number(data, *keys):
    value = data

    for key in keys:
        if not isinstance(value, dict):
            return None

        value = value.get(key)

        if value is None:
            return None

    if value in ("OFF", "", "--"):
        return None

    return value


# -------------------------
# LOAD EACH GAME
# -------------------------

for index, game_id in enumerate(game_ids, start=1):

    try:

        response = requests.get(
            summary_url,
            params={"event": game_id},
            timeout=30
        )

        response.raise_for_status()

        data = response.json()

        pickcenter = data.get("pickcenter", [])

        if not pickcenter:
            print(
                f"[{index}/{len(game_ids)}] "
                f"{game_id}: No betting data"
            )
            continue

        market = pickcenter[0]

        provider = market.get("provider", {})

        provider_id = provider.get("id")
        provider_name = provider.get("name")

        away_team_odds = market.get(
            "awayTeamOdds",
            {}
        )

        home_team_odds = market.get(
            "homeTeamOdds",
            {}
        )

        away_team_id = away_team_odds.get(
            "teamId"
        )

        home_team_id = home_team_odds.get(
            "teamId"
        )

        # -------------------------
        # CURRENT MONEYLINE
        # -------------------------

        away_moneyline = get_number(
            market,
            "moneyline",
            "away",
            "close",
            "odds"
        )

        home_moneyline = get_number(
            market,
            "moneyline",
            "home",
            "close",
            "odds"
        )

        # -------------------------
        # CURRENT SPREAD
        # -------------------------

        away_spread = get_number(
            market,
            "pointSpread",
            "away",
            "close",
            "line"
        )

        home_spread = get_number(
            market,
            "pointSpread",
            "home",
            "close",
            "line"
        )

        away_spread_odds = get_number(
            market,
            "pointSpread",
            "away",
            "close",
            "odds"
        )

        home_spread_odds = get_number(
            market,
            "pointSpread",
            "home",
            "close",
            "odds"
        )

        # -------------------------
        # CURRENT TOTAL
        # -------------------------

        total = market.get("overUnder")

        if total in ("OFF", "", "--"):
            total = None

        over_odds = get_number(
            market,
            "total",
            "over",
            "close",
            "odds"
        )

        under_odds = get_number(
            market,
            "total",
            "under",
            "close",
            "odds"
        )

        # -------------------------
        # OPENING MONEYLINE
        # -------------------------

        opening_away_moneyline = get_number(
            market,
            "moneyline",
            "away",
            "open",
            "odds"
        )

        opening_home_moneyline = get_number(
            market,
            "moneyline",
            "home",
            "open",
            "odds"
        )

        # -------------------------
        # OPENING SPREAD
        # -------------------------

        opening_away_spread = get_number(
            market,
            "pointSpread",
            "away",
            "open",
            "line"
        )

        opening_home_spread = get_number(
            market,
            "pointSpread",
            "home",
            "open",
            "line"
        )

        # -------------------------
        # OPENING TOTAL
        # -------------------------

        opening_total_raw = get_number(
            market,
            "total",
            "over",
            "open",
            "line"
        )

        if opening_total_raw:
            opening_total = (
                str(opening_total_raw)
                .lower()
                .replace("o", "")
                .replace("u", "")
            )
        else:
            opening_total = None

        # -------------------------
        # INSERT SNAPSHOT
        # -------------------------

        captured_at = datetime.now(
            timezone.utc
        )

        cursor.execute(
            insert_sql,
            (
                game_id,
                provider_id,
                provider_name,

                away_team_id,
                home_team_id,

                away_moneyline,
                home_moneyline,

                away_spread,
                home_spread,

                away_spread_odds,
                home_spread_odds,

                total,
                over_odds,
                under_odds,

                opening_away_moneyline,
                opening_home_moneyline,

                opening_away_spread,
                opening_home_spread,

                opening_total,

                captured_at
            )
        )

        connection.commit()

        print(
            f"[{index}/{len(game_ids)}] "
            f"{game_id}: "
            f"{provider_name} | "
            f"Spread {market.get('details')} | "
            f"Total {total}"
        )

    except Exception as error:

        connection.rollback()

        print(
            f"[{index}/{len(game_ids)}] "
            f"{game_id}: ERROR — {error}"
        )


cursor.close()
connection.close()

print("Finished loading betting snapshots")
