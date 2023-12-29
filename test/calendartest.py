import sys

sys.path.append("src/")
from classes import GoogleCalendar

calendar = GoogleCalendar()

def invalidateToken():
    calendar.headers = {"Authorization": "Bearer "}

def printToken():
    print("Access Token: " + calendar.headers.get("Authorization", "").removeprefix("Bearer "))
    
def printCalendars():
    print("Calendars: " + ", ".join(list(calendar.calendars.keys())))

def printEvents():
    for c in calendar.calendars.keys():
        event = calendar.getNextEvent(c)
        if (event is None):
            print(c + ": None")
            continue
        name, date, _ = event
        print(c + ": " + name + " - " + date.strftime(GoogleCalendar.dateFormat))

printToken()
printCalendars()
printEvents()
invalidateToken()
calendar.refreshCalendars()
printCalendars()
invalidateToken()
printEvents()