import sys

sys.path.append("src/")
from google_calendar import GoogleCalendar

calendar = GoogleCalendar()


def print_calendars():
    print("Calendars: " + ", ".join(list(calendar.calendars)))


def print_events():
    for c in calendar.calendars:
        event = calendar.get_next_event(c)
        if event is None:
            print(f"{c}: None")
            continue
        name, date, _ = event
        print(f"{c}: {name} - {date.strftime(GoogleCalendar.DATE_FORMAT)}")


print_calendars()
print_events()
