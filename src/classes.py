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
    
    def __init__(self) -> None:
        self.getAccessToken()
        self.refreshCalendars()
        
    def isTokenExpired(self, resp) -> bool:
        json = resp.json()
        if (json.get("error") is not None): # Too many ways for token to fail
            return True
        return False
    
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
        if (json.get("access_token") is not None):
            self.headers = {"Authorization": "Bearer " + json.get("access_token")}
            
    def refreshCalendars(self) -> None:
        self.calendars = {}
        endpoint = "https://www.googleapis.com/calendar/v3/users/me/calendarList"
        resp = r.get(endpoint, headers=self.headers)
        for _ in range(self.maxRetries):
            if (not self.isTokenExpired(resp)): break
            self.getAccessToken()
            resp = r.get(endpoint, headers=self.headers)
        items = resp.json().get("items", [])
        for calendar in items:
            name = calendar.get("summary")
            id = calendar.get("id")
            self.calendars.update({name: id})
            
    def getEvents(self, calendarName, minDate: datetime|None = None) -> list[tuple[str, datetime, datetime]]:
        events = []
        id = self.calendars.get(calendarName)
        if (id is None): return events
        endpoint = "https://www.googleapis.com/calendar/v3/calendars/" + id + "/events"
        if (minDate is None): minDate = datetime.now().astimezone()
        payload = {
            "orderBy": "startTime",
            "singleEvents": True,
            "timeMin": minDate.isoformat() # This goes by event end time unfortunately
        }
        resp = r.get(endpoint, payload, headers=self.headers)
        for _ in range(self.maxRetries):
            if (not self.isTokenExpired(resp)): break
            self.getAccessToken()
            resp = r.get(endpoint, headers=self.headers)
        items = resp.json().get("items", [])
        for event in items:
            name = event.get("summary")
            start = event.get("start").get("date") if event.get("start").get("dateTime") is None else event.get("start").get("dateTime")
            end = event.get("end").get("date") if event.get("end").get("dateTime") is None else event.get("end").get("dateTime")
            start = datetime.fromisoformat(start)
            end = datetime.fromisoformat(end)
            events.append((name, start, end))
        return events
    
    def getNextEvent(self, calendarName, minDate: datetime|None = None) -> tuple[str, datetime, datetime] | None:
        '''Returns a tuple structured with the event's name, event's start date and event's end date or None if there is no next event.'''
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
        time.sleep(5)
        while not self.stopped:
            self.pollSubscriptions()
            time.sleep(self.intervalSeconds)
        print("Stopped Event Poller.", flush=True)
        
    def eventStruct(self, event):
        if (event is None):
            return None
        name, startTime, endTime = event
        return {"name": name, "start": startTime.isoformat(), "end": endTime.isoformat()}
    
    def pollSubscriptions(self) -> None:
        import bot  # I don't know how else to fix this problem, maybe split into multiple files
        subs = bot.readData().get("subscriptions", [])
        sub: dict
        for sub in subs:
            currentDate = datetime.now().astimezone()
            channelId = sub.get("channelId", "")
            calendarName = sub.get("calendarName", "")
            remindTime = sub.get("remindTime", 0)
            event = sub.get("nextEvent")
            if (event is None): # Check if a new event has been added
                last = datetime.fromisoformat(sub.get("lastEvent", currentDate.isoformat()))
                minDate = max(currentDate, last)
                e = bot.calendar.getNextEvent(calendarName, minDate)
                sub.update({"nextEvent": self.eventStruct(e)})
                continue
            name = event.get("name")
            eventStart = datetime.fromisoformat(event.get("start"))
            remindWindowStart = eventStart - timedelta(hours = remindTime)
            if (currentDate >= remindWindowStart):
                bot.sendMessage(channelId, "Reminder: " + name + " - " + eventStart.strftime(GoogleCalendar.dateFormat))
                eventEnd = datetime.fromisoformat(event.get("end"))
                minDate = max(currentDate, eventEnd)
                nextEvent = bot.calendar.getNextEvent(calendarName, minDate)
                sub.update({"nextEvent": self.eventStruct(nextEvent)})
                sub.update({"lastEvent": eventEnd.isoformat()})
        bot.writeData(subscriptions = subs)