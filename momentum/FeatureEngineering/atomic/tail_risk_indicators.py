from __future__ import annotations

from typing import Dict, List

import numpy as np
import pandas as pd

from momentum.core.logging import get_logger


logger = get_logger(__name__)


class TailRiskIndicatorEngine:
    """Layer 1 尾部風險特徵引擎。"""

    def __init__(self, config: Dict, data_sources: List[str]):
        self._config = config or {}
        self._data_sources = data_sources
        self.windows = self._config.get("windows", [21, 55, 100])
        self.cvar_alphas = self._config.get("cvar_alphas", [0.01, 0.05])
        self.rv_windows = self._config.get("rv_windows", [13, 21, 55])
        self.mdd_windows = self._config.get("mdd_windows", [21, 55, 100])

        for alpha in self.cvar_alphas:
            if not 0 < float(alpha) < 1:
                raise ValueError(f"cvar_alpha must be in (0, 1), got {alpha}")

    def compute_all(self, data: pd.DataFrame) -> pd.DataFrame:
        if "close" not in data.columns:
            logger.warning(
                "TailRiskIndicatorEngine requires 'close' column but it is missing, skipping "
                "(available columns: %s)",
                list(data.columns),
            )
            return pd.DataFrame(index=data.index)
        close = data["close"].astype(float)
        returns = close.pct_change().replace([np.inf, -np.inf], np.nan)

        frames: List[pd.DataFrame] = []
        methods = [
            self._compute_cvar,
            self._compute_rv_decomposition,
            self._compute_ud_vol_ratio,
            self._compute_gpr,
            self._compute_jarque_bera,
            lambda _: self._compute_max_drawdown(close),
        ]

        for method in methods:
            try:
                frames.append(method(returns))
            except Exception as exc:
                logger.warning("Tail risk indicator failed: %s", exc)

        frames = [frame for frame in frames if frame is not None and not frame.empty]
        if not frames:
            return pd.DataFrame(index=data.index)

        return pd.concat(frames, axis=1)

    def get_feature_metadata(self) -> Dict[str, Dict]:
        metadata: Dict[str, Dict] = {}

        for alpha in self.cvar_alphas:
            alpha_name = int(round(float(alpha) * 100))
            for window in self.windows:
                metadata[f"tr_cvar_{alpha_name}pct_{window}"] = self._meta(
                    "cvar", {"alpha": alpha, "window": window}
                )

        for window in self.rv_windows:
            metadata[f"tr_rv_up_{window}"] = self._meta("rv_up", {"window": window})
            metadata[f"tr_rv_down_{window}"] = self._meta("rv_down", {"window": window})
            metadata[f"tr_rsj_{window}"] = self._meta("rsj", {"window": window})
            metadata[f"tr_ud_vol_ratio_{window}"] = self._meta("ud_vol_ratio", {"window": window})

        for window in self.windows:
            metadata[f"tr_gpr_{window}"] = self._meta("gpr", {"window": window})

        for window in [55, 100]:
            metadata[f"tr_jb_{window}"] = self._meta("jarque_bera", {"window": window})

        for window in self.mdd_windows:
            metadata[f"tr_mdd_{window}"] = self._meta("max_drawdown", {"window": window})

        return metadata

    def get_data_warnings(self, data: pd.DataFrame) -> List[str]:
        """回傳此引擎在給定資料上可能遇到的缺欄位警告。"""
        if "close" not in data.columns:
            return ["尾部風險：缺少 close 欄位，整個引擎已跳過"]
        return []

    def _meta(self, indicator: str, params: Dict) -> Dict:
        return {
            "layer": "layer1",
            "category": "tail_risk",
            "indicator": indicator,
            "params": params,
            "description": f"{indicator} tail risk feature",
        }

    def _compute_cvar(self, returns: pd.Series) -> pd.DataFrame:
        output: Dict[str, pd.Series] = {}
        for alpha in self.cvar_alphas:
            alpha_name = int(round(float(alpha) * 100))
            for window in self.windows:
                var = returns.rolling(window).quantile(alpha)
                cvar = returns.rolling(window).apply(
                    lambda values: np.nanmean(values[values <= np.nanquantile(values, alpha)])
                    if np.isfinite(values).sum() > 0
                    else np.nan,
                    raw=True,
                )
                cvar = cvar.where(var.notna(), np.nan)
                output[f"tr_cvar_{alpha_name}pct_{window}"] = cvar
        return pd.DataFrame(output, index=returns.index)

    def _compute_rv_decomposition(self, returns: pd.Series) -> pd.DataFrame:
        rv_up_map, rv_down_map = self._compute_rv_components(returns)

        output: Dict[str, pd.Series] = {}
        for window in self.rv_windows:
            rv_up = rv_up_map[window]
            rv_down = rv_down_map[window]
            output[f"tr_rv_up_{window}"] = rv_up
            output[f"tr_rv_down_{window}"] = rv_down
            output[f"tr_rsj_{window}"] = rv_up - rv_down

        return pd.DataFrame(output, index=returns.index)

    def _compute_ud_vol_ratio(self, returns: pd.Series) -> pd.DataFrame:
        rv_up_map, rv_down_map = self._compute_rv_components(returns)
        output: Dict[str, pd.Series] = {}
        for window in self.rv_windows:
            rv_up = rv_up_map[window]
            rv_down = rv_down_map[window]
            output[f"tr_ud_vol_ratio_{window}"] = rv_up / rv_down.replace(0.0, np.nan)
        return pd.DataFrame(output, index=returns.index)

    def _compute_rv_components(self, returns: pd.Series) -> Dict[int, pd.Series]:
        squared = returns.pow(2)
        up_sq = squared.where(returns > 0, 0.0)
        down_sq = squared.where(returns < 0, 0.0)

        rv_up_map: Dict[int, pd.Series] = {}
        rv_down_map: Dict[int, pd.Series] = {}
        for window in self.rv_windows:
            rv_up_map[window] = np.sqrt(up_sq.rolling(window).sum())
            rv_down_map[window] = np.sqrt(down_sq.rolling(window).sum())
        return rv_up_map, rv_down_map

    def _compute_gpr(self, returns: pd.Series) -> pd.DataFrame:
        output: Dict[str, pd.Series] = {}
        gains = returns.where(returns > 0, 0.0)
        losses = returns.where(returns < 0, 0.0).abs()

        for window in self.windows:
            gain_sum = gains.rolling(window).sum()
            loss_sum = losses.rolling(window).sum()
            gpr = gain_sum / loss_sum.replace(0.0, np.nan)
            output[f"tr_gpr_{window}"] = gpr.clip(lower=0.0, upper=100.0)

        return pd.DataFrame(output, index=returns.index)

    def _compute_jarque_bera(self, returns: pd.Series) -> pd.DataFrame:
        output: Dict[str, pd.Series] = {}
        for window in [55, 100]:
            skew = returns.rolling(window).skew()
            kurt = returns.rolling(window).kurt()
            jb = (window / 6.0) * (skew.pow(2) + (kurt.pow(2) / 4.0))
            output[f"tr_jb_{window}"] = jb
        return pd.DataFrame(output, index=returns.index)

    def _compute_max_drawdown(self, close: pd.Series) -> pd.DataFrame:
        invalid_price = close <= 0
        if invalid_price.any():
            logger.warning("close has non-positive values, MDD set to NaN on invalid windows")

        output: Dict[str, pd.Series] = {}
        for window in self.mdd_windows:
            rolling_max = close.rolling(window).max()
            drawdown = (close - rolling_max) / rolling_max.replace(0.0, np.nan)
            mdd = drawdown.rolling(window).min().abs()
            if invalid_price.any():
                mdd = mdd.where(~invalid_price, np.nan)
            output[f"tr_mdd_{window}"] = mdd

        return pd.DataFrame(output, index=close.index)
