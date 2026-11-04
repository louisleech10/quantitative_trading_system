"""Statistical validation utilities for IC analysis."""

from __future__ import annotations

from typing import Iterable, Optional

import numpy as np
import pandas as pd
from scipy import stats

from momentum.core.logging import get_logger


logger = get_logger(__name__)


def _hac_nan_result(n_obs: int = 0, maxlags: float = np.nan) -> dict:
    """HAC fail-closed 結果（全 NaN 統計量）。"""
    maxlags_out: float | int
    if isinstance(maxlags, (int, np.integer)) or (
        isinstance(maxlags, float) and np.isfinite(maxlags)
    ):
        maxlags_out = int(maxlags)
    else:
        maxlags_out = np.nan
    return {
        "t_stat": np.nan,
        "p_value": np.nan,
        "se": np.nan,
        "n_obs": int(n_obs),
        "maxlags": maxlags_out,
    }


def _newey_west_bartlett_se(z: np.ndarray, maxlags: int) -> float:
    """Newey-West HAC SE（Bartlett 核），對齊 statsmodels OLS intercept + HAC。

    se = sqrt(S / n)，S = γ0 + 2 Σ_j w_j γ_j，w_j = 1 - j/(L+1)，
    γ_j = (1/n) Σ_t e_t e_{t-j}，e = z - mean(z)。
    """
    n = int(z.size)
    if n < 1:
        return float("nan")
    e = z - float(np.mean(z))
    gamma0 = float(np.dot(e, e) / n)
    s = gamma0
    L = int(maxlags)
    if L < 0:
        raise ValueError(f"maxlags must be >= 0, got {maxlags}")
    for j in range(1, L + 1):
        weight = 1.0 - j / (L + 1)
        gamma_j = float(np.dot(e[j:], e[:-j]) / n)
        s += 2.0 * weight * gamma_j
    if s < 0.0:
        s = 0.0
    return float(np.sqrt(s / n))


def _spearman_contribution_z(x: np.ndarray, y: np.ndarray) -> Optional[np.ndarray]:
    """u=zscore(rank(x)), v=zscore(rank(y)), z=u*v；rank 退化回 None。"""
    if x.size < 2 or y.size < 2 or x.size != y.size:
        return None
    rx = stats.rankdata(x, method="average").astype(float)
    ry = stats.rankdata(y, method="average").astype(float)
    sx = float(np.std(rx, ddof=1))
    sy = float(np.std(ry, ddof=1))
    if sx == 0.0 or sy == 0.0 or not np.isfinite(sx) or not np.isfinite(sy):
        return None
    u = (rx - float(np.mean(rx))) / sx
    v = (ry - float(np.mean(ry))) / sy
    return u * v


#: 縱向 HAC 可用之 IC 方法（同 `global.default_method` 之 schema Literal）。
HAC_IC_METHODS: frozenset[str] = frozenset({"spearman", "pearson", "kendall"})


def _method_contribution(method: str, x: np.ndarray, y: np.ndarray) -> tuple[Optional[np.ndarray], float]:
    """(af) 逐根貢獻序列與 SE 因子：spearman／pearson 標準化乘積（因子 1）、kendall Hájek 投影（因子 2）。"""
    from momentum.Analysis.hac_ewc import KENDALL_SE_FACTOR, kendall_projection_h, pearson_contribution_z

    if method == "spearman":
        return _spearman_contribution_z(x, y), 1.0
    if method == "pearson":
        return pearson_contribution_z(x, y), 1.0
    return kendall_projection_h(x, y), KENDALL_SE_FACTOR


def _longitudinal_result(base: dict, *, ewc_dof: Optional[int], inference_status: str,
                         data_warning_detail: Optional[dict] = None,
                         persistence_not_estimable: bool = False,
                         warning_not_evaluated: bool = False) -> dict:
    """縱向逐特徵結果：共用鍵（`_hac_nan_result` 同集合）＋ ewc_dof／inference_status／data_warning／data_warning_detail。

    data_warning 封閉值：null／`small_effective_sample`（detail 為封閉八鍵）／`persistence_not_estimable`（p 可算但特徵持續性
    ρ̂ 不可估、無法判定資料是否足夠；detail 為 null）／`warning_not_evaluated`（當下記憶體不足以模擬，可重跑；detail 為 null）。
    """
    out = dict(base)
    out["ewc_dof"] = ewc_dof
    out["inference_status"] = inference_status
    if warning_not_evaluated:
        out["data_warning"] = "warning_not_evaluated"
    elif persistence_not_estimable:
        out["data_warning"] = "persistence_not_estimable"
    else:
        out["data_warning"] = "small_effective_sample" if data_warning_detail is not None else None
    out["data_warning_detail"] = data_warning_detail
    return out


