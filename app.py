import streamlit as st
import psycopg2
import pandas as pd
import math
from zoneinfo import ZoneInfo

from analytics import (
    get_skill_player_score,
    get_defensive_impact_score,
    get_key_player_spotlights,
    get_matchup_comparison,
    get_matchup_advantages,
    classify_matchup_edge,
    get_matchup_edges,
    get_matchup_prediction_adjustment,
    american_odds_to_probability,
    remove_vig,
    get_team_power_rating,
    get_raw_prediction_edge,
    get_recent_form_adjustment,
    get_v2_win_probability,
    get_season_blend_weights,
    blend_profile,
    get_prediction_confidence,
)

DISPLAY_SEASON = 2026

TEAM_ABBREVIATIONS = {
    "Arizona Cardinals": "ARI",
    "Atlanta Falcons": "ATL",
    "Baltimore Ravens": "BAL",
    "Buffalo Bills": "BUF",
    "Carolina Panthers": "CAR",
    "Chicago Bears": "CHI",
    "Cincinnati Bengals": "CIN",
    "Cleveland Browns": "CLE",
    "Dallas Cowboys": "DAL",
    "Denver Broncos": "DEN",
    "Detroit Lions": "DET",
    "Green Bay Packers": "GB",
    "Houston Texans": "HOU",
    "Indianapolis Colts": "IND",
    "Jacksonville Jaguars": "JAX",
    "Kansas City Chiefs": "KC",
    "Las Vegas Raiders": "LV",
    "Los Angeles Chargers": "LAC",
    "Los Angeles Rams": "LAR",
    "Miami Dolphins": "MIA",
    "Minnesota Vikings": "MIN",
    "New England Patriots": "NE",
    "New Orleans Saints": "NO",
    "New York Giants": "NYG",
    "New York Jets": "NYJ",
    "Philadelphia Eagles": "PHI",
    "Pittsburgh Steelers": "PIT",
    "San Francisco 49ers": "SF",
    "Seattle Seahawks": "SEA",
    "Tampa Bay Buccaneers": "TB",
    "Tennessee Titans": "TEN",
    "Washington Commanders": "WAS"
}

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




def render_offensive_player(
    starter,
    qb_profile,
    qb_player_id,
    rb_profile,
    rb_player_id,
    receiver_profile_map
):
    (
        position_slot,
        position,
        player_id,
        player_name,
        jersey,
        status,
        headshot
    ) = starter

    st.markdown(f"**{player_name}**")

    if jersey:
        st.caption(f"#{jersey} · {position}")

    if status and status != "Active":
        st.write(f"Status: {status}")

    # -------------------------
    # QUARTERBACK
    # -------------------------

    if (
        position == "QB"
        and player_id == qb_player_id
        and qb_profile
    ):
        st.write(
            f"{qb_profile['completions']}/"
            f"{qb_profile['attempts']} "
            f"({qb_profile['completion_pct'] * 100:.1f}%)"
        )

        st.write(
            f"{qb_profile['passing_yards']} Pass YDS · "
            f"{qb_profile['passing_touchdowns']} TD · "
            f"{qb_profile['interceptions']} INT"
        )

        st.write(
            f"{qb_profile['passing_yards_per_game']:.1f} YDS/G · "
            f"{qb_profile['yards_per_attempt']:.1f} Y/A"
        )

        if qb_profile["average_qbr"] is not None:
            st.write(
                f"Avg. Game QBR: "
                f"{qb_profile['average_qbr']:.1f}"
            )

        if qb_profile["average_passer_rating"] is not None:
            st.write(
                f"Avg. Game Passer Rating: "
                f"{qb_profile['average_passer_rating']:.1f}"
            )

        if (
            qb_profile["rushing_attempts"] > 0
            or qb_profile["rushing_yards"] != 0
        ):
            st.write(
                f"Rushing: "
                f"{qb_profile['rushing_yards']} YDS · "
                f"{qb_profile['rushing_touchdowns']} TD"
            )

    # -------------------------
    # RUNNING BACK
    # -------------------------

    elif (
        position == "RB"
        and player_id == rb_player_id
        and rb_profile
    ):
        st.write(
            f"{rb_profile['rushing_attempts']} CAR · "
            f"{rb_profile['rushing_yards']} YDS · "
            f"{rb_profile['rushing_touchdowns']} TD"
        )

        st.write(
            f"{rb_profile['rushing_yards_per_game']:.1f} YDS/G · "
            f"{rb_profile['yards_per_carry']:.1f} Y/C"
        )

        st.write(
            f"{rb_profile['receptions']} REC · "
            f"{rb_profile['receiving_targets']} TGT · "
            f"{rb_profile['receiving_yards']} REC YDS · "
            f"{rb_profile['receiving_touchdowns']} REC TD"
        )

        st.write(
            f"{rb_profile['scrimmage_yards']} Scrimmage YDS · "
            f"{rb_profile['total_touchdowns']} Total TD"
        )

    # -------------------------
    # RECEIVERS
    # -------------------------

    elif position in ("WR", "TE"):
        profile = receiver_profile_map.get(player_id)

        if profile:
            st.write(
                f"{profile['receptions']} REC · "
                f"{profile['targets']} TGT · "
                f"{profile['receiving_yards']} YDS · "
                f"{profile['receiving_touchdowns']} TD"
            )

            st.write(
                f"{profile['catch_pct'] * 100:.1f}% Catch · "
                f"{profile['yards_per_reception']:.1f} Y/REC · "
                f"{profile['receiving_yards_per_game']:.1f} YDS/G"
            )

            if profile["rushing_attempts"] > 0:
                st.write(
                    f"Rushing: "
                    f"{profile['rushing_attempts']} CAR · "
                    f"{profile['rushing_yards']} YDS · "
                    f"{profile['rushing_touchdowns']} TD"
                )

def render_defensive_player(
    starter,
    defensive_profile_map
):
    (
        position_slot,
        position,
        player_id,
        player_name,
        jersey,
        status,
        headshot
    ) = starter

    st.markdown(f"**{player_name}**")

    if jersey:
        st.caption(f"#{jersey} · {position}")

    if status and status != "Active":
        st.write(f"Status: {status}")

    profile = defensive_profile_map.get(player_id)

    if not profile:
        return

    st.write(
        f"{profile['total_tackles']} TKL · "
        f"{profile['solo_tackles']} SOLO · "
        f"{profile['sacks']:.1f} SACK"
    )

    st.write(
        f"{profile['tackles_for_loss']:.1f} TFL · "
        f"{profile['qb_hits']} QB HIT · "
        f"{profile['passes_defended']} PD"
    )

    if (
        profile["interceptions"] > 0
        or profile["fumbles_recovered"] > 0
    ):
        st.write(
            f"{profile['interceptions']} INT · "
            f"{profile['interception_yards']} INT YDS · "
            f"{profile['fumbles_recovered']} FR"
        )

    if (
        profile["interception_touchdowns"] > 0
        or profile["defensive_touchdowns"] > 0
    ):
        st.write(
            f"{profile['interception_touchdowns']} INT TD · "
            f"{profile['defensive_touchdowns']} DEF TD"
        )

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

def render_special_teams_player(
    starter,
    profile_map
):
    (
        position_slot,
        position,
        player_id,
        player_name,
        jersey,
        status,
        headshot
    ) = starter

    st.markdown(f"**{player_name}**")

    if jersey:
        st.caption(f"#{jersey} · {position}")

    if status and status != "Active":
        st.write(f"Status: {status}")

    profile = profile_map.get(player_id)

    if not profile:
        return

    # -------------------------
    # KICKER
    # -------------------------

    if position_slot == "pk":
        st.write(
            f"{profile['field_goals_made']}/"
            f"{profile['field_goal_attempts']} FG · "
            f"{profile['field_goal_pct'] * 100:.1f}%"
        )

        st.write(
            f"Long: "
            f"{profile['long_field_goal_made'] if profile['long_field_goal_made'] is not None else 'N/A'} · "
            f"{profile['extra_points_made']}/"
            f"{profile['extra_point_attempts']} XP · "
            f"{profile['total_kicking_points']} PTS"
        )

    # -------------------------
    # PUNTER
    # -------------------------

    elif position_slot == "p":
        st.write(
            f"{profile['punts']} PUNTS · "
            f"{profile['punt_yards']} YDS · "
            f"{profile['gross_avg_punt_yards']:.1f} AVG"
        )

        st.write(
            f"{profile['punts_inside_20']} IN20 · "
            f"{profile['touchbacks']} TB · "
            f"Long: "
            f"{profile['long_punt'] if profile['long_punt'] is not None else 'N/A'}"
        )

    # -------------------------
    # KICK RETURNER
    # -------------------------

    elif position_slot == "kr":
        st.write(
            f"{profile['kick_returns']} KR · "
            f"{profile['kick_return_yards']} YDS · "
            f"{profile['yards_per_kick_return']:.1f} AVG"
        )

        st.write(
            f"Long: "
            f"{profile['long_kick_return'] if profile['long_kick_return'] is not None else 'N/A'} · "
            f"{profile['kick_return_touchdowns']} TD"
        )

    # -------------------------
    # PUNT RETURNER
    # -------------------------

    elif position_slot == "pr":
        st.write(
            f"{profile['punt_returns']} PR · "
            f"{profile['punt_return_yards']} YDS · "
            f"{profile['yards_per_punt_return']:.1f} AVG"
        )

        st.write(
            f"Long: "
            f"{profile['long_punt_return'] if profile['long_punt_return'] is not None else 'N/A'} · "
            f"{profile['punt_return_touchdowns']} TD"
        )

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

def build_depth_map(players):
    return {
        (player[0], player[7]): player
        for player in players
    }


def get_matchup_depth_rows(
    away_players,
    home_players,
    display_order
):
    away_map = build_depth_map(away_players)
    home_map = build_depth_map(home_players)

    all_keys = set(away_map) | set(home_map)

    order_index = {
        slot: index
        for index, slot in enumerate(display_order)
    }

    rows = sorted(
        all_keys,
        key=lambda key: (
            order_index.get(key[0], 999),
            key[0],
            key[1]
        )
    )

    return away_map, home_map, rows

def render_offensive_depth_player(
    player,
    profile_map
):
    (
        position_slot,
        position,
        player_id,
        player_name,
        jersey,
        status,
        headshot,
        depth_order
    ) = player

    st.markdown(f"**{player_name}**")

    if jersey:
        st.caption(
            f"#{jersey} · {position} · Depth {depth_order}"
        )
    else:
        st.caption(
            f"{position} · Depth {depth_order}"
        )

    if status and status != "Active":
        st.write(f"Status: {status}")

    profile = profile_map.get(player_id)

    if not profile:
        return

    if position == "QB":
        st.write(
            f"{profile['completions']}/"
            f"{profile['attempts']} "
            f"({profile['completion_pct'] * 100:.1f}%)"
        )

        st.write(
            f"{profile['passing_yards']} Pass YDS · "
            f"{profile['passing_touchdowns']} TD · "
            f"{profile['interceptions']} INT"
        )

        st.write(
            f"{profile['passing_yards_per_game']:.1f} YDS/G · "
            f"{profile['yards_per_attempt']:.1f} Y/A"
        )

    elif position == "RB":
        st.write(
            f"{profile['rushing_attempts']} CAR · "
            f"{profile['rushing_yards']} YDS · "
            f"{profile['rushing_touchdowns']} TD"
        )

        st.write(
            f"{profile['rushing_yards_per_game']:.1f} YDS/G · "
            f"{profile['yards_per_carry']:.1f} Y/C"
        )

        st.write(
            f"{profile['receptions']} REC · "
            f"{profile['receiving_targets']} TGT · "
            f"{profile['receiving_yards']} REC YDS"
        )

    elif position in ("WR", "TE"):
        st.write(
            f"{profile['receptions']} REC · "
            f"{profile['targets']} TGT · "
            f"{profile['receiving_yards']} YDS · "
            f"{profile['receiving_touchdowns']} TD"
        )

        st.write(
            f"{profile['catch_pct'] * 100:.1f}% Catch · "
            f"{profile['yards_per_reception']:.1f} Y/REC · "
            f"{profile['receiving_yards_per_game']:.1f} YDS/G"
        )



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




def build_matchup_summary(
    offense_team,
    defense_team,
    edges
):
    if not edges:
        return None

    metric_labels = {
        "total_yards": "total yardage",
        "passing_yards": "passing",
        "rushing_yards": "rushing",
        "yards_per_play": "yards per play",
        "third_down": "third down",
        "red_zone": "red zone",
        "turnovers": "turnovers"
    }

    offense_edges = [
        metric_labels.get(metric, metric)
        for metric, result in edges.items()
        if result == "Offense edge"
    ]

    defense_edges = [
        metric_labels.get(metric, metric)
        for metric, result in edges.items()
        if result == "Defense edge"
    ]

    strength_vs_strength = [
        metric_labels.get(metric, metric)
        for metric, result in edges.items()
        if result == "Strength vs strength"
    ]

    weakness_vs_weakness = [
        metric_labels.get(metric, metric)
        for metric, result in edges.items()
        if result == "Weakness vs weakness"
    ]

    if len(offense_edges) > len(defense_edges):
        summary = (
            f"{possessive(offense_team)} offense holds the broader matchup edge."
        )

    elif len(defense_edges) > len(offense_edges):
        summary = (
            f"{possessive(defense_team)} defense holds the broader matchup edge."
        )

    else:
        summary = (
            "The matchup is relatively balanced across the major categories."
        )

    if strength_vs_strength:
        summary += (
            f" Strength vs strength appears in "
            f"{', '.join(strength_vs_strength)}."
        )

    if weakness_vs_weakness:
        summary += (
            f" Both units have struggled in "
            f"{', '.join(weakness_vs_weakness)}."
        )

    return summary

