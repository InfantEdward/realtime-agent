from typing import Optional
from logging import Logger
from textual import events
from textual.app import App, ComposeResult
from textual.widgets import Button, RichLog
from textual.containers import Container
from src.utils.logging.log_utils import CustomLogger
from src.agent.agent import RealtimeAgent
from src.audio.audio_handler import RealtimeAudioHandler
from src.frontend.widgets import SessionDisplay, AudioStatusIndicator
from typing_extensions import override


class RealtimeFrontend(App[None]):
    CSS = """
        Screen {
            background: #1a1b26;  /* Dark blue-grey background */
        }

        Container {
            border: double rgb(91, 164, 91);
        }

        Horizontal {
            width: 100%;
        }

        #input-container {
            height: 5;  /* Explicit height for input container */
            margin: 1 1;
            padding: 1 2;
        }

        Input {
            width: 80%;
            height: 3;  /* Explicit height for input */
        }

        Button {
            width: 20%;
            height: 3;  /* Explicit height for button */
        }

        #bottom-pane {
            width: 100%;
            height: 82%;  /* Reduced to make room for session display */
            border: round rgb(205, 133, 63);
            content-align: center middle;
        }

        #status-indicator {
            height: 3;
            content-align: center middle;
            background: #2a2b36;
            border: solid rgb(91, 164, 91);
            margin: 1 1;
        }

        #session-display {
            height: 3;
            content-align: center middle;
            background: #2a2b36;
            border: solid rgb(91, 164, 91);
            margin: 1 1;
        }

        Static {
            color: white;
        }
    """

    def __init__(
        self,
        realtime_agent: RealtimeAgent,
        audio_handler: RealtimeAudioHandler,
        logger: Optional[Logger] = None,
    ) -> None:
        super().__init__()
        self.realtime_agent = realtime_agent
        self.audio_handler = audio_handler
        self.logger = logger or CustomLogger(__name__)
        self._setup_callbacks()

    def _setup_callbacks(self) -> None:
        try:
            self.logger.info("Setting up session created callback")
            self.realtime_agent.set_session_created_callback(
                self.on_session_created
            )
            self.logger.info("Setting up audio status update callback")
            self.audio_handler.set_status_update_callback(
                self.update_status_indicator
            )
        except Exception as e:
            self.logger.error(f"Error setting up callbacks: {e}")
            exit(1)

    @override
    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        with Container():
            yield SessionDisplay(id="session-display")
            yield AudioStatusIndicator(id="status-indicator")
            yield RichLog(
                id="bottom-pane", wrap=True, highlight=True, markup=True
            )

    def on_session_created(self, session_id: str) -> None:
        session_display = self.query_one(SessionDisplay)
        session_display.session_id = session_id

    async def on_mount(self) -> None:
        self.run_worker(self._handle_realtime())
        self.run_worker(self.audio_handler.send_mic_audio())

    async def _handle_realtime(self) -> None:
        async for evt_type, payload in self.realtime_agent.connect():
            if evt_type == "audio_delta":
                self.audio_handler.handle_incoming_audio(
                    payload.item_id, payload.delta
                )
            elif evt_type == "transcript_delta":
                bottom_pane = self.query_one("#bottom-pane", RichLog)
                bottom_pane.clear()
                bottom_pane.write(payload)

    async def on_key(self, event: events.Key) -> None:
        """Handle key press events."""
        if event.key == "enter":
            self.query_one(Button).press()
            return

        if event.key == "q":
            self.exit()
            return

        if event.key == "k":
            status_indicator = self.query_one(AudioStatusIndicator)
            if status_indicator.is_recording:
                self.audio_handler.should_send_audio.clear()
                status_indicator.is_recording = False
                if (
                    self.realtime_agent.session
                    and self.realtime_agent.session.turn_detection is None
                ):
                    conn = await self.realtime_agent.get_connection()
                    await conn.input_audio_buffer.commit()
                    await conn.response.create()
            else:
                self.audio_handler.should_send_audio.set()
                status_indicator.is_recording = True

    def update_status_indicator(self, is_recording: bool) -> None:
        status_indicator = self.query_one(AudioStatusIndicator)
        status_indicator.is_recording = is_recording
