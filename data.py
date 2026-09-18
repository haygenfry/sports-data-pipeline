from analytics import get_team_power_rating

def get_last_three(cursor, team_id, season, game_date):
    cursor.execute(
        """
        SELECT
            away_team_id,
            away_score,
            home_team_id,
            home_score
        FROM nfl_games
        WHERE completed = TRUE
          AND season = %s
          AND game_date < %s
          AND (
              away_team_id = %s
              OR home_team_id = %s
          )
        ORDER BY game_date DESC
        LIMIT 3;
        """,
        (season, game_date, team_id, team_id)
    )

    games = cursor.fetchall()

    results = []

    for away_team_id, away_score, home_team_id, home_score in games:
        if away_score == home_score:
            results.append("T")
        elif away_team_id == team_id:
            results.append("W" if away_score > home_score else "L")
        else:
            results.append("W" if home_score > away_score else "L")

    return results


def get_head_to_head(cursor, team_1_id, team_2_id, game_date):
    cursor.execute(
        """
        SELECT
            season,
            game_date,
            away_team,
            away_score,
            home_team,
            home_score
        FROM nfl_games
        WHERE completed = TRUE
          AND game_date < %s
          AND (
              (away_team_id = %s AND home_team_id = %s)
              OR
              (away_team_id = %s AND home_team_id = %s)
          )
        ORDER BY game_date DESC
        LIMIT 5;
        """,
        (
            game_date,
            team_1_id,
            team_2_id,
            team_2_id,
            team_1_id
        )
    )

    return cursor.fetchall()


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

def get_matchup_profile_rows_bulk(
    cursor,
    away_team_id,
    home_team_id,
    current_season,
    current_game_date,
    previous_season
):
    # ---------------------------------
    # SCORING ROWS
    # ---------------------------------

    cursor.execute(
        """
        SELECT
            season,
            home_team_id,
            home_score,
            away_team_id,
            away_score,
            game_date
        FROM nfl_games
        WHERE completed = TRUE
          AND season IN (%s, %s)
          AND (
              home_team_id IN (%s::text, %s::text)
              OR away_team_id IN (%s::text, %s::text)
          )
          AND (
              season = %s
              OR game_date < %s
          )
        ORDER BY season, game_date;
        """,
        (
            current_season,
            previous_season,
            away_team_id,
            home_team_id,
            away_team_id,
            home_team_id,
            previous_season,
            current_game_date
        )
    )

    scoring_rows = cursor.fetchall()

    # ---------------------------------
    # TEAM STAT ROWS
    # ---------------------------------

    cursor.execute(
        """
        SELECT
            g.season,
            g.game_date,
            s.game_id,
            s.team_id,
            s.total_yards,
            s.passing_yards,
            s.rushing_yards,
            s.yards_per_play,
            s.first_downs,
            s.turnovers,
            s.third_down_eff,
            s.red_zone_eff,
            s.possession_time,
            s.defensive_touchdowns
        FROM nfl_team_game_stats s
        JOIN nfl_games g
            ON s.game_id = g.game_id
        WHERE g.completed = TRUE
          AND g.season IN (%s, %s)
          AND s.team_id IN (%s::text, %s::text)
          AND (
              g.season = %s
              OR g.game_date < %s
          )
        ORDER BY g.season, g.game_date;
        """,
        (
            current_season,
            previous_season,
            away_team_id,
            home_team_id,
            previous_season,
            current_game_date
        )
    )

    team_stat_rows = cursor.fetchall()

    # ---------------------------------
    # OPPONENT STAT ROWS
    # ---------------------------------

    cursor.execute(
        """
        SELECT
            g.season,
            g.game_date,
            team.game_id,
            team.team_id,
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
        WHERE g.completed = TRUE
          AND g.season IN (%s, %s)
          AND team.team_id IN (%s::text, %s::text)
          AND (
              g.season = %s
              OR g.game_date < %s
          )
        ORDER BY g.season, g.game_date;
        """,
        (
            current_season,
            previous_season,
            away_team_id,
            home_team_id,
            previous_season,
            current_game_date
        )
    )

    defensive_rows = cursor.fetchall()

    return {
        "scoring": scoring_rows,
        "boxscore": team_stat_rows,
        "defense": defensive_rows
    }

def build_scoring_profile_from_rows(
    rows,
    team_id,
    season
):
    team_id = str(team_id)

    games = [
        row
        for row in rows
        if row[0] == season
        and (
            row[1] == team_id
            or row[3] == team_id
        )
    ]

    if not games:
        return None

    points_for = 0
    points_against = 0
    wins = 0

    home_points_for = 0
    home_games = 0

    road_points_for = 0
    road_games = 0

    for (
        _,
        home_team_id,
        home_score,
        away_team_id,
        away_score,
        _
    ) in games:

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

    for (
        _,
        home_team_id,
        home_score,
        away_team_id,
        away_score,
        _
    ) in last_three_games:

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
        "scoring_margin": (
            points_for - points_against
        ) / games_played,
        "win_pct": wins / games_played,

        "home_ppg": (
            home_points_for / home_games
            if home_games
            else None
        ),

        "road_ppg": (
            road_points_for / road_games
            if road_games
            else None
        ),

        "last_three_ppg": (
            last_three_points_for / last_three_count
        ),

        "last_three_ppg_allowed": (
            last_three_points_against / last_three_count
        )
    }


def build_boxscore_profile_from_rows(
    rows,
    team_id,
    season
):
    team_id = str(team_id)

    team_rows = [
        row
        for row in rows
        if row[0] == season
        and row[3] == team_id
    ]

    if not team_rows:
        return None

    last_three_rows = team_rows[-3:]

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

    for row in team_rows:
        game_total_yards = row[4]
        game_passing_yards = row[5]
        game_rushing_yards = row[6]
        game_yards_per_play = row[7]
        game_first_downs = row[8]
        game_turnovers = row[9]
        game_third_down_eff = row[10]
        game_red_zone_eff = row[11]
        game_possession_time = row[12]

        total_yards += game_total_yards
        passing_yards += game_passing_yards
        rushing_yards += game_rushing_yards
        yards_per_play += float(game_yards_per_play)
        first_downs += game_first_downs
        turnovers += game_turnovers

        third_made, third_attempts = (
            game_third_down_eff.split("-")
        )

        third_down_made += int(third_made)
        third_down_attempts += int(third_attempts)

        red_made, red_attempts = (
            game_red_zone_eff.split("-")
        )

        red_zone_made += int(red_made)
        red_zone_attempts += int(red_attempts)

        minutes, seconds = (
            game_possession_time.split(":")
        )

        possession_seconds += (
            int(minutes) * 60
            + int(seconds)
        )

    games_played = len(team_rows)

    average_possession_seconds = (
        possession_seconds / games_played
    )

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
        row[4]
        for row in last_three_rows
    )

    last_three_turnovers = sum(
        row[9]
        for row in last_three_rows
    )

    last_three_games = len(last_three_rows)

    return {
        "total_yards_per_game": (
            total_yards / games_played
        ),

        "passing_yards_per_game": (
            passing_yards / games_played
        ),

        "rushing_yards_per_game": (
            rushing_yards / games_played
        ),

        "yards_per_play": (
            yards_per_play / games_played
        ),

        "first_downs_per_game": (
            first_downs / games_played
        ),

        "turnovers_per_game": (
            turnovers / games_played
        ),

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
            last_three_total_yards
            / last_three_games
        ),

        "last_three_turnovers_per_game": (
            last_three_turnovers
            / last_three_games
        ),

        "last_three_turnovers": (
            last_three_turnovers
        )
    }


