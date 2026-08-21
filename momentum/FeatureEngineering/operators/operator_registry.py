from __future__ import annotations

from typing import Callable, Dict, List

from momentum.core.logging import get_logger


logger = get_logger(__name__)


class OperatorRegistry:
    """Operator registry for derived feature computation."""

    def __init__(self) -> None:
        self._operators: Dict[str, Callable] = {}

    def register(self, name: str, func: Callable) -> None:
        if not callable(func):
            raise TypeError(f"Operator must be callable: {name}")
        self._operators[name] = func

    def get(self, name: str) -> Callable:
        if name not in self._operators:
            raise KeyError(f"Operator not registered: {name}")
        return self._operators[name]

    def list_all(self) -> List[str]:
        return sorted(self._operators.keys())

    @classmethod
    def default_registry(cls) -> "OperatorRegistry":
        registry = cls()
        from momentum.FeatureEngineering.operators.derived_operators import DerivedOperatorEngine

        engine = DerivedOperatorEngine(config={})
        registry.register("distance", engine.compute_distance)
        registry.register("cross", engine.compute_cross)
        registry.register("momentum", engine.compute_momentum)
        registry.register("ratio", engine.compute_ratio)
        registry.register("binary_signal", engine.compute_binary_signal)
        registry.register("signed_strength", engine.transform_sign)
        registry.register("ts_argmax", engine.ts_argmax)
        registry.register("ts_argmin", engine.ts_argmin)
        registry.register("ts_corr", engine.ts_corr)
        registry.register("ts_rank", engine.ts_rank)
        registry.register("decay_linear", engine.decay_linear)
        registry.register("sign", engine.transform_sign)
        registry.register("log1p", engine.transform_log1p)
        registry.register("abs", engine.transform_abs)
        registry.register("clip", engine.transform_clip)
        # GAP-3 Task B3.3 state-counter 算子（僅註冊行；既有算子不動）
        from momentum.FeatureEngineering.operators import state_counters as sc

        registry.register("bars_since_cross", sc.bars_since_cross)
        registry.register("consecutive_run", sc.consecutive_run)
        registry.register("bars_since_threshold", sc.bars_since_threshold)
        registry.register("window_max_ratio", sc.window_max_ratio)
        registry.register("cross_count", sc.cross_count)
        return registry
