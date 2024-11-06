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
    schedule: list[Optional[DayTuple]] = field(default_factory=list)  # 7 days long, starts at Monday
    subscriptions: list[dict] = field(default_factory=list)

    def schedule_to_str(self) -> str:
        return (
            f"Mo: {self.__day_to_str(self.schedule[0])}"
            + f" | Tu: {self.__day_to_str(self.schedule[1])}"
            + f" | We: {self.__day_to_str(self.schedule[2])}"
            + f" | Th: {self.__day_to_str(self.schedule[3])}"
            + f" | Fr: {self.__day_to_str(self.schedule[4])}"
            + f" | Sa: {self.__day_to_str(self.schedule[5])}"
            + f" | Su: {self.__day_to_str(self.schedule[6])}"
        )

    def __day_to_str(self, day: Optional[DayTuple]) -> str:
        time_format = "%I:%M %p"
        if day is None:
            return "--"
        return f"{day.start_time.strftime(time_format)} - {day.end_time.strftime(time_format)}"


def create() -> None:
    if not os.path.exists(FILE_PATH):
        write(Data())


def read() -> Data:
    with open(FILE_PATH, "rb") as f:
        return pickle.load(f)


def write(data: Data) -> None:
    with LOCK:
        with open(FILE_PATH, "wb") as f:
            pickle.dump(data, f)


def delete() -> None:
    with LOCK:
        if os.path.exists(FILE_PATH):
            os.remove(FILE_PATH)
