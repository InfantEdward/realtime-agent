from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse


router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def serve_index():
    """
    Returns index.html at the root `/`
    """
    with open("static/index.html", "r", encoding="utf-8") as f:
        return f.read()


@router.post("/start_session")
async def start_session(request: Request):
    """
    Calls ws_service.start_session() -> spawns agent.connect() in background
    """
    ws_service = request.app.state.ws_service
    return await ws_service.start_session()


@router.post("/stop_session")
async def stop_session(session_id: str = Query(...), request: Request = None):
    """
    Calls ws_service.stop_session(session_id)
    """
    ws_service = request.app.state.ws_service
    return await ws_service.stop_session(session_id)
