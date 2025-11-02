"""
優化任務 WebSocket Endpoint - 實時進度推送

功能:
1. WebSocket連接管理（訂閱/取消訂閱）
2. 實時進度推送（通過ProgressMonitor callback）
3. 心跳檢測（保持連接活躍）
4. 錯誤處理與自動重連

Author: Claude (Phase 3.5 Day 5-6)
Date: 2025-11-02
"""

import asyncio
import json
from typing import Dict, Set, Optional
from datetime import datetime

from fastapi import WebSocket, WebSocketDisconnect, APIRouter, Query
from starlette.websockets import WebSocketState

from api.core.logging import get_logger
from api.services.optimization_task_service import optimization_task_service


router = APIRouter(prefix="/ws")


class WebSocketConnectionManager:
    """
    WebSocket連接管理器

    負責管理所有優化任務的WebSocket連接，支援:
    1. 連接管理: 添加/移除連接
    2. 訂閱管理: task_id -> WebSocket映射
    3. 消息廣播: 推送進度給訂閱者
    4. 心跳檢測: 保持連接活躍

    設計理念:
    - 單例模式: 全局唯一連接管理器
    - 線程安全: 使用asyncio.Lock保護共享狀態
    - 訂閱模式: 每個task_id可以有多個訂閱者（多用戶場景）
    """

    def __init__(self):
        """初始化WebSocket連接管理器"""
        self.logger = get_logger("api.websocket_manager")

        # 活躍連接（task_id -> Set[WebSocket]）
        self.active_connections: Dict[str, Set[WebSocket]] = {}

        # 連接元數據（WebSocket -> metadata）
        self.connection_metadata: Dict[WebSocket, Dict] = {}

        # 異步鎖（保護共享狀態）
        self.lock = asyncio.Lock()

        self.logger.info("WebSocketConnectionManager initialized")

    async def connect(self, websocket: WebSocket, task_id: str, client_id: Optional[str] = None):
        """
        接受WebSocket連接並訂閱任務

        Args:
            websocket: WebSocket連接
            task_id: 任務ID
            client_id: 客戶端ID（可選，用於識別多個連接）
        """
        await websocket.accept()

        async with self.lock:
            # 添加到訂閱列表
            if task_id not in self.active_connections:
                self.active_connections[task_id] = set()

            self.active_connections[task_id].add(websocket)

            # 保存元數據
            self.connection_metadata[websocket] = {
                'task_id': task_id,
                'client_id': client_id or 'anonymous',
                'connected_at': datetime.now().isoformat()
            }

        self.logger.info(
            f"WebSocket connected: task_id={task_id}, "
            f"client_id={client_id}, total_subscribers={len(self.active_connections[task_id])}"
        )

        # 發送連接成功消息
        await self.send_personal_message(websocket, {
            'event': 'connected',
            'data': {
                'task_id': task_id,
                'message': 'WebSocket connection established'
            }
        })

        # 發送當前任務狀態
        await self._send_current_task_status(websocket, task_id)

    async def disconnect(self, websocket: WebSocket):
        """
        斷開WebSocket連接

        Args:
            websocket: WebSocket連接
        """
        async with self.lock:
            # 獲取元數據
            metadata = self.connection_metadata.get(websocket, {})
            task_id = metadata.get('task_id')

            # 從訂閱列表移除
            if task_id and task_id in self.active_connections:
                self.active_connections[task_id].discard(websocket)

                # 如果沒有訂閱者了，清理task_id
                if not self.active_connections[task_id]:
                    del self.active_connections[task_id]

            # 清理元數據
            if websocket in self.connection_metadata:
                del self.connection_metadata[websocket]

        self.logger.info(f"WebSocket disconnected: task_id={task_id}")

    async def send_personal_message(self, websocket: WebSocket, message: dict):
        """
        發送消息給單個連接

        Args:
            websocket: WebSocket連接
            message: 消息字典
        """
        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.send_json(message)
        except Exception as e:
            self.logger.error(f"Failed to send personal message: {e}")

    async def broadcast_to_task(self, task_id: str, message: dict):
        """
        廣播消息給任務的所有訂閱者

        Args:
            task_id: 任務ID
            message: 消息字典
        """
        async with self.lock:
            if task_id not in self.active_connections:
                return

            # 複製訂閱者列表（避免迭代時修改）
            subscribers = list(self.active_connections[task_id])

        # 向所有訂閱者發送消息
        disconnected = []
        for websocket in subscribers:
            try:
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.send_json(message)
                else:
                    disconnected.append(websocket)
            except Exception as e:
                self.logger.error(f"Failed to broadcast to task {task_id}: {e}")
                disconnected.append(websocket)

        # 清理斷開的連接
        for websocket in disconnected:
            await self.disconnect(websocket)

    async def _send_current_task_status(self, websocket: WebSocket, task_id: str):
        """
        發送當前任務狀態（連接建立時）

        Args:
            websocket: WebSocket連接
            task_id: 任務ID
        """
        try:
            task_info = optimization_task_service.get_task(task_id)

            if task_info:
                await self.send_personal_message(websocket, {
                    'event': 'task_status',
                    'data': task_info.to_dict()
                })
        except Exception as e:
            self.logger.error(f"Failed to send current task status: {e}")

    def get_connection_count(self, task_id: str) -> int:
        """
        獲取任務的訂閱者數量

        Args:
            task_id: 任務ID

        Returns:
            訂閱者數量
        """
        return len(self.active_connections.get(task_id, set()))


