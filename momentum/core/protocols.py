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
class IBrowseRegistrar(Protocol):
    """Register persisted feature outputs for Feature Explorer browsing."""

    def register(self, symbol: str, timeframe: str, manifest_path: str) -> str:
        ...


@runtime_checkable
class IQualityComputer(Protocol):
    """Compute batch quality summaries from a persisted feature manifest."""

    def compute(self, manifest_path: str) -> dict:
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


@runtime_checkable
class IFeatureReader(Protocol):
    """Read persisted feature metadata and projected columns."""

    def feature_run_dir(self, symbol: str, tf: str, config_hash: str) -> Any:
        ...

    def load_manifest_v2(
        self,
        symbol: str,
        tf: str,
        config_hash: str,
        artifact_kind: str = "raw",
    ) -> dict:
        ...

    def stream_groups_v2(
        self,
        symbol: str,
        tf: str,
        config_hash: str,
        artifact_kind: str = "raw",
    ) -> Iterable[Tuple[str, Any]]:
        ...

    def load_columns_v2(
        self,
        symbol: str,
        tf: str,
        config_hash: str,
        columns: List[str],
        artifact_kind: str = "raw",
        *,
        attach_row_index: bool = False,
    ) -> Any:
        ...

    def load_row_index_v2(
        self,
        symbol: str,
        tf: str,
        config_hash: str,
        artifact_kind: str = "raw",
    ) -> Any:
        """該 artifact_kind 之 sidecar 時間軸（raw 未宣告回 None；processed 未宣告或檔缺 ⇒ 具名錯誤）。"""
        ...

    def list_features(self, symbol: str, config_hash: str) -> List[str]:
        ...

    def load_columns(
        self,
        symbol: str,
        config_hash: str,
        columns: List[str],
    ) -> Any:
        ...


@runtime_checkable
class IMemoryBudget(Protocol):
    """生成記憶體預算（ICFIRSTALIGN Task 4.2）：分派點之配置前判定與層界線（實作＝`momentum.factories.get_memory_budget`）。"""

    def check_estimate(self, branch_id: str, params: Dict[str, Any], **kwargs: Any) -> List[Any]:
        """以分支表估算並判定；不通過 ⇒ `GenerationMemoryBudgetExceeded`（配置之前）。"""
        ...

    def configured_budget_bytes(self) -> int:
        """快區 R（實體記憶體 × 比例或設定絕對值；SPEC v35：只管並行准入與選路，不作拒絕理由）。"""
        ...

    # 具名例外（SPEC v35）：`GenerationMemoryBudgetExceeded`（機器可用量不足／停止旗標）、
    # `MemoryRerouteNeeded`（域內 worker 估算低估 ⇒ 根串行重試，前者之子類）
    GenerationMemoryBudgetExceeded: type
    MemoryRerouteNeeded: type


@runtime_checkable
class IMemoryBudgetScheduler(Protocol):
    """子行程預算域之有限波次排程器（ICFIRSTALIGN Task 4.2 v25–v27；`momentum.factories.create_memory_budget_scheduler`）。"""

    def run(
        self,
        tasks: Any,
        worker_fn: Callable[[Any, Any], Any],
        serial_fn: Callable[[Any], Any],
        on_wave_joined: Callable[[List[Any]], None],
    ) -> List[Any]:
        """依序准入有限波次；不足只排隊；無可准入走根行程內之串行臂；每波 join 後呼叫 `on_wave_joined`。"""
        ...

    def snapshot(self) -> Any:
        """目前之准入狀態（成員、啟動槽、可吸收量、壓力、停止旗標）。"""
        ...

    def request_stop(self) -> None:
        """呼叫端取消：未准入之任務不再執行；已啟動者確認退出後 `run` 才返回（SPEC v30）。"""
        ...
