"""Helper functions for creating modals and blocks for Slack views."""

from typing import Any


def create_plain_text(text: str) -> dict[str, str]:
    return {"type": "plain_text", "text": text}


def create_mrkdwn_text(text: str) -> dict[str, str]:
    return {"type": "mrkdwn", "text": text}


def create_user_select(action_id: str) -> dict[str, Any]:
    return {
        "type": "section",
        "text": create_plain_text("User:"),
        "accessory": {
            "type": "users_select",
            "placeholder": create_plain_text("Select a user"),
            "action_id": action_id,
        },
    }


def create_multi_static_select(action_id: str) -> dict[str, Any]:
    return {
        "type": "input",
        "element": {
            "type": "multi_static_select",
            "placeholder": create_plain_text("Placeholder"),
            "options": [
                {
                    "text": create_plain_text("Placeholder"),
                    "value": "value-0",
                },
                {
                    "text": create_plain_text("Placeholder"),
                    "value": "value-1",
                },
                {
                    "text": create_plain_text("Placeholder"),
                    "value": "value-2",
                },
            ],
            "action_id": action_id,
        },
        "label": create_plain_text("Placeholder"),
    }
