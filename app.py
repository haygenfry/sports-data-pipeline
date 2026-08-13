import streamlit as st
import psycopg2
from zoneinfo import ZoneInfo

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

connection = psycopg2.connect(
    host="localhost",
    port=5432,
    database="nfl_data",
    user="nfl_user",
    password="nfl_password"
)

st.title("NFL 2026 Schedule")

selected_week = st.selectbox(
    "Select Week",
    list(range(1, 19))
)

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
    (2026, selected_week)
)

games = cursor.fetchall()

if "selected_game" not in st.session_state:
    st.session_state["selected_game"] = None

# -------------------------
# GAME DETAIL PAGE
# -------------------------

if st.session_state["selected_game"]:

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
        2026,
        game_date
    )

    home_last_three = get_last_three(
        cursor,
        home_team_id,
        2026,
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
        2026,
        game_date
    )

    home_scoring = get_team_scoring_profile(
        cursor,
        home_team_id,
        2026,
        game_date
    )

    if st.button("← Back to Schedule"):
        st.session_state["selected_game"] = None
        st.rerun()

    st.title(f"{away_team} at {home_team}")

    away_col, middle_col, home_col = st.columns([2, 1, 2])

    with away_col:
        st.image(away_logo, width=120)
        st.subheader(away_team)

    with middle_col:
        st.markdown("## @")

    with home_col:
        st.image(home_logo, width=120)
        st.subheader(home_team)

    eastern_time = game_date.astimezone(
        ZoneInfo("America/New_York")
    )

    st.write(
        eastern_time.strftime(
            "%A, %B %d · %I:%M %p %Z"
        )
    )

    st.write(venue)

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
        team_stats_tab,
        players_tab,
        matchup_tab,
        injuries_tab,
        weather_tab,
        betting_tab,
        history_tab
    ) = st.tabs([
        "Overview",
        "Team Stats",
        "Players",
        "Matchup",
        "Injuries",
        "Weather",
        "Betting",
        "History"
    ])

    with overview_tab:
        st.subheader("Game Overview")
        st.write("Prediction and matchup summary coming soon.")

    with team_stats_tab:
        st.subheader("Team Stats")

        away_stats_col, home_stats_col = st.columns(2)

        with away_stats_col:
            st.markdown(f"### {away_team}")

            if away_scoring:
                st.write(f"Games Played: {away_scoring['games_played']}")
                st.write(f"Points/Game: {away_scoring['ppg']:.1f}")
                st.write(f"Points Allowed/Game: {away_scoring['ppg_allowed']:.1f}")
                st.write(f"Scoring Margin/Game: {away_scoring['scoring_margin']:+.1f}")
                st.write(f"Win %: {away_scoring['win_pct']:.3f}")

                if away_scoring["home_ppg"] is not None:
                    st.write(f"Home PPG: {away_scoring['home_ppg']:.1f}")

                if away_scoring["road_ppg"] is not None:
                    st.write(f"Road PPG: {away_scoring['road_ppg']:.1f}")

                st.write(f"Last 3 PPG: {away_scoring['last_three_ppg']:.1f}")
                st.write(
                    f"Last 3 PPG Allowed: "
                    f"{away_scoring['last_three_ppg_allowed']:.1f}"
                )

            else:
                st.write("No 2026 games played.")

        with home_stats_col:
            st.markdown(f"### {home_team}")

            if home_scoring:
                st.write(f"Games Played: {home_scoring['games_played']}")
                st.write(f"Points/Game: {home_scoring['ppg']:.1f}")
                st.write(f"Points Allowed/Game: {home_scoring['ppg_allowed']:.1f}")
                st.write(f"Scoring Margin/Game: {home_scoring['scoring_margin']:+.1f}")
                st.write(f"Win %: {home_scoring['win_pct']:.3f}")

                if home_scoring["home_ppg"] is not None:
                    st.write(f"Home PPG: {home_scoring['home_ppg']:.1f}")

                if home_scoring["road_ppg"] is not None:
                    st.write(f"Road PPG: {home_scoring['road_ppg']:.1f}")

                st.write(f"Last 3 PPG: {home_scoring['last_three_ppg']:.1f}")
                st.write(
                    f"Last 3 PPG Allowed: "
                    f"{home_scoring['last_three_ppg_allowed']:.1f}"
                )

            else:
                st.write("No 2026 games played.")

    with players_tab:
        st.subheader("Players")
        st.write("Starters, key players, and player statistics coming soon.")

    with matchup_tab:
        st.subheader("Matchup")
        st.write("Matchup advantages and team comparisons coming soon.")

    with injuries_tab:
        st.subheader("Injuries")
        st.write("Injury reports coming soon.")

    with weather_tab:
        st.subheader("Weather")
        st.write("Game-day weather information coming soon.")

    with betting_tab:
        st.subheader("Betting")
        st.write("Lines and implied probabilities coming soon.")

    with history_tab:
        st.subheader("Head-to-Head")

        if head_to_head:

            for (
                h2h_season,
                h2h_date,
                h2h_away_team,
                h2h_away_score,
                h2h_home_team,
                h2h_home_score
            ) in head_to_head:

                st.markdown(
                    f"**{h2h_away_team} {h2h_away_score} "
                    f"— {h2h_home_team} {h2h_home_score}**"
                )

                st.caption(
                    h2h_date.astimezone(
                        ZoneInfo("America/New_York")
                    ).strftime("%B %d, %Y")
                )

        else:
            st.write("No previous meetings found.")
    st.stop()

# -------------------------
# SCHEDULE PAGE
# -------------------------

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

        away_col, middle_col, home_col = st.columns([2, 1, 2])

        with away_col:
            st.image(away_logo, width=80)
            st.markdown(f"### {away_team}")

        with middle_col:
            st.markdown("### @")

        with home_col:
            st.image(home_logo, width=80)
            st.markdown(f"### {home_team}")

        st.write(
            eastern_time.strftime(
                "%A, %B %d · %I:%M %p %Z"
            )
        )

        st.write(venue)

        if st.button("View Game", key=game_id):
            st.session_state["selected_game"] = game_id
            st.rerun()

cursor.close()
connection.close()