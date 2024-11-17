"""Tests the Google Calendar by printing all calendars and their next event."""

from google_calendar import GoogleCalendar

calendar = GoogleCalendar()

print("Calendars: " + ", ".join(list(calendar.calendars)))

for c in calendar.calendars:
    event = calendar.get_next_event(c)
    if event is None:
        print(f"{c}: None")
        continue
    name, date, _ = event
    print(f"{c}: {name} - {date.strftime(GoogleCalendar.DATE_FORMAT)}")
