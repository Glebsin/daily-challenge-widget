import sys
from ossapi import Ossapi

client_id = "your_client_id"
client_secret = "your_client_secret"
api = Ossapi(client_id, client_secret)

username = sys.argv[1]

user = api.user(username)

daily_stat = user.daily_challenge_user_stats

print(f"User {username} current daily streak: {daily_stat.daily_streak_current}")