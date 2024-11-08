import sys

sys.path.append("src/")
from time import sleep

from tts import TTS

tts = TTS()
tts.say("Hello World hi hi hi lol", blocking=True)
tts.say("Hello World")
sleep(0.5)
tts.say("Bob says hi", blocking=True)
