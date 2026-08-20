import requests
import json

url = (
    "https://site.api.espn.com/apis/site/v2/"
    "sports/football/nfl/summary"
)

game_id = "401872656"

response = requests.get(
    url,
    params={"event": game_id},
    timeout=30
)

response.raise_for_status()

data = response.json()

print("TOP-LEVEL KEYS:")
print(data.keys())

print("\nODDS:")
print(
    json.dumps(
        data.get("odds"),
        indent=4
    )
)

print("\nPICKCENTER:")
print(
    json.dumps(
        data.get("pickcenter"),
        indent=4
    )
)