import json
from typing import Dict, Set
from uuid import UUID
from fastapi import WebSocket

class ConnectionManager:
    """
    Manages active WebSocket connections per project workspace.
    Broadcasts real-time events when project activities, crashing, or schedule simulations change.
    """
    def __init__(self):
        # Maps project_id (str) to set of active WebSocket instances
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, project_id: str):
        await websocket.accept()
        if project_id not in self.active_connections:
            self.active_connections[project_id] = set()
        self.active_connections[project_id].add(websocket)

    def disconnect(self, websocket: WebSocket, project_id: str):
        if project_id in self.active_connections:
            self.active_connections[project_id].discard(websocket)
            if not self.active_connections[project_id]:
                del self.active_connections[project_id]

    async def broadcast(self, project_id: str, message: dict):
        p_id = str(project_id)
        if p_id in self.active_connections:
            dead_sockets = set()
            for connection in list(self.active_connections[p_id]):
                try:
                    await connection.send_json(message)
                except Exception:
                    dead_sockets.add(connection)
            for ws in dead_sockets:
                self.disconnect(ws, p_id)

ws_manager = ConnectionManager()
