import time
from datetime import datetime, timedelta
from threading import Thread
from typing import Final

import requests as r

from secret import googleClientId, googleClientSecret, googleRefreshToken


class GoogleCalendar():
    
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
        items = resp.json().get("items", [], [])
        for calendar in items:
            name = calendar.get("summary")
            id = calendar.get("id")
            self.calendars.update({name: id})
            
    def getEvents(self, calendarName, minDate: datetime|None = None) -> list[tuple[str, datetime, datetime]]:
        events = []
        id = self.calendars.get(calendarName)
        if (id == None): return events
        endpoint = "https://www.googleapis.com/calendar/v3/calendars/" + id + "/events"
        if (minDate == None): minDate = datetime.now().astimezone()
        payload = {
            "orderBy": "startTime",
            "singleEvents": True,
            "timeMin": minDate.isoformat() # This goes by event end time unfortunately
        }
        resp = r.get(endpoint, payload, headers=self.headers)
        self.retryFuncIfTokenExpired(resp, self.getEvents)
        items = resp.json().get("items", [])
        for event in items:
            name = event.get("summary")
            start = event.get("start").get("date") if event.get("start").get("dateTime") == None else event.get("start").get("dateTime")
            end = event.get("end").get("date") if event.get("end").get("dateTime") == None else event.get("end").get("dateTime")
            start = datetime.fromisoformat(start)
            end = datetime.fromisoformat(end)
            events.append((name, start, end))
        return events
    
    def getNextEvent(self, calendarName, minDate: datetime|None = None) -> tuple[str, datetime, datetime] | None:
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
        import bot  # I don't know how else to fix this problem, maybe split into multiple files
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
            eventDate = datetime.fromisoformat(event["start"])
            remindWindowStart = eventDate - timedelta(hours = remindTime)
            currentDate = datetime.now().astimezone()
            if (currentDate >= remindWindowStart):
                bot.sendMessage(channelId, "Reminder: " + name + " - " + eventDate.strftime(GoogleCalendar.dateFormat))
                eventEnd = datetime.fromisoformat(event["end"])
                minDate = max(currentDate, eventEnd)
                nextEvent = bot.calendar.getNextEvent(calendarName, minDate)
                if (nextEvent != None):
                    name, start, _ = nextEvent
                    sub["nextEvent"] = {"name": name, "date": start.isoformat()}
                else:
                    sub["nextEvent"] = None # Signal no new future events
                bot.writeData(subscriptions = subs)