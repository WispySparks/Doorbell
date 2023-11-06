import json
import os
import re
from datetime import datetime, time

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "hide"

import requests as r
from pygame import mixer
from websockets.exceptions import ConnectionClosed
from websockets.sync.client import connect

from secret import appToken, botToken, soundPath

slackAPI = "https://slack.com/api/"
appHeaders = {"Authorization": "Bearer " + appToken}
headers = {"Authorization": "Bearer " + botToken}
doorbellWords = ["door", "noor", "abracadabra", "open sesame"]
schedulePath = "schedule.json"
mixer.init()
sound = mixer.Sound(soundPath)

# API Endpoints
openConnection = slackAPI + "apps.connections.open"
postMessage = slackAPI + "chat.postMessage"
userInfo = slackAPI + "users.info"

def main():
    response = r.post(openConnection, headers=appHeaders)
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
            except ConnectionClosed as e:
                print("Connection Closed. Refreshing . . .")
                break
                
def handleMentionEvent(event):
    channel = event["channel"]
    text = str(event["text"]).lower()
    args = text.split()[1:] # Ignore first word which is the mention
    user = getUserName(event["user"])
    print("Channel: {}, Text: {}".format(channel, text))
    if (len(args) < 1): return
    if (args[0] in doorbellWords):
        schedule = readSchedule()
        if (schedule == None):
            sendMessage(channel, "Schedule not created yet!")
            return
        t = datetime.now()
        correctDay = int(list(schedule["days"])[t.weekday()]) == 1
        correctTime = checkTime(schedule, t.time())
        if (correctDay and correctTime):
            sendMessage(channel, "Ding! (" + user + ")")
            sound.play()
        else:
            sendMessage(channel, "Sorry, currently the bot isn't supposed to run. Check the schedule? @Doorbell schedule")
    elif (args[0] == "schedule"):
        handleSchedule(channel, args)
    else:
        sendMessage(channel, "Invalid argument: " + args[0])
            
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
        if (re.match("^[0-2][0-9]:[0-5][0-9]-[0-2][0-9]:[0-5][0-9]$", time) == None):
            sendMessage(channel, "Invalid time format. Should be XX:XX-XX:XX.")
            return
        sendMessage(channel, "Wrote schedule.")
        writeSchedule(days, time)
        sendMessage(channel, getFormattedSchedule(readSchedule()))
        
def sendMessage(channelID, msg):
    payload = {"channel": channelID, "text": msg}
    response = r.post(postMessage, payload, headers=headers)
    print("PM Status Code: " + str(response.status_code))
    print("Sent " + msg)
    
def getUserName(userID):
    payload = {"user": userID}
    response = r.get(userInfo, payload, headers=headers)
    return response.json()["user"]["real_name"]

def checkTime(schedule, curretTime):
    t: str = schedule["time"]
    st = t.split("-")[0]
    et = t.split("-")[1] # I'm so sorry you have to read this
    startTime = time(int(st.split(":")[0]), int(st.split(":")[1]))
    endTime = time(int(et.split(":")[0]), int(et.split(":")[1]))
    return startTime <= curretTime <= endTime # Operator overloading is a thing

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
        main()