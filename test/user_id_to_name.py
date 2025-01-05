"""Converts a Slack user id into their name."""

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from secret import APP_TOKEN, BOT_TOKEN

app = App(token=BOT_TOKEN)
slack_socket_handler = SocketModeHandler(app, APP_TOKEN)
slack_socket_handler.connect()


def user_id_to_name(user_id: str) -> str:
    """Converts a Slack User ID into their name."""
    return app.client.users_info(user=user_id).get("user", {}).get("real_name", "")


try:
    while True:
        print(user_id_to_name(input("ID: ")))
except KeyboardInterrupt:
    print("Stopping.")
    slack_socket_handler.close()
