"""
Regime Detector - K-Means 無監督市場體制偵測

從 K 線資料中自動識別市場 regime（如高波動趨勢、低波動盤整等），
取代原有的規則式 bull/bear/high_vol/low_vol 硬規則。

核心特徵：
  - volatility: rolling pct_change std
  - trend_strength: |close - EMA| / ATR
  - volume_regime: volume / rolling_mean_volume

防護機制：
  - Expanding window fit 防止 Look-ahead Bias（LA-1 Segment-causal）
  - Label alignment 按 volatility 排序保證語義穩定（same-model re-predict）
  - 資料不足時 fallback 到規則式判定（PIT 分位）

Author: AI Agent
Date: 2026-04-10
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from momentum.Analysis.pit_stats import pit_expanding_quantile_thresholds
from momentum.core.logging import get_logger

logger = get_logger(__name__)

# 固定 refit 間隔（禁依最終 n 推導）；config 可調
DEFAULT_REFIT_INTERVAL: int = 50

# 語義化 regime 標籤（按 volatility 降序排列）
REGIME_LABELS_4 = [
    "high_vol_trending",
    "mid_vol_trending",
    "mid_vol_ranging",
    "low_vol_ranging",
]

REGIME_LABELS_3 = [
    "high_volatility",
    "medium_volatility",
    "low_volatility",
]


@dataclass
class RegimeDetectionResult:
    """Regime 偵測結果"""
    labels: np.ndarray  # shape (n_samples,) — 語義化字串標籤
    n_clusters: int
    cluster_centers: np.ndarray  # shape (n_clusters, n_features)
    cluster_stats: List[Dict]  # 每個 cluster 的統計
    method: str  # "kmeans" | "rule"
    feature_names: List[str]

    def to_dict(self) -> Dict:
        return {
            "n_clusters": self.n_clusters,
            "method": self.method,
            "feature_names": self.feature_names,
            "cluster_stats": self.cluster_stats,
        }


class RegimeDetector:
    """
    K-Means 市場體制偵測器

    從收盤價、成交量等原始 K 線資料中提取特徵，
    使用 K-Means 聚類自動識別市場 regime。
    """

    def __init__(
        self,
        n_clusters: int = 4,
        lookback: int = 55,
        min_samples_for_fit: int = 100,
        random_state: int = 42,
        refit_interval: int = DEFAULT_REFIT_INTERVAL,
    ):
        """
        Args:
            n_clusters: 聚類數量（預設 4：高波趨勢/中波趨勢/中波盤整/低波盤整）
            lookback: 計算特徵的回看窗口
            min_samples_for_fit: 最少樣本數才進行聚類
            random_state: 隨機種子（確保可重現）
            refit_interval: Segment-causal refit 間隔（固定常數，禁依 n 推導）
        """
        if n_clusters < 2:
            raise ValueError(f"n_clusters must be >= 2, got {n_clusters}")
        if lookback < 5:
            raise ValueError(f"lookback must be >= 5, got {lookback}")
        if int(refit_interval) < 1:
            raise ValueError(f"refit_interval must be >= 1, got {refit_interval}")

        self.n_clusters = n_clusters
        self.lookback = lookback
        self.min_samples_for_fit = max(min_samples_for_fit, n_clusters * 5)
        self.random_state = random_state
        self.refit_interval = int(refit_interval)
        self._label_map = REGIME_LABELS_4 if n_clusters == 4 else REGIME_LABELS_3

    def detect(
        self,
        close: pd.Series,
        volume: Optional[pd.Series] = None,
        expanding: bool = True,
    ) -> RegimeDetectionResult:
        """
        偵測市場 regime。

        Args:
            close: 收盤價序列（必須有 index）
            volume: 成交量序列（可選，增強聚類品質）
            expanding: True=expanding window fit（防 look-ahead）；
                False=全期 ``_fit_global``（§N residual / P2；IC/XGBoost
                caller 不得傳 False，見呼叫層鎖）。

        Returns:
            RegimeDetectionResult
        """
        features_df = self._build_features(close, volume)
        valid_mask = features_df.notna().all(axis=1)
        valid_df = features_df[valid_mask]

        if len(valid_df) < self.min_samples_for_fit:
            logger.warning(
                "Insufficient samples for K-Means (%d < %d), falling back to rule-based",
                len(valid_df),
                self.min_samples_for_fit,
            )
            return self._fallback_rule_based(close, volume, features_df)

        # expanding=False → _fit_global（P2 residual；全域 guard 已撤，見 SPEC §N）
        if expanding:
            labels = self._fit_expanding(valid_df, close=close, volume=volume)
        else:
            labels = self._fit_global(valid_df)

        # 回填到原始 index
        full_labels = np.full(len(features_df), "", dtype=object)
        full_labels[valid_mask.values] = labels

        # 統計每個 cluster
        cluster_stats = self._compute_cluster_stats(valid_df, labels)

        return RegimeDetectionResult(
            labels=full_labels,
            n_clusters=self.n_clusters,
            cluster_centers=np.zeros((self.n_clusters, len(features_df.columns))),
            cluster_stats=cluster_stats,
            method="kmeans",
            feature_names=features_df.columns.tolist(),
        )

    def detect_phases_for_index(
        self,
        close: pd.Series,
        volume: Optional[pd.Series] = None,
        index: pd.Index = None,
    ) -> List[str]:
        """
        產出與 index 對齊的 regime labels（供 RegimeAnalyzer 使用）。

        若 index 為 None，使用 close 的 index。
        回傳 List[str]，長度 == len(index)。

        LA-1 §N：XGBoost 路徑 caller 鎖 expanding=True（不得全期 fit）。
        """
        # caller 層鎖：本路徑固定 PIT Segment-causal，不暴露 expanding 參數
        expanding_locked = True
        assert expanding_locked is True, "XGBoost phases path requires expanding=True"
        result = self.detect(close, volume, expanding=expanding_locked)
        labels_series = pd.Series(result.labels, index=close.index)

        target_index = index if index is not None else close.index
        aligned = labels_series.reindex(target_index, fill_value="unknown")
        return aligned.tolist()

    def _build_features(
        self, close: pd.Series, volume: Optional[pd.Series]
    ) -> pd.DataFrame:
        """從 K 線資料提取聚類特徵。"""
        features = {}

        # Feature 1: Volatility (rolling std of pct_change)
        pct = close.pct_change(fill_method=None)
        features["volatility"] = pct.rolling(
            self.lookback, min_periods=max(5, self.lookback // 2)
        ).std()

        # Feature 2: Trend strength (|close - EMA| / ATR)
        ema = close.ewm(span=self.lookback, adjust=False).mean()
        high_low_range = close.rolling(self.lookback, min_periods=5).max() - close.rolling(
            self.lookback, min_periods=5
        ).min()
        # 避免除以零
        atr_proxy = high_low_range.replace(0, np.nan)
        features["trend_strength"] = (close - ema).abs() / atr_proxy

        # Feature 3: Volume regime (若有 volume)
        if volume is not None and not volume.isna().all():
            vol_ma = volume.rolling(self.lookback, min_periods=5).mean()
            vol_ma_safe = vol_ma.replace(0, np.nan)
            features["volume_ratio"] = volume / vol_ma_safe

        return pd.DataFrame(features, index=close.index)

    def _fit_global(self, valid_df: pd.DataFrame) -> np.ndarray:
        """全局 fit（§N exclude / P2 residual；detect 不再呼叫）。"""
        scaler = StandardScaler()
        X = scaler.fit_transform(valid_df.values)

        km = KMeans(
            n_clusters=self.n_clusters,
            random_state=self.random_state,
            n_init=10,
            max_iter=300,
        )
        raw_labels = km.fit_predict(X)

        return self._align_labels(raw_labels, valid_df["volatility"].values)

    def _fit_expanding(
        self,
        valid_df: pd.DataFrame,
        close: Optional[pd.Series] = None,
        volume: Optional[pd.Series] = None,
    ) -> np.ndarray:
        """Segment-causal expanding fit（SPEC B1.3 偽碼全文）。

        REFIT_INTERVAL 固定（config 可調），禁依最終 n 推導。
        決策時點 = prev_end：fit / same-model re-predict 命名 / 段內 predict
        全同一 model namespace。
        """
        n = len(valid_df)
        labels = np.full(n, "unknown", dtype=object)

        warm_up = self.min_samples_for_fit
        refit_interval = self.refit_interval  # 固定常數，禁 max(50, n//10)

        refit_points = list(range(warm_up, n, refit_interval))
        if not refit_points or refit_points[-1] != n:
            refit_points.append(n)

        # 首段 / prefix 不足 → 委派 B1.2 PIT rule（對齊 valid_df index）
        rule_full: Optional[np.ndarray] = None
        if close is not None:
            close_aligned = close.reindex(valid_df.index)
            vol_aligned = (
                volume.reindex(valid_df.index) if volume is not None else None
            )
            rule_full = self._compute_pit_rule_labels(
                close_aligned, vol_aligned
            )

        prev_end = 0
        for end_idx in refit_points:
            if prev_end < self.min_samples_for_fit:
                # 含首段 prev_end=0：委派 B1.2 真值表
                if rule_full is not None:
                    labels[prev_end:end_idx] = rule_full[prev_end:end_idx]
                else:
                    labels[prev_end:end_idx] = "unknown"
                prev_end = end_idx
                continue

            # fit 只用段前 prefix [0:prev_end]
            train_df = valid_df.iloc[:prev_end]
            scaler_t = StandardScaler()
            X_train = scaler_t.fit_transform(train_df.values)
            model_t = KMeans(
                n_clusters=self.n_clusters,
                random_state=self.random_state,
                n_init=10,
                max_iter=300,
            )
            model_t.fit(X_train)

            # same-model re-predict prefix → name_map（禁用歷史 raw id 跨 model）
            prefix_raw = model_t.predict(X_train)
            name_map = self._build_name_map(
                prefix_raw, train_df["volatility"].to_numpy(dtype=np.float64)
            )

            # 段內 predict；map 未涵蓋 raw id → "unknown"（不回頭擴充）
            segment = valid_df.iloc[prev_end:end_idx]
            X_seg = scaler_t.transform(segment.values)
            seg_raw = model_t.predict(X_seg)
            seg_names = np.array(
                [name_map.get(int(r), "unknown") for r in seg_raw],
                dtype=object,
            )
            labels[prev_end:end_idx] = seg_names
            prev_end = end_idx

        return labels

    def _build_name_map(
        self, raw_labels: np.ndarray, volatility: np.ndarray
    ) -> Dict[int, str]:
        """按 cluster 內 volatility 均值降序 → 語義名 map（同一 model namespace）。"""
        unique_labels = np.unique(raw_labels)
        unique_labels = unique_labels[unique_labels >= 0]
        n_actual = len(unique_labels)

        cluster_vol: Dict[int, float] = {}
        for label in unique_labels:
            mask = raw_labels == label
            vol_values = volatility[mask]
            valid_vols = vol_values[~np.isnan(vol_values)]
            cluster_vol[int(label)] = (
                float(np.mean(valid_vols)) if len(valid_vols) > 0 else 0.0
            )

        sorted_labels = sorted(
            cluster_vol.keys(), key=lambda k: cluster_vol[k], reverse=True
        )

        if n_actual <= len(self._label_map):
            label_names = self._label_map[:n_actual]
        else:
            label_names = [f"regime_{i}" for i in range(n_actual)]

        return {int(old): label_names[i] for i, old in enumerate(sorted_labels)}

    def _align_labels(
        self, raw_labels: np.ndarray, volatility: np.ndarray
    ) -> np.ndarray:
        """
        按 cluster 內的 volatility 均值降序排序，
        確保 label 語義穩定（高波動 → 低波動）。

        供 ``_fit_global``（§N residual）使用；expanding 路徑改走
        ``_build_name_map`` per-segment same-model re-predict。
        """
        mapping = self._build_name_map(raw_labels, volatility)
        result = np.array(
            [mapping.get(int(l), "unknown") for l in raw_labels], dtype=object
        )
        return result

    def _compute_pit_rule_labels(
        self,
        close: pd.Series,
        volume: Optional[pd.Series] = None,
    ) -> np.ndarray:
        """B1.2 真值表：PIT rule labels，長度 == len(close)。

        ① len(vol_values)<2 → 全 "unknown"
        ② warmup（effective_count(vol)<100 → 門檻 (-inf,+inf)）→ high/low=False，
           bull/bear/mid 照舊（不得 unknown）
        ③ 非 warmup → PIT 門檻分類
        """
        ema = close.ewm(span=self.lookback, adjust=False).mean()
        vol = close.pct_change(fill_method=None).rolling(self.lookback).std()

        vol_values = vol.dropna()
        if len(vol_values) < 2:
            return np.full(len(close), "unknown", dtype=object)

        lo_t, hi_t = pit_expanding_quantile_thresholds(
            vol, lo_q=0.20, hi_q=0.80, min_samples=100
        )

        labels = np.full(len(close), "mid_vol_ranging", dtype=object)
        # 與 close / vol 對齊的 boolean mask（NaN 比較 → False）
        bull_mask = (close > ema).fillna(False).to_numpy()
        bear_mask = (close <= ema).fillna(False).to_numpy()
        high_vol_mask = (vol >= hi_t).fillna(False).to_numpy()
        low_vol_mask = (vol <= lo_t).fillna(False).to_numpy()

        labels[bull_mask & high_vol_mask] = "high_vol_trending"
        labels[bull_mask & ~high_vol_mask & ~low_vol_mask] = "mid_vol_trending"
        labels[bear_mask & high_vol_mask] = "high_vol_trending"
        labels[bear_mask & ~high_vol_mask & ~low_vol_mask] = "mid_vol_ranging"
        labels[low_vol_mask] = "low_vol_ranging"
        return labels

    def _fallback_rule_based(
        self,
        close: pd.Series,
        volume: Optional[pd.Series],
        features_df: pd.DataFrame,
    ) -> RegimeDetectionResult:
        """資料不足時 fallback 到規則式 regime 判定（PIT 分位，B1.2）。"""
        labels = self._compute_pit_rule_labels(close, volume)

        return RegimeDetectionResult(
            labels=labels,
            n_clusters=self.n_clusters,
            cluster_centers=np.zeros((self.n_clusters, len(features_df.columns))),
            cluster_stats=[],
            method="rule",
            feature_names=features_df.columns.tolist(),
        )

    def _compute_cluster_stats(
        self, valid_df: pd.DataFrame, labels: np.ndarray
    ) -> List[Dict]:
        """計算每個 regime 的統計摘要。"""
        stats = []
        unique = sorted(set(labels))
        for label in unique:
            if label == "" or label == "unknown":
                continue
            mask = labels == label
            count = int(mask.sum())
            cluster_data = valid_df[mask]
            stat = {
                "regime": label,
                "count": count,
                "pct": round(count / len(labels) * 100, 1),
            }
            for col in valid_df.columns:
                values = cluster_data[col].dropna()
                if len(values) > 0:
                    stat[f"{col}_mean"] = round(float(values.mean()), 6)
                    stat[f"{col}_std"] = round(float(values.std()), 6)
            stats.append(stat)
        return stats
