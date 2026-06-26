"""IC split adapter for converting ML validators into SplitPlan contracts."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from itertools import combinations
from typing import Any, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from momentum.core.contracts import (
    SplitPlan,
    _coerce_timestamp_array,
    _normalize_symbol_array,
    _normalize_symbol_value,
    validate_split_integrity,
    validate_split_pair_integrity,
)
from momentum.core.logging import get_logger

logger = get_logger(__name__)


class EmbargoRelaxedError(ValueError):
    """CPCV returned a train set larger than the requested purge/embargo allows."""


SplitPlanPair = Tuple[SplitPlan, SplitPlan]


@dataclass
class ICSplitAdapter:
    """將既有 ML 切分器輸出轉成 IC Phase 1 SplitPlan。"""

    expected_freq: Optional[str] = None
    strict_embargo: bool = True
    allowed_symbols: Optional[set[str]] = None

    def split_cpcv(
        self,
        cpcv: Any,
        data: pd.DataFrame,
        *,
        symbol_col: str = "symbol",
        ts_col: str = "timestamp",
        feature_cols: Optional[Sequence[str]] = None,
        allowed_symbols: Optional[set[str]] = None,
    ) -> List[SplitPlanPair]:
        """逐 symbol 包裝 CombinatorialPurgedCV.split()。"""
        self._validate_frame(data, symbol_col, ts_col)
        frame = self._with_row_positions(data, symbol_col, ts_col)
        effective_allowed = self._effective_allowed_symbols(allowed_symbols)
        base_hash = self._base_universe_hash(frame, symbol_col, ts_col)
        plans: List[SplitPlanPair] = []
        full_ts = frame[ts_col].to_numpy()
        full_symbols = frame[symbol_col].to_numpy()

        for symbol, group in frame.groupby(symbol_col, sort=False, dropna=False):
            symbol = _normalize_symbol_value(symbol)
            group_sorted = group.sort_values(ts_col, kind="mergesort")
            positions = group_sorted["_split_row_pos"].to_numpy(dtype=int)
            X = self._feature_frame(group_sorted, symbol_col, ts_col, feature_cols)
            for fold_index, (train_local, test_local) in enumerate(cpcv.split(X)):
                train_local_arr = np.asarray(train_local, dtype=int)
                test_local_arr = np.asarray(test_local, dtype=int)
                if self.strict_embargo:
                    self._assert_expected_cpcv_test_groups(
                        test_local_arr,
                        n_samples=len(group_sorted),
                        n_groups=int(cpcv.config.n_groups),
                        n_test_groups=int(cpcv.config.n_test_groups),
                        max_paths=cpcv.config.max_paths,
                        fold_index=fold_index,
                        symbol=symbol,
                    )
                    self._assert_requested_cpcv_embargo(
                        train_local_arr,
                        test_local_arr,
                        n_samples=len(group_sorted),
                        purge_gap=int(cpcv.config.purge_gap),
                        embargo_pct=float(cpcv.config.embargo_pct),
                        fold_index=fold_index,
                        symbol=symbol,
                    )
                plans.append(
                    self._build_plan_pair(
                        positions=positions,
                        train_local=train_local_arr,
                        test_local=test_local_arr,
                        ts=full_ts,
                        symbols=full_symbols,
                        symbol=symbol,
                        purge_gap=int(cpcv.config.purge_gap),
                        embargo=int(len(group_sorted) * float(cpcv.config.embargo_pct)),
                        base_universe_hash=base_hash,
                        allowed_symbols=effective_allowed,
                    )
                )
        if not plans:
            raise ValueError("ICSplitAdapter produced no CPCV splits")
        return plans

    def split_wf(
        self,
        wf: Any,
        data: pd.DataFrame,
        *,
        symbol_col: str = "symbol",
        ts_col: str = "timestamp",
        allowed_symbols: Optional[set[str]] = None,
    ) -> List[SplitPlanPair]:
        """逐 symbol 展開 WalkForwardValidator._generate_rolling_splits() range tuple。"""
        self._validate_frame(data, symbol_col, ts_col)
        frame = self._with_row_positions(data, symbol_col, ts_col)
        effective_allowed = self._effective_allowed_symbols(allowed_symbols)
        base_hash = self._base_universe_hash(frame, symbol_col, ts_col)
        plans: List[SplitPlanPair] = []
        full_ts = frame[ts_col].to_numpy()
        full_symbols = frame[symbol_col].to_numpy()
        config = wf.config
        step_size = config.step_size or config.test_size

        for symbol, group in frame.groupby(symbol_col, sort=False, dropna=False):
            symbol = _normalize_symbol_value(symbol)
            group_sorted = group.sort_values(ts_col, kind="mergesort")
            positions = group_sorted["_split_row_pos"].to_numpy(dtype=int)
            splits = wf._generate_rolling_splits(
                len(group_sorted),
                int(config.train_size),
                int(config.test_size),
                int(step_size),
            )
            for fold_index, (train_range, test_range) in enumerate(splits):
                train_local = np.arange(train_range[0], train_range[1], dtype=int)
                test_local = np.arange(test_range[0], test_range[1], dtype=int)
                if self.strict_embargo:
                    self._assert_wf_cross_fold_embargo(
                        train_local,
                        previous_test_ranges=[
                            prior_test_range for _, prior_test_range in splits[:fold_index]
                        ],
                        n_samples=len(group_sorted),
                        embargo_len=int(len(group_sorted) * float(config.embargo_pct)),
                        symbol=symbol,
                    )
                plans.append(
                    self._build_plan_pair(
                        positions=positions,
                        train_local=train_local,
                        test_local=test_local,
                        ts=full_ts,
                        symbols=full_symbols,
                        symbol=symbol,
                        purge_gap=int(config.purge_gap),
                        embargo=int(len(group_sorted) * float(config.embargo_pct)),
                        base_universe_hash=base_hash,
                        allowed_symbols=effective_allowed,
                    )
                )
        if not plans:
            raise ValueError("ICSplitAdapter produced no walk-forward splits")
        return plans

    @staticmethod
    def _validate_frame(data: pd.DataFrame, symbol_col: str, ts_col: str) -> None:
        """檢查真實資料 frame 具備 adapter 所需欄位。"""
        if data.empty:
            raise ValueError("data must not be empty")
        missing = {symbol_col, ts_col} - set(data.columns)
        if missing:
            raise ValueError(f"data missing required columns: {sorted(missing)}")

    @staticmethod
    def _with_row_positions(
        data: pd.DataFrame,
        symbol_col: str,
        ts_col: str,
    ) -> pd.DataFrame:
        """建立不修改輸入的 row position view。"""
        frame = data.copy()
        frame["_split_row_pos"] = np.arange(len(frame), dtype=int)
        frame[ts_col] = _coerce_timestamp_array(frame[ts_col].to_numpy())
        frame[symbol_col] = _normalize_symbol_array(frame[symbol_col].to_numpy())
        return frame

    @staticmethod
    def _base_universe_hash(
        frame: pd.DataFrame,
        symbol_col: str,
        ts_col: str,
    ) -> str:
        """以 symbol/time row identity 建立 deterministic universe hash。"""
        identity = pd.util.hash_pandas_object(
            frame[[symbol_col, ts_col, "_split_row_pos"]],
            index=True,
        ).values
        return hashlib.sha256(identity.tobytes()).hexdigest()

    @staticmethod
    def _feature_frame(
        group: pd.DataFrame,
        symbol_col: str,
        ts_col: str,
        feature_cols: Optional[Sequence[str]],
    ) -> pd.DataFrame:
        """取得 splitter 使用的 feature frame。"""
        if feature_cols is not None:
            return group.loc[:, list(feature_cols)].reset_index(drop=True)
        excluded = {symbol_col, ts_col, "_split_row_pos"}
        cols = [col for col in group.columns if col not in excluded]
        return group.loc[:, cols].reset_index(drop=True)

    def _build_plan_pair(
        self,
        *,
        positions: np.ndarray,
        train_local: np.ndarray,
        test_local: np.ndarray,
        ts: np.ndarray,
        symbols: np.ndarray,
        symbol: str,
        purge_gap: int,
        embargo: int,
        base_universe_hash: str,
        allowed_symbols: Optional[set[str]],
    ) -> SplitPlanPair:
        """建立 train/test SplitPlan 並套用契約校驗。"""
        train_rows = positions[train_local]
        test_rows = positions[test_local]
        train_plan = SplitPlan(
            split_label="train",
            index_kind="positional",
            row_index=train_rows,
            time_bounds=self._time_bounds(ts, train_rows),
            purge_gap=purge_gap,
            embargo=embargo,
            expected_freq=self.expected_freq,
            base_universe_hash=base_universe_hash,
            symbol=symbol,
        )
        test_plan = SplitPlan(
            split_label="test",
            index_kind="positional",
            row_index=test_rows,
            time_bounds=self._time_bounds(ts, test_rows),
            purge_gap=purge_gap,
            embargo=embargo,
            expected_freq=self.expected_freq,
            base_universe_hash=base_universe_hash,
            symbol=symbol,
        )
        validate_split_pair_integrity(
            train_plan,
            test_plan,
            ts,
            symbols,
            allowed_symbols=allowed_symbols,
        )
        return train_plan, test_plan

    def _effective_allowed_symbols(
        self,
        allowed_symbols: Optional[set[str]],
    ) -> Optional[set[str]]:
        """合併 adapter 預設 universe 與 method override。"""
        return allowed_symbols if allowed_symbols is not None else self.allowed_symbols

    @staticmethod
    def _time_bounds(ts: np.ndarray, row_index: np.ndarray) -> tuple:
        """回傳 SplitPlan time_bounds。"""
        if row_index.size == 0:
            return (None, None)
        values = ts[row_index]
        return (pd.Timestamp(values[0]), pd.Timestamp(values[-1]))

    @staticmethod
    def _contiguous_ranges(indices: np.ndarray) -> List[Tuple[int, int]]:
        """將 sorted test index 壓成 [start,end) ranges。"""
        if indices.size == 0:
            return []
        sorted_idx = np.sort(indices.astype(int))
        ranges: List[Tuple[int, int]] = []
        start = int(sorted_idx[0])
        prev = start
        for value in sorted_idx[1:]:
            current = int(value)
            if current != prev + 1:
                ranges.append((start, prev + 1))
                start = current
            prev = current
        ranges.append((start, prev + 1))
        return ranges

    def _assert_requested_cpcv_embargo(
        self,
        train_indices: np.ndarray,
        test_indices: np.ndarray,
        *,
        n_samples: int,
        purge_gap: int,
        embargo_pct: float,
        fold_index: int,
        symbol: str,
    ) -> None:
        """用 requested config 重算 CPCV train set，偵測 silent relaxation。"""
        mask = np.ones(n_samples, dtype=bool)
        mask[test_indices] = False
        embargo_len = int(n_samples * embargo_pct)
        for start, end in self._contiguous_ranges(test_indices):
            purge_start = max(0, start - purge_gap)
            purge_end = min(n_samples, end + purge_gap + embargo_len)
            mask[purge_start:purge_end] = False
        expected_train = np.where(mask)[0]
        returned = np.sort(train_indices.astype(int))
        if not np.array_equal(returned, expected_train):
            extra = np.setdiff1d(returned, expected_train)
            logger.error(
                "CPCV embargo mismatch for %s fold %s: returned=%s expected=%s extra=%s",
                symbol,
                fold_index,
                len(returned),
                len(expected_train),
                extra[:10].tolist(),
            )
            raise EmbargoRelaxedError(
                f"CPCV returned train set does not match requested purge/embargo "
                f"for {symbol} fold {fold_index}"
            )

    @staticmethod
    def _expected_cpcv_test_group_sets(
        *,
        n_groups: int,
        n_test_groups: int,
        max_paths: Optional[int],
    ) -> List[Tuple[int, ...]]:
        """依 requested CPCV config 獨立重建 expected test group sets。"""
        test_group_sets = list(combinations(range(n_groups), n_test_groups))
        if max_paths is not None and len(test_group_sets) > max_paths:
            rng = np.random.default_rng(42)
            selected_idx = rng.choice(len(test_group_sets), size=max_paths, replace=False)
            test_group_sets = [test_group_sets[idx] for idx in np.sort(selected_idx)]
        return [tuple(group_set) for group_set in test_group_sets]

    @staticmethod
    def _compute_group_boundaries(n_samples: int, n_groups: int) -> List[Tuple[int, int]]:
        """用 CPCV config 獨立重建 group boundaries。"""
        indices = np.linspace(0, n_samples, n_groups + 1, dtype=int)
        return [(int(indices[index]), int(indices[index + 1])) for index in range(n_groups)]

    def _assert_expected_cpcv_test_groups(
        self,
        test_indices: np.ndarray,
        *,
        n_samples: int,
        n_groups: int,
        n_test_groups: int,
        max_paths: Optional[int],
        fold_index: int,
        symbol: str,
    ) -> None:
        """獨立重建 CPCV expected test boundaries，避免相信 splitter 回傳邊界。"""
        expected_group_sets = self._expected_cpcv_test_group_sets(
            n_groups=n_groups,
            n_test_groups=n_test_groups,
            max_paths=max_paths,
        )
        if fold_index >= len(expected_group_sets):
            raise EmbargoRelaxedError(f"CPCV returned unexpected extra fold for {symbol}")
        boundaries = self._compute_group_boundaries(n_samples, n_groups)
        expected_test: List[int] = []
        for group_index in expected_group_sets[fold_index]:
            start, end = boundaries[group_index]
            expected_test.extend(range(start, end))
        expected_arr = np.asarray(expected_test, dtype=int)
        returned = np.sort(test_indices.astype(int))
        if not np.array_equal(returned, expected_arr):
            raise EmbargoRelaxedError(
                f"CPCV returned test boundaries do not match requested groups "
                f"for {symbol} fold {fold_index}"
            )

    @staticmethod
    def _assert_wf_cross_fold_embargo(
        train_indices: np.ndarray,
        *,
        previous_test_ranges: Sequence[Tuple[int, int]],
        n_samples: int,
        embargo_len: int,
        symbol: str,
    ) -> None:
        """檢查 WF 後續 train 不含先前 fold test 後 embargo rows。"""
        if embargo_len <= 0:
            return
        for test_start, test_end in previous_test_ranges:
            embargo_start = int(test_end)
            embargo_end = min(n_samples, int(test_end) + embargo_len)
            leaking = train_indices[
                (train_indices >= embargo_start) & (train_indices < embargo_end)
            ]
            if leaking.size > 0:
                raise EmbargoRelaxedError(
                    f"WF train contains prior fold embargo rows for {symbol}"
                )
