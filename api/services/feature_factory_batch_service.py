"""Feature Factory batch generation service."""

from __future__ import annotations

import asyncio
import gc
import hashlib
import json
import time
import uuid
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from enum import Enum
from pathlib import Path
import threading
from typing import Any, Callable, Dict, List, Optional, Tuple

import psutil
from fastapi import HTTPException

from api.core.logging import get_logger
from api.models.feature_factory_models import BatchGenerateRequest
from momentum.FeatureEngineering.utils.hardware_utils import (
    get_current_tier_gb,
    get_tier_concurrent_symbols,
)
from momentum.core.config import (
    MomentumConfig,
    batch_nested_environment,
    get_batch_nested_enabled,
)


logger = get_logger("api.feature_factory_batch_service")

BYTES_PER_GB = 1024 ** 3
BYTES_PER_MB = 1024 ** 2
RAM_GATE_MIN_AVAILABLE_GB = 4.0
RSS_CUMULATIVE_WINDOW = 20
RSS_CUMULATIVE_LIMIT_MB = 1536


class BatchBusyError(ValueError):
    """Raised when another heavy Feature Factory batch is already running."""

    def __init__(self, message: str, retry_after_seconds: int = 30) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


class BatchFailureType(str, Enum):
    """Failure classes for resumable Feature Factory batch items."""

    OOM = "oom"
    RAM_GATE = "ram_gate"
    COMPUTE_ERROR = "compute_error"