def build_defensive_profile_from_rows(
    rows,
    team_id,
    season
):
    team_id = str(team_id)

    team_rows = [
        row
        for row in rows
        if row[0] == season
        and row[3] == team_id
    ]

    if not team_rows:
        return None

    last_three_rows = team_rows[-3:]

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

    for row in team_rows:
        opponent_total_yards = row[4]
        opponent_passing_yards = row[5]
        opponent_rushing_yards = row[6]
        opponent_yards_per_play = row[7]
        opponent_first_downs = row[8]
        opponent_turnovers = row[9]
        opponent_third_down_eff = row[10]
        opponent_red_zone_eff = row[11]
        game_defensive_touchdowns = row[12]

        total_yards_allowed += opponent_total_yards
        passing_yards_allowed += opponent_passing_yards
        rushing_yards_allowed += opponent_rushing_yards

        yards_per_play_allowed += float(
            opponent_yards_per_play
        )

        first_downs_allowed += opponent_first_downs
        takeaways += opponent_turnovers

        defensive_touchdowns += (
            game_defensive_touchdowns
        )

        third_made, third_attempts = (
            opponent_third_down_eff.split("-")
        )

        opponent_third_down_made += int(
            third_made
        )

        opponent_third_down_attempts += int(
            third_attempts
        )

        red_made, red_attempts = (
            opponent_red_zone_eff.split("-")
        )

        opponent_red_zone_made += int(red_made)
        opponent_red_zone_attempts += int(
            red_attempts
        )

    games_played = len(team_rows)

    last_three_yards_allowed = sum(
        row[4]
        for row in last_three_rows
    )

    last_three_takeaways = sum(
        row[9]
        for row in last_three_rows
    )

    last_three_games = len(last_three_rows)

    return {
        "yards_allowed_per_game": (
            total_yards_allowed / games_played
        ),

        "passing_yards_allowed_per_game": (
            passing_yards_allowed / games_played
        ),

        "rushing_yards_allowed_per_game": (
            rushing_yards_allowed / games_played
        ),

        "yards_per_play_allowed": (
            yards_per_play_allowed / games_played
        ),

        "first_downs_allowed_per_game": (
            first_downs_allowed / games_played
        ),

        "takeaways_per_game": (
            takeaways / games_played
        ),

        "opponent_third_down_pct": (
            opponent_third_down_made
            / opponent_third_down_attempts
            if opponent_third_down_attempts
            else 0
        ),

        "opponent_red_zone_pct": (
            opponent_red_zone_made
            / opponent_red_zone_attempts
            if opponent_red_zone_attempts
            else 0
        ),

        "defensive_touchdowns": (
            defensive_touchdowns
        ),

        "last_three_yards_allowed_per_game": (
            last_three_yards_allowed
            / last_three_games
        ),

        "last_three_takeaways_per_game": (
            last_three_takeaways
            / last_three_games
        ),

        "last_three_takeaways": (
            last_three_takeaways
        )
    }


def build_matchup_profiles_from_bulk_rows(
    bulk_rows,
    away_team_id,
    home_team_id,
    current_season,
    previous_season
):
    profiles = {}

    for label, team_id in (
        ("away", away_team_id),
        ("home", home_team_id)
    ):
        profiles[f"{label}_scoring"] = (
            build_scoring_profile_from_rows(
                bulk_rows["scoring"],
                team_id,
                current_season
            )
        )

        profiles[f"{label}_boxscore"] = (
            build_boxscore_profile_from_rows(
                bulk_rows["boxscore"],
                team_id,
                current_season
            )
        )

        profiles[f"{label}_defense"] = (
            build_defensive_profile_from_rows(
                bulk_rows["defense"],
                team_id,
                current_season
            )
        )

        profiles[f"{label}_previous_scoring"] = (
            build_scoring_profile_from_rows(
                bulk_rows["scoring"],
                team_id,
                previous_season
            )
        )

        profiles[f"{label}_previous_boxscore"] = (
            build_boxscore_profile_from_rows(
                bulk_rows["boxscore"],
                team_id,
                previous_season
            )
        )

        profiles[f"{label}_previous_defense"] = (
            build_defensive_profile_from_rows(
                bulk_rows["defense"],
                team_id,
                previous_season
            )
        )

    return profiles

def get_offensive_starters(cursor, team_id):
    cursor.execute(
        """
        SELECT
            d.position_slot,
            d.position,
            d.player_id,
            d.player_name,
            p.jersey,
            p.status,
            p.headshot
        FROM nfl_depth_chart d
        LEFT JOIN nfl_players p
            ON d.player_id = p.player_id
        WHERE d.team_id = %s
          AND d.depth_order = 1
          AND d.position_group = 'OFF'
        ORDER BY d.position_slot;
        """,
        (team_id,)
    )

    return cursor.fetchall()


def get_defensive_starters(cursor, team_id):
    cursor.execute(
        """
        SELECT
            d.position_slot,
            d.position,
            d.player_id,
            d.player_name,
            p.jersey,
            p.status,
            p.headshot
        FROM nfl_depth_chart d
        LEFT JOIN nfl_players p
            ON d.player_id = p.player_id
        WHERE d.team_id = %s
          AND d.depth_order = 1
          AND d.position_group = 'DEF'
        ORDER BY d.position_slot;
        """,
        (team_id,)
    )

    return cursor.fetchall()


def get_special_teams_starters(cursor, team_id):
    cursor.execute(
        """
        SELECT
            d.position_slot,
            d.position,
            d.player_id,
            d.player_name,
            p.jersey,
            p.status,
            p.headshot
        FROM nfl_depth_chart d
        LEFT JOIN nfl_players p
            ON d.player_id = p.player_id
        WHERE d.team_id = %s
          AND d.depth_order = 1
          AND d.position_group = 'ST'
        ORDER BY d.position_slot;
        """,
        (team_id,)
    )

    return cursor.fetchall()


def get_qb_profile(cursor, player_id, season, game_date):
    cursor.execute(
        """
        SELECT
            p.completions_attempts,
            p.passing_yards,
            p.passing_touchdowns,
            p.passing_interceptions,
            p.qbr,
            p.passer_rating,
            p.rushing_attempts,
            p.rushing_yards,
            p.rushing_touchdowns
        FROM nfl_player_game_stats p
        JOIN nfl_games g
            ON p.game_id = g.game_id
        WHERE p.player_id = %s
          AND g.season = %s
          AND g.completed = TRUE
          AND g.game_date < %s
        ORDER BY g.game_date;
        """,
        (player_id, season, game_date)
    )

    rows = cursor.fetchall()

    if not rows:
        return None

    completions = 0
    attempts = 0
    passing_yards = 0
    passing_touchdowns = 0
    interceptions = 0

    rushing_attempts = 0
    rushing_yards = 0
    rushing_touchdowns = 0

    qbr_values = []
    passer_rating_values = []

    for (
        completions_attempts,
        game_passing_yards,
        game_passing_touchdowns,
        game_interceptions,
        qbr,
        passer_rating,
        game_rushing_attempts,
        game_rushing_yards,
        game_rushing_touchdowns
    ) in rows:

        if completions_attempts:
            game_completions, game_attempts = (
                completions_attempts.split("/")
            )

            completions += int(game_completions)
            attempts += int(game_attempts)

        if game_passing_yards is not None:
            passing_yards += game_passing_yards

        if game_passing_touchdowns is not None:
            passing_touchdowns += game_passing_touchdowns

        if game_interceptions is not None:
            interceptions += game_interceptions

        if qbr is not None:
            qbr_values.append(float(qbr))

        if passer_rating is not None:
            passer_rating_values.append(float(passer_rating))

        if game_rushing_attempts is not None:
            rushing_attempts += game_rushing_attempts

        if game_rushing_yards is not None:
            rushing_yards += game_rushing_yards

        if game_rushing_touchdowns is not None:
            rushing_touchdowns += game_rushing_touchdowns

    games_played = len(rows)

    return {
        "games_played": games_played,
        "completions": completions,
        "attempts": attempts,
        "completion_pct": (
            completions / attempts
            if attempts
            else 0
        ),
        "passing_yards": passing_yards,
        "passing_yards_per_game": (
            passing_yards / games_played
        ),
        "passing_touchdowns": passing_touchdowns,
        "interceptions": interceptions,
        "yards_per_attempt": (
            passing_yards / attempts
            if attempts
            else 0
        ),
        "average_qbr": (
            sum(qbr_values) / len(qbr_values)
            if qbr_values
            else None
        ),
        "average_passer_rating": (
            sum(passer_rating_values) / len(passer_rating_values)
            if passer_rating_values
            else None
        ),
        "rushing_attempts": rushing_attempts,
        "rushing_yards": rushing_yards,
        "rushing_touchdowns": rushing_touchdowns
    }

