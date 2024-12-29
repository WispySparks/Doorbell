"""Logic for the /roles command. Allows for assigning roles to different users and managing which roles exist."""

import random
import string
from typing import Final

from slack_bolt import Ack, App
from slack_sdk import WebClient
from slack_sdk.models.blocks import (
    ActionsBlock,
    ButtonElement,
    InputBlock,
    Option,
    PlainTextInputElement,
    SectionBlock,
    StaticMultiSelectElement,
    UserSelectElement,
)
from slack_sdk.models.views import View

import database


class RolesCommand:  # It'd be nice if it saved when you selected roles.
    """Contains all the functionality pertaining to the /roles command.
    To give your Slack app this command call register(app)."""

    VIEW_TYPE: Final[str] = "modal"
    ROOT_CALLBACK_ID: Final[str] = "roles_view"
    MANAGE_CALLBACK_ID: Final[str] = "roles_view_manage"
    VIEW_TITLE: Final[str] = "Roles"
    VIEW_SUBMIT: Final[str] = "Save"

    MANAGE_ADD_BLOCK_ID: Final[str] = "roles_manage_add"
    MANAGE_ADD_ACTION_ID: Final[str] = MANAGE_ADD_BLOCK_ID
    MANAGE_REMOVE_BLOCK_ID: Final[str] = "roles_manage_remove"
    MANAGE_REMOVE_ACTION_ID: Final[str] = MANAGE_REMOVE_BLOCK_ID

    MANAGE_BUTTON_ACTION_ID: Final[str] = "roles_manage"
    MANAGE_ROLES_BUTTON: Final[ActionsBlock] = ActionsBlock(
        elements=[ButtonElement(text="Manage Roles", action_id=MANAGE_BUTTON_ACTION_ID)]
    )

    USER_SELECT_BLOCK_ID: Final[str] = "roles_user_select"
    USER_SELECT_ACTION_ID: Final[str] = USER_SELECT_BLOCK_ID
    USER_SELECT: Final[SectionBlock] = SectionBlock(
        block_id=USER_SELECT_BLOCK_ID,
        text="User:",
        accessory=UserSelectElement(placeholder="Select a user", action_id=USER_SELECT_ACTION_ID),
    )

    ROLE_SELECT_ACTION_ID: Final[str] = "roles_role_select"

    def register(self, app: App) -> None:
        """Registers your Slack app to have a /roles command."""
        app.command("/roles")(self._roles_command)
        app.action(self.MANAGE_BUTTON_ACTION_ID)(self._roles_manage)
        app.action(self.ROLE_SELECT_ACTION_ID)(lambda ack: ack())  # Dummy because it's not an input
        app.action(self.MANAGE_REMOVE_ACTION_ID)(lambda ack: ack())  # Dummy because it's not an input
        app.action(self.USER_SELECT_ACTION_ID)(self._roles_user_select)
        app.view_submission(self.ROOT_CALLBACK_ID)(self._roles_submit)
        app.view_submission(self.MANAGE_CALLBACK_ID)(self._roles_manage_submit)

    def _roles_command(self, ack: Ack, command: dict, client: WebClient) -> None:
        ack()
        client.views_open(
            trigger_id=command["trigger_id"],
            view=View(
                type=self.VIEW_TYPE,
                callback_id=self.ROOT_CALLBACK_ID,
                title=self.VIEW_TITLE,
                blocks=[self.MANAGE_ROLES_BUTTON, self.USER_SELECT],
            ),
        )

    def _roles_manage(self, ack: Ack, body: dict, client: WebClient) -> None:
        ack()
        user = body["view"]["state"]["values"][self.USER_SELECT_BLOCK_ID][self.USER_SELECT_ACTION_ID]["selected_user"]
        options = self._generate_options(database.read().get_roles())
        blocks = [
            InputBlock(
                label="Roles to add (space separated)",
                optional=True,
                block_id=self.MANAGE_ADD_BLOCK_ID,
                element=PlainTextInputElement(
                    placeholder="Business CAD Leads ...", action_id=self.MANAGE_ADD_ACTION_ID
                ),
            )
        ]
        if options:
            blocks += [
                SectionBlock(
                    text="Roles to remove",
                    block_id=self.MANAGE_REMOVE_BLOCK_ID,
                    accessory=StaticMultiSelectElement(options=options, action_id=self.MANAGE_REMOVE_ACTION_ID),
                )
            ]
        client.views_push(
            trigger_id=body["trigger_id"],
            view=View(
                type=self.VIEW_TYPE,
                callback_id=self.MANAGE_CALLBACK_ID,
                title=self.VIEW_TITLE,
                submit=self.VIEW_SUBMIT,
                blocks=blocks,
                private_metadata=user,
            ),
        )

    def _roles_user_select(self, ack: Ack, action: dict, body: dict, client: WebClient) -> None:
        ack()
        self._roles_update_view(action["selected_user"], body["view"]["id"], client)

    def _roles_update_view(self, user: str, view_id: str, client: WebClient) -> None:
        data = database.read()
        user_roles = self._generate_options(data.get_roles_for_user(user))
        options = self._generate_options(data.get_roles())
        blocks = [self.MANAGE_ROLES_BUTTON, self.USER_SELECT]
        select_block_id = "".join(random.choices(string.ascii_letters + string.digits, k=10))
        submit = None
        if options and user != "":
            blocks += [
                SectionBlock(
                    text="Roles",
                    block_id=select_block_id,
                    accessory=StaticMultiSelectElement(
                        options=options, initial_options=user_roles, action_id=self.ROLE_SELECT_ACTION_ID
                    ),
                )
            ]
            submit = self.VIEW_SUBMIT
        client.views_update(
            view_id=view_id,
            view=View(
                type=self.VIEW_TYPE,
                callback_id=self.ROOT_CALLBACK_ID,
                title=self.VIEW_TITLE,
                submit=submit,
                blocks=blocks,
                private_metadata=select_block_id,
            ),
        )

    def _roles_submit(self, ack: Ack, view: dict, body: dict) -> None:
        private_metadata = view["private_metadata"]
        ack(
            response_action="update",
            view=View(
                type=self.VIEW_TYPE,
                callback_id=self.ROOT_CALLBACK_ID,
                title=self.VIEW_TITLE,
                submit=self.VIEW_SUBMIT,
                blocks=view["blocks"],
                private_metadata=private_metadata,
            ),
        )
        values = view["state"]["values"]
        user = values[self.USER_SELECT_BLOCK_ID][self.USER_SELECT_ACTION_ID]["selected_user"]
        selected = values.get(private_metadata, {}).get(self.ROLE_SELECT_ACTION_ID, {}).get("selected_options", [])
        roles = {role["value"] for role in selected}
        data = database.read()
        data.set_roles(user, roles)
        database.write(data)
        initiator = body.get("user", {}).get("id", "")
        print(f"{initiator} set roles for {user} to {roles}.")

    def _roles_manage_submit(self, ack: Ack, view: dict, body: dict, client: WebClient) -> None:
        ack()
        roles_to_add = view["state"]["values"][self.MANAGE_ADD_BLOCK_ID][self.MANAGE_ADD_ACTION_ID]["value"]
        if roles_to_add is None:
            roles_to_add = ""
        roles_to_add = roles_to_add.split()
        roles_to_remove = (
            view.get("state", {})
            .get("values", {})
            .get(self.MANAGE_REMOVE_BLOCK_ID, {})
            .get(self.MANAGE_REMOVE_ACTION_ID, {})
            .get("selected_options", [])
        )
        roles_to_remove = [option["value"] for option in roles_to_remove]
        data = database.read()
        for role in roles_to_add:
            data.add_role(role)
        for role in roles_to_remove:
            data.remove_role(role)
        database.write(data)
        initiator = body.get("user", {}).get("id", "")
        print(f"{initiator} added roles {roles_to_add} and removed roles {roles_to_remove}.")
        self._roles_update_view(view["private_metadata"], view["root_view_id"], client)

    def _generate_options(self, roles: set[str]) -> list[Option]:
        return [Option(text=role, value=role) for role in roles]
