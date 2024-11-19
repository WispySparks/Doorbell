import time
from datetime import datetime, timedelta
from threading import Thread
from typing import Optional

import database
from doorbell import Doorbell
from google_calendar import GoogleCalendar


class EventPoller(Thread):

    def __init__(self, interval_seconds: int, doorbell: Doorbell) -> None:
        super().__init__()
        self._target = self.continuously_poll
        self.interval_seconds = interval_seconds
        self.doorbell = doorbell
        self.stopped = False

    def stop(self) -> None:
        self.stopped = True

    def continuously_poll(self) -> None:
        time.sleep(5)
        while not self.stopped:
            self.poll_subscriptions()
            time.sleep(self.interval_seconds)
        print("Stopped Event Poller.")

    def event_struct(self, event: tuple[str, datetime, datetime]) -> Optional[dict]:
        if event is None:
            return None
        name, start_time, end_time = event
        return {"name": name, "start": start_time.isoformat(), "end": end_time.isoformat()}

    def poll_subscriptions(self) -> None:
        subs = database.read().subscriptions
        sub: dict
        for sub in subs:
            current_date = datetime.now().astimezone()
            channel_id = sub.get("channelId", "")
            calendar_name = sub.get("calendarName", "")
            remind_time = sub.get("remindTime", 0)
            event = sub.get("nextEvent")
            if event is None:  # Check if a new event has been added
                last = datetime.fromisoformat(sub.get("lastEvent", current_date.isoformat()))
                min_date = max(current_date, last)
                next_event = self.doorbell.calendar.get_next_event(calendar_name, min_date)
                if next_event is not None:
                    sub.update({"nextEvent": self.event_struct(next_event)})
                continue
            name = event.get("name")
            event_start = datetime.fromisoformat(event.get("start"))
            remind_window_start = event_start - timedelta(hours=remind_time)
            if current_date >= remind_window_start.astimezone():
                self.doorbell.app.client.chat_postMessage(
                    channel=channel_id,
                    text=f"Reminder: {name} - {event_start.strftime(GoogleCalendar.DATE_FORMAT)}",
                )
                event_end = datetime.fromisoformat(event.get("end"))
                min_date = max(current_date, event_end)
                next_event = self.doorbell.calendar.get_next_event(calendar_name, min_date)
                if next_event is not None:
                    sub.update({"nextEvent": self.event_struct(next_event)})
                sub.update({"lastEvent": event_end.isoformat()})
        database.write(database.Data(subscriptions=subs))
