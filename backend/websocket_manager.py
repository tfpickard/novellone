import asyncio
import json
import logging
from typing import Any, Set

from starlette.websockets import WebSocket

logger = logging.getLogger(__name__)


class WebSocketManager:
    def __init__(self) -> None:
        self._connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.add(websocket)
        logger.debug("WebSocket connected: %s", websocket.client)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections.discard(websocket)
        logger.debug("WebSocket disconnected: %s", websocket.client)

    async def broadcast(self, message: dict[str, Any]) -> None:
        data = json.dumps(message)
        async with self._lock:
            connections = list(self._connections)
        for connection in connections:
            try:
                await connection.send_text(data)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to send message via WebSocket: %s", exc)


ws_manager = WebSocketManager()

__all__ = ["WebSocketManager", "ws_manager"]