def possessive(name):
    if name.endswith("s"):
        return f"{name}'"

    return f"{name}'s"

def render_matchup_table(
    offense_team,
    defense_team,
    comparison,
    edges
):
    st.markdown(
        f"### {offense_team} Offense vs {defense_team} Defense"
    )

    if not comparison or not edges:
        st.write("No matchup data available yet.")
        return

    st.caption(
        f"{possessive(offense_team)} offensive production compared with "
        f"{possessive(defense_team)} defensive performance entering this game."
        )

    summary = build_matchup_summary(
        offense_team,
        defense_team,
        edges
    )

    if summary:
        st.markdown("#### Key Matchup Read")
        st.write(summary)

    # -------------------------
    # HEADER
    # -------------------------

    metric_col, offense_col, defense_col, read_col = st.columns(
        [1.4, 1, 1, 1.4]
    )

    with metric_col:
        st.markdown("**Metric**")

    with offense_col:
        st.markdown(f"**{offense_team} Offense**")

    with defense_col:
        st.markdown(f"**{defense_team} Defense**")

    with read_col:
        st.markdown("**Matchup Read**")

    st.divider()

    rows = [
        (
            "Total Yards",
            comparison["total_yards"][0],
            comparison["total_yards"][1],
            edges["total_yards"],
            "yards"
        ),
        (
            "Passing",
            comparison["passing_yards"][0],
            comparison["passing_yards"][1],
            edges["passing_yards"],
            "yards"
        ),
        (
            "Rushing",
            comparison["rushing_yards"][0],
            comparison["rushing_yards"][1],
            edges["rushing_yards"],
            "yards"
        ),
        (
            "Yards / Play",
            comparison["yards_per_play"][0],
            comparison["yards_per_play"][1],
            edges["yards_per_play"],
            "decimal"
        ),
        (
            "3rd Down",
            comparison["third_down"][0],
            comparison["third_down"][1],
            edges["third_down"],
            "percent"
        ),
        (
            "Red Zone",
            comparison["red_zone"][0],
            comparison["red_zone"][1],
            edges["red_zone"],
            "percent"
        ),
        (
            "Turnovers / Takeaways",
            comparison["turnovers_takeaways"][0],
            comparison["turnovers_takeaways"][1],
            edges["turnovers"],
            "turnovers"
        )
    ]

    for (
        metric,
        offense_value,
        defense_value,
        matchup_read,
        value_type
    ) in rows:

        metric_col, offense_col, defense_col, read_col = st.columns(
            [1.4, 1, 1, 1.4]
        )

        with metric_col:
            st.write(metric)

        with offense_col:

            if value_type == "percent":
                st.write(f"{offense_value * 100:.1f}%")

            elif value_type == "decimal":
                st.write(f"{offense_value:.2f}")

            elif value_type == "turnovers":
                st.write(f"{offense_value:.2f} TO/G")

            else:
                st.write(f"{offense_value:.1f}")

        with defense_col:

            if value_type == "percent":
                st.write(f"{defense_value * 100:.1f}% allowed")

            elif value_type == "decimal":
                st.write(f"{defense_value:.2f} allowed")

            elif value_type == "turnovers":
                st.write(f"{defense_value:.2f} TAKE/G")

            else:
                st.write(f"{defense_value:.1f} allowed")

        with read_col:
            st.write(matchup_read)