def get_qb_profiles(
    cursor,
    player_ids,
    season,
    game_date
):
    if not player_ids:
        return {}

    cursor.execute(
        """
        SELECT
            p.player_id,
            p.completions_attempts,
            p.passing_yards,
            p.passing_touchdowns,
            p.passing_interceptions,
            p.qbr,
            p.passer_rating,
            p.rushing_attempts,
            p.rushing_yards,
            p.rushing_touchdowns
        FROM nfl_player_game_stats p
        JOIN nfl_games g
            ON p.game_id = g.game_id
        WHERE p.player_id = ANY(%s)
          AND g.season = %s
          AND g.completed = TRUE
          AND g.game_date < %s
        ORDER BY p.player_id, g.game_date;
        """,
        (player_ids, season, game_date)
    )

    grouped_rows = {}

    for row in cursor.fetchall():
        grouped_rows.setdefault(
            row[0],
            []
        ).append(row[1:])

    profiles = {}

    for player_id in player_ids:
        rows = grouped_rows.get(player_id, [])

        if not rows:
            profiles[player_id] = None
            continue

        completions = 0
        attempts = 0
        passing_yards = 0
        passing_touchdowns = 0
        interceptions = 0
        rushing_attempts = 0
        rushing_yards = 0
        rushing_touchdowns = 0
        qbr_values = []
        passer_rating_values = []

        for (
            completions_attempts,
            game_passing_yards,
            game_passing_touchdowns,
            game_interceptions,
            qbr,
            passer_rating,
            game_rushing_attempts,
            game_rushing_yards,
            game_rushing_touchdowns
        ) in rows:

            if completions_attempts:
                game_completions, game_attempts = (
                    completions_attempts.split("/")
                )
                completions += int(game_completions)
                attempts += int(game_attempts)

            if game_passing_yards is not None:
                passing_yards += game_passing_yards

            if game_passing_touchdowns is not None:
                passing_touchdowns += game_passing_touchdowns

            if game_interceptions is not None:
                interceptions += game_interceptions

            if qbr is not None:
                qbr_values.append(float(qbr))

            if passer_rating is not None:
                passer_rating_values.append(
                    float(passer_rating)
                )

            if game_rushing_attempts is not None:
                rushing_attempts += game_rushing_attempts

            if game_rushing_yards is not None:
                rushing_yards += game_rushing_yards

            if game_rushing_touchdowns is not None:
                rushing_touchdowns += (
                    game_rushing_touchdowns
                )

        games_played = len(rows)

        profiles[player_id] = {
            "games_played": games_played,
            "completions": completions,
            "attempts": attempts,
            "completion_pct": (
                completions / attempts
                if attempts
                else 0
            ),
            "passing_yards": passing_yards,
            "passing_yards_per_game": (
                passing_yards / games_played
            ),
            "passing_touchdowns": passing_touchdowns,
            "interceptions": interceptions,
            "yards_per_attempt": (
                passing_yards / attempts
                if attempts
                else 0
            ),
            "average_qbr": (
                sum(qbr_values) / len(qbr_values)
                if qbr_values
                else None
            ),
            "average_passer_rating": (
                sum(passer_rating_values)
                / len(passer_rating_values)
                if passer_rating_values
                else None
            ),
            "rushing_attempts": rushing_attempts,
            "rushing_yards": rushing_yards,
            "rushing_touchdowns": rushing_touchdowns
        }

    return profiles


def get_rb_profile(cursor, player_id, season, game_date):
    cursor.execute(
        """
        SELECT
            p.rushing_attempts,
            p.rushing_yards,
            p.rushing_touchdowns,
            p.receptions,
            p.receiving_yards,
            p.receiving_touchdowns,
            p.receiving_targets
        FROM nfl_player_game_stats p
        JOIN nfl_games g
            ON p.game_id = g.game_id
        WHERE p.player_id = %s
          AND g.season = %s
          AND g.completed = TRUE
          AND g.game_date < %s
        ORDER BY g.game_date;
        """,
        (player_id, season, game_date)
    )

    rows = cursor.fetchall()

    if not rows:
        return None

    rushing_attempts = 0
    rushing_yards = 0
    rushing_touchdowns = 0

    receptions = 0
    receiving_yards = 0
    receiving_touchdowns = 0
    receiving_targets = 0

    for (
        game_rushing_attempts,
        game_rushing_yards,
        game_rushing_touchdowns,
        game_receptions,
        game_receiving_yards,
        game_receiving_touchdowns,
        game_receiving_targets
    ) in rows:

        if game_rushing_attempts is not None:
            rushing_attempts += game_rushing_attempts

        if game_rushing_yards is not None:
            rushing_yards += game_rushing_yards

        if game_rushing_touchdowns is not None:
            rushing_touchdowns += game_rushing_touchdowns

        if game_receptions is not None:
            receptions += game_receptions

        if game_receiving_yards is not None:
            receiving_yards += game_receiving_yards

        if game_receiving_touchdowns is not None:
            receiving_touchdowns += game_receiving_touchdowns

        if game_receiving_targets is not None:
            receiving_targets += game_receiving_targets

    games_played = len(rows)

    return {
        "games_played": games_played,
        "rushing_attempts": rushing_attempts,
        "rushing_yards": rushing_yards,
        "rushing_yards_per_game": (
            rushing_yards / games_played
        ),
        "yards_per_carry": (
            rushing_yards / rushing_attempts
            if rushing_attempts
            else 0
        ),
        "rushing_touchdowns": rushing_touchdowns,
        "receptions": receptions,
        "receiving_targets": receiving_targets,
        "receiving_yards": receiving_yards,
        "receiving_yards_per_game": (
            receiving_yards / games_played
        ),
        "receiving_touchdowns": receiving_touchdowns,
        "scrimmage_yards": (
            rushing_yards + receiving_yards
        ),
        "total_touchdowns": (
            rushing_touchdowns + receiving_touchdowns
        )
    }

def get_rb_profiles(
    cursor,
    player_ids,
    season,
    game_date
):
    if not player_ids:
        return {}

    cursor.execute(
        """
        SELECT
            p.player_id,
            p.rushing_attempts,
            p.rushing_yards,
            p.rushing_touchdowns,
            p.receptions,
            p.receiving_yards,
            p.receiving_touchdowns,
            p.receiving_targets
        FROM nfl_player_game_stats p
        JOIN nfl_games g
            ON p.game_id = g.game_id
        WHERE p.player_id = ANY(%s)
          AND g.season = %s
          AND g.completed = TRUE
          AND g.game_date < %s
        ORDER BY p.player_id, g.game_date;
        """,
        (player_ids, season, game_date)
    )

    grouped_rows = {}

    for row in cursor.fetchall():
        grouped_rows.setdefault(
            row[0],
            []
        ).append(row[1:])

    profiles = {}

    for player_id in player_ids:
        rows = grouped_rows.get(player_id, [])

        if not rows:
            profiles[player_id] = None
            continue

        rushing_attempts = 0
        rushing_yards = 0
        rushing_touchdowns = 0
        receptions = 0
        receiving_yards = 0
        receiving_touchdowns = 0
        receiving_targets = 0

        for (
            game_rushing_attempts,
            game_rushing_yards,
            game_rushing_touchdowns,
            game_receptions,
            game_receiving_yards,
            game_receiving_touchdowns,
            game_receiving_targets
        ) in rows:

            if game_rushing_attempts is not None:
                rushing_attempts += game_rushing_attempts

            if game_rushing_yards is not None:
                rushing_yards += game_rushing_yards

            if game_rushing_touchdowns is not None:
                rushing_touchdowns += (
                    game_rushing_touchdowns
                )

            if game_receptions is not None:
                receptions += game_receptions

            if game_receiving_yards is not None:
                receiving_yards += game_receiving_yards

            if game_receiving_touchdowns is not None:
                receiving_touchdowns += (
                    game_receiving_touchdowns
                )

            if game_receiving_targets is not None:
                receiving_targets += game_receiving_targets

        games_played = len(rows)

        profiles[player_id] = {
            "games_played": games_played,
            "rushing_attempts": rushing_attempts,
            "rushing_yards": rushing_yards,
            "rushing_yards_per_game": (
                rushing_yards / games_played
            ),
            "yards_per_carry": (
                rushing_yards / rushing_attempts
                if rushing_attempts
                else 0
            ),
            "rushing_touchdowns": rushing_touchdowns,
            "receptions": receptions,
            "receiving_targets": receiving_targets,
            "receiving_yards": receiving_yards,
            "receiving_yards_per_game": (
                receiving_yards / games_played
            ),
            "receiving_touchdowns": receiving_touchdowns,
            "scrimmage_yards": (
                rushing_yards + receiving_yards
            ),
            "total_touchdowns": (
                rushing_touchdowns
                + receiving_touchdowns
            )
        }

    return profiles

