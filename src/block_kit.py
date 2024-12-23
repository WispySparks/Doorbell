"""Helper functions for creating modals and blocks for Slack views."""

from typing import Any, Optional


def create_plain_text(text: str) -> dict[str, str]:
    return {"type": "plain_text", "text": text}


def create_mrkdwn_text(text: str) -> dict[str, str]:
    return {"type": "mrkdwn", "text": text}


def create_user_select(*, action_id: str, block_id: str, initial_user: Optional[str] = None) -> dict[str, Any]:
    result = {
        "type": "section",
        "block_id": block_id,
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
    *,
    label: str,
    options: dict[str, str],
    initial_options: list[str],
    action_id: Optional[str] = None,
    block_id: Optional[str] = None,
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
        "optional": True,
        "element": {
            "type": "multi_static_select",
            "options": view_options,
        },
        "label": create_plain_text(label),
    }
    if initial_options:
        result["element"] |= {"initial_options": view_initial_options}
    if action_id:
        result["element"] |= {"action_id": action_id}
    if block_id:
        result |= {"block_id": block_id}
    return result


def create_button(*, text: str, action_id: str) -> dict[str, Any]:
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


def create_plain_text_input(
    *,
    label: str,
    optional: bool = False,
    placeholder: Optional[str] = None,
    action_id: Optional[str] = None,
    block_id: Optional[str] = None,
):
    result = {
        "type": "input",
        "optional": optional,
        "label": create_plain_text(label),
        "element": {"type": "plain_text_input"},
    }
    if placeholder:
        result["element"] |= {"placeholder": create_plain_text(placeholder)}
    if action_id:
        result["element"] |= {"action_id": action_id}
    if block_id:
        result |= {"block_id": block_id}
    return result


def create_view(
    *, callback_id: str, title: str, blocks: list, submit: Optional[str] = None, private_metadata: Optional[str] = None
) -> dict[str, Any]:
    result = {
        "type": "modal",
        "callback_id": callback_id,
        "title": create_plain_text(title),
        "blocks": blocks,
    }
    if submit is not None:
        result |= {"submit": create_plain_text(submit)}
    if private_metadata is not None:
        result |= {"private_metadata": private_metadata}
    return result
