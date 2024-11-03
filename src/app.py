import datetime as dt
import os
import re
import subprocess
import sys
from pathlib import Path
from threading import Thread
from time import sleep
from typing import Final, Optional

import pyttsx3
from pygame import mixer
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_bolt.context.say import Say
from websockets.exceptions import ConnectionClosed
from websockets.sync import server

import database
from google_calendar import GoogleCalendar
from secret import APP_TOKEN, BOT_TOKEN, SOUND_PATH

mixer.init()

app = App(token=BOT_TOKEN)
slack_socket_handler = SocketModeHandler(app, APP_TOKEN)
DOORBELL_WORDS: Final = ["door", "noor", "abracadabra", "open sesame", "ding", "ring", "boop"]
sound = mixer.Sound(SOUND_PATH)
calendar = GoogleCalendar()
txt_to_speech = pyttsx3.init()
txt_to_speech.setProperty("rate", 100)
spicetify_client_connection: Optional[server.ServerConnection] = None


@app.event("app_mention")  # TODO google_calendar(calendars next subscribe) docopt?, attempt to make code more pythonic
def mention_event(body: dict, say: Say) -> None:
    event = body["event"]
    channel = event["channel"]
    text: str = event["text"]
    user = event["user"]
    user_name = app.client.users_info(user=user)["user"]["real_name"]
    args = text.lower().split()[1:]  # Ignore first word which is the mention
    case_sensitive_args = text.split()[1:]  # Needed for URLs
    print(f"Channel: {channel}, Args: {args}, User: {user_name}")

    if len(args) < 1:
        say("Hi! (Must provide a command).")
        return
    cmd = args[0]
    if cmd in DOORBELL_WORDS:
        doorbell(say, user_name, args)
    elif cmd == "schedule":
        manage_schedule(say, args)
    elif cmd == "play":
        play_song(say, case_sensitive_args)
    elif cmd == "restart":
        restart(say)
    elif cmd == "update":
        result = subprocess.run("git pull", capture_output=True, text=True, check=False)
        say(str(result.stdout) + " " + str(result.stderr))
        restart(say)
    elif cmd in ("exit", "stop"):
        say("Stopping.")
        slack_socket_handler.close()
    else:
        say("Invalid argument: " + cmd + ". Valid arguments are door, " + "schedule, play, restart, update, and exit.")


def doorbell(say: Say, user: str, args: list[str]) -> None:
    schedule = database.read().schedule
    if not schedule:
        say("Schedule not created yet!")
        return
    date = dt.datetime.now()
    day = schedule[date.weekday()]
    if day is not None and (day.start_time <= date.time() <= day.end_time):
        say("Ding! (" + user + ")")
        sound.play()
        sleep(sound.get_length())
        door = "" if len(args) < 2 else args[1]
        if not re.match(r"^\d{2}[a-z]$", door):
            door = ""
        txt_to_speech.say(user + "is at the door " + door)
        txt_to_speech.runAndWait()
        txt_to_speech.stop()
    else:
        say("Sorry, currently the bot isn't supposed to run. Check the schedule? @Doorbell schedule")


def manage_schedule(say: Say, args: list[str]) -> None:
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
        say("Wrote schedule.\n" + database.read().schedule_to_str())


def calendar_subscribe(say: Say, channel: str, args: list[str]) -> None:  # TODO This is definitely broken
    if len(args) < 2:
        say("Must provide how many hours before to be reminded.")
    elif len(args) < 3:
        say("Must provide a calendar to subscribe to.")
    else:
        remind_time_hours = float(args[1])
        calendar_name = " ".join(args[2:])
        next_event = calendar.get_next_event(calendar_name)
        if next_event is None:
            say("Invalid calendar - " + calendar_name + " or no future events.")
            return
        name, start, end = next_event
        subs: list = database.read().subscriptions
        subs.append(
            {
                "channelId": channel,
                "calendarName": calendar,
                "remindTime": remind_time_hours,
                "nextEvent": {"name": name, "start": start.isoformat(), "end": end.isoformat()},
            }
        )
        database.write(database.Data(subscriptions=subs))
        say("Subscribed to " + calendar_name + " and reminds " + str(remind_time_hours) + " hours before.")


def play_song(say: Say, args: list[str]) -> None:
    global spicetify_client_connection
    if len(args) < 2:
        say("Must give a Spotify track URL.")
        return
    if spicetify_client_connection is None:
        say("Spotify has not connected to Doorbell.")
        return
    song_url = args[1].replace("<", "").replace(">", "")  # Links in slack are bound by angle brackets
    if not re.match("^https://open\\.spotify\\.com/", song_url):
        say("Invalid Spotify URL.")
        return
    try:
        spicetify_client_connection.send(song_url)
    except ConnectionClosed:
        spicetify_client_connection = None
        say("Doorbell has lost connection with Spotify.")
    else:
        say("Added " + song_url + " to the queue.", unfurl_links=False, unfurl_media=False)


def restart(say: Say) -> None:
    say("Restarting.")
    slack_socket_handler.close()
    os.execl(sys.executable, f"{sys.executable}", *sys.argv)


def on_client_connection(client: server.ServerConnection) -> None:
    global spicetify_client_connection
    print("Spicetify has connected!")
    spicetify_client_connection = client
    while not slack_socket_handler.client.closed:
        pass


if __name__ == "__main__":
    # There's three main threads/processes, the slack thread which handles all the slack event processing,
    # the websocket thread which serves the websocket server to connect to spicetify, and the main thread
    # which just sits here until the slack thread is shutdown, and then shuts down the websocket server.
    if "-l" in sys.argv:
        LOG_DIR: Final = "./logs/"
        Path(LOG_DIR).mkdir(exist_ok=True)
        with open(
            LOG_DIR + dt.datetime.now().strftime("%Y-%m-%d--%H-%M-%S") + ".log", "w", encoding="utf-8", buffering=1
        ) as file:
            sys.stderr = sys.stdout = file
    database.create()
    slack_socket_handler.connect()
    websocketServer = server.serve(on_client_connection, "localhost", 8765)
    Thread(target=websocketServer.serve_forever).start()
    print("Started Doorbell!")
    while not slack_socket_handler.client.closed:
        pass
    websocketServer.shutdown()
    print("Exited Doorbell.")
