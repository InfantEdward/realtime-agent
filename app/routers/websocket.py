from fastapi import APIRouter, WebSocket
from starlette.websockets import WebSocketDisconnect

router = APIRouter()


@router.websocket("/ws/audio/{session_id}")
async def websocket_audio_endpoint(websocket: WebSocket, session_id: str):
    ws_service = websocket.app.state.ws_service

    try:
        await ws_service.handle_websocket(websocket, session_id)
    except WebSocketDisconnect:
        pass
