"""Signal density objective adapter for pluggable Optuna optimizer."""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional, Tuple, Union

from momentum.core.protocols import IOptimizationObjective


class SignalDensityObjective(IOptimizationObjective):
    """Signal density 目標函式適配器（向後相容包裝）。"""

    def __init__(
        self,
        search_space_factory: Callable[[Any], Dict[str, Any]],
        evaluator: Callable[[Dict[str, Any]], Union[float, Tuple[float, ...]]],
        pruning_callback_factory: Optional[Callable[[Any], Optional[Any]]] = None,
        multi_objective: bool = False,
    ):
        self._search_space_factory = search_space_factory
        self._evaluator = evaluator
        self._pruning_callback_factory = pruning_callback_factory
        self._multi_objective = multi_objective

    @property
    def name(self) -> str:
        return "signal_density"

    @property
    def direction(self) -> str:
        return "maximize"

    @property
    def directions(self) -> Optional[list[str]]:
        if self._multi_objective:
            return ["maximize", "maximize"]
        return None

    def create_search_space(self, trial: Any) -> Dict[str, Any]:
        return self._search_space_factory(trial)

    def evaluate(self, params: Dict[str, Any]) -> Union[float, Tuple[float, ...]]:
        return self._evaluator(params)

    def get_pruning_callback(self, trial: Any) -> Optional[Any]:
        if self._pruning_callback_factory is None:
            return None
        return self._pruning_callback_factory(trial)
