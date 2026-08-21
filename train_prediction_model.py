import csv

from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    brier_score_loss,
    log_loss
)


INPUT_FILE = "multi_season_prediction_backtest.csv"

FEATURE_NAMES = [
    "power_edge",
    "matchup_edge",
    "recent_form_edge"
]


# -------------------------
# LOAD DATA
# -------------------------

rows = []

with open(INPUT_FILE, "r") as file:
    reader = csv.DictReader(file)

    for row in reader:

        if row["actual_home_win"] in ("", "None"):
            continue

        rows.append(row)


print(f"Loaded {len(rows)} historical games")


# -------------------------
# ROLLING SEASON HOLDOUTS
# -------------------------

seasons = sorted(
    {
        int(row["season"])
        for row in rows
    }
)


print("\nROLLING SEASON HOLDOUTS")
print("-----------------------")


for test_season in seasons[1:]:

    training_rows = [
        row
        for row in rows
        if int(row["season"]) < test_season
    ]

    test_rows = [
        row
        for row in rows
        if int(row["season"]) == test_season
    ]

    if not training_rows or not test_rows:
        continue


    X_train = [
        [
            float(row[feature])
            for feature in FEATURE_NAMES
        ]
        for row in training_rows
    ]

    y_train = [
        int(row["actual_home_win"])
        for row in training_rows
    ]


    X_test = [
        [
            float(row[feature])
            for feature in FEATURE_NAMES
        ]
        for row in test_rows
    ]

    y_test = [
        int(row["actual_home_win"])
        for row in test_rows
    ]


    model = LogisticRegression()

    model.fit(
        X_train,
        y_train
    )


    probabilities = model.predict_proba(
        X_test
    )[:, 1]

    predictions = model.predict(
        X_test
    )


    accuracy = accuracy_score(
        y_test,
        predictions
    )

    brier = brier_score_loss(
        y_test,
        probabilities
    )

    loss = log_loss(
        y_test,
        probabilities
    )


    print(
        f"\nTrain before {test_season} "
        f"→ Test {test_season}"
    )

    print(
        f"Training games: {len(training_rows)}"
    )

    print(
        f"Test games:     {len(test_rows)}"
    )

    print(
        f"Accuracy:       "
        f"{accuracy * 100:.1f}%"
    )

    print(
        f"Brier:          "
        f"{brier:.4f}"
    )

    print(
        f"Log loss:       "
        f"{loss:.4f}"
    )

    print(
        f"Intercept:      "
        f"{model.intercept_[0]:.6f}"
    )

    print("Coefficients:")

    for feature, coefficient in zip(
        FEATURE_NAMES,
        model.coef_[0]
    ):
        print(
            f"  {feature}: "
            f"{coefficient:.6f}"
        )

# -------------------------
# FEATURE ABLATION
# -------------------------

FEATURE_SETS = {
    "Power only": [
        "power_edge"
    ],
    "Power + matchup": [
        "power_edge",
        "matchup_edge"
    ],
    "Power + recent form": [
        "power_edge",
        "recent_form_edge"
    ],
    "Power + matchup + recent form": [
        "power_edge",
        "matchup_edge",
        "recent_form_edge"
    ]
}


print("\nFEATURE ABLATION")
print("----------------")


for test_season in seasons[1:]:

    training_rows = [
        row
        for row in rows
        if int(row["season"]) < test_season
    ]

    test_rows = [
        row
        for row in rows
        if int(row["season"]) == test_season
    ]

    if not training_rows or not test_rows:
        continue


    print(
        f"\nTest season: {test_season}"
    )


    for model_name, feature_names in FEATURE_SETS.items():

        X_train = [
            [
                float(row[feature])
                for feature in feature_names
            ]
            for row in training_rows
        ]

        y_train = [
            int(row["actual_home_win"])
            for row in training_rows
        ]

        X_test = [
            [
                float(row[feature])
                for feature in feature_names
            ]
            for row in test_rows
        ]

        y_test = [
            int(row["actual_home_win"])
            for row in test_rows
        ]


        model = LogisticRegression()

        model.fit(
            X_train,
            y_train
        )


        probabilities = model.predict_proba(
            X_test
        )[:, 1]

        predictions = model.predict(
            X_test
        )


        accuracy = accuracy_score(
            y_test,
            predictions
        )

        brier = brier_score_loss(
            y_test,
            probabilities
        )

        loss = log_loss(
            y_test,
            probabilities
        )


        print(
            f"\n{model_name}"
        )

        print(
            f"  Accuracy: "
            f"{accuracy * 100:.1f}%"
        )

        print(
            f"  Brier:    "
            f"{brier:.4f}"
        )

        print(
            f"  Log loss: "
            f"{loss:.4f}"
        )

# -------------------------
# POWER COMPONENT ABLATION
# -------------------------

