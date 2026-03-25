"""Momentum cross-domain protocols."""

from __future__ import annotations

from typing import (
    Protocol,
    Iterable,
    Any,
    Dict,
    Optional,
    Callable,
    List,
    Tuple,
    Union,
    runtime_checkable,
)


@runtime_checkable
class IKlineReader(Protocol):
    """Read kline data by symbol/timeframe and optional time range."""

    def read_klines(
        self,
        symbol: str,
        timeframe: str,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        validate_continuity: bool = False,
    ) -> Any:
        ...

    def read_klines_around_timestamp(
        self,
        symbol: str,
        timeframe: str,
        center_timestamp: int,
        lookback: int,
        forward: int,
    ) -> Any:
        ...

    def get_metadata(self, symbol: str, timeframe: str) -> Optional[Dict[str, Any]]:
        ...

    def get_last_timestamp(self, symbol: str, timeframe: str) -> Optional[int]:
        ...


@runtime_checkable
class IIndicatorEngine(Protocol):
    """Indicator calculation engine interface."""

    def calculate_indicators_from_dataframe(
        self,
        kline_df: Any,
        configs: Iterable[Dict[str, Any]],
    ) -> Any:
        ...


@runtime_checkable
class IModelTrainer(Protocol):
    """Model training interface for analysis/optimization."""

    def train_model(
        self,
        features: Any,
        labels: Any,
        feature_names: Iterable[str],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        ...

    def predict_proba(self, features: Any) -> Any:
        ...

    def get_feature_importance(
        self,
        method: str = "gain",
        top_n: Optional[int] = None,
    ) -> Any:
        ...

    def save_model(self, path: str) -> None:
        ...

    def load_model(self, path: str) -> None:
        ...

    def get_model_type(self) -> str:
        ...

    def get_model_params(self) -> Dict[str, Any]:
        ...

    def get_native_model(self) -> Any:
        ...


@runtime_checkable
class IOptimizationObjective(Protocol):
    """Pluggable optimization objective protocol."""

    @property
    def name(self) -> str:
        ...

    @property
    def direction(self) -> str:
        ...

    @property
    def directions(self) -> Optional[List[str]]:
        ...

    def create_search_space(self, trial: Any) -> Dict[str, Any]:
        ...

    def evaluate(self, params: Dict[str, Any]) -> Union[float, Tuple[float, ...]]:
        ...

    def get_pruning_callback(self, trial: Any) -> Optional[Any]:
        ...


@runtime_checkable
class IBacktestEngine(Protocol):
    """Backtest engine protocol."""

    def run_backtest(
        self,
        prices: Any,
        predicted_proba: Any,
        atr_values: Any,
        strategy_params: Dict[str, Any],
    ) -> Any:
        ...


@runtime_checkable
class IPositionSizer(Protocol):
    """Position sizing protocol."""

    def calculate_position_size(
        self,
        predicted_proba: float,
        equity: float,
        risk_params: Dict[str, Any],
    ) -> float:
        ...


@runtime_checkable
class IICAnalyzer(Protocol):
    """IC analyzer interface for cross-domain usage."""

    def analyze(
        self,
        features_path: str,
        labels_path: str,
        meta_path: Optional[str] = None,
        config_override: Optional[dict] = None,
        progress_callback: Optional[Callable] = None,
        kline_reader: Optional[Any] = None,
    ) -> dict:
        ...

    def get_top_features(self, n: int, sort_by: str = "icir") -> list:
        ...

    def get_filtered_features(self) -> Any:
        ...

    def get_report(self) -> dict:
        ...

    def refilter(self, thresholds: dict) -> dict:
        ...


@runtime_checkable
class ILabelGenerator(Protocol):
    """Label generator interface for IC analysis."""

    def generate_returns_by_type(
        self,
        close: Any,
        horizon: int,
        return_type: str,
        benchmark_close: Optional[Any] = None,
    ) -> Any:
        ...

    def horizon_to_bars(self, time_duration: str, timeframe: str) -> int:
        ...


@runtime_checkable
class ICVValidator(Protocol):
    """Cross-validation interface for model validation."""

    def validate(
        self,
        model: Any,
        X: Any,
        y: Any,
        config: Optional[dict] = None,
    ) -> dict:
        ...

    def get_oot_result(self) -> dict:
        ...
