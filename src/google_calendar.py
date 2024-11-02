from datetime import datetime
from typing import Final

import requests as r

from secret import googleClientId, googleClientSecret, googleRefreshToken

# TODO look for a python package for google like bolt is to slack
# https://github.com/googleapis/google-api-python-client
# https://github.com/googleapis/google-auth-library-python


class GoogleCalendar:

    headers: dict[str, str] = {"Authorization": "Bearer "}
    calendars: dict[str, str] = {}
    dateFormat: Final[str] = "%#m/%d/%Y - %#I:%M %p"  # Only works on windows machines
    maxRetries: Final[int] = 3
    requestTimeout: Final[int] = 10

    def __init__(self) -> None:
        self.getAccessToken()
        self.refreshCalendars()

    def isTokenExpired(self, resp) -> bool:
        json = resp.json()
        if json.get("error") is not None:  # Too many ways for token to fail
            return True
        return False

    def getAccessToken(self) -> None:
        endpoint = "https://oauth2.googleapis.com/token"
        payload = {
            "client_id": googleClientId,
            "client_secret": googleClientSecret,
            "refresh_token": googleRefreshToken,
            "grant_type": "refresh_token",
        }
        resp = r.post(endpoint, payload, timeout=self.requestTimeout)
        json = resp.json()
        if json.get("access_token") is not None:
            self.headers = {"Authorization": "Bearer " + json.get("access_token")}

    def refreshCalendars(self) -> None:
        self.calendars = {}
        endpoint = "https://www.googleapis.com/calendar/v3/users/me/calendarList"
        resp = r.get(endpoint, headers=self.headers, timeout=self.requestTimeout)
        for _ in range(self.maxRetries):
            if not self.isTokenExpired(resp):
                break
            self.getAccessToken()
            resp = r.get(endpoint, headers=self.headers, timeout=self.requestTimeout)
        items = resp.json().get("items", [])
        for calendar in items:
            name = calendar.get("summary")
            calendar_id = calendar.get("id")
            self.calendars.update({name: calendar_id})

    def getEvents(self, calendarName, minDate: datetime | None = None) -> list[tuple[str, datetime, datetime]]:
        events = []
        calendar_id = self.calendars.get(calendarName)
        if calendar_id is None:
            return events
        endpoint = "https://www.googleapis.com/calendar/v3/calendars/" + calendar_id + "/events"
        if minDate is None:
            minDate = datetime.now().astimezone()
        payload = {
            "orderBy": "startTime",
            "singleEvents": True,
            "timeMin": minDate.isoformat(),  # This goes by event end time unfortunately
        }
        resp = r.get(endpoint, payload, headers=self.headers, timeout=self.requestTimeout)
        for _ in range(self.maxRetries):
            if not self.isTokenExpired(resp):
                break
            self.getAccessToken()
            resp = r.get(endpoint, headers=self.headers, timeout=self.requestTimeout)
        items = resp.json().get("items", [])
        for event in items:
            name = event.get("summary")
            start = (
                event.get("start").get("date")
                if event.get("start").get("dateTime") is None
                else event.get("start").get("dateTime")
            )
            end = (
                event.get("end").get("date")
                if event.get("end").get("dateTime") is None
                else event.get("end").get("dateTime")
            )
            start = datetime.fromisoformat(start)
            end = datetime.fromisoformat(end)
            events.append((name, start, end))
        return events

    def getNextEvent(self, calendarName, minDate: datetime | None = None) -> tuple[str, datetime, datetime] | None:
        """Returns a tuple structured with the event's name, event's start date and event's end date
        or None if there is no next event."""
        events = self.getEvents(calendarName, minDate)
        if len(events) < 1:
            return None
        return events[0]
