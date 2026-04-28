"""
Feature Factory WebSocket Endpoint - 實時進度推送
"""

import asyncio
from datetime import datetime
from typing import Dict, Optional, Set

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from api.core.logging import get_logger
from api.services.feature_factory_batch_service import get_feature_factory_batch_service
from api.services.feature_factory_service import feature_factory_service


router = APIRouter(prefix="/ws")
logger = get_logger("api.websocket.feature_factory")


class FeatureFactoryConnectionManager:
    """WebSocket connection manager for Feature Factory."""

    def __init__(self):
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


connection_manager = FeatureFactoryConnectionManager()


class FeatureFactoryBatchConnectionManager:
    """WebSocket connection manager for Feature Factory batch tasks."""

    def __init__(self):
        self._connections: Dict[str, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, task_id: str) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.setdefault(task_id, set()).add(websocket)

    async def disconnect(self, websocket: WebSocket, task_id: str) -> None:
        async with self._lock:
            if task_id in self._connections:
                self._connections[task_id].discard(websocket)
                if not self._connections[task_id]:
                    del self._connections[task_id]

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
            await self.disconnect(websocket, task_id)


batch_manager = FeatureFactoryBatchConnectionManager()


@router.websocket("/features/{task_id}")
async def feature_factory_websocket(
    websocket: WebSocket,
    task_id: str,
    client_id: Optional[str] = Query(None, description="客戶端ID")
):
    """Feature Factory WebSocket endpoint."""
    task_status = feature_factory_service.get_task_status(task_id)
    if not task_status:
        await websocket.close(code=4004, reason=f"Task not found: {task_id}")
        return

    await connection_manager.connect(websocket, task_id, client_id)

    async def send_payload(payload: Dict) -> None:
        await connection_manager.broadcast(task_id, {
            "event": "progress",
            "data": payload,
            "timestamp": datetime.now().isoformat(),
        })

    def notification_callback(payload: Dict) -> None:
        asyncio.create_task(send_payload(payload))

    feature_factory_service.register_notification_callback(task_id, notification_callback)

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
        feature_factory_service.unregister_notification_callback(task_id, notification_callback)


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


@router.websocket("/features/batch/{task_id}")
async def feature_factory_batch_websocket(websocket: WebSocket, task_id: str):
    """Feature Factory batch progress WebSocket endpoint."""
    batch_service = get_feature_factory_batch_service()
    status = batch_service.get_status(task_id)
    if not status:
        await websocket.close(code=4004, reason=f"Task not found: {task_id}")
        return

    await batch_manager.connect(websocket, task_id)

    async def send_payload(payload: Dict) -> None:
        await batch_manager.broadcast(task_id, {
            "event": "batch_progress",
            "data": {
                "task_id": payload.get("task_id"),
                "total": payload.get("total", 0),
                "completed": payload.get("completed", 0),
                "failed": payload.get("failed", 0),
                "current_symbol": payload.get("current_symbol"),
                "current_timeframe": payload.get("current_timeframe"),
                "progress": payload.get("progress", 0.0),
                "status": payload.get("status"),
                "queued": payload.get("queued", 0),
                "concurrent_symbols": payload.get("concurrent_symbols", 1),
                "memory_sanity_failed": payload.get("memory_sanity_failed", False),
                "last_item_metrics": payload.get("last_item_metrics"),
            },
            "timestamp": datetime.now().isoformat(),
        })

    def notification_callback(payload: Dict) -> None:
        asyncio.create_task(send_payload(payload))

    batch_service.register_notification_callback(task_id, notification_callback)
    await send_payload(status)

    try:
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30)
                if data == "ping":
                    await websocket.send_json({"event": "pong"})
            except asyncio.TimeoutError:
                await websocket.send_json({"event": "ping"})
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.error("Batch WebSocket error: %s", exc, exc_info=True)
    finally:
        await batch_manager.disconnect(websocket, task_id)
        batch_service.unregister_notification_callback(task_id, notification_callback)
