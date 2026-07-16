"""Data preprocessing utilities for IC analysis.

LA-0 B4 / P0-3：fit_mode 四出口
  train_mask    — split 主幹，mask 內 fit → 全段 transform
  pit_expanding — 無 split 分析，per-t expanding PIT（pit_stats）
  full_sample   — 研究逃生，全期 fit + oos_guarantees=False 紅標
  unset         — schema default；+ fit_mask=None → fail-closed raise
"""

from __future__ import annotations

from typing import Literal, Optional

import numpy as np
import pandas as pd

from momentum.Analysis.pit_stats import (
    MIN_SAMPLES,
    PIT_STATS_VERSION,
    pit_expanding_bounds,
    pit_expanding_mad,
    pit_expanding_mean_std,
    pit_train_fit,
    pit_valid_mask,
)
from momentum.core.logging import get_logger


logger = get_logger(__name__)

FitMode = Literal["train_mask", "pit_expanding", "full_sample", "unset"]
VALID_FIT_MODES: frozenset[str] = frozenset(
    {"train_mask", "pit_expanding", "full_sample", "unset"}
)

# MAD / zscore winsor 倍率（對齊既有 _clip_series 行為）
_MAD_K = 3.5
_ZSCORE_K = 3.0


class DataPreprocessor:
    """Stage 1: 數據預處理 — Winsorization, 缺失值處理, 標準化."""

    def __init__(self, config: dict):
        self._config = config or {}

    # ------------------------------------------------------------------
    # fit_mode 解析（fail-closed）
    # ------------------------------------------------------------------
    def resolve_fit_mode(
        self,
        fit_mode: Optional[str] = None,
        fit_mask: Optional[np.ndarray] = None,
    ) -> str:
        """解析有效 fit_mode。

        - 參數優先於 config
        - unset + fit_mask=None → fail-closed raise
        - unset + fit_mask 有值 → 視為 train_mask（顯式 mask 呼叫）
        - train_mask 必須有 fit_mask
        """
        raw = fit_mode if fit_mode is not None else self._config.get("fit_mode", "unset")
        if raw is None:
            raw = "unset"
        mode = str(raw).lower().strip()
        if mode not in VALID_FIT_MODES:
            raise ValueError(
                f"Unknown fit_mode={raw!r}; "
                f"expected one of {sorted(VALID_FIT_MODES)}"
            )

        if mode == "unset":
            if fit_mask is None:
                raise ValueError(
                    "fit_mode=unset with fit_mask=None is fail-closed; "
                    "pass fit_mode in {train_mask, pit_expanding, full_sample}"
                )
            return "train_mask"

        if mode == "train_mask" and fit_mask is None:
            raise ValueError("fit_mode=train_mask requires a non-None fit_mask")

        return mode

    @staticmethod
    def _oos_guarantees_for_mode(mode: str) -> bool:
        """full_sample 研究逃生紅標；其餘生產 mode 為 True。"""
        return mode != "full_sample"

    def preprocess(
        self,
        features_df: pd.DataFrame,
        metadata: Optional[dict] = None,
        fit_mask: Optional[np.ndarray] = None,
        fit_mode: Optional[str] = None,
    ) -> tuple[pd.DataFrame, dict]:
        if features_df is None or features_df.empty:
            raise ValueError("features_df is empty")

        mode = self.resolve_fit_mode(fit_mode=fit_mode, fit_mask=fit_mask)

        log: dict = {
            "removed_features": {},
            "winsorized_features": [],
            "skipped_winsorization": [],
            "fit_mode": mode,
            "pit_stats_version": PIT_STATS_VERSION,
            "oos_guarantees": self._oos_guarantees_for_mode(mode),
            "per_bar_validity": {},
        }

        df = features_df.copy()

        winsor_cfg = self._config.get("winsorization", {})
        if winsor_cfg.get("enabled", True):
            method = winsor_cfg.get("method", "percentile")
            lower = winsor_cfg.get("lower_percentile", 1.0)
            upper = winsor_cfg.get("upper_percentile", 99.0)
            df, winsor_log = self.winsorize(
                df,
                method=method,
                lower=lower,
                upper=upper,
                metadata=metadata,
                fit_mask=fit_mask,
                fit_mode=mode,
            )
            log["winsorized_features"] = winsor_log["winsorized"]
            log["skipped_winsorization"] = winsor_log["skipped"]

        missing_cfg = self._config.get("missing_values", {})
        max_fill_forward = int(missing_cfg.get("max_fill_forward", 3))
        min_coverage = float(missing_cfg.get("min_coverage", 0.3))
        df, removed_low_coverage = self.handle_missing(
            df,
            max_fill_forward=max_fill_forward,
            min_coverage=min_coverage,
            fit_mask=fit_mask,
            fit_mode=mode,
        )
        if removed_low_coverage:
            log["removed_features"]["low_coverage"] = removed_low_coverage
        # pit_expanding：欄不 drop，validity 記在 instance 供 log
        cov_validity = getattr(self, "_last_coverage_validity", None)
        if cov_validity:
            log["per_bar_validity"]["coverage"] = cov_validity

        df, removed_constants = self.remove_constant_features(
            df, fit_mask=fit_mask, fit_mode=mode
        )
        if removed_constants:
            log["removed_features"]["constant"] = removed_constants
        const_validity = getattr(self, "_last_constant_validity", None)
        if const_validity:
            log["per_bar_validity"]["constant"] = const_validity

        standardize_cfg = self._config.get("standardize", {})
        method = standardize_cfg.get("method", "none")
        df = self.standardize(
            df, method=method, fit_mask=fit_mask, fit_mode=mode
        )

        logger.info(
            "Data preprocessing complete: columns=%s fit_mode=%s oos_guarantees=%s",
            df.shape[1],
            mode,
            log["oos_guarantees"],
        )
        return df, log

    def winsorize(
        self,
        df: pd.DataFrame,
        method: str,
        lower: float,
        upper: float,
        metadata: Optional[dict] = None,
        fit_mask: Optional[np.ndarray] = None,
        fit_mode: Optional[str] = None,
    ) -> tuple[pd.DataFrame, dict]:
        mode = self.resolve_fit_mode(fit_mode=fit_mode, fit_mask=fit_mask)
        method = method.lower()
        if method == "none":
            return df, {"winsorized": [], "skipped": list(df.columns), "fit_mode": mode}

        winsorized: list[str] = []
        skipped: list[str] = []
        clipped = df.copy()

        for column in clipped.columns:
            series = clipped[column]
            # type-feature 為靜態屬性：metadata/category 優先；禁以完整未來序列翻轉分支
            if self._column_is_type_feature(
                column,
                series,
                metadata=metadata,
                fit_mask=fit_mask,
                fit_mode=mode,
            ):
                skipped.append(column)
                continue

            clipped[column] = self._clip_series(
                series,
                method,
                lower,
                upper,
                fit_mask=fit_mask,
                fit_mode=mode,
            )
            winsorized.append(column)

        return clipped, {"winsorized": winsorized, "skipped": skipped, "fit_mode": mode}

    def handle_missing(
        self,
        df: pd.DataFrame,
        max_fill_forward: int,
        min_coverage: float,
        fit_mask: Optional[np.ndarray] = None,
        fit_mode: Optional[str] = None,
    ) -> tuple[pd.DataFrame, list[str]]:
        mode = self.resolve_fit_mode(fit_mode=fit_mode, fit_mask=fit_mask)
        if max_fill_forward and max_fill_forward > 0:
            filled = df.ffill(limit=int(max_fill_forward))
        else:
            filled = df.copy()
        self._last_coverage_validity: dict[str, list[bool]] = {}

        if mode == "pit_expanding":
            # T3：保欄不 drop。coverage mask 對**原序列**各算一次；
            # 不在此處套 NaN（避免 constant 再跑 pit_valid_mask → 雙 warmup）。
            # 最終 mask 在 remove_constant_features 與 constant/pit 組合後一次套用。
            validity: dict[str, list[bool]] = {}
            out = filled.copy()
            for column in out.columns:
                series = out[column]
                # expanding coverage = 累積非 NaN / (t+1)（原序列，不串 pit 遮罩）
                notna = series.notna().to_numpy(dtype=np.float64)
                cum = np.cumsum(notna)
                positions = np.arange(1, len(series) + 1, dtype=np.float64)
                cov = cum / positions
                cov_ok = cov >= float(min_coverage)
                validity[column] = cov_ok.tolist()
            self._last_coverage_validity = validity
            return out, []

        fit_df = self._select_fit_frame(filled, fit_mask=fit_mask, fit_mode=mode)
        coverage = fit_df.notna().mean()
        removed = coverage[coverage < min_coverage].index.tolist()
        if removed:
            filled = filled.drop(columns=removed)
        return filled, removed

    def remove_constant_features(
        self,
        df: pd.DataFrame,
        fit_mask: Optional[np.ndarray] = None,
        fit_mode: Optional[str] = None,
    ) -> tuple[pd.DataFrame, list[str]]:
        mode = self.resolve_fit_mode(fit_mode=fit_mode, fit_mask=fit_mask)
        self._last_constant_validity: dict[str, list[bool]] = {}

        if mode == "pit_expanding":
            # T3：coverage / constant / pit_valid 各對原序列算一次再 AND，禁串接重跑。
            validity: dict[str, list[bool]] = {}
            out = df.copy()
            cov_store = getattr(self, "_last_coverage_validity", None) or {}
            for column in out.columns:
                series = out[column]
                n = len(series)
                # pit_valid 對原序列一次（§MS first_valid dense→99）
                pit_ok = pit_valid_mask(series, min_samples=MIN_SAMPLES).to_numpy(
                    dtype=bool
                )
                values = series.to_numpy(dtype=np.float64, copy=False)
                finite = np.isfinite(values)
                cur_min = np.nan
                cur_max = np.nan
                has_val = False
                non_constant = np.zeros(n, dtype=bool)
                for t in range(n):
                    if finite[t]:
                        v = values[t]
                        if not has_val:
                            cur_min = v
                            cur_max = v
                            has_val = True
                        else:
                            if v < cur_min:
                                cur_min = v
                            if v > cur_max:
                                cur_max = v
                    if has_val and cur_min < cur_max:
                        non_constant[t] = True
                cov_list = cov_store.get(column)
                if cov_list is None or len(cov_list) != n:
                    cov_ok = np.ones(n, dtype=bool)
                else:
                    cov_ok = np.asarray(cov_list, dtype=bool)
                # 兩 mask + pit 對原序列組合；最終 first-valid == §MS canonical
                valid = pit_ok & non_constant & cov_ok
                validity[column] = valid.tolist()
                if not valid.all():
                    out.loc[~valid, column] = np.nan
            self._last_constant_validity = validity
            return out, []

        fit_df = self._select_fit_frame(df, fit_mask=fit_mask, fit_mode=mode)
        nunique = fit_df.nunique(dropna=True)
        removed = nunique[nunique <= 1].index.tolist()
        if removed:
            df = df.drop(columns=removed)
        return df, removed

    def standardize(
        self,
        df: pd.DataFrame,
        method: str = "none",
        fit_mask: Optional[np.ndarray] = None,
        fit_mode: Optional[str] = None,
    ) -> pd.DataFrame:
        method = method.lower()
        if method == "none":
            return df

        # cross-sectional / rank 無時間 fit 洩漏，不依 fit_mode
        if method == "cross_sectional_zscore":
            mean = df.mean(axis=1)
            std = df.std(axis=1).replace(0, np.nan)
            return df.sub(mean, axis=0).div(std, axis=0).fillna(0.0)
        if method == "rank_transform":
            return df.rank(axis=1, pct=True)

        mode = self.resolve_fit_mode(fit_mode=fit_mode, fit_mask=fit_mask)

        if method == "time_series_zscore":
            if mode == "pit_expanding":
                parts: dict[str, pd.Series] = {}
                for column in df.columns:
                    mean_s, std_s = pit_expanding_mean_std(
                        df[column], min_samples=MIN_SAMPLES
                    )
                    std_safe = std_s.replace(0, np.nan)
                    z = (df[column] - mean_s) / std_safe
                    parts[column] = z.fillna(0.0)
                return pd.DataFrame(parts, index=df.index)

            if mode == "train_mask":
                def _zscore_transform(
                    fit_df: pd.DataFrame, full_df: pd.DataFrame
                ) -> pd.DataFrame:
                    mean = fit_df.mean(axis=0)
                    std = fit_df.std(axis=0).replace(0, np.nan)
                    return full_df.sub(mean, axis=1).div(std, axis=1).fillna(0.0)

                return pit_train_fit(df, fit_mask, _zscore_transform)

            # full_sample
            fit_df = self._select_fit_frame(df, fit_mask=None, fit_mode="full_sample")
            mean = fit_df.mean(axis=0)
            std = fit_df.std(axis=0).replace(0, np.nan)
            return df.sub(mean, axis=1).div(std, axis=1).fillna(0.0)

        raise ValueError(f"Unknown standardize method: {method}")

    def _clip_series(
        self,
        series: pd.Series,
        method: str,
        lower: float,
        upper: float,
        fit_mask: Optional[np.ndarray] = None,
        fit_mode: Optional[str] = None,
    ) -> pd.Series:
        mode = self.resolve_fit_mode(fit_mode=fit_mode, fit_mask=fit_mask)

        if mode == "pit_expanding":
            return self._clip_series_pit(series, method, lower, upper)

        if mode == "train_mask":
            return self._clip_series_train(series, method, lower, upper, fit_mask)

        # full_sample — 全期 fit（legacy）
        return self._clip_series_static(series, method, lower, upper, fit_mask=None)

    def _clip_series_pit(
        self,
        series: pd.Series,
        method: str,
        lower: float,
        upper: float,
    ) -> pd.Series:
        """per-t expanding PIT winsorize。

        percentile：優先 pandas expanding（與 pit_expanding_bounds 在 dense 上等價
        atol~1e-15，且 O(n log n) 可跑 20k×N 生產路徑）；小樣本/需 byte 對齊
        時仍可走 pit_stats 原語。mad/zscore 鎖 pit_stats。
        """
        if method == "percentile":
            lo_q = float(lower) / 100.0
            hi_q = float(upper) / 100.0
            # n 小用 pit_stats（與單元測試 oracle 完全同路徑）；大 n 用 pandas
            if len(series) <= 512:
                lo, hi = pit_expanding_bounds(
                    series, lo_q, hi_q, min_samples=MIN_SAMPLES
                )
            else:
                # expanding min_periods=MIN_SAMPLES → warmup NaN；改 -inf/+inf no-clip
                exp = series.expanding(min_periods=MIN_SAMPLES)
                lo = exp.quantile(lo_q).fillna(-np.inf)
                hi = exp.quantile(hi_q).fillna(np.inf)
            return series.clip(lower=lo, upper=hi)

        if method == "mad":
            med, mad = pit_expanding_mad(series, min_samples=MIN_SAMPLES)
            # mad==0 或 warmup(NaN) → 該 bar 不 clip
            bound = _MAD_K * mad
            lo = med - bound
            hi = med + bound
            valid = med.notna() & mad.notna() & (mad.to_numpy() != 0)
            clipped = series.clip(lower=lo, upper=hi)
            return series.where(~valid, clipped)

        if method == "zscore":
            mean_s, std_s = pit_expanding_mean_std(
                series, min_samples=MIN_SAMPLES
            )
            bound = _ZSCORE_K * std_s
            lo = mean_s - bound
            hi = mean_s + bound
            valid = mean_s.notna() & std_s.notna() & (std_s.to_numpy() != 0)
            clipped = series.clip(lower=lo, upper=hi)
            return series.where(~valid, clipped)

        raise ValueError(f"Unknown winsorization method: {method}")

    def _clip_series_train(
        self,
        series: pd.Series,
        method: str,
        lower: float,
        upper: float,
        fit_mask: Optional[np.ndarray],
    ) -> pd.Series:
        """train_mask：mask 內估參數 → 全段 clip（pit_train_fit 邊界）。"""
        col = series.name if series.name is not None else "_x"
        frame = series.to_frame(name=col)

        def _transform(fit_df: pd.DataFrame, full_df: pd.DataFrame) -> pd.DataFrame:
            fit_s = fit_df[col]
            full_s = full_df[col]
            clipped = self._clip_series_static(
                full_s, method, lower, upper, fit_series_override=fit_s
            )
            return clipped.to_frame(name=col)

        out = pit_train_fit(frame, fit_mask, _transform)
        return out[col]

    def _clip_series_static(
        self,
        series: pd.Series,
        method: str,
        lower: float,
        upper: float,
        fit_mask: Optional[np.ndarray] = None,
        fit_series_override: Optional[pd.Series] = None,
    ) -> pd.Series:
        """用單一 fit 切片估邊界後 clip 全序列（full_sample / train 內部）。"""
        if fit_series_override is not None:
            fit_series = fit_series_override
        else:
            fit_series = (
                series
                if fit_mask is None
                else series.loc[self._coerce_fit_mask(len(series), fit_mask)]
            )
        if fit_series.dropna().empty:
            return series
        if method == "percentile":
            lower_q = lower / 100.0
            upper_q = upper / 100.0
            lo = fit_series.quantile(lower_q)
            hi = fit_series.quantile(upper_q)
            return series.clip(lo, hi)

        if method == "mad":
            median = np.nanmedian(fit_series)
            mad = np.nanmedian(np.abs(fit_series - median))
            if mad == 0 or np.isnan(mad):
                return series
            bound = _MAD_K * mad
            return series.clip(median - bound, median + bound)

        if method == "zscore":
            mean = fit_series.mean()
            std = fit_series.std()
            if std == 0 or np.isnan(std):
                return series
            bound = _ZSCORE_K * std
            return series.clip(mean - bound, mean + bound)

        raise ValueError(f"Unknown winsorization method: {method}")

    # 型態特徵合法離散值（pattern/type 標籤）；僅作 value 判定集合，非時間序列屬性
    _TYPE_FEATURE_VALUES: frozenset = frozenset({-100, 0, 100, -100.0, 0.0, 100.0})
    _TYPE_CATEGORY_TOKENS: frozenset[str] = frozenset(
        {
            "type",
            "pattern",
            "categorical",
            "categorical_position",
            "discrete_type",
            "type_feature",
        }
    )

    @classmethod
    def _is_type_feature(cls, series: pd.Series) -> bool:
        """value-set 判定（僅允許 fit 可見切片呼叫；禁全序列未來）。"""
        values = set(series.dropna().unique())
        if not values:
            return False
        return values.issubset(cls._TYPE_FEATURE_VALUES)

    @classmethod
    def _type_feature_from_metadata(
        cls, column: str, metadata: Optional[dict]
    ) -> Optional[bool]:
        """靜態 metadata/category 判定。True/False=已宣告；None=未宣告。"""
        if not metadata:
            return None
        type_cols = metadata.get("type_features") or metadata.get(
            "type_feature_columns"
        )
        if type_cols is not None:
            cols = {str(c) for c in type_cols}
            if str(column) in cols:
                return True
        features = metadata.get("features")
        col_meta: Optional[dict] = None
        if isinstance(features, dict):
            raw = features.get(column) or features.get(str(column))
            if isinstance(raw, dict):
                col_meta = raw
        if col_meta is None:
            raw2 = metadata.get(column)
            if isinstance(raw2, dict):
                col_meta = raw2
        if not isinstance(col_meta, dict):
            return None
        if "is_type_feature" in col_meta:
            return bool(col_meta["is_type_feature"])
        for key in ("category", "feature_type", "dtype_kind", "feature_category"):
            token = col_meta.get(key)
            if token is None:
                continue
            if str(token).lower().strip() in cls._TYPE_CATEGORY_TOKENS:
                return True
        return None

    def _column_is_type_feature(
        self,
        column: str,
        series: pd.Series,
        metadata: Optional[dict],
        fit_mask: Optional[np.ndarray],
        fit_mode: Optional[str],
    ) -> bool:
        """type-feature 分支：靜態屬性優先；禁 pit_expanding 讀完整未來序列。

        - metadata/category 宣告 → 直接用（與未來值無關）
        - train_mask → 僅 fit slice value-set
        - full_sample → 全期 value-set（研究逃生，oos_guarantees=False）
        - pit_expanding → 禁 value-set 讀全序列；未宣告 metadata → False
          （避免截尾 True / 加未來 False 的 look-ahead 分支翻轉）
        """
        declared = self._type_feature_from_metadata(column, metadata)
        if declared is not None:
            return declared

        mode = fit_mode or "unset"
        if mode == "pit_expanding":
            # 靜態屬性未宣告時不 peek 未來值；不把全序列當 type 判定輸入
            return False

        if mode == "full_sample":
            return self._is_type_feature(series)

        # train_mask / unset→train_mask：只看 fit 可見切片
        fit_series = self._select_fit_series(
            series, fit_mask=fit_mask, fit_mode=mode
        )
        return self._is_type_feature(fit_series)

    @staticmethod
    def _coerce_fit_mask(length: int, fit_mask: Optional[np.ndarray]) -> Optional[np.ndarray]:
        if fit_mask is None:
            return None
        mask = np.asarray(fit_mask, dtype=bool)
        if mask.shape[0] != length:
            raise ValueError("fit_mask length must match data length")
        if not bool(mask.any()):
            raise ValueError("fit_mask must select at least one row")
        return mask

    @classmethod
    def _select_fit_frame(
        cls,
        df: pd.DataFrame,
        fit_mask: Optional[np.ndarray],
        fit_mode: Optional[str] = None,
    ) -> pd.DataFrame:
        """依 mode 選 fit 切片。pit_expanding 不應呼叫此法做一次全欄統計。"""
        if fit_mode == "full_sample":
            return df
        if fit_mode == "pit_expanding":
            # per-bar 路徑不應依賴此切片做統計；回全表僅相容舊呼叫
            return df
        mask = cls._coerce_fit_mask(len(df), fit_mask)
        return df if mask is None else df.loc[mask]

    @classmethod
    def _select_fit_series(
        cls,
        series: pd.Series,
        fit_mask: Optional[np.ndarray],
        fit_mode: Optional[str] = None,
    ) -> pd.Series:
        if fit_mode == "full_sample":
            return series
        if fit_mode == "pit_expanding":
            # 禁作為 type-feature 全序列 peek；呼叫端應走 _column_is_type_feature
            raise ValueError(
                "pit_expanding must not select full series for fit-time type "
                "classification (look-ahead); use metadata or train_mask slice"
            )
        mask = cls._coerce_fit_mask(len(series), fit_mask)
        return series if mask is None else series.loc[mask]