# 全局單例
websocket_manager = WebSocketConnectionManager()


@router.websocket("/optimization/{task_id}")
async def optimization_websocket_endpoint(
    websocket: WebSocket,
    task_id: str,
    client_id: Optional[str] = Query(None, description="客戶端ID（可選）")
):
    """
    優化任務WebSocket端點

    連接URL: ws://localhost:8000/ws/optimization/{task_id}?client_id=xxx

    消息格式（服務器->客戶端）:
    {
        "event": "progress_update" | "new_best_value" | "milestone_reached" | "optimization_finished" | "error",
        "data": {
            "task_id": "xxx",
            ... event-specific data ...
        },
        "timestamp": "2025-11-02T16:00:00.000Z"
    }

    心跳機制:
    - 服務器每30秒發送一次ping
    - 客戶端應回應pong（或任何消息）

    Args:
        websocket: WebSocket連接
        task_id: 任務ID
        client_id: 客戶端ID（可選）
    """
    logger = get_logger("api.websocket")

    # 驗證任務是否存在
    task_info = optimization_task_service.get_task(task_id)
    if not task_info:
        await websocket.close(code=4004, reason=f"Task not found: {task_id}")
        logger.warning(f"WebSocket connection rejected: task not found {task_id}")
        return

    # 建立連接
    await websocket_manager.connect(websocket, task_id, client_id)

    # 註冊ProgressMonitor callback（將進度推送到WebSocket）
    def progress_notification_callback(event_type: str, data: dict):
        """
        ProgressMonitor callback -> WebSocket推送

        此函數會在OptunaOptimizer執行過程中被ProgressMonitor調用
        """
        asyncio.create_task(websocket_manager.broadcast_to_task(
            task_id,
            {
                'event': event_type,
                'data': data,
                'timestamp': datetime.now().isoformat()
            }
        ))

    optimization_task_service.register_notification_callback(task_id, progress_notification_callback)

    try:
        # 心跳任務
        heartbeat_task = asyncio.create_task(_send_heartbeat(websocket))

        # 接收客戶端消息（主要用於保持連接活躍）
        while True:
            try:
                # 等待客戶端消息（timeout 60秒）
                message = await asyncio.wait_for(websocket.receive_text(), timeout=60.0)

                # 處理客戶端消息（目前僅記錄，可擴展為命令處理）
                try:
                    data = json.loads(message)
                    if data.get('type') == 'pong':
                        # 心跳回應
                        pass
                    else:
                        logger.debug(f"Received client message: {data}")
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON from client: {message}")

            except asyncio.TimeoutError:
                # 60秒內沒有收到消息，檢查連接狀態
                if websocket.client_state != WebSocketState.CONNECTED:
                    logger.info(f"WebSocket disconnected (timeout): {task_id}")
                    break

    except WebSocketDisconnect:
        logger.info(f"Client disconnected: task_id={task_id}")

    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)

    finally:
        # 清理
        heartbeat_task.cancel()
        await websocket_manager.disconnect(websocket)
        optimization_task_service.unregister_notification_callback(task_id)


async def _send_heartbeat(websocket: WebSocket, interval: int = 30):
    """
    發送心跳包（保持連接活躍）

    Args:
        websocket: WebSocket連接
        interval: 心跳間隔（秒）
    """
    try:
        while True:
            await asyncio.sleep(interval)

            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.send_json({
                    'event': 'ping',
                    'timestamp': datetime.now().isoformat()
                })
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger = get_logger("api.websocket")
        logger.error(f"Heartbeat error: {e}")
