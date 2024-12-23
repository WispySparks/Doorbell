"""Contains the main code for the Doorbell Slack bot."""

import datetime as dt
import json
import random
import re
import string
import subprocess
import sys
from pathlib import Path
from threading import Thread
from time import sleep
from typing import Final, Optional

from pygame import mixer
from slack_bolt import Ack, App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_bolt.context.say import Say
from slack_sdk import WebClient
from websockets.exceptions import ConnectionClosed
from websockets.sync import server

import block_kit
import database
from event_poller import EventPoller
from google_calendar import GoogleCalendar
from secret import APP_TOKEN, BOT_TOKEN, SOUND_PATH
from tts import TTS

mixer.init()


class Doorbell:  # TODO: Scuffed usergroups, modals
    """The Doorbell Slack bot. All of the functionality starts in mention_event()."""

    app = App(token=BOT_TOKEN)
    slack_socket_handler = SocketModeHandler(app, APP_TOKEN)
    DOORBELL_WORDS: Final = ["door", "noor", "abracadabra", "open sesame", "ding", "ring", "boop"]
    sound = mixer.Sound(SOUND_PATH)
    calendar = GoogleCalendar()
    text_to_speech = TTS()
    spicetify_client_connection: Optional[server.ServerConnection] = None

    def __init__(self) -> None:
        if "-l" in sys.argv:
            log_dir: Final = "./logs/"
            Path(log_dir).mkdir(exist_ok=True)
            sys.stderr = sys.stdout = open(
                log_dir + dt.datetime.now().strftime("%Y-%m-%d--%H-%M-%S") + ".log", "w", encoding="utf-8", buffering=1
            )
        self.app.event("app_mention")(self.mention_event)
        self.app.event("message")(self.message_event)

        self.app.command("/roles")(self.roles_command)
        self.app.action("roles_manage")(self.roles_manage)
        self.app.action("roles_user_select")(self.roles_user_select)
        self.app.view_submission("roles_view")(self.roles_submit)
        self.app.view_submission("roles_view_manage")(self.roles_manage_submit)

        database.create()
        database.check_for_corruption()
        self._connect_to_slack()
        self.event_poller = EventPoller(5, self)
        self.event_poller.start()
        self.websocket_server = server.serve(self._on_client_connection, "localhost", 8765)
        Thread(target=self.websocket_server.serve_forever, name="Websocket Server").start()
        self.closed = False
        self.restarting = False

    def mention_event(self, body: dict, say: Say) -> None:
        """The callback function for the Slack mention event, https://api.slack.com/events/app_mention."""
        event = body["event"]
        channel_id = event["channel"]
        text: str = event["text"]
        user = event["user"]
        user_name = self.app.client.users_info(user=user)["user"]["real_name"]
        args = text.lower().split()[1:]  # Ignore first word which is the mention
        case_sensitive_args = text.split()[1:]  # Needed for URLs
        print(f"Channel: {channel_id}/{self.get_channel_name(channel_id)}, Args: {args}, User: {user_name}")

        if len(args) < 1:
            say("Hi! (Try using 'help' to get a list of commands).")
            return
        cmd = args[0]
        if cmd in self.DOORBELL_WORDS:
            self.ring_doorbell(say, user_name, args)
        elif cmd == "schedule":
            self.manage_schedule(say, args)
        elif cmd == "calendars":
            say("Calendars: " + ", ".join(list(self.calendar.calendars)))
        elif cmd == "next":
            if len(case_sensitive_args) < 2:
                say("Need to provide a calendar.")
                return
            calendar_name = " ".join(case_sensitive_args[1:])
            if calendar_name not in self.calendar.calendars:
                say(f"Invalid calendar '{calendar_name}'.")
                return
            event = self.calendar.get_next_event(calendar_name)
            if event is None:
                say(f"{calendar_name} has no future events.")
                return
            say(f"{event.name} - {event.start.strftime(GoogleCalendar.DATE_FORMAT)}")
        elif cmd == "subscribe":
            self.calendar_subscribe(say, channel_id, case_sensitive_args)
        elif cmd == "unsubscribe":
            if len(case_sensitive_args) < 2:
                say("Must provide a calendar to unsubscribe from.")
            calendar_name = " ".join(case_sensitive_args[1:])
            data = database.read()
            subs = data.subscriptions_for_channel(channel_id)
            for sub in subs:
                if sub.calendar_name == calendar_name:
                    data.subscriptions.remove(sub)
                    database.write(data)
                    say(f"Unsubscribed from {calendar_name}.")
                    break
            else:
                say("No subscription to that calendar.")
        elif cmd == "subscriptions":
            say(database.read().subscriptions_to_str(channel_id))
        elif cmd == "all_subscriptions":
            say(database.read().all_subscriptions_to_str(self))
        elif cmd == "play":
            self.play_song(say, case_sensitive_args)
        elif cmd == "restart":
            self.restart(say)
        elif cmd == "update":
            say("Updating.")
            result = subprocess.run("git pull", capture_output=True, text=True, check=False)
            subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=False)
            subprocess.run(["npm.cmd", "run", "build"], check=False, cwd="spicetify-extension/")
            subprocess.run(["spicetify", "backup", "apply"], check=False)
            subprocess.run(["spicetify", "apply"], check=False)
            say(f"{result.stdout.strip()} {result.stderr.strip()}", unfurl_links=False, unfurl_media=False)
            self.restart(say)
        elif cmd == "backup":
            say("Here ya go boss.")
            self.upload_file(channel_id, bytes(database.get_copy()), database.FILE_PATH)
        elif cmd == "version":
            result = subprocess.run("git rev-parse HEAD", capture_output=True, text=True, check=False)
            say(f"Doorbell is currently on commit {result.stdout.strip()}.")
        elif cmd in ("exit", "stop"):
            say("Stopping.")
            self.close()
        else:
            invalid = "" if cmd == "help" else f"Invalid argument: {cmd}. "
            say(
                f"{invalid}Valid arguments are door, schedule, calendars, next, subscribe,"
                " unsubscribe, subscriptions, all_subscriptions, play, restart, update, backup, version, and exit."
            )

    def message_event(self, body: dict) -> None:
        event = body["event"]
        text: str = event["text"]
        lower_text = text.lower()
        data = database.read()
        roles = data.get_roles()
        users = set()
        for role in roles:
            if "@" + role in lower_text:
                users.update(data.get_users_for_role(role))
        print(users)
        for user in users:
            pass
            # self.post_message(user, text)

    def roles_command(self, ack: Ack, command: dict, client: WebClient):
        ack()
        action_id = "roles_user_select"
        client.views_open(
            trigger_id=command["trigger_id"],
            view=block_kit.create_view(
                callback_id="roles_view",
                title="Roles",
                blocks=[
                    block_kit.create_button(text="Manage Roles", action_id="roles_manage"),
                    block_kit.create_user_select(action_id=action_id, block_id=action_id),
                ],
            ),
        )

    def roles_manage(self, ack: Ack, body: dict, client: WebClient):
        ack()
        text_id = "add"
        select_id = "remove"
        options = {role: role for role in database.read().get_roles()}
        blocks = [
            block_kit.create_plain_text_input(
                label="Roles to add (space separated)",
                optional=True,
                placeholder="Business CAD Leads ...",
                action_id=text_id,
                block_id=text_id,
            )
        ]
        if options:
            blocks.append(
                block_kit.create_multi_static_select(
                    label="Roles to remove",
                    options=options,
                    initial_options=[],
                    action_id=select_id,
                    block_id=select_id,
                )
            )
        client.views_push(
            trigger_id=body["trigger_id"],
            view=block_kit.create_view(
                callback_id="roles_view_manage",
                title="Roles",
                submit="Save",
                blocks=blocks,
            ),
        )

    def roles_user_select(self, ack: Ack, action: dict, body: dict, client: WebClient):
        ack()
        user = action["selected_user"]
        data = database.read()
        roles = data.get_roles()
        user_roles = list(data.get_roles_for_user(user))
        options = {role: role for role in roles}
        view = body["view"]
        blocks = [
            block_kit.create_button(text="Manage Roles", action_id="roles_manage"),
            block_kit.create_user_select(action_id=action["action_id"], block_id=action["block_id"]),
        ]
        if options:
            blocks.append(
                block_kit.create_multi_static_select(
                    label="Roles",
                    options=options,
                    initial_options=user_roles,
                    action_id="roles_role_select",
                    block_id=f"{user}_select",
                )
            )
        client.views_update(
            view_id=view["id"],
            view=block_kit.create_view(callback_id=view["callback_id"], title="Roles", submit="Save", blocks=blocks),
        )

    def roles_submit(self, ack: Ack, view: dict):
        action_id = "roles_user_select"
        # TODO maybe just keep the multi selector there / we could reuse the whole blocks
        ack(
            response_action="update",
            view=block_kit.create_view(
                callback_id="roles_view",
                title="Roles",
                blocks=[
                    block_kit.create_button(text="Manage Roles", action_id="roles_manage"),
                    block_kit.create_user_select(action_id=action_id, block_id=action_id),
                ],
            ),
        )
        state = view["state"]["values"]
        user = state[action_id][action_id]["selected_user"]
        selected = state.get(f"{user}_select", {}).get("roles_role_select", {}).get("selected_options", [])
        roles = {role["value"] for role in selected}
        data = database.read()
        data.set_roles(user, roles)
        database.write(data)

    def roles_manage_submit(self, ack: Ack, view: dict):
        # TODO needs to reload the selecter on the view below
        ack()
        roles_to_add = view["state"]["values"]["add"]["add"]["value"]
        if roles_to_add is None:
            roles_to_add = ""
        roles_to_add = roles_to_add.split()
        roles_to_remove = (
            view.get("state", {}).get("values", {}).get("remove", {}).get("remove", {}).get("selected_options", [])
        )
        data = database.read()
        for role in roles_to_add:
            data.add_role(role)
        for role in roles_to_remove:
            data.remove_role(role["value"])
        database.write(data)

    def ring_doorbell(self, say: Say, user: str, args: list[str]) -> None:
        """Rings the doorbell and activates text to speech if the schedule allows it."""
        schedule = database.read().schedule
        if not schedule:
            say("Schedule not created yet!")
            return
        date = dt.datetime.now()
        day = schedule[date.weekday()]
        if day is not None and (day.start_time <= date.time() <= day.end_time):
            say(f"Ding! ({user})")
            self.sound.play()
            sleep(self.sound.get_length())
            door = "" if len(args) < 2 else args[1]
            if not re.match(r"^\d{2}[a-z]$", door):
                door = ""
            self.text_to_speech.say(f"{user} is at the door {door}", blocking=True)
        else:
            say("Sorry, currently Doorbell isn't supposed to run. Check the schedule? @Doorbell schedule")

    def manage_schedule(self, say: Say, args: list[str]) -> None:
        """Either reads the current schedule to the user or accepts a new schedule to write from the user."""
        data = database.read()
        if len(args) < 2:
            if not data.schedule:
                say("Schedule not created yet!")
            else:
                say(data.schedule_to_str())
        elif len(args) < 8:
            say(
                "Need to specify the times of each day that doorbell can run or use a `-` to not run that day."
                + " It starts with Monday all the way till Sunday, e.g. 14:10-16:30 - - - - 12:00-13:00 -"
            )
        else:
            new_schedule: list[Optional[database.DaySchedule]] = []
            active_times = args[1:]
            for day in range(7):
                time = active_times[day]
                if time == "-":
                    new_schedule.append(None)
                elif re.match("^([0-1][0-9]|[2][0-3]):[0-5][0-9]-([0-1][0-9]|[2][0-3]):[0-5][0-9]$", time) is None:
                    say("Invalid time format. Should be XX:XX-XX:XX in 24 hour time.")
                    return
                else:
                    start, end = time.split("-")
                    start_time = dt.time(int(start.split(":")[0]), int(start.split(":")[1]))
                    end_time = dt.time(int(end.split(":")[0]), int(end.split(":")[1]))
                    new_schedule.append(database.DaySchedule(start_time, end_time))
            data.schedule = new_schedule
            database.write(data)
            say(f"Wrote schedule.\n{database.read().schedule_to_str()}")

    def calendar_subscribe(self, say: Say, channel: str, args: list[str]) -> None:
        """Subscribes to a google calendar to be reminded of any future events."""
        if len(args) < 2:
            say("Must provide how many hours before to be reminded.")
        elif len(args) < 3:
            say("Must provide a calendar to subscribe to.")
        else:
            try:
                remind_time = dt.timedelta(hours=float(args[1]))
            except ValueError:
                say(f"First argument must be a number of hours. '{args[1]}' could not be converted to a float.")
                return
            calendar_name = " ".join(args[2:])
            if calendar_name not in self.calendar.calendars:
                say(f"Invalid calendar '{calendar_name}'.")
                return
            next_event = self.calendar.get_next_event(calendar_name)
            data = database.read()
            subs = data.subscriptions_for_channel(channel)
            for sub in subs:
                if sub.calendar_name == calendar_name:
                    say("Can't subscribe to the same calendar multiple times in the same channel.")
                    return
            data.subscriptions.append(
                database.Subscription(
                    channel, calendar_name, remind_time, next_event, dt.datetime.now().astimezone(dt.timezone.utc)
                )
            )
            database.write(data)
            say(f"Subscribed to {calendar_name} and reminds {str(remind_time.total_seconds() / 3600)} hours before.")

    def play_song(self, say: Say, args: list[str]) -> None:
        """Adds a Spotify song to the queue if Spotify is open."""
        if len(args) < 2:
            say("Must give a Spotify track URL.")
            return
        if self.spicetify_client_connection is None:
            say("Spotify has not connected to Doorbell.")
            return
        song_url = args[1].replace("<", "").replace(">", "")  # Links in slack are bound by angle brackets
        if not re.match(r"^https://open.spotify.com/", song_url):
            say("Invalid Spotify URL.")
            return
        try:
            self.spicetify_client_connection.send(song_url)
        except ConnectionClosed:
            self.spicetify_client_connection = None
            say("Doorbell has lost connection with Spotify.")
        else:
            say(f"Added {song_url} to the queue.", unfurl_links=False, unfurl_media=False)

    def _on_client_connection(self, client: server.ServerConnection) -> None:
        print("\nSpicetify has connected!")
        self.spicetify_client_connection = client
        while not self.closed:
            pass

    def _connect_to_slack(self) -> None:
        self.slack_socket_handler.connect()

    def get_channel_name(self, channel_id: str) -> str:
        """Returns the name of Slack channel given its channel id."""
        result = self.app.client.conversations_info(channel=channel_id)
        if result["channel"] is not None:
            return result["channel"].get("name", "None")
        return "None"

    def post_message(self, channel_id: str, message: str) -> None:
        """Posts a message to the specified Slack channel."""
        self.app.client.chat_postMessage(channel=channel_id, text=message, unfurl_links=False, unfurl_media=False)

    def upload_file(self, channel_id: str, file: bytes, name: str) -> None:
        """Uploads a file to the specified Slack channel."""
        self.app.client.files_upload_v2(channel=channel_id, file=file, filename=name)

    def restart(self, say: Say) -> None:
        """Sets a flag for consumers that Doorbell should be restarted. All restart logic is
        handled externally.
        """
        say("Restarting.")
        self.restarting = True
        self.close()

    def close(self) -> None:
        """Disconnects from Slack and kills all threads pertaining to Doorbell."""
        self.closed = True
        self.slack_socket_handler.close()
        self.websocket_server.shutdown()
        self.event_poller.stop()
