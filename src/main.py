"""Run this file to start Doorbell normally."""

import os
import sys
import threading

from doorbell import Doorbell

if __name__ == "__main__":
    # The main thread sits here until Doorbell is closed by a command and then joins up with
    # all the other threads that have been cleaned up by Doorbell#close(), restarting if needed
    doorbell = Doorbell()
    print("Started Doorbell!")
    try:
        while not doorbell.closed:
            pass
    except KeyboardInterrupt:
        print("KeyboardInterrupt detected.")
        doorbell.close()
    for thread in threading.enumerate():
        if thread == threading.current_thread() or thread.daemon:
            continue
        thread.join()
    print("Exited Doorbell.")
    if doorbell.restarting:
        os.execl(sys.executable, f"{sys.executable}", *sys.argv)
