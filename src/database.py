"""Contains the Data struct stored in the database and methods for interacting with the database.
The database is stored as a pickle file."""

import os
import pickle
from dataclasses import dataclass, field
from datetime import time
from threading import Lock
from typing import Final, NamedTuple, Optional

LOCK: Final = Lock()
FILE_PATH: Final = "data.pickle"
DayTuple = NamedTuple("DayTuple", [("start_time", time), ("end_time", time)])


@dataclass(frozen=True)
class Data:
    """The Data object being stored in the database."""

    schedule: list[Optional[DayTuple]] = field(default_factory=list)  # 7 days long, starts at Monday
    subscriptions: list[dict] = field(default_factory=list)

    def schedule_to_str(self) -> str:
        """Formats the internal schedule as a pretty string."""
        return (
            f"Mo: {self._day_to_str(self.schedule[0])}"
            + f" | Tu: {self._day_to_str(self.schedule[1])}"
            + f" | We: {self._day_to_str(self.schedule[2])}"
            + f" | Th: {self._day_to_str(self.schedule[3])}"
            + f" | Fr: {self._day_to_str(self.schedule[4])}"
            + f" | Sa: {self._day_to_str(self.schedule[5])}"
            + f" | Su: {self._day_to_str(self.schedule[6])}"
        )

    def _day_to_str(self, day: Optional[DayTuple]) -> str:
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
    with open(FILE_PATH, "rb") as f:
        return pickle.load(f)


def write(data: Data) -> None:
    """Writes data to the pickle file containing the database."""
    with LOCK:
        with open(FILE_PATH, "wb") as f:
            pickle.dump(data, f)


def delete() -> None:
    """Deletes the pickle file containing the database."""
    with LOCK:
        if os.path.exists(FILE_PATH):
            os.remove(FILE_PATH)