def get_receiving_profile(cursor, player_id, season, game_date):
    cursor.execute(
        """
        SELECT
            p.receptions,
            p.receiving_targets,
            p.receiving_yards,
            p.receiving_touchdowns,
            p.rushing_attempts,
            p.rushing_yards,
            p.rushing_touchdowns
        FROM nfl_player_game_stats p
        JOIN nfl_games g
            ON p.game_id = g.game_id
        WHERE p.player_id = %s
          AND g.season = %s
          AND g.completed = TRUE
          AND g.game_date < %s
        ORDER BY g.game_date;
        """,
        (player_id, season, game_date)
    )

    rows = cursor.fetchall()

    if not rows:
        return None

    receptions = 0
    targets = 0
    receiving_yards = 0
    receiving_touchdowns = 0

    rushing_attempts = 0
    rushing_yards = 0
    rushing_touchdowns = 0

    for (
        game_receptions,
        game_targets,
        game_receiving_yards,
        game_receiving_touchdowns,
        game_rushing_attempts,
        game_rushing_yards,
        game_rushing_touchdowns
    ) in rows:

        if game_receptions is not None:
            receptions += game_receptions

        if game_targets is not None:
            targets += game_targets

        if game_receiving_yards is not None:
            receiving_yards += game_receiving_yards

        if game_receiving_touchdowns is not None:
            receiving_touchdowns += game_receiving_touchdowns

        if game_rushing_attempts is not None:
            rushing_attempts += game_rushing_attempts

        if game_rushing_yards is not None:
            rushing_yards += game_rushing_yards

        if game_rushing_touchdowns is not None:
            rushing_touchdowns += game_rushing_touchdowns

    games_played = len(rows)

    return {
        "games_played": games_played,
        "receptions": receptions,
        "targets": targets,
        "catch_pct": (
            receptions / targets
            if targets
            else 0
        ),
        "receiving_yards": receiving_yards,
        "receiving_yards_per_game": (
            receiving_yards / games_played
        ),
        "yards_per_reception": (
            receiving_yards / receptions
            if receptions
            else 0
        ),
        "receiving_touchdowns": receiving_touchdowns,
        "rushing_attempts": rushing_attempts,
        "rushing_yards": rushing_yards,
        "rushing_touchdowns": rushing_touchdowns
    }

def get_receiving_profiles(
    cursor,
    player_ids,
    season,
    game_date
):
    if not player_ids:
        return {}

    cursor.execute(
        """
        SELECT
            p.player_id,
            p.receptions,
            p.receiving_targets,
            p.receiving_yards,
            p.receiving_touchdowns,
            p.rushing_attempts,
            p.rushing_yards,
            p.rushing_touchdowns
        FROM nfl_player_game_stats p
        JOIN nfl_games g
            ON p.game_id = g.game_id
        WHERE p.player_id = ANY(%s)
          AND g.season = %s
          AND g.completed = TRUE
          AND g.game_date < %s
        ORDER BY p.player_id, g.game_date;
        """,
        (player_ids, season, game_date)
    )

    rows = cursor.fetchall()

    grouped_rows = {}

    for row in rows:
        player_id = row[0]
        grouped_rows.setdefault(
            player_id,
            []
        ).append(row[1:])

    profiles = {}

    for player_id in player_ids:
        player_rows = grouped_rows.get(
            player_id,
            []
        )

        if not player_rows:
            profiles[player_id] = None
            continue

        receptions = 0
        targets = 0
        receiving_yards = 0
        receiving_touchdowns = 0
        rushing_attempts = 0
        rushing_yards = 0
        rushing_touchdowns = 0

        for (
            game_receptions,
            game_targets,
            game_receiving_yards,
            game_receiving_touchdowns,
            game_rushing_attempts,
            game_rushing_yards,
            game_rushing_touchdowns
        ) in player_rows:

            if game_receptions is not None:
                receptions += game_receptions

            if game_targets is not None:
                targets += game_targets

            if game_receiving_yards is not None:
                receiving_yards += game_receiving_yards

            if game_receiving_touchdowns is not None:
                receiving_touchdowns += (
                    game_receiving_touchdowns
                )

            if game_rushing_attempts is not None:
                rushing_attempts += (
                    game_rushing_attempts
                )

            if game_rushing_yards is not None:
                rushing_yards += game_rushing_yards

            if game_rushing_touchdowns is not None:
                rushing_touchdowns += (
                    game_rushing_touchdowns
                )

        games_played = len(player_rows)

        profiles[player_id] = {
            "games_played": games_played,
            "receptions": receptions,
            "targets": targets,
            "catch_pct": (
                receptions / targets
                if targets
                else 0
            ),
            "receiving_yards": receiving_yards,
            "receiving_yards_per_game": (
                receiving_yards / games_played
            ),
            "yards_per_reception": (
                receiving_yards / receptions
                if receptions
                else 0
            ),
            "receiving_touchdowns": (
                receiving_touchdowns
            ),
            "rushing_attempts": rushing_attempts,
            "rushing_yards": rushing_yards,
            "rushing_touchdowns": (
                rushing_touchdowns
            )
        }

    return profiles

def get_defensive_player_profile(
    cursor,
    player_id,
    season,
    game_date
):
    cursor.execute(
        """
        SELECT
            p.total_tackles,
            p.solo_tackles,
            p.sacks,
            p.tackles_for_loss,
            p.passes_defended,
            p.qb_hits,
            p.defensive_touchdowns,
            p.defensive_interceptions,
            p.interception_yards,
            p.interception_touchdowns,
            p.fumbles_recovered
        FROM nfl_player_game_stats p
        JOIN nfl_games g
            ON p.game_id = g.game_id
        WHERE p.player_id = %s
          AND g.season = %s
          AND g.completed = TRUE
          AND g.game_date < %s
        ORDER BY g.game_date;
        """,
        (player_id, season, game_date)
    )

    rows = cursor.fetchall()

    if not rows:
        return None

    total_tackles = 0
    solo_tackles = 0
    sacks = 0
    tackles_for_loss = 0
    passes_defended = 0
    qb_hits = 0
    defensive_touchdowns = 0
    interceptions = 0
    interception_yards = 0
    interception_touchdowns = 0
    fumbles_recovered = 0

    for (
        game_total_tackles,
        game_solo_tackles,
        game_sacks,
        game_tackles_for_loss,
        game_passes_defended,
        game_qb_hits,
        game_defensive_touchdowns,
        game_interceptions,
        game_interception_yards,
        game_interception_touchdowns,
        game_fumbles_recovered
    ) in rows:

        if game_total_tackles is not None:
            total_tackles += game_total_tackles

        if game_solo_tackles is not None:
            solo_tackles += game_solo_tackles

        if game_sacks is not None:
            sacks += float(game_sacks)

        if game_tackles_for_loss is not None:
            tackles_for_loss += float(game_tackles_for_loss)

        if game_passes_defended is not None:
            passes_defended += game_passes_defended

        if game_qb_hits is not None:
            qb_hits += game_qb_hits

        if game_defensive_touchdowns is not None:
            defensive_touchdowns += game_defensive_touchdowns

        if game_interceptions is not None:
            interceptions += game_interceptions

        if game_interception_yards is not None:
            interception_yards += game_interception_yards

        if game_interception_touchdowns is not None:
            interception_touchdowns += game_interception_touchdowns

        if game_fumbles_recovered is not None:
            fumbles_recovered += game_fumbles_recovered

    return {
        "games_played": len(rows),
        "total_tackles": total_tackles,
        "solo_tackles": solo_tackles,
        "sacks": sacks,
        "tackles_for_loss": tackles_for_loss,
        "passes_defended": passes_defended,
        "qb_hits": qb_hits,
        "defensive_touchdowns": defensive_touchdowns,
        "interceptions": interceptions,
        "interception_yards": interception_yards,
        "interception_touchdowns": interception_touchdowns,
        "fumbles_recovered": fumbles_recovered
    }

