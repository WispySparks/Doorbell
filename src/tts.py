from concurrent.futures import Future, wait
from ctypes import WinError
from time import sleep
from typing import TypeVar

from winrt.windows.foundation import AsyncStatus, IAsyncOperation
from winrt.windows.media.core import MediaSource
from winrt.windows.media.playback import IMediaPlaybackSource, MediaPlayer
from winrt.windows.media.speechsynthesis import SpeechSynthesizer
from winrt.windows.storage.streams import IRandomAccessStream


class TTS:

    def __init__(self) -> None:
        self.player = MediaPlayer()
        self.synth = SpeechSynthesizer()

    def say(self, text: str, blocking: bool = False) -> None:
        """Says a string of text using text to speech. Can optionally be a blocking call.
        >>> tts_obj.say("Hello World")"""
        stream = self._wait_for(self.synth.synthesize_text_to_stream_async(text))
        source = MediaSource.create_from_stream(IRandomAccessStream._from(stream), stream.content_type)
        if source is None:
            return
        self.player.source = IMediaPlaybackSource._from(source)
        if blocking:
            session = self.player.playback_session
            if session is None:
                return
            time_waited = 0
            while session.natural_duration.total_seconds() == 0:  # Wait until audio is loaded
                sleep(0.1)
                time_waited += 0.1
                if time_waited > 5:  # Timeout after 5 seconds
                    return
            self.player.play()
            sleep(session.natural_duration.total_seconds())
        else:
            self.player.play()

    # SPDX-License-Identifier: MIT
    # Copyright 2024 David Lechner <david@pybricks.com>
    # https://github.com/pywinrt/pywinrt/blob/c5cc3fd54934eff02ba200b3ef665541a68194e5/samples/screen_capture/sync.py
    _T = TypeVar("_T")

    def _wait_for(self, operation: IAsyncOperation[_T]) -> _T:
        """
        Wait for the given async operation to complete and return its result.

        For use in non-asyncio apps.
        """
        future = Future()

        def completed(async_op: IAsyncOperation, status: AsyncStatus):
            try:
                if status == AsyncStatus.COMPLETED:
                    future.set_result(async_op.get_results())
                elif status == AsyncStatus.ERROR:
                    future.set_exception(WinError(async_op.error_code.value))
                elif status == AsyncStatus.CANCELED:
                    future.cancel()
            except BaseException as e:
                future.set_exception(e)

        operation.completed = completed

        wait([future])

        return future.result()
