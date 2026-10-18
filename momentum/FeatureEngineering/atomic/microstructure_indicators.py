from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy.stats import norm

from momentum.core.logging import get_logger
from momentum.FeatureEngineering.atomic import l1_output_points as l1op
from momentum.FeatureEngineering.atomic.compute_guard import guard_indicator_compute, resolve_fail_open
from momentum.FeatureEngineering.feature_naming import build_identity, format_feature_name, source_from_inputs


logger = get_logger(__name__)

# FF-NAME Task 2.2：倍數表條目 → 欄名 indicator 詞（compute、輸出點、metadata 三處共用之身分常數）
_MS_INDICATOR: Dict[str, str] = {
    "MS_AMIHUD_ILLIQ": "amihud-illiq",
    "MS_KYLE_LAMBDA": "kyle-lambda",
    "MS_ROLL_SPREAD": "roll-spread",
    "MS_CS_SPREAD": "cs-spread",
    "MS_OFI_RAW": "ofi-raw",
    "MS_OFI_ZSCORE": "ofi-zscore",
    "MS_LARGE_TRADE_RATIO": "large-trade-ratio",
    "MS_VPIN": "vpin",
    "MS_VPIN_ZSCORE": "vpin-zscore",
}


# ── Float32-safe ratio cap ──────────────────────────────────────────
# Float32 max is ~3.4e38; pandas nanops aggregates in float64 then casts.
# We cap ratios at 1e30 so:
#   - downstream float32 storage never overflows (no inf produced)
#   - extreme but legitimate values (e.g. 1e6–e8) are preserved
#   - L6.5 winsorization can still trim them to reasonable z-scores
# 1e-12 epsilon mask catches pathological near-zero denominators
# (volume/std/baseline) without flagging legitimate small values.
_RATIO_EPSILON = 1e-12
_RATIO_CAP = 1e30


def _safe_ratio(
    numerator: pd.Series,
    denominator: pd.Series,
    *,
    eps: float = _RATIO_EPSILON,
    cap: float = _RATIO_CAP,
) -> pd.Series:
    """Divide two series with overflow-safe semantics.

    1. Mask |denom| < eps  → NaN  (avoids +/- 1e30 spikes from underflow)
    2. Compute division
    3. Replace inf/-inf with NaN  (defence-in-depth)
    4. Clip to [-cap, cap]  (float32 cast safety)

    Result: pandas Series with no inf, no overflow risk on float32 cast.
    The first NaN-mask is the *real* fix; cap is belt-and-braces.
    """
    safe_denom = denominator.where(denominator.abs() > eps, np.nan)
    result = numerator / safe_denom
    result = result.replace([np.inf, -np.inf], np.nan)
    return result.clip(lower=-cap, upper=cap)


