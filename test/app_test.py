"""Allows running commands for Doorbell from the command line without using Slack."""

import json
import threading

from doorbell import Doorbell


def fake_response(text: str) -> dict:
    """Creates a fake payload for testing Doorbell."""
    return {"event": {"channel": "None", "text": f"@Doorbell {text}", "user": "U05UFPWSEJH"}}


def print_ignore_kwargs(*args, **_):
    """Use the print function while ignoring any keyword arguments."""
    print(*args)


doorbell = Doorbell(False)
print("Started Doorbell!")
print(json.dumps(doorbell.app.client.auth_test().data, indent=4))
try:
    while not doorbell.closed:
        cmd = input("Command: ")
        doorbell.mention_event(fake_response(cmd), print_ignore_kwargs)  # type: ignore
except KeyboardInterrupt:
    doorbell.close()
for thread in threading.enumerate():
    if thread == threading.current_thread() or thread.daemon:
        continue
    thread.join()
if doorbell.restarting:
    print("Restarting isn't available for Doorbell CLI.")
print("Exited Doorbell.")
