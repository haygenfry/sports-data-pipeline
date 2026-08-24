import math

def get_skill_player_score(
    position,
    profile
):
    if not profile:
        return None

    if position == "RB":
        games_played = profile["games_played"]

        if not games_played:
            return None

        scrimmage_yards_per_game = (
            profile["scrimmage_yards"]
            / games_played
        )

        touchdowns_per_game = (
            profile["total_touchdowns"]
            / games_played
        )

        return (
            scrimmage_yards_per_game
            + touchdowns_per_game * 25
        )

    if position in ("WR", "TE"):
        games_played = profile["games_played"]

        if not games_played:
            return None

        touchdowns_per_game = (
            profile["receiving_touchdowns"]
            / games_played
        )

        targets_per_game = (
            profile["targets"]
            / games_played
        )

        return (
            profile["receiving_yards_per_game"]
            + touchdowns_per_game * 25
            + targets_per_game * 2
        )

    return None


def get_defensive_impact_score(
    profile
):
    if not profile:
        return None

    games_played = profile["games_played"]

    if not games_played:
        return None

    score = (
        profile["total_tackles"] * 0.25
        + profile["sacks"] * 4.0
        + profile["tackles_for_loss"] * 1.5
        + profile["passes_defended"] * 1.5
        + profile["qb_hits"] * 1.0
        + profile["interceptions"] * 5.0
        + profile["fumbles_recovered"] * 4.0
        + profile["defensive_touchdowns"] * 6.0
    )

    return score / games_played


def get_key_player_spotlights(
    offensive_map,
    defensive_map,
    qb_profile,
    qb_player_id,
    rb_profile,
    rb_player_id,
    receiver_profile_map,
    defensive_profile_map
):
    skill_candidates = []

    # -------------------------
    # QUARTERBACK
    # -------------------------

    qb_candidate = None

    if qb_player_id and qb_profile:

        qb_starter = next(
            (
                player
                for player in offensive_map.values()
                if player[2] == qb_player_id
            ),
            None
        )

        if qb_starter:
            qb_candidate = {
                "player": qb_starter,
                "profile": qb_profile,
                "type": "QB"
            }

    # -------------------------
    # RUNNING BACK
    # -------------------------

    if rb_player_id and rb_profile:

        rb_starter = next(
            (
                player
                for player in offensive_map.values()
                if player[2] == rb_player_id
            ),
            None
        )

        if rb_starter:
            score = get_skill_player_score(
                "RB",
                rb_profile
            )

            if score is not None:
                skill_candidates.append(
                    {
                        "player": rb_starter,
                        "profile": rb_profile,
                        "score": score,
                        "type": "RB"
                    }
                )

    # -------------------------
    # RECEIVERS
    # -------------------------

    for player in offensive_map.values():

        position = player[1]
        player_id = player[2]

        if position not in ("WR", "TE"):
            continue

        profile = receiver_profile_map.get(
            player_id
        )

        if not profile:
            continue

        score = get_skill_player_score(
            position,
            profile
        )

        if score is not None:
            skill_candidates.append(
                {
                    "player": player,
                    "profile": profile,
                    "score": score,
                    "type": position
                }
            )

    top_skill_player = (
        max(
            skill_candidates,
            key=lambda player: player["score"]
        )
        if skill_candidates
        else None
    )

    # -------------------------
    # DEFENSE
    # -------------------------

    defensive_candidates = []

    for player in defensive_map.values():

        player_id = player[2]

        profile = defensive_profile_map.get(
            player_id
        )

        if not profile:
            continue

        score = get_defensive_impact_score(
            profile
        )

        if score is not None:
            defensive_candidates.append(
                {
                    "player": player,
                    "profile": profile,
                    "score": score,
                    "type": player[1]
                }
            )

    top_defensive_player = (
        max(
            defensive_candidates,
            key=lambda player: player["score"]
        )
        if defensive_candidates
        else None
    )

    return {
        "qb": qb_candidate,
        "skill": top_skill_player,
        "defense": top_defensive_player
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


def get_matchup_advantages(comparison):
    if not comparison:
        return None

    advantages = {}

    # Higher offense values are generally better here.
    advantages["total_yards"] = (
        comparison["total_yards"][0]
        - comparison["total_yards"][1]
    )

    advantages["passing_yards"] = (
        comparison["passing_yards"][0]
        - comparison["passing_yards"][1]
    )

    advantages["rushing_yards"] = (
        comparison["rushing_yards"][0]
        - comparison["rushing_yards"][1]
    )

    advantages["yards_per_play"] = (
        comparison["yards_per_play"][0]
        - comparison["yards_per_play"][1]
    )

    advantages["third_down"] = (
        comparison["third_down"][0]
        - comparison["third_down"][1]
    )

    advantages["red_zone"] = (
        comparison["red_zone"][0]
        - comparison["red_zone"][1]
    )

    # Lower offensive turnovers are better,
    # while higher defensive takeaways are better.
    # Negative = favorable for offense.
    advantages["turnover_pressure"] = (
        comparison["turnovers_takeaways"][0]
        - comparison["turnovers_takeaways"][1]
    )

    return advantages


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


def american_odds_to_probability(odds):

    if odds is None:
        return None

    odds = float(odds)

    if odds < 0:
        return (
            abs(odds)
            / (abs(odds) + 100)
        )

    return (
        100
        / (odds + 100)
    )


def remove_vig(
    away_probability,
    home_probability
):
    if (
        away_probability is None
        or home_probability is None
    ):
        return None, None

    total_probability = (
        away_probability
        + home_probability
    )

    if total_probability == 0:
        return None, None

    return (
        away_probability / total_probability,
        home_probability / total_probability
    )


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


def get_v2_win_probability(
    power_edge,
    matchup_edge,
    recent_form_edge
):
    if (
        power_edge is None
        or matchup_edge is None
        or recent_form_edge is None
    ):
        return None

    intercept = 0.220707

    power_coefficient = 0.059819
    matchup_coefficient = 0.129711
    recent_form_coefficient = 0.165316

    logit = (
        intercept
        + power_coefficient * power_edge
        + matchup_coefficient * matchup_edge
        + recent_form_coefficient * recent_form_edge
    )

    home_probability = (
        1
        / (1 + math.exp(-logit))
    )

    away_probability = (
        1 - home_probability
    )

    return {
        "home_win_probability": home_probability,
        "away_win_probability": away_probability
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


def get_prediction_confidence(probability):
    if probability < 0.55:
        return "Toss-up"

    if probability < 0.60:
        return "Lean"

    if probability < 0.70:
        return "Moderate"

    return "Strong"


