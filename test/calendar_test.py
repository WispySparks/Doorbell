import sys

sys.path.append("src/")
from google_calendar import GoogleCalendar

calendar = GoogleCalendar()


def printCalendars():
    print("Calendars: " + ", ".join(list(calendar.calendars.keys())))


def printEvents():
    for c in calendar.calendars.keys():
        event = calendar.getNextEvent(c)
        if event is None:
            print(c + ": None")
            continue
        name, date, _ = event
        print(c + ": " + name + " - " + date.strftime(GoogleCalendar.DATE_FORMAT))


printCalendars()
printEvents()
