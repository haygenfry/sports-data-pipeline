import csv
import psycopg2


BACKTEST_SEASONS = [2022, 2023, 2024, 2025]
START_WEEK = 1


connection = psycopg2.connect(
    host="localhost",
    port=5432,
    database="nfl_data",
    user="nfl_user",
    password="nfl_password"
)

cursor = connection.cursor()

def get_team_scoring_profile(cursor, team_id, season, game_date):
    cursor.execute(
        """
        SELECT
            home_team_id,
            home_score,
            away_team_id,
            away_score,
            game_date
        FROM nfl_games
        WHERE completed = TRUE
          AND season = %s
          AND game_date < %s
          AND (
              home_team_id = %s
              OR away_team_id = %s
          )
        ORDER BY game_date;
        """,
        (season, game_date, team_id, team_id)
    )

    games = cursor.fetchall()

    if not games:
        return None

    points_for = 0
    points_against = 0
    wins = 0

    home_points_for = 0
    home_games = 0

    road_points_for = 0
    road_games = 0

    for home_team_id, home_score, away_team_id, away_score, _ in games:

        if home_team_id == team_id:
            points_for += home_score
            points_against += away_score

            home_points_for += home_score
            home_games += 1

            if home_score > away_score:
                wins += 1

        else:
            points_for += away_score
            points_against += home_score

            road_points_for += away_score
            road_games += 1

            if away_score > home_score:
                wins += 1

    games_played = len(games)

    last_three_games = games[-3:]

    last_three_points_for = 0
    last_three_points_against = 0

    for home_team_id, home_score, away_team_id, away_score, _ in last_three_games:

        if home_team_id == team_id:
            last_three_points_for += home_score
            last_three_points_against += away_score
        else:
            last_three_points_for += away_score
            last_three_points_against += home_score

    last_three_count = len(last_three_games)

    return {
        "games_played": games_played,
        "ppg": points_for / games_played,
        "ppg_allowed": points_against / games_played,
        "scoring_margin": (points_for - points_against) / games_played,
        "win_pct": wins / games_played,

        "home_ppg": home_points_for / home_games if home_games else None,
        "road_ppg": road_points_for / road_games if road_games else None,

        "last_three_ppg": last_three_points_for / last_three_count,
        "last_three_ppg_allowed": last_three_points_against / last_three_count
    }

def get_team_boxscore_profile(cursor, team_id, season, game_date):
    cursor.execute(
        """
        SELECT
            s.total_yards,
            s.passing_yards,
            s.rushing_yards,
            s.yards_per_play,
            s.first_downs,
            s.turnovers,
            s.third_down_eff,
            s.red_zone_eff,
            s.possession_time
        FROM nfl_team_game_stats s
        JOIN nfl_games g
            ON s.game_id = g.game_id
        WHERE s.team_id = %s
          AND g.season = %s
          AND g.completed = TRUE
          AND g.game_date < %s
        ORDER BY g.game_date;
        """,
        (team_id, season, game_date)
    )

    rows = cursor.fetchall()

    if not rows:
        return None
    last_three_rows = rows[-3:]

    total_yards = 0
    passing_yards = 0
    rushing_yards = 0
    yards_per_play = 0
    first_downs = 0
    turnovers = 0

    third_down_made = 0
    third_down_attempts = 0

    red_zone_made = 0
    red_zone_attempts = 0

    possession_seconds = 0

    for (
        game_total_yards,
        game_passing_yards,
        game_rushing_yards,
        game_yards_per_play,
        game_first_downs,
        game_turnovers,
        game_third_down_eff,
        game_red_zone_eff,
        game_possession_time
    ) in rows:

        total_yards += game_total_yards
        passing_yards += game_passing_yards
        rushing_yards += game_rushing_yards
        yards_per_play += float(game_yards_per_play)
        first_downs += game_first_downs
        turnovers += game_turnovers

        third_made, third_attempts = game_third_down_eff.split("-")
        third_down_made += int(third_made)
        third_down_attempts += int(third_attempts)

        red_made, red_attempts = game_red_zone_eff.split("-")
        red_zone_made += int(red_made)
        red_zone_attempts += int(red_attempts)

        minutes, seconds = game_possession_time.split(":")
        possession_seconds += int(minutes) * 60 + int(seconds)

    games_played = len(rows)

    average_possession_seconds = possession_seconds / games_played

    average_possession_minutes = int(
        average_possession_seconds // 60
    )

    average_possession_remaining_seconds = int(
        average_possession_seconds % 60
    )

    average_possession = (
        f"{average_possession_minutes}:"
        f"{average_possession_remaining_seconds:02d}"
    )

    last_three_total_yards = sum(
        row[0] for row in last_three_rows
    )

    last_three_turnovers = sum(
        row[5] for row in last_three_rows
    )

    last_three_games = len(last_three_rows)

    return {
        "total_yards_per_game": total_yards / games_played,
        "passing_yards_per_game": passing_yards / games_played,
        "rushing_yards_per_game": rushing_yards / games_played,
        "yards_per_play": yards_per_play / games_played,
        "first_downs_per_game": first_downs / games_played,
        "turnovers_per_game": turnovers / games_played,

        "third_down_pct": (
            third_down_made / third_down_attempts
            if third_down_attempts
            else 0
        ),

        "red_zone_pct": (
            red_zone_made / red_zone_attempts
            if red_zone_attempts
            else 0
        ),

        "average_possession": average_possession,

        "last_three_yards_per_game": (
            last_three_total_yards / last_three_games
        ),

        "last_three_turnovers_per_game": (
            last_three_turnovers / last_three_games
        ),

        "last_three_turnovers": last_three_turnovers
    }

