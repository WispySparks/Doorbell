import json
import os
import re
from datetime import datetime, time
from threading import Lock
from typing import Any, Final

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "hide"

import requests as r
from pygame import mixer
from websockets.exceptions import ConnectionClosed
from websockets.sync import client

from classes import EventPoller, GoogleCalendar
from secret import appToken, botToken, soundPath

doorbellWords: Final = ["door", "noor", "abracadabra", "open sesame"]
dataPath: Final = "data.json"
mixer.init()
sound: Final = mixer.Sound(soundPath)
calendar: Final = GoogleCalendar()
eventPoller: Final = EventPoller(60)
lock: Final = Lock()

# API
slackAPI: Final = "https://slack.com/api/"
openConnection: Final = slackAPI + "apps.connections.open"
postMessage: Final = slackAPI + "chat.postMessage"
userInfo: Final = slackAPI + "users.info"
authHeader: Final = {"Authorization": "Bearer " + botToken}

def main() -> None:
    calendar.getAccessToken() # For on restart
    calendar.getCalendars()
    headers = {"Authorization": "Bearer " + appToken}
    response = r.post(openConnection, headers=headers)
    print("WS Status Code: " + str(response.status_code))
    url = response.json().get("url") + "&debug_reconnects=true"
    with client.connect(url) as socket:
        print("Connected to WebSocket.")
        while True:
            try:
                resp = json.loads(socket.recv())
                envelope_id = resp.get("envelope_id")
                if (envelope_id != None):
                    # Acknowledge event
                    socket.send(json.dumps({"envelope_id": envelope_id}))
                    if (resp.get("retry_attempt") > 0 and resp.get("retry_reason") == "timeout"): return # Ignore retries, they're annoying
                    event = resp.get("payload").get("event")
                    if (event.get("type") == "app_mention"):
                        handleMentionEvent(event)
            except ConnectionClosed:
                print("Connection Closed. Refreshing . . .")
                break
                
def handleMentionEvent(event: dict) -> None:
    channel = event.get("channel", "")
    text: str = event.get("text", "")
    args = text.split()[1:] # Ignore first word which is the mention
    user = getUserName(event.get("user", "")) 
    print("Channel: {}, Args: {}, User: {}".format(channel, args, user))
    if (len(args) < 1):
        sendMessage(channel, "Hi! (Must provide a command).")
        return
    cmd = args[0].lower()
    if (cmd in doorbellWords):
        handleDoorbell(channel, user)
    elif (cmd == "schedule"):
        handleSchedule(channel, args)
    elif (cmd == "calendars"):
        sendMessage(channel, ", ".join(list(calendar.calendars.keys())))
    elif (cmd == "next"):
        if (len(args) < 2):
            sendMessage(channel, "Need to provide a calendar.")
            return
        calendarName = " ".join(args[1:])
        nextEvent = calendar.getNextEvent(calendarName)
        if (nextEvent == None):
            sendMessage(channel, "Invalid Calendar - " + calendarName + ".")
            return
        name, date = nextEvent
        sendMessage(channel, name + " - " + date.strftime(GoogleCalendar.dateFormat))
    elif (cmd == "subscribe"):
        handleSubscribe(channel, args)
    elif (cmd == "restart"):
        sendMessage(channel, "Restarting.")
        raise Exception("Restarting bot.")
    elif (cmd == "exit" or cmd == "die"):
        sendMessage(channel, "Stopping.")
        handleExit()
    else:
        sendMessage(channel, "Invalid argument: " + cmd + ". Valid arguments are door, " +
        "schedule, calendars, next, subscribe(not fully impl), restart, and exit.")
        
def handleDoorbell(channel: str, user: str) -> None:
    schedule = readData()
    days = schedule.get("days")
    time = schedule.get("time")
    if (days == None or time == None):
        sendMessage(channel, "Schedule not created yet!")
        return
    date = datetime.now()
    isCorrectDay = int(list(days)[date.weekday()]) == 1
    if (isCorrectDay and isCorrectTime(time)):
        sendMessage(channel, "Ding! (" + user + ")")
        sound.play()
    else:
        sendMessage(channel, "Sorry, currently the bot isn't supposed to run. Check the schedule? @Doorbell schedule")
            
def handleSchedule(channel: str, args: list[str]) -> None:
    if (len(args) < 2):
        schedule = readData()
        if (schedule.get("days") == None or schedule.get("time") == None):
            sendMessage(channel, "Schedule not created yet!")
        else:
            sendMessage(channel, getFormattedSchedule(schedule))
    elif (len(args) < 3):
        sendMessage(channel, "Need an argument for days and an argument for time.")
    else:
        days = args[1]
        time = args[2]
        if (re.match("^[01]{7}$", days) == None):
            sendMessage(channel, "Invalid days format. List 0's and 1's for the days starting at Monday.")
            return
        if (re.match("^([0-1][0-9]|[2][0-3]):[0-5][0-9]-([0-1][0-9]|[2][0-3]):[0-5][0-9]$", time) == None):
            sendMessage(channel, "Invalid time format. Should be XX:XX-XX:XX.")
            return
        sendMessage(channel, "Wrote schedule.")
        writeData(days, time)
        sendMessage(channel, getFormattedSchedule(readData()))
        
def handleSubscribe(channel: str, args: list[str]) -> None:
    if (len(args) < 2):
        sendMessage(channel, "Must provide how many hours before to be reminded.")
    elif (len(args) < 3):
        sendMessage(channel, "Must provide a calendar to subscribe to.")
    else:
        remindTimeHours = float(args[1])
        calendarName = " ".join(args[2:])
        event = calendar.getNextEvent(calendarName)
        if (event == None):
            sendMessage(channel, "Invalid calendar - " + calendarName + " or no future events.")
            return
        name, date = event
        subs: list = readData().get("subscriptions", [])
        subs.append({
            "channelId": channel,
            "calendarName": calendarName,
            "remindTime": remindTimeHours,
            "nextEvent": {
                "name": name,
                "date": date.isoformat()
            }
        })
        writeData(subscriptions = subs)
        sendMessage(channel, "Subscribed to " + calendarName + " and reminds " + str(remindTimeHours) + " hours before.")
        
def sendMessage(channelID: str, msg: str) -> None:
    payload = {"channel": channelID, "text": msg}
    r.post(postMessage, payload, headers=authHeader)
    print("Sent " + msg)
    
def getUserName(userID: str) -> str:
    payload = {"user": userID}
    response = r.get(userInfo, payload, headers=authHeader)
    return response.json().get("user").get("real_name")

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
    if days == None: days = readData().get("days")
    if time == None: time = readData().get("time")
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