"""Allows running commands for Doorbell from the command line without using Slack."""

import json
from threading import Thread

import app


def fake_response(cmd: str) -> dict:
    """Creates a fake payload for testing Doorbell."""
    return {"event": {"channel": "None", "text": f"@Doorbell {cmd}", "user": "U05UFPWSEJH"}}


def test_doorbell() -> None:
    """Takes input from the command line and feeds it into doorbell.
    Run from a thread because app.main() is blocking."""
    print(json.dumps(app.app.client.auth_test().data, indent=4))
    while True:
        cmd = input("Command: ")
        app.mention_event(fake_response(cmd), print)  # type: ignore


Thread(target=test_doorbell, daemon=True).start()
app.main()
