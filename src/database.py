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
    schedule: dict[int, tuple[bool, time, time]] = field(default_factory=dict)
    subscriptions: list[dict] = field(default_factory=list)
    
    def scheduleToStr(self):
        return str()

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