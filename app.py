from datetime import timedelta
from db import get_connection
import os
from dotenv import load_dotenv
import streamlit as st
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

from components import (
    render_stat_section_spacer,
    render_offensive_player,
    render_defensive_player,
    render_special_teams_player,
    render_offensive_depth_player,
    build_matchup_summary,
    possessive,
    render_matchup_table,
    render_responsive_comparison_table,
    render_passing_box_score,
    render_rushing_box_score,
    render_receiving_box_score,
    render_defensive_box_score,
    render_kicking_box_score,
    render_punting_box_score,
    render_return_box_score,
    render_fumbles_box_score,
    get_weather_description,
    display_weather_forecast,
    render_team_logo,
    render_matchup_team,
)

from data import (
    get_last_three,
    get_head_to_head,
    get_team_scoring_profile,
    get_team_boxscore_profile,
    get_team_defensive_profile,
    get_offensive_starters,
    get_defensive_starters,
    get_special_teams_starters,
    get_qb_profile,
    get_qb_profiles,
    get_rb_profile,
    get_rb_profiles,
    get_receiving_profiles,
    get_defensive_player_profiles,
    get_special_teams_profiles,
    get_depth_players_bulk,
    get_league_matchup_baselines,
    get_game_team_stats,
    get_game_player_stats,
    get_game_injuries,
    get_injury_changes,
    get_latest_injury_snapshot_time,
    get_game_weather,
    get_latest_betting_snapshot,
    get_team_record_before_date,
    get_league_records_before_date,
    get_league_power_rankings,
)

load_dotenv()

