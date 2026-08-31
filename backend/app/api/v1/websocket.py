from uuid import UUID
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.core.websocket import ws_manager

router = APIRouter(tags=["websockets"])

@router.websocket("/projects/{project_id}/ws")
@router.websocket("/ws/projects/{project_id}")
async def project_events_websocket(websocket: WebSocket, project_id: str):
    """
    WebSocket endpoint for real-time project schedule & activity updates.
    Broadcasts live updates whenever activities are added, updated, deleted, or simulated.
    """
    await ws_manager.connect(websocket, project_id)
    try:
        while True:
            # Maintain active connection and accept client messages (e.g. ping/heartbeat)
            data = await websocket.receive_text()
            # Echo back ping acknowledgement
            if data == "ping":
                await websocket.send_json({"type": "pong", "project_id": project_id})
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, project_id)
    except Exception:
        ws_manager.disconnect(websocket, project_id)