def get_matchup_advantage_summary(
    away_team,
    home_team,
    away_edges,
    home_edges
):
    if not away_edges or not home_edges:
        return None

    metric_labels = {
        "total_yards": "Total Yards",
        "passing_yards": "Passing",
        "rushing_yards": "Rushing",
        "yards_per_play": "Yards / Play",
        "third_down": "Third Down",
        "red_zone": "Red Zone",
        "turnovers": "Turnovers"
    }

    away_advantages = []
    home_advantages = []

    for metric, label in metric_labels.items():

        away_result = away_edges.get(metric)
        home_result = home_edges.get(metric)

        if away_result == "Offense edge":
            away_advantages.append(
                f"{label} — offensive edge"
            )

        elif away_result == "Defense edge":
            home_advantages.append(
                f"{label} — defensive edge"
            )

        if home_result == "Offense edge":
            home_advantages.append(
                f"{label} — offensive edge"
            )

        elif home_result == "Defense edge":
            away_advantages.append(
                f"{label} — defensive edge"
            )

    return {
        "away_team": away_team,
        "home_team": home_team,
        "away_advantages": away_advantages,
        "home_advantages": home_advantages
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

def render_passing_box_score(
    team_name,
    player_stats
):
    passers = [
        player
        for player in player_stats
        if player["completions_attempts"] is not None
    ]

    if not passers:
        return

    st.markdown(f"#### {team_name} Passing")

    header_cols = st.columns([2, 1, 1, 1, 1, 1, 1, 1])

    headers = [
        "Player",
        "C/ATT",
        "YDS",
        "AVG",
        "TD",
        "INT",
        "SACKS",
        "RTG"
    ]

    for col, header in zip(header_cols, headers):
        col.markdown(f"**{header}**")

    for player in passers:

        cols = st.columns([2, 1, 1, 1, 1, 1, 1, 1])

        values = [
            player["player_name"],
            player["completions_attempts"],
            player["passing_yards"],
            player["yards_per_pass_attempt"],
            player["passing_touchdowns"],
            player["passing_interceptions"],
            player["sacks_sack_yards_lost"],
            player["passer_rating"]
        ]

        for index, (col, value) in enumerate(zip(cols, values)):

            if value is None:
                display_value = "—"

            elif index in (3, 7):
                display_value = f"{float(value):.1f}"

            else:
                display_value = str(value)

            col.write(display_value)

def render_rushing_box_score(
    team_name,
    player_stats
):
    rushers = [
        player
        for player in player_stats
        if player["rushing_attempts"] is not None
        and player["rushing_attempts"] > 0
    ]

    if not rushers:
        return

    rushers.sort(
        key=lambda player: player["rushing_attempts"],
        reverse=True
    )

    st.markdown(f"#### {team_name} Rushing")

    header_cols = st.columns([2, 1, 1, 1, 1, 1])

    headers = [
        "Player",
        "CAR",
        "YDS",
        "AVG",
        "TD",
        "LONG"
    ]

    for col, header in zip(header_cols, headers):
        col.markdown(f"**{header}**")

    for player in rushers:

        cols = st.columns([2, 1, 1, 1, 1, 1])

        values = [
            player["player_name"],
            player["rushing_attempts"],
            player["rushing_yards"],
            player["yards_per_rush_attempt"],
            player["rushing_touchdowns"],
            player["long_rushing"]
        ]

        for index, (col, value) in enumerate(zip(cols, values)):

            if value is None:
                display_value = "—"

            elif index == 3:
                display_value = f"{float(value):.1f}"

            else:
                display_value = str(value)

            col.write(display_value)

def render_receiving_box_score(
    team_name,
    player_stats
):
    receivers = [
        player
        for player in player_stats
        if (
            player["receiving_targets"] is not None
            and player["receiving_targets"] > 0
        )
        or (
            player["receptions"] is not None
            and player["receptions"] > 0
        )
    ]

    if not receivers:
        return

    receivers.sort(
        key=lambda player: (
            player["receiving_yards"] or 0,
            player["receptions"] or 0
        ),
        reverse=True
    )

    st.markdown(f"#### {team_name} Receiving")

    header_cols = st.columns(
        [2, 1, 1, 1, 1, 1, 1]
    )

    headers = [
        "Player",
        "REC",
        "TGT",
        "YDS",
        "AVG",
        "TD",
        "LONG"
    ]

    for col, header in zip(header_cols, headers):
        col.markdown(f"**{header}**")

    for player in receivers:

        cols = st.columns(
            [2, 1, 1, 1, 1, 1, 1]
        )

        values = [
            player["player_name"],
            player["receptions"],
            player["receiving_targets"],
            player["receiving_yards"],
            player["yards_per_reception"],
            player["receiving_touchdowns"],
            player["long_reception"]
        ]

        for index, (col, value) in enumerate(
            zip(cols, values)
        ):

            if value is None:
                display_value = "—"

            elif index == 4:
                display_value = f"{float(value):.1f}"

            else:
                display_value = str(value)

            col.write(display_value)

def render_defensive_box_score(
    team_name,
    player_stats
):
    defenders = [
        player
        for player in player_stats
        if any([
            (player["total_tackles"] or 0) > 0,
            (player["solo_tackles"] or 0) > 0,
            float(player["sacks"] or 0) > 0,
            float(player["tackles_for_loss"] or 0) > 0,
            (player["passes_defended"] or 0) > 0,
            (player["qb_hits"] or 0) > 0,
            (player["defensive_interceptions"] or 0) > 0,
            (player["fumbles_recovered"] or 0) > 0,
            (player["defensive_touchdowns"] or 0) > 0
        ])
    ]

    if not defenders:
        return

    defenders.sort(
        key=lambda player: (
            player["total_tackles"] or 0,
            float(player["sacks"] or 0),
            player["defensive_interceptions"] or 0
        ),
        reverse=True
    )

    st.markdown(f"#### {team_name} Defense")

    header_cols = st.columns(
        [2, 1, 1, 1, 1, 1, 1, 1, 1, 1]
    )

    headers = [
        "Player",
        "TOT",
        "SOLO",
        "SACK",
        "TFL",
        "PD",
        "QB HIT",
        "INT",
        "FR",
        "TD"
    ]

    for col, header in zip(header_cols, headers):
        col.markdown(f"**{header}**")

    for player in defenders:

        cols = st.columns(
            [2, 1, 1, 1, 1, 1, 1, 1, 1, 1]
        )

        values = [
            player["player_name"],
            player["total_tackles"],
            player["solo_tackles"],
            player["sacks"],
            player["tackles_for_loss"],
            player["passes_defended"],
            player["qb_hits"],
            player["defensive_interceptions"],
            player["fumbles_recovered"],
            player["defensive_touchdowns"]
        ]

        for index, (col, value) in enumerate(
            zip(cols, values)
        ):
            if value is None:
                display_value = "0"

            elif index in (3, 4):
                number = float(value)

                if number.is_integer():
                    display_value = str(int(number))
                else:
                    display_value = f"{number:.1f}"

            else:
                display_value = str(value)

            col.write(display_value)

def render_kicking_box_score(
    team_name,
    player_stats
):
    kickers = [
        player
        for player in player_stats
        if player["field_goals_made_attempted"] is not None
        or player["extra_points_made_attempted"] is not None
    ]

    if not kickers:
        return

    st.markdown(f"#### {team_name} Kicking")

    header_cols = st.columns([2, 1, 1, 1, 1, 1])

    headers = [
        "Player",
        "FG",
        "FG%",
        "LONG",
        "XP",
        "PTS"
    ]

    for col, header in zip(header_cols, headers):
        col.markdown(f"**{header}**")

    for player in kickers:

        cols = st.columns([2, 1, 1, 1, 1, 1])

        fg_pct = player["field_goal_pct"]

        values = [
            player["player_name"],
            player["field_goals_made_attempted"],
            (
                f"{float(fg_pct):.1f}%"
                if fg_pct is not None
                else "—"
            ),
            player["long_field_goal_made"],
            player["extra_points_made_attempted"],
            player["total_kicking_points"]
        ]

        for col, value in zip(cols, values):
            col.write("—" if value is None else str(value))

def render_punting_box_score(
    team_name,
    player_stats
):
    punters = [
        player
        for player in player_stats
        if player["punts"] is not None
        and player["punts"] > 0
    ]

    if not punters:
        return

    st.markdown(f"#### {team_name} Punting")

    header_cols = st.columns([2, 1, 1, 1, 1, 1, 1])

    headers = [
        "Player",
        "PUNTS",
        "YDS",
        "AVG",
        "TB",
        "IN20",
        "LONG"
    ]

    for col, header in zip(header_cols, headers):
        col.markdown(f"**{header}**")

    for player in punters:

        cols = st.columns([2, 1, 1, 1, 1, 1, 1])

        avg = player["gross_avg_punt_yards"]

        values = [
            player["player_name"],
            player["punts"],
            player["punt_yards"],
            f"{float(avg):.1f}" if avg is not None else "—",
            player["touchbacks"],
            player["punts_inside_20"],
            player["long_punt"]
        ]

        for col, value in zip(cols, values):
            col.write("—" if value is None else str(value))

def render_return_box_score(
    team_name,
    player_stats
):
    returners = [
        player
        for player in player_stats
        if (
            (player["kick_returns"] or 0) > 0
            or (player["punt_returns"] or 0) > 0
        )
    ]

    if not returners:
        return

    st.markdown(f"#### {team_name} Returns")

    header_cols = st.columns(
        [2, 1, 1, 1, 1, 1, 1, 1, 1]
    )

    headers = [
        "Player",
        "KR",
        "KR YDS",
        "KR AVG",
        "KR LONG",
        "PR",
        "PR YDS",
        "PR AVG",
        "TD"
    ]

    for col, header in zip(header_cols, headers):
        col.markdown(f"**{header}**")

    for player in returners:

        cols = st.columns(
            [2, 1, 1, 1, 1, 1, 1, 1, 1]
        )

        kr_avg = player["yards_per_kick_return"]
        pr_avg = player["yards_per_punt_return"]

        values = [
            player["player_name"],
            player["kick_returns"] or 0,
            player["kick_return_yards"] or 0,
            (
                f"{float(kr_avg):.1f}"
                if kr_avg is not None
                else "—"
            ),
            player["long_kick_return"] or 0,
            player["punt_returns"] or 0,
            player["punt_return_yards"] or 0,
            (
                f"{float(pr_avg):.1f}"
                if pr_avg is not None
                else "—"
            ),
            (player["kick_return_touchdowns"] or 0)
            + (player["punt_return_touchdowns"] or 0)
        ]

        for col, value in zip(cols, values):
            col.write(str(value))

def render_fumbles_box_score(
    team_name,
    player_stats
):
    fumblers = [
        player
        for player in player_stats
        if (
            (player["fumbles"] or 0) > 0
            or (player["fumbles_lost"] or 0) > 0
        )
    ]

    if not fumblers:
        return

    fumblers.sort(
        key=lambda player: (
            player["fumbles"] or 0,
            player["fumbles_lost"] or 0
        ),
        reverse=True
    )

    st.markdown(f"#### {team_name} Fumbles")

    header_cols = st.columns([2, 1, 1])

    headers = [
        "Player",
        "FUM",
        "LOST"
    ]

    for col, header in zip(header_cols, headers):
        col.markdown(f"**{header}**")

    for player in fumblers:

        cols = st.columns([2, 1, 1])

        values = [
            player["player_name"],
            player["fumbles"] or 0,
            player["fumbles_lost"] or 0
        ]

        for col, value in zip(cols, values):
            col.write(str(value))

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

def get_weather_description(weather_code):
    descriptions = {
        0: "Clear",
        1: "Mostly Clear",
        2: "Partly Cloudy",
        3: "Overcast",
        45: "Fog",
        48: "Freezing Fog",
        51: "Light Drizzle",
        53: "Drizzle",
        55: "Heavy Drizzle",
        56: "Light Freezing Drizzle",
        57: "Heavy Freezing Drizzle",
        61: "Light Rain",
        63: "Rain",
        65: "Heavy Rain",
        66: "Light Freezing Rain",
        67: "Heavy Freezing Rain",
        71: "Light Snow",
        73: "Snow",
        75: "Heavy Snow",
        77: "Snow Grains",
        80: "Light Rain Showers",
        81: "Rain Showers",
        82: "Heavy Rain Showers",
        85: "Light Snow Showers",
        86: "Heavy Snow Showers",
        95: "Thunderstorms",
        96: "Thunderstorms with Hail",
        99: "Severe Thunderstorms with Hail"
    }

    return descriptions.get(
        weather_code,
        "Unknown"
    )

def display_weather_forecast(game_weather):

    weather_description = get_weather_description(
        game_weather["weather_code"]
    )

    temp_col, feels_col, condition_col = st.columns(3)

    with temp_col:
        st.metric(
            "Temperature",
            f"{float(game_weather['temperature_f']):.0f}°F"
        )

    with feels_col:
        st.metric(
            "Feels Like",
            f"{float(game_weather['apparent_temperature_f']):.0f}°F"
        )

    with condition_col:
        st.metric(
            "Conditions",
            weather_description
        )

    st.divider()

    precip_col, humidity_col, wind_col, gust_col = st.columns(4)

    with precip_col:
        st.metric(
            "Precipitation",
            f"{float(game_weather['precipitation_probability']):.0f}%"
        )

    with humidity_col:
        st.metric(
            "Humidity",
            f"{float(game_weather['relative_humidity']):.0f}%"
        )

    with wind_col:
        st.metric(
            "Wind",
            f"{float(game_weather['wind_speed_mph']):.1f} mph"
        )

    with gust_col:
        st.metric(
            "Gusts",
            f"{float(game_weather['wind_gust_mph']):.1f} mph"
        )

    st.caption(
        f"Forecast for "
        f"{game_weather['forecast_time'].strftime('%b %d, %Y %I:%M %p')}"
    )

    st.caption(
        f"Forecast updated: "
        f"{game_weather['captured_at'].strftime('%b %d, %Y %I:%M %p')}"
    )

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


def get_league_power_rankings(
    cursor,
    season,
    cutoff_date
):
    cursor.execute(
        """
        SELECT DISTINCT
            team_id,
            team_name
        FROM (
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
        ) teams
        WHERE team_id IS NOT NULL
        ORDER BY team_name;
        """,
        (season, season)
    )

    teams = cursor.fetchall()

    rankings = []

    for team_id, team_name in teams:

        scoring = get_team_scoring_profile(
            cursor,
            team_id,
            season,
            cutoff_date
        )

        offense = get_team_boxscore_profile(
            cursor,
            team_id,
            season,
            cutoff_date
        )

        defense = get_team_defensive_profile(
            cursor,
            team_id,
            season,
            cutoff_date
        )

        power = get_team_power_rating(
            scoring,
            offense,
            defense
        )

        if power is not None:
            rankings.append(
                {
                    "team": team_name,
                    "rating": power["rating"]
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






def render_team_logo(
    logo_url,
    size=120
):
    st.markdown(
        f"""
        <div style="
            height: {size}px;
            display: flex;
            align-items: center;
            justify-content: flex-start;
        ">
            <img
                src="{logo_url}"
                style="
                    max-width: {size}px;
                    max-height: {size}px;
                    object-fit: contain;
                "
            >
        </div>
        """,
        unsafe_allow_html=True
    )

def render_matchup_team(
    team_name,
    logo_url,
    score=None,
    logo_size=120
):
    score_html = ""

    if score is not None:
        score_html = (
            f"<div style='"
            f"font-size:42px;"
            f"font-weight:700;"
            f"line-height:1.1;"
            f"margin-top:14px;"
            f"'>"
            f"{score}"
            f"</div>"
        )

    html = (
        f"<div>"
        f"<div style='"
        f"height:{logo_size}px;"
        f"display:flex;"
        f"align-items:center;"
        f"'>"
        f"<img src='{logo_url}' "
        f"style='"
        f"max-width:{logo_size}px;"
        f"max-height:{logo_size}px;"
        f"object-fit:contain;"
        f"'>"
        f"</div>"

        f"<div style='"
        f"height:72px;"
        f"display:flex;"
        f"align-items:center;"
        f"font-size:28px;"
        f"font-weight:700;"
        f"line-height:1.2;"
        f"margin-top:12px;"
        f"'>"
        f"{team_name}"
        f"</div>"

        f"{score_html}"
        f"</div>"
    )

    st.html(html)

OFFENSIVE_DISPLAY_ORDER = [
    "qb",
    "rb",
    "fb",
    "wr1",
    "wr2",
    "wr3",
    "te",
    "lt",
    "lg",
    "c",
    "rg",
    "rt"
]

DEFENSIVE_DISPLAY_ORDER = [
    "lde",
    "le",
    "dt",
    "nt",
    "rde",
    "re",
    "wlb",
    "lilb",
    "mlb",
    "rilb",
    "slb",
    "olb",
    "lcb",
    "cb1",
    "cb2",
    "nb",
    "ss",
    "fs",
    "rcb"
]

SPECIAL_TEAMS_DISPLAY_ORDER = [
    "pk",
    "p",
    "h",
    "pr",
    "kr",
    "ls"
]

connection = psycopg2.connect(
    host="localhost",
    port=5432,
    database="nfl_data",
    user="nfl_user",
    password="nfl_password"
)


if "page" not in st.session_state:
    st.session_state["page"] = "home"

if "selected_game" not in st.session_state:
    st.session_state["selected_game"] = None


nav_home, nav_schedule, nav_power = st.columns(3)

with nav_home:
    if st.button(
        "Home",
        key="nav_home",
        use_container_width=True
    ):
        st.session_state["page"] = "home"
        st.session_state["selected_game"] = None
        st.rerun()

with nav_schedule:
    if st.button(
        "Schedule",
        key="nav_schedule",
        use_container_width=True
    ):
        st.session_state["page"] = "schedule"
        st.session_state["selected_game"] = None
        st.rerun()

with nav_power:
    if st.button(
        "Power Rankings",
        key="nav_power_rankings",
        use_container_width=True
    ):
        st.session_state["page"] = "power_rankings"
        st.session_state["selected_game"] = None
        st.rerun()

if "selected_week" not in st.session_state:
    st.session_state["selected_week"] = 1

# -------------------------
# HOME PAGE
# -------------------------

if st.session_state["page"] == "home":

    st.title("NFL Dashboard")

    st.caption(
        "Game predictions, matchup analysis, power ratings, "
        "player spotlights, betting markets, and live NFL data."
    )

    st.divider()

    # -------------------------
    # QUICK ACCESS
    # -------------------------

    st.subheader("Explore")

    schedule_col, rankings_col = st.columns(2)

    with schedule_col:
        with st.container(border=True):
            st.markdown("### Weekly Schedule")
            st.write(
                "Browse every matchup by week and open full "
                "game previews."
            )

            if st.button(
                "View Schedule",
                key="home_schedule",
                use_container_width=True
            ):
                st.session_state["page"] = "schedule"
                st.rerun()

    with rankings_col:
        with st.container(border=True):
            st.markdown("### Power Rankings")
            st.write(
                "View league-wide team ratings entering "
                "each week."
            )

            if st.button(
                "View Power Rankings",
                key="home_power_rankings",
                use_container_width=True
            ):
                st.session_state["page"] = "power_rankings"
                st.rerun()

    st.divider()

    # -------------------------
    # MODEL
    # -------------------------

    st.subheader("Prediction Model")

    model_col, confidence_col, matchup_col = st.columns(3)

    with model_col:
        st.metric(
            "2025 Holdout Accuracy",
            "67.5%"
        )

    with confidence_col:
        st.metric(
            "70–80% Confidence",
            "72.5%"
        )

    with matchup_col:
        st.metric(
            "Model Version",
            "V2"
        )

    st.caption(
        "V2 was evaluated using rolling season holdouts, with each "
        "season evaluated using only information available prior to each game."
    )

    st.divider()

    # -------------------------
    # FEATURES
    # -------------------------

    st.subheader("Dashboard Features")

    feature_rows = [
        {
            "Feature": "Game Predictions",
            "Description": "Win probabilities, confidence, and prediction breakdown."
        },
        {
            "Feature": "Matchup Analysis",
            "Description": "Offense-vs-defense comparisons and matchup advantages."
        },
        {
            "Feature": "Power Ratings",
            "Description": "Team strength ratings and league-wide rankings."
        },
        {
            "Feature": "Betting Markets",
            "Description": "Moneylines, spreads, totals, no-vig probabilities, and model edge."
        },
        {
            "Feature": "Player Spotlights",
            "Description": "Key quarterbacks, skill players, and defensive impact players."
        },
        {
            "Feature": "Injuries & Weather",
            "Description": "Game-context information for availability and conditions."
        }
    ]

    st.dataframe(
        pd.DataFrame(feature_rows),
        hide_index=True,
        use_container_width=True
    )

    st.stop()

if st.session_state["page"] == "schedule":

    st.title(f"NFL {DISPLAY_SEASON} Schedule")

    selected_week = st.selectbox(
        "Select Week",
        list(range(1, 19)),
        index=st.session_state["selected_week"] - 1
    )

    st.session_state["selected_week"] = selected_week

else:
    selected_week = st.session_state["selected_week"]
cursor = connection.cursor()

cursor.execute(
    """
    SELECT
        g.game_id,
        g.game_date,
        g.away_team,
        g.home_team,
        g.away_team_id,
        g.home_team_id,
        g.away_logo,
        g.home_logo,
        g.away_record,
        g.home_record,
        g.away_home_record,
        g.away_road_record,
        g.home_home_record,
        g.home_road_record,
        g.venue,
        g.venue_type,
        g.away_score,
        g.home_score,
        g.game_state,
        g.game_status,
        g.completed,

        away_standings.conference,
        away_standings.division_record,
        away_standings.conference_record,
        away_standings.streak,

        home_standings.conference,
        home_standings.division_record,
        home_standings.conference_record,
        home_standings.streak

    FROM nfl_games g

    LEFT JOIN nfl_team_standings away_standings
        ON g.away_team_id = away_standings.team_id
        AND g.season = away_standings.season

    LEFT JOIN nfl_team_standings home_standings
        ON g.home_team_id = home_standings.team_id
        AND g.season = home_standings.season

    WHERE g.season = %s
      AND g.week = %s

    ORDER BY g.game_date;
    """,
    (DISPLAY_SEASON, selected_week)
)

games = cursor.fetchall()


# -------------------------
# GAME DETAIL PAGE
# -------------------------
if (
    st.session_state["page"] == "game"
    and st.session_state["selected_game"]
):

    selected_game_id = st.session_state["selected_game"]

    selected_game = next(
        (
            game for game in games
            if game[0] == selected_game_id
        ),
        None
    )

    if selected_game is None:
        st.session_state["selected_game"] = None
        st.rerun()

    (
        game_id,
        game_date,
        away_team,
        home_team,
        away_team_id,
        home_team_id,
        away_logo,
        home_logo,
        away_record,
        home_record,
        away_home_record,
        away_road_record,
        home_home_record,
        home_road_record,
        venue,
        venue_type,
        away_score,
        home_score,
        game_state,
        game_status,
        completed,
        away_conference,
        away_division_record,
        away_conference_record,
        away_streak,
        home_conference,
        home_division_record,
        home_conference_record,
        home_streak
    ) = selected_game
    away_last_three = get_last_three(
        cursor,
        away_team_id,
        DISPLAY_SEASON,
        game_date
    )

    home_last_three = get_last_three(
        cursor,
        home_team_id,
        DISPLAY_SEASON,
        game_date
    )

    head_to_head = get_head_to_head(
        cursor,
        away_team_id,
        home_team_id,
        game_date
    )

    away_scoring = get_team_scoring_profile(
        cursor,
        away_team_id,
        DISPLAY_SEASON,
        game_date
    )

    home_scoring = get_team_scoring_profile(
        cursor,
        home_team_id,
        DISPLAY_SEASON,
        game_date
    )

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

    away_boxscore = get_team_boxscore_profile(
        cursor,
        away_team_id,
        DISPLAY_SEASON,
        game_date
    )

    home_boxscore = get_team_boxscore_profile(
        cursor,
        home_team_id,
        DISPLAY_SEASON,
        game_date
    )

    away_defense = get_team_defensive_profile(
        cursor,
        away_team_id,
        DISPLAY_SEASON,
        game_date
    )

    home_defense = get_team_defensive_profile(
        cursor,
        home_team_id,
        DISPLAY_SEASON,
        game_date
    )

    previous_season = DISPLAY_SEASON - 1

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

    away_offense_vs_home_defense = get_matchup_comparison(
        away_boxscore_blended,
        home_defense_blended
    )

    home_offense_vs_away_defense = get_matchup_comparison(
        home_boxscore_blended,
        away_defense_blended
    )

    away_power_rating = get_team_power_rating(
        away_scoring_blended,
        away_boxscore_blended,
        away_defense_blended
    )

    home_power_rating = get_team_power_rating(
        home_scoring_blended,
        home_boxscore_blended,
        home_defense_blended
    )

    away_matchup_advantages = get_matchup_advantages(
        away_offense_vs_home_defense
    )

    home_matchup_advantages = get_matchup_advantages(
        home_offense_vs_away_defense
    )

    league_matchup_baselines = get_league_matchup_baselines(
        cursor,
        DISPLAY_SEASON,
        game_date
    )

    away_matchup_edges = get_matchup_edges(
        away_offense_vs_home_defense,
        league_matchup_baselines
    )

    home_matchup_edges = get_matchup_edges(
        home_offense_vs_away_defense,
        league_matchup_baselines
    )

    matchup_prediction_adjustment = (
        get_matchup_prediction_adjustment(
            away_matchup_edges,
            home_matchup_edges
        )
    )

    recent_form_adjustment = get_recent_form_adjustment(
        away_scoring,
        home_scoring,
        away_boxscore,
        home_boxscore,
        away_defense,
        home_defense
    )

    raw_prediction_edge = get_raw_prediction_edge(
        away_power_rating,
        home_power_rating,
        matchup_prediction_adjustment,
        recent_form_adjustment
    )

    game_prediction = get_v2_win_probability(
        raw_prediction_edge["power_edge"]
        if raw_prediction_edge
        else None,

        raw_prediction_edge["matchup_edge"]
        if raw_prediction_edge
        else None,

        raw_prediction_edge["recent_form_edge"]
        if raw_prediction_edge
        else None
    )

    away_game_team_stats = get_game_team_stats(
        cursor,
        game_id,
        away_team_id
    )

    home_game_team_stats = get_game_team_stats(
        cursor,
        game_id,
        home_team_id
    )

    away_game_player_stats = get_game_player_stats(
        cursor,
        game_id,
        away_team_id
    )

    home_game_player_stats = get_game_player_stats(
        cursor,
        game_id,
        home_team_id
    )

    away_injuries = get_game_injuries(
        cursor,
        game_id,
        away_team_id
    )

    home_injuries = get_game_injuries(
        cursor,
        game_id,
        home_team_id
    )

    away_injury_changes = get_injury_changes(
        cursor,
        game_id,
        away_team_id
    )

    home_injury_changes = get_injury_changes(
        cursor,
        game_id,
        home_team_id
    )

    away_injury_updated = get_latest_injury_snapshot_time(
        cursor,
        game_id,
        away_team_id
    )

    home_injury_updated = get_latest_injury_snapshot_time(
        cursor,
        game_id,
        home_team_id
    )

    game_weather = get_game_weather(
        cursor,
        game_id
    )

    game_betting = get_latest_betting_snapshot(
        cursor,
        game_id
    )

    away_ml_probability = None
    home_ml_probability = None

    away_no_vig_probability = None
    home_no_vig_probability = None

    if game_betting:
        away_ml_probability = american_odds_to_probability(
            game_betting["away_moneyline"]
        )

        home_ml_probability = american_odds_to_probability(
            game_betting["home_moneyline"]
        )

        (
            away_no_vig_probability,
            home_no_vig_probability
        ) = remove_vig(
            away_ml_probability,
            home_ml_probability
        )
    away_offensive_starters = get_offensive_starters(
        cursor,
        away_team_id
    )

    home_offensive_starters = get_offensive_starters(
        cursor,
        home_team_id
    )

    away_qb = next(
        (
            starter
            for starter in away_offensive_starters
            if starter[0] == "qb"
        ),
        None
    )

    home_qb = next(
        (
            starter
            for starter in home_offensive_starters
            if starter[0] == "qb"
        ),
        None
    )

    away_qb_profile = None

    if away_qb:
        away_qb_profile = get_qb_profile(
            cursor,
            away_qb[2],
            DISPLAY_SEASON,
            game_date
        ) 

    home_qb_profile = None

    if home_qb:
        home_qb_profile = get_qb_profile(
            cursor,
            home_qb[2],
            DISPLAY_SEASON,
            game_date
        )

    away_rb = next(
        (
            starter
            for starter in away_offensive_starters
            if starter[0] == "rb"
        ),
        None
    )

    home_rb = next(
        (
            starter
            for starter in home_offensive_starters
            if starter[0] == "rb"
        ),
        None
    )

    away_rb_profile = None

    if away_rb:
        away_rb_profile = get_rb_profile(
            cursor,
            away_rb[2],
            DISPLAY_SEASON,
            game_date
        )

    home_rb_profile = None

    if home_rb:
        home_rb_profile = get_rb_profile(
            cursor,
            home_rb[2],
            DISPLAY_SEASON,
            game_date
        )

    away_receivers = [
        starter
        for starter in away_offensive_starters
        if starter[0] in ("wr1", "wr2", "wr3", "te")
    ]

    home_receivers = [
        starter
        for starter in home_offensive_starters
        if starter[0] in ("wr1", "wr2", "wr3", "te")
    ]

    away_receiver_profiles = []

    for receiver in away_receivers:
        profile = get_receiving_profile(
            cursor,
            receiver[2],
            DISPLAY_SEASON,
            game_date
        )

        away_receiver_profiles.append(
            (receiver, profile)
        )


    home_receiver_profiles = []

    for receiver in home_receivers:
        profile = get_receiving_profile(
            cursor,
            receiver[2],
            DISPLAY_SEASON,
            game_date
        )

        home_receiver_profiles.append(
            (receiver, profile)
        )

    away_receiver_profile_map = {
        receiver[2]: profile
        for receiver, profile in away_receiver_profiles
    }

    home_receiver_profile_map = {
        receiver[2]: profile
        for receiver, profile in home_receiver_profiles
    }

    away_offensive_map = {
                starter[0]: starter
                for starter in away_offensive_starters
            }
    
    home_offensive_map = {
        starter[0]: starter
        for starter in home_offensive_starters
    }
    
    matchup_offensive_slots = [
        slot
        for slot in OFFENSIVE_DISPLAY_ORDER
        if (
            slot in away_offensive_map
            or slot in home_offensive_map
        )
    ]

    away_defensive_starters = get_defensive_starters(
        cursor,
        away_team_id
    )

    home_defensive_starters = get_defensive_starters(
        cursor,
        home_team_id
    )

    away_defensive_map = {
        starter[0]: starter
        for starter in away_defensive_starters
    }

    home_defensive_map = {
        starter[0]: starter
        for starter in home_defensive_starters
    }

    matchup_defensive_slots = [
        slot
        for slot in DEFENSIVE_DISPLAY_ORDER
        if (
            slot in away_defensive_map
            or slot in home_defensive_map
        )
    ]

    away_defensive_profile_map = {}

    for starter in away_defensive_starters:
        player_id = starter[2]

        away_defensive_profile_map[player_id] = (
            get_defensive_player_profile(
                cursor,
                player_id,
                DISPLAY_SEASON,
                game_date
            )
        )

    home_defensive_profile_map = {}

    for starter in home_defensive_starters:
        player_id = starter[2]

        home_defensive_profile_map[player_id] = (
            get_defensive_player_profile(
                cursor,
                player_id,
                DISPLAY_SEASON,
                game_date
            )
        )

    away_special_teams = get_special_teams_starters(
        cursor,
        away_team_id
    )

    home_special_teams = get_special_teams_starters(
        cursor,
        home_team_id
    )

    away_special_teams_map = {
        starter[0]: starter
        for starter in away_special_teams
    }

    home_special_teams_map = {
        starter[0]: starter
        for starter in home_special_teams
    }

    away_special_teams_profile_map = {}

    for starter in away_special_teams:
        player_id = starter[2]

        away_special_teams_profile_map[player_id] = (
            get_special_teams_profile(
                cursor,
                player_id,
                DISPLAY_SEASON,
                game_date
            )
        )


    home_special_teams_profile_map = {}

    for starter in home_special_teams:
        player_id = starter[2]

        home_special_teams_profile_map[player_id] = (
            get_special_teams_profile(
                cursor,
                player_id,
                DISPLAY_SEASON,
                game_date
            )
        )

    matchup_special_teams_slots = [
        slot
        for slot in SPECIAL_TEAMS_DISPLAY_ORDER
        if (
            slot in away_special_teams_map
            or slot in home_special_teams_map
        )
    ]

    away_offensive_depth = get_depth_players(
        cursor,
        away_team_id,
        "OFF"
    )

    home_offensive_depth = get_depth_players(
        cursor,
        home_team_id,
        "OFF"
    )

    away_defensive_depth = get_depth_players(
        cursor,
        away_team_id,
        "DEF"
    )

    home_defensive_depth = get_depth_players(
        cursor,
        home_team_id,
        "DEF"
    )

    away_special_teams_depth = get_depth_players(
        cursor,
        away_team_id,
        "ST"
    )

    home_special_teams_depth = get_depth_players(
        cursor,
        home_team_id,
        "ST"
    )

    league_power_rankings = get_league_power_rankings(
        cursor,
        DISPLAY_SEASON,
        game_date
    )

    away_league_power = next(
        (
            team
            for team in league_power_rankings
            if team["team"] == away_team
        ),
        None
    )

    home_league_power = next(
        (
            team
            for team in league_power_rankings
            if team["team"] == home_team
        ),
        None
    )

    away_offensive_depth_profile_map = {}

    for player in away_offensive_depth:
        (
            position_slot,
            position,
            player_id,
            player_name,
            jersey,
            status,
            headshot,
            depth_order
        ) = player

        if position == "QB":
            profile = get_qb_profile(
                cursor,
                player_id,
                DISPLAY_SEASON,
                game_date
            )

        elif position == "RB":
            profile = get_rb_profile(
                cursor,
                player_id,
                DISPLAY_SEASON,
                game_date
            )

        elif position in ("WR", "TE"):
            profile = get_receiving_profile(
                cursor,
                player_id,
                DISPLAY_SEASON,
                game_date
            )

        else:
            profile = None

        away_offensive_depth_profile_map[player_id] = profile

    home_offensive_depth_profile_map = {}

    for player in home_offensive_depth:
        (
            position_slot,
            position,
            player_id,
            player_name,
            jersey,
            status,
            headshot,
            depth_order
        ) = player

        if position == "QB":
            profile = get_qb_profile(
                cursor,
                player_id,
                DISPLAY_SEASON,
                game_date
            )

        elif position == "RB":
            profile = get_rb_profile(
                cursor,
                player_id,
                DISPLAY_SEASON,
                game_date
            )

        elif position in ("WR", "TE"):
            profile = get_receiving_profile(
                cursor,
                player_id,
                DISPLAY_SEASON,
                game_date
            )

        else:
            profile = None

        home_offensive_depth_profile_map[player_id] = profile

    away_defensive_depth_profile_map = {
        player[2]: get_defensive_player_profile(
            cursor,
            player[2],
            DISPLAY_SEASON,
            game_date
        )
        for player in away_defensive_depth
    }

    home_defensive_depth_profile_map = {
        player[2]: get_defensive_player_profile(
            cursor,
            player[2],
            DISPLAY_SEASON,
            game_date
        )
        for player in home_defensive_depth
    }

    away_special_teams_depth_profile_map = {
        player[2]: get_special_teams_profile(
            cursor,
            player[2],
            DISPLAY_SEASON,
            game_date
        )
        for player in away_special_teams_depth
    }

    home_special_teams_depth_profile_map = {
        player[2]: get_special_teams_profile(
            cursor,
            player[2],
            DISPLAY_SEASON,
            game_date
        )
        for player in home_special_teams_depth
    }

    (
        away_offensive_depth_map,
        home_offensive_depth_map,
        matchup_offensive_depth_rows
    ) = get_matchup_depth_rows(
        away_offensive_depth,
        home_offensive_depth,
        OFFENSIVE_DISPLAY_ORDER
    )


    (
        away_defensive_depth_map,
        home_defensive_depth_map,
        matchup_defensive_depth_rows
    ) = get_matchup_depth_rows(
        away_defensive_depth,
        home_defensive_depth,
        DEFENSIVE_DISPLAY_ORDER
    )


    (
        away_special_teams_depth_map,
        home_special_teams_depth_map,
        matchup_special_teams_depth_rows
    ) = get_matchup_depth_rows(
        away_special_teams_depth,
        home_special_teams_depth,
        SPECIAL_TEAMS_DISPLAY_ORDER
    )

    away_last_three_turnover_diff = None

    if away_boxscore and away_defense:
        away_last_three_turnover_diff = (
            away_defense["last_three_takeaways"]
            - away_boxscore["last_three_turnovers"]
        )

    home_last_three_turnover_diff = None

    if home_boxscore and home_defense:
        home_last_three_turnover_diff = (
            home_defense["last_three_takeaways"]
            - home_boxscore["last_three_turnovers"]
        )

    if st.button("← Back to Schedule"):
        st.session_state["selected_game"] = None
        st.session_state["page"] = "schedule"
        st.rerun()

    st.title(f"{away_team} at {home_team}")

    # -------------------------
    # GAME STATUS
    # -------------------------

    if game_status == "Canceled":
        st.markdown(
            "<div style='text-align: center;'>CANCELED</div>",
            unsafe_allow_html=True
        )

    elif game_state == "in":
        st.markdown(
            "<div style='text-align: center;'>LIVE</div>",
            unsafe_allow_html=True
        )

    elif completed:
        st.markdown(
            "<div style='text-align: center;'>FINAL</div>",
            unsafe_allow_html=True
        )

    else:
        st.markdown(
            "<div style='text-align: center;'>UPCOMING</div>",
            unsafe_allow_html=True
        )


    # -------------------------
    # MATCHUP HEADER
    # -------------------------

    away_col, middle_col, home_col = st.columns(
        [2, 1, 2]
    )

    with away_col:
        render_matchup_team(
            away_team,
            away_logo,
            away_score
            if game_state == "in" or completed
            else None,
            logo_size=120
        )

    with middle_col:
        st.markdown("## @")

    with home_col:
        render_matchup_team(
            home_team,
            home_logo,
            home_score
            if game_state == "in" or completed
            else None,
            logo_size=120
        )


    # -------------------------
    # GAME TIME / LIVE STATUS
    # -------------------------

    eastern_time = game_date.astimezone(
        ZoneInfo("America/New_York")
    )

    if game_status == "Canceled":
        st.markdown(
            "<div style='text-align: center;'>Game canceled</div>",
            unsafe_allow_html=True
        )

    elif game_state == "in":
        st.markdown(
            f"<div style='text-align: center;'>"
            f"{game_status or 'In Progress'}"
            f"</div>",
            unsafe_allow_html=True
        )

    elif not completed:
        st.markdown(
            "<div style='text-align: center;'>"
            + eastern_time.strftime(
                "%A, %B %d · %I:%M %p %Z"
            )
            + "</div>",
            unsafe_allow_html=True
        )


    # -------------------------
    # VENUE
    # -------------------------

    st.markdown(
        f"<div style='text-align: center;'>{venue}</div>",
        unsafe_allow_html=True
    )

    st.divider()

    st.header("Team Records")

    away_info, home_info = st.columns(2)

    with away_info:
        st.markdown(f"### {away_team}")
        st.write(f"Conference: {away_conference}")
        st.write(f"Overall: {away_record}")
        st.write(f"Home: {away_home_record}")
        st.write(f"Road: {away_road_record}")
        st.write(f"Division: {away_division_record}")
        st.write(f"Conference Record: {away_conference_record}")
        st.write(f"Streak: {away_streak}")
        st.write(
            f"Last 3 (most recent first): "
            f"{' - '.join(away_last_three) if away_last_three else 'No games played'}"
        )
    with home_info:
        st.markdown(f"### {home_team}")
        st.write(f"Conference: {home_conference}")
        st.write(f"Overall: {home_record}")
        st.write(f"Home: {home_home_record}")
        st.write(f"Road: {home_road_record}")
        st.write(f"Division: {home_division_record}")
        st.write(f"Conference Record: {home_conference_record}")
        st.write(f"Streak: {home_streak}")
        st.write(
            f"Last 3 (most recent first): "
            f"{' - '.join(home_last_three) if home_last_three else 'No games played'}"
        )

    st.divider()

    (
        overview_tab,
        prediction_tab,
        team_stats_tab,
        players_tab,
        matchup_tab,
        game_stats_tab,
        injuries_tab,
        weather_tab,
        betting_tab,
        history_tab
    ) = st.tabs([
        "Overview",
        "Prediction",
        "Team Stats",
        "Players",
        "Matchup",
        "Game Stats",
        "Injuries",
        "Weather",
        "Betting",
        "History"
    ])

    with overview_tab:
        st.subheader("Game Overview")

        # -------------------------
        # PREDICTION SUMMARY
        # -------------------------

        if game_prediction:

            away_probability = (
                game_prediction["away_win_probability"]
                * 100
            )

            home_probability = (
                game_prediction["home_win_probability"]
                * 100
            )

            if home_probability > away_probability:
                predicted_team = home_team
                predicted_probability = home_probability
            else:
                predicted_team = away_team
                predicted_probability = away_probability

            prediction_col, matchup_col = st.columns(2)

            with prediction_col:
                st.markdown("### Model Prediction")
                st.metric(
                    predicted_team,
                    f"{predicted_probability:.1f}%"
                )

            with matchup_col:
                st.markdown("### Matchup Lean")

                if matchup_prediction_adjustment is None:
                    st.write("Unavailable")

                elif matchup_prediction_adjustment > 0.25:
                    st.metric(
                        home_team,
                        "Home matchup edge"
                    )

                elif matchup_prediction_adjustment < -0.25:
                    st.metric(
                        away_team,
                        "Away matchup edge"
                    )

                else:
                    st.metric(
                        "Roughly Even",
                        "Balanced matchup"
                    )

        else:
            st.info(
                "Prediction and matchup summary will populate once "
                "enough game data is available."
            )

        st.divider()

        # -------------------------
        # TEAM CONTEXT
        # -------------------------

        st.markdown("### Team Context")

        away_context_col, home_context_col = st.columns(2)

        with away_context_col:
            st.markdown(f"**{away_team}**")

            st.write(
                f"Record: {away_record}"
            )

            st.write(
                f"Last 3: "
                f"{' - '.join(away_last_three) if away_last_three else 'No games played'}"
            )

        with home_context_col:
            st.markdown(f"**{home_team}**")

            st.write(
                f"Record: {home_record}"
            )

            st.write(
                f"Last 3: "
                f"{' - '.join(home_last_three) if home_last_three else 'No games played'}"
            )

        st.divider()

        # -------------------------
        # MARKET SUMMARY
        # -------------------------

        st.markdown("### Market")

        if (
            game_betting
            and game_betting["away_moneyline"] is not None
            and game_betting["home_moneyline"] is not None
        ):
            market_col_1, market_col_2 = st.columns(2)

            with market_col_1:
                st.metric(
                    away_team,
                    f"{int(game_betting['away_moneyline']):+d}"
                )

            with market_col_2:
                st.metric(
                    home_team,
                    f"{int(game_betting['home_moneyline']):+d}"
                )

        else:
            st.write(
                "Current moneyline market unavailable."
            )

    with prediction_tab:
        st.subheader("Game Prediction")

        if not game_prediction:
            st.info(
                "Prediction unavailable for this game."
            )

        else:
            away_probability = (
                game_prediction[
                    "away_win_probability"
                ]
                * 100
            )

            home_probability = (
                game_prediction[
                    "home_win_probability"
                ]
                * 100
            )

            away_prediction_col, home_prediction_col = (
                st.columns(2)
            )

            with away_prediction_col:
                st.markdown(
                    f"### {away_team}"
                )

                st.metric(
                    "Win Probability",
                    f"{away_probability:.1f}%"
                )

            with home_prediction_col:
                st.markdown(
                    f"### {home_team}"
                )

                st.metric(
                    "Win Probability",
                    f"{home_probability:.1f}%"
                )

            if away_probability > home_probability:
                predicted_winner = away_team
                predicted_probability = away_probability

            else:
                predicted_winner = home_team
                predicted_probability = home_probability

            prediction_confidence = get_prediction_confidence(
                predicted_probability / 100
            )

            st.markdown("### Model Pick")

            st.write(
                f"{predicted_winner} "
                f"({predicted_probability:.1f}%)"
            )

            st.caption(
                f"Confidence: {prediction_confidence}"
            )

        st.divider()

        st.subheader("Prediction Breakdown")

        breakdown_rows = [
            {
                "Component": "Power Rating Edge",
                "Input": raw_prediction_edge["power_edge"]
            },
            {
                "Component": "Matchup Edge",
                "Input": raw_prediction_edge["matchup_edge"]
            },
            {
                "Component": "Recent Form Edge",
                "Input": raw_prediction_edge["recent_form_edge"]
            }
        ]

        breakdown_df = pd.DataFrame(
            breakdown_rows
        )

        breakdown_df["Input"] = (
            breakdown_df["Input"]
            .map(lambda value: f"{value:+.2f}")
        )

        st.dataframe(
            breakdown_df,
            hide_index=True,
            use_container_width=True
        )

        st.caption(
            f"Positive values favor {home_team}; "
            f"negative values favor {away_team}. "
            "V2 combines these inputs using weights learned "
            "from historical games."
        )

        st.divider()

        st.subheader("Model vs Market")

        if (
            game_prediction is not None
            and away_no_vig_probability is not None
            and home_no_vig_probability is not None
        ):
            away_model_probability = (
                game_prediction["away_win_probability"]
            )

            home_model_probability = (
                game_prediction["home_win_probability"]
            )

            away_market_edge = (
                away_model_probability
                - away_no_vig_probability
            )

            home_market_edge = (
                home_model_probability
                - home_no_vig_probability
            )

            model_market_df = pd.DataFrame(
                [
                    {
                        "Team": away_team,
                        "Model": f"{away_model_probability * 100:.1f}%",
                        "Market": f"{away_no_vig_probability * 100:.1f}%",
                        "Difference": f"{away_market_edge * 100:+.1f}%"
                    },
                    {
                        "Team": home_team,
                        "Model": f"{home_model_probability * 100:.1f}%",
                        "Market": f"{home_no_vig_probability * 100:.1f}%",
                        "Difference": f"{home_market_edge * 100:+.1f}%"
                    }
                ]
            )

            st.dataframe(
                model_market_df,
                hide_index=True,
                use_container_width=True
            )

            st.markdown("### Model Edge")

            if away_market_edge > home_market_edge:
                market_edge_team = away_team
                market_edge_value = away_market_edge
                market_model_probability = away_model_probability
                market_probability = away_no_vig_probability
            else:
                market_edge_team = home_team
                market_edge_value = home_market_edge
                market_model_probability = home_model_probability
                market_probability = home_no_vig_probability

            if market_edge_value > 0.03:
                st.metric(
                    market_edge_team,
                    f"{market_edge_value * 100:+.1f}%"
                )

                st.caption(
                    f"V2 model: {market_model_probability * 100:.1f}% · "
                    f"No-vig market: {market_probability * 100:.1f}%"
                )

            else:
                st.write(
                    "No meaningful moneyline edge identified."
                )

            st.caption(
                "Difference shows the model's win probability "
                "minus the sportsbook's no-vig market probability."
            )

        else:
            if game_prediction is None:
                st.info(
                    "Model comparison will populate once enough "
                    "2026 game data is available to generate a prediction."
                )

            else:
                st.info(
                    "Market comparison is unavailable because "
                    "moneyline odds are not available for this game."
                )

    with team_stats_tab:
        st.subheader("Team Stats")

        if (
            away_scoring
            and home_scoring
            and away_boxscore
            and home_boxscore
            and away_defense
            and home_defense
        ):

            # -------------------------
            # SCORING
            # -------------------------

            st.markdown("### Scoring")

            scoring_rows = [
                {
                    "Metric": "Games Played",
                    away_team: away_scoring["games_played"],
                    home_team: home_scoring["games_played"]
                },
                {
                    "Metric": "Points / Game",
                    away_team: f"{away_scoring['ppg']:.1f}",
                    home_team: f"{home_scoring['ppg']:.1f}"
                },
                {
                    "Metric": "Points Allowed / Game",
                    away_team: f"{away_scoring['ppg_allowed']:.1f}",
                    home_team: f"{home_scoring['ppg_allowed']:.1f}"
                },
                {
                    "Metric": "Scoring Margin / Game",
                    away_team: f"{away_scoring['scoring_margin']:+.1f}",
                    home_team: f"{home_scoring['scoring_margin']:+.1f}"
                },
                {
                    "Metric": "Win %",
                    away_team: f"{away_scoring['win_pct'] * 100:.1f}%",
                    home_team: f"{home_scoring['win_pct'] * 100:.1f}%"
                },
                {
                    "Metric": "Home PPG",
                    away_team: (
                        f"{away_scoring['home_ppg']:.1f}"
                        if away_scoring["home_ppg"] is not None
                        else "—"
                    ),
                    home_team: (
                        f"{home_scoring['home_ppg']:.1f}"
                        if home_scoring["home_ppg"] is not None
                        else "—"
                    )
                },
                {
                    "Metric": "Road PPG",
                    away_team: (
                        f"{away_scoring['road_ppg']:.1f}"
                        if away_scoring["road_ppg"] is not None
                        else "—"
                    ),
                    home_team: (
                        f"{home_scoring['road_ppg']:.1f}"
                        if home_scoring["road_ppg"] is not None
                        else "—"
                    )
                }
            ]

            st.dataframe(
                scoring_rows,
                use_container_width=True,
                hide_index=True
            )

            # -------------------------
            # OFFENSE
            # -------------------------

            st.markdown("### Offense")

            offense_rows = [
                {
                    "Metric": "Total Yards / Game",
                    away_team: f"{away_boxscore['total_yards_per_game']:.1f}",
                    home_team: f"{home_boxscore['total_yards_per_game']:.1f}"
                },
                {
                    "Metric": "Passing Yards / Game",
                    away_team: f"{away_boxscore['passing_yards_per_game']:.1f}",
                    home_team: f"{home_boxscore['passing_yards_per_game']:.1f}"
                },
                {
                    "Metric": "Rushing Yards / Game",
                    away_team: f"{away_boxscore['rushing_yards_per_game']:.1f}",
                    home_team: f"{home_boxscore['rushing_yards_per_game']:.1f}"
                },
                {
                    "Metric": "Yards / Play",
                    away_team: f"{away_boxscore['yards_per_play']:.2f}",
                    home_team: f"{home_boxscore['yards_per_play']:.2f}"
                },
                {
                    "Metric": "First Downs / Game",
                    away_team: f"{away_boxscore['first_downs_per_game']:.1f}",
                    home_team: f"{home_boxscore['first_downs_per_game']:.1f}"
                },
                {
                    "Metric": "Turnovers / Game",
                    away_team: f"{away_boxscore['turnovers_per_game']:.2f}",
                    home_team: f"{home_boxscore['turnovers_per_game']:.2f}"
                },
                {
                    "Metric": "3rd Down",
                    away_team: f"{away_boxscore['third_down_pct'] * 100:.1f}%",
                    home_team: f"{home_boxscore['third_down_pct'] * 100:.1f}%"
                },
                {
                    "Metric": "Red Zone",
                    away_team: f"{away_boxscore['red_zone_pct'] * 100:.1f}%",
                    home_team: f"{home_boxscore['red_zone_pct'] * 100:.1f}%"
                },
                {
                    "Metric": "Avg. Possession",
                    away_team: away_boxscore["average_possession"],
                    home_team: home_boxscore["average_possession"]
                }
            ]

            st.dataframe(
                offense_rows,
                use_container_width=True,
                hide_index=True
            )

            # -------------------------
            # DEFENSE
            # -------------------------

            st.markdown("### Defense")

            defense_rows = [
                {
                    "Metric": "Yards Allowed / Game",
                    away_team: f"{away_defense['yards_allowed_per_game']:.1f}",
                    home_team: f"{home_defense['yards_allowed_per_game']:.1f}"
                },
                {
                    "Metric": "Pass Yards Allowed / Game",
                    away_team: f"{away_defense['passing_yards_allowed_per_game']:.1f}",
                    home_team: f"{home_defense['passing_yards_allowed_per_game']:.1f}"
                },
                {
                    "Metric": "Rush Yards Allowed / Game",
                    away_team: f"{away_defense['rushing_yards_allowed_per_game']:.1f}",
                    home_team: f"{home_defense['rushing_yards_allowed_per_game']:.1f}"
                },
                {
                    "Metric": "Yards / Play Allowed",
                    away_team: f"{away_defense['yards_per_play_allowed']:.2f}",
                    home_team: f"{home_defense['yards_per_play_allowed']:.2f}"
                },
                {
                    "Metric": "First Downs Allowed / Game",
                    away_team: f"{away_defense['first_downs_allowed_per_game']:.1f}",
                    home_team: f"{home_defense['first_downs_allowed_per_game']:.1f}"
                },
                {
                    "Metric": "Takeaways / Game",
                    away_team: f"{away_defense['takeaways_per_game']:.2f}",
                    home_team: f"{home_defense['takeaways_per_game']:.2f}"
                },
                {
                    "Metric": "Opponent 3rd Down",
                    away_team: (
                        f"{away_defense['opponent_third_down_pct'] * 100:.1f}%"
                    ),
                    home_team: (
                        f"{home_defense['opponent_third_down_pct'] * 100:.1f}%"
                    )
                },
                {
                    "Metric": "Opponent Red Zone",
                    away_team: (
                        f"{away_defense['opponent_red_zone_pct'] * 100:.1f}%"
                    ),
                    home_team: (
                        f"{home_defense['opponent_red_zone_pct'] * 100:.1f}%"
                    )
                },
                {
                    "Metric": "Defensive TDs",
                    away_team: away_defense["defensive_touchdowns"],
                    home_team: home_defense["defensive_touchdowns"]
                }
            ]

            st.dataframe(
                defense_rows,
                use_container_width=True,
                hide_index=True
            )

            # -------------------------
            # RECENT FORM
            # -------------------------

            st.divider()
            st.subheader("Recent Form — Last 3 Games")

            recent_form_rows = [
                {
                    "Metric": "Record",
                    away_team: (
                        " - ".join(away_last_three)
                        if away_last_three
                        else "—"
                    ),
                    home_team: (
                        " - ".join(home_last_three)
                        if home_last_three
                        else "—"
                    )
                },
                {
                    "Metric": "Points / Game",
                    away_team: f"{away_scoring['last_three_ppg']:.1f}",
                    home_team: f"{home_scoring['last_three_ppg']:.1f}"
                },
                {
                    "Metric": "Points Allowed / Game",
                    away_team: f"{away_scoring['last_three_ppg_allowed']:.1f}",
                    home_team: f"{home_scoring['last_three_ppg_allowed']:.1f}"
                },
                {
                    "Metric": "Yards / Game",
                    away_team: f"{away_boxscore['last_three_yards_per_game']:.1f}",
                    home_team: f"{home_boxscore['last_three_yards_per_game']:.1f}"
                },
                {
                    "Metric": "Yards Allowed / Game",
                    away_team: f"{away_defense['last_three_yards_allowed_per_game']:.1f}",
                    home_team: f"{home_defense['last_three_yards_allowed_per_game']:.1f}"
                },
                {
                    "Metric": "Turnover Differential",
                    away_team: f"{away_last_three_turnover_diff:+d}",
                    home_team: f"{home_last_three_turnover_diff:+d}"
                }
            ]

            st.dataframe(
                recent_form_rows,
                use_container_width=True,
                hide_index=True
            )

        else:
            st.info(
                f"Team statistics will populate once both teams "
                f"have completed games in the {DISPLAY_SEASON} season."
            )

    away_key_players = get_key_player_spotlights(
        away_offensive_map,
        away_defensive_map,
        away_qb_profile,
        away_qb[2] if away_qb else None,
        away_rb_profile,
        away_rb[2] if away_rb else None,
        away_receiver_profile_map,
        away_defensive_profile_map
    )

    home_key_players = get_key_player_spotlights(
        home_offensive_map,
        home_defensive_map,
        home_qb_profile,
        home_qb[2] if home_qb else None,
        home_rb_profile,
        home_rb[2] if home_rb else None,
        home_receiver_profile_map,
        home_defensive_profile_map
    )

    with players_tab:

        st.subheader("Key Player Spotlights")

        has_away_spotlights = any(
            away_key_players.values()
        )

        has_home_spotlights = any(
            home_key_players.values()
        )

        if not has_away_spotlights and not has_home_spotlights:
            st.info(
                "Player spotlights will populate once current-season "
                "game data is available."
            )

        else:
            away_spotlight_col, home_spotlight_col = st.columns(2)

            # -------------------------
            # AWAY TEAM
            # -------------------------

            with away_spotlight_col:
                st.markdown(f"### {away_team}")

                # QUARTERBACK
                if away_key_players["qb"]:
                    qb = away_key_players["qb"]
                    player = qb["player"]
                    profile = qb["profile"]

                    st.markdown(
                        f"**QB · {player[3]}**"
                    )

                    st.write(
                        f"{profile['passing_yards_per_game']:.1f} pass YPG · "
                        f"{profile['passing_touchdowns']} Pass TD · "
                        f"{profile['interceptions']} INT"
                    )

                    if (
                        profile["rushing_yards"] > 0
                        or profile["rushing_touchdowns"] > 0
                    ):
                        st.write(
                            f"{profile['rushing_yards']} Rush YDS · "
                            f"{profile['rushing_touchdowns']} Rush TD"
                        )

                # SKILL PLAYER
                if away_key_players["skill"]:
                    skill = away_key_players["skill"]
                    player = skill["player"]
                    profile = skill["profile"]

                    st.markdown(
                        f"**Skill · {player[3]} ({skill['type']})**"
                    )

                    if skill["type"] == "RB":
                        st.write(
                            f"{profile['scrimmage_yards'] / profile['games_played']:.1f} "
                            f"scrimmage YPG · "
                            f"{profile['total_touchdowns']} TD"
                        )

                    else:
                        st.write(
                            f"{profile['receiving_yards_per_game']:.1f} rec YPG · "
                            f"{profile['targets']} targets · "
                            f"{profile['receiving_touchdowns']} TD"
                        )

                # DEFENSE
                if away_key_players["defense"]:
                    defense = away_key_players["defense"]
                    player = defense["player"]
                    profile = defense["profile"]

                    st.markdown(
                        f"**Defense · {player[3]} ({defense['type']})**"
                    )

                    st.write(
                        f"{profile['sacks']:.1f} sacks · "
                        f"{profile['interceptions']} INT · "
                        f"{profile['total_tackles']} tackles"
                    )

            # -------------------------
            # HOME TEAM
            # -------------------------

            with home_spotlight_col:
                st.markdown(f"### {home_team}")

                # QUARTERBACK
                if home_key_players["qb"]:
                    qb = home_key_players["qb"]
                    player = qb["player"]
                    profile = qb["profile"]

                    st.markdown(
                        f"**QB · {player[3]}**"
                    )

                    st.write(
                        f"{profile['passing_yards_per_game']:.1f} pass YPG · "
                        f"{profile['passing_touchdowns']} Pass TD · "
                        f"{profile['interceptions']} INT"
                    )

                    if (
                        profile["rushing_yards"] > 0
                        or profile["rushing_touchdowns"] > 0
                    ):
                        st.write(
                            f"{profile['rushing_yards']} Rush YDS · "
                            f"{profile['rushing_touchdowns']} Rush TD"
                        )

                # SKILL PLAYER
                if home_key_players["skill"]:
                    skill = home_key_players["skill"]
                    player = skill["player"]
                    profile = skill["profile"]

                    st.markdown(
                        f"**Skill · {player[3]} ({skill['type']})**"
                    )

                    if skill["type"] == "RB":
                        st.write(
                            f"{profile['scrimmage_yards'] / profile['games_played']:.1f} "
                            f"scrimmage YPG · "
                            f"{profile['total_touchdowns']} TD"
                        )

                    else:
                        st.write(
                            f"{profile['receiving_yards_per_game']:.1f} rec YPG · "
                            f"{profile['targets']} targets · "
                            f"{profile['receiving_touchdowns']} TD"
                        )

                # DEFENSE
                if home_key_players["defense"]:
                    defense = home_key_players["defense"]
                    player = defense["player"]
                    profile = defense["profile"]

                    st.markdown(
                        f"**Defense · {player[3]} ({defense['type']})**"
                    )

                    st.write(
                        f"{profile['sacks']:.1f} sacks · "
                        f"{profile['interceptions']} INT · "
                        f"{profile['total_tackles']} tackles"
                    )

        st.divider()

        st.subheader("Offensive Starters")

        for position_slot in matchup_offensive_slots:

            away_starter = away_offensive_map.get(position_slot)
            home_starter = home_offensive_map.get(position_slot)

            st.markdown(f"### {position_slot.upper()}")

            away_player_col, home_player_col = st.columns(2)

            with away_player_col:
                with st.container(border=True):
                    st.markdown(f"**{away_team}**")

                    if away_starter:
                        render_offensive_player(
                            away_starter,
                            away_qb_profile,
                            away_qb[2] if away_qb else None,
                            away_rb_profile,
                            away_rb[2] if away_rb else None,
                            away_receiver_profile_map
                        )
                    else:
                        st.markdown("**N/A**")
                        st.caption("No listed starter")

            with home_player_col:
                with st.container(border=True):
                    st.markdown(f"**{home_team}**")

                    if home_starter:
                        render_offensive_player(
                            home_starter,
                            home_qb_profile,
                            home_qb[2] if home_qb else None,
                            home_rb_profile,
                            home_rb[2] if home_rb else None,
                            home_receiver_profile_map
                        )
                    else:
                        st.markdown("**N/A**")
                        st.caption("No listed starter")

        with st.expander("Offensive Depth / Rotation"):

            for position_slot, depth_order in matchup_offensive_depth_rows:

                away_player = away_offensive_depth_map.get(
                    (position_slot, depth_order)
                )

                home_player = home_offensive_depth_map.get(
                    (position_slot, depth_order)
                )

                st.markdown(
                    f"### {position_slot.upper()} · "
                    f"Depth {depth_order}"
                )

                away_depth_col, home_depth_col = st.columns(2)

                with away_depth_col:
                    with st.container(border=True):
                        st.markdown(f"**{away_team}**")

                        if away_player:
                            render_offensive_depth_player(
                                away_player,
                                away_offensive_depth_profile_map
                            )
                        else:
                            st.markdown("**N/A**")
                            st.caption("No listed player")

                with home_depth_col:
                    with st.container(border=True):
                        st.markdown(f"**{home_team}**")

                        if home_player:
                            render_offensive_depth_player(
                                home_player,
                                home_offensive_depth_profile_map
                            )
                        else:
                            st.markdown("**N/A**")
                            st.caption("No listed player")

        st.divider()
        st.subheader("Defensive Starters")

        for position_slot in matchup_defensive_slots:

            away_starter = away_defensive_map.get(position_slot)
            home_starter = home_defensive_map.get(position_slot)

            st.markdown(f"### {position_slot.upper()}")

            away_defense_col, home_defense_col = st.columns(2)

            with away_defense_col:
                with st.container(border=True):
                    st.markdown(f"**{away_team}**")

                    if away_starter:
                        render_defensive_player(
                            away_starter,
                            away_defensive_profile_map
                        )
                    else:
                        st.markdown("**N/A**")
                        st.caption("No listed starter")

            with home_defense_col:
                with st.container(border=True):
                    st.markdown(f"**{home_team}**")

                    if home_starter:
                        render_defensive_player(
                            home_starter,
                            home_defensive_profile_map
                        )
                    else:
                        st.markdown("**N/A**")
                        st.caption("No listed starter")

        with st.expander("Defensive Depth / Rotation"):

            for position_slot, depth_order in matchup_defensive_depth_rows:

                away_player = away_defensive_depth_map.get(
                    (position_slot, depth_order)
                )

                home_player = home_defensive_depth_map.get(
                    (position_slot, depth_order)
                )

                st.markdown(
                    f"### {position_slot.upper()} · "
                    f"Depth {depth_order}"
                )

                away_depth_col, home_depth_col = st.columns(2)

                with away_depth_col:
                    with st.container(border=True):
                        st.markdown(f"**{away_team}**")

                        if away_player:
                            render_defensive_player(
                                away_player[:7],
                                away_defensive_depth_profile_map
                            )
                        else:
                            st.markdown("**N/A**")
                            st.caption("No listed player")

                with home_depth_col:
                    with st.container(border=True):
                        st.markdown(f"**{home_team}**")

                        if home_player:
                            render_defensive_player(
                                home_player[:7],
                                home_defensive_depth_profile_map
                            )
                        else:
                            st.markdown("**N/A**")
                            st.caption("No listed player")

        st.divider()
        st.subheader("Special Teams")

        for position_slot in matchup_special_teams_slots:

            away_starter = away_special_teams_map.get(position_slot)
            home_starter = home_special_teams_map.get(position_slot)

            st.markdown(f"### {position_slot.upper()}")

            away_special_col, home_special_col = st.columns(2)

            with away_special_col:
                with st.container(border=True):
                    st.markdown(f"**{away_team}**")

                    if away_starter:
                        render_special_teams_player(
                            away_starter,
                            away_special_teams_profile_map
                        )
                    else:
                        st.markdown("**N/A**")
                        st.caption("No listed starter")

            with home_special_col:
                with st.container(border=True):
                    st.markdown(f"**{home_team}**")

                    if home_starter:
                        render_special_teams_player(
                            home_starter,
                            home_special_teams_profile_map
                        )
                    else:
                        st.markdown("**N/A**")
                        st.caption("No listed starter")

        with st.expander("Special Teams Depth / Rotation"):

            for position_slot, depth_order in matchup_special_teams_depth_rows:

                away_player = away_special_teams_depth_map.get(
                    (position_slot, depth_order)
                )

                home_player = home_special_teams_depth_map.get(
                    (position_slot, depth_order)
                )

                st.markdown(
                    f"### {position_slot.upper()} · "
                    f"Depth {depth_order}"
                )

                away_depth_col, home_depth_col = st.columns(2)

                with away_depth_col:
                    with st.container(border=True):
                        st.markdown(f"**{away_team}**")

                        if away_player:
                            render_special_teams_player(
                                away_player[:7],
                                away_special_teams_depth_profile_map
                            )
                        else:
                            st.markdown("**N/A**")
                            st.caption("No listed player")

                with home_depth_col:
                    with st.container(border=True):
                        st.markdown(f"**{home_team}**")

                        if home_player:
                            render_special_teams_player(
                                home_player[:7],
                                home_special_teams_depth_profile_map
                            )
                        else:
                            st.markdown("**N/A**")
                            st.caption("No listed player")

    with matchup_tab:

        st.subheader("Power Ratings")

        if away_league_power and home_league_power:

            away_power_col, home_power_col = st.columns(2)

            with away_power_col:
                st.markdown(f"### {away_team}")

                st.metric(
                    "League Rank",
                    f"#{away_league_power['rank']}"
                )

                st.metric(
                    "Power Rating",
                    f"{away_league_power['rating']:+.2f}"
                )

            with home_power_col:
                st.markdown(f"### {home_team}")

                st.metric(
                    "League Rank",
                    f"#{home_league_power['rank']}"
                )

                st.metric(
                    "Power Rating",
                    f"{home_league_power['rating']:+.2f}"
                )

        else:
            st.info(
                "Power ratings will populate once both teams "
                "have completed games this season."
            )

        st.divider()

        matchup_summary = get_matchup_advantage_summary(
            away_team,
            home_team,
            away_matchup_edges,
            home_matchup_edges
        )

        st.subheader("Matchup Advantages")

        if matchup_summary:

            away_adv_col, home_adv_col = st.columns(2)

            with away_adv_col:
                st.markdown(f"### {away_team}")

                if matchup_summary["away_advantages"]:
                    for advantage in matchup_summary["away_advantages"]:
                        st.write(f"• {advantage}")
                else:
                    st.write("No clear matchup advantages.")

            with home_adv_col:
                st.markdown(f"### {home_team}")

                if matchup_summary["home_advantages"]:
                    for advantage in matchup_summary["home_advantages"]:
                        st.write(f"• {advantage}")
                else:
                    st.write("No clear matchup advantages.")

        else:
            st.info(
                "Current-season matchup advantages are not available yet."
            )

        if matchup_prediction_adjustment is not None:

            if matchup_prediction_adjustment > 0.25:
                matchup_lean_team = home_team

            elif matchup_prediction_adjustment < -0.25:
                matchup_lean_team = away_team

            else:
                matchup_lean_team = None

            st.markdown("#### Overall Matchup Lean")

            if matchup_lean_team:
                st.write(matchup_lean_team)
            else:
                st.write("Roughly even")

        st.divider()

        st.subheader("Offense vs Defense")

        render_matchup_table(
            away_team,
            home_team,
            away_offense_vs_home_defense,
            away_matchup_edges
        )

        st.divider()

        render_matchup_table(
            home_team,
            away_team,
            home_offense_vs_away_defense,
            home_matchup_edges
        )

    with game_stats_tab:
        st.subheader("Game Stats")

        if not away_game_team_stats or not home_game_team_stats:
            st.write("Game stats available after completion.")

        else:
            st.markdown(
                f"### {away_team} vs {home_team}"
            )

            metric_col, away_col, home_col = st.columns(
                [1.5, 1, 1]
            )

            with metric_col:
                st.markdown("**Metric**")

            with away_col:
                st.markdown(f"**{away_team}**")

            with home_col:
                st.markdown(f"**{home_team}**")

            st.divider()

            team_stat_rows = [
                (
                    "Total Yards",
                    away_game_team_stats["total_yards"],
                    home_game_team_stats["total_yards"]
                ),
                (
                    "Passing Yards",
                    away_game_team_stats["passing_yards"],
                    home_game_team_stats["passing_yards"]
                ),
                (
                    "Rushing Yards",
                    away_game_team_stats["rushing_yards"],
                    home_game_team_stats["rushing_yards"]
                ),
                (
                    "Yards / Play",
                    away_game_team_stats["yards_per_play"],
                    home_game_team_stats["yards_per_play"]
                ),
                (
                    "First Downs",
                    away_game_team_stats["first_downs"],
                    home_game_team_stats["first_downs"]
                ),
                (
                    "Turnovers",
                    away_game_team_stats["turnovers"],
                    home_game_team_stats["turnovers"]
                ),
                (
                    "3rd Down",
                    away_game_team_stats["third_down_eff"],
                    home_game_team_stats["third_down_eff"]
                ),
                (
                    "Red Zone",
                    away_game_team_stats["red_zone_eff"],
                    home_game_team_stats["red_zone_eff"]
                ),
                (
                    "Possession",
                    away_game_team_stats["possession_time"],
                    home_game_team_stats["possession_time"]
                )
            ]

            for metric, away_value, home_value in team_stat_rows:

                metric_col, away_col, home_col = st.columns(
                    [1.5, 1, 1]
                )

                with metric_col:
                    st.write(metric)

                with away_col:
                    if metric == "Yards / Play":
                        st.write(
                            f"{away_value:.2f}"
                            if away_value is not None
                            else "N/A"
                        )
                    else:
                        st.write(
                            away_value
                            if away_value is not None
                            else "N/A"
                        )

                with home_col:
                    if metric == "Yards / Play":
                        st.write(
                            f"{home_value:.2f}"
                            if home_value is not None
                            else "N/A"
                        )
                    else:
                        st.write(
                            home_value
                            if home_value is not None
                            else "N/A"
                        )

        st.divider()
        st.subheader("Player Box Score")

        render_passing_box_score(
            away_team,
            away_game_player_stats
        )

        render_passing_box_score(
            home_team,
            home_game_player_stats
        )

        st.divider()

        render_rushing_box_score(
            away_team,
            away_game_player_stats
        )

        render_rushing_box_score(
            home_team,
            home_game_player_stats
        )

        st.divider()

        render_receiving_box_score(
            away_team,
            away_game_player_stats
        )

        render_receiving_box_score(
            home_team,
            home_game_player_stats
        )

        st.divider()

        render_fumbles_box_score(
            away_team,
            away_game_player_stats
        )

        render_fumbles_box_score(
            home_team,
            home_game_player_stats
        )

        st.divider()

        render_defensive_box_score(
            away_team,
            away_game_player_stats
        )

        render_defensive_box_score(
            home_team,
            home_game_player_stats
        )

        st.divider()
        st.subheader("Special Teams")

        render_kicking_box_score(
            away_team,
            away_game_player_stats
        )

        render_kicking_box_score(
            home_team,
            home_game_player_stats
        )

        st.divider()

        render_punting_box_score(
            away_team,
            away_game_player_stats
        )

        render_punting_box_score(
            home_team,
            home_game_player_stats
        )

        st.divider()

        render_return_box_score(
            away_team,
            away_game_player_stats
        )

        render_return_box_score(
            home_team,
            home_game_player_stats
        )

    with injuries_tab:
        st.subheader("Injuries")

        away_injury_col, home_injury_col = st.columns(2)

        with away_injury_col:
            st.markdown(f"### {away_team}")

            if not away_injuries:
                st.write("No injuries listed.")

            else:
                away_injury_table = []

                for injury in away_injuries:
                    away_injury_table.append(
                        {
                            "Player": injury["player_name"],
                            "Pos": injury["position"] or "—",
                            "Status": injury["status"] or "—",
                            "Injury": (
                                injury["injury_type"]
                                or "Undisclosed"
                            ),
                            "Return": (
                                str(injury["return_date"])
                                if injury["return_date"]
                                else "—"
                            )
                        }
                    )

                st.dataframe(
                    away_injury_table,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Player": st.column_config.TextColumn(
                            "Player",
                            width="medium"
                        ),
                        "Pos": st.column_config.TextColumn(
                            "Pos",
                            width="small"
                        ),
                        "Status": st.column_config.TextColumn(
                            "Status",
                            width="medium"
                        ),
                        "Injury": st.column_config.TextColumn(
                            "Injury",
                            width="medium"
                        ),
                        "Return": st.column_config.TextColumn(
                            "Return",
                            width="small"
                        )
                    }
                )

            if away_injury_updated:
                st.caption(
                    f"Updated: {away_injury_updated.strftime('%b %d, %Y %I:%M %p')}"
                )

        with home_injury_col:
            st.markdown(f"### {home_team}")

            if not home_injuries:
                st.write("No injuries listed.")

            else:
                home_injury_table = []

                for injury in home_injuries:
                    home_injury_table.append(
                        {
                            "Player": injury["player_name"],
                            "Pos": injury["position"] or "—",
                            "Status": injury["status"] or "—",
                            "Injury": (
                                injury["injury_type"]
                                or "Undisclosed"
                            ),
                            "Return": (
                                str(injury["return_date"])
                                if injury["return_date"]
                                else "—"
                            )
                        }
                    )

                st.dataframe(
                    home_injury_table,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Player": st.column_config.TextColumn(
                            "Player",
                            width="medium"
                        ),
                        "Pos": st.column_config.TextColumn(
                            "Pos",
                            width="small"
                        ),
                        "Status": st.column_config.TextColumn(
                            "Status",
                            width="medium"
                        ),
                        "Injury": st.column_config.TextColumn(
                            "Injury",
                            width="medium"
                        ),
                        "Return": st.column_config.TextColumn(
                            "Return",
                            width="small"
                        )
                    }
                )

            if home_injury_updated:
                st.caption(
                    f"Updated: {home_injury_updated.strftime('%b %d, %Y %I:%M %p')}"
                )

        if away_injury_changes or home_injury_changes:

            st.divider()
            st.markdown("### Recent Changes")

            away_change_col, home_change_col = st.columns(2)

            with away_change_col:
                st.markdown(f"#### {away_team}")

                if not away_injury_changes:
                    st.write("No recent changes.")

                else:
                    for change in away_injury_changes:

                        if change["change_type"] == "status_change":
                            st.write(
                                f"**{change['player_name']}** — "
                                f"{change['old_status']} → "
                                f"{change['new_status']}"
                            )

                        elif change["change_type"] == "added":
                            st.write(
                                f"**{change['player_name']}** — "
                                f"Added to report "
                                f"({change['new_status']})"
                            )

                        elif change["change_type"] == "removed":
                            st.write(
                                f"**{change['player_name']}** — "
                                f"No longer listed"
                            )

            with home_change_col:
                st.markdown(f"#### {home_team}")

                if not home_injury_changes:
                    st.write("No recent changes.")

                else:
                    for change in home_injury_changes:

                        if change["change_type"] == "status_change":
                            st.write(
                                f"**{change['player_name']}** — "
                                f"{change['old_status']} → "
                                f"{change['new_status']}"
                            )

                        elif change["change_type"] == "added":
                            st.write(
                                f"**{change['player_name']}** — "
                                f"Added to report "
                                f"({change['new_status']})"
                            )

                        elif change["change_type"] == "removed":
                            st.write(
                                f"**{change['player_name']}** — "
                                f"No longer listed"
                            )

    with weather_tab:
        st.subheader("Weather")

        st.markdown(f"### {venue}")

        if venue_type == "indoor":

            st.info(
                "Indoor venue — outdoor weather is not expected "
                "to materially affect game conditions."
            )

        else:

            if venue_type == "retractable":
                st.info(
                    "Retractable-roof venue. Outdoor conditions are shown "
                    "when available, but actual game conditions will depend "
                    "on roof status."
                )

            if not game_weather:
                st.info(
                    "Game-time forecast is not available yet. "
                    "Weather data will begin populating when the game "
                    "enters the forecast window."
                )

            else:
                display_weather_forecast(game_weather)

    with betting_tab:
        st.subheader("Betting")

        if not game_betting:
            st.info("No betting market is currently available for this game.")

        else:
            provider_name = game_betting["provider_name"] or "Market"

            st.caption(f"Odds via {provider_name}")

            # -------------------------
            # CURRENT MARKET
            # -------------------------

            st.markdown("### Current Market")

            spread_col, moneyline_col, total_col = st.columns(3)

            with spread_col:
                st.markdown("#### Spread")

                if game_betting["away_spread"] is not None:
                    st.write(
                        f"**{away_team}:** "
                        f"{float(game_betting['away_spread']):+g} "
                        f"({game_betting['away_spread_odds'] or '—'})"
                    )
                else:
                    st.write(f"**{away_team}:** OFF")

                if game_betting["home_spread"] is not None:
                    st.write(
                        f"**{home_team}:** "
                        f"{float(game_betting['home_spread']):+g} "
                        f"({game_betting['home_spread_odds'] or '—'})"
                    )
                else:
                    st.write(f"**{home_team}:** OFF")

            with moneyline_col:
                st.markdown("#### Moneyline")

                if game_betting["away_moneyline"] is not None:
                    st.write(
                        f"**{away_team}:** "
                        f"{int(game_betting['away_moneyline']):+d}"
                    )
                else:
                    st.write(f"**{away_team}:** —")

                if game_betting["home_moneyline"] is not None:
                    st.write(
                        f"**{home_team}:** "
                        f"{int(game_betting['home_moneyline']):+d}"
                    )
                else:
                    st.write(f"**{home_team}:** —")

            with total_col:
                st.markdown("#### Total")

                if game_betting["total"] is not None:
                    st.write(
                        f"**O/U:** "
                        f"{float(game_betting['total']):.1f}"
                    )

                    st.write(
                        f"Over: {game_betting['over_odds'] or '—'}"
                    )

                    st.write(
                        f"Under: {game_betting['under_odds'] or '—'}"
                    )
                else:
                    st.write("Total: OFF")

            # -------------------------
            # IMPLIED PROBABILITY
            # -------------------------

            st.divider()
            st.markdown("### Market Win Probability")
            st.caption("Moneyline-implied probability with sportsbook vig removed.")

            away_prob_col, home_prob_col = st.columns(2)

            with away_prob_col:
                if away_no_vig_probability is not None:
                    st.metric(
                        away_team,
                        f"{away_no_vig_probability * 100:.1f}%"
                    )
                else:
                    st.metric(away_team, "—")

            with home_prob_col:
                if home_no_vig_probability is not None:
                    st.metric(
                        home_team,
                        f"{home_no_vig_probability * 100:.1f}%"
                    )
                else:
                    st.metric(home_team, "—")

            # -------------------------
            # OPENING VS CURRENT
            # -------------------------

            st.divider()
            st.markdown("### Opening vs Current")

            market_rows = [
                {
                    "Market": f"{away_team} Spread",
                    "Opening": (
                        f"{float(game_betting['opening_away_spread']):+g}"
                        if game_betting["opening_away_spread"] is not None
                        else "—"
                    ),
                    "Current": (
                        f"{float(game_betting['away_spread']):+g}"
                        if game_betting["away_spread"] is not None
                        else "OFF"
                    )
                },
                {
                    "Market": f"{home_team} Spread",
                    "Opening": (
                        f"{float(game_betting['opening_home_spread']):+g}"
                        if game_betting["opening_home_spread"] is not None
                        else "—"
                    ),
                    "Current": (
                        f"{float(game_betting['home_spread']):+g}"
                        if game_betting["home_spread"] is not None
                        else "OFF"
                    )
                },
                {
                    "Market": f"{away_team} Moneyline",
                    "Opening": (
                        f"{int(game_betting['opening_away_moneyline']):+d}"
                        if game_betting["opening_away_moneyline"] is not None
                        else "—"
                    ),
                    "Current": (
                        f"{int(game_betting['away_moneyline']):+d}"
                        if game_betting["away_moneyline"] is not None
                        else "—"
                    )
                },
                {
                    "Market": f"{home_team} Moneyline",
                    "Opening": (
                        f"{int(game_betting['opening_home_moneyline']):+d}"
                        if game_betting["opening_home_moneyline"] is not None
                        else "—"
                    ),
                    "Current": (
                        f"{int(game_betting['home_moneyline']):+d}"
                        if game_betting["home_moneyline"] is not None
                        else "—"
                    )
                },
                {
                    "Market": "Total",
                    "Opening": (
                        f"{float(game_betting['opening_total']):.1f}"
                        if game_betting["opening_total"] is not None
                        else "—"
                    ),
                    "Current": (
                        f"{float(game_betting['total']):.1f}"
                        if game_betting["total"] is not None
                        else "OFF"
                    )
                }
            ]

            st.dataframe(
                market_rows,
                use_container_width=True,
                hide_index=True
            )

            st.caption(
                f"Snapshot captured: "
                f"{game_betting['captured_at'].strftime('%b %d, %Y %I:%M %p')}"
            )

    with history_tab:
        st.subheader("Head-to-Head")

        if head_to_head:

            away_h2h_wins = 0
            home_h2h_wins = 0
            ties = 0

            away_margin_total = 0

            history_rows = []

            for (
                h2h_season,
                h2h_date,
                h2h_away_team,
                h2h_away_score,
                h2h_home_team,
                h2h_home_score
            ) in head_to_head:

                # -------------------------
                # WINNER
                # -------------------------

                if h2h_away_score > h2h_home_score:
                    winner = h2h_away_team

                elif h2h_home_score > h2h_away_score:
                    winner = h2h_home_team

                else:
                    winner = "Tie"

                # -------------------------
                # SELECTED TEAM H2H WINS
                # -------------------------

                if winner == away_team:
                    away_h2h_wins += 1

                elif winner == home_team:
                    home_h2h_wins += 1

                else:
                    ties += 1

                # -------------------------
                # MARGIN FROM AWAY TEAM'S
                # PERSPECTIVE
                # -------------------------

                if h2h_away_team == away_team:
                    away_team_score = h2h_away_score
                    home_team_score = h2h_home_score

                else:
                    away_team_score = h2h_home_score
                    home_team_score = h2h_away_score

                away_margin_total += (
                    away_team_score - home_team_score
                )

                # -------------------------
                # DISPLAY ROW
                # -------------------------

                eastern_date = h2h_date.astimezone(
                    ZoneInfo("America/New_York")
                )

                history_rows.append(
                    {
                        "Date": eastern_date.strftime(
                            "%b %d, %Y"
                        ),
                        "Season": h2h_season,
                        "Matchup": (
                            f"{h2h_away_team} @ "
                            f"{h2h_home_team}"
                        ),
                        "Score": (
                            f"{h2h_away_score} - "
                            f"{h2h_home_score}"
                        ),
                        "Winner": winner
                    }
                )

            # -------------------------
            # SUMMARY
            # -------------------------

            games_count = len(head_to_head)

            average_away_margin = (
                away_margin_total / games_count
            )

            st.markdown(
                f"### Last {games_count} Meetings"
            )

            summary_col_1, summary_col_2, summary_col_3 = (
                st.columns(3)
            )

            with summary_col_1:
                st.metric(
                    f"{away_team} Wins",
                    away_h2h_wins
                )

            with summary_col_2:
                st.metric(
                    f"{home_team} Wins",
                    home_h2h_wins
                )

            with summary_col_3:

                away_abbr = TEAM_ABBREVIATIONS.get(
                    away_team,
                    away_team
                )

                home_abbr = TEAM_ABBREVIATIONS.get(
                    home_team,
                    home_team
                )

                if average_away_margin > 0:
                    margin_text = (
                        f"{away_abbr} "
                        f"+{average_away_margin:.1f}"
                    )

                elif average_away_margin < 0:
                    margin_text = (
                        f"{home_abbr} "
                        f"+{abs(average_away_margin):.1f}"
                    )

                else:
                    margin_text = "EVEN"

                st.metric(
                    "Average Margin",
                    margin_text
                )

            if ties:
                st.caption(
                    f"Ties in sample: {ties}"
                )

            st.dataframe(
                history_rows,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Date": st.column_config.TextColumn(
                        "Date",
                        width="small"
                    ),
                    "Season": st.column_config.NumberColumn(
                        "Season",
                        format="%d",
                        width="small"
                    ),
                    "Matchup": st.column_config.TextColumn(
                        "Matchup",
                        width="large"
                    ),
                    "Score": st.column_config.TextColumn(
                        "Score",
                        width="small"
                    ),
                    "Winner": st.column_config.TextColumn(
                        "Winner",
                        width="medium"
                    )
                }
            )

        else:
            st.info(
                "No previous meetings found."
            )

    st.stop()

