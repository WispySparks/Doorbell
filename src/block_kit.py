"""Helper functions for creating modals and blocks for Slack views."""

from typing import Any, Optional


def create_plain_text(text: str) -> dict[str, str]:
    return {"type": "plain_text", "text": text}


def create_mrkdwn_text(text: str) -> dict[str, str]:
    return {"type": "mrkdwn", "text": text}


def create_user_select(action_id: str, initial_user: Optional[str] = None) -> dict[str, Any]:
    result = {
        "type": "section",
        "block_id": action_id,
        "text": create_plain_text("User:"),
        "accessory": {
            "type": "users_select",
            "placeholder": create_plain_text("Select a user"),
            "action_id": action_id,
        },
    }
    if initial_user is not None:
        result["accessory"] |= {"initial_user": initial_user}
    return result


def create_multi_static_select(
    label: str, options: dict[str, str], initial_options: list[str], action_id: str
) -> dict[str, Any]:
    view_options = []
    view_initial_options = []
    for text, value in options.items():
        option = {"text": create_plain_text(text), "value": value}
        view_options.append(option)
        if text in initial_options:
            view_initial_options.append(option)
    result = {
        "type": "input",
        "block_id": action_id,
        "element": {
            "type": "multi_static_select",
            "options": view_options,
            "action_id": action_id,
        },
        "label": create_plain_text(label),
    }
    if initial_options:
        result["element"] |= {"initial_options": view_initial_options}
    return result


def create_button(text: str, action_id: str):
    return {
        "type": "actions",
        "elements": [
            {
                "type": "button",
                "text": create_plain_text(text),
                "value": text,
                "action_id": action_id,
            }
        ],
    }
