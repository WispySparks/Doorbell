import json
import os

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import requests as r
from pygame import mixer
from websockets.sync.client import connect

from Hidden import appToken, botToken, soundPath

slackAPI = "https://slack.com/api/"
appHeaders = {"Authorization": appToken}
headers = {"Authorization": botToken}
validWords = ["door", "noor", "abracadabra", "open sesame"]
mixer.init()
sound = mixer.Sound(soundPath)

# API Endpoints
openConnection = slackAPI + "apps.connections.open"
postMessage = slackAPI + "chat.postMessage"

def main():
    response = r.post(openConnection, headers=appHeaders)
    print("WS Status Code: " + str(response.status_code))
    url = response.json()["url"] + "&debug_reconnects=true"
    with connect(url) as socket:
        while True:
            response = json.loads(socket.recv())
            if (response.get("envelope_id") != None):
                # Acknowledge event
                socket.send(json.dumps({"envelope_id": response["envelope_id"]}))
                handleMentionEvent(response)
                
def handleMentionEvent(json):
    event = json["payload"]["event"]
    if (event["type"] == "app_mention"):
        channel = event["channel"]
        text = event["text"]
        print("Mention Event")
        print("Channel: {}, Text: {}".format(channel, text))
        for word in validWords:
            if (text.__contains__(word)):
                sendMessage(channel, "Ding!")
                sound.play()

def sendMessage(channelID, msg):
    payload = {
        "channel": channelID,
        "text": msg
    }
    response = r.post(postMessage, payload, headers=headers)
    print("PM Status Code: " + str(response.status_code))
    print("Sent " + msg)
    
if __name__ == "__main__":
    main()