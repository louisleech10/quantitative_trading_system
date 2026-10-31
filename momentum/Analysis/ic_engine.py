"""IC core engine for IC Gatekeeper."""

from __future__ import annotations

import gc
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import optimize, stats

from momentum.Analysis.pit_stats import (
    pit_expanding_quantile_thresholds,
    rolling_window_rank_corr,
)
from momentum.FeatureEngineering.consumer_gate import (
    assert_consumer_run_status,
    effective_run_status,
    is_source_run_status_reusable,
)
from momentum.core.contracts import AlignmentViolationError
from momentum.core.icfirstalign_errors import (
    ICCacheRawUnavailableError,
    RowIndexArtifactMissingError,
    RowIndexLengthMismatchError,
)
from momentum.core.exceptions import InvalidInputError
from momentum.core.logging import get_logger
from momentum.core.protocols import IFeatureReader


logger = get_logger(__name__)

try:
    from numba import njit, prange
except ImportError:  # pragma: no cover
    prange = range

    def njit(*args, **kwargs):  # type: ignore[misc]
        def _decorator(fn):
            return fn

        if args and callable(args[0]):
            return args[0]
        return _decorator


@njit(cache=True, parallel=True)
def _rolling_pearson_numba(x: np.ndarray, y: np.ndarray, window: int, stride: int) -> np.ndarray:
    """ICPERF Task 0.4 ㉘：逐窗 Pearson（窗內兩趟：先均值、再中心化動差；不以原值累積和相減）。

    窗內該特徵或標籤有任一非有限值、或任一為常數（窗內全等於首值，同 `scipy.stats.pearsonr` 之常數判定）⇒ NaN；
    結果截於 [−1, 1]（同 scipy）。特徵維於內層迴圈（列主序連續存取）。各窗互相獨立 ⇒ 窗維 prange 平行（r55 群集 H
    四項平衡：每窗之運算次序不變，結果逐位元與循序相同）；暫存逐窗配置（執行緒私有）。
    """
    n_bars, n_features = x.shape
    n_out = (n_bars - window) // stride + 1
    out = np.full((n_out, n_features), np.nan)
    for oi in prange(n_out):
        sum_x = np.empty(n_features)
        sxy = np.empty(n_features)
        sxx = np.empty(n_features)
        ok = np.empty(n_features, dtype=np.bool_)
        varying = np.empty(n_features, dtype=np.bool_)
        start = oi * stride
        y0 = y[start]
        y_ok = True
        y_varying = False
        y_sum = 0.0
        for i in range(window):
            v = y[start + i]
            if not np.isfinite(v):
                y_ok = False
                break
            if v != y0:
                y_varying = True
            y_sum += v
        if not (y_ok and y_varying):
            continue
        y_bar = y_sum / window
        syy = 0.0
        for i in range(window):
            dy = y[start + i] - y_bar
            syy += dy * dy
        for fi in range(n_features):
            sum_x[fi] = 0.0
            sxy[fi] = 0.0
            sxx[fi] = 0.0
            ok[fi] = True
            varying[fi] = False
        for i in range(window):
            row = start + i
            for fi in range(n_features):
                v = x[row, fi]
                if not np.isfinite(v):
                    ok[fi] = False
                elif v != x[start, fi]:
                    varying[fi] = True
                sum_x[fi] += v
        for fi in range(n_features):
            sum_x[fi] = sum_x[fi] / window
        for i in range(window):
            row = start + i
            dy = y[row] - y_bar
            for fi in range(n_features):
                dx = x[row, fi] - sum_x[fi]
                sxy[fi] += dx * dy
                sxx[fi] += dx * dx
        sy = np.sqrt(syy)
        for fi in range(n_features):
            if ok[fi] and varying[fi]:
                r = sxy[fi] / (np.sqrt(sxx[fi]) * sy)
                if r > 1.0:
                    r = 1.0
                elif r < -1.0:
                    r = -1.0
                out[oi, fi] = r
    return out


