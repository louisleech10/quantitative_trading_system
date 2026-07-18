"""Model Task Service - 通用模型任務調度服務。"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from api.core.logging import get_logger
from momentum.factories import (
    create_feature_library,
    create_feature_storage,
    create_model_comparison,
    create_model_trainer,
)

logger = get_logger(__name__)


class ModelTaskService:
    """通用模型任務調度服務（LightGBM/XGBoost）。"""

    def __init__(self):
        self.logger = logger
        self.feature_storage = create_feature_storage()
        self.feature_library = create_feature_library()
        self.tasks: Dict[str, Dict[str, Any]] = {}

    async def start_training_task(
        self,
        engine: str,
        config: Optional[Dict[str, Any]],
        data_source: str,
        validation: Optional[Dict[str, Any]] = None,
        run_comparison: bool = False,
    ) -> str:
        task_id = str(uuid.uuid4())
        self.tasks[task_id] = {
            "task_id": task_id,
            "status": "running",
            "engine": engine,
            "created_at": datetime.now().isoformat(),
            "result": None,
            "error": None,
        }

        asyncio.create_task(
            self._run_task(
                task_id=task_id,
                engine=engine,
                config=config or {},
                data_source=data_source,
                validation=validation or {},
                run_comparison=run_comparison,
            )
        )
        return task_id

    async def _run_task(
        self,
        task_id: str,
        engine: str,
        config: Dict[str, Any],
        data_source: str,
        validation: Dict[str, Any],
        run_comparison: bool,
    ) -> None:
        try:
            trainer = create_model_trainer(engine=engine, config=config)
            X, y, feature_names = await self._load_data(data_source)

            training_kwargs = self._build_training_kwargs(validation)
            performance = await asyncio.to_thread(
                trainer.train_model,
                X,
                y,
                feature_names,
                **training_kwargs,
            )

            from momentum.Analysis.eval_scope_utils import (
                apply_service_matrix_scopes,
                build_service_oot_bundle,
                performance_to_scoped_dict,
            )
            import pickle

            # LA-2 B2 F3：動態 OOT SplitPlan + oot_receipt 寫入鏈
            try:
                model_obj = getattr(trainer, "model", None) or getattr(
                    getattr(trainer, "analyzer", None), "model", None
                )
                model_artifact = pickle.dumps(model_obj) if model_obj is not None else b"model-task"
            except Exception:  # noqa: BLE001
                model_artifact = b"model-task-artifact"
            oot_bundle = build_service_oot_bundle(
                n_samples=len(y),
                model_artifact=model_artifact,
                trusted_issuer="model_task_service",
                oot_ratio=0.2,
                horizon=1,
                embargo=0,
                base_universe_hash=f"model_task:{engine}:{len(y)}",
            )
            has_oot_held_out = bool(oot_bundle["has_oot_held_out"])
            result: Dict[str, Any] = {
                "engine": trainer.get_model_type(),
                "performance": performance_to_scoped_dict(performance),
                "model_performance": performance_to_scoped_dict(performance),
                "feature_importance": self._normalize_feature_importance(
                    trainer.get_feature_importance(method="gain", top_n=20)
                ),
                "oot_receipt": oot_bundle["oot_receipt"],
                "oof_receipts": list(
                    getattr(trainer, "last_oof_receipts", None)
                    or getattr(getattr(trainer, "analyzer", None), "last_oof_receipts", [])
                    or []
                ),
            }
            result = apply_service_matrix_scopes(result, has_oot_held_out=has_oot_held_out)

            if run_comparison:
                comparison = create_model_comparison()
                comparison.train_all(X=X, y=y, feature_names=feature_names, **training_kwargs)
                result["comparison"] = comparison.compare().to_dict()

            self.tasks[task_id].update(
                {
                    "status": "completed",
                    "completed_at": datetime.now().isoformat(),
                    "result": result,
                }
            )
            self.logger.info(f"模型任務完成: {task_id}")
        except Exception as exc:
            self.logger.error(f"模型任務失敗: {task_id}, error={str(exc)}", exc_info=True)
            self.tasks[task_id].update(
                {
                    "status": "failed",
                    "completed_at": datetime.now().isoformat(),
                    "error": str(exc),
                }
            )

    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        task = self.tasks.get(task_id)
        if task is None:
            return {
                "task_id": task_id,
                "status": "not_found",
                "error": "任務不存在",
            }
        return task

    async def _load_data(self, data_source: str) -> Tuple[pd.DataFrame, np.ndarray, List[str]]:
        if data_source.startswith("library:"):
            parts = data_source.split(":")
            if len(parts) != 3:
                raise ValueError("library 資料來源格式錯誤，應為 library:{symbol}:{timeframe}")

            _, symbol, timeframe = parts
            features_df = await asyncio.to_thread(self.feature_library.load, symbol, timeframe)
            feature_names = features_df.columns.tolist()
        else:
            try:
                features_df, feature_names, _ = await asyncio.to_thread(
                    self.feature_storage.load_features_from_hdf5,
                    data_source,
                )
            except FileNotFoundError as exc:
                raise ValueError(f"找不到特徵資料來源: {data_source}") from exc

        if "label" not in features_df.columns:
            raise ValueError("特徵資料缺少 label 欄位")

        y = features_df["label"].to_numpy()
        X = features_df.drop(columns=["label", "open_time"], errors="ignore")

        if X.empty:
            raise ValueError("特徵資料為空")

        final_feature_names = X.columns.tolist() if isinstance(X, pd.DataFrame) else feature_names
        return X, y, final_feature_names

    def _build_training_kwargs(self, validation: Dict[str, Any]) -> Dict[str, Any]:
        allowed_keys = {
            "cv_folds",
            "purge_gap",
            "early_stopping_rounds",
            "eval_size",
            "time_series_split",
            "timestamps",
            "embargo_pct",
        }
        return {key: value for key, value in validation.items() if key in allowed_keys}

    def _to_dict(self, item: Any) -> Dict[str, Any]:
        if hasattr(item, "to_dict") and callable(item.to_dict):
            return item.to_dict()
        if hasattr(item, "__dict__"):
            return {
                key: value
                for key, value in item.__dict__.items()
                if not key.startswith("_")
            }
        return {"value": item}

    def _normalize_feature_importance(self, items: List[Any]) -> List[Dict[str, Any]]:
        normalized: List[Dict[str, Any]] = []
        for item in items:
            raw = self._to_dict(item)
            feature_name = raw.get("feature_name", raw.get("feature"))
            normalized.append(
                {
                    "feature_name": feature_name,
                    "importance": raw.get("importance", 0.0),
                    "rank": raw.get("rank", 0),
                }
            )
        return normalized
