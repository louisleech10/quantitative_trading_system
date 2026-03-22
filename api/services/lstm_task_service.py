"""
lstm_task_service.py
====================

LSTM / Transformer 非同步訓練任務服務。

接口設計對齊 XGBoostTaskService，支援：
- POST /api/v1/lstm/train    → 啟動非同步訓練任務
- GET  /api/v1/lstm/task/{id} → 查詢任務狀態與結果
- POST /api/v1/lstm/predict  → 用已訓練模型推理（回傳機率）
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from api.core.logging import get_logger
from api.utils.json_serializer import sanitize_for_json

logger = get_logger(__name__)


# ─────────────────────────────────────────────
# 任務狀態資料結構
# ─────────────────────────────────────────────

@dataclass
class LSTMTaskStatus:
    task_id: str
    status: str                       # "pending" | "running" | "completed" | "failed"
    progress: int = 0                 # 0~100
    current_epoch: int = 0
    total_epochs: int = 0
    message: str = ""
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: Optional[str] = None
    # 訓練結果（完成後填入）
    train_loss_history: List[float] = field(default_factory=list)
    val_loss_history: List[float] = field(default_factory=list)
    best_val_loss: float = float("inf")
    best_epoch: int = 0
    val_auc: float = 0.0
    n_train_samples: int = 0
    n_val_samples: int = 0
    # 錯誤訊息
    error: Optional[str] = None


# ─────────────────────────────────────────────
# 主服務
# ─────────────────────────────────────────────

class LSTMTaskService:
    """
    LSTM 訓練任務的非同步服務層。

    職責：
    - 管理任務生命週期（建立 → 訓練 → 完成|失敗）
    - 提供進度查詢接口（供前端 polling 或 WebSocket 使用）
    - 持有已訓練模型引用，供 predict 接口使用
    - 不直接實例化 LSTMEngine（透過 factory 注入，遵循 Rule 3）

    Note:
        模型以 task_id 為 key 暫存在記憶體中（_model_cache）。
        生產環境應改為 save/load .pt 到 data_cache/models/。
    """

    def __init__(self) -> None:
        self._tasks: Dict[str, LSTMTaskStatus] = {}
        self._model_cache: Dict[str, Any] = {}   # task_id → LSTMEngine instance

    # ── 公開 API 方法 ─────────────────────────

    async def start_training(
        self,
        X: np.ndarray,
        y: np.ndarray,
        config_dict: Optional[Dict] = None,
        val_ratio: float = 0.2,
    ) -> str:
        """
        啟動非同步訓練任務。

        Args:
            X: 特徵張量（2D 或 3D numpy array）
            y: 標籤陣列（二元 0/1）
            config_dict: SequenceModelConfig 的 dict 形式（可選）
            val_ratio: 驗證集比例

        Returns:
            task_id (str)
        """
        task_id = str(uuid.uuid4())
        status = LSTMTaskStatus(
            task_id=task_id,
            status="pending",
            message="任務已建立，等待執行...",
        )
        self._tasks[task_id] = status

        asyncio.create_task(
            self._run_training(task_id, X, y, config_dict, val_ratio)
        )
        logger.info(f"LSTM 訓練任務已建立：task_id={task_id}")
        return task_id

    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """
        查詢任務狀態，回傳可序列化的 dict。
        前端 polling 接口：GET /api/v1/lstm/task/{task_id}
        """
        status = self._tasks.get(task_id)
        if status is None:
            return None

        return sanitize_for_json({
            "task_id": status.task_id,
            "status": status.status,
            "progress": status.progress,
            "current_epoch": status.current_epoch,
            "total_epochs": status.total_epochs,
            "message": status.message,
            "created_at": status.created_at,
            "completed_at": status.completed_at,
            "train_loss_history": status.train_loss_history,
            "val_loss_history": status.val_loss_history,
            "best_val_loss": status.best_val_loss,
            "best_epoch": status.best_epoch,
            "val_auc": status.val_auc,
            "n_train_samples": status.n_train_samples,
            "n_val_samples": status.n_val_samples,
            "error": status.error,
        })

    def predict(self, task_id: str, X: np.ndarray) -> np.ndarray:
        """
        使用已訓練的模型推理，回傳機率陣列。
        接口與 XGBoostAnalyzer.predict_proba 一致。

        Args:
            task_id: 對應已完成的訓練任務 ID
            X: 輸入特徵（2D 或 3D numpy array）

        Returns:
            np.ndarray, shape (n_windows,), 值域 [0, 1]

        Raises:
            ValueError: 任務不存在或尚未完成
        """
        engine = self._model_cache.get(task_id)
        if engine is None:
            status = self._tasks.get(task_id)
            if status is None:
                raise ValueError(f"任務 {task_id} 不存在")
            if status.status != "completed":
                raise ValueError(f"任務 {task_id} 尚未完成（目前狀態：{status.status}）")
            raise ValueError(f"任務 {task_id} 的模型已被釋放")

        return engine.predict_proba(X)

    def list_tasks(self) -> List[Dict]:
        """回傳所有任務的摘要列表（最新在前）"""
        tasks = sorted(
            self._tasks.values(),
            key=lambda s: s.created_at,
            reverse=True,
        )
        return [
            {
                "task_id": s.task_id,
                "status": s.status,
                "progress": s.progress,
                "val_auc": s.val_auc,
                "created_at": s.created_at,
                "completed_at": s.completed_at,
            }
            for s in tasks
        ]

    # ── 私有：背景訓練協程 ─────────────────────

    async def _run_training(
        self,
        task_id: str,
        X: np.ndarray,
        y: np.ndarray,
        config_dict: Optional[Dict],
        val_ratio: float,
    ) -> None:
        """背景執行 LSTM 訓練（在 thread pool 執行，不阻塞 event loop）"""
        status = self._tasks[task_id]
        status.status = "running"
        status.message = "正在初始化模型..."

        try:
            # Lazy import：避免 torch 影響系統啟動時間
            from momentum.Analysis.lstm_engine import LSTMEngine, SequenceModelConfig  # noqa: PLC0415

            # 建立設定
            cfg_kwargs = config_dict or {}
            config = SequenceModelConfig(**{
                k: v for k, v in cfg_kwargs.items()
                if k in SequenceModelConfig.__dataclass_fields__
            })

            status.total_epochs = config.epochs
            status.message = f"開始訓練（{config.epochs} epochs）..."

            engine = LSTMEngine(config=config)

            # 在 thread pool 執行 CPU/GPU 密集訓練，帶進度回調
            result = await asyncio.to_thread(
                self._train_with_progress, engine, X, y, val_ratio, task_id
            )

            # 填入結果
            status.train_loss_history = result.train_loss_history
            status.val_loss_history = result.val_loss_history
            status.best_val_loss = result.best_val_loss
            status.best_epoch = result.best_epoch
            status.val_auc = result.val_auc
            status.n_train_samples = result.n_train_samples
            status.n_val_samples = result.n_val_samples
            status.progress = 100
            status.current_epoch = config.epochs
            status.status = "completed"
            status.completed_at = datetime.utcnow().isoformat()
            status.message = (
                f"訓練完成。best_epoch={result.best_epoch}, "
                f"val_auc={result.val_auc:.4f}"
            )

            self._model_cache[task_id] = engine
            logger.info(f"LSTM 任務完成：task_id={task_id}, val_auc={result.val_auc:.4f}")

        except Exception as exc:
            status.status = "failed"
            status.error = str(exc)
            status.message = f"訓練失敗：{exc}"
            status.completed_at = datetime.utcnow().isoformat()
            logger.error(f"LSTM 任務失敗：task_id={task_id}", exc_info=True)

    def _train_with_progress(
        self,
        engine,
        X: np.ndarray,
        y: np.ndarray,
        val_ratio: float,
        task_id: str,
    ):
        """
        同步訓練包裝（在 thread pool 執行）。
        透過修改 status 物件回報進度（event loop safe：只寫基本型態）。
        """
        status = self._tasks[task_id]
        original_epochs = engine.config.epochs

        # 逐 epoch 訓練並更新進度（將 epochs 拆為多個小批次）
        # 骨幹版：直接呼叫 train_model；
        # 未來優化：可改為 epoch-by-epoch callback 機制
        result = engine.train_model(X, y, val_ratio=val_ratio)

        # 訓練結束後同步進度欄位（實際 epoch 更新在 LSTMEngine 內部 logger）
        status.current_epoch = original_epochs
        status.progress = 100
        return result