POWER_COMPONENT_SETS = {
    "Scoring only": [
        "scoring_edge"
    ],

    "Scoring + YPP": [
        "scoring_edge",
        "yards_per_play_edge"
    ],

    "Scoring + YPP + turnovers": [
        "scoring_edge",
        "yards_per_play_edge",
        "turnover_edge"
    ],

    "Scoring + YPP + turnovers + third down": [
        "scoring_edge",
        "yards_per_play_edge",
        "turnover_edge",
        "third_down_edge"
    ],

    "All power components": [
        "scoring_edge",
        "yards_per_play_edge",
        "turnover_edge",
        "third_down_edge",
        "red_zone_edge"
    ],

    "All power + matchup": [
        "scoring_edge",
        "yards_per_play_edge",
        "turnover_edge",
        "third_down_edge",
        "red_zone_edge",
        "matchup_edge"
    ],

    "All power + recent form": [
        "scoring_edge",
        "yards_per_play_edge",
        "turnover_edge",
        "third_down_edge",
        "red_zone_edge",
        "recent_form_edge"
    ],

    "All power + matchup + recent form": [
        "scoring_edge",
        "yards_per_play_edge",
        "turnover_edge",
        "third_down_edge",
        "red_zone_edge",
        "matchup_edge",
        "recent_form_edge"
    ]
}


print("\nPOWER COMPONENT ABLATION")
print("------------------------")


for test_season in seasons[1:]:

    training_rows = [
        row
        for row in rows
        if int(row["season"]) < test_season
    ]

    test_rows = [
        row
        for row in rows
        if int(row["season"]) == test_season
    ]

    if not training_rows or not test_rows:
        continue


    print(
        f"\nTest season: {test_season}"
    )


    for model_name, feature_names in POWER_COMPONENT_SETS.items():

        X_train = [
            [
                float(row[feature])
                for feature in feature_names
            ]
            for row in training_rows
        ]

        y_train = [
            int(row["actual_home_win"])
            for row in training_rows
        ]

        X_test = [
            [
                float(row[feature])
                for feature in feature_names
            ]
            for row in test_rows
        ]

        y_test = [
            int(row["actual_home_win"])
            for row in test_rows
        ]


        model = LogisticRegression()

        model.fit(
            X_train,
            y_train
        )


        probabilities = model.predict_proba(
            X_test
        )[:, 1]

        predictions = model.predict(
            X_test
        )


        accuracy = accuracy_score(
            y_test,
            predictions
        )

        brier = brier_score_loss(
            y_test,
            probabilities
        )

        loss = log_loss(
            y_test,
            probabilities
        )


        print(
            f"\n{model_name}"
        )

        print(
            f"  Accuracy: "
            f"{accuracy * 100:.1f}%"
        )

        print(
            f"  Brier:    "
            f"{brier:.4f}"
        )

        print(
            f"  Log loss: "
            f"{loss:.4f}"
        )

# -------------------------
# OPPONENT STRENGTH ABLATION
# -------------------------

OPPONENT_STRENGTH_SETS = {
    "Power only": [
        "power_edge"
    ],

    "Power + opponent strength": [
        "power_edge",
        "opponent_strength_edge"
    ],

    "Power + matchup + recent form": [
        "power_edge",
        "matchup_edge",
        "recent_form_edge"
    ],

    "Power + matchup + recent form + opponent strength": [
        "power_edge",
        "matchup_edge",
        "recent_form_edge",
        "opponent_strength_edge"
    ]
}


print("\nOPPONENT STRENGTH ABLATION")
print("--------------------------")


for test_season in seasons[1:]:

    training_rows = [
        row
        for row in rows
        if int(row["season"]) < test_season
    ]

    test_rows = [
        row
        for row in rows
        if int(row["season"]) == test_season
    ]

    if not training_rows or not test_rows:
        continue

    print(f"\nTest season: {test_season}")

    for model_name, feature_names in OPPONENT_STRENGTH_SETS.items():

        X_train = [
            [
                float(row[feature])
                for feature in feature_names
            ]
            for row in training_rows
        ]

        y_train = [
            int(row["actual_home_win"])
            for row in training_rows
        ]

        X_test = [
            [
                float(row[feature])
                for feature in feature_names
            ]
            for row in test_rows
        ]

        y_test = [
            int(row["actual_home_win"])
            for row in test_rows
        ]

        model = LogisticRegression()

        model.fit(
            X_train,
            y_train
        )

        probabilities = model.predict_proba(
            X_test
        )[:, 1]

        predictions = model.predict(
            X_test
        )

        accuracy = accuracy_score(
            y_test,
            predictions
        )

        brier = brier_score_loss(
            y_test,
            probabilities
        )

        loss = log_loss(
            y_test,
            probabilities
        )

        print(f"\n{model_name}")

        print(
            f"  Accuracy: "
            f"{accuracy * 100:.1f}%"
        )

        print(
            f"  Brier:    "
            f"{brier:.4f}"
        )

        print(
            f"  Log loss: "
            f"{loss:.4f}"
        )

        if "opponent_strength_edge" in feature_names:
            opponent_index = feature_names.index(
                "opponent_strength_edge"
            )

            print(
                f"  Opponent strength coefficient: "
                f"{model.coef_[0][opponent_index]:.6f}"
            )

# -------------------------
# FINAL MODEL
# -------------------------

X_all = [
    [
        float(row[feature])
        for feature in FEATURE_NAMES
    ]
    for row in rows
]

y_all = [
    int(row["actual_home_win"])
    for row in rows
]


final_model = LogisticRegression()

final_model.fit(
    X_all,
    y_all
)


print("\nFINAL MODEL")
print("-----------")

print(
    f"Training games: "
    f"{len(rows)}"
)

print(
    f"Intercept: "
    f"{final_model.intercept_[0]:.6f}"
)

print("Coefficients:")

for feature, coefficient in zip(
    FEATURE_NAMES,
    final_model.coef_[0]
):
    print(
        f"  {feature}: "
        f"{coefficient:.6f}"
    )