def compute_hac_ic_statistics(
    features_df: pd.DataFrame,
    label: pd.Series,
    horizon: int,
    *,
    method: str,
    alpha: float,
    maxlags: Optional[int] = None,
) -> dict[str, dict]:
    """縱向第 5 段顯著性（ICPERF SPEC v5.63 ㊹）：逐根貢獻序列依所選 IC 方法，檢定依 LLSW 2018 EWC。

    - 預設（未明示 maxlags）：EWC，ν＝⌊0.4·n^(2/3)⌋、p 依 t_ν；fail-closed 只限公式不可定義
      （ν < 1 ⇒ `insufficient_sample`；一側常數或 Ω 非有限／≤ 0 ⇒ `degenerate`）。可算者照常出 p，
      另依實際 n_obs、h、方法、α、φ̂ 估資料不足警示（不改 p）。
    - 明示 maxlags：沿用 Newey–West Bartlett 固定 L 與 t(n−1)（現行行為）。

    Args:
        method: IC 方法（keyword-only、必傳；spearman／pearson／kendall）。
        alpha: 第 5 段實際顯著水準 `alpha_effective`（keyword-only、必傳；只供警示）。

    Returns:
        per-feature dict：t_stat／p_value／se／n_obs／maxlags／ewc_dof／inference_status／data_warning／data_warning_detail
    """
    if method not in HAC_IC_METHODS:
        raise ValueError(f"method must be one of {sorted(HAC_IC_METHODS)}, got {method!r}")
    if horizon is None or int(horizon) < 1:
        raise ValueError(f"horizon must be >= 1, got {horizon}")
    horizon = int(horizon)
    min_lag_floor = horizon - 1

    if maxlags is not None:
        maxlags_int = int(maxlags)
        if maxlags_int < min_lag_floor:
            raise ValueError(
                f"maxlags={maxlags_int} < horizon-1={min_lag_floor}; "
                "explicit maxlags must be >= horizon-1"
            )

    if features_df is None or label is None:
        return {}
    if not isinstance(features_df, pd.DataFrame) or features_df.shape[1] == 0:
        return {}

    alpha = float(alpha)
    if not np.isfinite(alpha):
        raise ValueError(f"alpha must be finite, got {alpha}")

    from momentum.Analysis.hac_ewc import ewc_test, ls_ar1_coefficient, small_sample_warning

    label_s = label if isinstance(label, pd.Series) else pd.Series(label)
    results: dict[str, dict] = {}

    for col in features_df.columns:
        x = features_df[col]
        pair = pd.concat([x, label_s], axis=1, join="inner").dropna()
        n_valid = int(pair.shape[0])
        x_arr = pair.iloc[:, 0].to_numpy(dtype=float)
        y_arr = pair.iloc[:, 1].to_numpy(dtype=float)

        if maxlags is not None:
            # 明示 maxlags：Newey–West Bartlett 固定 L 與 t(n−1)（現行行為；貢獻序列依方法）
            L = int(maxlags)
            if n_valid < 2 or L >= n_valid - 1 or n_valid < max(8, 2 * L):
                results[str(col)] = _longitudinal_result(
                    _hac_nan_result(n_obs=n_valid, maxlags=L), ewc_dof=None,
                    inference_status="insufficient_sample")
                continue
            z, se_factor = _method_contribution(method, x_arr, y_arr)
            se = _newey_west_bartlett_se(z, L) * se_factor if z is not None else float("nan")
            if z is None or not np.isfinite(se) or se == 0.0:
                results[str(col)] = _longitudinal_result(
                    _hac_nan_result(n_obs=n_valid, maxlags=L), ewc_dof=None, inference_status="degenerate")
                continue
            t_stat = float(float(np.mean(z)) / se)
            results[str(col)] = _longitudinal_result(
                {"t_stat": t_stat, "p_value": float(2.0 * stats.t.sf(abs(t_stat), df=n_valid - 1)),
                 "se": float(se), "n_obs": n_valid, "maxlags": int(L)},
                ewc_dof=None, inference_status="ok")
            continue

        # 預設：EWC（LLSW 2018）
        nan_base = {"t_stat": np.nan, "p_value": np.nan, "se": np.nan, "n_obs": n_valid, "maxlags": None}
        z, se_factor = (None, 1.0) if n_valid < 2 else _method_contribution(method, x_arr, y_arr)
        if n_valid < 2:
            results[str(col)] = _longitudinal_result(nan_base, ewc_dof=0, inference_status="insufficient_sample")
            continue
        if z is None:
            from momentum.Analysis.hac_ewc import ewc_dof as _ewc_dof

            nu = _ewc_dof(n_valid)
            status = "insufficient_sample" if nu < 1 else "degenerate"
            results[str(col)] = _longitudinal_result(nan_base, ewc_dof=int(nu), inference_status=status)
            continue
        test = ewc_test(z, se_factor)
        base = {"t_stat": test["t_stat"], "p_value": test["p_value"], "se": test["se"],
                "n_obs": n_valid, "maxlags": None}
        detail: Optional[dict] = None
        not_estimable = False
        not_evaluated = False
        if test["inference_status"] == "ok":
            # 警示之持續性輸入：含截距 AR(1) 最小平方估計 ρ̂，於模擬端以 Andrews (1993) 中位數不偏反演（SPEC v5.64）
            rho_hat = ls_ar1_coefficient(x_arr)
            if np.isfinite(rho_hat):
                try:
                    detail = small_sample_warning(n_valid, horizon, method, alpha, rho_hat)
                except MemoryError as exc:  # 預檢之 WarningSimulationMemoryError 與實際配置失敗皆然：可重試，警示未執行，p／q 照常（SPEC v5.68、r94）
                    logger.warning("資料不足警示未執行（記憶體不足，可重跑）：%s／%s", col, exc)
                    not_evaluated = True
            else:
                not_estimable = True  # 滯後段常數等致 ρ̂ 不可估：p 照常，警示判定不可用（SPEC v5.67）
        results[str(col)] = _longitudinal_result(
            base, ewc_dof=test["ewc_dof"], inference_status=test["inference_status"], data_warning_detail=detail,
            persistence_not_estimable=not_estimable, warning_not_evaluated=not_evaluated)

    return results


