"""Feature Factory batch generation service."""

from __future__ import annotations

import asyncio
import time
import uuid
from concurrent.futures import ProcessPoolExecutor
from typing import Any, Callable, Dict, List, Optional

from api.core.logging import get_logger
from api.models.feature_factory_models import BatchGenerateRequest


logger = get_logger("api.feature_factory_batch_service")


class FeatureFactoryBatchService:
    """Batch service for multi-symbol feature generation."""

    def __init__(self):
        self._tasks: Dict[str, Dict[str, Any]] = {}
        self._notification_callbacks: Dict[str, List[Callable[[Dict[str, Any]], None]]] = {}
        self._running_batch_count: int = 0
        self._max_concurrent_batches: int = 2
        self._task_ttl_seconds: int = 3600
        self._lock = asyncio.Lock()

    async def start_batch(self, request: BatchGenerateRequest) -> str:
        """啟動批次任務，回傳 task_id。"""
        self._cleanup_expired_tasks()

        async with self._lock:
            if self._running_batch_count >= self._max_concurrent_batches:
                raise ValueError(
                    f"已有 {self._running_batch_count} 個批次任務執行中，"
                    f"上限為 {self._max_concurrent_batches}。請等待現有任務完成。"
                )

            task_id = str(uuid.uuid4())
            self._running_batch_count += 1
            self._tasks[task_id] = {
                "task_id": task_id,
                "status": "pending",
                "total": len(request.symbols),
                "completed": 0,
                "failed": 0,
                "progress": 0.0,
                "current_symbol": None,
                "results": {},
                "errors": {},
                "created_at": time.time(),
            }

        asyncio.create_task(self._run_batch(task_id, request))
        logger.info(
            "Feature Factory batch task created: task_id=%s symbols=%d timeframe=%s workers=%d",
            task_id,
            len(request.symbols),
            request.timeframe,
            request.max_workers,
        )
        return task_id

    async def _run_batch(self, task_id: str, request: BatchGenerateRequest) -> None:
        """在 ProcessPoolExecutor 中並行執行。"""
        try:
            task = self._tasks.get(task_id)
            if not task:
                return

            task["status"] = "running"
            self._notify_progress(task_id)

            loop = asyncio.get_running_loop()
            with ProcessPoolExecutor(max_workers=request.max_workers) as executor:
                async def _wait_one(symbol: str, future: asyncio.Future):
                    try:
                        result = await future
                        return symbol, result, None
                    except Exception as exc:  # pragma: no cover - branch verified by callers
                        return symbol, None, exc

                wrapped_futures = []
                for symbol in request.symbols:
                    future = loop.run_in_executor(
                        executor,
                        self._compute_single,
                        symbol,
                        request.timeframe,
                        request.config_override,
                        request.force_regenerate,
                    )
                    wrapped_futures.append(_wait_one(symbol, future))

                for wrapped_future in asyncio.as_completed(wrapped_futures):
                    symbol, hdf5_path, error = await wrapped_future
                    task["current_symbol"] = symbol

                    if error is None:
                        task["completed"] += 1
                        task["results"][symbol] = hdf5_path
                    else:
                        task["failed"] += 1
                        task["errors"][symbol] = str(error)
                        logger.error(
                            "Batch task %s failed for %s: %s",
                            task_id,
                            symbol,
                            error,
                            exc_info=True,
                        )

                    done = task["completed"] + task["failed"]
                    task["progress"] = done / max(task["total"], 1)
                    self._notify_progress(task_id)

            total = task["total"]
            failed = task["failed"]
            if failed == 0:
                task["status"] = "completed"
            elif failed < total:
                task["status"] = "partial"
            else:
                task["status"] = "failed"

            task["progress"] = 1.0
            task["completed_at"] = time.time()
            self._notify_progress(task_id)

        except Exception as exc:
            logger.error("Batch task %s crashed: %s", task_id, exc, exc_info=True)
            task = self._tasks.get(task_id)
            if task:
                task["status"] = "failed"
                task["progress"] = 1.0
                task["errors"]["__batch__"] = str(exc)
                task["completed_at"] = time.time()
                self._notify_progress(task_id)
        finally:
            async with self._lock:
                self._running_batch_count = max(self._running_batch_count - 1, 0)

    @staticmethod
    def _compute_single(
        symbol: str,
        timeframe: str,
        config_override: Optional[Dict[str, Any]],
        force_regenerate: bool,
    ) -> str:
        """在子進程中執行單一標的特徵計算。"""
        from momentum.factories import create_feature_factory

        factory = create_feature_factory()
        try:
            result = factory.generate_features(
                symbol=symbol,
                timeframe=timeframe,
                config_override=config_override,
                force_regenerate=force_regenerate,
            )
            return result.hdf5_path or ""
        except FileNotFoundError as exc:
            raise RuntimeError(f"{symbol} ({timeframe}): 資料檔不存在 - {exc}") from exc
        except Exception as exc:
            raise RuntimeError(f"{symbol} ({timeframe}): 計算失敗 - {exc}") from exc

    def register_notification_callback(
        self,
        task_id: str,
        callback: Callable[[Dict[str, Any]], None],
    ) -> None:
        """註冊批次任務通知 callback。"""
        self._notification_callbacks.setdefault(task_id, []).append(callback)

    def unregister_notification_callback(
        self,
        task_id: str,
        callback: Callable[[Dict[str, Any]], None],
    ) -> None:
        """移除批次任務通知 callback。"""
        callbacks = self._notification_callbacks.get(task_id, [])
        if callback in callbacks:
            callbacks.remove(callback)
        if not callbacks and task_id in self._notification_callbacks:
            del self._notification_callbacks[task_id]

    def _notify_progress(self, task_id: str) -> None:
        """通知訂閱者批次進度。"""
        status = self.get_status(task_id)
        if not status:
            return
        callbacks = list(self._notification_callbacks.get(task_id, []))
        for callback in callbacks:
            try:
                callback(status)
            except Exception as exc:
                logger.error("Batch notification callback failed: %s", exc, exc_info=True)

    def _cleanup_expired_tasks(self) -> None:
        """清理過期 task，避免記憶體洩漏。"""
        now = time.time()
        expired_task_ids = [
            task_id
            for task_id, task in self._tasks.items()
            if task.get("completed_at") and (now - task["completed_at"]) > self._task_ttl_seconds
        ]
        for task_id in expired_task_ids:
            self._tasks.pop(task_id, None)
            self._notification_callbacks.pop(task_id, None)

    def get_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """取得任務狀態。"""
        self._cleanup_expired_tasks()
        task = self._tasks.get(task_id)
        if not task:
            return None

        done = task["completed"] + task["failed"]
        progress = done / max(task["total"], 1)

        return {
            "task_id": task["task_id"],
            "status": task["status"],
            "total": task["total"],
            "completed": task["completed"],
            "failed": task["failed"],
            "current_symbol": task.get("current_symbol"),
            "progress": progress,
            "results": dict(task["results"]),
            "errors": dict(task["errors"]),
        }


_feature_factory_batch_service: Optional[FeatureFactoryBatchService] = None


def set_feature_factory_batch_service(service: FeatureFactoryBatchService) -> None:
    """設定全域 batch service 單例。"""
    global _feature_factory_batch_service
    _feature_factory_batch_service = service


def get_feature_factory_batch_service() -> FeatureFactoryBatchService:
    """取得全域 batch service 單例。"""
    global _feature_factory_batch_service
    if _feature_factory_batch_service is None:
        _feature_factory_batch_service = FeatureFactoryBatchService()
    return _feature_factory_batch_service
