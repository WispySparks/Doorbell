import re
import sys
from datetime import datetime
from pathlib import Path
from time import sleep
from typing import Final

import pyttsx3
from pygame import mixer
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

import database
from classes import GoogleCalendar
from secret import appToken, botToken, soundPath

app = App(token=botToken)
socketHandler = SocketModeHandler(app, appToken)

doorbellWords: Final = ["door", "noor", "abracadabra", "open sesame", "ding", "ring", "boop"]
mixer.init()
sound: Final = mixer.Sound(soundPath)
engine = pyttsx3.init()
engine.setProperty('rate', 100)
calendar: Final = GoogleCalendar()
# eventPoller: Final = EventPoller(60)

@app.event("app_mention")
def handleMentionEvent(body, say) -> None:
    event = body["event"]
    channel = event["channel"]
    text: str = event["text"]
    user = event["user"]
    userName = app.client.users_info(user=user)["user"]["real_name"]
    args = text.lower().split()[1:] # Ignore first word which is the mention
    print("Channel: {}, Args: {}, User: {}".format(channel, args, userName))
    
    if (len(args) < 1):
        say("Hi! (Must provide a command).")
        return
    cmd = args[0]
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
    # elif (cmd == "subscribe"):
    #     handleSubscribe(say, channel, args)
    # elif (cmd == "restart"):
    #     say("Restarting.")
    #     raise Exception("Restarting bot.")
    elif (cmd == "exit" or cmd == "stop"):
        say("Stopping.")
        socketHandler.close()
        exit()
    else:
        say("Invalid argument: " + cmd + ". Valid arguments are door, " +
        "schedule, calendars, next, subscribe(not fully impl), restart, and exit.")
        
def handleDoorbell(say, user: str, args: list[str]) -> None:
    schedule = database.read().schedule
    if (not schedule):
        say("Schedule not created yet!")
        return
    date = datetime.now()
    validDay, startTime, endTime = schedule[date.weekday()]
    door = "" if len(args) < 2 else args[1]
    if (validDay and (startTime <= date.time() <= endTime)):
        say("Ding! (" + user + ")")
        sound.play()
        sleep(sound.get_length())
        engine.say(user + "is at the door " + door)
        engine.runAndWait()
    else:
        say("Sorry, currently the bot isn't supposed to run. Check the schedule? @Doorbell schedule")
            
def handleSchedule(say, args: list[str]) -> None:
    if (len(args) < 2):
        data = database.read()
        if (not data.schedule):
            say("Schedule not created yet!")
        else:
            say(data.scheduleToStr())
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
        database.write(database.Data())
        say("Wrote schedule.\n" + database.read().scheduleToStr())
        
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
        
if (__name__ == "__main__"):
    if ("-l" in sys.argv):
        logDir: Final = "./logs/"
        Path(logDir).mkdir(exist_ok=True)
        sys.stderr = sys.stdout = open(logDir + datetime.now().strftime("%Y-%m-%d--%H-%M-%S") + ".log", 'w', buffering=1)
    database.create()
    print("Hiiai")
    socketHandler.start()
