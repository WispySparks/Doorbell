"""Allows running commands for Doorbell from the command line for easy testing without using Slack."""

import json
import sys
from threading import Thread

sys.path.append("src/")
import app


def fake_response(cmd: str) -> dict:
    """Creates a fake payload for testing the bot."""
    return {"event": {"channel": "None", "text": f"@Doorbell {cmd}", "user": "U05UFPWSEJH"}}


def test_doorbell() -> None:
    """Takes input from the command line and feeds it into doorbell. Run from a thread because app.main() is blocking."""
    while not app.slack_socket_handler.client.is_connected():
        pass
    print(json.dumps(app.app.client.auth_test().data, indent=4))
    while not app.slack_socket_handler.client.closed:
        cmd = input("Command: ")
        app.mention_event(fake_response(cmd), print)  # type: ignore


Thread(target=test_doorbell, daemon=True).start()
app.main()