def get_defensive_player_profiles(
    cursor,
    player_ids,
    season,
    game_date
):
    if not player_ids:
        return {}

    cursor.execute(
        """
        SELECT
            p.player_id,
            p.total_tackles,
            p.solo_tackles,
            p.sacks,
            p.tackles_for_loss,
            p.passes_defended,
            p.qb_hits,
            p.defensive_touchdowns,
            p.defensive_interceptions,
            p.interception_yards,
            p.interception_touchdowns,
            p.fumbles_recovered
        FROM nfl_player_game_stats p
        JOIN nfl_games g
            ON p.game_id = g.game_id
        WHERE p.player_id = ANY(%s)
          AND g.season = %s
          AND g.completed = TRUE
          AND g.game_date < %s
        ORDER BY p.player_id, g.game_date;
        """,
        (player_ids, season, game_date)
    )

    rows = cursor.fetchall()

    grouped_rows = {}

    for row in rows:
        player_id = row[0]

        grouped_rows.setdefault(
            player_id,
            []
        ).append(row[1:])

    profiles = {}

    for player_id in player_ids:

        player_rows = grouped_rows.get(
            player_id,
            []
        )

        if not player_rows:
            profiles[player_id] = None
            continue

        total_tackles = 0
        solo_tackles = 0
        sacks = 0
        tackles_for_loss = 0
        passes_defended = 0
        qb_hits = 0
        defensive_touchdowns = 0
        interceptions = 0
        interception_yards = 0
        interception_touchdowns = 0
        fumbles_recovered = 0

        for (
            game_total_tackles,
            game_solo_tackles,
            game_sacks,
            game_tackles_for_loss,
            game_passes_defended,
            game_qb_hits,
            game_defensive_touchdowns,
            game_interceptions,
            game_interception_yards,
            game_interception_touchdowns,
            game_fumbles_recovered
        ) in player_rows:

            if game_total_tackles is not None:
                total_tackles += game_total_tackles

            if game_solo_tackles is not None:
                solo_tackles += game_solo_tackles

            if game_sacks is not None:
                sacks += float(game_sacks)

            if game_tackles_for_loss is not None:
                tackles_for_loss += float(
                    game_tackles_for_loss
                )

            if game_passes_defended is not None:
                passes_defended += game_passes_defended

            if game_qb_hits is not None:
                qb_hits += game_qb_hits

            if game_defensive_touchdowns is not None:
                defensive_touchdowns += (
                    game_defensive_touchdowns
                )

            if game_interceptions is not None:
                interceptions += game_interceptions

            if game_interception_yards is not None:
                interception_yards += (
                    game_interception_yards
                )

            if game_interception_touchdowns is not None:
                interception_touchdowns += (
                    game_interception_touchdowns
                )

            if game_fumbles_recovered is not None:
                fumbles_recovered += (
                    game_fumbles_recovered
                )

        profiles[player_id] = {
            "games_played": len(player_rows),
            "total_tackles": total_tackles,
            "solo_tackles": solo_tackles,
            "sacks": sacks,
            "tackles_for_loss": tackles_for_loss,
            "passes_defended": passes_defended,
            "qb_hits": qb_hits,
            "defensive_touchdowns": defensive_touchdowns,
            "interceptions": interceptions,
            "interception_yards": interception_yards,
            "interception_touchdowns": (
                interception_touchdowns
            ),
            "fumbles_recovered": fumbles_recovered
        }

    return profiles

def get_special_teams_profile(
    cursor,
    player_id,
    season,
    game_date
):
    cursor.execute(
        """
        SELECT
            p.kick_returns,
            p.kick_return_yards,
            p.yards_per_kick_return,
            p.long_kick_return,
            p.kick_return_touchdowns,
            p.punt_returns,
            p.punt_return_yards,
            p.yards_per_punt_return,
            p.long_punt_return,
            p.punt_return_touchdowns,
            p.field_goals_made_attempted,
            p.field_goal_pct,
            p.long_field_goal_made,
            p.extra_points_made_attempted,
            p.total_kicking_points,
            p.punts,
            p.punt_yards,
            p.gross_avg_punt_yards,
            p.touchbacks,
            p.punts_inside_20,
            p.long_punt
        FROM nfl_player_game_stats p
        JOIN nfl_games g
            ON p.game_id = g.game_id
        WHERE p.player_id = %s
          AND g.season = %s
          AND g.completed = TRUE
          AND g.game_date < %s
        ORDER BY g.game_date;
        """,
        (player_id, season, game_date)
    )

    rows = cursor.fetchall()

    if not rows:
        return None

    kick_returns = 0
    kick_return_yards = 0
    kick_return_touchdowns = 0
    long_kick_return = None

    punt_returns = 0
    punt_return_yards = 0
    punt_return_touchdowns = 0
    long_punt_return = None

    field_goals_made = 0
    field_goal_attempts = 0
    long_field_goal_made = None

    extra_points_made = 0
    extra_point_attempts = 0
    total_kicking_points = 0

    punts = 0
    punt_yards = 0
    touchbacks = 0
    punts_inside_20 = 0
    long_punt = None

    for (
        game_kick_returns,
        game_kick_return_yards,
        game_yards_per_kick_return,
        game_long_kick_return,
        game_kick_return_touchdowns,
        game_punt_returns,
        game_punt_return_yards,
        game_yards_per_punt_return,
        game_long_punt_return,
        game_punt_return_touchdowns,
        game_field_goals,
        game_field_goal_pct,
        game_long_field_goal,
        game_extra_points,
        game_total_kicking_points,
        game_punts,
        game_punt_yards,
        game_gross_avg_punt_yards,
        game_touchbacks,
        game_punts_inside_20,
        game_long_punt
    ) in rows:

        if game_kick_returns is not None:
            kick_returns += game_kick_returns

        if game_kick_return_yards is not None:
            kick_return_yards += game_kick_return_yards

        if game_kick_return_touchdowns is not None:
            kick_return_touchdowns += game_kick_return_touchdowns

        if game_long_kick_return is not None:
            long_kick_return = max(
                long_kick_return or game_long_kick_return,
                game_long_kick_return
            )

        if game_punt_returns is not None:
            punt_returns += game_punt_returns

        if game_punt_return_yards is not None:
            punt_return_yards += game_punt_return_yards

        if game_punt_return_touchdowns is not None:
            punt_return_touchdowns += game_punt_return_touchdowns

        if game_long_punt_return is not None:
            long_punt_return = max(
                long_punt_return or game_long_punt_return,
                game_long_punt_return
            )

        if game_field_goals:
            made, attempted = game_field_goals.split("/")
            field_goals_made += int(made)
            field_goal_attempts += int(attempted)

        if game_long_field_goal is not None:
            long_field_goal_made = max(
                long_field_goal_made or game_long_field_goal,
                game_long_field_goal
            )

        if game_extra_points:
            made, attempted = game_extra_points.split("/")
            extra_points_made += int(made)
            extra_point_attempts += int(attempted)

        if game_total_kicking_points is not None:
            total_kicking_points += game_total_kicking_points

        if game_punts is not None:
            punts += game_punts

        if game_punt_yards is not None:
            punt_yards += game_punt_yards

        if game_touchbacks is not None:
            touchbacks += game_touchbacks

        if game_punts_inside_20 is not None:
            punts_inside_20 += game_punts_inside_20

        if game_long_punt is not None:
            long_punt = max(
                long_punt or game_long_punt,
                game_long_punt
            )

    return {
        "games_played": len(rows),

        "kick_returns": kick_returns,
        "kick_return_yards": kick_return_yards,
        "yards_per_kick_return": (
            kick_return_yards / kick_returns
            if kick_returns
            else 0
        ),
        "long_kick_return": long_kick_return,
        "kick_return_touchdowns": kick_return_touchdowns,

        "punt_returns": punt_returns,
        "punt_return_yards": punt_return_yards,
        "yards_per_punt_return": (
            punt_return_yards / punt_returns
            if punt_returns
            else 0
        ),
        "long_punt_return": long_punt_return,
        "punt_return_touchdowns": punt_return_touchdowns,

        "field_goals_made": field_goals_made,
        "field_goal_attempts": field_goal_attempts,
        "field_goal_pct": (
            field_goals_made / field_goal_attempts
            if field_goal_attempts
            else 0
        ),
        "long_field_goal_made": long_field_goal_made,

        "extra_points_made": extra_points_made,
        "extra_point_attempts": extra_point_attempts,
        "total_kicking_points": total_kicking_points,

        "punts": punts,
        "punt_yards": punt_yards,
        "gross_avg_punt_yards": (
            punt_yards / punts
            if punts
            else 0
        ),
        "touchbacks": touchbacks,
        "punts_inside_20": punts_inside_20,
        "long_punt": long_punt
    }

