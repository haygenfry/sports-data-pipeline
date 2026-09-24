import subprocess
import sys


if len(sys.argv) != 2:
    print("Usage: python refresh_week.py <week>")
    sys.exit(1)

week = sys.argv[1]

loaders = [
    "load_team_game_stats.py",
    "load_player_game_stats.py",
    "load_betting.py",
    "load_weather.py",
    "load_injuries.py",
]

print(f"\nRefreshing Week {week}\n")

for loader in loaders:
    print(f"--- Running {loader} ---")

    result = subprocess.run(
        [sys.executable, loader, week]
    )

    if result.returncode != 0:
        print(f"\nRefresh failed while running {loader}")
        sys.exit(result.returncode)

    print()

print(f"Week {week} refresh complete.")