# 生產 FDR 唯一 canonical 方法（D-F/D-G）；三層契約恆等集合
# apply_fdr / SignificanceFdrSchema / _resolve_fdr_method 接受集合必須 == {"fdr_bh"}
# exact-whitelist：禁 .strip()/.lower()/str 正規化；禁 silent raw-p 降級
_ALLOWED_FDR_METHODS: frozenset[str] = frozenset({"fdr_bh"})


def apply_fdr(
    p_values: dict[str, float],
    alpha: float,
    *,
    method: str = "fdr_bh",
) -> tuple[dict[str, float], int]:
    """FDR 應用層：finite p 子集校正，NaN 保位；不做 α 比較。

    Args:
        p_values: feature → raw p
        alpha: 保留簽名供下游消費；本函式不依 α 過濾
        method: 必須**精確**等於 ``"fdr_bh"``（三層白名單恆等）。
            不接受大小寫變體、前後空白、顯式 ``None``、空字串、非字串或任何
            其他值；函式參數缺省 ``"fdr_bh"`` 僅表達缺鍵語意，與顯式 ``None``
            不同。亦不做 ``.strip()`` / ``.lower()`` 正規化（fail-closed）。

    Returns:
        (q_values, n_tests)；n_tests = finite p 個數

    Raises:
        ValueError: method 不是精確 ``"fdr_bh"`` 時（避免對外謊報 p_value_adj 已校正）
    """
    del alpha  # 不做 α 比較；參數保留供 API 相容
    # exact match only — 與 schema Literal / _resolve_fdr_method 接受集合恆等
    if method not in _ALLOWED_FDR_METHODS:
        raise ValueError(
            f"Unsupported FDR method={method!r}; canonical only: exact 'fdr_bh' "
            "(fail-closed: no strip/lower/normalize; no silent raw-p fallback)"
        )

    if not p_values:
        return {}, 0

    finite: dict[str, float] = {}
    for key, value in p_values.items():
        try:
            fv = float(value)
        except (TypeError, ValueError):
            continue
        if np.isfinite(fv):
            finite[key] = fv

    n_tests = len(finite)
    if n_tests == 0:
        return {key: np.nan for key in p_values}, 0

    # 白名單已通過；交既有 adjust_multiple_comparisons（本體不動，B1 禁項）
    adjusted = StatisticalValidator({}).adjust_multiple_comparisons(
        finite, method=method
    )

    q_values: dict[str, float] = {}
    for key, value in p_values.items():
        try:
            fv = float(value)
        except (TypeError, ValueError):
            q_values[key] = np.nan
            continue
        if np.isfinite(fv):
            q_values[key] = float(adjusted[key])
        else:
            q_values[key] = np.nan
    return q_values, n_tests


