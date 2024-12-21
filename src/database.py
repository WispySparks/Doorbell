"""Contains the Data struct stored in the database and methods for interacting with the database.
The database is stored as a pickle file."""

from __future__ import annotations

import os
import pickle
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from threading import Lock
from typing import TYPE_CHECKING, Final, Optional

from google_calendar import CalendarEvent

if TYPE_CHECKING:
    from doorbell import Doorbell


_LOCK: Final = Lock()
FILE_PATH: Final = "data.pickle"


@dataclass(frozen=True)
class DaySchedule:
    """The schedule for a single day."""

    start_time: time
    end_time: time


@dataclass
class Subscription:
    """A subscription to a google calendar in a channel."""

    channel_id: str
    calendar_name: str
    remind_time: timedelta
    next_event: Optional[CalendarEvent]
    last_event: datetime


@dataclass
class Data:
    """The Data object being stored in the database."""

    schedule: list[Optional[DaySchedule]] = field(default_factory=list)  # 7 days long, starts at Monday
    subscriptions: list[Subscription] = field(default_factory=list)
    roles: dict[str, set[str]] = field(default_factory=dict)

    def schedule_to_str(self) -> str:
        """Formats the internal schedule as a pretty string."""
        if not self.schedule:
            return "No schedule."
        return (
            f"Mo: {self._day_to_str(self.schedule[0])}"
            + f" | Tu: {self._day_to_str(self.schedule[1])}"
            + f" | We: {self._day_to_str(self.schedule[2])}"
            + f" | Th: {self._day_to_str(self.schedule[3])}"
            + f" | Fr: {self._day_to_str(self.schedule[4])}"
            + f" | Sa: {self._day_to_str(self.schedule[5])}"
            + f" | Su: {self._day_to_str(self.schedule[6])}"
        )

    def all_subscriptions_to_str(self, doorbell: Doorbell) -> str:
        """Formats all the internal subscriptions as a pretty string."""
        if not self.subscriptions:
            return "No subscriptions."
        string = "All Subscriptions:\n"
        channel_ids = set()
        for sub in self.subscriptions:
            channel_ids.add(sub.channel_id)
        for channel_id in channel_ids:
            string += doorbell.get_channel_name(channel_id) + " " + self.subscriptions_to_str(channel_id) + "\n"
        return string.strip()

    def subscriptions_to_str(self, channel_id: str) -> str:
        """Formats the internal subscriptions for a given channel as a pretty string."""
        subs = self.subscriptions_for_channel(channel_id)
        if not subs:
            return "No subscriptions."
        string = "Subscriptions:\n"
        for sub in subs:
            name = "None" if sub.next_event is None else sub.next_event.name
            string += (
                f"{sub.calendar_name}: {sub.remind_time.total_seconds() / 3600} hours, next reminder is for {name}\n"
            )
        return string.strip()

    def subscriptions_for_channel(self, channel_id: str) -> list[Subscription]:
        """Returns all the subscriptions within a given Slack channel."""
        subs = []
        for sub in self.subscriptions:
            if sub.channel_id == channel_id:
                subs.append(sub)
        return subs

    def add_role(self, role: str, *users: str):
        if role not in self.roles:
            self.roles[role] = set()
        for user in users:
            self.roles[role].add(user)

    def remove_role(self, role: str, *users: str):
        for user in users:
            if user in self.roles[role]:
                self.roles[role].remove(user)
        if not self.roles[role]:
            self.roles.pop(role)

    def get_roles(self) -> list[str]:
        return list(self.roles.keys())

    def get_roles_for_user(self, user: str) -> list[str]:
        user_roles = []
        for role, users in self.roles.items():
            if user in users:
                user_roles.append(role)
                continue
        return user_roles

    def _day_to_str(self, day: Optional[DaySchedule]) -> str:
        time_format = "%I:%M %p"
        if day is None:
            return "--"
        return f"{day.start_time.strftime(time_format)} - {day.end_time.strftime(time_format)}"


def create() -> None:
    """Creates a pickle file containing the database if it doesn't exist."""
    if not os.path.exists(FILE_PATH):
        write(Data())


def read() -> Data:
    """Reads data from the pickle file containing the database."""
    with _LOCK:
        with open(FILE_PATH, "rb") as f:
            return pickle.load(f)


def write(data: Data) -> None:
    """Writes data to the pickle file containing the database."""
    with _LOCK:
        with open(FILE_PATH, "wb") as f:
            pickle.dump(data, f)


def delete() -> None:
    """Deletes the pickle file containing the database."""
    with _LOCK:
        if os.path.exists(FILE_PATH):
            os.remove(FILE_PATH)


def get_copy() -> bytearray:
    """Returns a bytearray with a copy of the database's (pickle file) contents."""
    with _LOCK:
        buffer = bytearray(os.path.getsize(FILE_PATH))
        with open(FILE_PATH, "rb") as f:
            f.readinto1(buffer)
        return buffer


def check_for_corruption() -> None:
    """Attempts to read the pickle file and if there's an error
    the old database will be deleted and a new one created."""
    try:
        data = read()
        if vars(data).keys() != vars(Data()).keys():
            raise AttributeError()
    except AttributeError:  # Corrupted / Structure changed
        print("Couldn't read database, recreating...")
        delete()
        create()
