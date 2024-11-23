"""Allows running commands for Doorbell from the command line without using Slack.
A command prefixed with # switches into that channel e.g. '#blueberry'."""

import json
import threading

from doorbell import Doorbell


def fake_response(text: str, channel_id: str) -> dict:
    """Creates a fake payload for testing Doorbell."""
    return {"event": {"channel": channel_id, "text": f"@Doorbell {text}", "user": "U05UFPWSEJH"}}


def print_ignore_kwargs(*args, **_):
    """Use the print function while ignoring any keyword arguments."""
    print(*args)


def main() -> None:
    """Runs the Doorbell CLI."""
    doorbell = Doorbell(False)
    print("Started Doorbell!")
    print(json.dumps(doorbell.app.client.auth_test().data, indent=4))
    try:
        channel = "none"
        while not doorbell.closed:
            cmd = input("Command: ")
            if cmd.startswith("#"):
                channel = cmd[1:]
                continue
            doorbell.mention_event(fake_response(cmd, channel), print_ignore_kwargs)  # type: ignore
    except KeyboardInterrupt:
        doorbell.close()
    for thread in threading.enumerate():
        if thread == threading.current_thread() or thread.daemon:
            continue
        thread.join()
    if doorbell.restarting:
        print("Restarting isn't available for Doorbell CLI.")
    print("Exited Doorbell.")


if __name__ == "__main__":
    main()