# -------------------------
# POWER RANKINGS PAGE
# -------------------------

if st.session_state["page"] == "power_rankings":

    st.title(f"NFL {DISPLAY_SEASON} Power Rankings")

    ranking_week = st.selectbox(
        "Rankings entering Week",
        list(range(1, 19)),
        key="power_ranking_week"
    )

    cursor.execute(
        """
        SELECT MIN(game_date)
        FROM nfl_games
        WHERE season = %s
          AND week = %s;
        """,
        (
            DISPLAY_SEASON,
            ranking_week
        )
    )

    ranking_cutoff_date = cursor.fetchone()[0]

    if ranking_cutoff_date is None:
        st.info(
            "No games were found for this week."
        )

    else:
        league_power_rankings = get_league_power_rankings(
            cursor,
            DISPLAY_SEASON,
            ranking_cutoff_date
        )

        st.caption(
            f"Ratings entering Week {ranking_week}. "
            "Only games played before this week are included."
        )

        st.caption(
            "0.00 represents league-average performance. "
            "Positive ratings indicate above-average performance; "
            "negative ratings indicate below-average performance."
        )

        if not league_power_rankings:
            st.info(
                "Power rankings are not available yet. "
                "Teams must complete games before receiving a rating."
            )

        else:
            ranking_rows = []

            for team in league_power_rankings:

                cursor.execute(
                    """
                    SELECT team_id
                    FROM (
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
                    ) teams
                    WHERE team_name = %s
                    LIMIT 1;
                    """,
                    (
                        DISPLAY_SEASON,
                        DISPLAY_SEASON,
                        team["team"]
                    )
                )

                team_id_row = cursor.fetchone()

                team_record = "—"

                if team_id_row:
                    team_record = get_team_record_before_date(
                        cursor,
                        team_id_row[0],
                        DISPLAY_SEASON,
                        ranking_cutoff_date
                    )

                ranking_rows.append(
                    {
                        "Rank": team["rank"],
                        "Team": team["team"],
                        "Record": team_record,
                        "Power Rating": team["rating"]
                    }
                )

            rankings_df = pd.DataFrame(
                ranking_rows
            )

            st.dataframe(
                rankings_df,
                hide_index=True,
                width="stretch",
                column_config={
                    "Rank": st.column_config.NumberColumn(
                        "Rank",
                        format="#%d",
                        width="small"
                    ),
                    "Team": st.column_config.TextColumn(
                        "Team",
                        width="large"
                    ),
                    "Record": st.column_config.TextColumn(
                        "Record",
                        width="small"
                    ),
                    "Power Rating": st.column_config.NumberColumn(
                        "Power Rating",
                        format="%+.2f",
                        width="medium"
                    )
                }
            )

    st.stop()

