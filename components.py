import streamlit as st
import html
import textwrap

def render_stat_section_spacer():
    st.markdown(
        "<div style='height: 24px;'></div>",
        unsafe_allow_html=True
    )

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

def render_responsive_comparison_table(
    headers,
    rows,
    mobile_labels=None
):
    """
    Render a comparison table that stays tabular on desktop
    and becomes compact stacked rows on mobile.

    headers:
        ["Metric", "49ers", "Rams"]

    rows:
        [
            ["Total Yards", "407", "456"],
            ["Passing Yards", "333", "378"],
        ]

    mobile_labels:
        Optional shorter labels for mobile, excluding Metric.
        Example: ["SF", "LAR"]
    """

    if mobile_labels is None:
        mobile_labels = headers[1:]

    header_html = "".join(
        f"<th>{html.escape(str(header))}</th>"
        for header in headers
    )

    desktop_rows = []

    mobile_rows = []

    for row in rows:
        desktop_cells = "".join(
            f"<td>{html.escape(str(value))}</td>"
            for value in row
        )

        desktop_rows.append(
            f"<tr>{desktop_cells}</tr>"
        )

        metric = html.escape(str(row[0]))

        values_html = "".join(
            f"""
            <div class="responsive-comparison-mobile-value">
                <span class="responsive-comparison-mobile-label">
                    {html.escape(str(label))}
                </span>
                <span>
                    {html.escape(str(value))}
                </span>
            </div>
            """
            for label, value in zip(
                mobile_labels,
                row[1:]
            )
        )

        mobile_rows.append(
            f"""
            <div class="responsive-comparison-mobile-row">
                <div class="responsive-comparison-mobile-metric">
                    {metric}
                </div>
                <div class="responsive-comparison-mobile-values">
                    {values_html}
                </div>
            </div>
            """
        )

    html_content = f"""
    <style>
    html, body {{
        margin: 0;
        padding: 0;
    }}

    body {{
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI",
                     sans-serif;
        color: #31333F;
    }}

    :root {{
        --table-cell-y: 8px;
        --table-cell-x: 10px;
        --mobile-row-y: 12px;
        --mobile-metric-gap: 6px;
        --mobile-column-gap: 12px;
        --border-strong: rgba(128, 128, 128, 0.35);
        --border-light: rgba(128, 128, 128, 0.18);
    }}

    .responsive-comparison-desktop {{
        width: 100%;
        border-collapse: collapse;
        margin-bottom: 1rem;
    }}

    .responsive-comparison-desktop th {{
        text-align: left;
        padding: 0.55rem 0.7rem;
        border-bottom: 1px solid rgba(128, 128, 128, 0.35);
    }}

    .responsive-comparison-desktop td {{
        padding: var(--table-cell-y) var(--table-cell-x);
        border-bottom: 1px solid var(--border-light);
        vertical-align: top;
    }}

    .responsive-comparison-mobile {{
        display: none;
    }}

    @media (max-width: 640px) {{
        .responsive-comparison-desktop {{
            display: none;
        }}

        .responsive-comparison-mobile {{
            display: block;
        }}

        .responsive-comparison-mobile-row {{
            padding: var(--mobile-row-y) 0;
            border-bottom: 1px solid var(--border-light);
        }}

        .responsive-comparison-mobile-metric {{
            font-weight: 600;
            margin-bottom: var(--mobile-metric-gap);
        }}

        .responsive-comparison-mobile-values {{
            display: grid;
            grid-template-columns: repeat(
                {len(headers) - 1},
                minmax(0, 1fr)
            );
            gap: var(--mobile-column-gap);
        }}

        .responsive-comparison-mobile-label {{
            display: block;
            font-size: 0.78rem;
            opacity: 0.7;
            margin-bottom: 0.1rem;
        }}
    }}
    </style>

    <table class="responsive-comparison-desktop">
        <thead>
            <tr>
                {header_html}
            </tr>
        </thead>
        <tbody>
            {''.join(desktop_rows)}
        </tbody>
    </table>

    <div class="responsive-comparison-mobile">
        {''.join(mobile_rows)}
    </div>
    """

    st.iframe(
        html_content,
        width="stretch",
        height="content"
    )

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

    formatted_rows = []

    for (
        metric,
        offense_value,
        defense_value,
        matchup_read,
        value_type
    ) in rows:

        if value_type == "percent":
            offense_display = f"{offense_value * 100:.1f}%"
            defense_display = f"{defense_value * 100:.1f}% allowed"

        elif value_type == "decimal":
            offense_display = f"{offense_value:.2f}"
            defense_display = f"{defense_value:.2f} allowed"

        elif value_type == "turnovers":
            offense_display = f"{offense_value:.2f} TO/G"
            defense_display = f"{defense_value:.2f} TAKE/G"

        else:
            offense_display = f"{offense_value:.1f}"
            defense_display = f"{defense_value:.1f} allowed"

        formatted_rows.append(
            [
                metric,
                offense_display,
                defense_display,
                matchup_read
            ]
        )

    render_responsive_comparison_table(
        headers=[
            "Metric",
            f"{offense_team} Offense",
            f"{defense_team} Defense",
            "Matchup Read"
        ],
        rows=formatted_rows,
        mobile_labels=[
            "Offense",
            "Defense",
            "Read"
        ]
    )

