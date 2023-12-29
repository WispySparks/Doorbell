import sys

sys.path.append("src/")
from classes import GoogleCalendar

calendar = GoogleCalendar()

def dumpCalendar():
    print("Access Token: " + calendar.headers.get("Authorization", "").removeprefix("Bearer "))
    print("Calendars: " + ", ".join(list(calendar.calendars.keys())))
    for c in calendar.calendars.keys():
        event = calendar.getNextEvent(c)
        if (event is None):
            print(c + ": - None")
            continue
        name, date = event
        print(c + ": " + name + " - " + date.strftime(GoogleCalendar.dateFormat))

dumpCalendar()
calendar.headers = {"Authorization": "Bearer "}
dumpCalendar()
print("Access Token: " + calendar.headers.get("Authorization", "").removeprefix("Bearer "))