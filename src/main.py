import datetime
import os
import sys
import traceback
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
            x = 3 / 0
            bot.main()
        except Exception as e:
            print(traceback.format_exc(), flush = True)
        sys.stderr.flush()