def render_box_score_table(headers, rows):
    header_html = "".join(
        f"<th>{html.escape(str(header))}</th>"
        for header in headers
    )

    body_rows = []

    for row in rows:
        cells = "".join(
            f"<td>{html.escape(str(value))}</td>"
            for value in row
        )

        body_rows.append(f"<tr>{cells}</tr>")

    html_content = f"""
    <style>
        body {{
            margin: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI",
                         sans-serif;
            color: #31333F;
        }}

        .box-score-wrapper {{
            width: 100%;
            overflow-x: auto;
        }}

        .box-score-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }}

        .box-score-table th {{
            text-align: left;
            font-weight: 600;
            padding: 8px 10px;
            border-bottom: 1px solid #c7c7c7;
            white-space: nowrap;
        }}

        .box-score-table td {{
            padding: 8px 10px;
            border-bottom: 1px solid #e6e6e6;
            white-space: nowrap;
        }}

        .box-score-table th:first-child,
        .box-score-table td:first-child {{
            min-width: 130px;
        }}

        @media (max-width: 640px) {{
            .box-score-table {{
                font-size: 14px;
                min-width: 560px;
            }}

            .box-score-table th,
            .box-score-table td {{
                padding: 7px 8px;
            }}

            .box-score-table th:first-child,
            .box-score-table td:first-child {{
                min-width: 120px;
            }}
        }}
    </style>

    <div class="box-score-wrapper">
        <table class="box-score-table">
            <thead>
                <tr>{header_html}</tr>
            </thead>
            <tbody>
                {''.join(body_rows)}
            </tbody>
        </table>
    </div>
    """

    st.iframe(
        html_content,
        width="stretch",
        height="content"
    )

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

    rows = []

    for player in passers:
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

        formatted_values = []

        for index, value in enumerate(values):
            if value is None:
                display_value = "—"

            elif index in (3, 7):
                display_value = f"{float(value):.1f}"

            else:
                display_value = str(value)

            formatted_values.append(display_value)

        rows.append(formatted_values)

    render_box_score_table(headers, rows)


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

    headers = [
        "Player",
        "CAR",
        "YDS",
        "AVG",
        "TD",
        "LONG"
    ]

    rows = []

    for player in rushers:
        values = [
            player["player_name"],
            player["rushing_attempts"],
            player["rushing_yards"],
            player["yards_per_rush_attempt"],
            player["rushing_touchdowns"],
            player["long_rushing"]
        ]

        formatted_values = []

        for index, value in enumerate(values):
            if value is None:
                display_value = "—"

            elif index == 3:
                display_value = f"{float(value):.1f}"

            else:
                display_value = str(value)

            formatted_values.append(display_value)

        rows.append(formatted_values)

    render_box_score_table(headers, rows)


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

    headers = [
        "Player",
        "REC",
        "TGT",
        "YDS",
        "AVG",
        "TD",
        "LONG"
    ]

    rows = []

    for player in receivers:
        values = [
            player["player_name"],
            player["receptions"],
            player["receiving_targets"],
            player["receiving_yards"],
            player["yards_per_reception"],
            player["receiving_touchdowns"],
            player["long_reception"]
        ]

        formatted_values = []

        for index, value in enumerate(values):
            if value is None:
                display_value = "—"

            elif index == 4:
                display_value = f"{float(value):.1f}"

            else:
                display_value = str(value)

            formatted_values.append(display_value)

        rows.append(formatted_values)

    render_box_score_table(headers, rows)


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

    rows = []

    for player in defenders:
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

        formatted_values = []

        for index, value in enumerate(values):
            if value is None:
                display_value = "0"

            elif index in (3, 4):
                number = float(value)
                display_value = (
                    str(int(number))
                    if number.is_integer()
                    else f"{number:.1f}"
                )

            else:
                display_value = str(value)

            formatted_values.append(display_value)

        rows.append(formatted_values)

    render_box_score_table(headers, rows)
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

    headers = [
        "Player",
        "FG",
        "FG%",
        "LONG",
        "XP",
        "PTS"
    ]

    rows = []

    for player in kickers:
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

        rows.append([
            "—" if value is None else str(value)
            for value in values
        ])

    render_box_score_table(headers, rows)
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

    headers = [
        "Player",
        "PUNTS",
        "YDS",
        "AVG",
        "TB",
        "IN20",
        "LONG"
    ]

    rows = []

    for player in punters:
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

        rows.append([
            "—" if value is None else str(value)
            for value in values
        ])

    render_box_score_table(headers, rows)
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

    rows = []

    for player in returners:
        kr_avg = player["yards_per_kick_return"]
        pr_avg = player["yards_per_punt_return"]

        rows.append([
            str(player["player_name"]),
            str(player["kick_returns"] or 0),
            str(player["kick_return_yards"] or 0),
            f"{float(kr_avg):.1f}" if kr_avg is not None else "—",
            str(player["long_kick_return"] or 0),
            str(player["punt_returns"] or 0),
            str(player["punt_return_yards"] or 0),
            f"{float(pr_avg):.1f}" if pr_avg is not None else "—",
            str(
                (player["kick_return_touchdowns"] or 0)
                + (player["punt_return_touchdowns"] or 0)
            )
        ])

    render_box_score_table(headers, rows)
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

    headers = [
        "Player",
        "FUM",
        "LOST"
    ]

    rows = [
        [
            player["player_name"],
            player["fumbles"] or 0,
            player["fumbles_lost"] or 0
        ]
        for player in fumblers
    ]

    render_box_score_table(headers, rows)

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
