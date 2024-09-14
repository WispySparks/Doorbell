import json
import re
import sys
from datetime import datetime, time
from pathlib import Path
from threading import Lock
from time import sleep
from typing import Any, Final

import pyttsx3
from pygame import mixer
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from classes import EventPoller, GoogleCalendar
from secret import appToken, botToken, soundPath

app = App(token=botToken)

doorbellWords: Final = ["door", "noor", "abracadabra", "open sesame", "ding", "ring", "boop"]
dataPath: Final = "data.json"
mixer.init()
sound: Final = mixer.Sound(soundPath)
engine = pyttsx3.init()
engine.setProperty('rate', 100)
calendar: Final = GoogleCalendar()
eventPoller: Final = EventPoller(60)
lock: Final = Lock()

@app.event("app_mention")
def handleMentionEvent(event, say) -> None:
    channel = event["channel"]
    text: str = event["text"]
    user = event["user"]
    userName = app.client.users_info(user=user)["user"]["realname"]
    args = text.split()[1:] # Ignore first word which is the mention
    print("Channel: {}, Args: {}, User: {}".format(channel, args, userName))
    
    if (len(args) < 1):
        say("Hi! (Must provide a command).")
        return
    cmd = args[0].lower()
    if (cmd in doorbellWords):
        handleDoorbell(say, userName, args)
    elif (cmd == "schedule"):
        handleSchedule(say, args)
    # elif (cmd == "calendars"):
    #     say(", ".join(list(calendar.calendars.keys())))
    # elif (cmd == "next"):
    #     if (len(args) < 2):
    #         say("Need to provide a calendar.")
    #         return
    #     calendarName = " ".join(args[1:])
    #     nextEvent = calendar.getNextEvent(calendarName)
    #     if (nextEvent is None):
    #         say("Invalid Calendar - " + calendarName + " or no future events.")
    #         return
    #     name, start, _ = nextEvent
    #     say(name + " - " + start.strftime(GoogleCalendar.dateFormat))
    elif (cmd == "subscribe"):
        handleSubscribe(say, channel, args)
    elif (cmd == "restart"):
        say("Restarting.")
        raise Exception("Restarting bot.")
    elif (cmd == "exit" or cmd == "die"):
        say("Stopping.")
        handleExit()
    else:
        say("Invalid argument: " + cmd + ". Valid arguments are door, " +
        "schedule, calendars, next, subscribe(not fully impl), restart, and exit.")
        
def handleDoorbell(say, user: str, args) -> None:
    schedule = readData()
    days = schedule.get("days")
    time = schedule.get("time")
    if (days is None or time is None):
        say("Schedule not created yet!")
        return
    date = datetime.now()
    isCorrectDay = int(list(days)[date.weekday()]) == 1
    door = "" if len(args) < 2 else args[1]
    if (isCorrectDay and isCorrectTime(time)):
        say("Ding! (" + user + ")")
        sound.play()
        sleep(sound.get_length())
        engine.say(user + "is at the door " + door)
        engine.runAndWait()
    else:
        say("Sorry, currently the bot isn't supposed to run. Check the schedule? @Doorbell schedule")
            
def handleSchedule(say, args: list[str]) -> None:
    if (len(args) < 2):
        schedule = readData()
        if (schedule.get("days") is None or schedule.get("time") is None):
            say("Schedule not created yet!")
        else:
            say(getFormattedSchedule(schedule))
    elif (len(args) < 3):
        say("Need an argument for days and an argument for time.")
    else:
        days = args[1]
        time = args[2]
        if (re.match("^[01]{7}$", days) is None):
            say("Invalid days format. List 0's and 1's for the days starting at Monday.")
            return
        if (re.match("^([0-1][0-9]|[2][0-3]):[0-5][0-9]-([0-1][0-9]|[2][0-3]):[0-5][0-9]$", time) is None):
            say("Invalid time format. Should be XX:XX-XX:XX.")
            return
        say("Wrote schedule.")
        writeData(days, time)
        say(getFormattedSchedule(readData()))
        
def handleSubscribe(say, channel: str, args: list[str]) -> None:
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
        subs: list = readData().get("subscriptions", [])
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
        writeData(subscriptions = subs)
        say("Subscribed to " + calendarName + " and reminds " + str(remindTimeHours) + " hours before.")
        
def isCorrectTime(t: str) -> bool:
    currentTime = datetime.now().time()
    start = t.split("-")[0]
    end = t.split("-")[1] # I'm so sorry you have to read this
    startTime = time(int(start.split(":")[0]), int(start.split(":")[1]))
    endTime = time(int(end.split(":")[0]), int(end.split(":")[1]))
    return startTime <= currentTime <= endTime # Operator overloading is a thing

def getFormattedSchedule(schedule: dict) -> str:
    chars = list(schedule.get("days", ""))
    days = "Mo:" + chars[0] + ", Tu:" + chars[1] + ", We:" + chars[2] + ", Th:" + chars[3] + ", Fr:" \
            + chars[4] + ", Sa:" + chars[5]  + ", Su:" + chars[6]
    return "Days: " + days + ", Time: " + schedule.get("time", "")

def readData() -> dict[str, Any]:
    with open(dataPath, "r") as f:
        return json.loads(f.read())
    
def writeData(days = None, time = None, subscriptions = []) -> None:
    # This lets you not have to write all the fields at once
    if days is None: days = readData().get("days")
    if time is None: time = readData().get("time")
    if subscriptions == []: subscriptions = readData().get("subscriptions", [])
    writeDataAll(days, time, subscriptions)
        
def writeDataAll(days: str | None, time: str | None, subscriptions: list) -> None:
    with lock: 
        data = {
            "days": days,
            "time": time,
            "subscriptions": subscriptions
        }
        with open(dataPath, "w+") as f:
            json.dump(data, f, indent = 4)
            
def handleExit():
    eventPoller.stop()
    quit(0)
    
if (__name__ == "__main__"):
    logDir: Final = "./logs/"
    Path(logDir).mkdir(exist_ok=True)
    if ("-l" in sys.argv):
        sys.stderr = sys.stdout = open(logDir + datetime.now().strftime("%Y-%m-%d--%H-%M-%S") + ".log", 'w')
    calendar.getAccessToken() # For on restart
    calendar.refreshCalendars()
    SocketModeHandler(app, appToken).start()
