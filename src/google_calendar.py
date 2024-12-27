"""Contains the GoogleCalendar class for accessing the team's calendar."""

import datetime as dt
import os.path
from dataclasses import dataclass
from datetime import datetime
from typing import Final, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


@dataclass(frozen=True)
class CalendarEvent:
    """An event on the Google Calendar."""

    name: str
    start: datetime
    end: datetime


class GoogleCalendar:
    """Interfaces with the Armada Robotics's Google Calendar."""

    SCOPES: Final = ["https://www.googleapis.com/auth/calendar.readonly"]
    DATE_FORMAT: Final[str] = "%#m/%d/%Y - %#I:%M %p"  # Only works on windows machines
    calendars: dict[str, str] = {}  # Name: CalendarID

    def __init__(self) -> None:
        try:
            creds = None
            if os.path.exists("token.json"):
                creds = Credentials.from_authorized_user_file("token.json", self.SCOPES)
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file("credentials.json", self.SCOPES)
                    creds = flow.run_local_server(port=0)
                with open("token.json", "w", encoding="utf-8") as token:
                    token.write(creds.to_json())
            self.service = build("calendar", "v3", credentials=creds)
            result = self.service.calendarList().list().execute()
            calendar_list: list[dict] = result.get("items", [])
            if calendar_list:
                for calendar in calendar_list:
                    name = calendar.get("summary", "")
                    calendar_id = calendar.get("id", "")
                    self.calendars.update({name: calendar_id})
        except HttpError as error:
            print(f"GoogleCalendar Error: {error}")

    def get_events(self, calendar: str, min_date: Optional[datetime] = None) -> list[CalendarEvent]:
        """Returns list of events for the given calendar
        in the form of a tuple with the event's name, start date, and end date."""
        events: list[CalendarEvent] = []
        calendar_id = self.calendars.get(calendar)
        if calendar_id is None:
            return events
        if min_date is None:
            min_date = datetime.now().astimezone(dt.timezone.utc)
        result = (
            self.service.events()
            .list(calendarId=calendar_id, orderBy="startTime", singleEvents=True, timeMin=min_date.isoformat())
            .execute()
            .get("items", [])
        )
        for event in result:
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
            start = datetime.fromisoformat(start).astimezone(dt.timezone.utc)
            end = datetime.fromisoformat(end).astimezone(dt.timezone.utc)
            events.append(CalendarEvent(name, start, end))
        return events

    def get_next_event(self, calendar: str, min_date: Optional[datetime] = None) -> Optional[CalendarEvent]:
        """Returns a tuple structured with the event's name, event's start date and event's end date
        or None if there is no next event."""
        events = self.get_events(calendar, min_date)
        if events:
            return events[0]
        return None
