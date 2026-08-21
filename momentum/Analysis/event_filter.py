"""Event filter utilities for IC analysis."""

from __future__ import annotations

import re
from typing import Optional, Protocol

import numpy as np
import pandas as pd

from momentum.core.exceptions import InvalidQueryError
from momentum.core.logging import get_logger
from momentum.Analysis.event_samples.condition_engine import (
    ConditionError,
    ConditionSpec,
    allowed_filtering_params,
    evaluate_condition,
)


logger = get_logger(__name__)


def apply_condition_spec(df: pd.DataFrame, spec: ConditionSpec) -> tuple[pd.DataFrame, dict]:
    """GAP-3 B3.2 薄 adapter：以 B3.1 條件引擎對 df 求遮罩（同引擎、非平行實作）。

    只接受 `expression_role='feature'`（D3-4：selection_predicate 欄不得流入特徵表）。
    回 (filtered_df, info)；info 帶 `mode='condition_engine'`＋digest＋column_roles 供 provenance。
    """
    if spec.expression_role != "feature":
        raise InvalidQueryError(
            f"event_filter 只接受 expression_role='feature'（D3-4），得 {spec.expression_role!r}"
        )
    try:
        mask = evaluate_condition(spec, df)
    except (ConditionError, KeyError) as exc:
        raise InvalidQueryError(f"condition evaluation failed: {exc}") from exc
    info = {
        "mode": "condition_engine",
        "condition_digest": spec.canonical_digest,
        "condition_expression": spec.expression,
        "condition_column_roles": dict(spec.column_roles),
        "condition_max_lookback": int(spec.max_lookback),
        # 誠實邊界（D3-3）：legacy df.eval 路徑仍保留；「已共用完整引擎」須待角色隔離 receipt 過審後才得宣稱
        "engine": "condition_engine_adapter",
    }
    return df[mask], info


__all__ = ["EventFilter", "IEventFilter", "allowed_filtering_params", "apply_condition_spec"]


class IEventFilter(Protocol):
    """Event filter protocol (module-local)."""

    def apply_filter(
        self,
        df: pd.DataFrame,
        query: Optional[str] = None,
        timestamps: Optional[list[int]] = None,
        *,
        condition_spec: Optional[ConditionSpec] = None,
    ) -> tuple[pd.DataFrame, dict]:
        ...

    def validate_query(self, query: str, columns: list[str]) -> bool:
        ...

    def check_sample_size(self, n_events: int, config: dict) -> tuple[str, float]:
        ...


class EventFilter:
    """Stage 3: 事件過濾 — Query String 解析 + Boolean Mask + 樣本數安全檢查。"""

    _BLOCKLIST = {
        "__",
        "import",
        "exec",
        "eval",
        "open",
        "os",
        "sys",
        "subprocess",
        "lambda",
    }
    _ALLOWED_KEYWORDS = {"and", "or", "not", "True", "False", "None"}

    def __init__(self, config: dict):
        self._config = config or {}

    def apply_filter(
        self,
        df: pd.DataFrame,
        query: Optional[str] = None,
        timestamps: Optional[list[int]] = None,
        *,
        condition_spec: Optional["ConditionSpec"] = None,
    ) -> tuple[pd.DataFrame, dict]:
        """套用事件過濾。

        既有 `query`（legacy `df.eval` 遮罩）與 `timestamps` 路徑語意不變。
        `condition_spec`（GAP-3 B3.2 薄 adapter；keyword-only，預設 None ⇒ 行為不變）：以 B3.1
        條件引擎求遮罩；IC 事件遮罩之欄位進特徵表，故 **只接受 `expression_role='feature'`**
        （selection_predicate 欄不得流入特徵表——SPEC D3-4），否則 InvalidQueryError。
        與 `query` 同時給 ⇒ 拒（單一遮罩來源）。
        """

        if df is None:
            raise ValueError("df is required")

        filter_info: dict = {
            "mode": "none",
            "query": query,
            "timestamps": timestamps,
        }

        filtered = df
        if condition_spec is not None:
            if query:
                raise InvalidQueryError("condition_spec and query are mutually exclusive")
            filtered, cond_info = apply_condition_spec(df, condition_spec)
            filter_info.update(cond_info)
        elif query:
            self._ensure_valid_query(query, df.columns.tolist())
            try:
                mask = df.eval(query, engine="python")
            except Exception as exc:  # noqa: BLE001
                logger.error("Query evaluation failed: %s", exc, exc_info=True)
                raise InvalidQueryError("query evaluation failed") from exc
            if not isinstance(mask, pd.Series) or not pd.api.types.is_bool_dtype(mask):
                raise InvalidQueryError("query must evaluate to a boolean mask")
            filtered = df[mask]
            filter_info["mode"] = "query"
        elif timestamps is not None:
            timestamps = list(timestamps)
            if "timestamp" in df.columns:
                mask = df["timestamp"].isin(timestamps)
            else:
                mask = df.index.isin(timestamps)
            filtered = df[mask]
            filter_info["mode"] = "timestamps"

        tier, adjusted_p = self.check_sample_size(len(filtered), self._config)
        filter_info.update(
            {
                "n_events": int(len(filtered)),
                "tier": tier,
                "adjusted_p_threshold": adjusted_p,
            }
        )

        if tier == "insufficient":
            logger.warning("Insufficient events: n=%s", len(filtered))

        return filtered, filter_info

    def validate_query(self, query: str, columns: list[str]) -> bool:
        """Query String 安全驗證。"""

        if not query or len(query) > 500:
            return False

        identifiers = re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", query)
        for name in identifiers:
            lowered = name.lower()
            if name in self._ALLOWED_KEYWORDS or lowered in self._ALLOWED_KEYWORDS:
                continue
            if name in columns:
                if lowered.startswith("__"):
                    return False
            elif lowered in self._BLOCKLIST or lowered.startswith("__"):
                return False
            elif name not in columns:
                return False

        return True

    def check_sample_size(self, n_events: int, config: dict) -> tuple[str, float]:
        """樣本數安全檢查。"""

        cfg = config or {}
        min_events = int(cfg.get("min_events", 30))
        tiers = cfg.get("sample_size_tiers", {}) or {}
        sufficient = int(tiers.get("sufficient", 200))
        marginal = int(tiers.get("marginal", 100))
        low_confidence = int(tiers.get("low_confidence", 30))

        if n_events < min_events or n_events < low_confidence:
            return "insufficient", float("nan")
        if n_events >= sufficient:
            return "sufficient", 0.05
        if n_events >= marginal:
            return "marginal", 0.05
        return "low_confidence", 0.10

    def _ensure_valid_query(self, query: str, columns: list[str]) -> None:
        if not self.validate_query(query, columns):
            raise InvalidQueryError("invalid event filter query")