class MicrostructureIndicatorEngine:
    """Layer 1 微觀結構特徵引擎。"""

    def __init__(self, config: Dict, data_sources: List[str]):
        self._config = config or {}
        self._data_sources = data_sources
        self._fail_open = resolve_fail_open(
            self._config.get("fail_open_indicators")
        )
        self.windows = self._config.get("windows", [5, 13, 21, 55])
        self.epsilon = float(self._config.get("epsilon", 1e-10))
        self.min_trades = int(self._config.get("min_trades", 1))
        self.enabled_features = self._config.get("enabled_features", "all")
        self.cs_spread_smooth = self._config.get("cs_spread_smooth", [5, 13, 21])
        self.kyle_lambda_windows = self._config.get("kyle_lambda_windows", [13, 21, 55])
        self.vpin_n_buckets = self._config.get("vpin_n_buckets", [30, 50])
        self.vpin_zscore_windows = self._config.get("vpin_zscore_windows", [21, 55])
        self._seen_columns: Optional[Tuple[str, ...]] = None  # 最近一次輸出點所見之資料欄（metadata 分支依此）

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
                    guard_indicator_compute(name, exc, fail_open=self._fail_open)

        frames = [frame for frame in frames if frame is not None and not frame.empty]
        if not frames:
            return pd.DataFrame(index=data.index)
        return l1op.mask_engine_frame("microstructure", pd.concat(frames, axis=1), self._output_points(data), data)

    @staticmethod
    def _branch_inputs(columns: Iterable[str]) -> Dict[str, Tuple[str, ...]]:
        """各輸出之實際輸入資料鍵（依輸出點契約順序；分支依資料是否含 `quote_volume`／`taker_ratio`）。
        FF-NAME Task 2.2：source＝此元組之 canonical 串接 ⇒ 分支改變輸入即改變欄名。"""
        cols = set(map(str, columns))
        volume_in = ("quote_volume",) if "quote_volume" in cols else ("close", "volume")
        ofi_in = ("taker_ratio",) if "taker_ratio" in cols else ("taker_buy_volume", "volume")
        return {
            "MS_AMIHUD_ILLIQ": tuple(dict.fromkeys(("close",) + volume_in)),
            "MS_OFI_RAW": ofi_in,
            "MS_OFI_ZSCORE": ofi_in,
            "MS_KYLE_LAMBDA": ("close", "volume"),
            "MS_ROLL_SPREAD": ("close",),
            "MS_LARGE_TRADE_RATIO": tuple(dict.fromkeys(("trades",) + volume_in)),
            "MS_CS_SPREAD": ("high", "low"),
            "MS_VPIN": ("close", "volume"),
            "MS_VPIN_ZSCORE": ("close", "volume"),
        }

    def _col(self, entry: str, columns: Iterable[str], *params: object) -> str:
        """FF-NAME Task 2.2：microstructure 欄名＝身分常數之 `format_feature_name`（compute、輸出點、metadata 共用）。"""
        inputs = self._branch_inputs(columns)[entry]
        return format_feature_name(build_identity(source_from_inputs(inputs), "microstructure", _MS_INDICATOR[entry],
                                                  params))

    def _output_points(self, data: pd.DataFrame) -> Dict[str, Dict]:
        """FF-STAT Task 2.3：逐輸出欄之參數契約（完整遞移週期集合；SPEC §C v38／v39）。"""
        p = l1op.point
        columns = list(data.columns)
        self._seen_columns = tuple(map(str, columns))
        inputs = self._branch_inputs(columns)
        sigma_window = max(self.vpin_n_buckets)
        ofi_raw = self._col("MS_OFI_RAW", columns)
        points: Dict[str, Dict] = {ofi_raw: p("MS_OFI_RAW", {}, inputs["MS_OFI_RAW"])}
        for w in self.windows:
            points[self._col("MS_AMIHUD_ILLIQ", columns, w)] = p("MS_AMIHUD_ILLIQ", {"window": w},
                                                                 inputs["MS_AMIHUD_ILLIQ"])
            points[self._col("MS_OFI_ZSCORE", columns, w)] = p("MS_OFI_ZSCORE", {"window": w}, inputs["MS_OFI_ZSCORE"],
                                                               upstream=(ofi_raw,), window=w)
        for w in self.kyle_lambda_windows:
            points[self._col("MS_KYLE_LAMBDA", columns, w)] = p("MS_KYLE_LAMBDA", {"window": w},
                                                                inputs["MS_KYLE_LAMBDA"])
            points[self._col("MS_ROLL_SPREAD", columns, w)] = p("MS_ROLL_SPREAD", {"window": w},
                                                                inputs["MS_ROLL_SPREAD"])
            points[self._col("MS_LARGE_TRADE_RATIO", columns, w)] = p("MS_LARGE_TRADE_RATIO", {"window": w},
                                                                      inputs["MS_LARGE_TRADE_RATIO"])
        for w in self.cs_spread_smooth:
            points[self._col("MS_CS_SPREAD", columns, w)] = p("MS_CS_SPREAD", {"window": w}, inputs["MS_CS_SPREAD"])
        for b in self.vpin_n_buckets:
            points[self._col("MS_VPIN", columns, b)] = p("MS_VPIN", {"n_buckets": b, "sigma_window": sigma_window},
                                                         inputs["MS_VPIN"])
        base = self._col("MS_VPIN", columns, self.vpin_n_buckets[0])
        for w in self.vpin_zscore_windows:
            points[self._col("MS_VPIN_ZSCORE", columns, w)] = p("MS_VPIN_ZSCORE", {"window": w},
                                                                inputs["MS_VPIN_ZSCORE"], upstream=(base,), window=w)
        return points

    def get_feature_metadata(self, data: Optional[pd.DataFrame] = None) -> Dict[str, Dict]:
        """metadata 之鍵＝輸出點同一身分。分支依 `data` 之欄（未給則取最近一次輸出點所見之欄；皆無則視為含
        `quote_volume`／`taker_ratio` 之主分支）。microstructure 輸出為多輸入或價格差分衍生量，無單一直接取值之
        raw 鍵 ⇒ `raw_lookup_key` 一律 None（與改前 metadata 無 source 之 Distance 結果一致）。"""
        if data is not None:
            columns: Iterable[str] = list(data.columns)
        elif getattr(self, "_seen_columns", None) is not None:
            columns = self._seen_columns
        else:
            columns = ("quote_volume", "taker_ratio")
        entries = []
        for window in self.windows:
            entries.append(("MS_AMIHUD_ILLIQ", (window,), {"window": window}))
            entries.append(("MS_OFI_ZSCORE", (window,), {"window": window}))
        for window in self.kyle_lambda_windows:
            entries.append(("MS_KYLE_LAMBDA", (window,), {"window": window}))
            entries.append(("MS_ROLL_SPREAD", (window,), {"window": window}))
            entries.append(("MS_LARGE_TRADE_RATIO", (window,), {"window": window}))
        for window in self.cs_spread_smooth:
            entries.append(("MS_CS_SPREAD", (window,), {"window": window}))
        for bucket in self.vpin_n_buckets:
            entries.append(("MS_VPIN", (bucket,), {"n_buckets": bucket}))
        for window in self.vpin_zscore_windows:
            entries.append(("MS_VPIN_ZSCORE", (window,), {"window": window}))
        entries.append(("MS_OFI_RAW", (), {}))
        inputs = self._branch_inputs(columns)
        return {self._col(entry, columns, *values): self._meta(entry, inputs[entry], params)
                for entry, values, params in entries}

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

    def _meta(self, entry: str, inputs: Tuple[str, ...], params: Dict) -> Dict:
        indicator = _MS_INDICATOR[entry]
        return {
            "layer": "layer1",
            "category": "microstructure",
            "indicator": indicator,
            "source": source_from_inputs(inputs),
            "raw_lookup_key": None,
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

        ratio = _safe_ratio(returns, quote_volume)
        return pd.DataFrame(
            {self._col("MS_AMIHUD_ILLIQ", data.columns, window): ratio.rolling(window).mean() for window in self.windows},
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
            value = _safe_ratio(cov, var).fillna(0.0)
            output[self._col("MS_KYLE_LAMBDA", data.columns, window)] = value

        return pd.DataFrame(output, index=data.index)

    def _compute_roll_spread(self, data: pd.DataFrame) -> pd.DataFrame:
        dp = data["close"].astype(float).diff()
        lag_dp = dp.shift(1)

        output: Dict[str, pd.Series] = {}
        for window in self.kyle_lambda_windows:
            autocov = dp.rolling(window).cov(lag_dp)
            spread = 2.0 * np.sqrt((-autocov).clip(lower=0.0))
            output[self._col("MS_ROLL_SPREAD", data.columns, window)] = spread.fillna(0.0)

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
            output[self._col("MS_CS_SPREAD", data.columns, window)] = spread_raw.rolling(window).mean().fillna(0.0)

        return pd.DataFrame(output, index=data.index)

    def _compute_ofi(self, data: pd.DataFrame) -> pd.DataFrame:
        if "taker_ratio" in data.columns:
            taker_ratio = data["taker_ratio"].astype(float)
        else:
            logger.warning("taker_ratio missing, fallback to taker_buy_volume / volume")
            taker_ratio = data["taker_buy_volume"].astype(float) / data["volume"].replace(0.0, np.nan)

        ofi_raw = (2.0 * taker_ratio - 1.0).replace([np.inf, -np.inf], np.nan)
        output: Dict[str, pd.Series] = {self._col("MS_OFI_RAW", data.columns): ofi_raw}

        for window in self.windows:
            mean = ofi_raw.rolling(window).mean()
            std = ofi_raw.rolling(window).std()
            output[self._col("MS_OFI_ZSCORE", data.columns, window)] = _safe_ratio(ofi_raw - mean, std)

        return pd.DataFrame(output, index=data.index)

    def _compute_large_trade_ratio(self, data: pd.DataFrame) -> pd.DataFrame:
        if "quote_volume" in data.columns:
            quote_volume = data["quote_volume"].astype(float)
        else:
            quote_volume = data["close"].astype(float) * data["volume"].astype(float)

        if "trades" not in data.columns:
            logger.warning("trades missing, large trade ratio set to NaN")
            return pd.DataFrame(
                {self._col("MS_LARGE_TRADE_RATIO", data.columns, window): pd.Series(np.nan, index=data.index)
                 for window in self.kyle_lambda_windows},
                index=data.index,
            )

        trades = data["trades"].astype(float)
        trades = trades.where(trades >= self.min_trades, np.nan)
        avg_trade_size = _safe_ratio(quote_volume, trades)

        output: Dict[str, pd.Series] = {}
        for window in self.kyle_lambda_windows:
            baseline = avg_trade_size.rolling(window).median()
            output[self._col("MS_LARGE_TRADE_RATIO", data.columns, window)] = _safe_ratio(
                avg_trade_size, baseline
            )

        return pd.DataFrame(output, index=data.index)

    def _compute_vpin(self, data: pd.DataFrame) -> pd.DataFrame:
        close = data["close"].astype(float)
        volume = data["volume"].astype(float)

        delta_p = close.diff().fillna(0.0)
        sigma = delta_p.rolling(max(self.vpin_n_buckets)).std().fillna(0.0)

        z = _safe_ratio(delta_p, sigma)
        buy_pct = pd.Series(norm.cdf(z.fillna(0.0)), index=data.index)
        buy_pct = buy_pct.where(sigma != 0.0, 0.5)

        buy_volume = volume * buy_pct
        sell_volume = volume - buy_volume

        output: Dict[str, pd.Series] = {}
        for window in self.vpin_n_buckets:
            imbalance = (buy_volume - sell_volume).abs().rolling(window).sum()
            vol_sum = volume.rolling(window).sum()
            vpin = _safe_ratio(imbalance, vol_sum)
            if sigma.eq(0.0).all():
                vpin = pd.Series(0.0, index=data.index)
            output[self._col("MS_VPIN", data.columns, window)] = vpin

        for window in self.vpin_zscore_windows:
            base_window = self.vpin_n_buckets[0]
            base_vpin = output[self._col("MS_VPIN", data.columns, base_window)]
            mean = base_vpin.rolling(window).mean()
            std = base_vpin.rolling(window).std()
            output[self._col("MS_VPIN_ZSCORE", data.columns, window)] = _safe_ratio(base_vpin - mean, std)

        return pd.DataFrame(output, index=data.index)