def get_team_defensive_profile(cursor, team_id, season, game_date):
    cursor.execute(
        """
        SELECT
            opponent.total_yards,
            opponent.passing_yards,
            opponent.rushing_yards,
            opponent.yards_per_play,
            opponent.first_downs,
            opponent.turnovers,
            opponent.third_down_eff,
            opponent.red_zone_eff,
            team.defensive_touchdowns
        FROM nfl_team_game_stats team
        JOIN nfl_games g
            ON team.game_id = g.game_id
        JOIN nfl_team_game_stats opponent
            ON team.game_id = opponent.game_id
            AND team.team_id <> opponent.team_id
        WHERE team.team_id = %s
          AND g.season = %s
          AND g.completed = TRUE
          AND g.game_date < %s
        ORDER BY g.game_date;
        """,
        (team_id, season, game_date)
    )

    rows = cursor.fetchall()

    if not rows:
        return None
    last_three_rows = rows[-3:]

    total_yards_allowed = 0
    passing_yards_allowed = 0
    rushing_yards_allowed = 0
    yards_per_play_allowed = 0
    first_downs_allowed = 0
    takeaways = 0
    defensive_touchdowns = 0

    opponent_third_down_made = 0
    opponent_third_down_attempts = 0

    opponent_red_zone_made = 0
    opponent_red_zone_attempts = 0

    for (
        opponent_total_yards,
        opponent_passing_yards,
        opponent_rushing_yards,
        opponent_yards_per_play,
        opponent_first_downs,
        opponent_turnovers,
        opponent_third_down_eff,
        opponent_red_zone_eff,
        game_defensive_touchdowns
    ) in rows:

        total_yards_allowed += opponent_total_yards
        passing_yards_allowed += opponent_passing_yards
        rushing_yards_allowed += opponent_rushing_yards
        yards_per_play_allowed += float(opponent_yards_per_play)
        first_downs_allowed += opponent_first_downs

        takeaways += opponent_turnovers
        defensive_touchdowns += game_defensive_touchdowns

        third_made, third_attempts = opponent_third_down_eff.split("-")
        opponent_third_down_made += int(third_made)
        opponent_third_down_attempts += int(third_attempts)

        red_made, red_attempts = opponent_red_zone_eff.split("-")
        opponent_red_zone_made += int(red_made)
        opponent_red_zone_attempts += int(red_attempts)

    games_played = len(rows)

    last_three_yards_allowed = sum(
        row[0] for row in last_three_rows
    )

    last_three_takeaways = sum(
        row[5] for row in last_three_rows
    )

    last_three_games = len(last_three_rows)

    return {
        "yards_allowed_per_game": total_yards_allowed / games_played,
        "passing_yards_allowed_per_game": passing_yards_allowed / games_played,
        "rushing_yards_allowed_per_game": rushing_yards_allowed / games_played,
        "yards_per_play_allowed": yards_per_play_allowed / games_played,
        "first_downs_allowed_per_game": first_downs_allowed / games_played,
        "takeaways_per_game": takeaways / games_played,
        "opponent_third_down_pct": (
            opponent_third_down_made / opponent_third_down_attempts
            if opponent_third_down_attempts
            else 0
        ),
        "opponent_red_zone_pct": (
            opponent_red_zone_made / opponent_red_zone_attempts
            if opponent_red_zone_attempts
            else 0
        ),
        "defensive_touchdowns": defensive_touchdowns,

        "last_three_yards_allowed_per_game": (
            last_three_yards_allowed / last_three_games
        ),

        "last_three_takeaways_per_game": (
            last_three_takeaways / last_three_games
        ),

        "last_three_takeaways": last_three_takeaways
    }