class StatisticalValidator:
    """Stage 5 (部分): IC 統計驗證。"""

    def __init__(self, config: dict):
        self._config = config or {}
        self._default_p_value_max = float(self._config.get("p_value_max", 0.05))

    def compute_pooled_ic_statistics_deprecated(
        self, rolling_ic_dict: dict
    ) -> dict[str, dict]:
        """【已棄用】多窗 rolling IC 串接 + i.i.d. t-test。

        僅供語意遷移測試對照；生產路徑必須使用 compute_hac_ic_statistics。
        舊名 compute_ic_statistics 已移除，不得再被生產 import。
        """

        stats_results: dict[str, dict] = {}
        for feature, windows in (rolling_ic_dict or {}).items():
            values = self._collect_values(windows)
            ic_stats = self._compute_stats(values)
            stats_results[feature] = ic_stats
        return stats_results

    def adjust_multiple_comparisons(
        self, p_values: dict, method: str = "fdr_bh"
    ) -> dict[str, float]:
        """多重比較校正 (Bonferroni / FDR)。"""

        if not p_values:
            return {}

        method = (method or "").lower()
        if method == "bonferroni":
            return self._bonferroni(p_values)
        if method in {"fdr_bh", "fdr"}:
            return self._fdr_bh(p_values)

        logger.warning("Unknown adjustment method=%s, return raw p-values", method)
        return {key: float(value) for key, value in p_values.items()}

    def _collect_values(self, windows: object) -> np.ndarray:
        if windows is None:
            return np.array([], dtype=float)
        if isinstance(windows, dict):
            values: list[float] = []
            for _, series in sorted(windows.items()):
                values.extend(self._to_list(series))
            return np.array(values, dtype=float)
        return np.array(self._to_list(windows), dtype=float)

    @staticmethod
    def _to_list(values: object) -> list[float]:
        if values is None:
            return []
        if isinstance(values, np.ndarray):
            return values.astype(float).tolist()
        if isinstance(values, (list, tuple, pd.Series)):
            return pd.Series(values).astype(float).tolist()
        return [float(values)]

    def _compute_stats(self, values: np.ndarray) -> dict:
        values = values[np.isfinite(values)]
        n_obs = int(values.size)
        if n_obs < 2:
            return {
                "t_stat": np.nan,
                "p_value": np.nan,
                "ci_lower": np.nan,
                "ci_upper": np.nan,
                "n_observations": n_obs,
            }

        mean = float(np.mean(values))
        std = float(np.std(values, ddof=1))
        if std == 0:
            return {
                "t_stat": np.nan,
                "p_value": np.nan,
                "ci_lower": np.nan,
                "ci_upper": np.nan,
                "n_observations": n_obs,
            }

        t_stat = float(mean / (std / np.sqrt(n_obs)))
        ttest = stats.ttest_1samp(values, 0.0, nan_policy="omit")
        p_value = float(ttest.pvalue)
        ci_lower, ci_upper = self._confidence_interval(mean, std, n_obs)
        return {
            "t_stat": t_stat,
            "p_value": p_value,
            "ci_lower": ci_lower,
            "ci_upper": ci_upper,
            "n_observations": n_obs,
        }

    @staticmethod
    def _confidence_interval(
        mean: float, std: float, n_obs: int, alpha: float = 0.05
    ) -> tuple[float, float]:
        if n_obs < 2 or std == 0:
            return np.nan, np.nan
        t_crit = stats.t.ppf(1 - alpha / 2, df=n_obs - 1)
        margin = t_crit * std / np.sqrt(n_obs)
        return float(mean - margin), float(mean + margin)

    @staticmethod
    def _bonferroni(p_values: dict) -> dict[str, float]:
        total = len(p_values)
        adjusted: dict[str, float] = {}
        for key, value in p_values.items():
            adj = min(float(value) * total, 1.0)
            adjusted[key] = adj
        return adjusted

    @staticmethod
    def _fdr_bh(p_values: dict) -> dict[str, float]:
        """Benjamini–Hochberg 校正：委派業界標準 `statsmodels.stats.multitest.multipletests(method="fdr_bh")`
        （ICPERF Task 0.2 v5.59 (ah)；使用者 2026-11-02「為何不直接套用業界標準函式庫就好？」——改前為自寫 p·n／rank 之
        逆向累積最小值，與 statsmodels 於末位浮點可不同）。

        檢定集合＝有限 p（NaN／±inf 保位為 NaN、不入集合，同 `apply_fdr` 之 NaN 保位）；值不可轉 float ⇒ 照舊 raise。"""
        from statsmodels.stats.multitest import multipletests

        values = {key: float(value) for key, value in p_values.items()}
        finite_keys = [key for key, value in values.items() if np.isfinite(value)]
        adjusted: dict[str, float] = {key: float("nan") for key in values}
        if finite_keys:
            q = multipletests([values[key] for key in finite_keys], method="fdr_bh")[1]
            for key, value in zip(finite_keys, q):
                adjusted[key] = float(value)
        return adjusted
