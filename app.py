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