def get_matchup_comparison(offense, defense):
    if not offense or not defense:
        return None

    return {
        "total_yards": (
            offense["total_yards_per_game"],
            defense["yards_allowed_per_game"]
        ),
        "passing_yards": (
            offense["passing_yards_per_game"],
            defense["passing_yards_allowed_per_game"]
        ),
        "rushing_yards": (
            offense["rushing_yards_per_game"],
            defense["rushing_yards_allowed_per_game"]
        ),
        "yards_per_play": (
            offense["yards_per_play"],
            defense["yards_per_play_allowed"]
        ),
        "third_down": (
            offense["third_down_pct"],
            defense["opponent_third_down_pct"]
        ),
        "red_zone": (
            offense["red_zone_pct"],
            defense["opponent_red_zone_pct"]
        ),
        "turnovers_takeaways": (
            offense["turnovers_per_game"],
            defense["takeaways_per_game"]
        )
    }

def classify_matchup_edge(
    offense_value,
    defense_value,
    league_value,
    lower_is_better=False
):
    if (
        offense_value is None
        or defense_value is None
        or league_value is None
    ):
        return None

    if lower_is_better:
        offense_strength = league_value - offense_value
        defense_strength = defense_value - league_value
    else:
        offense_strength = offense_value - league_value
        defense_strength = league_value - defense_value

    if offense_strength > 0 and defense_strength < 0:
        return "Offense edge"

    if offense_strength < 0 and defense_strength > 0:
        return "Defense edge"

    if offense_strength > 0 and defense_strength > 0:
        return "Strength vs strength"

    if offense_strength < 0 and defense_strength < 0:
        return "Weakness vs weakness"

    return "Neutral"

def get_matchup_edges(
    comparison,
    league_baselines
):
    if not comparison or not league_baselines:
        return None

    return {
        "total_yards": classify_matchup_edge(
            comparison["total_yards"][0],
            comparison["total_yards"][1],
            league_baselines["total_yards"]
        ),

        "passing_yards": classify_matchup_edge(
            comparison["passing_yards"][0],
            comparison["passing_yards"][1],
            league_baselines["passing_yards"]
        ),

        "rushing_yards": classify_matchup_edge(
            comparison["rushing_yards"][0],
            comparison["rushing_yards"][1],
            league_baselines["rushing_yards"]
        ),

        "yards_per_play": classify_matchup_edge(
            comparison["yards_per_play"][0],
            comparison["yards_per_play"][1],
            league_baselines["yards_per_play"]
        ),

        "third_down": classify_matchup_edge(
            comparison["third_down"][0],
            comparison["third_down"][1],
            league_baselines["third_down"]
        ),

        "red_zone": classify_matchup_edge(
            comparison["red_zone"][0],
            comparison["red_zone"][1],
            league_baselines["red_zone"]
        ),

        "turnovers": classify_matchup_edge(
            comparison["turnovers_takeaways"][0],
            comparison["turnovers_takeaways"][1],
            league_baselines["turnovers"],
            lower_is_better=True
        )
    }

def get_team_power_rating(
    scoring,
    offense,
    defense
):
    if not scoring or not offense or not defense:
        return None

    scoring_component = (
        scoring["scoring_margin"] / 7.0
    )

    yards_per_play_component = (
        offense["yards_per_play"]
        - defense["yards_per_play_allowed"]
    )

    turnover_component = (
        defense["takeaways_per_game"]
        - offense["turnovers_per_game"]
    )

    third_down_component = (
        offense["third_down_pct"]
        - defense["opponent_third_down_pct"]
    ) * 10

    red_zone_component = (
        offense["red_zone_pct"]
        - defense["opponent_red_zone_pct"]
    ) * 5

    rating = (
        scoring_component * 2.0
        + yards_per_play_component * 3.0
        + turnover_component * 1.5
        + third_down_component
        + red_zone_component
    )

    return {
        "rating": rating,
        "scoring_component": scoring_component,
        "yards_per_play_component": yards_per_play_component,
        "turnover_component": turnover_component,
        "third_down_component": third_down_component,
        "red_zone_component": red_zone_component
    }

