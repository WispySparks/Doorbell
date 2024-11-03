import os.path
from datetime import datetime
from typing import Final, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class GoogleCalendar:

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
                with open("token.json", "w") as token:
                    token.write(creds.to_json())
            self.service = build("calendar", "v3", credentials=creds)
            result = self.service.calendarList().list().execute()
            calendarList: list[dict] = result.get("items", [])
            if calendarList:
                for calendar in calendarList:
                    name = calendar.get("summary", "")
                    calendar_id = calendar.get("id", "")
                    self.calendars.update({name: calendar_id})
        except HttpError as error:
            print(f"GoogleCalendar Error: {error}")

    def getEvents(self, calendar: str, minDate: Optional[datetime] = None) -> list[tuple[str, datetime, datetime]]:
        events = []
        calendar_id = self.calendars.get(calendar)
        if calendar_id is None:
            return events
        if minDate is None:
            minDate = datetime.now().astimezone()
        result = (
            self.service.events()
            .list(calendarId=calendar_id, orderBy="startTime", singleEvents=True, timeMin=minDate.isoformat())
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
            start = datetime.fromisoformat(start)
            end = datetime.fromisoformat(end)
            events.append((name, start, end))
        return events

    def getNextEvent(
        self, calendar: str, minDate: Optional[datetime] = None
    ) -> Optional[tuple[str, datetime, datetime]]:
        """Returns a tuple structured with the event's name, event's start date and event's end date
        or None if there is no next event."""
        events = self.getEvents(calendar, minDate)
        if events:
            return events[0]
        return None
