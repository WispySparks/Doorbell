import os
import pickle
from dataclasses import dataclass, field
from datetime import time
from threading import Lock
from typing import Final

lock: Final = Lock()
filePath: Final = "data.pickle"

@dataclass(frozen=True)
class Data:
    schedule: list[tuple[bool, time, time]] = field(default_factory=list) # 7 days long, starts at Monday
    subscriptions: list[dict] = field(default_factory=list)
    
    def scheduleToStr(self) -> str:
        return "Mo: " + self.__dayToStr(self.schedule[0]) \
        + " Tu: " + self.__dayToStr(self.schedule[1]) \
        + " We: " + self.__dayToStr(self.schedule[2]) \
        + " Th: " + self.__dayToStr(self.schedule[3]) \
        + " Fr: " + self.__dayToStr(self.schedule[4]) \
        + " Sa: " + self.__dayToStr(self.schedule[5]) \
        + " Su: " + self.__dayToStr(self.schedule[6])
    
    def __dayToStr(self, day: tuple[bool, time, time]) -> str:
        validDay, start, end = day
        if (not validDay): return "--"
        return start.strftime("%H:%M") + "-" + end.strftime("%H:%M")
        

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