class FeatureFactoryBatchService:
    """Batch service for multi-symbol feature generation."""

    _heavy_batch_lock = asyncio.Lock()
    _heavy_batch_reserved = False
    _class_state_lock = threading.Lock()

    def __init__(self, checkpoint_dir: Optional[Path] = None) -> None:
        self._tasks: Dict[str, Dict[str, Any]] = {}
        self._notification_callbacks: Dict[str, List[Callable[[Dict[str, Any]], None]]] = {}
        self._running_batch_count: int = 0
        self._max_concurrent_batches: int = 1
        self._task_ttl_seconds: int = 3600
        self._lock = asyncio.Lock()
        default_checkpoint_dir = (
            MomentumConfig.from_project_root().data_cache_path / "feature_preprocessing"
        )
        self._checkpoint_dir = Path(checkpoint_dir or default_checkpoint_dir)
        self._checkpoint_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    async def _reserve_heavy_batch_slot(cls) -> bool:
        """Reserve the process-wide heavy batch slot without waiting in a queue."""

        with cls._class_state_lock:
            if cls._heavy_batch_reserved or cls._heavy_batch_lock.locked():
                return False
            cls._heavy_batch_reserved = True

        try:
            await cls._heavy_batch_lock.acquire()
        except BaseException:
            with cls._class_state_lock:
                cls._heavy_batch_reserved = False
            raise
        return True

    @classmethod
    def _release_heavy_batch_slot(cls) -> None:
        """Release the process-wide heavy batch slot."""

        with cls._class_state_lock:
            cls._heavy_batch_reserved = False
            if cls._heavy_batch_lock.locked():
                cls._heavy_batch_lock.release()

    async def start_batch(self, request: BatchGenerateRequest) -> str:
        """啟動批次任務，回傳 task_id。"""
        self._cleanup_expired_tasks()
        self._ram_gate()

        if not await self._reserve_heavy_batch_slot():
            raise BatchBusyError(
                "已有 Feature Factory heavy batch 任務執行中，請稍後重試。",
                retry_after_seconds=30,
            )

        try:
            async with self._lock:
                if self._running_batch_count >= self._max_concurrent_batches:
                    raise BatchBusyError(
                        f"已有 {self._running_batch_count} 個批次任務執行中，"
                        f"上限為 {self._max_concurrent_batches}。請等待現有任務完成。",
                        retry_after_seconds=30,
                    )

                task_id = str(uuid.uuid4())
                checkpoint = self._build_initial_checkpoint(task_id, request)
                self._safe_persist_checkpoint(checkpoint)
                self._running_batch_count += 1
                self._tasks[task_id] = self._build_task_state(
                    task_id,
                    request,
                    checkpoint,
                    status="pending",
                )
        except Exception:
            self._release_heavy_batch_slot()
            raise

        asyncio.create_task(self._run_batch(task_id, request, checkpoint, lock_reserved=True))
        logger.info(
            "[L6.5] Feature Factory batch task created: task_id=%s symbols=%d timeframe=%s",
            task_id,
            len(request.symbols),
            request.timeframe,
        )
        return task_id

    async def resume_batch(self, batch_id: str) -> Dict[str, Any]:
        """Start a resumable batch from an existing checkpoint."""

        checkpoint = self._load_checkpoint(batch_id)
        if checkpoint is None:
            raise FileNotFoundError(f"batch checkpoint not found: {batch_id}")

        skipped_items = len(checkpoint.get("completed_items", []))
        queued_items = len(checkpoint.get("queued_items", []))
        resumed_from = str(checkpoint.get("last_updated_at") or checkpoint.get("started_at") or "")

        if queued_items == 0:
            self._tasks[batch_id] = self._build_task_state_from_checkpoint(
                checkpoint,
                status="completed",
            )
            return {
                "batch_id": batch_id,
                "resumed_from": resumed_from,
                "skipped_items": skipped_items,
                "queued_items": queued_items,
                "status": "completed",
            }

        self._ram_gate()
        if not await self._reserve_heavy_batch_slot():
            raise BatchBusyError(
                "已有 Feature Factory heavy batch 任務執行中，請稍後重試。",
                retry_after_seconds=30,
            )

        try:
            self._tasks[batch_id] = self._build_task_state_from_checkpoint(
                checkpoint,
                status="pending",
            )
            async with self._lock:
                self._running_batch_count += 1
        except Exception:
            self._release_heavy_batch_slot()
            raise

        asyncio.create_task(self.execute_resume(checkpoint, lock_reserved=True))
        return {
            "batch_id": batch_id,
            "resumed_from": resumed_from,
            "skipped_items": skipped_items,
            "queued_items": queued_items,
            "status": "running",
        }

    async def execute_resume(
        self,
        checkpoint: Dict[str, Any],
        lock_reserved: bool = False,
    ) -> None:
        """Execute a resumed batch from checkpoint state."""

        request_payload = checkpoint.get("request_payload") or {}
        request = BatchGenerateRequest(**request_payload)
        if not lock_reserved:
            self._ram_gate()
            if not await self._reserve_heavy_batch_slot():
                raise BatchBusyError(
                    "已有 Feature Factory heavy batch 任務執行中，請稍後重試。",
                    retry_after_seconds=30,
                )
            async with self._lock:
                self._running_batch_count += 1
            self._tasks[checkpoint["batch_id"]] = self._build_task_state_from_checkpoint(
                checkpoint,
                status="pending",
            )

        await self._run_batch(
            str(checkpoint["batch_id"]),
            request,
            checkpoint,
            lock_reserved=True,
        )

    async def _run_batch(
        self,
        task_id: str,
        request: BatchGenerateRequest,
        checkpoint: Dict[str, Any],
        lock_reserved: bool = False,
    ) -> None:
        """Run a batch with RAM gate, checkpointing, and tier-aware symbol waves."""
        try:
            task = self._tasks.get(task_id)
            if not task:
                return

            task["status"] = "running"
            task["started_at"] = task.get("started_at") or time.time()
            concurrent_symbols = self._resolve_concurrent_symbols()
            task["concurrent_symbols"] = concurrent_symbols
            checkpoint["concurrent_symbols"] = concurrent_symbols
            checkpoint["last_updated_at"] = datetime.now().isoformat()
            self._safe_persist_checkpoint(checkpoint)
            self._notify_progress(task_id)

            # 計算 feature_klines 的 cache_dir，確保子進程使用相同路徑
            try:
                from api.core.config import settings
                batch_cache_dir: Optional[str] = str(settings.data_cache_path / "feature_klines")
            except Exception:
                batch_cache_dir = None

            while checkpoint.get("queued_items"):
                try:
                    self._ram_gate()
                except HTTPException as exc:
                    task["status"] = "paused_ram_gate"
                    task["errors"]["__ram_gate__"] = str(exc.detail)
                    checkpoint["last_error"] = {
                        "reason": str(exc.detail),
                        "failure_type": BatchFailureType.RAM_GATE.value,
                        "timestamp": datetime.now().isoformat(),
                    }
                    checkpoint["last_updated_at"] = datetime.now().isoformat()
                    self._safe_persist_checkpoint(checkpoint)
                    self._notify_progress(task_id)
                    return

                queued_items = list(checkpoint.get("queued_items", []))
                item_wave = queued_items[: max(1, concurrent_symbols)]
                if not item_wave:
                    break

                oom_seen = await self._process_item_wave(
                    task,
                    checkpoint,
                    item_wave,
                    request,
                    batch_cache_dir,
                )
                if oom_seen or task.get("memory_sanity_failed"):
                    concurrent_symbols = 1
                    task["concurrent_symbols"] = 1
                    checkpoint["concurrent_symbols"] = 1

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
            checkpoint["last_updated_at"] = datetime.now().isoformat()
            checkpoint["status"] = task["status"]
            self._safe_persist_checkpoint(checkpoint)
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
            if lock_reserved:
                self._release_heavy_batch_slot()
            async with self._lock:
                self._running_batch_count = max(self._running_batch_count - 1, 0)

    async def _process_item_wave(
        self,
        task: Dict[str, Any],
        checkpoint: Dict[str, Any],
        item_wave: List[Dict[str, str]],
        request: BatchGenerateRequest,
        batch_cache_dir: Optional[str],
    ) -> bool:
        """Process one tier-sized wave of symbol/timeframe items."""

        loop = asyncio.get_running_loop()
        task_id = str(task["task_id"])
        rss_before_by_item: Dict[Tuple[str, str], int] = {}

        for item in item_wave:
            symbol = str(item["symbol"])
            timeframe = str(item["timeframe"])
            rss_before_by_item[(symbol, timeframe)] = self._rss_mb()

        async def _wait_one(
            item: Dict[str, str],
            future: asyncio.Future,
        ) -> Tuple[Dict[str, str], Optional[str], Optional[BaseException]]:
            try:
                result = await future
                return item, result, None
            except Exception as exc:  # pragma: no cover - exercised through callers
                return item, None, exc

        wrapped_futures = []
        with batch_nested_environment(True):
            with ProcessPoolExecutor(max_workers=max(1, len(item_wave))) as executor:
                for item in item_wave:
                    future = loop.run_in_executor(
                        executor,
                        self._compute_single,
                        str(item["symbol"]),
                        str(item["timeframe"]),
                        request.config_override,
                        request.force_regenerate,
                        batch_cache_dir,
                    )
                    wrapped_futures.append(_wait_one(item, future))

                oom_seen = False
                for wrapped_future in asyncio.as_completed(wrapped_futures):
                    item, hdf5_path, error = await wrapped_future
                    symbol = str(item["symbol"])
                    timeframe = str(item["timeframe"])
                    rss_before = rss_before_by_item[(symbol, timeframe)]
                    rss_peak = max(rss_before, self._rss_mb())
                    gc.collect()
                    rss_after = self._rss_mb()
                    failure_type = self._classify_failure(error) if error else None
                    oom_seen = oom_seen or failure_type == BatchFailureType.OOM

                    self._record_item_result(
                        task,
                        checkpoint,
                        symbol,
                        timeframe,
                        hdf5_path or "",
                        error,
                        failure_type,
                        rss_before,
                        rss_peak,
                        rss_after,
                    )
                    self._notify_progress(task_id)
        return oom_seen

    def _record_item_result(
        self,
        task: Dict[str, Any],
        checkpoint: Dict[str, Any],
        symbol: str,
        timeframe: str,
        hdf5_path: str,
        error: Optional[BaseException],
        failure_type: Optional[BatchFailureType],
        rss_before_mb: int,
        rss_peak_mb: int,
        rss_after_gc_mb: int,
    ) -> None:
        """Record one completed or failed item in memory and checkpoint state."""

        task["current_symbol"] = symbol
        task["current_timeframe"] = timeframe
        output_paths = [hdf5_path] if hdf5_path else []
        metrics = {
            "current_symbol": symbol,
            "current_timeframe": timeframe,
            "rss_before_item_mb": rss_before_mb,
            "rss_peak_item_mb": rss_peak_mb,
            "rss_after_gc_mb": rss_after_gc_mb,
        }
        task["last_item_metrics"] = metrics

        self._remove_queued_item(checkpoint, symbol, timeframe)

        if error is None:
            task["completed"] += 1
            task["results"][symbol] = hdf5_path
            checkpoint.setdefault("completed_items", []).append({
                "symbol": symbol,
                "timeframe": timeframe,
                "output_paths": output_paths,
                "rss_peak_item_mb": rss_peak_mb,
                "rss_after_gc_mb": rss_after_gc_mb,
            })
        else:
            task["failed"] += 1
            task["errors"][symbol] = str(error)
            resolved_failure_type = failure_type or BatchFailureType.COMPUTE_ERROR
            checkpoint.setdefault("failed_items", []).append({
                "symbol": symbol,
                "timeframe": timeframe,
                "reason": str(error),
                "failure_type": resolved_failure_type.value,
            })
            logger.error(
                "[L6.5] Batch task %s failed for %s %s: %s",
                task["task_id"],
                symbol,
                timeframe,
                error,
                exc_info=(type(error), error, error.__traceback__),
            )

        memory_failed = self._memory_sanity_failed(
            checkpoint,
            rss_before_mb,
            rss_peak_mb,
            rss_after_gc_mb,
        )
        task["memory_sanity_failed"] = bool(task.get("memory_sanity_failed") or memory_failed)
        checkpoint["memory_sanity_failed"] = task["memory_sanity_failed"]
        if memory_failed:
            checkpoint["last_memory_sanity_failure"] = dict(metrics)
            logger.warning(
                "[L6.5] Batch memory sanity failed task_id=%s symbol=%s timeframe=%s before=%s peak=%s after_gc=%s",
                task["task_id"],
                symbol,
                timeframe,
                rss_before_mb,
                rss_peak_mb,
                rss_after_gc_mb,
            )

        done = task["completed"] + task["failed"]
        task["progress"] = done / max(task["total"], 1)
        checkpoint["last_updated_at"] = datetime.now().isoformat()
        self._safe_persist_checkpoint(checkpoint)

    def _resolve_concurrent_symbols(self) -> int:
        """Resolve concurrent symbol count from tier table and nested guard."""

        tier_gb = get_current_tier_gb()
        concurrent_symbols = max(1, get_tier_concurrent_symbols(tier_gb))
        if get_batch_nested_enabled():
            logger.warning(
                "[L6.5] FFACT_BATCH_NESTED detected; forcing concurrent_symbols=1"
            )
            return 1
        return concurrent_symbols

    def _ram_gate(self, min_available_gb: float = RAM_GATE_MIN_AVAILABLE_GB) -> None:
        """Reject new heavy work when available RAM is below the safety gate."""

        available_bytes = psutil.virtual_memory().available
        min_available_bytes = int(min_available_gb * BYTES_PER_GB)
        if available_bytes < min_available_bytes:
            available_gb = available_bytes / BYTES_PER_GB
            raise HTTPException(
                status_code=429,
                detail=(
                    f"RAM gate: available={available_gb:.2f}GB below "
                    f"required={min_available_gb:.2f}GB"
                ),
            )

    def _checkpoint_path(self, batch_id: str) -> Path:
        """Return checkpoint path for a batch id."""

        safe_batch_id = "".join(ch for ch in batch_id if ch.isalnum() or ch in {"-", "_"})
        return self._checkpoint_dir / f"batch_state_{safe_batch_id}.json"

    def _build_initial_checkpoint(
        self,
        task_id: str,
        request: BatchGenerateRequest,
    ) -> Dict[str, Any]:
        """Build the initial checkpoint payload for a batch request."""

        request_payload = request.model_dump()
        now = datetime.now().isoformat()
        queued_items = [
            {"symbol": symbol, "timeframe": request.timeframe}
            for symbol in request.symbols
        ]
        return {
            "schema_version": 1,
            "batch_id": task_id,
            "request_hash": self._hash_payload(request_payload),
            "config_hash": self._hash_payload(request.config_override or {}),
            "request_payload": request_payload,
            "started_at": now,
            "last_updated_at": now,
            "completed_items": [],
            "failed_items": [],
            "queued_items": queued_items,
            "concurrent_symbols": self._resolve_concurrent_symbols(),
            "memory_sanity_failed": False,
            "rss_after_gc_history_mb": [],
        }

    def _build_task_state(
        self,
        task_id: str,
        request: BatchGenerateRequest,
        checkpoint: Dict[str, Any],
        status: str,
    ) -> Dict[str, Any]:
        """Build an in-memory task state from request and checkpoint."""

        return {
            "task_id": task_id,
            "status": status,
            "total": len(request.symbols),
            "completed": len(checkpoint.get("completed_items", [])),
            "failed": len(checkpoint.get("failed_items", [])),
            "progress": 0.0,
            "current_symbol": None,
            "current_timeframe": None,
            "results": self._results_from_completed(checkpoint.get("completed_items", [])),
            "errors": self._errors_from_failed(checkpoint.get("failed_items", [])),
            "created_at": time.time(),
            "concurrent_symbols": checkpoint.get("concurrent_symbols", 1),
            "memory_sanity_failed": bool(checkpoint.get("memory_sanity_failed", False)),
            "last_item_metrics": None,
        }

    def _build_task_state_from_checkpoint(
        self,
        checkpoint: Dict[str, Any],
        status: str,
    ) -> Dict[str, Any]:
        """Build in-memory task state from checkpoint for resume."""

        request_payload = checkpoint.get("request_payload") or {}
        request = BatchGenerateRequest(**request_payload)
        state = self._build_task_state(str(checkpoint["batch_id"]), request, checkpoint, status)
        done = state["completed"] + state["failed"]
        state["progress"] = done / max(state["total"], 1)
        return state

    @staticmethod
    def _hash_payload(payload: Any) -> str:
        """Return a stable short hash for request/config checkpoint metadata."""

        serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def _results_from_completed(completed_items: List[Dict[str, Any]]) -> Dict[str, str]:
        """Build legacy result map from checkpoint completed items."""

        results: Dict[str, str] = {}
        for item in completed_items:
            output_paths = item.get("output_paths") or []
            if output_paths:
                results[str(item.get("symbol", ""))] = str(output_paths[0])
        return results

    @staticmethod
    def _errors_from_failed(failed_items: List[Dict[str, Any]]) -> Dict[str, str]:
        """Build legacy error map from checkpoint failed items."""

        return {
            str(item.get("symbol", "")): str(item.get("reason", ""))
            for item in failed_items
        }

    def _load_checkpoint(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """Load a checkpoint if it exists."""

        path = self._checkpoint_path(batch_id)
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as file_obj:
            payload = json.load(file_obj)
        if not isinstance(payload, dict):
            raise ValueError(f"Invalid checkpoint payload: {path}")
        return payload

    def _safe_persist_checkpoint(self, checkpoint: Dict[str, Any]) -> None:
        """Persist checkpoint, logging write failures without aborting the batch."""

        try:
            self._write_checkpoint_atomic(checkpoint)
        except OSError as exc:
            logger.error(
                "[L6.5] Failed to write batch checkpoint batch_id=%s: %s",
                checkpoint.get("batch_id"),
                exc,
                exc_info=True,
            )
        except Exception as exc:
            logger.error(
                "[L6.5] Unexpected checkpoint write failure batch_id=%s: %s",
                checkpoint.get("batch_id"),
                exc,
                exc_info=True,
            )

    def _write_checkpoint_atomic(self, checkpoint: Dict[str, Any]) -> None:
        """Write a checkpoint JSON atomically with temp + rename."""

        path = self._checkpoint_path(str(checkpoint["batch_id"]))
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        with temp_path.open("w", encoding="utf-8") as file_obj:
            json.dump(checkpoint, file_obj, ensure_ascii=False, indent=2, sort_keys=True)
        temp_path.replace(path)

    @staticmethod
    def _remove_queued_item(checkpoint: Dict[str, Any], symbol: str, timeframe: str) -> None:
        """Remove a completed/failed item from queued checkpoint items."""

        checkpoint["queued_items"] = [
            item
            for item in checkpoint.get("queued_items", [])
            if not (item.get("symbol") == symbol and item.get("timeframe") == timeframe)
        ]

    @staticmethod
    def _classify_failure(error: Optional[BaseException]) -> BatchFailureType:
        """Classify item failure for checkpoint resume decisions."""

        if error is None:
            return BatchFailureType.COMPUTE_ERROR
        message = str(error).lower()
        oom_tokens = ("oom", "out of memory", "cannot allocate", "sigkill", "killed")
        if any(token in message for token in oom_tokens):
            return BatchFailureType.OOM
        return BatchFailureType.COMPUTE_ERROR

    @staticmethod
    def _rss_mb() -> int:
        """Return current parent process RSS in MB."""

        return int(psutil.Process().memory_info().rss // BYTES_PER_MB)

    @staticmethod
    def _memory_sanity_failed(
        checkpoint: Dict[str, Any],
        rss_before_mb: int,
        rss_peak_mb: int,
        rss_after_gc_mb: int,
    ) -> bool:
        """Evaluate Task 0.6 T0.P7 memory sanity heuristics."""

        single_item_limit = max(rss_before_mb + 1024, int(rss_peak_mb * 0.75))
        single_item_failed = rss_after_gc_mb > single_item_limit

        history = checkpoint.setdefault("rss_after_gc_history_mb", [])
        history.append(rss_after_gc_mb)
        cumulative_failed = False
        if len(history) >= RSS_CUMULATIVE_WINDOW:
            window = history[-RSS_CUMULATIVE_WINDOW:]
            monotonic = all(window[idx] <= window[idx + 1] for idx in range(len(window) - 1))
            cumulative_failed = monotonic and (window[-1] - window[0] > RSS_CUMULATIVE_LIMIT_MB)

        return bool(single_item_failed or cumulative_failed)

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
            "current_timeframe": task.get("current_timeframe"),
            "progress": progress,
            "queued": max(task["total"] - done, 0),
            "concurrent_symbols": task.get("concurrent_symbols", 1),
            "memory_sanity_failed": bool(task.get("memory_sanity_failed", False)),
            "last_item_metrics": task.get("last_item_metrics"),
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
