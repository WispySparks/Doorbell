import datetime as dt
import re
import sys
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
txtToSpeech = pyttsx3.init()
txtToSpeech.setProperty("rate", 100)
calendar: Final = GoogleCalendar()
# eventPoller: Final = EventPoller(60)

@app.event("app_mention") #TODO make a command to update doorbell (git pull and restart)
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
    elif (cmd == "exit" or cmd == "stop"): #TODO This doesn't work
        say("Stopping.")
        socketHandler.close()
        # eventPoller.stop()
        exit()
    else:
        say("Invalid argument: " + cmd + ". Valid arguments are door, " +
        "schedule, and exit.")
        
def handleDoorbell(say, user: str, args: list[str]) -> None:
    schedule = database.read().schedule
    if (not schedule):
        say("Schedule not created yet!")
        return
    date = dt.datetime.now()
    validDay, startTime, endTime = schedule[date.weekday()]
    door = "" if len(args) < 2 else args[1]
    if (validDay and (startTime <= date.time() <= endTime)):
        say("Ding! (" + user + ")")
        sound.play()
        sleep(sound.get_length())
        if (txtToSpeech._inLoop):
            txtToSpeech.endLoop()
        txtToSpeech.say(user + "is at the door " + door)
        txtToSpeech.runAndWait()
    else:
        say("Sorry, currently the bot isn't supposed to run. Check the schedule? @Doorbell schedule")
            
def handleSchedule(say, args: list[str]) -> None:
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
        schedule: list[tuple[bool, dt.time, dt.time]] = []
        activeTimes = args[1:] 
        for day in range(7):
            time = activeTimes[day]
            if (time == "-"):
                schedule.append((False, dt.time(), dt.time()))
            elif (re.match("^([0-1][0-9]|[2][0-3]):[0-5][0-9]-([0-1][0-9]|[2][0-3]):[0-5][0-9]$", time) is None):
                say("Invalid time format. Should be XX:XX-XX:XX in 24 hour time.")
                return
            else:
                start, end = time.split("-")
                startTime = dt.time(int(start.split(":")[0]), int(start.split(":")[1]))
                endTime = dt.time(int(end.split(":")[0]), int(end.split(":")[1]))        
                schedule.append((True, startTime, endTime))
        database.write(database.Data(schedule))
        say("Wrote schedule.\n" + database.read().scheduleToStr())
        
def handleSubscribe(say, channel: str, args: list[str]) -> None: #TODO This is definitely broken
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
        sys.stderr = sys.stdout = open(logDir + dt.datetime.now().strftime("%Y-%m-%d--%H-%M-%S") + ".log", "w", buffering=1)
    database.create()
    socketHandler.start()
