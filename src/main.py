import os

import bot

if __name__ == "__main__":
    if not os.path.isfile(bot.dataPath):
        bot.writeDataAll(None, None, [])
    bot.eventPoller.start()
    while True: 
        try:
            bot.main()
        except Exception as e:
            print(e)