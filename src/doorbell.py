"""Contains the main code for the Doorbell Slack bot. Can be run directly to start Doorbell normally."""

import datetime as dt
import os
import re
import subprocess
import sys
import threading
from pathlib import Path
from threading import Thread
from time import sleep
from typing import Final, Optional

from pygame import mixer
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_bolt.context.say import Say
from websockets.exceptions import ConnectionClosed
from websockets.sync import server

import database
from google_calendar import GoogleCalendar
from secret import APP_TOKEN, BOT_TOKEN, SOUND_PATH
from tts import TTS

mixer.init()


# and could have a command to delete data for updates to the database structure
class Doorbell:  # TODO docopt?, calendar subscriptions + event poller
    """The Doorbell Slack bot. All of the functionality starts in mention_event()."""

    app = App(token=BOT_TOKEN)
    slack_socket_handler = SocketModeHandler(app, APP_TOKEN)
    DOORBELL_WORDS: Final = ["door", "noor", "abracadabra", "open sesame", "ding", "ring", "boop"]
    sound = mixer.Sound(SOUND_PATH)
    calendar = GoogleCalendar()
    text_to_speech = TTS()
    spicetify_client_connection: Optional[server.ServerConnection] = None

    def __init__(self, connect_to_slack: bool = True) -> None:

        if "-l" in sys.argv:
            log_dir: Final = "./logs/"
            Path(log_dir).mkdir(exist_ok=True)
            sys.stderr = sys.stdout = open(
                log_dir + dt.datetime.now().strftime("%Y-%m-%d--%H-%M-%S") + ".log", "w", encoding="utf-8", buffering=1
            )
        database.create()
        if connect_to_slack:
            self.slack_socket_handler.connect()
        self.websocket_server = server.serve(self.on_client_connection, "localhost", 8765)
        Thread(target=self.websocket_server.serve_forever, name="Websocket Server").start()
        self.closed = False
        self.restarting = False

    #! There's a deadlock somewhere
    @app.event("app_mention")
    def mention_event(self, body: dict, say: Say) -> None:
        event = body["event"]
        channel = event["channel"]
        text: str = event["text"]
        user = event["user"]
        user_name = self.app.client.users_info(user=user)["user"]["real_name"]
        args = text.lower().split()[1:]  # Ignore first word which is the mention
        case_sensitive_args = text.split()[1:]  # Needed for URLs
        print(f"Channel: {channel}, Args: {args}, User: {user_name}")

        if len(args) < 1:
            say("Hi! (Must provide a command).")
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
            event = self.calendar.get_next_event(calendar_name)
            if event is None:
                say(f"Invalid Calendar - {calendar_name} or no future events.")
                return
            name, start, _ = event
            say(f"{name} - {start.strftime(GoogleCalendar.DATE_FORMAT)}")
        elif cmd == "play":
            self.play_song(say, case_sensitive_args)
        elif cmd == "restart":
            self.restart(say)
        elif cmd == "update":
            result = subprocess.run("git pull", capture_output=True, text=True, check=False)
            subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=False)
            subprocess.run(["npm.cmd", "run", "build"], check=False, cwd="spicetify-extension/")
            subprocess.run(["spicetify", "backup", "apply"], check=False)
            subprocess.run(["spicetify", "apply"], check=False)
            say(f"{str(result.stdout)} {str(result.stderr)}")
            self.restart(say)
        elif cmd in ("exit", "stop"):
            say("Stopping.")
            self.close()
        else:
            invalid = "" if cmd == "help" else f"Invalid argument: {cmd}. "
            say(f"{invalid}Valid arguments are door, schedule, calendars, next, play, restart, update, and exit.")

    def ring_doorbell(self, say: Say, user: str, args: list[str]) -> None:
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
        if len(args) < 2:
            data = database.read()
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
            schedule: list[Optional[database.DayTuple]] = []
            active_times = args[1:]
            for day in range(7):
                time = active_times[day]
                if time == "-":
                    schedule.append(None)
                elif re.match("^([0-1][0-9]|[2][0-3]):[0-5][0-9]-([0-1][0-9]|[2][0-3]):[0-5][0-9]$", time) is None:
                    say("Invalid time format. Should be XX:XX-XX:XX in 24 hour time.")
                    return
                else:
                    start, end = time.split("-")
                    start_time = dt.time(int(start.split(":")[0]), int(start.split(":")[1]))
                    end_time = dt.time(int(end.split(":")[0]), int(end.split(":")[1]))
                    schedule.append(database.DayTuple(start_time, end_time))
            database.write(database.Data(schedule))
            say(f"Wrote schedule.\n{database.read().schedule_to_str()}")

    def calendar_subscribe(self, say: Say, channel: str, args: list[str]) -> None:
        if len(args) < 2:
            say("Must provide how many hours before to be reminded.")
        elif len(args) < 3:
            say("Must provide a calendar to subscribe to.")
        else:
            remind_time_hours = float(args[1])
            calendar_name = " ".join(args[2:])
            next_event = self.calendar.get_next_event(calendar_name)
            if next_event is None:
                say(f"Invalid calendar - {calendar_name} or no future events.")
                return
            name, start, end = next_event
            subs: list = database.read().subscriptions
            subs.append(
                {
                    "channelId": channel,
                    "calendarName": calendar_name,
                    "remindTime": remind_time_hours,
                    "nextEvent": {"name": name, "start": start.isoformat(), "end": end.isoformat()},
                }
            )
            database.write(database.Data(subscriptions=subs))
            say(f"Subscribed to {calendar_name} and reminds {str(remind_time_hours)} hours before.")

    def play_song(self, say: Say, args: list[str]) -> None:
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

    def restart(self, say: Say) -> None:
        """
        Sets a flag for consumers that Doorbell should be restarted. All restart logic is
        handled externally.
        """
        say("Restarting.")
        self.restarting = True
        self.close()

    def on_client_connection(self, client: server.ServerConnection) -> None:
        print("Spicetify has connected!")
        self.spicetify_client_connection = client
        while not self.closed:
            pass

    def close(self) -> None:
        """Disconnects from Slack and kills all threads pertaining to Doorbell."""
        self.closed = True
        self.slack_socket_handler.close()
        self.websocket_server.shutdown()


if __name__ == "__main__":
    # The main thread sits here until Doorbell is closed by a command and then joins up with
    # all the other threads that have been cleaned up by Doorbell#close(), restarting if needed
    doorbell = Doorbell()
    print("Started Doorbell!")
    try:
        while not doorbell.closed:
            pass
    except KeyboardInterrupt:
        doorbell.close()
    for thread in threading.enumerate():
        if thread == threading.current_thread() or thread.daemon:
            continue
        thread.join()
    print("Exited Doorbell.")
    if doorbell.restarting:
        os.execl(sys.executable, f"{sys.executable}", *sys.argv)