# -------------------------
# SCHEDULE PAGE
# -------------------------

if st.session_state["page"] == "schedule":

    st.subheader(f"Week {selected_week}")
    st.write(f"{len(games)} games")

    for game in games:
        (
            game_id,
            game_date,
            away_team,
            home_team,
            away_team_id,
            home_team_id,
            away_logo,
            home_logo,
            away_record,
            home_record,
            away_home_record,
            away_road_record,
            home_home_record,
            home_road_record,
            venue,
            venue_type,
            away_score,
            home_score,
            game_state,
            game_status,
            completed,
            away_conference,
            away_division_record,
            away_conference_record,
            away_streak,
            home_conference,
            home_division_record,
            home_conference_record,
            home_streak
        ) = game

        eastern_time = game_date.astimezone(
            ZoneInfo("America/New_York")
        )

        with st.container(border=True):

            # -------------------------
            # GAME STATUS
            # -------------------------

            if game_status == "Canceled":
                st.caption("CANCELED")

            elif game_state == "in":
                st.caption("LIVE")

            elif completed:
                st.caption("FINAL")

            else:
                st.caption("UPCOMING")

            # -------------------------
            # TEAMS / SCORE
            # -------------------------

            away_col, middle_col, home_col = st.columns(
                [2, 1, 2]
            )

            with away_col:
                render_matchup_team(
                    away_team,
                    away_logo,
                    away_score
                    if game_state == "in" or completed
                    else None,
                    logo_size=80
                )

            with middle_col:
                st.markdown("### @")

            with home_col:
                render_matchup_team(
                    home_team,
                    home_logo,
                    home_score
                    if game_state == "in" or completed
                    else None,
                    logo_size=80
                )


            # -------------------------
            # DATE / LIVE STATUS
            # -------------------------

            if game_status == "Canceled":
                st.write("Game canceled")

            elif game_state == "in":
                st.write(
                    game_status or "In Progress"
                )

            if game_status == "Canceled":
                st.write("Game canceled")

            elif game_state == "in":
                st.write(
                    game_status or "In Progress"
                )

            elif not completed:
                st.write(
                    eastern_time.strftime(
                        "%A, %B %d · %I:%M %p %Z"
                    )
                )

            st.write(venue)

            if st.button(
                "View Game",
                key=f"view_{game_id}"
            ):
                st.session_state["selected_game"] = game_id
                st.session_state["page"] = "game"
                st.rerun()

cursor.close()
connection.close()
