import os
import pickle
from dataclasses import dataclass, field
from datetime import time
from threading import Lock
from typing import Final, NamedTuple, Optional, override

lock: Final = Lock()
filePath: Final = "data.pickle"
DayTuple = NamedTuple("DayTuple", [("startTime", time), ("endTime", time)])

@dataclass(frozen=True)
class Data:
    schedule: list[Optional[DayTuple]] = field(default_factory=list) # 7 days long, starts at Monday
    subscriptions: list[dict] = field(default_factory=list)
    
    @override
    def __str__(self) -> str:
        return "Mo: " + self.__dayToStr(self.schedule[0]) \
        + " | Tu: " + self.__dayToStr(self.schedule[1]) \
        + " | We: " + self.__dayToStr(self.schedule[2]) \
        + " | Th: " + self.__dayToStr(self.schedule[3]) \
        + " | Fr: " + self.__dayToStr(self.schedule[4]) \
        + " | Sa: " + self.__dayToStr(self.schedule[5]) \
        + " | Su: " + self.__dayToStr(self.schedule[6])
    
    def __dayToStr(self, day: Optional[DayTuple]) -> str:
        if (day is None): return "--"
        return day.startTime.strftime("%I:%M %p") + " - " + day.endTime.strftime("%I:%M %p")
        

def create() -> None:
    if (not os.path.exists(filePath)):
        write(Data())

def read() -> Data:
    with open(filePath, "rb") as f:
        return pickle.load(f)
    
def write(data: Data) -> None:
    with lock: 
        with open(filePath, "wb") as f:
            pickle.dump(data, f)