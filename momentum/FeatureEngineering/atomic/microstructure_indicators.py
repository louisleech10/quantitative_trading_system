from __future__ import annotations

from typing import Dict, List

import numpy as np
import pandas as pd
from scipy.stats import norm

from momentum.core.logging import get_logger


logger = get_logger(__name__)


class MicrostructureIndicatorEngine:
    """Layer 1 微觀結構特徵引擎。"""

    def __init__(self, config: Dict, data_sources: List[str]):
        self._config = config or {}
        self._data_sources = data_sources
        self.windows = self._config.get("windows", [5, 13, 21, 55])
        self.epsilon = float(self._config.get("epsilon", 1e-10))
        self.min_trades = int(self._config.get("min_trades", 1))
        self.enabled_features = self._config.get("enabled_features", "all")
        self.cs_spread_smooth = self._config.get("cs_spread_smooth", [5, 13, 21])
        self.kyle_lambda_windows = self._config.get("kyle_lambda_windows", [13, 21, 55])
        self.vpin_n_buckets = self._config.get("vpin_n_buckets", [30, 50])
        self.vpin_zscore_windows = self._config.get("vpin_zscore_windows", [21, 55])

    def compute_all(self, data: pd.DataFrame) -> pd.DataFrame:
        frames: List[pd.DataFrame] = []
        methods = [
            ("amihud", self._compute_amihud),
            ("kyle_lambda", self._compute_kyle_lambda),
            ("roll_spread", self._compute_roll_spread),
            ("cs_spread", self._compute_cs_spread),
            ("ofi", self._compute_ofi),
            ("large_trade_ratio", self._compute_large_trade_ratio),
            ("vpin", self._compute_vpin),
        ]

        for name, method in methods:
            if self.enabled_features == "all" or name in self.enabled_features:
                try:
                    frames.append(method(data))
                except Exception as exc:
                    logger.warning("Microstructure indicator %s failed: %s", name, exc)

        frames = [frame for frame in frames if frame is not None and not frame.empty]
        if not frames:
            return pd.DataFrame(index=data.index)
        return pd.concat(frames, axis=1)

    def get_feature_metadata(self) -> Dict[str, Dict]:
        metadata: Dict[str, Dict] = {}

        for window in self.windows:
            metadata[f"ms_amihud_illiq_{window}"] = self._meta("amihud", {"window": window})
            metadata[f"ms_ofi_zscore_{window}"] = self._meta("ofi_zscore", {"window": window})

        for window in self.kyle_lambda_windows:
            metadata[f"ms_kyle_lambda_{window}"] = self._meta("kyle_lambda", {"window": window})
            metadata[f"ms_roll_spread_{window}"] = self._meta("roll_spread", {"window": window})
            metadata[f"ms_large_trade_ratio_{window}"] = self._meta("large_trade_ratio", {"window": window})

        for window in self.cs_spread_smooth:
            metadata[f"ms_cs_spread_{window}"] = self._meta("cs_spread", {"window": window})

        for bucket in self.vpin_n_buckets:
            metadata[f"ms_vpin_{bucket}"] = self._meta("vpin", {"window": bucket})

        for window in self.vpin_zscore_windows:
            metadata[f"ms_vpin_zscore_{window}"] = self._meta("vpin_zscore", {"window": window})

        metadata["ms_ofi_raw"] = self._meta("ofi_raw", {})
        return metadata

    def get_data_warnings(self, data: pd.DataFrame) -> List[str]:
        """回傳此引擎在給定資料上可能遇到的缺欄位警告。"""
        warns: List[str] = []
        ef = self.enabled_features
        ofi_enabled = ef == "all" or "ofi" in ef
        if ofi_enabled:
            if "taker_ratio" not in data.columns and "taker_buy_volume" not in data.columns:
                warns.append(
                    "微觀結構 OFI：缺少 taker_ratio 與 taker_buy_volume，指標已跳過"
                    "（請在數據源設定中啟用 taker_ratio）"
                )
            elif "taker_ratio" not in data.columns:
                warns.append(
                    "微觀結構 OFI：缺少 taker_ratio，已改用 taker_buy_volume / volume 近似（精度較低）"
                )
        ltr_enabled = ef == "all" or "large_trade_ratio" in ef
        if ltr_enabled and "trades" not in data.columns:
            warns.append(
                "微觀結構 Large Trade Ratio：缺少 trades 欄位，特徵輸出全為 NaN"
            )
        amihud_enabled = ef == "all" or "amihud" in ef
        if amihud_enabled and "quote_volume" not in data.columns:
            warns.append(
                "微觀結構 Amihud：缺少 quote_volume，已改用 close × volume 代替（精度較低）"
            )
        return warns

    def _meta(self, indicator: str, params: Dict) -> Dict:
        return {
            "layer": "layer1",
            "category": "microstructure",
            "indicator": indicator,
            "params": params,
            "description": f"{indicator} microstructure feature",
        }

    def _compute_amihud(self, data: pd.DataFrame) -> pd.DataFrame:
        close = data["close"]
        returns = close.pct_change().abs()

        if "quote_volume" in data.columns:
            quote_volume = data["quote_volume"].astype(float)
        else:
            quote_volume = (close * data["volume"]).astype(float)

        ratio = returns / quote_volume.replace(0.0, np.nan)
        return pd.DataFrame(
            {f"ms_amihud_illiq_{window}": ratio.rolling(window).mean() for window in self.windows},
            index=data.index,
        )

    def _compute_kyle_lambda(self, data: pd.DataFrame) -> pd.DataFrame:
        close = data["close"].astype(float)
        volume = data["volume"].astype(float)

        price_change = close.diff()
        signed_volume = volume * np.sign(close.pct_change().fillna(0.0))

        output: Dict[str, pd.Series] = {}
        for window in self.kyle_lambda_windows:
            cov = price_change.rolling(window).cov(signed_volume)
            var = signed_volume.rolling(window).var()
            value = cov / var.replace(0.0, np.nan)
            value = value.fillna(0.0)
            output[f"ms_kyle_lambda_{window}"] = value

        return pd.DataFrame(output, index=data.index)

    def _compute_roll_spread(self, data: pd.DataFrame) -> pd.DataFrame:
        dp = data["close"].astype(float).diff()
        lag_dp = dp.shift(1)

        output: Dict[str, pd.Series] = {}
        for window in self.kyle_lambda_windows:
            autocov = dp.rolling(window).cov(lag_dp)
            spread = 2.0 * np.sqrt((-autocov).clip(lower=0.0))
            output[f"ms_roll_spread_{window}"] = spread.fillna(0.0)

        return pd.DataFrame(output, index=data.index)

    def _compute_cs_spread(self, data: pd.DataFrame) -> pd.DataFrame:
        high = data["high"].astype(float)
        low = data["low"].astype(float)

        high_2 = high.rolling(2).max()
        low_2 = low.rolling(2).min()

        beta = np.log((high / low.replace(0.0, np.nan)).clip(lower=1.0)) ** 2
        gamma = np.log((high_2 / low_2.replace(0.0, np.nan)).clip(lower=1.0)) ** 2

        alpha = np.sqrt(2.0 * beta) - np.sqrt(gamma)
        exp_alpha = np.exp(alpha)
        spread_raw = 2.0 * (exp_alpha - 1.0) / (exp_alpha + 1.0)
        spread_raw = spread_raw.clip(lower=0.0).replace([np.inf, -np.inf], np.nan)

        output: Dict[str, pd.Series] = {}
        for window in self.cs_spread_smooth:
            output[f"ms_cs_spread_{window}"] = spread_raw.rolling(window).mean().fillna(0.0)

        return pd.DataFrame(output, index=data.index)

    def _compute_ofi(self, data: pd.DataFrame) -> pd.DataFrame:
        if "taker_ratio" in data.columns:
            taker_ratio = data["taker_ratio"].astype(float)
        else:
            logger.warning("taker_ratio missing, fallback to taker_buy_volume / volume")
            taker_ratio = data["taker_buy_volume"].astype(float) / data["volume"].replace(0.0, np.nan)

        ofi_raw = (2.0 * taker_ratio - 1.0).replace([np.inf, -np.inf], np.nan)
        output: Dict[str, pd.Series] = {"ms_ofi_raw": ofi_raw}

        for window in self.windows:
            mean = ofi_raw.rolling(window).mean()
            std = ofi_raw.rolling(window).std()
            output[f"ms_ofi_zscore_{window}"] = (ofi_raw - mean) / std.replace(0.0, np.nan)

        return pd.DataFrame(output, index=data.index)

    def _compute_large_trade_ratio(self, data: pd.DataFrame) -> pd.DataFrame:
        if "quote_volume" in data.columns:
            quote_volume = data["quote_volume"].astype(float)
        else:
            quote_volume = data["close"].astype(float) * data["volume"].astype(float)

        if "trades" not in data.columns:
            logger.warning("trades missing, large trade ratio set to NaN")
            return pd.DataFrame(
                {f"ms_large_trade_ratio_{window}": pd.Series(np.nan, index=data.index) for window in self.kyle_lambda_windows},
                index=data.index,
            )

        trades = data["trades"].astype(float)
        trades = trades.where(trades >= self.min_trades, np.nan)
        avg_trade_size = quote_volume / trades

        output: Dict[str, pd.Series] = {}
        for window in self.kyle_lambda_windows:
            baseline = avg_trade_size.rolling(window).median()
            output[f"ms_large_trade_ratio_{window}"] = avg_trade_size / baseline.replace(0.0, np.nan)

        return pd.DataFrame(output, index=data.index)

    def _compute_vpin(self, data: pd.DataFrame) -> pd.DataFrame:
        close = data["close"].astype(float)
        volume = data["volume"].astype(float)

        delta_p = close.diff().fillna(0.0)
        sigma = delta_p.rolling(max(self.vpin_n_buckets)).std().fillna(0.0)

        z = delta_p / sigma.replace(0.0, np.nan)
        buy_pct = pd.Series(norm.cdf(z.fillna(0.0)), index=data.index)
        buy_pct = buy_pct.where(sigma != 0.0, 0.5)

        buy_volume = volume * buy_pct
        sell_volume = volume - buy_volume

        output: Dict[str, pd.Series] = {}
        for window in self.vpin_n_buckets:
            imbalance = (buy_volume - sell_volume).abs().rolling(window).sum()
            vol_sum = volume.rolling(window).sum()
            vpin = imbalance / vol_sum.replace(0.0, np.nan)
            if sigma.eq(0.0).all():
                vpin = pd.Series(0.0, index=data.index)
            output[f"ms_vpin_{window}"] = vpin

        for window in self.vpin_zscore_windows:
            base_window = self.vpin_n_buckets[0]
            base_vpin = output[f"ms_vpin_{base_window}"]
            mean = base_vpin.rolling(window).mean()
            std = base_vpin.rolling(window).std()
            output[f"ms_vpin_zscore_{window}"] = (base_vpin - mean) / std.replace(0.0, np.nan)

        return pd.DataFrame(output, index=data.index)