def get_matchup_prediction_adjustment(
    away_edges,
    home_edges
):
    if not away_edges or not home_edges:
        return 0.0

    edge_values = {
        "Offense edge": 1.0,
        "Defense edge": -1.0,
        "Strength vs strength": 0.0,
        "Weakness vs weakness": 0.0,
        "Neutral": 0.0
    }

    metric_weights = {
        "total_yards": 0.25,
        "passing_yards": 0.25,
        "rushing_yards": 0.25,
        "yards_per_play": 1.00,
        "third_down": 0.50,
        "red_zone": 0.50,
        "turnovers": 0.75
    }

    def score_team(edges):
        score = 0.0
        max_score = 0.0

        for metric, weight in metric_weights.items():
            result = edges.get(metric)

            score += (
                edge_values.get(result, 0.0)
                * weight
            )

            max_score += weight

        if max_score == 0:
            return 0.0

        return score / max_score

    away_score = score_team(away_edges)
    home_score = score_team(home_edges)

    # Positive = home advantage
    # Negative = away advantage
    net_matchup_score = (
        home_score - away_score
    )

    # Keep matchup influence modest.
    # Maximum possible contribution = +/- 2 raw-edge units.
    matchup_adjustment = max(
        -2.0,
        min(
            2.0,
            net_matchup_score * 2.0
        )
    )

    return matchup_adjustment

def get_recent_form_adjustment(
    away_scoring,
    home_scoring,
    away_offense,
    home_offense,
    away_defense,
    home_defense
):
    if (
        not away_scoring
        or not home_scoring
        or not away_offense
        or not home_offense
        or not away_defense
        or not home_defense
    ):
        return 0.0

    away_scoring_margin = (
        away_scoring["last_three_ppg"]
        - away_scoring["last_three_ppg_allowed"]
    )

    home_scoring_margin = (
        home_scoring["last_three_ppg"]
        - home_scoring["last_three_ppg_allowed"]
    )

    away_yard_margin = (
        away_offense["last_three_yards_per_game"]
        - away_defense["last_three_yards_allowed_per_game"]
    )

    home_yard_margin = (
        home_offense["last_three_yards_per_game"]
        - home_defense["last_three_yards_allowed_per_game"]
    )

    away_turnover_margin = (
        away_defense["last_three_takeaways"]
        - away_offense["last_three_turnovers"]
    )

    home_turnover_margin = (
        home_defense["last_three_takeaways"]
        - home_offense["last_three_turnovers"]
    )

    scoring_difference = (
        home_scoring_margin
        - away_scoring_margin
    )

    yard_difference = (
        home_yard_margin
        - away_yard_margin
    )

    turnover_difference = (
        home_turnover_margin
        - away_turnover_margin
    )

    scoring_component = scoring_difference / 14.0
    yard_component = yard_difference / 150.0
    turnover_component = turnover_difference / 4.0

    recent_form_score = (
        scoring_component * 0.5
        + yard_component * 0.3
        + turnover_component * 0.2
    )

    recent_form_adjustment = max(
        -1.5,
        min(
            1.5,
            recent_form_score * 1.5
        )
    )

    return recent_form_adjustment

def get_raw_prediction_edge(
    away_power,
    home_power,
    matchup_adjustment=0.0,
    recent_form_adjustment=0.0
):
    if not away_power or not home_power:
        return None

    power_edge = (
        home_power["rating"]
        - away_power["rating"]
    )

    home_field_edge = 1.5

    raw_edge = (
        power_edge
        + home_field_edge
        + matchup_adjustment
        + recent_form_adjustment
    )

    return {
        "raw_edge": raw_edge,
        "power_edge": power_edge,
        "home_field_edge": home_field_edge,
        "matchup_edge": matchup_adjustment,
        "recent_form_edge": recent_form_adjustment
    }

