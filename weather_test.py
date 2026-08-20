import requests

game_id = "401872656"

url = (
    "https://site.api.espn.com/apis/site/v2/"
    "sports/football/nfl/summary"
)

response = requests.get(
    url,
    params={"event": game_id},
    timeout=30
)

response.raise_for_status()

data = response.json()

print("HEADER:")
print(data.get("header"))

print("\nWEATHER:")
print(data.get("weather"))

print("\nGAME INFO:")
print(data.get("gameInfo"))