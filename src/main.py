import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Final

import bot

if (__name__ == "__main__"):
    logDir: Final[str] = "./logs/"
    Path(logDir).mkdir(exist_ok=True)
    if ("-l" in sys.argv):
        sys.stderr = sys.stdout = open(logDir + datetime.now().strftime("%Y-%m-%d--%H-%M-%S") + ".log", 'w')
    # if (not os.path.isfile(bot.dataPath)):
    #     bot.writeDataAll(None, None, [])
    # bot.eventPoller.start()
    while True: 
        try:
            bot.main()
        except Exception as e:
            print(traceback.format_exc())