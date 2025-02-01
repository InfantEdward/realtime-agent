from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.routers import session, websocket
from app.services.websocket_service import WebsocketService


class RealtimeAPI(FastAPI):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.setup()

    def setup(self):
        # Serve static files (e.g., index.html)
        self.mount("/static", StaticFiles(directory="static"), name="static")

        # Create one instance of WebsocketService to share across routers
        ws_service = WebsocketService()

        # Store it in app.state so both session.py and websocket.py see the same service
        self.state.ws_service = ws_service

        # Include routers
        self.include_router(session.router)
        self.include_router(websocket.router)
