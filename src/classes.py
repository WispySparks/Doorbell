import time
from datetime import datetime, timedelta
from threading import Thread
from typing import Final

import requests as r

import bot
from secret import googleClientId, googleClientSecret, googleRefreshToken


class GoogleCalendar(): # Still need to implement getting a new access token when old one is expired
    
    headers: dict[str, str] = {"Authorization": "Bearer "}
    calendars: dict[str, str] = {}
    dateFormat: Final[str] = "%#m/%d/%Y - %#I:%M %p" # Only works on windows machines
    maxRetries: Final[int] = 3
    currentRetries: int = 0
    
    def __init__(self) -> None:
        self.getAccessToken()
        self.getCalendars()
        
    def isTokenExpired(self, json) -> bool:
        if (json.get("error") != None and json.get("error").get("status", "") == "UNAUTHENTICATED"):
            return True
        return False
    
    def retryFuncIfTokenExpired(self, resp, func):
        if (self.isTokenExpired(resp.json()) and self.currentRetries < self.maxRetries):
            self.getAccessToken()
            self.currentRetries += 1
            return func()
        
    def getAccessToken(self) -> None:
        endpoint = "https://oauth2.googleapis.com/token"
        payload = {
            "client_id": googleClientId,
            "client_secret": googleClientSecret,
            "refresh_token": googleRefreshToken,
            "grant_type": "refresh_token"
        }
        resp = r.post(endpoint, payload)
        json = resp.json()
        if (json.get("access_token") != None):
            self.headers = {"Authorization": "Bearer " + json.get("access_token")}
            
    def getCalendars(self) -> None:
        endpoint = "https://www.googleapis.com/calendar/v3/users/me/calendarList"
        resp = r.get(endpoint, headers=self.headers)
        self.retryFuncIfTokenExpired(resp, self.getCalendars)
        items = resp.json().get("items", [])
        for calendar in items:
            name = calendar.get("summary")
            id = calendar.get("id")
            self.calendars.update({name: id})
            
    def getEvents(self, calendarName, minDate: datetime|None = None) -> list[tuple[str, datetime]]:
        events = []
        id = self.calendars.get(calendarName)
        if (id == None): return events
        endpoint = "https://www.googleapis.com/calendar/v3/calendars/" + id + "/events"
        if (minDate == None): minDate = datetime.now().astimezone()
        payload = {
            "orderBy": "startTime",
            "singleEvents": True,
            "timeMin": minDate.isoformat()
        }
        resp = r.get(endpoint, payload, headers=self.headers)
        self.retryFuncIfTokenExpired(resp, self.getEvents)
        items = resp.json().get("items", [])
        for event in items:
            name = event.get("summary")
            start = event.get("start").get("date") if event.get("start").get("dateTime") == None else event.get("start").get("dateTime")
            date = datetime.fromisoformat(start)
            events.append((name, date))
        return events
    
    def getNextEvent(self, calendarName, minDate: datetime|None = None) -> tuple[str, datetime] | None:
        events = self.getEvents(calendarName, minDate)
        if len(events) < 1: return None
        return events[0]
    
class EventPoller(Thread):
    
    def __init__(self, intervalSeconds) -> None:
        super().__init__()
        self._target = self.continuouslyPoll
        self.intervalSeconds = intervalSeconds
        self.stopped = False
        
    def stop(self):
        self.stopped = True
        
    def continuouslyPoll(self) -> None:
        while not self.stopped:
            self.pollSubscriptions()
            time.sleep(self.intervalSeconds)
        print("Stopped Event Poller.")
    
    def pollSubscriptions(self) -> None:
        data = bot.readData()
        subs = data.get("subscriptions", [])
        for sub in subs:
            channelId = sub["channelId"]
            calendarName = sub["calendarName"]
            remindTime = sub["remindTime"]
            event = sub["nextEvent"]
            if (event == None): # Check if a new event has been added
                e = bot.calendar.getNextEvent(calendarName)
                if (e != None):
                    sub["nextEvent"] = e
                    bot.writeData(subscriptions = subs)
                continue
            name = event["name"]
            eventDate = datetime.fromisoformat(event["date"])
            remindWindowStart = eventDate - timedelta(hours = remindTime)
            currentDate = datetime.now().astimezone()
            if (currentDate >= remindWindowStart):
                bot.sendMessage(channelId, "Reminder: " + name + " - " + eventDate.strftime(GoogleCalendar.dateFormat))
                minDate = max(currentDate, eventDate + timedelta(hours=24)) # Add a second to not get same event
                nextEvent = bot.calendar.getNextEvent(calendarName, minDate)
                if (nextEvent != None):
                    name, date = nextEvent
                    sub["nextEvent"] = {"name": name, "date": date.isoformat()}
                else:
                    sub["nextEvent"] = None # Signal no new future events
                bot.writeData(subscriptions = subs)