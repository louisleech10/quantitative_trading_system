"""IC analysis WebSocket endpoint for progress updates."""

import asyncio
from datetime import datetime
from typing import Dict, Optional, Set

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from api.core.logging import get_logger
from api.services.ic_analysis_service import ic_analysis_service


router = APIRouter(prefix="/ws")
logger = get_logger("api.websocket.ic_analysis")


class ICConnectionManager:
    """WebSocket connection manager for IC analysis."""

    def __init__(self) -> None:
        self._connections: Dict[str, Set[WebSocket]] = {}
        self._metadata: Dict[WebSocket, Dict[str, str]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, task_id: str, client_id: Optional[str]) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.setdefault(task_id, set()).add(websocket)
            self._metadata[websocket] = {
                "task_id": task_id,
                "client_id": client_id or "anonymous",
                "connected_at": datetime.now().isoformat(),
            }

        await self.send_personal_message(websocket, {
            "event": "connected",
            "data": {"task_id": task_id},
            "timestamp": datetime.now().isoformat(),
        })

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            metadata = self._metadata.pop(websocket, {})
            task_id = metadata.get("task_id")
            if task_id and task_id in self._connections:
                self._connections[task_id].discard(websocket)
                if not self._connections[task_id]:
                    del self._connections[task_id]

    async def send_personal_message(self, websocket: WebSocket, message: Dict) -> None:
        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.send_json(message)
        except Exception as exc:
            logger.error("Failed to send personal message: %s", exc, exc_info=True)

    async def broadcast(self, task_id: str, message: Dict) -> None:
        async with self._lock:
            subscribers = list(self._connections.get(task_id, set()))

        disconnected = []
        for websocket in subscribers:
            try:
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.send_json(message)
                else:
                    disconnected.append(websocket)
            except Exception:
                disconnected.append(websocket)

        for websocket in disconnected:
            await self.disconnect(websocket)


connection_manager = ICConnectionManager()


@router.websocket("/ic-analysis/{task_id}")
async def ic_analysis_websocket(
    websocket: WebSocket,
    task_id: str,
    client_id: Optional[str] = Query(None, description="Client id"),
):
    """IC analysis WebSocket endpoint."""
    task_status = ic_analysis_service.get_task_status(task_id)
    if not task_status:
        await websocket.close(code=4004, reason=f"Task not found: {task_id}")
        return

    await connection_manager.connect(websocket, task_id, client_id)
    loop = asyncio.get_running_loop()

    async def send_payload(payload: Dict) -> None:
        current_step = payload.get("current_step") or payload.get("module_name") or payload.get("stage")
        await connection_manager.broadcast(task_id, {
            "event": "progress",
            "data": {
                **payload,
                "current_step": current_step,
            },
            "timestamp": datetime.now().isoformat(),
        })

    def notification_callback(payload: Dict) -> None:
        asyncio.run_coroutine_threadsafe(send_payload(payload), loop)

    ic_analysis_service.register_notification_callback(task_id, notification_callback)

    try:
        heartbeat_task = asyncio.create_task(_send_heartbeat(websocket))

        while True:
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=60.0)
            except asyncio.TimeoutError:
                if websocket.client_state != WebSocketState.CONNECTED:
                    break

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.error("WebSocket error: %s", exc, exc_info=True)
    finally:
        heartbeat_task.cancel()
        await connection_manager.disconnect(websocket)
        ic_analysis_service.unregister_notification_callback(task_id, notification_callback)


async def _send_heartbeat(websocket: WebSocket, interval: int = 30) -> None:
    try:
        while True:
            await asyncio.sleep(interval)
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.send_json({
                    "event": "ping",
                    "timestamp": datetime.now().isoformat(),
                })
    except asyncio.CancelledError:
        pass
    except Exception as exc:
        logger.error("Heartbeat error: %s", exc, exc_info=True)
