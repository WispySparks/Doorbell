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
from secret import appToken, botToken, soundPath

app = App(token=botToken)
slackSocketHandler = SocketModeHandler(app, appToken)

doorbellWords: Final = ["door", "noor", "abracadabra", "open sesame", "ding", "ring", "boop"]
mixer.init()
sound: Final = mixer.Sound(soundPath)
txtToSpeech = pyttsx3.init()
txtToSpeech.setProperty("rate", 100)
calendar: Final = GoogleCalendar()
spicetifyClientConnection = None
#TODO docopt?, attempt to make code more pythonic / PEP8 (to an extent)
@app.event("app_mention")
def handleMentionEvent(body: dict, say: Say) -> None:
    event = body["event"]
    channel = event["channel"]
    text: str = event["text"]
    user = event["user"]
    userName = app.client.users_info(user=user)["user"]["real_name"]
    args = text.lower().split()[1:] # Ignore first word which is the mention
    caseSensitiveArgs = text.split()[1:] # Needed for URLs
    print("Channel: {}, Args: {}, User: {}".format(channel, args, userName))
    
    if (len(args) < 1):
        say("Hi! (Must provide a command).")
        return
    cmd = args[0]
    if (cmd in doorbellWords):
        handleDoorbell(say, userName, args)
    elif (cmd == "schedule"):
        handleSchedule(say, args)
    elif (cmd == "play"):
        playSong(say, caseSensitiveArgs)
    elif (cmd == "restart"):
        restart(say)
    elif (cmd == "update"):
        result = subprocess.run("git pull", capture_output=True, text=True)
        say(str(result.stdout) + " " + str(result.stderr))
        restart(say)
    elif (cmd == "exit" or cmd == "stop"):
        say("Stopping.")
        slackSocketHandler.close()
    else:
        say("Invalid argument: " + cmd + ". Valid arguments are door, " +
        "schedule, play, restart, update, and exit.")
        
def handleDoorbell(say: Say, user: str, args: list[str]) -> None:
    schedule = database.read().schedule
    if (not schedule):
        say("Schedule not created yet!")
        return
    date = dt.datetime.now()
    day = schedule[date.weekday()]
    if (day is not None and (day.startTime <= date.time() <= day.endTime)):
        say("Ding! (" + user + ")")
        sound.play()
        sleep(sound.get_length())
        if (txtToSpeech._inLoop):
            txtToSpeech.endLoop()
        door = "" if len(args) < 2 else args[1]
        txtToSpeech.say(user + "is at the door " + door)
        txtToSpeech.runAndWait()
    else:
        say("Sorry, currently the bot isn't supposed to run. Check the schedule? @Doorbell schedule")
            
def handleSchedule(say: Say, args: list[str]) -> None:
    if (len(args) < 2):
        data = database.read()
        if (not data.schedule):
            say("Schedule not created yet!")
        else:
            say(data.scheduleToStr())
    elif (len(args) < 8):
        say("Need to specify the times of each day that doorbell can run or use a `-` to not run that day." +
            " It starts with Monday all the way till Sunday, e.g. 14:10-16:30 - - - - 12:00-13:00 -")
    else:
        schedule: list[Optional[database.DayTuple]] = []
        activeTimes = args[1:] 
        for day in range(7):
            time = activeTimes[day]
            if (time == "-"):
                schedule.append(None)
            elif (re.match("^([0-1][0-9]|[2][0-3]):[0-5][0-9]-([0-1][0-9]|[2][0-3]):[0-5][0-9]$", time) is None):
                say("Invalid time format. Should be XX:XX-XX:XX in 24 hour time.")
                return
            else:
                start, end = time.split("-")
                startTime = dt.time(int(start.split(":")[0]), int(start.split(":")[1]))
                endTime = dt.time(int(end.split(":")[0]), int(end.split(":")[1]))        
                schedule.append(database.DayTuple(startTime, endTime))
        database.write(database.Data(schedule))
        say("Wrote schedule.\n" + database.read().scheduleToStr())
        
def handleSubscribe(say: Say, channel: str, args: list[str]) -> None: #TODO This is definitely broken
    if (len(args) < 2):
        say("Must provide how many hours before to be reminded.")
    elif (len(args) < 3):
        say("Must provide a calendar to subscribe to.")
    else:
        remindTimeHours = float(args[1])
        calendarName = " ".join(args[2:])
        nextEvent = calendar.getNextEvent(calendarName)
        if (nextEvent is None):
            say("Invalid calendar - " + calendarName + " or no future events.")
            return
        name, start, end = nextEvent
        subs: list = database.read().subscriptions
        subs.append({
            "channelId": channel,
            "calendarName": calendarName,
            "remindTime": remindTimeHours,
            "nextEvent": {
                "name": name,
                "start": start.isoformat(),
                "end": end.isoformat()
            }
        })
        database.write(database.Data(subscriptions = subs))
        say("Subscribed to " + calendarName + " and reminds " + str(remindTimeHours) + " hours before.")

def playSong(say: Say, args: list[str]) -> None:
    global spicetifyClientConnection
    if (len(args) < 2):
        say("Must give a Spotify track URL.")
        return
    if (spicetifyClientConnection is None):
        say("Spotify has not connected to Doorbell.")
        return
    songURL = args[1].replace("<", "").replace(">", "") # Links in slack are bound by angle brackets
    if (not re.match("^https://open\\.spotify\\.com/", songURL)):
        say("Invalid Spotify URL.")
        return
    try:
        spicetifyClientConnection.send(songURL)
    except ConnectionClosed:
        spicetifyClientConnection = None
        say("Doorbell has lost connection with Spotify.")
    else:
        say("Added " + songURL + " to the queue.", unfurl_links=False, unfurl_media=False)
    
def restart(say: Say) -> None:
    say("Restarting.")
    slackSocketHandler.close()
    os.execl(sys.executable, f"{sys.executable}", *sys.argv)
    
def onClientConnection(client: server.ServerConnection) -> None:
    global spicetifyClientConnection
    print("Spicetify has connected!")
    spicetifyClientConnection = client
    while not slackSocketHandler.client.closed: pass

if (__name__ == "__main__"):
    # There's three main threads/processes, the slack thread which handles all the slack event processing,
    # the websocket thread which serves the websocket server to connect to spicetify, and the main thread
    # which just sits here until the slack thread is shutdown, and then shuts down the websocket server.
    if ("-l" in sys.argv):
        logDir: Final = "./logs/"
        Path(logDir).mkdir(exist_ok=True)
        sys.stderr = sys.stdout = open(logDir + dt.datetime.now().strftime("%Y-%m-%d--%H-%M-%S") + ".log", "w", buffering=1)
    database.create()
    slackSocketHandler.connect()
    websocketServer = server.serve(onClientConnection, "localhost", 8765)
    Thread(target=websocketServer.serve_forever).start()
    print("Started Doorbell!")
    while not slackSocketHandler.client.closed: pass
    websocketServer.shutdown()
    print("Exited Doorbell.")