def get_league_matchup_baselines(
    cursor,
    season,
    game_date
):
    cursor.execute(
        """
        SELECT
            AVG(s.total_yards),
            AVG(s.passing_yards),
            AVG(s.rushing_yards),
            AVG(s.yards_per_play),
            SUM(
                SPLIT_PART(s.third_down_eff, '-', 1)::NUMERIC
            )
            /
            NULLIF(
                SUM(
                    SPLIT_PART(s.third_down_eff, '-', 2)::NUMERIC
                ),
                0
            ),
            SUM(
                SPLIT_PART(s.red_zone_eff, '-', 1)::NUMERIC
            )
            /
            NULLIF(
                SUM(
                    SPLIT_PART(s.red_zone_eff, '-', 2)::NUMERIC
                ),
                0
            ),
            AVG(s.turnovers)
        FROM nfl_team_game_stats s
        JOIN nfl_games g
            ON s.game_id = g.game_id
        WHERE g.season = %s
          AND g.completed = TRUE
          AND g.game_date < %s;
        """,
        (season, game_date)
    )

    row = cursor.fetchone()

    if not row or row[0] is None:
        return None

    return {
        "total_yards": float(row[0]),
        "passing_yards": float(row[1]),
        "rushing_yards": float(row[2]),
        "yards_per_play": float(row[3]),
        "third_down": float(row[4]) if row[4] is not None else None,
        "red_zone": float(row[5]) if row[5] is not None else None,
        "turnovers": float(row[6])
    }

def get_season_blend_weights(
    current_games_played
):
    if current_games_played <= 0:
        return {
            "previous_season": 1.0,
            "current_season": 0.0
        }

    if current_games_played == 1:
        return {
            "previous_season": 0.75,
            "current_season": 0.25
        }

    if current_games_played == 2:
        return {
            "previous_season": 0.50,
            "current_season": 0.50
        }

    if current_games_played == 3:
        return {
            "previous_season": 0.25,
            "current_season": 0.75
        }

    return {
        "previous_season": 0.0,
        "current_season": 1.0
    }

def blend_profile(
    previous_profile,
    current_profile,
    previous_weight,
    current_weight
):
    if previous_profile is None and current_profile is None:
        return None

    if previous_profile is None:
        return current_profile

    if current_profile is None:
        return previous_profile

    blended = {}

    non_blended_keys = {
        "games_played",
        "last_three_ppg",
        "last_three_ppg_allowed"
    }

    keys = (
        set(previous_profile.keys())
        | set(current_profile.keys())
    )

    for key in keys:
        previous_value = previous_profile.get(key)
        current_value = current_profile.get(key)

        if key in non_blended_keys:
            blended[key] = (
                current_value
                if current_value is not None
                else previous_value
            )
            continue

        if isinstance(previous_value, (int, float)) and isinstance(
            current_value,
            (int, float)
        ):
            blended[key] = (
                previous_value * previous_weight
                + current_value * current_weight
            )

        elif current_value is not None:
            blended[key] = current_value

        else:
            blended[key] = previous_value

    return blended

season_placeholders = ", ".join(
    ["%s"] * len(BACKTEST_SEASONS)
)

cursor.execute(
    f"""
    SELECT
        season,
        game_id,
        week,
        game_date,

        away_team_id,
        away_team,
        away_score,

        home_team_id,
        home_team,
        home_score

    FROM nfl_games

    WHERE season IN ({season_placeholders})
      AND completed = TRUE
      AND week >= %s

    ORDER BY game_date;
    """,
    (
        *BACKTEST_SEASONS,
        START_WEEK
    )
)

games = cursor.fetchall()

print(
    f"Found {len(games)} completed games "
    f"across {BACKTEST_SEASONS}"
)

results = []


