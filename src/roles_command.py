"""Logic for the /roles command. Allows for assigning roles to different users and managing which roles exist."""

import random
import string

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


class RolesCommand:
    """Contains all the functionality pertaining to the /roles command.
    To give your Slack app this command call register(app)."""

    view_type = "modal"
    root_callback_id = "roles_view"
    manage_callback_id = "roles_view_manage"
    view_title = "Roles"
    view_submit = "Save"

    manage_add_block_id = "roles_manage_add"
    manage_add_action_id = "roles_manage_add"
    manage_remove_block_id = "roles_manage_remove"
    manage_remove_action_id = "roles_manage_remove"

    manage_button_action_id = "roles_manage"
    manage_roles_button = ActionsBlock(elements=[ButtonElement(text="Manage Roles", action_id=manage_button_action_id)])

    user_select_block_id = "roles_user_select"
    user_select_action_id = user_select_block_id
    user_select = SectionBlock(
        block_id=user_select_block_id,
        text="User:",
        accessory=UserSelectElement(placeholder="Select a user", action_id=user_select_action_id),
    )

    role_select_action_id = "roles_role_select"

    def register(self, app: App) -> None:
        """Registers your Slack app to have a /roles command."""
        app.command("/roles")(self._roles_command)
        app.action(self.manage_button_action_id)(self._roles_manage)
        app.action(self.role_select_action_id)(lambda ack: ack())  # Dummy because it's not an input
        app.action("remove")(lambda ack: ack())  # Dummy because it's not an input
        app.action(self.user_select_action_id)(self._roles_user_select)
        app.view_submission(self.root_callback_id)(self._roles_submit)
        app.view_submission(self.manage_callback_id)(self._roles_manage_submit)

    def _roles_command(self, ack: Ack, command: dict, client: WebClient) -> None:
        ack()
        client.views_open(
            trigger_id=command["trigger_id"],
            view=View(
                type=self.view_type,
                callback_id=self.root_callback_id,
                title=self.view_title,
                blocks=[self.manage_roles_button, self.user_select],
            ),
        )

    def _roles_manage(self, ack: Ack, body: dict, client: WebClient) -> None:
        ack()
        user = body["view"]["state"]["values"][self.user_select_block_id][self.user_select_action_id]["selected_user"]
        options = [Option(text=role, value=role) for role in database.read().get_roles()]
        blocks = [
            InputBlock(
                label="Roles to add (space separated)",
                optional=True,
                block_id=self.manage_add_block_id,
                element=PlainTextInputElement(
                    placeholder="Business CAD Leads ...", action_id=self.manage_add_action_id
                ),
            )
        ]
        if options:
            blocks += [
                SectionBlock(
                    text="Roles to remove",
                    block_id=self.manage_remove_block_id,
                    accessory=StaticMultiSelectElement(options=options, action_id=self.manage_remove_action_id),
                )
            ]
        client.views_push(
            trigger_id=body["trigger_id"],
            view=View(
                type=self.view_type,
                callback_id=self.manage_callback_id,
                title=self.view_title,
                submit=self.view_submit,
                blocks=blocks,
                private_metadata=user,
            ),
        )

    def _roles_user_select(self, ack: Ack, action: dict, body: dict, client: WebClient) -> None:
        ack()
        self._roles_update_view(action["selected_user"], body["view"]["id"], client)

    def _roles_update_view(self, user: str, view_id: str, client: WebClient) -> None:
        data = database.read()
        roles = data.get_roles()
        user_roles = [Option(text=role, value=role) for role in data.get_roles_for_user(user)]
        options = [Option(text=role, value=role) for role in roles]
        blocks = [self.manage_roles_button, self.user_select]
        select_block_id = "".join(random.choices(string.ascii_letters + string.digits, k=10))
        submit = None
        if options and user != "":
            blocks += [
                SectionBlock(
                    text="Roles",
                    block_id=select_block_id,
                    accessory=StaticMultiSelectElement(
                        options=options, initial_options=user_roles, action_id=self.role_select_action_id
                    ),
                )
            ]
            submit = self.view_submit
        client.views_update(
            view_id=view_id,
            view=View(
                type=self.view_type,
                callback_id=self.root_callback_id,
                title=self.view_title,
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
                type=self.view_type,
                callback_id=view["callback_id"],
                title=self.view_title,
                submit=self.view_submit,
                blocks=view["blocks"],
                private_metadata=private_metadata,
            ),
        )
        values = view["state"]["values"]
        user = values[self.user_select_block_id][self.user_select_action_id]["selected_user"]
        selected = values.get(private_metadata, {}).get(self.role_select_action_id, {}).get("selected_options", [])
        roles = {role["value"] for role in selected}
        data = database.read()
        data.set_roles(user, roles)
        database.write(data)
        initiator = body.get("user", {}).get("id", "")
        print(f"{initiator} set roles for {user} to {roles}.")

    def _roles_manage_submit(self, ack: Ack, view: dict, body: dict, client: WebClient) -> None:
        ack()
        roles_to_add = view["state"]["values"][self.manage_add_block_id][self.manage_add_action_id]["value"]
        if roles_to_add is None:
            roles_to_add = ""
        roles_to_add = roles_to_add.split()
        roles_to_remove = (
            view.get("state", {})
            .get("values", {})
            .get(self.manage_remove_block_id, {})
            .get(self.manage_remove_action_id, {})
            .get("selected_options", [])
        )
        data = database.read()
        for role in roles_to_add:
            data.add_role(role)
        for role in roles_to_remove:
            data.remove_role(role["value"])
        database.write(data)
        initiator = body.get("user", {}).get("id", "")
        print(f"{initiator} added roles {roles_to_add} and removed roles {roles_to_remove}.")
        self._roles_update_view(view["private_metadata"], view["root_view_id"], client)
