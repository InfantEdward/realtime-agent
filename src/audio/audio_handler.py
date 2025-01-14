import asyncio
import base64
import sounddevice as sd  # type: ignore
from typing import Any, Callable, Optional, cast
from src.audio.audio_util import CHANNELS, SAMPLE_RATE, AudioPlayerAsync
from src.agent.agent import RealtimeAgent


class RealtimeAudioHandler:
    def __init__(self, realtime_agent: RealtimeAgent) -> None:
        self.realtime_agent = realtime_agent
        self.should_send_audio = asyncio.Event()
        self.last_audio_item_id: str | None = None
        self.audio_player = AudioPlayerAsync()
        self.status_update_callback: Optional[Callable[[bool], None]] = None

    async def send_mic_audio(self) -> None:

        sent_audio = False
        read_size = int(SAMPLE_RATE * 0.02)
        stream = sd.InputStream(
            channels=CHANNELS,
            samplerate=SAMPLE_RATE,
            dtype="int16",
        )
        stream.start()

        try:
            while True:
                if stream.read_available < read_size:
                    await asyncio.sleep(0)
                    continue

                await self.should_send_audio.wait()

                if self.status_update_callback:
                    self.status_update_callback(True)

                data, _ = stream.read(read_size)

                connection = await self.realtime_agent.get_connection()
                if not sent_audio:
                    asyncio.create_task(
                        connection.send({"type": "response.cancel"})
                    )
                    sent_audio = True

                await connection.input_audio_buffer.append(
                    audio=base64.b64encode(cast(Any, data)).decode("utf-8")
                )

                await asyncio.sleep(0)
        except KeyboardInterrupt:
            pass
        finally:
            stream.stop()
            stream.close()

    def handle_incoming_audio(self, event_item_id: str, delta: bytes) -> None:
        if event_item_id != self.last_audio_item_id:
            self.audio_player.reset_frame_count()
            self.last_audio_item_id = event_item_id
        bytes_data = base64.b64decode(delta)
        self.audio_player.add_data(bytes_data)

    def set_status_update_callback(
        self, callback: Callable[[bool], None]
    ) -> None:
        self.status_update_callback = callback