for index, game in enumerate(
    games,
    start=1
):
    (
        season,
        game_id,
        week,
        game_date,

        away_team_id,
        away_team,
        away_score,

        home_team_id,
        home_team,
        home_score
    ) = game

    # -------------------------
    # CURRENT-season PROFILES
    # -------------------------

    away_scoring = get_team_scoring_profile(
        cursor,
        away_team_id,
        season,
        game_date
    )

    home_scoring = get_team_scoring_profile(
        cursor,
        home_team_id,
        season,
        game_date
    )

    away_boxscore = get_team_boxscore_profile(
        cursor,
        away_team_id,
        season,
        game_date
    )

    home_boxscore = get_team_boxscore_profile(
        cursor,
        home_team_id,
        season,
        game_date
    )

    away_defense = get_team_defensive_profile(
        cursor,
        away_team_id,
        season,
        game_date
    )

    home_defense = get_team_defensive_profile(
        cursor,
        home_team_id,
        season,
        game_date
    )


    # -------------------------
    # PREVIOUS-season PROFILES
    # -------------------------

    previous_season = season - 1

    away_previous_scoring = get_team_scoring_profile(
        cursor,
        away_team_id,
        previous_season,
        game_date
    )

    home_previous_scoring = get_team_scoring_profile(
        cursor,
        home_team_id,
        previous_season,
        game_date
    )

    away_previous_boxscore = get_team_boxscore_profile(
        cursor,
        away_team_id,
        previous_season,
        game_date
    )

    home_previous_boxscore = get_team_boxscore_profile(
        cursor,
        home_team_id,
        previous_season,
        game_date
    )

    away_previous_defense = get_team_defensive_profile(
        cursor,
        away_team_id,
        previous_season,
        game_date
    )

    home_previous_defense = get_team_defensive_profile(
        cursor,
        home_team_id,
        previous_season,
        game_date
    )


    # -------------------------
    # season BLEND WEIGHTS
    # -------------------------

    away_current_games = (
        away_scoring["games_played"]
        if away_scoring
        else 0
    )

    home_current_games = (
        home_scoring["games_played"]
        if home_scoring
        else 0
    )

    away_blend_weights = get_season_blend_weights(
        away_current_games
    )

    home_blend_weights = get_season_blend_weights(
        home_current_games
    )


    # -------------------------
    # BLENDED PROFILES
    # -------------------------

    away_scoring_blended = blend_profile(
        away_previous_scoring,
        away_scoring,
        away_blend_weights["previous_season"],
        away_blend_weights["current_season"]
    )

    home_scoring_blended = blend_profile(
        home_previous_scoring,
        home_scoring,
        home_blend_weights["previous_season"],
        home_blend_weights["current_season"]
    )

    away_boxscore_blended = blend_profile(
        away_previous_boxscore,
        away_boxscore,
        away_blend_weights["previous_season"],
        away_blend_weights["current_season"]
    )

    home_boxscore_blended = blend_profile(
        home_previous_boxscore,
        home_boxscore,
        home_blend_weights["previous_season"],
        home_blend_weights["current_season"]
    )

    away_defense_blended = blend_profile(
        away_previous_defense,
        away_defense,
        away_blend_weights["previous_season"],
        away_blend_weights["current_season"]
    )

    home_defense_blended = blend_profile(
        home_previous_defense,
        home_defense,
        home_blend_weights["previous_season"],
        home_blend_weights["current_season"]
    )


    missing_profiles = []

    profiles_to_check = {
        "away_scoring": away_scoring_blended,
        "home_scoring": home_scoring_blended,
        "away_boxscore": away_boxscore_blended,
        "home_boxscore": home_boxscore_blended,
        "away_defense": away_defense_blended,
        "home_defense": home_defense_blended
    }

    for profile_name, profile in profiles_to_check.items():
        if profile is None:
            missing_profiles.append(profile_name)

    if missing_profiles:
        print(
            f"[{index}/{len(games)}] "
            f"Skipped {away_team} @ {home_team}: "
            f"missing {', '.join(missing_profiles)}"
        )
        continue

    # -------------------------
    # POWER RATINGS
    # -------------------------

    away_power = get_team_power_rating(
        away_scoring_blended,
        away_boxscore_blended,
        away_defense_blended
    )

    home_power = get_team_power_rating(
        home_scoring_blended,
        home_boxscore_blended,
        home_defense_blended
    )

    # -------------------------
    # MATCHUP
    # -------------------------

    current_league_baselines = get_league_matchup_baselines(
        cursor,
        season,
        game_date
    )

    previous_league_baselines = get_league_matchup_baselines(
        cursor,
        previous_season,
        game_date
    )

    league_current_games = min(
        away_current_games,
        home_current_games
    )

    league_blend_weights = get_season_blend_weights(
        league_current_games
    )

    league_baselines = blend_profile(
        previous_league_baselines,
        current_league_baselines,
        league_blend_weights["previous_season"],
        league_blend_weights["current_season"]
    )

    away_comparison = get_matchup_comparison(
        away_boxscore_blended,
        home_defense_blended
    )

    home_comparison = get_matchup_comparison(
        home_boxscore_blended,
        away_defense_blended
    )

    away_edges = get_matchup_edges(
        away_comparison,
        league_baselines
    )

    home_edges = get_matchup_edges(
        home_comparison,
        league_baselines
    )

    matchup_adjustment = (
        get_matchup_prediction_adjustment(
            away_edges,
            home_edges
        )
    )

    # -------------------------
    # RECENT FORM
    # -------------------------

    recent_form_adjustment = (
        get_recent_form_adjustment(
            away_scoring,
            home_scoring,
            away_boxscore,
            home_boxscore,
            away_defense,
            home_defense
        )
    )

    # -------------------------
    # RAW MODEL
    # -------------------------

    prediction = get_raw_prediction_edge(
        away_power,
        home_power,
        matchup_adjustment,
        recent_form_adjustment
    )

    if not prediction:
        continue

    raw_edge = prediction["raw_edge"]

    # Positive = model favors home.
    # Negative = model favors away.

    if raw_edge > 0:
        predicted_winner = home_team

    elif raw_edge < 0:
        predicted_winner = away_team

    else:
        predicted_winner = "Even"

    # -------------------------
    # ACTUAL RESULT
    # -------------------------

    if home_score > away_score:
        actual_winner = home_team
        actual_home_win = 1

    elif away_score > home_score:
        actual_winner = away_team
        actual_home_win = 0

    else:
        actual_winner = "Tie"
        actual_home_win = None

    correct = (
        predicted_winner == actual_winner
    )

    results.append(
        {
            "season": season,
            "game_id": game_id,
            "week": week,
            "game_date": game_date,

            "away_team": away_team,
            "home_team": home_team,

            "away_score": away_score,
            "home_score": home_score,

            "power_edge": prediction[
                "power_edge"
            ],
            "home_field_edge": prediction[
                "home_field_edge"
            ],
            "matchup_edge": prediction[
                "matchup_edge"
            ],
            "recent_form_edge": prediction[
                "recent_form_edge"
            ],
            "raw_edge": raw_edge,

            "predicted_winner": predicted_winner,
            "actual_winner": actual_winner,
            "actual_home_win": actual_home_win,
            "correct": correct
        }
    )

    print(
        f"[{index}/{len(games)}] "
        f"{away_team} @ {home_team} | "
        f"Edge {raw_edge:+.2f} | "
        f"{'CORRECT' if correct else 'MISS'}"
    )

