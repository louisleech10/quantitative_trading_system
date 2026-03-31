from __future__ import annotations

import math
from typing import Dict, List

import numpy as np
import pandas as pd

from momentum.core.logging import get_logger


logger = get_logger(__name__)

try:
    from numba import jit

    HAS_NUMBA = True
except ImportError:
    HAS_NUMBA = False
    logger.warning("Numba not available, ApEn/SampEn will use pure numpy (slower)")


class EntropyIndicatorEngine:
    """Layer 1 資訊理論特徵引擎。"""

    def __init__(self, config: Dict, data_sources: List[str]):
        self._config = config or {}
        self._data_sources = data_sources
        self.windows = self._config.get("windows", [55, 100])
        self.n_bins = int(self._config.get("n_bins", 10))
        self.apen_m = int(self._config.get("apen_m", 2))
        self.apen_r_ratio = float(self._config.get("apen_r_ratio", 0.2))
        self.shannon_windows = self._config.get("shannon_windows", [21, 55, 100])
        self.hurst_windows = self._config.get("hurst_windows", [55, 100, 200])
        self.fractal_kmax = int(self._config.get("fractal_kmax", 10))
        self.use_numba = bool(self._config.get("use_numba", True)) and HAS_NUMBA
        self.perm_m = int(self._config.get("perm_m", 3))
        self.perm_windows = self._config.get("perm_windows", [21, 55, 100])
        self.apply_to = self._config.get("apply_to", ["close_return"])

        if self.perm_m < 2:
            raise ValueError(f"perm_m must be >= 2, got {self.perm_m}")

    def compute_all(self, data: pd.DataFrame) -> pd.DataFrame:
        frames: List[pd.DataFrame] = []

        for source in self.apply_to:
            try:
                series = self._resolve_series(data, source)
            except KeyError:
                logger.warning("Entropy source missing: %s", source)
                continue

            if series.isna().mean() > 0.5:
                logger.warning("Entropy source %s has >50%% NaN", source)

            frames.append(self._compute_shannon_entropy(series, source))

            if source == "close_return":
                frames.append(self._compute_approximate_entropy(series))
                frames.append(self._compute_sample_entropy(series))
                frames.append(self._compute_hurst(series))
                frames.append(self._compute_fractal_dimension(series))
                frames.append(self._compute_permutation_entropy(series))

        frames = [frame for frame in frames if frame is not None and not frame.empty]
        if not frames:
            return pd.DataFrame(index=data.index)

        return pd.concat(frames, axis=1)

    def get_feature_metadata(self) -> Dict[str, Dict]:
        metadata: Dict[str, Dict] = {}

        for source in self.apply_to:
            for window in self.shannon_windows:
                metadata[f"ent_shannon_{source}_{window}"] = self._meta("shannon", source, {"window": window})

        for window in self.windows:
            metadata[f"ent_apen_{window}"] = self._meta("approximate_entropy", "close_return", {"window": window})
            metadata[f"ent_sampen_{window}"] = self._meta("sample_entropy", "close_return", {"window": window})
            metadata[f"ent_fractal_dim_{window}"] = self._meta("fractal_dimension", "close_return", {"window": window})

        for window in self.hurst_windows:
            metadata[f"ent_hurst_{window}"] = self._meta("hurst", "close_return", {"window": window})

        for window in self.perm_windows:
            metadata[f"ent_perm_{window}"] = self._meta("permutation_entropy", "close_return", {"window": window})

        return metadata

    def get_data_warnings(self, data: pd.DataFrame) -> List[str]:
        """回傳此引擎在給定資料上可能遇到的缺欄位警告。"""
        warns: List[str] = []
        for source in self.apply_to:
            if source == "close_return":
                continue  # close 由 _BASE_OHLCV 保證一定存在
            if source not in data.columns:
                warns.append(
                    f"資訊熵 Shannon：數據源 '{source}' 不在資料欄位中，已跳過"
                    f"（請確認 data_sources.enabled_sources 包含 '{source}'）"
                )
        return warns

    def _meta(self, indicator: str, source: str, params: Dict) -> Dict:
        return {
            "layer": "layer1",
            "category": "entropy",
            "indicator": indicator,
            "source": source,
            "params": params,
            "description": f"{indicator} entropy feature",
        }

    def _resolve_series(self, data: pd.DataFrame, source: str) -> pd.Series:
        if source == "close_return":
            return data["close"].astype(float).pct_change()
        if source in data.columns:
            return data[source].astype(float)
        raise KeyError(source)

    def _compute_shannon_entropy(self, series: pd.Series, source_name: str) -> pd.DataFrame:
        output: Dict[str, pd.Series] = {}
        for window in self.shannon_windows:
            output[f"ent_shannon_{source_name}_{window}"] = series.rolling(window).apply(
                lambda values: self._shannon_of_array(values, self.n_bins), raw=True
            )
        return pd.DataFrame(output, index=series.index)

    def _compute_approximate_entropy(self, series: pd.Series) -> pd.DataFrame:
        output: Dict[str, pd.Series] = {}
        for window in self.windows:
            output[f"ent_apen_{window}"] = series.rolling(window).apply(
                lambda values: self._approximate_entropy(values, self.apen_m, self.apen_r_ratio), raw=True
            )
        return pd.DataFrame(output, index=series.index)

    def _compute_sample_entropy(self, series: pd.Series) -> pd.DataFrame:
        output: Dict[str, pd.Series] = {}
        for window in self.windows:
            output[f"ent_sampen_{window}"] = series.rolling(window).apply(
                lambda values: self._sample_entropy(values, self.apen_m, self.apen_r_ratio), raw=True
            )
        return pd.DataFrame(output, index=series.index)

    def _compute_hurst(self, series: pd.Series) -> pd.DataFrame:
        output: Dict[str, pd.Series] = {}
        for window in self.hurst_windows:
            output[f"ent_hurst_{window}"] = series.rolling(window).apply(
                self._hurst_rs, raw=True
            )
        return pd.DataFrame(output, index=series.index)

    def _compute_fractal_dimension(self, series: pd.Series) -> pd.DataFrame:
        output: Dict[str, pd.Series] = {}
        for window in self.windows:
            output[f"ent_fractal_dim_{window}"] = series.rolling(window).apply(
                self._higuchi_fractal_dimension, raw=True
            )
        return pd.DataFrame(output, index=series.index)

    def _compute_permutation_entropy(self, series: pd.Series) -> pd.DataFrame:
        output: Dict[str, pd.Series] = {}
        for window in self.perm_windows:
            output[f"ent_perm_{window}"] = series.rolling(window).apply(
                lambda values: self._perm_entropy(values, self.perm_m), raw=True
            )
        return pd.DataFrame(output, index=series.index)

    @staticmethod
    def _shannon_of_array(values: np.ndarray, n_bins: int) -> float:
        values = values[np.isfinite(values)]
        if len(values) == 0:
            return np.nan
        if np.all(values == values[0]):
            return 0.0
        hist, _ = np.histogram(values, bins=n_bins)
        prob = hist / max(hist.sum(), 1)
        prob = prob[prob > 0]
        return float(-(prob * np.log2(prob)).sum())

    @staticmethod
    def _approximate_entropy(values: np.ndarray, m: int, r_ratio: float) -> float:
        values = values[np.isfinite(values)]
        n = len(values)
        if n <= m + 1:
            return np.nan
        std = np.std(values)
        r = max(r_ratio * std, 1e-8)

        def phi(mm: int) -> float:
            vectors = np.array([values[i : i + mm] for i in range(n - mm + 1)])
            if len(vectors) == 0:
                return np.nan
            distances = np.max(np.abs(vectors[:, None, :] - vectors[None, :, :]), axis=2)
            c = np.sum(distances <= r, axis=0) / len(vectors)
            c = np.clip(c, 1e-12, None)
            return np.mean(np.log(c))

        phi_m = phi(m)
        phi_m1 = phi(m + 1)
        if np.isnan(phi_m) or np.isnan(phi_m1):
            return np.nan
        return float(phi_m - phi_m1)

    @staticmethod
    def _sample_entropy(values: np.ndarray, m: int, r_ratio: float) -> float:
        values = values[np.isfinite(values)]
        n = len(values)
        if n <= m + 1:
            return np.nan
        std = np.std(values)
        r = max(r_ratio * std, 1e-8)

        def count_matches(mm: int) -> int:
            vectors = np.array([values[i : i + mm] for i in range(n - mm + 1)])
            if len(vectors) <= 1:
                return 0
            distances = np.max(np.abs(vectors[:, None, :] - vectors[None, :, :]), axis=2)
            mask = np.triu(np.ones_like(distances, dtype=bool), k=1)
            return int(np.sum((distances <= r) & mask))

        b = count_matches(m)
        a = count_matches(m + 1)
        if b == 0 or a == 0:
            return np.nan
        return float(-np.log(a / b))

    @staticmethod
    def _hurst_rs(values: np.ndarray) -> float:
        values = values[np.isfinite(values)]
        n = len(values)
        if n < 20:
            return np.nan

        chunk_sizes = np.unique(np.floor(np.logspace(np.log10(10), np.log10(max(n // 2, 10)), num=6)).astype(int))
        rs_values: List[float] = []
        valid_sizes: List[int] = []

        for size in chunk_sizes:
            if size < 10 or size >= n:
                continue
            num_chunks = n // size
            if num_chunks < 2:
                continue
            trimmed = values[: num_chunks * size].reshape(num_chunks, size)
            demeaned = trimmed - trimmed.mean(axis=1, keepdims=True)
            cumulative = np.cumsum(demeaned, axis=1)
            r = cumulative.max(axis=1) - cumulative.min(axis=1)
            s = trimmed.std(axis=1)
            rs = r / np.where(s == 0.0, np.nan, s)
            valid_rs = rs[np.isfinite(rs)]
            if len(valid_rs) == 0:
                continue
            mean_rs = float(np.mean(valid_rs))
            if np.isfinite(mean_rs) and mean_rs > 0:
                rs_values.append(mean_rs)
                valid_sizes.append(int(size))

        if len(rs_values) < 2:
            return np.nan

        x = np.log(valid_sizes)
        y = np.log(rs_values)
        slope, intercept = np.polyfit(x, y, 1)
        y_hat = slope * x + intercept
        ss_res = np.sum((y - y_hat) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r_squared = 1.0 - ss_res / ss_tot if ss_tot != 0 else 0.0

        if r_squared < 0.1:
            return np.nan
        return float(slope)

    def _higuchi_fractal_dimension(self, values: np.ndarray) -> float:
        values = values[np.isfinite(values)]
        n = len(values)
        if n < 20:
            return np.nan

        k_max = min(self.fractal_kmax, n // 2)
        if k_max < 2:
            return np.nan

        lk: List[float] = []
        ks: List[int] = []

        for k in range(1, k_max + 1):
            lm_vals = []
            for m in range(k):
                idx = np.arange(m, n, k)
                if len(idx) < 2:
                    continue
                diff = np.abs(np.diff(values[idx])).sum()
                norm = (n - 1) / (((n - m - 1) // k) * k)
                lm_vals.append(diff * norm)
            if lm_vals:
                lk.append(np.mean(lm_vals) / k)
                ks.append(k)

        if len(lk) < 2:
            return np.nan

        x = np.log(1.0 / np.array(ks))
        y = np.log(np.array(lk))
        slope, _ = np.polyfit(x, y, 1)
        return float(slope)

    @staticmethod
    def _perm_entropy(values: np.ndarray, m: int) -> float:
        values = values[np.isfinite(values)]
        n = len(values)
        if m < 2:
            raise ValueError(f"perm_m must be >= 2, got {m}")
        if n < m:
            return np.nan
        if np.all(values == values[0]):
            return 0.0

        patterns = []
        for i in range(n - m + 1):
            pattern = tuple(np.argsort(values[i : i + m], kind="mergesort"))
            patterns.append(pattern)

        if not patterns:
            return np.nan

        counts = pd.Series(patterns).value_counts().values.astype(float)
        prob = counts / counts.sum()
        entropy = -(prob * np.log2(prob)).sum()
        return float(entropy / np.log2(math.factorial(m)))