def get_special_teams_profiles(
    cursor,
    player_ids,
    season,
    game_date
):
    if not player_ids:
        return {}

    cursor.execute(
        """
        SELECT
            p.player_id,
            p.kick_returns,
            p.kick_return_yards,
            p.yards_per_kick_return,
            p.long_kick_return,
            p.kick_return_touchdowns,
            p.punt_returns,
            p.punt_return_yards,
            p.yards_per_punt_return,
            p.long_punt_return,
            p.punt_return_touchdowns,
            p.field_goals_made_attempted,
            p.field_goal_pct,
            p.long_field_goal_made,
            p.extra_points_made_attempted,
            p.total_kicking_points,
            p.punts,
            p.punt_yards,
            p.gross_avg_punt_yards,
            p.touchbacks,
            p.punts_inside_20,
            p.long_punt
        FROM nfl_player_game_stats p
        JOIN nfl_games g
            ON p.game_id = g.game_id
        WHERE p.player_id = ANY(%s)
          AND g.season = %s
          AND g.completed = TRUE
          AND g.game_date < %s
        ORDER BY p.player_id, g.game_date;
        """,
        (player_ids, season, game_date)
    )

    grouped_rows = {}

    for row in cursor.fetchall():
        grouped_rows.setdefault(
            row[0],
            []
        ).append(row[1:])

    profiles = {}

    for player_id in player_ids:
        rows = grouped_rows.get(player_id, [])

        if not rows:
            profiles[player_id] = None
            continue

        kick_returns = 0
        kick_return_yards = 0
        kick_return_touchdowns = 0
        long_kick_return = None

        punt_returns = 0
        punt_return_yards = 0
        punt_return_touchdowns = 0
        long_punt_return = None

        field_goals_made = 0
        field_goal_attempts = 0
        long_field_goal_made = None

        extra_points_made = 0
        extra_point_attempts = 0
        total_kicking_points = 0

        punts = 0
        punt_yards = 0
        touchbacks = 0
        punts_inside_20 = 0
        long_punt = None

        for (
            game_kick_returns,
            game_kick_return_yards,
            game_yards_per_kick_return,
            game_long_kick_return,
            game_kick_return_touchdowns,
            game_punt_returns,
            game_punt_return_yards,
            game_yards_per_punt_return,
            game_long_punt_return,
            game_punt_return_touchdowns,
            game_field_goals,
            game_field_goal_pct,
            game_long_field_goal,
            game_extra_points,
            game_total_kicking_points,
            game_punts,
            game_punt_yards,
            game_gross_avg_punt_yards,
            game_touchbacks,
            game_punts_inside_20,
            game_long_punt
        ) in rows:

            if game_kick_returns is not None:
                kick_returns += game_kick_returns

            if game_kick_return_yards is not None:
                kick_return_yards += game_kick_return_yards

            if game_kick_return_touchdowns is not None:
                kick_return_touchdowns += (
                    game_kick_return_touchdowns
                )

            if game_long_kick_return is not None:
                long_kick_return = max(
                    long_kick_return or game_long_kick_return,
                    game_long_kick_return
                )

            if game_punt_returns is not None:
                punt_returns += game_punt_returns

            if game_punt_return_yards is not None:
                punt_return_yards += game_punt_return_yards

            if game_punt_return_touchdowns is not None:
                punt_return_touchdowns += (
                    game_punt_return_touchdowns
                )

            if game_long_punt_return is not None:
                long_punt_return = max(
                    long_punt_return or game_long_punt_return,
                    game_long_punt_return
                )

            if game_field_goals:
                made, attempted = game_field_goals.split("/")
                field_goals_made += int(made)
                field_goal_attempts += int(attempted)

            if game_long_field_goal is not None:
                long_field_goal_made = max(
                    long_field_goal_made
                    or game_long_field_goal,
                    game_long_field_goal
                )

            if game_extra_points:
                made, attempted = game_extra_points.split("/")
                extra_points_made += int(made)
                extra_point_attempts += int(attempted)

            if game_total_kicking_points is not None:
                total_kicking_points += game_total_kicking_points

            if game_punts is not None:
                punts += game_punts

            if game_punt_yards is not None:
                punt_yards += game_punt_yards

            if game_touchbacks is not None:
                touchbacks += game_touchbacks

            if game_punts_inside_20 is not None:
                punts_inside_20 += game_punts_inside_20

            if game_long_punt is not None:
                long_punt = max(
                    long_punt or game_long_punt,
                    game_long_punt
                )

        profiles[player_id] = {
            "games_played": len(rows),

            "kick_returns": kick_returns,
            "kick_return_yards": kick_return_yards,
            "yards_per_kick_return": (
                kick_return_yards / kick_returns
                if kick_returns
                else 0
            ),
            "long_kick_return": long_kick_return,
            "kick_return_touchdowns": kick_return_touchdowns,

            "punt_returns": punt_returns,
            "punt_return_yards": punt_return_yards,
            "yards_per_punt_return": (
                punt_return_yards / punt_returns
                if punt_returns
                else 0
            ),
            "long_punt_return": long_punt_return,
            "punt_return_touchdowns": punt_return_touchdowns,

            "field_goals_made": field_goals_made,
            "field_goal_attempts": field_goal_attempts,
            "field_goal_pct": (
                field_goals_made / field_goal_attempts
                if field_goal_attempts
                else 0
            ),
            "long_field_goal_made": long_field_goal_made,

            "extra_points_made": extra_points_made,
            "extra_point_attempts": extra_point_attempts,
            "total_kicking_points": total_kicking_points,

            "punts": punts,
            "punt_yards": punt_yards,
            "gross_avg_punt_yards": (
                punt_yards / punts
                if punts
                else 0
            ),
            "touchbacks": touchbacks,
            "punts_inside_20": punts_inside_20,
            "long_punt": long_punt
        }

    return profiles


def get_depth_players(
    cursor,
    team_id,
    position_group
):
    cursor.execute(
        """
        SELECT
            d.position_slot,
            d.position,
            d.player_id,
            d.player_name,
            p.jersey,
            p.status,
            p.headshot,
            d.depth_order
        FROM nfl_depth_chart d
        LEFT JOIN nfl_players p
            ON d.player_id = p.player_id
        WHERE d.team_id = %s
          AND d.position_group = %s
          AND d.depth_order > 1
        ORDER BY
            d.position_slot,
            d.depth_order;
        """,
        (team_id, position_group)
    )

    return cursor.fetchall()

def get_depth_players_bulk(
    cursor,
    team_ids
):
    if not team_ids:
        return {}

    cursor.execute(
        """
        SELECT
            d.team_id,
            d.position_group,
            d.position_slot,
            d.position,
            d.player_id,
            d.player_name,
            p.jersey,
            p.status,
            p.headshot,
            d.depth_order
        FROM nfl_depth_chart d
        LEFT JOIN nfl_players p
            ON d.player_id = p.player_id
        WHERE d.team_id = ANY(%s)
          AND d.position_group IN ('OFF', 'DEF', 'ST')
          AND d.depth_order > 1
        ORDER BY
            d.team_id,
            d.position_group,
            d.position_slot,
            d.depth_order;
        """,
        (team_ids,)
    )

    depth_map = {}

    for row in cursor.fetchall():
        team_id = row[0]
        position_group = row[1]

        player = row[2:]

        depth_map.setdefault(
            (team_id, position_group),
            []
        ).append(player)

    return depth_map


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


def get_game_team_stats(
    cursor,
    game_id,
    team_id
):
    cursor.execute(
        """
        SELECT
            total_yards,
            passing_yards,
            rushing_yards,
            yards_per_play,
            first_downs,
            turnovers,
            third_down_eff,
            red_zone_eff,
            possession_time
        FROM nfl_team_game_stats
        WHERE game_id = %s
          AND team_id = %s;
        """,
        (game_id, team_id)
    )

    row = cursor.fetchone()

    if not row:
        return None

    return {
        "total_yards": row[0],
        "passing_yards": row[1],
        "rushing_yards": row[2],
        "yards_per_play": float(row[3]) if row[3] is not None else None,
        "first_downs": row[4],
        "turnovers": row[5],
        "third_down_eff": row[6],
        "red_zone_eff": row[7],
        "possession_time": row[8]
    }


