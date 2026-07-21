"""Module 7: Factor exposure analyzer."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from momentum.core.logging import get_logger


logger = get_logger(__name__)


def _attribution_unavailable(reason: str) -> dict[str, Any]:
    """歸因 fail-closed 形：恰三鍵 status/value/reason（D-6）。"""
    return {"status": "unavailable", "value": None, "reason": reason}


def _first_non_finite_output_field(result: dict[str, Any]) -> str | None:
    """D-13：回傳第一個非有限數值欄路徑（alpha/r_squared/factor_betas.*/attribution.*）。

    intercept / unexplained 與 alpha 同值（皆 beta[0]），輸出檢查只留 alpha 即可，
    避免冗餘欄位使 mutation 測不到。
    """
    for key in ("alpha", "r_squared"):
        val = result.get(key)
        try:
            if not np.isfinite(float(val)):
                return key
        except (TypeError, ValueError):
            return key

    for group in ("factor_betas", "attribution"):
        mapping = result.get(group) or {}
        if not isinstance(mapping, dict):
            return group
        for name, val in mapping.items():
            try:
                if not np.isfinite(float(val)):
                    return f"{group}.{name}"
            except (TypeError, ValueError):
                return f"{group}.{name}"
    return None


def _index_policy_reason(portfolio_index: pd.Index, factor_index: pd.Index) -> str | None:
    """D-5 index 政策：unique + monotonic increasing + tz 一致。

    不驗 freq、允許間隙、不限索引型別（RangeIndex 可通過）。
    僅 object/mixed → index_type_uncomparable；tz 不一致 → index_tz_mismatch。
    回傳 reason 字串，通過則 None。
    """
    for idx in (portfolio_index, factor_index):
        # object / 無法可靠比較的索引
        if isinstance(idx, pd.MultiIndex):
            return "index_type_uncomparable"
        try:
            dtype = idx.dtype
        except Exception:
            return "index_type_uncomparable"
        if pd.api.types.is_object_dtype(dtype) or str(dtype) == "mixed":
            return "index_type_uncomparable"
        # ExtensionDtype object 等
        if getattr(dtype, "kind", None) == "O":
            return "index_type_uncomparable"

        if not bool(idx.is_unique):
            return "index_not_unique"
        if not bool(idx.is_monotonic_increasing):
            return "index_not_monotonic"

    # tz-awareness 一致（僅當至少一側為 DatetimeIndex 時比對）
    p_dt = isinstance(portfolio_index, pd.DatetimeIndex)
    f_dt = isinstance(factor_index, pd.DatetimeIndex)
    if p_dt and f_dt:
        p_tz = portfolio_index.tz
        f_tz = factor_index.tz
        if (p_tz is None) != (f_tz is None):
            return "index_tz_mismatch"
        if p_tz is not None and f_tz is not None and str(p_tz) != str(f_tz):
            return "index_tz_mismatch"
    return None


class FactorExposureAnalyzer:
    def __init__(self, config: dict):
        cfg = config or {}
        self._config = cfg
        self._max_single_exposure = float(cfg.get("max_single_exposure", 0.4))
        self._neutralization_mode = str(cfg.get("neutralization_mode", "none") or "none")
        self._neutralization_lookback = int(cfg.get("neutralization_lookback", 63) or 63)
        # D-7：歸因最少樣本列數（預設 10；wiring 讀 config，禁硬編碼）
        self._attribution_min_rows = int(cfg.get("attribution_min_rows", 10))

    def neutralize_factor_matrix(
        self,
        factor_values: pd.DataFrame,
        market_proxy: pd.Series,
        mode: str | None = None,
        lookback: int | None = None,
    ) -> pd.DataFrame:
        if factor_values is None or factor_values.empty:
            return pd.DataFrame()

        normalized = factor_values.apply(pd.to_numeric, errors="coerce")
        effective_mode = str(mode or self._neutralization_mode or "none")

        if effective_mode == "none":
            return normalized.fillna(0.0)
        if effective_mode == "beta_neutral":
            return self._apply_beta_neutralization(normalized, market_proxy)
        if effective_mode == "vol_neutral":
            effective_lookback = int(lookback or self._neutralization_lookback)
            return self._apply_vol_neutralization(normalized, effective_lookback)

        logger.warning("unknown neutralization mode: %s", effective_mode)
        return normalized.fillna(0.0)

    def _apply_beta_neutralization(
        self,
        factor_values: pd.DataFrame,
        market_proxy: pd.Series,
    ) -> pd.DataFrame:
        proxy = pd.to_numeric(market_proxy, errors="coerce").reindex(factor_values.index)
        if proxy.notna().sum() < 10:
            logger.warning("beta-neutral skipped: insufficient market proxy samples")
            return factor_values.fillna(0.0)

        proxy_var = float(np.nanvar(proxy.to_numpy(dtype=float)))
        if np.isclose(proxy_var, 0.0):
            logger.warning("beta-neutral skipped: market proxy variance near zero")
            return factor_values.fillna(0.0)

        neutralized = pd.DataFrame(index=factor_values.index)
        for column_name in factor_values.columns:
            feature_series = pd.to_numeric(factor_values[column_name], errors="coerce")
            aligned = pd.concat([feature_series.rename("x"), proxy.rename("m")], axis=1).dropna()
            if len(aligned) < 10:
                neutralized[column_name] = feature_series
                continue

            covariance = float(np.cov(aligned["x"].to_numpy(), aligned["m"].to_numpy(), ddof=0)[0, 1])
            beta = covariance / proxy_var if not np.isclose(proxy_var, 0.0) else 0.0
            neutralized[column_name] = feature_series - beta * proxy

        return neutralized.replace([np.inf, -np.inf], np.nan).fillna(0.0)

    def _apply_vol_neutralization(
        self,
        factor_values: pd.DataFrame,
        lookback: int,
    ) -> pd.DataFrame:
        window = max(5, int(lookback))
        rolling_std = factor_values.rolling(window=window, min_periods=max(5, window // 3)).std()
        stabilized = rolling_std.replace(0.0, np.nan)
        neutralized = factor_values / stabilized
        return neutralized.replace([np.inf, -np.inf], np.nan).fillna(0.0)

    def calculate_portfolio_exposure(
        self,
        positions: pd.Series,
        factor_values: pd.DataFrame,
    ) -> pd.Series:
        """計算時間軸加權的因子曝險（非交易持倉語意）。

        參數 ``positions`` 在 production runner 中實際為**時間軸等權平均**
        （``len(factor_values)`` = 列數／時間點數，非標的數；見 orchestrator
        的 ``equal_time_weights``）。方法簽名保留 ``positions`` 以相容既有
        caller／測試；語意為列對齊權重，**不是**多標的 portfolio 持倉。
        """
        if factor_values is None or factor_values.empty:
            return pd.Series(dtype=float)

        weights = pd.Series(positions, dtype=float).reindex(factor_values.index).fillna(0.0)
        abs_sum = float(weights.abs().sum())
        if abs_sum == 0.0:
            return pd.Series(0.0, index=factor_values.columns, dtype=float)
        if not np.isclose(abs_sum, 1.0):
            weights = weights / abs_sum

        exposure = factor_values.apply(pd.to_numeric, errors="coerce").fillna(0.0).T @ weights
        return exposure.astype(float)

    def calculate_factor_attribution(
        self,
        portfolio_returns: pd.Series,
        factor_returns: pd.DataFrame,
    ) -> dict:
        """OLS 因子歸因（含截距）；fail-closed envelope（D-5/D-6/D-7/D-8/D-10/D-13）。

        **成功（扁平 + status）**::
            {status:"ok", alpha, r_squared, intercept, unexplained,
             factor_betas, attribution}

        **失敗（恰三鍵）**::
            {status:"unavailable", value:None, reason:"..."}

        reason 全域優先序（ADV-CM8，逐項擋在 lstsq **之前**；inf 最高）::
            1. non_finite_values（輸入 inf；raw portfolio/factors，concat **前**）
            2. index 政策（D-5：unique/monotonic/tz/type）
            3. nan_rows_dropped（dropna 任一丟列）
            4. insufficient_rows
            5. insufficient_factors（因子欄 < 2）
            6. non_finite_output（計算後輸出非有限）

        成功時 ``intercept`` / ``alpha`` / ``unexplained`` 皆為 ``beta[0]``（截距）。
        ``unexplained`` 為 deprecated alias，**不是**殘差。
        **禁** fillna；**禁** try/except LinAlgError 敷衍。
        """
        portfolio = pd.Series(portfolio_returns, copy=False)
        factors = pd.DataFrame(factor_returns).copy()

        # 數值化（errors→NaN，**不** fillna）
        portfolio = pd.to_numeric(portfolio, errors="coerce")
        factors = factors.apply(pd.to_numeric, errors="coerce")

        # —— 1. 輸入端 inf（D-10；CM8 最高優先；concat **前** 對 raw 各自檢）——
        #    必須先於 index 閘門：naive+aware+inf 應回 non_finite_values，非 index_tz_mismatch。
        p_vals = portfolio.to_numpy(dtype=float, copy=False)
        f_vals = factors.to_numpy(dtype=float, copy=False)
        p_inf = np.isinf(p_vals)
        f_inf = np.isinf(f_vals)
        if bool(p_inf.any()) or bool(f_inf.any()):
            inf_count = int(np.asarray(p_inf).sum()) + int(np.asarray(f_inf).sum())
            total = int(np.asarray(p_vals).size) + int(np.asarray(f_vals).size)
            return _attribution_unavailable(f"non_finite_values:{inf_count}/{total}")

        # —— 2. index 政策（D-5；先於 dropna，避免 tz 混用製造假性 NaN 誤報）——
        index_reason = _index_policy_reason(portfolio.index, factors.index)
        if index_reason is not None:
            return _attribution_unavailable(index_reason)

        try:
            combined = pd.concat(
                [portfolio.rename("portfolio"), factors],
                axis=1,
            )
        except (TypeError, ValueError):
            # 其餘 join 不可比（理論上 index 閘門已擋多數）→ fallback
            return _attribution_unavailable("index_type_uncomparable")

        # —— 3. dropna 任一丟列 → unavailable（D-8 閾值 0）——
        total_rows = int(len(combined))
        aligned = combined.dropna()
        kept_rows = int(len(aligned))
        dropped = total_rows - kept_rows
        if dropped > 0:
            return _attribution_unavailable(f"nan_rows_dropped:{dropped}/{total_rows}")

        # —— 4. 樣本不足（D-7；讀 self._attribution_min_rows）——
        min_rows = int(self._attribution_min_rows)
        if kept_rows < min_rows:
            return _attribution_unavailable(f"insufficient_rows:{kept_rows}<{min_rows}")

        # —— 5. 因子欄 < 2（ADV-CM7）——
        factor_names = [c for c in aligned.columns if c != "portfolio"]
        n_factors = len(factor_names)
        if n_factors < 2:
            return _attribution_unavailable(f"insufficient_factors:{n_factors}<2")

        # —— OLS（此時輸入必有限、index 過關、列數與因子數已過門檻）——
        y = aligned["portfolio"].to_numpy(dtype=float, copy=False)
        x = aligned[factor_names].to_numpy(dtype=float, copy=False)
        x = np.column_stack([np.ones(len(x), dtype=float), x])

        beta, *_ = np.linalg.lstsq(x, y, rcond=None)
        y_pred = x @ beta
        residual = y - y_pred

        ss_res = float(np.sum(residual ** 2))
        ss_tot = float(np.sum((y - np.mean(y)) ** 2))
        r_squared = float(1.0 - ss_res / ss_tot) if ss_tot > 0 else 0.0

        factor_betas = {name: float(beta[idx + 1]) for idx, name in enumerate(factor_names)}
        factor_means = aligned[factor_names].mean()
        attribution = {
            name: float(factor_betas[name] * factor_means[name]) for name in factor_names
        }

        intercept = float(beta[0])
        result: dict[str, Any] = {
            "status": "ok",
            "factor_betas": factor_betas,
            "alpha": intercept,
            "r_squared": r_squared,
            "attribution": attribution,
            # intercept = 正名；unexplained = deprecated alias（同值 beta[0]，非殘差）
            "intercept": intercept,
            "unexplained": intercept,
        }

        # —— 6. 輸出端非有限（D-13；alpha/r_squared/factor_betas/attribution；
        #     intercept/unexplained 同 alpha 不重複檢）——
        output_bad = _first_non_finite_output_field(result)
        if output_bad is not None:
            return _attribution_unavailable(f"non_finite_output:{output_bad}")

        return result

    def monitor_exposure_concentration(
        self,
        exposures: pd.Series,
        max_single_exposure: float = 0.4,
    ) -> dict:
        values = pd.Series(exposures, dtype=float).fillna(0.0)
        abs_values = values.abs()
        total = float(abs_values.sum())
        if total == 0.0:
            return {
                "max_exposure_factor": None,
                "max_exposure_value": 0.0,
                "hhi": 0.0,
                "concentrated": False,
                "warnings": ["near_zero_exposures"],
            }

        normalized = abs_values / total
        hhi = float(np.sum(np.square(normalized.values.astype(float))))
        max_factor = str(normalized.idxmax())
        max_value = float(normalized.loc[max_factor])

        threshold = float(max_single_exposure or self._max_single_exposure)
        warnings: list[str] = []
        if max_value > threshold:
            warnings.append("single_factor_exposure_too_high")
        if np.all(normalized.values < 0.05):
            warnings.append("near_zero_exposures")

        return {
            "max_exposure_factor": max_factor,
            "max_exposure_value": max_value,
            "hhi": hhi,
            "concentrated": bool(max_value > threshold),
            "warnings": warnings,
        }
