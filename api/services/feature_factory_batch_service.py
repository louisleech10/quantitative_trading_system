"""Feature Factory batch generation service."""

from __future__ import annotations

import asyncio
import time
import uuid
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
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

            # 計算 feature_klines 的 cache_dir，確保子進程使用相同路徑
            try:
                from api.core.config import settings
                batch_cache_dir: Optional[str] = str(settings.data_cache_path / "feature_klines")
            except Exception:
                batch_cache_dir = None

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
                        batch_cache_dir,
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
        cache_dir: Optional[str] = None,
    ) -> str:
        """在子進程中執行單一標的特徵計算。"""
        from momentum.factories import create_feature_factory

        # 子進程無法存取父進程的 module-level 單例，必須重新計算 cache_dir
        if cache_dir is None:
            try:
                from api.core.config import settings
                cache_dir = str(settings.data_cache_path / "feature_klines")
            except Exception:
                pass  # 使用 create_feature_factory 預設值（data_cache/）

        factory = create_feature_factory(cache_dir=cache_dir)
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

    async def get_batch_quality_summary(self, batch_task_id: str) -> Optional[Dict[str, Any]]:
        """計算批次任務中所有成功標的的快速品質彙整（NaN/常數/警告，跳過 ADF）。"""
        task = self._tasks.get(batch_task_id)
        if not task:
            return None

        results: Dict[str, str] = dict(task.get("results", {}))
        if not results:
            return {
                "batch_task_id": batch_task_id,
                "summaries": [],
                "total_symbols": 0,
                "pass_count": 0,
                "watch_count": 0,
                "reject_count": 0,
                "computed_at": datetime.now().isoformat(),
            }

        loop = asyncio.get_running_loop()

        async def _compute_one(symbol: str, hdf5_path: str) -> Optional[Dict[str, Any]]:
            try:
                return await loop.run_in_executor(
                    None, self._compute_symbol_quality, symbol, hdf5_path
                )
            except Exception as exc:
                logger.warning("Quality check failed for %s: %s", symbol, exc)
                return None

        raw = await asyncio.gather(*[_compute_one(sym, path) for sym, path in results.items()])
        summaries = [r for r in raw if r is not None]

        grade_order = {"reject": 0, "watch": 1, "pass": 2}
        summaries.sort(key=lambda x: grade_order.get(x["grade"], 3))

        pass_count = sum(1 for s in summaries if s["grade"] == "pass")
        watch_count = sum(1 for s in summaries if s["grade"] == "watch")
        reject_count = sum(1 for s in summaries if s["grade"] == "reject")

        return {
            "batch_task_id": batch_task_id,
            "summaries": summaries,
            "total_symbols": len(summaries),
            "pass_count": pass_count,
            "watch_count": watch_count,
            "reject_count": reject_count,
            "computed_at": datetime.now().isoformat(),
        }

    @staticmethod
    def _compute_symbol_quality(symbol: str, hdf5_path: str) -> Optional[Dict[str, Any]]:
        """在 thread executor 中直接讀取 HDF5 計算品質指標（向量化，不含 ADF）。"""
        import h5py
        import numpy as np
        from pathlib import Path

        file_path = Path(hdf5_path)
        if not file_path.exists():
            return None

        with h5py.File(file_path, "r") as h5f:
            top_keys = list(h5f.keys())
            if not top_keys:
                return None
            sym_key = top_keys[0]
            tf_keys = list(h5f[sym_key].keys())
            if not tf_keys:
                return None
            tf_key = tf_keys[0]
            group = h5f[f"{sym_key}/{tf_key}"]
            if "features" not in group:
                return None
            features = group["features"][:]  # shape: (bars, feature_count)

        bar_count = int(features.shape[0])
        feature_count = int(features.shape[1])

        nan_ratios = np.isnan(features).mean(axis=0)  # per-feature NaN ratio
        nan_ratio_mean = float(nan_ratios.mean())
        nan_ratio_max = float(nan_ratios.max())

        stds = np.nanstd(features, axis=0)
        constant_feature_count = int((stds == 0).sum())
        alert_count = int((nan_ratios > 0.1).sum())

        # 量化業界標準評級
        if nan_ratio_mean > 0.3 or constant_feature_count > 0 or bar_count < 200:
            grade = "reject"
        elif nan_ratio_mean > 0.1 or alert_count > 5 or bar_count < 500:
            grade = "watch"
        else:
            grade = "pass"

        return {
            "symbol": symbol,
            "bar_count": bar_count,
            "feature_count": feature_count,
            "nan_ratio_mean": round(nan_ratio_mean, 6),
            "nan_ratio_max": round(nan_ratio_max, 6),
            "constant_feature_count": constant_feature_count,
            "alert_count": alert_count,
            "grade": grade,
        }

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
