import time
from datetime import datetime, timedelta
from threading import Thread

import app
import database
from google_calendar import GoogleCalendar


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
        if event is None:
            return None
        name, startTime, endTime = event
        return {"name": name, "start": startTime.isoformat(), "end": endTime.isoformat()}

    def pollSubscriptions(self) -> None:
        subs = database.read().subscriptions
        sub: dict
        for sub in subs:
            currentDate = datetime.now().astimezone()
            channelId = sub.get("channelId", "")
            calendarName = sub.get("calendarName", "")
            remindTime = sub.get("remindTime", 0)
            event = sub.get("nextEvent")
            if event is None:  # Check if a new event has been added
                last = datetime.fromisoformat(sub.get("lastEvent", currentDate.isoformat()))
                minDate = max(currentDate, last)
                e = app.calendar.getNextEvent(calendarName, minDate)
                sub.update({"nextEvent": self.eventStruct(e)})
                continue
            name = event.get("name")
            eventStart = datetime.fromisoformat(event.get("start"))
            remindWindowStart = eventStart - timedelta(hours=remindTime)
            if currentDate >= remindWindowStart.astimezone():
                app.app.client.chat_postMessage(
                    channel=channelId, text="Reminder: " + name + " - " + eventStart.strftime(GoogleCalendar.dateFormat)
                )
                eventEnd = datetime.fromisoformat(event.get("end"))
                minDate = max(currentDate, eventEnd)
                nextEvent = app.calendar.getNextEvent(calendarName, minDate)
                sub.update({"nextEvent": self.eventStruct(nextEvent)})
                sub.update({"lastEvent": eventEnd.isoformat()})
        database.write(database.Data(subscriptions=subs))
