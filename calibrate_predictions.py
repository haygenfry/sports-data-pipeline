import csv

from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    brier_score_loss,
    log_loss
)


INPUT_FILE = "multi_season_prediction_backtest.csv"


# -------------------------
# LOAD BACKTEST
# -------------------------

raw_edges = []
outcomes = []
seasons = []

with open(INPUT_FILE, "r") as file:
    reader = csv.DictReader(file)

    for row in reader:

        if row["actual_home_win"] in ("", "None"):
            continue

        raw_edges.append(
            [float(row["raw_edge"])]
        )

        outcomes.append(
            int(row["actual_home_win"])
        )

        seasons.append(
            int(row["season"])
        )

print(f"Loaded {len(raw_edges)} historical games")


# -------------------------
# FIT CALIBRATION MODEL
# -------------------------

model = LogisticRegression()

model.fit(
    raw_edges,
    outcomes
)


intercept = model.intercept_[0]
coefficient = model.coef_[0][0]


print("\nCALIBRATION MODEL")
print("-----------------")
print(f"Intercept:   {intercept:.6f}")
print(f"Coefficient: {coefficient:.6f}")


# -------------------------
# PREDICT HISTORICAL GAMES
# -------------------------

home_probabilities = model.predict_proba(
    raw_edges
)[:, 1]

predictions = model.predict(
    raw_edges
)


# -------------------------
# MODEL QUALITY
# -------------------------

accuracy = accuracy_score(
    outcomes,
    predictions
)

brier = brier_score_loss(
    outcomes,
    home_probabilities
)

loss = log_loss(
    outcomes,
    home_probabilities
)


print("\nCALIBRATION PERFORMANCE")
print("-----------------------")

print(
    f"Accuracy:    "
    f"{accuracy * 100:.1f}%"
)

print(
    f"Brier score: "
    f"{brier:.4f}"
)

print(
    f"Log loss:    "
    f"{loss:.4f}"
)


# -------------------------
# EDGE → PROBABILITY EXAMPLES
# -------------------------

test_edges = [
    -15,
    -10,
    -5,
    -2,
    0,
    2,
    5,
    10,
    15
]

test_features = [
    [edge]
    for edge in test_edges
]

test_probabilities = model.predict_proba(
    test_features
)[:, 1]


print("\nRAW EDGE → HOME WIN PROBABILITY")
print("-------------------------------")

for edge, probability in zip(
    test_edges,
    test_probabilities
):
    print(
        f"{edge:+5.1f} → "
        f"{probability * 100:5.1f}%"
    )

# -------------------------
# 2025 SEASON HOLDOUT
# -------------------------

train_edges = []
train_outcomes = []

holdout_edges = []
holdout_outcomes = []


for edge, outcome, season in zip(
    raw_edges,
    outcomes,
    seasons
):

    if season == 2025:
        holdout_edges.append(edge)
        holdout_outcomes.append(outcome)

    else:
        train_edges.append(edge)
        train_outcomes.append(outcome)


holdout_model = LogisticRegression()

holdout_model.fit(
    train_edges,
    train_outcomes
)


holdout_probabilities = (
    holdout_model.predict_proba(
        holdout_edges
    )[:, 1]
)

holdout_predictions = (
    holdout_model.predict(
        holdout_edges
    )
)


holdout_accuracy = accuracy_score(
    holdout_outcomes,
    holdout_predictions
)

holdout_brier = brier_score_loss(
    holdout_outcomes,
    holdout_probabilities
)

holdout_log_loss = log_loss(
    holdout_outcomes,
    holdout_probabilities
)


print("\n2025 SEASON HOLDOUT")
print("-------------------")

print(
    f"Training games: "
    f"{len(train_edges)}"
)

print(
    f"2025 test games: "
    f"{len(holdout_edges)}"
)

print(
    f"Test accuracy:   "
    f"{holdout_accuracy * 100:.1f}%"
)

print(
    f"Test Brier:      "
    f"{holdout_brier:.4f}"
)

print(
    f"Test log loss:   "
    f"{holdout_log_loss:.4f}"
)

print(
    f"Train intercept: "
    f"{holdout_model.intercept_[0]:.6f}"
)

print(
    f"Train coefficient: "
    f"{holdout_model.coef_[0][0]:.6f}"
)

# -------------------------
# ROLLING SEASON HOLDOUTS
# -------------------------

rolling_tests = [
    {
        "train_seasons": [2022],
        "test_season": 2023
    },
    {
        "train_seasons": [2022, 2023],
        "test_season": 2024
    },
    {
        "train_seasons": [2022, 2023, 2024],
        "test_season": 2025
    }
]


print("\nROLLING SEASON HOLDOUTS")
print("-----------------------")


for rolling_test in rolling_tests:

    train_seasons = rolling_test["train_seasons"]
    test_season = rolling_test["test_season"]

    rolling_train_edges = []
    rolling_train_outcomes = []

    rolling_test_edges = []
    rolling_test_outcomes = []


    for edge, outcome, season in zip(
        raw_edges,
        outcomes,
        seasons
    ):

        if season in train_seasons:
            rolling_train_edges.append(edge)
            rolling_train_outcomes.append(outcome)

        elif season == test_season:
            rolling_test_edges.append(edge)
            rolling_test_outcomes.append(outcome)


    rolling_model = LogisticRegression()

    rolling_model.fit(
        rolling_train_edges,
        rolling_train_outcomes
    )


    rolling_probabilities = (
        rolling_model.predict_proba(
            rolling_test_edges
        )[:, 1]
    )

    rolling_predictions = (
        rolling_model.predict(
            rolling_test_edges
        )
    )


    rolling_accuracy = accuracy_score(
        rolling_test_outcomes,
        rolling_predictions
    )

    rolling_brier = brier_score_loss(
        rolling_test_outcomes,
        rolling_probabilities
    )

    rolling_log_loss = log_loss(
        rolling_test_outcomes,
        rolling_probabilities
    )


    print(
        f"\nTrain {train_seasons} "
        f"→ Test {test_season}"
    )

    print(
        f"Training games: "
        f"{len(rolling_train_edges)}"
    )

    print(
        f"Test games:     "
        f"{len(rolling_test_edges)}"
    )

    print(
        f"Accuracy:       "
        f"{rolling_accuracy * 100:.1f}%"
    )

    print(
        f"Brier:          "
        f"{rolling_brier:.4f}"
    )

    print(
        f"Log loss:       "
        f"{rolling_log_loss:.4f}"
    )

    print(
        f"Intercept:      "
        f"{rolling_model.intercept_[0]:.6f}"
    )

    print(
        f"Coefficient:    "
        f"{rolling_model.coef_[0][0]:.6f}"
    )