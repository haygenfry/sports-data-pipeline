import csv

from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    brier_score_loss,
    log_loss
)


INPUT_FILE = "2025_prediction_backtest.csv"


# -------------------------
# LOAD BACKTEST
# -------------------------

raw_edges = []
outcomes = []


with open(INPUT_FILE, "r") as file:
    reader = csv.DictReader(file)

    for row in reader:

        # Ignore ties
        if row["actual_home_win"] in ("", "None"):
            continue

        raw_edges.append(
            [float(row["raw_edge"])]
        )

        outcomes.append(
            int(row["actual_home_win"])
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
# CHRONOLOGICAL TEST
# -------------------------

split_index = int(
    len(raw_edges) * 0.70
)

train_edges = raw_edges[:split_index]
train_outcomes = outcomes[:split_index]

test_edges = raw_edges[split_index:]
test_outcomes = outcomes[split_index:]


test_model = LogisticRegression()

test_model.fit(
    train_edges,
    train_outcomes
)


test_probabilities = (
    test_model.predict_proba(
        test_edges
    )[:, 1]
)

test_predictions = (
    test_model.predict(
        test_edges
    )
)


test_accuracy = accuracy_score(
    test_outcomes,
    test_predictions
)

test_brier = brier_score_loss(
    test_outcomes,
    test_probabilities
)

test_log_loss = log_loss(
    test_outcomes,
    test_probabilities
)


print("\nCHRONOLOGICAL TRAIN / TEST")
print("--------------------------")

print(
    f"Training games: "
    f"{len(train_edges)}"
)

print(
    f"Test games:     "
    f"{len(test_edges)}"
)

print(
    f"Test accuracy:  "
    f"{test_accuracy * 100:.1f}%"
)

print(
    f"Test Brier:     "
    f"{test_brier:.4f}"
)

print(
    f"Test log loss:  "
    f"{test_log_loss:.4f}"
)

print(
    f"Train intercept:   "
    f"{test_model.intercept_[0]:.6f}"
)

print(
    f"Train coefficient: "
    f"{test_model.coef_[0][0]:.6f}"
)