def get_game_player_stats(
    cursor,
    game_id,
    team_id
):
    cursor.execute(
        """
        SELECT
            player_id,
            player_name,
            jersey,

            completions_attempts,
            passing_yards,
            yards_per_pass_attempt,
            passing_touchdowns,
            passing_interceptions,
            sacks_sack_yards_lost,
            qbr,
            passer_rating,

            rushing_attempts,
            rushing_yards,
            yards_per_rush_attempt,
            rushing_touchdowns,
            long_rushing,

            receptions,
            receiving_targets,
            receiving_yards,
            yards_per_reception,
            receiving_touchdowns,
            long_reception,

            fumbles,
            fumbles_lost,

            total_tackles,
            solo_tackles,
            sacks,
            tackles_for_loss,
            passes_defended,
            qb_hits,
            defensive_touchdowns,
            defensive_interceptions,
            interception_yards,
            interception_touchdowns,
            fumbles_recovered,

            kick_returns,
            kick_return_yards,
            yards_per_kick_return,
            long_kick_return,
            kick_return_touchdowns,

            punt_returns,
            punt_return_yards,
            yards_per_punt_return,
            long_punt_return,
            punt_return_touchdowns,

            field_goals_made_attempted,
            field_goal_pct,
            long_field_goal_made,
            extra_points_made_attempted,
            total_kicking_points,

            punts,
            punt_yards,
            gross_avg_punt_yards,
            touchbacks,
            punts_inside_20,
            long_punt

        FROM nfl_player_game_stats

        WHERE game_id = %s
          AND team_id = %s

        ORDER BY player_name;
        """,
        (game_id, team_id)
    )

    rows = cursor.fetchall()

    columns = [
        desc[0]
        for desc in cursor.description
    ]

    return [
        dict(zip(columns, row))
        for row in rows
    ]


def get_game_injuries(
    cursor,
    game_id,
    team_id
):
    cursor.execute(
        """
        SELECT snapshot_id
        FROM nfl_injury_snapshots
        WHERE game_id = %s
          AND team_id = %s
        ORDER BY captured_at DESC
        LIMIT 1;
        """,
        (game_id, team_id)
    )

    snapshot_row = cursor.fetchone()

    if not snapshot_row:
        return []

    snapshot_id = snapshot_row[0]

    cursor.execute(
        """
        SELECT
            player_id,
            player_name,
            jersey,
            position,
            headshot,
            status,
            injury_type,
            injury_location,
            injury_detail,
            injury_side,
            injury_date,
            return_date
        FROM nfl_injuries
        WHERE snapshot_id = %s
        ORDER BY
            CASE
                WHEN status = 'Out' THEN 1
                WHEN status = 'Injured Reserve' THEN 2
                WHEN status = 'Doubtful' THEN 3
                WHEN status = 'Questionable' THEN 4
                ELSE 5
            END,
            player_name;
        """,
        (snapshot_id,)
    )

    rows = cursor.fetchall()

    return [
        {
            "player_id": row[0],
            "player_name": row[1],
            "jersey": row[2],
            "position": row[3],
            "headshot": row[4],
            "status": row[5],
            "injury_type": row[6],
            "injury_location": row[7],
            "injury_detail": row[8],
            "injury_side": row[9],
            "injury_date": row[10],
            "return_date": row[11]
        }
        for row in rows
    ]


def get_injury_changes(
    cursor,
    game_id,
    team_id
):
    cursor.execute(
        """
        SELECT
            snapshot_id,
            captured_at
        FROM nfl_injury_snapshots
        WHERE game_id = %s
          AND team_id = %s
        ORDER BY captured_at DESC
        LIMIT 2;
        """,
        (game_id, team_id)
    )

    snapshots = cursor.fetchall()

    if len(snapshots) < 2:
        return []

    latest_snapshot_id = snapshots[0][0]
    previous_snapshot_id = snapshots[1][0]

    cursor.execute(
        """
        SELECT
            player_id,
            player_name,
            status,
            injury_type
        FROM nfl_injuries
        WHERE snapshot_id = %s;
        """,
        (latest_snapshot_id,)
    )

    latest_rows = cursor.fetchall()

    cursor.execute(
        """
        SELECT
            player_id,
            player_name,
            status,
            injury_type
        FROM nfl_injuries
        WHERE snapshot_id = %s;
        """,
        (previous_snapshot_id,)
    )

    previous_rows = cursor.fetchall()

    latest_map = {
        row[0]: {
            "player_name": row[1],
            "status": row[2],
            "injury_type": row[3]
        }
        for row in latest_rows
    }

    previous_map = {
        row[0]: {
            "player_name": row[1],
            "status": row[2],
            "injury_type": row[3]
        }
        for row in previous_rows
    }

    changes = []

    all_player_ids = (
        set(latest_map.keys())
        | set(previous_map.keys())
    )

    for player_id in all_player_ids:

        latest = latest_map.get(player_id)
        previous = previous_map.get(player_id)

        if previous and not latest:
            changes.append(
                {
                    "player_id": player_id,
                    "player_name": previous["player_name"],
                    "change_type": "removed",
                    "old_status": previous["status"],
                    "new_status": None,
                    "injury_type": previous["injury_type"]
                }
            )

        elif latest and not previous:
            changes.append(
                {
                    "player_id": player_id,
                    "player_name": latest["player_name"],
                    "change_type": "added",
                    "old_status": None,
                    "new_status": latest["status"],
                    "injury_type": latest["injury_type"]
                }
            )

        elif latest["status"] != previous["status"]:
            changes.append(
                {
                    "player_id": player_id,
                    "player_name": latest["player_name"],
                    "change_type": "status_change",
                    "old_status": previous["status"],
                    "new_status": latest["status"],
                    "injury_type": latest["injury_type"]
                }
            )

    return changes


def get_latest_injury_snapshot_time(
    cursor,
    game_id,
    team_id
):
    cursor.execute(
        """
        SELECT captured_at
        FROM nfl_injury_snapshots
        WHERE game_id = %s
          AND team_id = %s
        ORDER BY captured_at DESC
        LIMIT 1;
        """,
        (game_id, team_id)
    )

    row = cursor.fetchone()

    return row[0] if row else None


def get_game_weather(
    cursor,
    game_id
):
    cursor.execute(
        """
        SELECT
            forecast_time,
            temperature_f,
            apparent_temperature_f,
            precipitation_probability,
            precipitation_inches,
            relative_humidity,
            wind_speed_mph,
            wind_gust_mph,
            wind_direction_degrees,
            weather_code,
            captured_at
        FROM nfl_weather_snapshots
        WHERE game_id = %s
        ORDER BY captured_at DESC
        LIMIT 1;
        """,
        (game_id,)
    )

    row = cursor.fetchone()

    if not row:
        return None

    return {
        "forecast_time": row[0],
        "temperature_f": row[1],
        "apparent_temperature_f": row[2],
        "precipitation_probability": row[3],
        "precipitation_inches": row[4],
        "relative_humidity": row[5],
        "wind_speed_mph": row[6],
        "wind_gust_mph": row[7],
        "wind_direction_degrees": row[8],
        "weather_code": row[9],
        "captured_at": row[10]
    }


def get_latest_betting_snapshot(
    cursor,
    game_id
):
    cursor.execute(
        """
        SELECT
            provider_name,
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
        FROM nfl_betting_snapshots
        WHERE game_id = %s
        ORDER BY captured_at DESC
        LIMIT 1;
        """,
        (game_id,)
    )

    row = cursor.fetchone()

    if not row:
        return None

    return {
        "provider_name": row[0],
        "away_moneyline": row[1],
        "home_moneyline": row[2],
        "away_spread": row[3],
        "home_spread": row[4],
        "away_spread_odds": row[5],
        "home_spread_odds": row[6],
        "total": row[7],
        "over_odds": row[8],
        "under_odds": row[9],
        "opening_away_moneyline": row[10],
        "opening_home_moneyline": row[11],
        "opening_away_spread": row[12],
        "opening_home_spread": row[13],
        "opening_total": row[14],
        "captured_at": row[15]
    }