@njit(cache=True, parallel=True)
def _rolling_kendall_numba(x: np.ndarray, y: np.ndarray, window: int, stride: int) -> np.ndarray:
    """ICPERF Task 0.4 ㉗：逐窗 Kendall τ-b（同 `scipy.stats.kendalltau` 預設 variant='b'），滑窗增量維護整數計數。

    窗內點對之 S＝Σ sign(xᵢ−xⱼ)·sign(yᵢ−yⱼ)（＝一致對數−不一致對數）、x 同值對數 Tx、y 同值對數 Ty 以整數精確維護：
    新點進窗加上其與窗內各點之貢獻、舊點出窗減去其與窗內其餘點之貢獻（每步 O(window)）；τ-b＝S／√(tot−Tx)／√(tot−Ty)，
    tot＝window(window−1)/2（同 scipy 之運算次序，截於 [−1, 1]）。窗內任一點 x 或 y 非有限 ⇒ NaN（非有限點不入計數）；
    Tx＝tot 或 Ty＝tot（常數窗）⇒ NaN（同 scipy）。各特徵之增量計數互相獨立 ⇒ 特徵維 prange 平行（r55 群集 H 四項平衡；
    整數計數與每特徵之運算次序不變，結果逐位元與循序相同）；逐特徵暫存為執行緒私有。
    """
    n_bars, n_features = x.shape
    n_out = (n_bars - window) // stride + 1
    out = np.full((n_out, n_features), np.nan)
    tot = window * (window - 1) // 2
    y_fin = np.empty(n_bars, dtype=np.bool_)
    for t in range(n_bars):
        y_fin[t] = np.isfinite(y[t])
    for fi in prange(n_features):
        xc = np.empty(n_bars)
        good = np.empty(n_bars, dtype=np.bool_)
        for t in range(n_bars):
            xc[t] = x[t, fi]
            good[t] = y_fin[t] and np.isfinite(xc[t])
        s = 0
        tx = 0
        ty = 0
        bad = 0
        for t in range(n_bars):
            lo = t - window + 1
            if lo < 0:
                lo = 0
            if good[t]:
                xt = xc[t]
                yt = y[t]
                for j in range(lo, t):
                    if not good[j]:
                        continue
                    xj = xc[j]
                    yj = y[j]
                    if xt == xj:
                        tx += 1
                        if yt == yj:
                            ty += 1
                    elif yt == yj:
                        ty += 1
                    elif (xt > xj) == (yt > yj):
                        s += 1
                    else:
                        s -= 1
            else:
                bad += 1
            if t < window - 1:
                continue
            start = t - window + 1
            if start % stride == 0 and bad == 0 and tx != tot and ty != tot:
                tau = s / np.sqrt(float(tot - tx)) / np.sqrt(float(tot - ty))
                if tau > 1.0:
                    tau = 1.0
                elif tau < -1.0:
                    tau = -1.0
                out[start // stride, fi] = tau
            # 舊點出窗：減去 start 與窗內其餘點（start+1..t）之貢獻
            if good[start]:
                xs = xc[start]
                ys = y[start]
                for j in range(start + 1, t + 1):
                    if not good[j]:
                        continue
                    xj = xc[j]
                    yj = y[j]
                    if xs == xj:
                        tx -= 1
                        if ys == yj:
                            ty -= 1
                    elif ys == yj:
                        ty -= 1
                    elif (xs > xj) == (ys > yj):
                        s -= 1
                    else:
                        s += 1
            else:
                bad -= 1
    return out


# ICFIRSTALIGN Task 1.4：IC cache 重用之完整計算身分（只容 threshold 不同；任一不同或缺欄 ⇒ 拒用、需 raw 重算）
CACHE_IDENTITY_FIELDS = (
    "symbol",
    "tf",
    "config_hash",
    "method",
    "label_horizon",
    "selection_window_start",
    "selection_window_end",
    "split_id",
    "feature_axis_sha256",
    "label_sha256",
    # FFDSTAR Task 2.3（§C D5）：特徵值身分＝manifest raw 節點之 `content_sha256`（raw 已刪時 manifest 仍在）；缺即拒用
    "content_sha256",
    # NUMVIEW Task 4.2（D2）：產生方式（`algorithm_id`）與事後路由身分（R5-B）；取自 raw 節點，缺即拒用（舊 run 不沿用）
    "algorithm_id",
    "route_identity",
)
#: 請求身分中值為 None 即拒用（不可得 ⇒ 身分不完整）之欄
_IDENTITY_FIELDS_REQUIRED_NON_NULL = ("feature_axis_sha256", "content_sha256", "algorithm_id", "route_identity")


def _utc_epoch_ns(index: Any) -> np.ndarray:
    """時間戳 → UTC int64 epoch 奈秒（完整精度，不截至整秒；審碼 b1 r1 codex P1-01：截秒使次秒不同之選窗身分碰撞）：
    tz-aware 任一時區轉 UTC 時刻；tz-naive 依 §C 資料契約視為 UTC；整數依 §C 視為 epoch 秒並換算為奈秒。"""
    if isinstance(index, pd.DatetimeIndex):
        dt = index.tz_convert("UTC").tz_localize(None) if index.tz is not None else index
        return np.asarray(dt.as_unit("ns").asi8, dtype=np.int64)
    values = np.asarray(index)
    if np.issubdtype(values.dtype, np.integer):
        return values.astype(np.int64) * np.int64(1_000_000_000)
    return _utc_epoch_ns(pd.DatetimeIndex(pd.to_datetime(values)))


def label_fingerprint(label: pd.Series) -> str:
    """label 指紋（SPEC Task 1.4）：sha256 依序吃 列數（int64 LE）、UTC epoch 奈秒（int64 LE）、NaN 遮罩（uint8）、
    有限值位置之 float64 LE。同一 UTC 時刻之不同表示（任一時區 tz-aware、UTC tz-naive、epoch 秒）得同一指紋。"""
    import hashlib

    series = label if isinstance(label, pd.Series) else pd.Series(label)
    instants = _utc_epoch_ns(series.index).astype("<i8")
    values = np.asarray(series.to_numpy(dtype=np.float64), dtype="<f8")
    mask = ~np.isfinite(values)
    digest = hashlib.sha256()
    digest.update(np.asarray([len(values)], dtype="<i8").tobytes())
    digest.update(instants.tobytes())
    digest.update(mask.astype(np.uint8).tobytes())
    digest.update(values[~mask].tobytes())
    return digest.hexdigest()


def _axis_fingerprint(row_index: Optional[pd.DatetimeIndex]) -> Optional[str]:
    """特徵軸指紋：raw sidecar 之 UTC epoch 奈秒（int64 LE）之 sha256；無軸 ⇒ None（身分不完整）。"""
    import hashlib

    if row_index is None:
        return None
    return hashlib.sha256(_utc_epoch_ns(row_index).astype("<i8").tobytes()).hexdigest()


def _window_bound(value: Any) -> Optional[int]:
    """選窗端點之身分值：UTC epoch 奈秒（與 `_apply_selection_window` 之 Timestamp 比較同精度）；舊秒制 cache 因值不同而拒用。"""
    if value is None or value == "":
        return None
    return int(_utc_epoch_ns(pd.DatetimeIndex([pd.Timestamp(value)]))[0])


class ICReadError(RuntimeError):
    """Raised when L7 raw IC streaming cannot be completed safely."""


@dataclass
class ICSelectionResult:
    """Result payload for IC-First raw streaming selection."""

    symbol: str
    tf: str
    config_hash: str
    selected: List[str]
    ic_scores: Dict[str, float]
    skipped_groups: List[str]
    quality_status: str
    selected_path: str
    data_fingerprint: Dict[str, Any]
    ic_params: Dict[str, Any]
    group_count: int
    total_features: int
    frozen_gate_eligible: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ICEngine:
    """Stage 4: IC core engine."""

    def __init__(self, config: dict):
        self._config = config or {}
        self._methods = self._config.get("methods", ["spearman"])
        self._rolling_windows = self._config.get("rolling_windows", [21, 63, 126])
        self._rolling_stride = self._config.get("rolling_stride", 1)
        self._ic_decay_horizons = self._config.get(
            "ic_decay_horizons", [1, 2, 3, 5, 8, 13, 21]
        )

        icir_config = self._config.get("icir", {})
        self._icir_window = icir_config.get("window", 63)
        self._reference_tf = icir_config.get("reference_tf", "12h")
        self._timeframe = self._config.get("timeframe")

        self._grouped_config = self._config.get("grouped_analysis", {})

    def set_timeframe(self, timeframe: Optional[str], reference_tf: Optional[str] = None) -> str:
        """TFWINDOW Task 3.1：由 run 之 `metadata.timeframe` 注入，讓 `_adjust_rolling_windows` 在生產路徑生效。

        回傳揭露值：`applied`／`not_applied:missing_timeframe`／`not_applied:invalid_timeframe`／
        `not_applied:invalid_reference_tf`（fail-loud，不假換算）。
        `reference_tf` 由呼叫端以 **effective** config 傳入（R5 CODEX-R5-P2-03：`config_override` 改了 reference 而引擎仍用建構時值）。
        「合法」＝可解析且為有限正數（R5 CODEX-R5-P1-02：`0h`／`-1h`／`infh`／`nanh` 曾被視為 applied ⇒ 視窗全 1 或拋例外）。
        出生事故：`ICEngine(config.ic_calculation.model_dump())` 從無 `timeframe` 鍵 ⇒ 12h 設計的 [21,63,126] 直接套 1h run。
        """
        if reference_tf is not None:
            self._reference_tf = str(reference_tf)
        if not timeframe:
            self._timeframe = None
            return "not_applied:missing_timeframe"
        if not self._is_valid_timeframe_hours(self._parse_timeframe_hours(str(timeframe))):
            self._timeframe = None
            logger.warning("Invalid timeframe for rolling windows: %s", timeframe)
            return "not_applied:invalid_timeframe"
        if not self._is_valid_timeframe_hours(self._parse_timeframe_hours(str(self._reference_tf or ""))):
            self._timeframe = None
            logger.warning("Invalid reference_tf for rolling windows: %s", self._reference_tf)
            return "not_applied:invalid_reference_tf"
        self._timeframe = str(timeframe)
        return "applied"

    @staticmethod
    def _is_valid_timeframe_hours(hours: Optional[float]) -> bool:
        """可解析且有限正數才算合法（`0h`／負／inf／nan 一律非法）。"""
        return hours is not None and np.isfinite(hours) and hours > 0

    def compute_ic(
        self,
        features_df: pd.DataFrame,
        label: pd.Series,
        method: str = "spearman",
    ) -> dict[str, float]:
        """計算所有特徵對單一 Label 的 IC."""

        if features_df.empty:
            return {}

        if len(features_df) < 2 or len(label) < 2:
            return {feature: np.nan for feature in features_df.columns}

        if method in {"spearman", "pearson"} and not self._has_missing(
            features_df, label
        ):
            return self._compute_vectorized_ic(features_df, label, method)

        label_name = label.name or "label"
        label_series = label.rename(label_name)
        results: dict[str, float] = {}

        for feature in features_df.columns:
            series = features_df[feature]
            value = self._compute_pairwise_corr(series, label_series, method)
            results[feature] = value

        return results

    def compute_ic_from_l7_raw(
        self,
        symbol: str,
        tf: str,
        config_hash: str,
        label: pd.Series,
        *,
        feature_reader: IFeatureReader,
        ic_threshold: Optional[float] = None,
        allow_partial_ic: bool = False,
        method: Optional[str] = None,
        label_horizon: Optional[str] = None,
        selection_window: Optional[Dict[str, Any]] = None,
        split_id: Optional[str] = None,
        ic_params: Optional[Dict[str, Any]] = None,
    ) -> ICSelectionResult:
        """Compute IC from canonical L7 raw parquet groups without full concat.

        Cache hit path: when raw/ has been deleted (cleanup_raw=True after pipeline),
        a previously saved ic_selected_features JSON holds all IC scores.  Re-applying
        a different threshold only requires loading that JSON — no raw parquet reads.
        """

        self._reject_positional_selection(selection_window)
        self._validate_selection_metadata(label_horizon, selection_window, split_id)
        resolved_method = method or (self._methods[0] if self._methods else "spearman")
        resolved_threshold = float(
            ic_threshold
            if ic_threshold is not None
            else self._config.get("ic_threshold", 0.02)
        )
        merged_ic_params = self._build_ic_params(
            method=resolved_method,
            ic_threshold=resolved_threshold,
            allow_partial_ic=allow_partial_ic,
            label_horizon=label_horizon,
            selection_window=selection_window,
            split_id=split_id,
            overrides=ic_params,
        )

        # Resolve paths early so the cache check can run before any raw/ access.
        run_dir = Path(feature_reader.feature_run_dir(symbol, tf, config_hash))
        selected_path = run_dir / f"ic_selected_features_{symbol}_{tf}.json"
        raw_dir = run_dir / "raw"

        # ── Cache hit path ──────────────────────────────────────────────────────
        # If raw/ was cleaned up but the JSON cache exists, re-apply the new
        # threshold to previously computed IC scores without reading raw parquet.
        if not raw_dir.exists() and selected_path.exists():
            try:
                axis_for_identity = feature_reader.load_row_index_v2(symbol, tf, config_hash, artifact_kind="raw")
            except (RowIndexArtifactMissingError, ValueError):
                axis_for_identity = None  # 特徵軸不可得 ⇒ 身分不完整 ⇒ 拒用
            # FFDSTAR Task 2.3：值身分取自 manifest raw 節點（raw 目錄已刪而 manifest 仍在；只讀 manifest、不讀群組檔）
            try:
                raw_node = (feature_reader.load_manifest_v2(
                    symbol, tf, config_hash, artifact_kind="raw", consumer="browse",
                ).get("artifacts") or {}).get("raw") or {}
                content_for_identity = raw_node.get("content_sha256")
            except (FileNotFoundError, ValueError):
                raw_node = {}
                content_for_identity = None  # manifest／raw 節點不可得 ⇒ 身分不完整 ⇒ 拒用
            request_identity = self._request_identity(
                symbol=symbol, tf=tf, config_hash=config_hash, method=resolved_method,
                label_horizon=label_horizon, selection_window=selection_window, split_id=split_id,
                row_index=axis_for_identity, label=label, content_sha256=content_for_identity,
                raw_node=raw_node,
            )
            cache_result = self._try_reuse_cached_ic_scores(
                selected_path=selected_path,
                symbol=symbol,
                tf=tf,
                config_hash=config_hash,
                label=label,
                merged_ic_params=merged_ic_params,
                resolved_threshold=resolved_threshold,
                allow_partial_ic=allow_partial_ic,
                request_identity=request_identity,
            )
            if cache_result is not None:
                return cache_result
            raise ICCacheRawUnavailableError(
                f"raw/ artifact not found at {raw_dir} and cached IC scores do not match the requested "
                f"computation identity (only ic_threshold may differ). Re-run the IC-First pipeline to "
                f"regenerate raw/."
            )
        # ── Full recompute path (raw/ must exist) ───────────────────────────────

        manifest = feature_reader.load_manifest_v2(
            symbol,
            tf,
            config_hash,
            artifact_kind="raw",
            consumer="strict",
            allow_partial=allow_partial_ic,
        )
        raw_artifact = self._validate_l7_raw_manifest(
            manifest,
            symbol=symbol,
            tf=tf,
            config_hash=config_hash,
            allow_partial_ic=allow_partial_ic,
        )
        base_dir = run_dir  # FRAMEPATH Task 2.6：只讀 V2 run 目錄（舊版面轉向已刪）

        # ICFIRSTALIGN Task 1.1：群組讀回接 raw sidecar 時間軸（缺 ⇒ 具名錯誤；不得以位置對齊）
        row_index = self._load_raw_row_index(feature_reader, symbol, tf, config_hash)
        data_fingerprint = self._build_data_fingerprint(
            symbol=symbol,
            tf=tf,
            config_hash=config_hash,
            manifest=manifest,
            raw_artifact=raw_artifact,
            ic_params=merged_ic_params,
        )
        # ICFIRSTALIGN Task 1.4：fingerprint 寫入完整計算身分（供日後 cache 重用之逐欄比對）
        data_fingerprint.update(self._request_identity(
            symbol=symbol, tf=tf, config_hash=config_hash, method=resolved_method,
            label_horizon=label_horizon, selection_window=selection_window, split_id=split_id,
            row_index=row_index, label=label, content_sha256=raw_artifact.get("content_sha256"),
            raw_node=raw_artifact,
        ))

        ic_scores: Dict[str, float] = {}
        skipped_groups: List[str] = []
        group_count = 0

        groups_meta = raw_artifact.get("groups", {}) or {}
        from momentum.factories import get_memory_budget  # R2：跨域經 factory 取 IMemoryBudget（呼叫時解析）

        budget = get_memory_budget()
        self._iter_l7_raw_group_paths(base_dir, raw_artifact)  # 群組路徑安全預檢（不讀檔；不安全／缺路徑 ⇒ ICReadError）

        def _before_group_read(group_name: str, _group_info: Dict[str, Any]) -> None:
            # ICFIRSTALIGN Task 4.2：群組讀回前之配置前預算判定（讀檔＋轉型；受保護 run 外為單行程模式）
            budget.check_estimate(
                "IC.group_read",
                {"rows": int(len(row_index)),
                 "group_cols": len((groups_meta.get(group_name) or {}).get("columns") or [])},
                label=f"IC.group_read:{group_name}",
            )

        def _on_group_read_error(group_name: str, parquet_path: Path, exc: Exception) -> None:
            if not allow_partial_ic:
                raise ICReadError(f"Failed to read L7 raw group {group_name}: {parquet_path}") from exc
            skipped_groups.append(str(parquet_path))
            logger.warning("[IC-First] skipped corrupted group: %s", parquet_path)

        # FF-NAME Task 3.4：群組只經 FeatureReader 讀取（manifest 共同邊界含命名世代閘）；依群組名排序同改前
        for group_name, group_df in feature_reader.stream_groups_v2(
            symbol, tf, config_hash, artifact_kind="raw", consumer="strict", allow_partial=allow_partial_ic,
            sort_groups=True, before_read=_before_group_read, on_read_error=_on_group_read_error,
        ):
            group_df = self._attach_row_index(group_df, row_index)

            try:
                group_ic = self._compute_l7_raw_group_ic(
                    group_df=group_df,
                    label=label,
                    method=resolved_method,
                    selection_window=selection_window,
                )
                ic_scores.update(group_ic)
                group_count += 1
            finally:
                del group_df
                gc.collect()

        selected = [
            feature
            for feature, ic_value in ic_scores.items()
            if self._passes_ic_threshold(ic_value, resolved_threshold)
        ]
        quality_status = "partial" if skipped_groups else "complete"
        payload = self._write_ic_selected_json_atomic(
            output_path=selected_path,
            symbol=symbol,
            tf=tf,
            config_hash=config_hash,
            selected=selected,
            ic_scores=ic_scores,
            data_fingerprint=data_fingerprint,
            ic_params=merged_ic_params,
            skipped_groups=skipped_groups,
            quality_status=quality_status,
        )

        logger.info(
            "[IC-First] ic_gate done: symbol=%s tf=%s selected=%d/%d status=%s skipped=%d",
            symbol,
            tf,
            len(selected),
            len(ic_scores),
            quality_status,
            len(skipped_groups),
        )
        return ICSelectionResult(
            symbol=symbol,
            tf=tf,
            config_hash=config_hash,
            selected=selected,
            ic_scores=ic_scores,
            skipped_groups=skipped_groups,
            quality_status=quality_status,
            selected_path=str(payload["selected_path"]),
            data_fingerprint=data_fingerprint,
            ic_params=merged_ic_params,
            group_count=group_count,
            total_features=int(raw_artifact.get("total_features", len(ic_scores))),
            frozen_gate_eligible=quality_status == "complete",
        )

    def compute_rolling_ic(
        self,
        features_df: pd.DataFrame,
        label: pd.Series,
        windows: list[int],
        stride: int = 1,
        method: str = "spearman",
    ) -> dict[str, dict]:
        """Rolling IC 時間序列.

        spearman：每窗內 rank + batch corr（PIT，見 ``pit_stats.rolling_window_rank_corr``）。
        kendall：逐窗 Kendall τ-b（ICPERF Task 0.4 ㉗，同 `scipy.stats.kendalltau`；`_rolling_kendall_matrix`）。
        pearson / 其他：逐窗 Pearson，窗內兩趟中心化動差（ICPERF Task 0.4 ㉘；`_rolling_corr_matrix`）。
        輸出 list 長度 = emitted window-ends（window-1, window-1+stride, ...）。
        ICPERF Task 0.4 ㉛：輸出窗＝依週期換算之 `windows`，另加換算後之 ICIR 窗（不在其中時另算，供 `compute_icir` 取用，
        不靜默退回第一個窗）。
        """

        # ICPERF Task 0.4 ④：時間軸＝標籤有限之列（與其他特徵無關，同請求各特徵共用此軸）；每窗每特徵獨立——窗內該特徵
        # 有任一非有限值 ⇒ 該窗 NaN（兩分支皆同）。舊版對全部特徵與標籤聯合 dropna，任一欄全 NaN 即使全部特徵滾動 IC 為空
        label_values = label.reindex(features_df.index).to_numpy(dtype=float)
        axis_rows = np.isfinite(label_values)
        if not axis_rows.any():
            return {name: {} for name in features_df.columns}

        adjusted_windows = list(self._adjust_rolling_windows(windows))
        icir_window = self._adjusted_icir_window()
        if icir_window not in adjusted_windows:
            adjusted_windows.append(icir_window)
        results: dict[str, dict] = {name: {} for name in features_df.columns}

        # raw values — spearman 不再全序列 pre-rank（P0-1 look-ahead 修正）
        x_values = features_df.to_numpy(dtype=float)[axis_rows]
        y_values = label_values[axis_rows]

        for window in adjusted_windows:
            window_key = f"window_{window}"
            if method == "spearman":
                corr_matrix = rolling_window_rank_corr(
                    x_values, y_values, window=int(window), stride=int(stride)
                )
            elif method == "kendall":
                corr_matrix = self._rolling_kendall_matrix(
                    x_values, y_values, window, stride
                )
            else:
                # pearson（及其他非 spearman／kendall）：逐窗 Pearson
                corr_matrix = self._rolling_corr_matrix(
                    x_values, y_values, window, stride
                )
            for idx, feature in enumerate(features_df.columns):
                results[feature][window_key] = corr_matrix[:, idx].tolist()
        return results

    def compute_icir(self, rolling_ic_results: dict) -> dict[str, dict]:
        """ICIR = IC Mean / IC Std."""

        icir_results: dict[str, dict] = {}
        self._warn_missing_icir_window(rolling_ic_results)
        for feature, windows in rolling_ic_results.items():
            series = self._select_icir_series(windows)
            values = np.array(series, dtype=float)
            if values.size == 0:
                ic_mean = np.nan
                ic_std = np.nan
                icir = np.nan
                hit_rate = np.nan
                neg_rate = np.nan
            else:
                ic_mean = float(np.nanmean(values))
                ic_std = float(np.nanstd(values))
                icir = float(ic_mean / ic_std) if ic_std > 0 else np.nan
                # ICPERF Task 0.4 ②：勝率只計有限 IC（滾動窗可出 NaN，pit_stats.py:277、:288），同 ic_mean 之 nanmean
                finite = values[np.isfinite(values)]
                hit_rate = float(np.mean(finite > 0)) if finite.size else np.nan
                # ICPERF Task 0.4 ⑧：負向勝率（有限 IC 中 < 0 之比例），供方向對齊勝率（direction＝−1 時）
                neg_rate = float(np.mean(finite < 0)) if finite.size else np.nan

            icir_results[feature] = {
                "ic_mean": ic_mean,
                "ic_std": ic_std,
                "icir": icir,
                "ic_hit_rate": hit_rate,
                "ic_neg_rate": neg_rate,
            }

        return icir_results

    def compute_ic_decay(
        self,
        features_df: pd.DataFrame,
        close: pd.Series,
        horizons: list[int],
        method: str = "spearman",
        return_type: str = "simple",
    ) -> dict[str, dict]:
        """IC Decay analysis."""

        horizon_results: dict[int, dict[str, float]] = {}
        for horizon in horizons:
            label = self._compute_returns(close, horizon, return_type)
            horizon_results[horizon] = self.compute_ic(features_df, label, method)

        results: dict[str, dict] = {}
        warning_counts: dict[str, int] = {}
        for feature in features_df.columns:
            ic_values = [horizon_results[h][feature] for h in horizons]
            decay_fit = self._fit_exponential_decay(horizons, ic_values)
            if decay_fit.get("fit_warning"):
                reason = str(decay_fit.get("fit_warning_reason") or "unknown")
                warning_counts[reason] = warning_counts.get(reason, 0) + 1
            peak_horizon = self._select_peak_horizon(horizons, ic_values)
            results[feature] = {
                "horizons": horizons,
                "ic_values": ic_values,
                "half_life": decay_fit.get("half_life"),
                "peak_horizon": peak_horizon,
                "decay_rate": decay_fit.get("decay_rate"),
                "decay_type": decay_fit.get("decay_type"),
                "fit_r2": decay_fit.get("r2"),
                "fit_warning": decay_fit.get("fit_warning"),
                "fit_warning_reason": decay_fit.get("fit_warning_reason"),
            }

        warning_total = sum(warning_counts.values())
        details = ", ".join(
            f"{reason}={count}" for reason, count in sorted(warning_counts.items())
        ) or "none"
        logger.info(
            "Decay: %d/%d fit warnings summarized (%s)",
            warning_total,
            len(features_df.columns),
            details,
        )

        return results

    def compute_grouped_ic(
        self,
        features_df: pd.DataFrame,
        label: pd.Series,
        raw_data: pd.DataFrame,
        metadata: dict,
        config: dict,
        *,
        regime_pair_counts: Optional[dict[str, dict[str, int]]] = None,
        regime_history: Optional[pd.DataFrame] = None,
        regime_keys: Optional[pd.Index] = None,
    ) -> dict[str, dict]:
        """分組 IC 分析.

        Args:
            regime_pair_counts: ICPERF Task 0.4 ㉓——呼叫端傳入空 dict 時，`by_regime` 各 regime 之逐特徵（特徵, 標籤）
                有限配對數就地寫入（`{regime: {feature: n}}`，與 `by_regime` 同一遮罩、同一對齊）；不進回傳之分組 IC
                輸出（輸出形狀不變）。None ⇒ 不計。
            regime_history: ICPERF Task 0.4 ㊳——完整連續 kline（含 ``close``，可含 ``volume``；索引為時間鍵、遞增）。給定時
                regime 指標（規則式 EMA 55／55 根波動／PIT 擴張分位門檻、K-Means 偵測）於此連續序列上只用 0..t 計算，再以
                ``regime_keys`` 取樣於分析列；未給 ⇒ 於分析列序上計算（舊行為，供無連續 kline 之呼叫端）。
            regime_keys: 與 ``features_df`` 逐列對齊之時間鍵（同 ``regime_history`` 索引之表示）；``regime_history`` 給定時必填。
        """

        grouped_results: dict[str, dict] = {}
        config = config or self._grouped_config
        method = config.get("method", self._methods[0])

        if config.get("by_volatility"):
            raise NotImplementedError(
                "by_volatility grouped is not supported in Phase 0; reserved for a later phase"
            )

        features_df, label, raw_data = self._align_with_raw_data(
            features_df, label, raw_data
        )

        if config.get("by_year"):
            by_year = {}
            for year, idx in self._iter_time_groups(raw_data, "year"):
                by_year[str(year)] = self.compute_ic(
                    features_df.loc[idx], label.loc[idx], method
                )
            grouped_results["by_year"] = by_year

        if config.get("by_quarter"):
            by_quarter = {}
            for quarter, idx in self._iter_time_groups(raw_data, "quarter"):
                by_quarter[str(quarter)] = self.compute_ic(
                    features_df.loc[idx], label.loc[idx], method
                )
            grouped_results["by_quarter"] = by_quarter

        if config.get("by_regime"):
            grouped_results["by_regime"] = self._compute_regime_groups(
                features_df, label, raw_data, config,
                pair_counts=regime_pair_counts,
                history=regime_history, keys=regime_keys,
            )

        if config.get("by_category"):
            grouped_results["by_category"] = self._compute_metadata_groups(
                features_df, label, metadata, "category", method
            )

        if config.get("by_data_source"):
            grouped_results["by_data_source"] = self._compute_metadata_groups(
                features_df, label, metadata, "data_source", method
            )

        if config.get("by_layer"):
            grouped_results["by_layer"] = self._compute_metadata_groups(
                features_df, label, metadata, "layer", method
            )

        return grouped_results

    def compute_ic_autocorrelation(
        self, rolling_ic_results: dict, lag: int = 1
    ) -> dict[str, float]:
        """IC autocorrelation (Lag-1)."""

        results: dict[str, float] = {}
        persistent_count = 0
        for feature, windows in rolling_ic_results.items():
            series = self._select_icir_series(windows)
            values = np.array(series, dtype=float)
            if values.size <= lag:
                results[feature] = np.nan
                continue
            if np.nanstd(values) == 0:
                results[feature] = np.nan
                continue
            value = float(np.corrcoef(values[:-lag], values[lag:])[0, 1])
            if value > 0.3:
                persistent_count += 1
            results[feature] = value
        if persistent_count > 0:
            logger.info("IC autocorr persistent: count=%s", persistent_count)
        return results

    @staticmethod
    def _validate_selection_metadata(
        label_horizon: Optional[str],
        selection_window: Optional[Dict[str, Any]],
        split_id: Optional[str],
    ) -> None:
        if not label_horizon:
            raise ValueError("label_horizon is required for IC selection metadata")
        if not selection_window and not split_id:
            raise ValueError("selection_window or split_id is required for IC selection metadata")

    @staticmethod
    def _build_ic_params(
        method: str,
        ic_threshold: float,
        allow_partial_ic: bool,
        label_horizon: Optional[str],
        selection_window: Optional[Dict[str, Any]],
        split_id: Optional[str],
        overrides: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "method": method,
            "ic_threshold": ic_threshold,
            "allow_partial_ic": allow_partial_ic,
            "label_horizon": label_horizon,
            "selection_window": selection_window,
            "split_id": split_id,
        }
        if overrides:
            params.update(overrides)
            params["method"] = method
            params["ic_threshold"] = ic_threshold
            params["allow_partial_ic"] = allow_partial_ic
            params["label_horizon"] = label_horizon
            params["selection_window"] = selection_window
            params["split_id"] = split_id
        return params

    @staticmethod
    def _validate_l7_raw_manifest(
        manifest: Dict[str, Any],
        symbol: str,
        tf: str,
        config_hash: str,
        *,
        allow_partial_ic: bool = False,
    ) -> Dict[str, Any]:
        assert_consumer_run_status(
            manifest,
            consumer="strict",
            allow_partial=allow_partial_ic,
            error_type=ICReadError,
        )
        if not manifest.get("complete"):
            raise ICReadError("L7 raw manifest is incomplete")
        if str(manifest.get("symbol")) != str(symbol):
            raise ICReadError("L7 raw manifest symbol mismatch")
        if str(manifest.get("tf")) != str(tf):
            raise ICReadError("L7 raw manifest timeframe mismatch")
        if str(manifest.get("config_hash")) != str(config_hash):
            raise ICReadError("L7 raw manifest config_hash mismatch")

        artifacts = manifest.get("artifacts", {})
        raw_artifact = artifacts.get("raw")
        if not isinstance(raw_artifact, dict):
            raise ICReadError("L7 raw artifact is missing")
        if not raw_artifact.get("complete"):
            raise ICReadError("L7 raw artifact is incomplete")

        groups = raw_artifact.get("groups", {})
        total_features = int(raw_artifact.get("total_features") or 0)
        if not groups or total_features <= 0:
            raise ICReadError("L7 raw artifact is empty; fail closed")
        return raw_artifact

    def _iter_l7_raw_group_paths(
        self,
        base_dir: Path,
        raw_artifact: Dict[str, Any],
    ) -> List[Tuple[str, Path]]:
        group_paths: List[Tuple[str, Path]] = []
        groups = raw_artifact.get("groups", {})
        for group_name in sorted(groups):
            group_info = groups[group_name]
            raw_path = group_info.get("path") or group_info.get("file")
            group_paths.append((group_name, self._resolve_manifest_path(base_dir, raw_path)))
        return group_paths

    @staticmethod
    def _resolve_manifest_path(base_dir: Path, raw_path: Optional[str]) -> Path:
        if not raw_path:
            raise ICReadError("L7 raw group path is missing")
        relative_path = Path(str(raw_path))
        if relative_path.is_absolute() or ".." in relative_path.parts:
            raise ICReadError(f"Unsafe L7 raw group path: {raw_path}")
        return base_dir / relative_path

    def _compute_l7_raw_group_ic(
        self,
        group_df: pd.DataFrame,
        label: pd.Series,
        method: str,
        selection_window: Optional[Dict[str, Any]],
    ) -> Dict[str, float]:
        numeric_df = group_df.select_dtypes(include=[np.number]).copy()
        if numeric_df.empty:
            return {}

        aligned_label = self._align_label_to_group(label, numeric_df)
        numeric_df, aligned_label = self._apply_selection_window(
            numeric_df,
            aligned_label,
            selection_window,
        )
        if numeric_df.empty or len(numeric_df) < 2:
            return {str(column): np.nan for column in numeric_df.columns}
        return self.compute_ic(numeric_df, aligned_label, method=method)

    POSITIONAL_SELECTION_KEYS = ("start_pos", "end_pos", "start_index", "end_index")

    @staticmethod
    def _reject_positional_selection(selection_window: Optional[Dict[str, Any]]) -> None:
        """ICFIRSTALIGN Task 1.1：選窗只收時間戳；位置鍵（含與時間鍵混用）⇒ ValueError。"""
        if not selection_window:
            return
        found = [key for key in ICEngine.POSITIONAL_SELECTION_KEYS if key in selection_window]
        if found:
            raise ValueError(
                f"selection_window 不接受位置鍵 {found}；請以時間戳 start／end 指定（位置對齊會錯位）"
            )

    @staticmethod
    def _request_identity(
        *,
        symbol: str,
        tf: str,
        config_hash: str,
        method: str,
        label_horizon: Optional[str],
        selection_window: Optional[Dict[str, Any]],
        split_id: Optional[str],
        row_index: Optional[pd.DatetimeIndex],
        label: pd.Series,
        content_sha256: Optional[str],
        raw_node: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        """本次請求之計算身分（Task 1.4）：選窗起訖正規化為 UTC epoch 秒；特徵軸與 label 以指紋表示。
        FFDSTAR Task 2.3：`content_sha256`＝manifest raw 節點之 run 內容身分（缺 ⇒ None，沿用時拒用）。
        NUMVIEW Task 4.2：`algorithm_id`、`route_identity` 取自 raw 節點（鍵名讀 FeatureEngineering 契約；缺 ⇒ None）。"""
        from momentum.factories import numeric_manifest_keys

        keys = numeric_manifest_keys()
        node = raw_node or {}
        window = selection_window or {}
        return {
            "symbol": symbol,
            "tf": tf,
            "config_hash": config_hash,
            "method": method,
            "label_horizon": None if label_horizon is None else str(label_horizon),
            "selection_window_start": _window_bound(window.get("start") or window.get("start_time")),
            "selection_window_end": _window_bound(window.get("end") or window.get("end_time")),
            "split_id": split_id,
            "feature_axis_sha256": _axis_fingerprint(row_index),
            "label_sha256": label_fingerprint(label),
            "content_sha256": None if content_sha256 is None else str(content_sha256),
            "algorithm_id": None if node.get(keys["algorithm_id"]) is None else str(node[keys["algorithm_id"]]),
            "route_identity": None if node.get(keys["route_identity"]) is None else str(node[keys["route_identity"]]),
        }

    @staticmethod
    def _load_raw_row_index(feature_reader: IFeatureReader, symbol: str, tf: str,
                            config_hash: str) -> pd.DatetimeIndex:
        """raw 成品之 sidecar 時間軸；未宣告或檔案缺 ⇒ `RowIndexArtifactMissingError`。"""
        row_index = feature_reader.load_row_index_v2(symbol, tf, config_hash, artifact_kind="raw")
        if row_index is None:
            raise RowIndexArtifactMissingError(
                f"raw 成品未宣告時間軸 sidecar（{symbol}/{tf}/{config_hash}）；拒絕以位置對齊計算 IC"
            )
        return row_index

    @staticmethod
    def _attach_row_index(group_df: pd.DataFrame, row_index: pd.DatetimeIndex) -> pd.DataFrame:
        """群組讀回之 RangeIndex 換為 sidecar 時間戳；列數不符 ⇒ `RowIndexLengthMismatchError`。"""
        if len(group_df) != len(row_index):
            raise RowIndexLengthMismatchError(
                f"L7 raw 群組列數 {len(group_df)} 與 sidecar 列數 {len(row_index)} 不符"
            )
        return group_df.set_axis(row_index, axis=0)

    @staticmethod
    def _align_label_to_group(label: pd.Series, group_df: pd.DataFrame) -> pd.Series:
        """label 只能與群組同一時間戳索引，或為群組索引之超集（依時間戳取子集）；其餘一律拒用。

        ICFIRSTALIGN Task 1.1：刪除不等長時之 `reindex` 靜默 NaN 分支（時間戳無交集時曾產出全 NaN 之 IC）。
        """
        label_series = label if isinstance(label, pd.Series) else pd.Series(label)
        label_name = label_series.name or "label"
        if label_series.index.equals(group_df.index):
            return label_series.rename(label_name)
        if (
            label_series.index.is_unique
            and bool(group_df.index.isin(label_series.index).all())
        ):
            return label_series.reindex(group_df.index).rename(label_name)
        raise AlignmentViolationError(
            "label 時間戳未涵蓋群組時間戳（非同一索引、亦非其超集）；拒絕位置或部分對齊"
        )

    @staticmethod
    def _apply_selection_window(
        features_df: pd.DataFrame,
        label: pd.Series,
        selection_window: Optional[Dict[str, Any]],
    ) -> Tuple[pd.DataFrame, pd.Series]:
        if not selection_window:
            return features_df, label

        start_value = selection_window.get("start") or selection_window.get("start_time")
        end_value = selection_window.get("end") or selection_window.get("end_time")
        if start_value is None and end_value is None:
            return features_df, label

        index = features_df.index
        mask = pd.Series(True, index=index)
        if isinstance(index, pd.DatetimeIndex):
            if start_value is not None:
                mask &= index >= pd.Timestamp(start_value)
            if end_value is not None:
                mask &= index <= pd.Timestamp(end_value)
        else:
            if start_value is not None:
                mask &= index >= start_value
            if end_value is not None:
                mask &= index <= end_value
        return features_df.loc[mask.to_numpy()], label.loc[mask.to_numpy()]

    @staticmethod
    def _passes_ic_threshold(ic_value: float, ic_threshold: float) -> bool:
        try:
            numeric_value = float(ic_value)
        except (TypeError, ValueError):
            return False
        return bool(np.isfinite(numeric_value) and abs(numeric_value) >= ic_threshold)

    @staticmethod
    def _build_data_fingerprint(
        symbol: str,
        tf: str,
        config_hash: str,
        manifest: Dict[str, Any],
        raw_artifact: Dict[str, Any],
        ic_params: Dict[str, Any],
    ) -> Dict[str, Any]:
        # FFDSTAR Task 2.3：`source_checksum` 來源＝manifest raw 節點之 `content_sha256`（manifest 無 `source_checksum` 鍵；
        # 改前讀不存在之鍵恆為 None）
        source_checksum = raw_artifact.get("content_sha256")
        hdf5_metadata = manifest.get("hdf5_metadata") or manifest.get("source_metadata")
        source_run_status = effective_run_status(manifest)
        fingerprint: Dict[str, Any] = {
            "symbol": symbol,
            "tf": tf,
            "source_run_status": source_run_status,
            "time_range": raw_artifact.get("time_range") or manifest.get("time_range"),
            "row_count": raw_artifact.get("row_count") or manifest.get("row_count"),
            "source_checksum": source_checksum,
            "hdf5_metadata": hdf5_metadata,
            "feature_schema_hash": raw_artifact.get("feature_schema_hash") or manifest.get("feature_schema_hash"),
            "config_hash": config_hash,
            "algorithm_versions": {
                "ic_engine": "ic_first_raw_v1",
                "schema_version": raw_artifact.get("schema_version"),
                "l65_algorithm_versions": manifest.get("algorithm_versions"),
            },
            "ic_params": ic_params,
            "label_horizon": ic_params.get("label_horizon"),
            "selection_window": ic_params.get("selection_window"),
            "split_id": ic_params.get("split_id"),
        }
        missing_required_fields = [
            key
            for key in (
                "symbol",
                "tf",
                "time_range",
                "row_count",
                "feature_schema_hash",
                "config_hash",
                "algorithm_versions",
                "ic_params",
                "label_horizon",
            )
            if fingerprint.get(key) in (None, "", {}, [])
        ]
        if source_checksum in (None, "") and hdf5_metadata in (None, {}, ""):
            missing_required_fields.append("source_checksum_or_hdf5_metadata")
        if not fingerprint.get("selection_window") and not fingerprint.get("split_id"):
            missing_required_fields.append("selection_window_or_split_id")
        fingerprint["missing_required_fields"] = sorted(set(missing_required_fields))
        fingerprint["cache_valid"] = not bool(missing_required_fields)
        fingerprint["cache_status"] = "recomputed"
        return fingerprint

    def _try_reuse_cached_ic_scores(
        self,
        selected_path: Path,
        symbol: str,
        tf: str,
        config_hash: str,
        label: pd.Series,
        merged_ic_params: Dict[str, Any],
        resolved_threshold: float,
        allow_partial_ic: bool = False,
        request_identity: Optional[Dict[str, Any]] = None,
    ) -> Optional["ICSelectionResult"]:
        """Re-apply a new IC threshold using previously cached IC scores.

        Called when raw/ has been deleted (cleanup_raw=True) but the JSON cache
        written by an earlier pipeline run still exists.

        ICFIRSTALIGN Task 1.4：只容 threshold 不同——`CACHE_IDENTITY_FIELDS` 之每一欄（symbol、tf、config_hash、
        方法、label_horizon、選窗起訖〔UTC〕、split_id、特徵軸指紋、label 指紋）須於 cache 內存在且與本次請求
        完全相等（不以容差、不以有效列數代替值指紋）；任一缺或不同 ⇒ 拒用（回 None）。

        Returns ICSelectionResult on cache hit, None on cache miss.
        """
        try:
            with selected_path.open("r", encoding="utf-8") as fh:
                cached = json.load(fh)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            logger.warning("[IC-First] cache read failed, raw/ required: %s", exc)
            return None

        cached_ic_scores: Dict[str, float] = cached.get("ic_scores") or {}
        if not cached_ic_scores:
            logger.warning("[IC-First] cached ic_scores empty — raw/ required")
            return None

        fp: Dict[str, Any] = cached.get("data_fingerprint") or {}

        # Validate full computation identity (NOT ic_threshold — threshold is allowed to change).
        if request_identity is None:
            logger.warning("[IC-First] no request identity supplied — raw/ required")
            return None
        for field in CACHE_IDENTITY_FIELDS:
            if field not in fp or field not in request_identity:
                logger.warning("[IC-First] cache fingerprint lacks identity field %s — raw/ required", field)
                return None
            if request_identity[field] is None and field in _IDENTITY_FIELDS_REQUIRED_NON_NULL:
                logger.warning("[IC-First] identity field %s unavailable — raw/ required", field)
                return None
            if fp[field] != request_identity[field]:
                logger.warning("[IC-First] cache identity mismatch on %s — raw/ required", field)
                return None

        source_run_status = (
            fp.get("source_run_status")
            or cached.get("source_run_status")
            or cached.get("run_status")
        )
        if not is_source_run_status_reusable(
            str(source_run_status) if source_run_status is not None else None,
            allow_partial=allow_partial_ic,
        ):
            logger.warning(
                "[IC-First] cached source_run_status=%r not reusable — raw/ required",
                source_run_status,
            )
            return None

        quality_status = cached.get("quality_status")
        if quality_status is None:
            quality_status = "unknown"
        if quality_status not in ("complete", "partial"):
            logger.warning(
                "[IC-First] cached quality_status=%r not reusable — raw/ required",
                quality_status,
            )
            return None
        if quality_status == "partial" and not allow_partial_ic:
            logger.warning(
                "[IC-First] cached partial quality_status without allow_partial_ic — raw/ required"
            )
            return None

        # Apply new threshold to cached IC scores.
        selected = [
            feature
            for feature, ic_value in cached_ic_scores.items()
            if self._passes_ic_threshold(ic_value, resolved_threshold)
        ]

        # Build updated fingerprint preserving all original data fields.
        new_fingerprint: Dict[str, Any] = {k: v for k, v in fp.items() if k != "cache_status"}
        new_fingerprint["cache_status"] = "reused_from_cache"
        new_fingerprint["ic_params"] = merged_ic_params

        skipped_groups: List[str] = cached.get("skipped_groups") or []
        total_features = cached.get("total_features") or len(cached_ic_scores)
        group_count: int = int(cached.get("group_count", 0))

        payload = self._write_ic_selected_json_atomic(
            output_path=selected_path,
            symbol=symbol,
            tf=tf,
            config_hash=config_hash,
            selected=selected,
            ic_scores=cached_ic_scores,
            data_fingerprint=new_fingerprint,
            ic_params=merged_ic_params,
            skipped_groups=skipped_groups,
            quality_status=quality_status,
        )
        logger.info(
            "[IC-First] cache hit: reused %d IC scores, selected=%d "
            "at threshold=%.4f (raw/ cleaned up, no parquet reads needed)",
            len(cached_ic_scores),
            len(selected),
            resolved_threshold,
        )
        return ICSelectionResult(
            symbol=symbol,
            tf=tf,
            config_hash=config_hash,
            selected=selected,
            ic_scores=cached_ic_scores,
            skipped_groups=skipped_groups,
            quality_status=quality_status,
            selected_path=str(payload["selected_path"]),
            data_fingerprint=new_fingerprint,
            ic_params=merged_ic_params,
            group_count=group_count,
            total_features=int(total_features),
            frozen_gate_eligible=quality_status == "complete",
        )

    def _write_ic_selected_json_atomic(
        self,
        output_path: Path,
        symbol: str,
        tf: str,
        config_hash: str,
        selected: List[str],
        ic_scores: Dict[str, float],
        data_fingerprint: Dict[str, Any],
        ic_params: Dict[str, Any],
        skipped_groups: List[str],
        quality_status: str,
    ) -> Dict[str, Any]:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        payload: Dict[str, Any] = {
            "schema_version": "ic_selected_v1",
            "complete": True,
            "symbol": symbol,
            "tf": tf,
            "timeframe": tf,
            "config_hash": config_hash,
            "selected": selected,
            "selected_count": len(selected),
            "ic_scores": ic_scores,
            "skipped_groups": skipped_groups,
            "quality_status": quality_status,
            "source_run_status": data_fingerprint.get("source_run_status"),
            "frozen_gate_eligible": quality_status == "complete",
            "data_fingerprint": data_fingerprint,
            "ic_params": ic_params,
            "selected_path": str(output_path),
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        safe_payload = self._json_safe(payload)
        temp_path = output_path.with_name(f".{output_path.name}.tmp")
        try:
            with temp_path.open("w", encoding="utf-8") as selected_file:
                json.dump(safe_payload, selected_file, ensure_ascii=False, indent=2, allow_nan=False)
            os.replace(temp_path, output_path)
        finally:
            if temp_path.exists():
                temp_path.unlink()
        return safe_payload

    def _json_safe(self, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, float):
            return value if np.isfinite(value) else None
        if isinstance(value, (str, int, bool)):
            return value
        if isinstance(value, np.generic):
            return self._json_safe(value.item())
        if isinstance(value, Path):
            return str(value)
        if isinstance(value, dict):
            return {str(key): self._json_safe(item) for key, item in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [self._json_safe(item) for item in value]
        if hasattr(value, "isoformat"):
            try:
                return value.isoformat()
            except Exception:
                pass
        return str(value)

    @staticmethod
    def _fit_exponential_decay(
        horizons: list[int], ic_values: list[float]
    ) -> dict:
        """Fit IC(h) = A * exp(-lambda * h) + C."""

        x = np.array(horizons, dtype=float)
        y = np.array(ic_values, dtype=float)
        mask = np.isfinite(x) & np.isfinite(y)
        x = x[mask]
        y = y[mask]

        if x.size < 3:
            return {
                "decay_rate": np.nan,
                "half_life": np.nan,
                "decay_type": "fit_failed",
                "r2": np.nan,
                "fit_warning": True,
                "fit_warning_reason": "insufficient_points",
            }

        if np.nanstd(y) < 1e-8:
            return {
                "decay_rate": np.nan,
                "half_life": np.nan,
                "decay_type": "fit_failed",
                "r2": np.nan,
                "fit_warning": True,
                "fit_warning_reason": "low_variance",
            }

        def model(h, a, lam, c):
            return a * np.exp(-lam * h) + c

        # ICPERF Task 0.4 ③：固定起點集合逐一擬合、取殘差平方和最小者（單一預設起點會落入較差之局部解）
        starts = (None, [y[0], 1.0, 0.0], [y[0], 0.1, 0.0], [y[0] - y[-1], 0.5, y[-1]])
        best_params = None
        best_ss_res = np.inf
        for p0 in starts:
            try:
                cand, _ = optimize.curve_fit(model, x, y, p0=p0, maxfev=20000)
            except Exception:
                continue
            cand_ss_res = float(np.sum((y - model(x, *cand)) ** 2))
            if np.isfinite(cand_ss_res) and cand_ss_res < best_ss_res:
                best_params, best_ss_res = cand, cand_ss_res

        try:
            if best_params is None:
                raise RuntimeError("all decay fit starts failed")
            a, lam, c = best_params
            ss_res = best_ss_res
            ss_tot = float(np.sum((y - np.mean(y)) ** 2))
            r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
            decay_type = "exponential" if r2 >= 0.5 else "non_exponential"
            fit_warning = decay_type != "exponential"
            fit_warning_reason = "low_r2" if fit_warning else None
            half_life = float(np.log(2) / lam) if lam > 0 else np.nan
            return {
                "decay_rate": float(lam),
                "half_life": half_life,
                "decay_type": decay_type,
                "r2": float(r2),
                "fit_warning": fit_warning,
                "fit_warning_reason": fit_warning_reason,
            }
        except Exception:
            return {
                "decay_rate": np.nan,
                "half_life": np.nan,
                "decay_type": "fit_failed",
                "r2": np.nan,
                "fit_warning": True,
                "fit_warning_reason": "fit_exception",
            }

    def _compute_pairwise_corr(
        self, series: pd.Series, label: pd.Series, method: str
    ) -> float:
        # ICPERF Task 0.4 ㊴（r55 群集 C）：非有限值（NaN、±inf）一律視為缺值（同 alphalens get_clean_factor 之
        # np.isfinite 過濾、同本模組滾動 IC 之有限值遮罩）；dropna 會保留 ±inf
        aligned = pd.concat([series, label], axis=1)
        aligned = aligned[np.isfinite(aligned.to_numpy(dtype=np.float64)).all(axis=1)]
        if aligned.empty:
            return np.nan

        x = aligned.iloc[:, 0]
        y = aligned.iloc[:, 1]
        if np.nanstd(x) == 0 or np.nanstd(y) == 0:
            return np.nan
        if method == "pearson":
            return float(stats.pearsonr(x, y)[0])
        if method == "kendall":
            return float(stats.kendalltau(x, y)[0])
        if method != "spearman":
            logger.warning("Unknown IC method=%s, fallback to spearman", method)
        return float(stats.spearmanr(x, y)[0])

    def _compute_returns(
        self,
        close: pd.Series,
        horizon: int,
        return_type: str,
        benchmark_close: Optional[pd.Series] = None,
    ) -> pd.Series:
        """與 orch / LabelGenerator 同源 dispatch（禁 silent 回退 simple）。

        行為表（engine == orch/LG，atol 數值路徑）::

            return_type     | 行為
            ----------------|------------------------------------------
            simple          | LabelGenerator.generate_return
            log             | LabelGenerator.generate_log_return
            excess          | LabelGenerator.generate_excess_return
                            | （缺 benchmark_close → ValueError，兩路徑同）
            risk_adjusted   | LabelGenerator.generate_risk_adjusted_return
            winsorized      | NotImplementedError LOOKAHEAD_LABEL_UNSUPPORTED
            other           | ValueError Unsupported return_type（禁 silent simple）
        """
        from momentum.factories import create_label_generator

        return create_label_generator().generate_returns_by_type(
            close,
            horizon,
            return_type,
            benchmark_close=benchmark_close,
        )

    def _adjusted_icir_window(self) -> int:
        """ICPERF Task 0.4 ㉛：ICIR 窗依週期換算（與滾動窗同一 `_adjust_rolling_windows`；未注入週期 ⇒ 設定值原值）。"""
        return int(self._adjust_rolling_windows([int(self._icir_window)])[0])

    def icir_window_selection(self, windows: list[int]) -> dict[str, Any]:
        """ICPERF Task 0.4 ㉛：ICIR 選窗之揭露——設定窗、換算後之窗與其滾動 IC 鍵，以及來源
        （`rolling_windows`＝換算後之滾動窗集合已含；`extra_window`＝不在其中、由 `compute_rolling_ic` 另算）。"""
        adjusted = [int(w) for w in self._adjust_rolling_windows(list(windows))]
        icir_window = self._adjusted_icir_window()
        return {
            "configured_window": int(self._icir_window),
            "adjusted_window": icir_window,
            "key": f"window_{icir_window}",
            "source": "rolling_windows" if icir_window in adjusted else "extra_window",
        }

    def _select_icir_series(self, windows: dict) -> list[float]:
        """ICIR／IC 自相關所用之滾動 IC 序列＝換算後 ICIR 窗之鍵；無該鍵 ⇒ 空序列（ICIR NaN），不退回其他窗
        （ICPERF Task 0.4 ㉛：舊版以設定值原值找鍵、找不到即取第一個窗 ⇒ 1h／4h 之 ICIR 實為最短窗）。"""
        if not windows:
            return []
        return list(windows.get(f"window_{self._adjusted_icir_window()}", []))

    def _warn_missing_icir_window(self, rolling_ic_results: dict) -> None:
        """有特徵之滾動結果非空卻缺 ICIR 窗之鍵 ⇒ 記一次警告（逐特徵迴圈外；ICIR 為 NaN、不退回其他窗）。"""
        key = f"window_{self._adjusted_icir_window()}"
        missing = sum(1 for windows in rolling_ic_results.values() if windows and key not in windows)
        if missing:
            logger.warning("ICIR window %s missing in rolling IC for %d features; ICIR set to NaN (no fallback)",
                           key, missing)

    def _iter_time_groups(self, raw_data: pd.DataFrame, mode: str):
        time_index = self._get_time_index(raw_data)
        if time_index is None:
            return []
        time_series = pd.Series(time_index, index=raw_data.index)
        if mode == "year":
            groups = time_series.groupby(time_series.dt.year).groups
            return [(key, idx) for key, idx in groups.items()]
        groups = time_series.groupby([time_series.dt.year, time_series.dt.quarter]).groups
        return [(f"{key[0]}Q{key[1]}", idx) for key, idx in groups.items()]

    def _get_time_index(self, raw_data: pd.DataFrame) -> Optional[pd.DatetimeIndex]:
        if isinstance(raw_data.index, pd.DatetimeIndex):
            return raw_data.index
        for col in ("open_time", "close_time", "timestamp"):
            if col in raw_data.columns:
                values = raw_data[col]
                if np.issubdtype(values.dtype, np.number):
                    if values.isna().any():
                        raise ValueError(f"timestamp column {col} contains NaN values")
                    max_abs = float(np.nanmax(np.abs(values.to_numpy(dtype=float))))
                    if max_abs >= 1e15:
                        raise ValueError(
                            f"timestamp column {col} has unsupported magnitude: {max_abs:g}"
                        )
                    unit = "ms" if max_abs >= 1e12 else "s"
                    parsed = pd.DatetimeIndex(
                        pd.to_datetime(values.to_numpy(), unit=unit, errors="raise")
                    )
                else:
                    parsed = pd.DatetimeIndex(pd.to_datetime(values, errors="raise"))
                years = parsed.year
                current_year = pd.Timestamp.utcnow().year
                if len(years) and (int(years.min()) < 1990 or int(years.max()) > current_year + 1):
                    raise ValueError(
                        f"timestamp column {col} produced implausible years: "
                        f"{int(years.min())}-{int(years.max())}"
                    )
                return parsed
        return None

    def _compute_regime_groups(
        self,
        features_df: pd.DataFrame,
        label: pd.Series,
        raw_data: pd.DataFrame,
        config: dict,
        pair_counts: Optional[dict[str, dict[str, int]]] = None,
        history: Optional[pd.DataFrame] = None,
        keys: Optional[pd.Index] = None,
    ) -> dict[str, dict]:
        if history is not None:
            # ICPERF Task 0.4 ㊳：regime 指標於完整連續 kline 上計算（只用 0..t），再取樣於分析列
            if keys is None or len(keys) != len(features_df):
                raise ValueError("regime_keys must align row-by-row with features_df when regime_history is given")
            if "close" not in history.columns:
                return {}
            close = history["close"]
            volume = history["volume"] if "volume" in history.columns else None
        else:
            close = raw_data.get("close")
            if close is None:
                return {}
            close = close.reindex(features_df.index)
            volume = raw_data.get("volume")
            if volume is not None:
                volume = volume.reindex(features_df.index)
            keys = None

        regime_method = config.get("regime_method", "rule")

        if regime_method == "kmeans":
            return self._compute_regime_groups_kmeans(
                features_df, label, close, volume, config,
                pair_counts=pair_counts, keys=keys,
            )

        return self._compute_regime_groups_rule(
            features_df, label, close, config, pair_counts=pair_counts, keys=keys,
        )

    @staticmethod
    def _sample_masks(masks: Mapping[str, pd.Series], keys: Optional[pd.Index],
                      index: pd.Index) -> dict[str, pd.Series]:
        """regime 遮罩取樣於分析列（ICPERF Task 0.4 ㊳）：keys 為 None ⇒ 遮罩已在分析列序上；否則依時間鍵取樣，
        鍵不在連續序列 ⇒ False（不歸任何 regime）。回傳之遮罩索引＝分析列索引。"""
        if keys is None:
            return {name: pd.Series(np.asarray(m, dtype=bool), index=index) for name, m in masks.items()}
        return {name: pd.Series(m.reindex(keys).fillna(False).to_numpy(dtype=bool), index=index)
                for name, m in masks.items()}

    #: 有限配對數逐欄塊之欄數（只限峰值記憶體：每塊 n_rows × 本值之 bool 暫存）
    _PAIR_COUNT_COL_BLOCK = 512

    @classmethod
    def _regime_finite_pair_counts(
        cls,
        features_df: pd.DataFrame,
        label: pd.Series,
        masks: Mapping[str, np.ndarray],
    ) -> dict[str, dict[str, int]]:
        """ICPERF Task 0.4 ㉓：各 regime 逐特徵之（特徵, 標籤）兩者皆有限之列數。

        masks 為與 ``features_df`` 列位置對齊之 bool 陣列（同 `by_regime` 取列之遮罩）；標籤依特徵索引對齊（同
        ``compute_ic`` 之 ``label.loc[idx]``）。逐欄塊計算，峰值暫存＝n_rows × ``_PAIR_COUNT_COL_BLOCK`` bool。
        """
        columns = list(features_df.columns)
        y_ok = np.isfinite(label.reindex(features_df.index).to_numpy(dtype=np.float64))
        rows = {name: np.asarray(m, dtype=bool) & y_ok for name, m in masks.items()}
        out: dict[str, dict[str, int]] = {name: {} for name in masks}
        for start in range(0, len(columns), cls._PAIR_COUNT_COL_BLOCK):
            block = columns[start:start + cls._PAIR_COUNT_COL_BLOCK]
            finite = np.isfinite(features_df[block].to_numpy(dtype=np.float64))
            for name, row_mask in rows.items():
                counts = finite[row_mask].sum(axis=0)
                out[name].update(zip(block, (int(c) for c in counts)))
        return out

    @staticmethod
    def _parse_regime_vol_percentiles(regime_defs: dict) -> tuple[float, float]:
        """解析並驗界 regime high/low vol percent（config 語意=percent，非 fraction）。

        非 finite / 非 numeric / 越界 / 反序 → InvalidInputError（禁漏 TypeError/ValueError）。
        合法預設 20/80 → lo_q=0.2, hi_q=0.8。
        """
        raw_high = regime_defs.get("high_vol_percentile", 80)
        raw_low = regime_defs.get("low_vol_percentile", 20)

        def _to_finite_float(raw: object, name: str) -> float:
            if raw is None:
                raise InvalidInputError(
                    f"regime_definitions.{name} must be finite numeric, got None"
                )
            try:
                val = float(raw)
            except (TypeError, ValueError) as exc:
                raise InvalidInputError(
                    f"regime_definitions.{name} must be finite numeric, got {raw!r}"
                ) from exc
            if not np.isfinite(val):
                raise InvalidInputError(
                    f"regime_definitions.{name} must be finite numeric, got {raw!r}"
                )
            return float(val)

        high_pct = _to_finite_float(raw_high, "high_vol_percentile")
        low_pct = _to_finite_float(raw_low, "low_vol_percentile")
        # 0 ≤ low_pct < high_pct ≤ 100
        if low_pct < 0 or high_pct > 100 or low_pct >= high_pct:
            raise InvalidInputError(
                f"regime_definitions percentiles invalid: "
                f"require 0 <= low_vol_percentile < high_vol_percentile <= 100, "
                f"got low={low_pct}, high={high_pct}"
            )
        return low_pct, high_pct

    def _build_regime_rule_masks(
        self,
        close: pd.Series,
        config: dict,
    ) -> dict[str, pd.Series] | None:
        """產線 rule mask 建構（PIT high/low + EMA bull/bear）。

        Returns:
            masks dict，或空 vol 時 ``None``（caller 對應 return {{}}）。
        """
        ema_55 = close.ewm(span=55, adjust=False).mean()
        vol = close.pct_change(fill_method=None).rolling(55).std()

        regime_defs = config.get("regime_definitions", {}) or {}
        low_pct, high_pct = self._parse_regime_vol_percentiles(regime_defs)

        # 空 vol guard 保留（Opt-A legacy：len(close)<55 等 → by_regime={}）
        vol_values = vol.dropna()
        if vol_values.empty:
            return None

        lo_q = low_pct / 100.0
        hi_q = high_pct / 100.0
        lo_t, hi_t = pit_expanding_quantile_thresholds(
            vol, lo_q=lo_q, hi_q=hi_q, min_samples=100
        )

        return {
            "bull": (close > ema_55).fillna(False),
            "bear": (close < ema_55).fillna(False),
            "high_vol": (vol >= hi_t).fillna(False),
            "low_vol": (vol <= lo_t).fillna(False),
        }

    def _compute_regime_groups_rule(
        self,
        features_df: pd.DataFrame,
        label: pd.Series,
        close: pd.Series,
        config: dict,
        pair_counts: Optional[dict[str, dict[str, int]]] = None,
        keys: Optional[pd.Index] = None,
    ) -> dict[str, dict]:
        """規則式 regime 分組（bull/bear/high_vol/low_vol）。

        high/low vol 門檻為 per-t expanding PIT（LA-1 P1-1）；
        bull/bear 維持 EMA 因果規則不變。pair_counts 見 ``compute_grouped_ic``；keys 非 None ⇒ ``close`` 為完整連續
        序列，遮罩算完再取樣於分析列（ICPERF Task 0.4 ㊳）。
        """
        masks = self._build_regime_rule_masks(close, config)
        if masks is None:
            return {}
        masks = self._sample_masks(masks, keys, features_df.index)

        if pair_counts is not None:
            pair_counts.update(self._regime_finite_pair_counts(
                features_df, label,
                {name: mask.to_numpy(dtype=bool) for name, mask in masks.items()},
            ))
        results: dict[str, dict] = {}
        method = config.get("method", self._methods[0])
        for name, mask in masks.items():
            idx = mask[mask].index
            if len(idx) == 0:
                results[name] = {}
                continue
            results[name] = self.compute_ic(
                features_df.loc[idx], label.loc[idx], method
            )
        return results

    def _compute_regime_groups_kmeans(
        self,
        features_df: pd.DataFrame,
        label: pd.Series,
        close: pd.Series,
        volume: Optional[pd.Series],
        config: dict,
        pair_counts: Optional[dict[str, dict[str, int]]] = None,
        keys: Optional[pd.Index] = None,
    ) -> dict[str, dict]:
        """K-Means 無監督 regime 分組（pair_counts 見 ``compute_grouped_ic``；keys 非 None ⇒ ``close``／``volume`` 為完整
        連續序列，偵測後取樣於分析列，ICPERF Task 0.4 ㊳）。"""
        from momentum.Analysis.regime_detector import RegimeDetector

        kmeans_cfg = config.get("regime_kmeans", {})
        n_clusters = kmeans_cfg.get("n_clusters", 4)
        lookback = kmeans_cfg.get("lookback", 55)
        min_samples = kmeans_cfg.get("min_samples_for_fit", 100)
        refit_interval = kmeans_cfg.get("refit_interval", 50)

        detector = RegimeDetector(
            n_clusters=n_clusters,
            lookback=lookback,
            min_samples_for_fit=min_samples,
            refit_interval=refit_interval,
        )
        # LA-2 B3：detect 固定 PIT Segment-causal（expanding/_fit_global 已移除）
        detection = detector.detect(close, volume)

        results: dict[str, dict] = {}
        method = config.get("method", self._methods[0])
        # 名稱依字串序（set 之迭代序隨字串雜湊種子而變 ⇒ 輸出鍵序不可重現）
        labels = np.asarray(detection.labels, dtype=object)
        if keys is not None:
            # 完整連續序列之逐根標籤取樣於分析列（鍵不在序列 ⇒ 不歸任何 regime）
            labels = pd.Series(labels[:len(close)], index=close.index[:len(labels)]).reindex(keys).to_numpy(dtype=object)
        regime_names = sorted(
            str(name) for name in set(labels)
            if isinstance(name, str) and name and name != "unknown"
        )
        if pair_counts is not None:
            pair_counts.update(self._regime_finite_pair_counts(
                features_df, label,
                {name: (labels == name)[:len(features_df)] for name in regime_names},
            ))
        for regime_name in regime_names:
            mask = labels == regime_name
            idx = features_df.index[mask[:len(features_df)]]
            if len(idx) == 0:
                results[regime_name] = {}
                continue
            results[regime_name] = self.compute_ic(
                features_df.loc[idx], label.loc[idx], method
            )
        return results

    def _compute_metadata_groups(
        self,
        features_df: pd.DataFrame,
        label: pd.Series,
        metadata: dict,
        key: str,
        method: str,
    ) -> dict[str, dict]:
        if not metadata:
            return {}
        group_map: dict[str, list[str]] = {}
        for feature in features_df.columns:
            meta = metadata.get(feature, {})
            value = meta.get(key)
            if value is None:
                continue
            group_map.setdefault(str(value), []).append(feature)

        results: dict[str, dict] = {}
        for group, features in group_map.items():
            results[group] = self.compute_ic(
                features_df[features], label, method
            )
        return results

    def _align_with_raw_data(
        self,
        features_df: pd.DataFrame,
        label: pd.Series,
        raw_data: pd.DataFrame,
    ) -> tuple[pd.DataFrame, pd.Series, pd.DataFrame]:
        if raw_data is None or raw_data.empty:
            return features_df, label, raw_data

        if (
            features_df.index.equals(raw_data.index)
            and label.index.equals(raw_data.index)
        ):
            return features_df, label, raw_data

        if len(features_df) == len(raw_data):
            features_df = features_df.copy()
            label = label.copy()
            features_df.index = raw_data.index
            label.index = raw_data.index
        else:
            raw_data = raw_data.reindex(features_df.index)

        return features_df, label, raw_data

    def _compute_vectorized_ic(
        self, features_df: pd.DataFrame, label: pd.Series, method: str
    ) -> dict[str, float]:
        if features_df.shape[0] < 2:
            return {feature: np.nan for feature in features_df.columns}
        if features_df.shape[1] == 1:
            feature = features_df.columns[0]
            value = self._compute_pairwise_corr(
                features_df[feature], label, method
            )
            return {feature: value}
        # ICPERF Task 0.4 ㉚：常數標籤 ⇒ 全欄 NaN；常數特徵 ⇒ 該欄 NaN 並自矩陣剔除（scipy.spearmanr 於第 0／1 欄常數時
        # 回純量 NaN、使 `corr[0, 1:]` 拋 TypeError，且會把他欄一併變 NaN）；相關矩陣一律二維（純量 ⇒ 2×2）。
        # 無常數欄時與改前同一計算（同一矩陣、同一呼叫）。
        label_values = np.asarray(label.values, dtype=float)
        feature_values = np.asarray(features_df.values, dtype=float)
        ic_out = np.full(feature_values.shape[1], np.nan)
        if np.all(label_values == label_values[0]):
            return dict(zip(features_df.columns, ic_out))
        live = ~np.all(feature_values == feature_values[0], axis=0)
        if not live.any():
            return dict(zip(features_df.columns, ic_out))
        values = np.column_stack([label_values, feature_values if live.all() else feature_values[:, live]])
        if method == "pearson":
            corr = np.corrcoef(values, rowvar=False)
        else:
            corr = stats.spearmanr(values, axis=0).correlation
        corr = np.asarray(corr, dtype=float)
        if corr.ndim == 0:
            corr = np.array([[1.0, float(corr)], [float(corr), 1.0]])
        ic_out[live] = corr[0, 1:]
        return dict(zip(features_df.columns, ic_out.astype(float)))

    def _has_missing(self, features_df: pd.DataFrame, label: pd.Series) -> bool:
        """任一非有限值（NaN、±inf；ICPERF Task 0.4 ㊴）⇒ True，走逐欄有限列配對；逐欄檢查不建整表副本。"""
        if not np.isfinite(label.to_numpy(dtype=np.float64)).all():
            return True
        return any(not np.isfinite(features_df[c].to_numpy(dtype=np.float64)).all() for c in features_df.columns)

    def _adjust_rolling_windows(self, windows: list[int]) -> list[int]:
        if not self._timeframe:
            return windows

        reference = self._parse_timeframe_hours(self._reference_tf)
        current = self._parse_timeframe_hours(self._timeframe)
        if not (self._is_valid_timeframe_hours(reference) and self._is_valid_timeframe_hours(current)):
            logger.warning("Invalid timeframe for rolling windows: %s", self._timeframe)
            return windows

        factor = reference / current
        adjusted = [max(int(round(window * factor)), 1) for window in windows]
        return adjusted

    def _parse_timeframe_hours(self, timeframe: str) -> Optional[float]:
        if not timeframe:
            return None
        unit = timeframe[-1].lower()
        try:
            value = float(timeframe[:-1])
        except ValueError:
            return None
        if unit == "h":
            return value
        if unit == "d":
            return value * 24
        if unit == "w":
            return value * 168
        return None

    def _rolling_spearman(
        self,
        series: pd.Series,
        label: pd.Series,
        window: int,
        stride: int,
    ) -> list[float]:
        values = series.values
        target = label.values
        results: list[float] = []
        for end in range(window, len(values) + 1, stride):
            x = values[end - window : end]
            y = target[end - window : end]
            if np.isnan(x).any() or np.isnan(y).any():
                continue
            if np.std(x) == 0 or np.std(y) == 0:
                results.append(np.nan)
                continue
            results.append(float(stats.spearmanr(x, y)[0]))
        return results

    @staticmethod
    def _rolling_corr_matrix(
        x_values: np.ndarray,
        y_values: np.ndarray,
        window: int,
        stride: int,
    ) -> np.ndarray:
        """逐窗 Pearson（ICPERF Task 0.4 ㉘）：窗內先求均值再累加中心化動差（`_rolling_pearson_numba`）。

        舊版以原值 `cumsum(x)`／`cumsum(x²)`／`cumsum(xy)` 相減求窗內動差，價格水準欄（值大、窗內變異小）相消誤差達 1e-7；
        改後與逐窗 `scipy.stats.pearsonr` 相對誤差 ≤ 1e-12。窗內任一非有限值或常數 ⇒ 該窗該欄 NaN（同 ④）。
        """
        if window <= 1:
            return np.empty((0, x_values.shape[1]))
        if stride < 1:
            raise ValueError("stride must be >= 1")

        n_rows = x_values.shape[0]
        if n_rows < window:
            return np.empty((0, x_values.shape[1]))

        x = np.ascontiguousarray(x_values, dtype=np.float64)
        y = np.ascontiguousarray(y_values, dtype=np.float64)
        return _rolling_pearson_numba(x, y, int(window), int(stride))

    @staticmethod
    def _rolling_kendall_matrix(
        x_values: np.ndarray,
        y_values: np.ndarray,
        window: int,
        stride: int,
    ) -> np.ndarray:
        """逐窗 Kendall τ-b（ICPERF Task 0.4 ㉗；`_rolling_kendall_numba`，滑窗整數計數每步 O(window)）。
        形狀與窗終點同 `_rolling_corr_matrix`；窗內任一非有限值或常數 ⇒ NaN。"""
        if window <= 1:
            return np.empty((0, x_values.shape[1]))
        if stride < 1:
            raise ValueError("stride must be >= 1")
        n_rows = x_values.shape[0]
        if n_rows < window:
            return np.empty((0, x_values.shape[1]))
        x = np.ascontiguousarray(x_values, dtype=np.float64)
        y = np.ascontiguousarray(y_values, dtype=np.float64)
        return _rolling_kendall_numba(x, y, int(window), int(stride))

    def _select_peak_horizon(
        self, horizons: list[int], ic_values: list[float]
    ) -> int:
        values = np.array(ic_values, dtype=float)
        if np.isfinite(values).any():
            return horizons[int(np.nanargmax(np.abs(values)))]
        return horizons[0]