LIVE_REFRESH_ENABLED = (
    os.getenv(
        "LIVE_REFRESH_ENABLED",
        "false"
    ).lower()
    == "true"
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

connection = get_connection()

if "page" not in st.session_state:
    st.session_state["page"] = "home"

if "selected_game" not in st.session_state:
    st.session_state["selected_game"] = None


nav_home, nav_schedule, nav_power = st.columns(3)

with nav_home:
    if st.button(
        "Home",
        key="nav_home",
        width="stretch"
    ):
        st.session_state["page"] = "home"
        st.session_state["selected_game"] = None
        st.rerun()

with nav_schedule:
    if st.button(
        "Schedule",
        key="nav_schedule",
        width="stretch"
    ):
        st.session_state["page"] = "schedule"
        st.session_state["selected_game"] = None
        st.rerun()

with nav_power:
    if st.button(
        "Power Rankings",
        key="nav_power_rankings",
        width="stretch"
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

    if LIVE_REFRESH_ENABLED:
        st.caption(
            "Live data refresh enabled."
        )
    else:
        st.caption(
            "Portfolio preview · Data is shown from the latest available snapshot."
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
                width="stretch"
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
                width="stretch"
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
        width="stretch"
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

    profile_game_date = (
        game_date + timedelta(seconds=1)
        if completed
        else game_date
    )

    if "game_section" not in st.session_state:
        st.session_state["game_section"] = "Overview"

    selected_game_section = st.session_state["game_section"]

    away_last_three = get_last_three(
        cursor,
        away_team_id,
        DISPLAY_SEASON,
        profile_game_date
    )

    home_last_three = get_last_three(
        cursor,
        home_team_id,
        DISPLAY_SEASON,
        profile_game_date
    )

    head_to_head = None

    if selected_game_section == "History":
        head_to_head = get_head_to_head(
            cursor,
            away_team_id,
            home_team_id,
            game_date
        )

    if selected_game_section in (
        "Overview",
        "Prediction",
        "Team Stats",
        "Matchup"
    ):
        away_scoring = get_team_scoring_profile(
            cursor,
            away_team_id,
            DISPLAY_SEASON,
            profile_game_date
        )

        home_scoring = get_team_scoring_profile(
            cursor,
            home_team_id,
            DISPLAY_SEASON,
            profile_game_date
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
            profile_game_date
        )

        home_boxscore = get_team_boxscore_profile(
            cursor,
            home_team_id,
            DISPLAY_SEASON,
            profile_game_date
        )

        away_defense = get_team_defensive_profile(
            cursor,
            away_team_id,
            DISPLAY_SEASON,
            profile_game_date
        )

        home_defense = get_team_defensive_profile(
            cursor,
            home_team_id,
            DISPLAY_SEASON,
            profile_game_date
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

    away_game_team_stats = None
    home_game_team_stats = None

    away_game_player_stats = None
    home_game_player_stats = None

    away_injuries = None
    home_injuries = None

    away_injury_changes = None
    home_injury_changes = None

    away_injury_updated = None
    home_injury_updated = None

    game_weather = None
    game_betting = None


    if selected_game_section == "Game Stats":
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


    if selected_game_section == "Injuries":
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


    if selected_game_section == "Weather":
        game_weather = get_game_weather(
            cursor,
            game_id
        )


    if selected_game_section in (
        "Overview",
        "Betting",
        "Prediction"
    ):
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

    if selected_game_section == "Players":
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

        receiver_player_ids = list({
            receiver[2]
            for receiver in (
                away_receivers
                + home_receivers
            )
            if receiver[2] is not None
        })

        receiver_profile_map = get_receiving_profiles(
            cursor,
            receiver_player_ids,
            DISPLAY_SEASON,
            game_date
        )

        away_receiver_profiles = [
            (
                receiver,
                receiver_profile_map.get(
                    receiver[2]
                )
            )
            for receiver in away_receivers
        ]

        home_receiver_profiles = [
            (
                receiver,
                receiver_profile_map.get(
                    receiver[2]
                )
            )
            for receiver in home_receivers
        ]

        away_receiver_profile_map = {
            receiver[2]: profile
            for receiver, profile
            in away_receiver_profiles
        }

        home_receiver_profile_map = {
            receiver[2]: profile
            for receiver, profile
            in home_receiver_profiles
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

        defensive_player_ids = list({
            starter[2]
            for starter in (
                away_defensive_starters
                + home_defensive_starters
            )
            if starter[2] is not None
        })

        defensive_profile_map = (
            get_defensive_player_profiles(
                cursor,
                defensive_player_ids,
                DISPLAY_SEASON,
                game_date
            )
        )

        away_defensive_profile_map = {
            starter[2]: defensive_profile_map.get(
                starter[2]
            )
            for starter in away_defensive_starters
        }

        home_defensive_profile_map = {
            starter[2]: defensive_profile_map.get(
                starter[2]
            )
            for starter in home_defensive_starters
        }


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

        special_teams_player_ids = list({
            starter[2]
            for starter in (
                away_special_teams
                + home_special_teams
            )
            if starter[2] is not None
        })

        special_teams_profile_map = (
            get_special_teams_profiles(
                cursor,
                special_teams_player_ids,
                DISPLAY_SEASON,
                game_date
            )
        )

        away_special_teams_profile_map = {
            starter[2]: special_teams_profile_map.get(
                starter[2]
            )
            for starter in away_special_teams
        }

        home_special_teams_profile_map = {
            starter[2]: special_teams_profile_map.get(
                starter[2]
            )
            for starter in home_special_teams
        }

        matchup_special_teams_slots = [
            slot
            for slot in SPECIAL_TEAMS_DISPLAY_ORDER
            if (
                slot in away_special_teams_map
                or slot in home_special_teams_map
            )
        ]

    if selected_game_section == "Players":
        depth_map = get_depth_players_bulk(
            cursor,
            [
                away_team_id,
                home_team_id
            ]
        )

        away_offensive_depth = depth_map.get(
            (away_team_id, "OFF"),
            []
        )

        home_offensive_depth = depth_map.get(
            (home_team_id, "OFF"),
            []
        )

        away_defensive_depth = depth_map.get(
            (away_team_id, "DEF"),
            []
        )

        home_defensive_depth = depth_map.get(
            (home_team_id, "DEF"),
            []
        )

        away_special_teams_depth = depth_map.get(
            (away_team_id, "ST"),
            []
        )

        home_special_teams_depth = depth_map.get(
            (home_team_id, "ST"),
            []
        )


        all_offensive_depth = (
            away_offensive_depth
            + home_offensive_depth
        )

        qb_player_ids = list({
            player[2]
            for player in all_offensive_depth
            if (
                player[1] == "QB"
                and player[2] is not None
            )
        })

        rb_player_ids = list({
            player[2]
            for player in all_offensive_depth
            if (
                player[1] == "RB"
                and player[2] is not None
            )
        })

        receiver_depth_player_ids = list({
            player[2]
            for player in all_offensive_depth
            if (
                player[1] in ("WR", "TE")
                and player[2] is not None
            )
        })

        qb_depth_profiles = get_qb_profiles(
            cursor,
            qb_player_ids,
            DISPLAY_SEASON,
            game_date
        )

        rb_depth_profiles = get_rb_profiles(
            cursor,
            rb_player_ids,
            DISPLAY_SEASON,
            game_date
        )

        receiver_depth_profiles = get_receiving_profiles(
            cursor,
            receiver_depth_player_ids,
            DISPLAY_SEASON,
            game_date
        )


        def get_offensive_depth_profile(player):
            player_id = player[2]
            position = player[1]

            if position == "QB":
                return qb_depth_profiles.get(
                    player_id
                )

            if position == "RB":
                return rb_depth_profiles.get(
                    player_id
                )

            if position in ("WR", "TE"):
                return receiver_depth_profiles.get(
                    player_id
                )

            return None


        away_offensive_depth_profile_map = {
            player[2]: get_offensive_depth_profile(
                player
            )
            for player in away_offensive_depth
        }

        home_offensive_depth_profile_map = {
            player[2]: get_offensive_depth_profile(
                player
            )
            for player in home_offensive_depth
        }

        defensive_depth_player_ids = list({
            player[2]
            for player in (
                away_defensive_depth
                + home_defensive_depth
            )
            if player[2] is not None
        })

        defensive_depth_profiles = (
            get_defensive_player_profiles(
                cursor,
                defensive_depth_player_ids,
                DISPLAY_SEASON,
                game_date
            )
        )

        away_defensive_depth_profile_map = {
            player[2]: defensive_depth_profiles.get(
                player[2]
            )
            for player in away_defensive_depth
        }

        home_defensive_depth_profile_map = {
            player[2]: defensive_depth_profiles.get(
                player[2]
            )
            for player in home_defensive_depth
        }

        special_teams_depth_player_ids = list({
            player[2]
            for player in (
                away_special_teams_depth
                + home_special_teams_depth
            )
            if player[2] is not None
        })

        special_teams_depth_profiles = (
            get_special_teams_profiles(
                cursor,
                special_teams_depth_player_ids,
                DISPLAY_SEASON,
                game_date
            )
        )

        away_special_teams_depth_profile_map = {
            player[2]: special_teams_depth_profiles.get(
                player[2]
            )
            for player in away_special_teams_depth
        }

        home_special_teams_depth_profile_map = {
            player[2]: special_teams_depth_profiles.get(
                player[2]
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

    if st.button("← Back to Schedule", key="back_to_schedule_1"):
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


    st.segmented_control(
        "Game Section",
        [
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
        ],
        key="game_section"
    )

    if selected_game_section == "Overview":
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

    if selected_game_section == "Prediction":
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
            width="stretch"
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
                width="stretch"
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
                    f"Model comparison will populate once enough "
                    f"{DISPLAY_SEASON} game data is available to generate a prediction."
                )

            else:
                st.info(
                    "Market comparison is unavailable because "
                    "moneyline odds are not available for this game."
                )

    if selected_game_section == "Team Stats":
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
                    away_team: str(
                        away_scoring["games_played"]
                    ),
                    home_team: str(
                        home_scoring["games_played"]
                    )
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
                width="stretch",
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
                width="stretch",
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
                    away_team: str(
                        away_defense["defensive_touchdowns"]
                    ),
                    home_team: str(
                        home_defense["defensive_touchdowns"]
                    )
                }
            ]

            st.dataframe(
                defense_rows,
                width="stretch",
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
                width="stretch",
                hide_index=True
            )

        else:
            st.info(
                f"Team statistics will populate once both teams "
                f"have completed games in the {DISPLAY_SEASON} season."
            )

    if selected_game_section == "Players":

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

    if selected_game_section in (
        "Players",
        "Matchup"
    ):
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


    if selected_game_section == "Players":
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

    if selected_game_section == "Matchup":

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

    if selected_game_section == "Game Stats":
        st.subheader("Game Stats")

        if not away_game_team_stats or not home_game_team_stats:
            st.write("Game stats available after completion.")

        else:
            st.markdown(
                f"### {away_team} vs {home_team}"
            )

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

            formatted_team_stat_rows = []

            for metric, away_value, home_value in team_stat_rows:

                if metric == "Yards / Play":
                    away_display = (
                        f"{away_value:.2f}"
                        if away_value is not None
                        else "N/A"
                    )

                    home_display = (
                        f"{home_value:.2f}"
                        if home_value is not None
                        else "N/A"
                    )

                else:
                    away_display = (
                        str(away_value)
                        if away_value is not None
                        else "N/A"
                    )

                    home_display = (
                        str(home_value)
                        if home_value is not None
                        else "N/A"
                    )

                formatted_team_stat_rows.append(
                    [
                        metric,
                        away_display,
                        home_display
                    ]
                )

            render_responsive_comparison_table(
                headers=[
                    "Metric",
                    away_team,
                    home_team
                ],
                rows=formatted_team_stat_rows,
                mobile_labels=[
                    away_team,
                    home_team
                ]
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

        render_stat_section_spacer()

        render_rushing_box_score(
            away_team,
            away_game_player_stats
        )

        render_rushing_box_score(
            home_team,
            home_game_player_stats
        )

        render_stat_section_spacer()

        render_receiving_box_score(
            away_team,
            away_game_player_stats
        )

        render_receiving_box_score(
            home_team,
            home_game_player_stats
        )

        render_stat_section_spacer()

        render_fumbles_box_score(
            away_team,
            away_game_player_stats
        )

        render_fumbles_box_score(
            home_team,
            home_game_player_stats
        )

        render_stat_section_spacer()

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

        render_stat_section_spacer()

        render_punting_box_score(
            away_team,
            away_game_player_stats
        )

        render_punting_box_score(
            home_team,
            home_game_player_stats
        )

        render_stat_section_spacer()

        render_return_box_score(
            away_team,
            away_game_player_stats
        )

        render_return_box_score(
            home_team,
            home_game_player_stats
        )

    if selected_game_section == "Injuries":
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
                    width="stretch",
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
                    width="stretch",
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

    if selected_game_section == "Weather":
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

    if selected_game_section == "Betting":
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
                width="stretch",
                hide_index=True
            )

            st.caption(
                f"Snapshot captured: "
                f"{game_betting['captured_at'].strftime('%b %d, %Y %I:%M %p')}"
            )

    if selected_game_section == "History":
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
                width="stretch",
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
            league_records = get_league_records_before_date(
            cursor,
            DISPLAY_SEASON,
            ranking_cutoff_date
            )

            ranking_rows = []

            for team in league_power_rankings:

                team_record = league_records.get(
                    team["team_id"],
                    "—"
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