def get_team_record_before_date(
    cursor,
    team_id,
    season,
    cutoff_date
):
    cursor.execute(
        """
        SELECT
            home_team_id,
            home_score,
            away_team_id,
            away_score
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
        (
            season,
            cutoff_date,
            team_id,
            team_id
        )
    )

    games = cursor.fetchall()

    wins = 0
    losses = 0
    ties = 0

    for (
        home_team_id,
        home_score,
        away_team_id,
        away_score
    ) in games:

        if home_score == away_score:
            ties += 1

        elif home_team_id == team_id:
            if home_score > away_score:
                wins += 1
            else:
                losses += 1

        else:
            if away_score > home_score:
                wins += 1
            else:
                losses += 1

    if ties:
        return f"{wins}-{losses}-{ties}"

    return f"{wins}-{losses}"

def get_league_records_before_date(
    cursor,
    season,
    cutoff_date
):
    cursor.execute(
        """
        SELECT
            team_id,
            SUM(wins) AS wins,
            SUM(losses) AS losses,
            SUM(ties) AS ties
        FROM (
            SELECT
                home_team_id AS team_id,
                CASE
                    WHEN home_score > away_score THEN 1
                    ELSE 0
                END AS wins,
                CASE
                    WHEN home_score < away_score THEN 1
                    ELSE 0
                END AS losses,
                CASE
                    WHEN home_score = away_score THEN 1
                    ELSE 0
                END AS ties
            FROM nfl_games
            WHERE season = %s
              AND completed = TRUE
              AND game_date < %s

            UNION ALL

            SELECT
                away_team_id AS team_id,
                CASE
                    WHEN away_score > home_score THEN 1
                    ELSE 0
                END AS wins,
                CASE
                    WHEN away_score < home_score THEN 1
                    ELSE 0
                END AS losses,
                CASE
                    WHEN away_score = home_score THEN 1
                    ELSE 0
                END AS ties
            FROM nfl_games
            WHERE season = %s
              AND completed = TRUE
              AND game_date < %s
        ) results
        WHERE team_id IS NOT NULL
        GROUP BY team_id;
        """,
        (
            season,
            cutoff_date,
            season,
            cutoff_date,
        )
    )

    records = {}

    for team_id, wins, losses, ties in cursor.fetchall():
        if ties:
            records[team_id] = (
                f"{wins}-{losses}-{ties}"
            )
        else:
            records[team_id] = (
                f"{wins}-{losses}"
            )

    return records


def get_league_power_rankings(
    cursor,
    season,
    cutoff_date
):
    cursor.execute(
        """
        WITH teams AS (
            SELECT
                home_team_id AS team_id,
                home_team AS team_name
            FROM nfl_games
            WHERE season = %s

            UNION

            SELECT
                away_team_id AS team_id,
                away_team AS team_name
            FROM nfl_games
            WHERE season = %s
        ),

        scoring_games AS (
            SELECT
                home_team_id AS team_id,
                home_score AS points_for,
                away_score AS points_against
            FROM nfl_games
            WHERE season = %s
              AND completed = TRUE
              AND game_date < %s

            UNION ALL

            SELECT
                away_team_id AS team_id,
                away_score AS points_for,
                home_score AS points_against
            FROM nfl_games
            WHERE season = %s
              AND completed = TRUE
              AND game_date < %s
        ),

        scoring AS (
            SELECT
                team_id,
                AVG(
                    points_for - points_against
                )::FLOAT AS scoring_margin
            FROM scoring_games
            GROUP BY team_id
        ),

        offense AS (
            SELECT
                s.team_id,

                AVG(
                    s.yards_per_play
                )::FLOAT AS yards_per_play,

                AVG(
                    s.turnovers
                )::FLOAT AS turnovers_per_game,

                (
                    SUM(
                        SPLIT_PART(
                            s.third_down_eff,
                            '-',
                            1
                        )::NUMERIC
                    )
                    /
                    NULLIF(
                        SUM(
                            SPLIT_PART(
                                s.third_down_eff,
                                '-',
                                2
                            )::NUMERIC
                        ),
                        0
                    )
                )::FLOAT AS third_down_pct,

                (
                    SUM(
                        SPLIT_PART(
                            s.red_zone_eff,
                            '-',
                            1
                        )::NUMERIC
                    )
                    /
                    NULLIF(
                        SUM(
                            SPLIT_PART(
                                s.red_zone_eff,
                                '-',
                                2
                            )::NUMERIC
                        ),
                        0
                    )
                )::FLOAT AS red_zone_pct

            FROM nfl_team_game_stats s

            JOIN nfl_games g
                ON s.game_id = g.game_id

            WHERE g.season = %s
              AND g.completed = TRUE
              AND g.game_date < %s

            GROUP BY s.team_id
        ),

        defense AS (
            SELECT
                team.team_id,

                AVG(
                    opponent.yards_per_play
                )::FLOAT AS yards_per_play_allowed,

                AVG(
                    opponent.turnovers
                )::FLOAT AS takeaways_per_game,

                (
                    SUM(
                        SPLIT_PART(
                            opponent.third_down_eff,
                            '-',
                            1
                        )::NUMERIC
                    )
                    /
                    NULLIF(
                        SUM(
                            SPLIT_PART(
                                opponent.third_down_eff,
                                '-',
                                2
                            )::NUMERIC
                        ),
                        0
                    )
                )::FLOAT AS opponent_third_down_pct,

                (
                    SUM(
                        SPLIT_PART(
                            opponent.red_zone_eff,
                            '-',
                            1
                        )::NUMERIC
                    )
                    /
                    NULLIF(
                        SUM(
                            SPLIT_PART(
                                opponent.red_zone_eff,
                                '-',
                                2
                            )::NUMERIC
                        ),
                        0
                    )
                )::FLOAT AS opponent_red_zone_pct

            FROM nfl_team_game_stats team

            JOIN nfl_games g
                ON team.game_id = g.game_id

            JOIN nfl_team_game_stats opponent
                ON team.game_id = opponent.game_id
                AND team.team_id <> opponent.team_id

            WHERE g.season = %s
              AND g.completed = TRUE
              AND g.game_date < %s

            GROUP BY team.team_id
        )

        SELECT
            teams.team_id,
            teams.team_name,
            scoring.scoring_margin,
            offense.yards_per_play,
            offense.turnovers_per_game,
            offense.third_down_pct,
            offense.red_zone_pct,
            defense.yards_per_play_allowed,
            defense.takeaways_per_game,
            defense.opponent_third_down_pct,
            defense.opponent_red_zone_pct

        FROM teams

        LEFT JOIN scoring
            ON teams.team_id = scoring.team_id

        LEFT JOIN offense
            ON teams.team_id = offense.team_id

        LEFT JOIN defense
            ON teams.team_id = defense.team_id

        WHERE teams.team_id IS NOT NULL

        ORDER BY teams.team_name;
        """,
        (
            season,
            season,

            season,
            cutoff_date,
            season,
            cutoff_date,

            season,
            cutoff_date,

            season,
            cutoff_date,
        )
    )

    rows = cursor.fetchall()

    rankings = []

    for (
        team_id,
        team_name,
        scoring_margin,
        yards_per_play,
        turnovers_per_game,
        third_down_pct,
        red_zone_pct,
        yards_per_play_allowed,
        takeaways_per_game,
        opponent_third_down_pct,
        opponent_red_zone_pct,
    ) in rows:

        required_values = (
            scoring_margin,
            yards_per_play,
            turnovers_per_game,
            third_down_pct,
            red_zone_pct,
            yards_per_play_allowed,
            takeaways_per_game,
            opponent_third_down_pct,
            opponent_red_zone_pct,
        )

        if any(
            value is None
            for value in required_values
        ):
            continue

        scoring = {
            "scoring_margin": scoring_margin
        }

        offense = {
            "yards_per_play": yards_per_play,
            "turnovers_per_game": turnovers_per_game,
            "third_down_pct": third_down_pct,
            "red_zone_pct": red_zone_pct,
        }

        defense = {
            "yards_per_play_allowed": (
                yards_per_play_allowed
            ),
            "takeaways_per_game": (
                takeaways_per_game
            ),
            "opponent_third_down_pct": (
                opponent_third_down_pct
            ),
            "opponent_red_zone_pct": (
                opponent_red_zone_pct
            ),
        }

        power = get_team_power_rating(
            scoring,
            offense,
            defense
        )

        if power is not None:
            rankings.append(
                {
                    "team_id": team_id,
                    "team": team_name,
                    "rating": power["rating"],
                }
            )

    rankings.sort(
        key=lambda team: team["rating"],
        reverse=True
    )

    for index, team in enumerate(
        rankings,
        start=1
    ):
        team["rank"] = index

    return rankings
