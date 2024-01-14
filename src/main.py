import datetime
import os
import sys
from pathlib import Path

import bot

if __name__ == "__main__":
    Path("./logs/").mkdir(exist_ok=True)
    if (sys.argv.__contains__("-L")):
        sys.stderr = sys.stdout = open("logs/" + datetime.datetime.now().strftime("%Y-%m-%d--%H-%M-%S") + ".log", 'w')
    if (not os.path.isfile(bot.dataPath)):
        bot.writeDataAll(None, None, [])
    bot.eventPoller.start()
    while True: 
        try:
            bot.main()
        except Exception as e:
            print(e, flush=True)
            sys.stderr.flush()