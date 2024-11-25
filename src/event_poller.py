"""Contains the Event Poller which polls for any subscriptions and sends reminders."""

from __future__ import annotations

import time
from datetime import datetime
from threading import Thread
from typing import TYPE_CHECKING

import database
from google_calendar import GoogleCalendar

if TYPE_CHECKING:
    from doorbell import Doorbell


class EventPoller(Thread):
    """Used to poll any subscriptions and send appropriate reminders."""

    def __init__(self, interval_seconds: float, doorbell: Doorbell) -> None:
        super().__init__(target=self._continuously_poll, name="Event Poller")
        self.interval_seconds = interval_seconds
        self.doorbell = doorbell
        self.stopped = False

    def stop(self) -> None:
        """Stops this thread."""
        self.stopped = True

    def _continuously_poll(self) -> None:
        while not self.stopped:
            self._poll_subscriptions()
            time.sleep(self.interval_seconds)
        print("Stopped Event Poller.")

    def _poll_subscriptions(self) -> None:
        data = database.read()
        for sub in data.subscriptions:
            current_date = datetime.now().astimezone()
            if sub.next_event is None:  # Check if a new event has been added
                min_date = max(current_date, sub.last_event)
                next_event = self.doorbell.calendar.get_next_event(sub.calendar_name, min_date)
                sub.next_event = next_event
                continue
            name = sub.next_event.name
            remind_window_start = sub.next_event.start - sub.remind_time
            if current_date >= remind_window_start.astimezone():
                self.doorbell.post_message(
                    channel_id=sub.channel_id,
                    message=f"Reminder: {name} - {sub.next_event.start.strftime(GoogleCalendar.DATE_FORMAT)}",
                )
                event_end = sub.next_event.end
                min_date = max(current_date, event_end)
                next_event = self.doorbell.calendar.get_next_event(sub.calendar_name, min_date)
                sub.next_event = next_event
                sub.last_event = event_end
        database.write(data)
