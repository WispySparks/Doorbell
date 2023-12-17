import json
import os
import re
from datetime import datetime, time

from googlecalendar import GoogleCalendar

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "hide"

import requests as r
from pygame import mixer
from websockets.exceptions import ConnectionClosed
from websockets.sync.client import connect

from secret import appToken, botToken, soundPath

slackAPI = "https://slack.com/api/"
authHeader = {"Authorization": "Bearer " + botToken}
doorbellWords = ["door", "noor", "abracadabra", "open sesame"]
schedulePath = "schedule.json"
mixer.init()
sound = mixer.Sound(soundPath)
calendar = GoogleCalendar()

# API Endpoints
openConnection = slackAPI + "apps.connections.open"
postMessage = slackAPI + "chat.postMessage"
userInfo = slackAPI + "users.info"

def main():
    headers = {"Authorization": "Bearer " + appToken}
    response = r.post(openConnection, headers=headers)
    print("WS Status Code: " + str(response.status_code))
    url = response.json()["url"] + "&debug_reconnects=true"
    with connect(url) as socket:
        print("Connected to WebSocket.")
        while True:
            try:
                response = json.loads(socket.recv())
                if (response.get("envelope_id") != None):
                    # Acknowledge event
                    socket.send(json.dumps({"envelope_id": response["envelope_id"]}))
                    if (response["retry_attempt"] > 0 and response["retry_reason"] == "timeout"): return # Ignore retries, they're annoying
                    event = response["payload"]["event"]
                    if (event["type"] == "app_mention"):
                        handleMentionEvent(event)
            except ConnectionClosed:
                print("Connection Closed. Refreshing . . .")
                break
                
def handleMentionEvent(event):
    channel = event["channel"]
    text = str(event["text"])
    args = text.split()[1:] # Ignore first word which is the mention
    user = getUserName(event["user"])
    print("Channel: {}, Text: {}".format(channel, text))
    if (len(args) < 1): return
    cmd = args[0].lower()
    if (cmd in doorbellWords):
        handleDoorbell(channel, user)
    elif (cmd == "schedule"):
        handleSchedule(channel, args)
    elif (cmd == "next"):
        if (len(args) < 2):
            sendMessage(channel, "Need to provide a calendar.")
            return
        calendarName = " ".join(text.split()[2:]) # I need to use differently split args because of names with spaces
        event = calendar.getNextEvent(calendarName)
        if (event == None):
            sendMessage(channel, "Invalid Calendar - " + calendarName + ".")
            return
        name, date = event
        sendMessage(channel, name + " - " + date.strftime("%#m/%d/%Y - %#I:%M %p"))
    elif (cmd == "restart"):
        sendMessage(channel, "Restarting.")
        raise Exception("Restarting bot.")
    elif (cmd == "die"):
        sendMessage(channel, "Stopping.")
        quit(0)
    else:
        sendMessage(channel, "Invalid argument: " + cmd)
        
def handleDoorbell(channel, user):
    schedule = readSchedule()
    if (schedule == None):
        sendMessage(channel, "Schedule not created yet!")
        return
    date = datetime.now()
    isCorrectDay = int(list(schedule["days"])[date.weekday()]) == 1
    if (isCorrectDay and isCorrectTime(schedule)):
        sendMessage(channel, "Ding! (" + user + ")")
        sound.play()
    else:
        sendMessage(channel, "Sorry, currently the bot isn't supposed to run. Check the schedule? @Doorbell schedule")
            
def handleSchedule(channel, args):
    if (len(args) < 2):
        schedule = readSchedule()
        if (schedule == None):
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
        writeSchedule(days, time)
        sendMessage(channel, getFormattedSchedule(readSchedule()))
        
def sendMessage(channelID, msg):
    payload = {"channel": channelID, "text": msg}
    response = r.post(postMessage, payload, headers=authHeader)
    print("PM Status Code: " + str(response.status_code))
    print("Sent " + msg)
    
def getUserName(userID):
    payload = {"user": userID}
    response = r.get(userInfo, payload, headers=authHeader)
    return response.json()["user"]["real_name"]

def isCorrectTime(schedule):
    currentTime = datetime.now().time()
    t: str = schedule["time"]
    st = t.split("-")[0]
    et = t.split("-")[1] # I'm so sorry you have to read this
    startTime = time(int(st.split(":")[0]), int(st.split(":")[1]))
    endTime = time(int(et.split(":")[0]), int(et.split(":")[1]))
    return startTime <= currentTime <= endTime # Operator overloading is a thing

def getFormattedSchedule(schedule):
    chars = list(schedule["days"])
    days = "Mo:" + chars[0] + ", Tu:" + chars[1] + ", We:" + chars[2] + ", Th:" + chars[3] + ", Fr:" \
            + chars[4] + ", Sa:" + chars[5]  + ", Su:" + chars[6]
    return "Days: " + days + ", Time: " + schedule["time"]

def readSchedule():
    if not os.path.isfile(schedulePath):
        return None
    with open(schedulePath, "r") as f:
        return json.loads(f.read())
    
def writeSchedule(days, time):
    data = {"days": days, "time": time}
    with open(schedulePath, "w+") as f:
        json.dump(data, f)     
    
if __name__ == "__main__":
    while True:
        try:
            main()
        except Exception as e:
            print(e)