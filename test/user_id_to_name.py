"""Converts a Slack user id into their name."""

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from secret import APP_TOKEN, BOT_TOKEN

app = App(token=BOT_TOKEN)
slack_socket_handler = SocketModeHandler(app, APP_TOKEN)
slack_socket_handler.connect()

try:
    while True:
        user_id = input("ID: ")
        name = app.client.users_info(user=user_id).get("user", {}).get("real_name", "")
        print(name)
except KeyboardInterrupt:
    print("Stopping.")
    slack_socket_handler.close()
