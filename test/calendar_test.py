import sys

sys.path.append("src/")
from google_calendar import GoogleCalendar

calendar = GoogleCalendar()


def print_calendars():
    print("Calendars: " + ", ".join(list(calendar.calendars.keys())))


def print_events():
    for c in calendar.calendars.keys():
        event = calendar.get_next_event(c)
        if event is None:
            print(c + ": None")
            continue
        name, date, _ = event
        print(c + ": " + name + " - " + date.strftime(GoogleCalendar.DATE_FORMAT))


print_calendars()
print_events()