output_file = "multi_season_prediction_backtest.csv"

if results:

    with open(
        output_file,
        "w",
        newline=""
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=results[0].keys()
        )

        writer.writeheader()
        writer.writerows(results)

    print(
        f"\nSaved {len(results)} predictions "
        f"to {output_file}"
    )

non_ties = [
    row
    for row in results
    if row["actual_home_win"] is not None
]

correct_predictions = sum(
    1
    for row in non_ties
    if row["correct"]
)

if non_ties:

    accuracy = (
        correct_predictions
        / len(non_ties)
    )

    print("\nBACKTEST SUMMARY")
    print("\nACCURACY BY SEASON")
    print("------------------")

    for backtest_season in BACKTEST_SEASONS:

        season_games = [
            row
            for row in non_ties
            if row["season"] == backtest_season
        ]

        if not season_games:
            continue

        season_correct = sum(
            1
            for row in season_games
            if row["correct"]
        )

        season_accuracy = (
            season_correct
            / len(season_games)
        )

        print(
            f"{backtest_season}: "
            f"{season_correct}/"
            f"{len(season_games)} "
            f"({season_accuracy * 100:.1f}%)"
        )

buckets = [
    (
        "0–2",
        lambda edge: 0 < abs(edge) <= 2
    ),
    (
        "2–5",
        lambda edge: 2 < abs(edge) <= 5
    ),
    (
        "5–10",
        lambda edge: 5 < abs(edge) <= 10
    ),
    (
        "10+",
        lambda edge: abs(edge) > 10
    )
]


print("\nEDGE STRENGTH")
print("-------------")

for name, condition in buckets:

    bucket_games = [
        row
        for row in non_ties
        if condition(row["raw_edge"])
    ]

    if not bucket_games:
        continue

    bucket_correct = sum(
        1
        for row in bucket_games
        if row["correct"]
    )

    bucket_accuracy = (
        bucket_correct
        / len(bucket_games)
    )

    print(
        f"{name}: "
        f"{bucket_correct}/"
        f"{len(bucket_games)} "
        f"({bucket_accuracy * 100:.1f}%)"
    )

cursor.close()
connection.close()