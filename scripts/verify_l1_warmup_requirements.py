"""
verify_l1_warmup_requirements.py

Empirically determine the MINIMUM warmup bars K required for each L1 output
point to converge to its "infinite history" value, and write the warmup table
``momentum/FeatureEngineering/atomic/warmup_table.yaml``.

FF-STAT Task 2.4（docs/FFSTAT_SPEC.md v32–v45；R4、R5、R9）
-----------------------------------------------------------
- 量測對象＝生產實際之計算路徑：TA-Lib 指標之參數取各引擎 ``_resolve_params``（預設設定
  ``ConfigManager().get_merged_config()``；未在設定之 TA-Lib 註冊指標以其預設參數或 13/55/233），
  單輸入指標於 close／volume／taker_ratio 各量；自訂欄（Keltner 等）、進階 atomic（microstructure、
  entropy、tail_risk）呼叫其引擎之計算函式（未遮罩）；CDL＊ 合為具名條目 ``CDL_PATTERN``。
- 3 標的 × 5 週期（5m、1h、4h、12h、1d）；1h／4h 讀 ``data_cache/feature_klines``，5m／12h／1d 讀長歷史
  快取 ``data_cache/feature_klines_longhist``（真實 Binance 資料，不做連續性檢查）。
- 誤差：評估窗（末 ``eval_window`` 根）內 max|test−gt| / max(P75|gt|, std(gt))；評估窗內 ground truth
  有限而 test 非有限 ⇒ inf（finite guard，v33）。整數輸出（CDL、HT_TRENDMODE）任一不符即不收斂。
- 可信度：量得 K 須 ≤ eval_start/2（ground truth 自身前史 ≥ 2K），否則該筆記 ``reliable: false``；可信度只作證據欄，
  採用值依 SPEC v47 取「已收斂」量測（含不可信者，其為實測下界）。
- 採用值：有參數者 ``recommended_factor``＝各週期各標的已收斂量測之 K/max(period_keys 值) 之最大（無條件進位
  至 0.01、下限 1.0）；無參數者 ``k``＝已收斂量測之 K 最大；累積型（OBV、AD）登記而不給係數；由元件組成之
  自訂欄（Keltner＝EMA＋ATR 等）之係數不得低於其元件之採用係數。
- 收據：逐（指標、參數、來源、標的、週期）記量得 K、test／ground truth 有限值數、誤差、可信與否。

Run
---
PYTHONPATH=. venv/bin/python scripts/verify_l1_warmup_requirements.py \
    [--timeframes 5m 1h 4h 12h 1d] [--symbols BTCUSDT ETHUSDT ADAUSDT] \
    [--output momentum/FeatureEngineering/atomic/warmup_table.yaml] \
    [--receipt handoffs/run_receipts/<日期>-ffstat-warmup-measure.json]
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import math
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import h5py
import numpy as np
import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

KLINE_DIR = PROJECT_ROOT / "data_cache" / "feature_klines"
LONGHIST_DIR = PROJECT_ROOT / "data_cache" / "feature_klines_longhist"
KLINE_PATH = KLINE_DIR / "kline_cache.h5"
DEFAULT_SYMBOL = "ETHUSDT"
DEFAULT_TF = "1h"
DEFAULT_OUTPUT = PROJECT_ROOT / "momentum" / "FeatureEngineering" / "atomic" / "warmup_table.yaml"
DEFAULT_SYMBOLS = ["BTCUSDT", "ETHUSDT", "ADAUSDT"]
DEFAULT_TIMEFRAMES = ["5m", "1h", "4h", "12h", "1d"]
LONGHIST_TIMEFRAMES = {"5m", "4h", "12h", "1d"}  # 4h：v53 起用長歷史（BTC 19,963 根），逐起點驗證之起點較多
TEST_PERIODS = [13, 55, 233]
SOURCES = ["close", "volume", "taker_ratio"]

# 參數字典中屬「週期」之鍵（其餘如 matype、nbdev、acceleration、fastlimit、alpha 不是週期）
PERIOD_KEY_NAMES = {
    "timeperiod", "fastperiod", "slowperiod", "signalperiod", "fastk_period", "slowk_period", "slowd_period",
    "fastd_period", "timeperiod1", "timeperiod2", "timeperiod3", "periods", "window", "n_buckets", "sigma_window",
}

# 條目之 family（細類）；warmup_class 由此導出：window_only ⇒ window_only；cumulative；pattern；其餘 ⇒ recursive
FAMILY = {
    "EMA": "ema_seeded", "DEMA": "compound_ema", "TEMA": "compound_ema", "T3": "compound_ema", "TRIX": "compound_ema",
    "KAMA": "adaptive_ema", "MAMA": "adaptive_ema", "MA": "window_only", "SMA": "window_only", "WMA": "window_only",
    "TRIMA": "window_only", "MIDPOINT": "window_only", "MIDPRICE": "window_only", "MAVP": "window_only",
    "BBANDS": "window_only", "HT_TRENDLINE": "hilbert", "HT_DCPERIOD": "hilbert", "HT_DCPHASE": "hilbert",
    "HT_PHASOR": "hilbert", "HT_SINE": "hilbert", "HT_TRENDMODE": "hilbert", "SAR": "stateful_pivot",
    "SAREXT": "stateful_pivot", "RSI": "wilder", "ADX": "wilder", "ADXR": "wilder", "DX": "wilder",
    "PLUS_DI": "wilder", "MINUS_DI": "wilder", "PLUS_DM": "wilder", "MINUS_DM": "wilder", "CMO": "wilder",
    "MFI": "window_only", "ATR": "wilder", "NATR": "wilder", "ULTOSC": "window_only", "MACD": "compound_ema",
    "MACDEXT": "compound_ema", "MACDFIX": "compound_ema", "APO": "compound_ema", "PPO": "compound_ema",
    "STOCH": "window_only", "STOCHF": "window_only", "STOCHRSI": "wilder", "CCI": "window_only",
    "MOM": "window_only", "ROC": "window_only", "ROCP": "window_only", "ROCR": "window_only",
    "ROCR100": "window_only", "AROON": "window_only", "AROONOSC": "window_only", "WILLR": "window_only",
    "BOP": "window_only", "TRANGE": "window_only", "OBV": "cumulative", "AD": "cumulative",
    "ADOSC": "cumulative_diff_ema", "LINEARREG": "window_only", "LINEARREG_SLOPE": "window_only",
    "LINEARREG_ANGLE": "window_only", "LINEARREG_INTERCEPT": "window_only", "TSF": "window_only",
    "STDDEV": "window_only", "VAR": "window_only", "BETA": "window_only", "CORREL": "window_only",
    "CDL_PATTERN": "pattern", "KELTNER": "compound_ema", "DONCHIAN": "window_only", "PARKINSON_VOL": "window_only",
    "GARMANKLASS_VOL": "window_only", "VWAP": "window_only", "VOLUME_MA_RATIO": "window_only",
    "FORCE_INDEX": "ema_seeded", "KLINGER_VOLUME_OSC": "compound_ema", "EASE_OF_MOVEMENT": "window_only",
    "MS_AMIHUD_ILLIQ": "window_only", "MS_KYLE_LAMBDA": "window_only", "MS_ROLL_SPREAD": "window_only",
    "MS_CS_SPREAD": "window_only", "MS_OFI_RAW": "window_only", "MS_LARGE_TRADE_RATIO": "window_only",
    "MS_VPIN": "window_only", "ENT_SHANNON": "window_only", "ENT_APEN": "window_only", "ENT_SAMPEN": "window_only",
    "ENT_FRACTAL_DIM": "window_only", "ENT_HURST": "window_only", "ENT_PERM": "window_only",
    "TR_CVAR": "window_only", "TR_RV_UP": "window_only", "TR_RV_DOWN": "window_only", "TR_RSJ": "window_only",
    "TR_UD_VOL_RATIO": "window_only", "TR_GPR": "window_only", "TR_JB": "window_only", "TR_MDD": "window_only",
}
CUMULATIVE = {"OBV", "AD"}
# 由元件組成之自訂欄：採用係數不得低於元件之採用係數（無參數者以元件係數×其週期為 k 下限）
COMPONENT_FLOOR = {"KELTNER": ("EMA", "ATR"), "FORCE_INDEX": ("EMA",)}
COMPONENT_K_FLOOR = {"KLINGER_VOLUME_OSC": ("EMA", 55)}


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
def load_klines(symbol: str = DEFAULT_SYMBOL, tf: str = DEFAULT_TF,
                cache_dir: Optional[Path] = None) -> Dict[str, np.ndarray]:
    """Load klines as a dict of float64 arrays.

    ``cache_dir``：K 線快取目錄（內含 ``kline_cache.h5``）；None ⇒ ``data_cache/feature_klines``。
    FF-STAT v40：5m／12h／1d 之倍數量測讀長歷史快取 ``data_cache/feature_klines_longhist``
    （真實 Binance 資料，含真實缺口，量測不做連續性檢查）。
    """
    path = (Path(cache_dir) / "kline_cache.h5") if cache_dir is not None else KLINE_PATH
    if not path.exists():
        raise FileNotFoundError(f"Kline cache not found: {path}")
    with h5py.File(path, "r") as f:
        rec = f[f"{symbol}/{tf}/data"][:]
    out = {name: rec[name].astype(np.float64) for name in rec.dtype.names if name != "timestamp"}
    if "number_of_trades" in out and "trades" not in out:
        out["trades"] = out["number_of_trades"]  # 與 crypto_spot_adapter 同一換名
    return out


def load_frame(symbol: str, tf: str) -> pd.DataFrame:
    cache_dir = LONGHIST_DIR if tf in LONGHIST_TIMEFRAMES else KLINE_DIR
    return pd.DataFrame(load_klines(symbol, tf, cache_dir))


# ---------------------------------------------------------------------------
# Error metric and convergence search
# ---------------------------------------------------------------------------
def scale_normalized_error(test: np.ndarray, gt: np.ndarray, integer: bool) -> float:
    """Max absolute deviation normalized by the indicator's *robust scale* over the evaluation window.

      err = max|test - gt|  /  max( P75(|gt|),  std(gt),  floor )
    """
    # FF-STAT v33 finite guard：評估窗內 ground truth 有限而 test 非有限 ⇒ 尚未收斂，誤差為 inf
    # （原以 NaN 遮除後計算，r13 真實 12h 探針顯示 DEMA／TEMA／T3 於 test 尚有 NaN 時被接受）
    if bool((np.isfinite(gt) & ~np.isfinite(test)).any()):
        return np.inf
    mask = ~(np.isnan(gt) | np.isnan(test))
    if mask.sum() == 0:
        return np.inf
    if integer:
        # boolean / signed integer output - any mismatch counts
        return float((test[mask] != gt[mask]).any())
    gt_v = gt[mask]
    diff = np.abs(test[mask] - gt_v)
    max_abs_diff = float(diff.max())
    p75 = float(np.percentile(np.abs(gt_v), 75))
    std = float(np.std(gt_v))
    scale = max(p75, std, 1e-8)
    return max_abs_diff / scale


_P75_KERNEL: Dict[str, Any] = {}


def rolling_abs_p75_lower_bound(values: np.ndarray, window: int) -> np.ndarray:
    """逐起點 s 之 ``P75(|values[s:s+window]| 之非 NaN 者)`` 保守下界（回傳長度 n−window+1）。

    供 `verify_exhaustive` 之判定捷徑：scale＝max(P75, std, 1e-8) ≥ 本下界，故 max|Δ| / 下界 < 門檻即必合格；
    窗內含 ±inf 或全 NaN 者回 0（捷徑不適用，改走原式）。以滑動有序緩衝求與 ``np.percentile``（linear）同式之值，
    再乘 (1−1e-9) 吸收與 numpy 逐位元之捨入差（量級 1e-15），保證不大於 numpy 之值。"""
    if "k" not in _P75_KERNEL:
        import numba

        @numba.njit(cache=True)
        def kernel(vals: np.ndarray, w: int) -> np.ndarray:
            n = vals.shape[0]
            m_out = n - w + 1
            out = np.zeros(max(m_out, 0))
            if m_out <= 0:
                return out
            buf = np.empty(w + 1)
            size = 0
            infs = 0
            for t in range(n):
                v = vals[t]
                if np.isinf(v):
                    infs += 1
                elif not np.isnan(v):
                    a = abs(v)
                    k = size
                    while k > 0 and buf[k - 1] > a:
                        buf[k] = buf[k - 1]
                        k -= 1
                    buf[k] = a
                    size += 1
                if t >= w:
                    old = vals[t - w]
                    if np.isinf(old):
                        infs -= 1
                    elif not np.isnan(old):
                        a = abs(old)
                        k = 0
                        while k < size and buf[k] != a:
                            k += 1
                        for j in range(k, size - 1):
                            buf[j] = buf[j + 1]
                        size -= 1
                if t < w - 1 or infs > 0 or size == 0:
                    continue
                pos = 0.75 * (size - 1)
                lo = int(np.floor(pos))
                hi = min(lo + 1, size - 1)
                frac = pos - lo
                out[t - w + 1] = (buf[lo] + frac * (buf[hi] - buf[lo])) * (1.0 - 1e-9)
            return out

        _P75_KERNEL["k"] = kernel
    return _P75_KERNEL["k"](np.ascontiguousarray(values, dtype=np.float64), int(window))


@dataclass
class Case:
    """一次計算呼叫（一組已解析參數、一個來源）；``fn(frame) -> [各輸出陣列]``。"""
    params: Dict[str, Any]
    fn: Callable[[pd.DataFrame], List[np.ndarray]]
    source: str = ""
    integer: bool = False
    gt_history: Optional[int] = None  # None ⇒ 以全歷史為 ground truth；窗型自訂欄限定前史以省時
    # K 下限：TA-Lib 之 lookback（首個有效輸出之位置）。CDL＊ 於 lookback 內輸出 0 而非 NaN、形態又罕見，
    # 短前史常「碰巧相符」⇒ 量測值不可信，以 lookback 為下限
    k_floor: int = 0


@dataclass
class Entry:
    name: str
    period_keys: Tuple[str, ...]
    cases: List[Case] = field(default_factory=list)

    @property
    def family(self) -> str:
        return FAMILY.get(self.name, "recursive")

    @property
    def warmup_class(self) -> str:
        if self.name in CUMULATIVE:
            return "cumulative"
        if self.family == "pattern":
            return "pattern"
        return "window_only" if self.family == "window_only" else "recursive"


def _k_candidates(start: int, cap: int) -> List[int]:
    values: List[int] = []
    k = max(start, 1)
    while k <= cap:
        values.append(k)
        k = max(k + 1, int(k * 1.10))
    for mult in (1, 2, 3, 5, 8, 12, 16, 20):
        values.append(max(start, 1) * mult)
    return sorted({v for v in values if 1 <= v <= cap})


def measure_case(case: Case, frame: pd.DataFrame, eval_window: int, threshold: float, cap: int,
                 start: int, positions: int = 1) -> Dict[str, Any]:
    """FFSTAT v52（審查 r35 兩家 P1）：多評估窗協定——於序列內取 ``positions`` 個等距評估窗（末窗恆為序列尾端；
    其餘評估窗起點介於 ``eval_window`` 與尾端之間），逐窗求最小 K，取最大。改前只量末窗一處，而所需 K 隨起點之
    種子誤差而變（真實 BTC／ETH 1h RSI 14 於 40 個起點 23–87 根，表值 66）。

    逐窗之 K 搜尋上限為該窗 ground truth 前史之一半（前史 < 2K 之窗其 ground truth 本身未收斂，於 k＝前史時
    test 與 ground truth 同式而假收斂）；某窗於上限內未收斂 ⇒ 該窗記 ``insufficient``，不入最大值；
    全部窗皆 insufficient 時退回單窗（末窗、原上限）之結果。回傳欄位同單窗版，另加 ``per_position``。"""
    n = len(frame)
    if positions <= 1:
        return _measure_window(case, frame, n, eval_window, threshold, cap, start)
    last_start = n - eval_window
    first_start = min(last_start, max(eval_window, 2 * max(start, 1)))
    starts = sorted({int(round(s)) for s in np.linspace(first_start, last_start, positions)})
    results = []
    for s in starts:
        res = _measure_window(case, frame, s + eval_window, eval_window, threshold, cap, start, half_history_cap=True)
        results.append({"eval_start": s, **res})
    usable = [r for r in results if r["converged"]]
    if not usable:
        tail = _measure_window(case, frame, n, eval_window, threshold, cap, start)
        tail["per_position"] = [{"eval_start": r["eval_start"], "k": r["k"], "err": r["err"],
                                 "converged": r["converged"]} for r in results]
        return tail
    best = max(usable, key=lambda r: r["k"])
    out = {k: v for k, v in best.items() if k != "eval_start"}
    out["reliable"] = bool(all(r["reliable"] for r in usable))
    out["per_position"] = [{"eval_start": r["eval_start"], "k": r["k"], "err": r["err"], "converged": r["converged"]}
                           for r in results]
    return out


def verify_exhaustive(case: Case, frame: pd.DataFrame, k: int, eval_window: int, threshold: float,
                      cap: int, deadline: Optional[float] = None, label: str = "") -> Dict[str, Any]:
    """FFSTAT v53 提案（審查 r36 兩家 P1：等距多窗無任意起點保證）：逐可採起點窮舉驗證。

    對每個起點 s（s ≥ 2K 使 ground truth 自身已有 ≥ 2K 前史；s ≤ n−eval_window）以 ``frame[s−K : s+eval_window]``
    計算、比對同一判準（``scale_normalized_error``）之 ground truth 於 [s, s+eval_window)。
    掃描中遇不合 ⇒ K 升至下一候選（×1.10、至少 +1）並自同一起點續掃；掃畢後以最終 K 對全部起點做確認輪，
    確認輪仍有不合即再升 K 重做確認輪，直至全數合格或達 ``cap``。回傳最終 K 與逐輪統計（起點數、不合數、最差誤差
    與其起點）。
    加速而不改判定：①TA-Lib 快路徑（整序列輸入一次備妥、逐起點切片直呼；啟用前以生產路徑於抽樣起點自檢逐位元組
    相等，不等即改走生產路徑）；②判定捷徑——scale＝max(P75, std, 1e-8) ≥ max(std, 1e-8)，故 max|Δ| < 門檻×max(std,
    1e-8) 即必合格，只有未能以此判定者才算 P75（與 ``scale_normalized_error`` 同式）；③同理以逐起點 P75 下界
    （`rolling_abs_p75_lower_bound`，每 case 一次）先判；④確認輪沿用掃描輪中已以最終 K 判定之起點（不重算）。
    ②③④ 經改前／改後逐項比對（K、合格、最差誤差與其起點、起點數）相同。"""
    n = len(frame)
    fast = None
    factory = getattr(case.fn, "fast_factory", None)
    if factory is not None and case.gt_history is None and not case.integer:
        fast = factory(frame)
        if fast is not None:
            for s in sorted({max(0, n // 3), max(0, n // 2), max(0, n - eval_window - 1 - 2 * int(k))}):
                b = min(n, s + int(k) + eval_window)
                ref = [np.asarray(a, dtype=np.float64) for a in case.fn(frame.iloc[s:b])]
                got = fast(s, b)
                if len(ref) != len(got) or not all(np.array_equal(r, g, equal_nan=True) for r, g in zip(ref, got)):
                    fast = None
                    break

    def compute(a: int, b: int) -> List[np.ndarray]:
        if fast is not None:
            return fast(a, b)
        return [np.asarray(x, dtype=np.float64) for x in case.fn(frame.iloc[a:b])]

    # ground truth 一律取全歷史（表之原則即「對無限歷史之 ground truth」）。多窗量測之 ``gt_history``
    # （窗型自訂欄限前史 400／600 根以省時）於此不用：全歷史 ground truth 較嚴，且整段一次算畢、不必逐起點重算。
    gt_full = compute(0, n)
    # 逐起點 P75 下界（只依 ground truth、與 K 無關，每 case 算一次）：窗內 ground truth 無 ±inf 時，
    # 通過有限性檢查後之 mask 恰為 ~isnan(gt)，故下界 ≤ scale_normalized_error 之 scale。
    p75_lb = None if case.integer else [rolling_abs_p75_lower_bound(g, eval_window) for g in gt_full]

    def error_at(s: int, kk: int, known_worst: float = float("inf")) -> float:
        """誤差；若可證其 < 門檻且 ≤ known_worst，回傳上界（不影響判定與最差值）以省 P75。"""
        gts = [g[s:s + eval_window] for g in gt_full]
        try:
            outs = compute(s - kk, s + eval_window)
        except Exception:  # noqa: BLE001 — 過短輸入
            return float("inf")
        worst = 0.0
        for idx, (t_full, g) in enumerate(zip(outs, gts)):
            t = t_full[-eval_window:]
            if case.integer:
                worst = max(worst, scale_normalized_error(t, g, True))
                continue
            if bool((np.isfinite(g) & ~np.isfinite(t)).any()):
                return float("inf")
            mask = ~(np.isnan(g) | np.isnan(t))
            if not mask.any():
                return float("inf")
            gv = g[mask]
            max_abs = float(np.abs(t[mask] - gv).max())
            if p75_lb is not None and len(t) == eval_window and s < len(p75_lb[idx]) and p75_lb[idx][s] > 0:
                upper = max_abs / max(float(p75_lb[idx][s]), 1e-8)
                if upper < threshold and upper <= max(worst, known_worst):
                    worst = max(worst, min(upper, known_worst)) if upper <= known_worst else worst
                    continue  # 同下方 std 捷徑：scale ≥ P75 下界 ⇒ 真誤差 ≤ upper
            lower_scale = max(float(np.std(gv)), 1e-8)
            upper = max_abs / lower_scale
            if upper < threshold and upper <= max(worst, known_worst):
                worst = max(worst, min(upper, known_worst)) if upper <= known_worst else worst
                continue  # 必合格且不影響最差值（scale ≥ lower_scale ⇒ 真誤差 ≤ upper）
            worst = max(worst, scale_normalized_error(t, g, False))
        return worst

    def check_deadline(s: int) -> None:
        """逐項執行預算（v55，審查 r39 codex P1-04；r40 codex P1-01 改每個起點查）：超過即拋 `TaskBudgetExceeded`。
        實際耗時上界＝預算＋單一起點之一次計算（查核本身約 0.1 微秒，相對單次計算可忽略）。"""
        if deadline is not None and time.time() > deadline:
            raise TaskBudgetExceeded(f"{label} 超過逐項預算（起點 {s}／{n - eval_window}）")

    def bump(kk: int) -> int:
        return min(cap, max(kk + 1, int(kk * 1.10)))

    rounds: List[Dict[str, Any]] = []
    k = max(int(k), 1)
    # 掃描輪：遇不合即升 K、自同一起點續掃。最後一次升 K 之後所掃之起點 [seg_lo, seg_hi) 已以最終 K 判定合格，
    # 其最差值與起點一併記下，確認輪沿用而不重算（同一起點、同一 K、同一判定式，結果必同）。
    s = 2 * k
    scan_fails = 0
    k_start = k
    seg_lo, seg_worst, seg_worst_start = s, 0.0, None
    while s <= n - eval_window and k < cap:
        check_deadline(s)
        err = error_at(s, k, seg_worst)
        if not err < threshold:
            scan_fails += 1
            k = bump(k)
            s = max(s, 2 * k)
            seg_lo, seg_worst, seg_worst_start = s, 0.0, None
            continue
        if err > seg_worst:
            seg_worst, seg_worst_start = err, s
        s += 1
    seg_hi = s if k < cap else seg_lo  # 升至 cap 而中止者：該 K 未掃過任何起點
    rounds.append({"phase": "scan", "k_from": k_start, "k": k, "fails": scan_fails})
    # 確認輪：最終 K 對全部可採起點。首輪之 [seg_lo, seg_hi) 沿用掃描輪結果（依起點順序併入最差值，
    # 與逐點重算之最差值及其起點相同）；確認輪有不合而再升 K 者，下一輪全數重算。
    reuse: Optional[Tuple[int, int, float, Optional[int]]] = (seg_lo, seg_hi, seg_worst, seg_worst_start)
    while True:
        worst, worst_start, fails, checked, reused = 0.0, None, 0, 0, 0
        s = 2 * k
        while s <= n - eval_window:
            check_deadline(s)
            if reuse is not None and s == reuse[0] and reuse[1] > reuse[0]:
                reused = reuse[1] - reuse[0]
                checked += reused
                if reuse[2] > worst:
                    worst, worst_start = reuse[2], reuse[3]
                s = reuse[1]
                continue
            err = error_at(s, k, worst)
            checked += 1
            if err > worst:
                worst, worst_start = err, s
            if not err < threshold:
                fails += 1
            s += 1
        rounds.append({"phase": "confirm", "k": k, "starts": checked, "reused_from_scan": reused, "fails": fails,
                       "worst": worst if np.isfinite(worst) else None, "worst_start": worst_start})
        reuse = None
        if fails == 0 or k >= cap:
            break
        k = bump(k)
    # b4 審碼 r1 codex P1-01：可採起點集合為空（2K > n−評估窗）⇒ 零次檢查不得記為通過
    no_starts = rounds[-1].get("starts", 0) == 0
    return {"k": k, "passed": (not no_starts) and rounds[-1]["fails"] == 0, "no_admissible_starts": no_starts,
            "fast_path": fast is not None, "rounds": rounds}


def _measure_window(case: Case, frame: pd.DataFrame, eval_end: int, eval_window: int, threshold: float, cap: int,
                    start: int, half_history_cap: bool = False) -> Dict[str, Any]:
    """最小 K 使 case 於 ``frame[eval_start−K : eval_end]`` 之評估窗輸出與 ground truth 相符（單一評估窗）。"""
    frame = frame.iloc[:eval_end]
    n = len(frame)
    eval_end = n
    eval_start = n - eval_window
    gt_lo = 0 if case.gt_history is None else max(0, eval_start - case.gt_history)
    gt_outputs = [np.asarray(a, dtype=np.float64)[-eval_window:] for a in case.fn(frame.iloc[gt_lo:eval_end])]
    max_k = min(cap, eval_start - gt_lo - 1)
    if half_history_cap:
        max_k = min(max_k, (eval_start - gt_lo) // 2)
    best = {"k": -1, "err": float("inf"), "test_finite": 0}
    for k in _k_candidates(start, max_k):
        try:
            outs = case.fn(frame.iloc[eval_start - k:eval_end])
        except Exception:  # noqa: BLE001 — 部分指標拒收過短輸入
            continue
        tails = [np.asarray(a, dtype=np.float64)[-eval_window:] for a in outs]
        err = max(scale_normalized_error(t, g, case.integer) for t, g in zip(tails, gt_outputs))
        finite = int(sum(np.isfinite(t).sum() for t in tails))
        if err < best["err"]:
            best = {"k": k, "err": err, "test_finite": finite}
        if err < threshold:
            best = {"k": k, "err": err, "test_finite": finite}
            break
    gt_finite = int(sum(np.isfinite(g).sum() for g in gt_outputs))
    converged = best["k"] > 0 and best["err"] < threshold
    if converged and best["k"] < case.k_floor:
        best["k"] = case.k_floor
    return {
        "k": int(best["k"]) if converged else None,
        "k_floor": case.k_floor,
        "err": float(best["err"]) if np.isfinite(best["err"]) else None,
        "converged": bool(converged),
        "reliable": bool(converged and best["k"] <= (eval_start - gt_lo) // 2),
        "test_finite": best["test_finite"] if converged else None,
        "gt_finite": gt_finite,
        "gt_history": eval_start - gt_lo,
    }


# ---------------------------------------------------------------------------
# Catalog：生產實際之 L1 計算路徑
# ---------------------------------------------------------------------------
def _period_keys(params_list: Sequence[Dict[str, Any]]) -> Tuple[str, ...]:
    keys = set()
    for params in params_list:
        keys |= {k for k in params if k in PERIOD_KEY_NAMES}
    return tuple(sorted(keys))


def _talib_fn(name: str, params: Dict[str, Any], source: str) -> Callable[[pd.DataFrame], List[np.ndarray]]:
    from momentum.FeatureEngineering.atomic.talib_wrapper import TALibWrapper

    def fn(frame: pd.DataFrame) -> List[np.ndarray]:
        out = TALibWrapper.compute(name, frame, dict(params), source or "close")
        return [out[c].to_numpy(dtype=np.float64) for c in out.columns]

    def fast_factory(frame: pd.DataFrame) -> Optional[Callable[[int, int], List[np.ndarray]]]:
        """逐起點驗證之快路徑（FFSTAT v53）：整條序列之 TA-Lib 輸入一次備妥、逐起點切片直呼同一 TA-Lib 函式
        （省 `TALibWrapper.compute` 之 DataFrame 建構）。MAVP（週期陣列參數）與 adapter 內計算者不走快路徑。
        使用端須以生產路徑抽樣自檢相等。"""
        import talib

        TALibWrapper.initialize()
        spec = TALibWrapper.get_indicator_spec(name)
        if spec.computed_in_adapter or spec.name == "MAVP":
            return None
        call_params = dict(params)
        inputs, _ = TALibWrapper._prepare_inputs(spec, frame, source or "close", call_params)
        func = getattr(talib, spec.talib_func)
        arrays = [np.ascontiguousarray(x, dtype=np.float64) for x in inputs]

        def call(a: int, b: int) -> List[np.ndarray]:
            out = func(*[x[a:b] for x in arrays], **call_params)
            return [np.asarray(o, dtype=np.float64) for o in (out if isinstance(out, tuple) else (out,))]

        return call

    fn.fast_factory = fast_factory  # type: ignore[attr-defined]
    return fn


def _talib_lookback(name: str, params: Dict[str, Any]) -> int:
    """TA-Lib 於該參數下之 lookback（首個有效輸出之列索引）；取不到回 0。"""
    from talib import abstract

    try:
        func = abstract.Function(name)
        settable = {k: v for k, v in params.items() if k in func.parameters}
        if settable:
            func.parameters = settable
        return int(func.lookback)
    except Exception:  # noqa: BLE001
        return 0


def _column_fn(method: Callable[[pd.DataFrame], pd.DataFrame], column: str) -> Callable[[pd.DataFrame], List[np.ndarray]]:
    def fn(frame: pd.DataFrame) -> List[np.ndarray]:
        out = method(frame)
        return [out[column].to_numpy(dtype=np.float64)]

    return fn


def _engine_params(config: Any) -> Dict[str, Tuple[str, List[Dict[str, Any]], bool]]:
    """預設設定下各 TA-Lib 指標：(類別, 各引擎 ``_resolve_params`` 之參數清單, 是否單輸入)。"""
    from momentum.FeatureEngineering.atomic.cycle_indicators import CycleIndicatorEngine
    from momentum.FeatureEngineering.atomic.momentum_indicators import MomentumIndicatorEngine
    from momentum.FeatureEngineering.atomic.pattern_indicators import PatternIndicatorEngine  # noqa: F401
    from momentum.FeatureEngineering.atomic.statistics_indicators import StatisticsIndicatorEngine
    from momentum.FeatureEngineering.atomic.talib_wrapper import TALibWrapper
    from momentum.FeatureEngineering.atomic.trend_indicators import TrendIndicatorEngine
    from momentum.FeatureEngineering.atomic.volatility_indicators import VolatilityIndicatorEngine
    from momentum.FeatureEngineering.atomic.volume_indicators import VolumeIndicatorEngine

    TALibWrapper.initialize()
    engines = {"trend": TrendIndicatorEngine, "momentum": MomentumIndicatorEngine,
               "volatility": VolatilityIndicatorEngine, "volume": VolumeIndicatorEngine,
               "cycle": CycleIndicatorEngine, "statistics": StatisticsIndicatorEngine}
    out: Dict[str, Tuple[str, List[Dict[str, Any]], bool]] = {}
    ai = config.atomic_indicators
    for cat, engine_cls in engines.items():
        cat_cfg = getattr(ai, cat).model_dump()
        engine = engine_cls(cat_cfg, SOURCES)
        for ind in cat_cfg.get("indicators", []):
            name = ind.get("name")
            if name not in TALibWrapper.INDICATOR_REGISTRY:
                continue
            spec = TALibWrapper.get_indicator_spec(name)
            if spec.computed_in_adapter:
                continue
            params_list = engine._resolve_params(name, ind)
            prev = out.get(spec.talib_func)
            merged = (prev[1] if prev else []) + [p for p in params_list if p not in (prev[1] if prev else [])]
            out[spec.talib_func] = (cat, merged, spec.input_type == "single")
    # 未在預設設定之 TA-Lib 註冊指標（使用者可啟用）：預設參數或 13/55/233
    for name, spec in TALibWrapper.INDICATOR_REGISTRY.items():
        if spec.computed_in_adapter or spec.category == "pattern" or spec.talib_func in out:
            continue
        defaults = dict(spec.default_params)
        if "timeperiod" in defaults:
            params_list = [{**defaults, "timeperiod": p} for p in TEST_PERIODS]
        else:
            params_list = [defaults]
        out[spec.talib_func] = (spec.category, params_list, spec.input_type == "single")
    return out


def build_catalog(timeframe_hint: str = "1h") -> List[Entry]:
    from momentum.FeatureEngineering.atomic.entropy_indicators import EntropyIndicatorEngine
    from momentum.FeatureEngineering.atomic.microstructure_indicators import MicrostructureIndicatorEngine
    from momentum.FeatureEngineering.atomic.tail_risk_indicators import TailRiskIndicatorEngine
    from momentum.FeatureEngineering.atomic.talib_wrapper import TALibWrapper
    from momentum.FeatureEngineering.atomic.volatility_indicators import VolatilityIndicatorEngine
    from momentum.FeatureEngineering.atomic.volume_indicators import VolumeIndicatorEngine
    from momentum.FeatureEngineering.config_manager import ConfigManager

    config = ConfigManager().get_merged_config()
    entries: List[Entry] = []

    # TA-Lib（不含 CDL）
    for name, (_cat, params_list, single) in sorted(_engine_params(config).items()):
        entry = Entry(name, _period_keys(params_list))
        if name in CUMULATIVE:
            entries.append(entry)
            continue
        for params in params_list:
            for source in (SOURCES if single else [""]):
                entry.cases.append(Case(dict(params), _talib_fn(name, params, source), source=source,
                                        integer=(name == "HT_TRENDMODE"), k_floor=_talib_lookback(name, params)))
        entries.append(entry)

    # CDL＊ ⇒ CDL_PATTERN
    cdl = Entry("CDL_PATTERN", ())
    for name, spec in sorted(TALibWrapper.INDICATOR_REGISTRY.items()):
        if spec.category == "pattern":
            # 參數與生產呼叫一致（空字典）；形態名記於 source（收據逐形態可查）
            cdl.cases.append(Case({}, _talib_fn(name, {}, ""), source=name, integer=True,
                                  k_floor=_talib_lookback(name, {})))
    entries.append(cdl)

    # 自訂欄（引擎寫死參數；與 l1 輸出點之參數字典一致）
    vol = VolatilityIndicatorEngine({}, SOURCES)
    volu = VolumeIndicatorEngine({}, SOURCES)
    custom = [
        ("KELTNER", {"timeperiod": 20}, vol._compute_keltner, "hlc_volatility_Keltner_Width_20_2.0", None),
        ("DONCHIAN", {"timeperiod": 20}, vol._compute_donchian, "hlc_volatility_Donchian_Width_20", 400),
        ("PARKINSON_VOL", {"timeperiod": 20}, vol._compute_parkinson, "hlc_volatility_Parkinson_20", 400),
        ("GARMANKLASS_VOL", {"timeperiod": 20}, vol._compute_garman_klass, "hlc_volatility_GarmanKlass_20", 400),
        ("VWAP", {"timeperiod": 20}, volu._compute_vwap, "hlcv_volume_VWAP_20", 400),
        ("VOLUME_MA_RATIO", {"timeperiod": 20}, volu._compute_volume_ma_ratio, "volume_volume_VolumeMA_Ratio_20", 400),
        ("FORCE_INDEX", {"timeperiod": 13}, volu._compute_force_index, "hlcv_volume_ForceIndex", None),
        ("KLINGER_VOLUME_OSC", {}, volu._compute_klinger, "hlcv_volume_Klinger_34_55", None),
        ("EASE_OF_MOVEMENT", {"timeperiod": 14}, volu._compute_eom, "hlcv_volume_EOM_14", 400),
    ]
    for name, params, method, column, gt_hist in custom:
        entries.append(Entry(name, _period_keys([params]),
                             [Case(params, _column_fn(method, column), gt_history=gt_hist)]))

    # 進階 atomic（預設關閉；使用者啟用時 L1 輸出點查表）——呼叫未遮罩之計算函式
    ai = config.atomic_indicators
    ms = MicrostructureIndicatorEngine(ai.microstructure.model_dump(), SOURCES)
    ent = EntropyIndicatorEngine(ai.entropy.model_dump(), SOURCES)
    tr = TailRiskIndicatorEngine(ai.tail_risk.model_dump(), SOURCES)

    def returns_method(method):
        return lambda frame: method(frame["close"].astype(float).pct_change().replace([np.inf, -np.inf], np.nan))

    def series_method(method, source):
        def call(frame):
            series = (frame["close"].astype(float).pct_change() if source == "close_return"
                      else frame[source].astype(float))
            return method(series) if method.__name__ != "_compute_shannon_entropy" else method(series, source)
        return call

    adv: List[Tuple[str, Dict[str, Any], Callable, str]] = []
    for w in ms.windows:
        adv.append(("MS_AMIHUD_ILLIQ", {"window": w}, ms._compute_amihud, f"ms_amihud_illiq_{w}"))
    for w in ms.kyle_lambda_windows:
        adv.append(("MS_KYLE_LAMBDA", {"window": w}, ms._compute_kyle_lambda, f"ms_kyle_lambda_{w}"))
        adv.append(("MS_ROLL_SPREAD", {"window": w}, ms._compute_roll_spread, f"ms_roll_spread_{w}"))
        adv.append(("MS_LARGE_TRADE_RATIO", {"window": w}, ms._compute_large_trade_ratio, f"ms_large_trade_ratio_{w}"))
    for w in ms.cs_spread_smooth:
        adv.append(("MS_CS_SPREAD", {"window": w}, ms._compute_cs_spread, f"ms_cs_spread_{w}"))
    adv.append(("MS_OFI_RAW", {}, ms._compute_ofi, "ms_ofi_raw"))
    for b in ms.vpin_n_buckets:
        adv.append(("MS_VPIN", {"n_buckets": b, "sigma_window": max(ms.vpin_n_buckets)}, ms._compute_vpin, f"ms_vpin_{b}"))
    for source in ent.apply_to:
        for w in ent.shannon_windows:
            adv.append(("ENT_SHANNON", {"window": w}, series_method(ent._compute_shannon_entropy, source),
                        f"ent_shannon_{source}_{w}"))
    for w in ent.windows:
        adv.append(("ENT_APEN", {"window": w}, series_method(ent._compute_approximate_entropy, "close_return"), f"ent_apen_{w}"))
        adv.append(("ENT_SAMPEN", {"window": w}, series_method(ent._compute_sample_entropy, "close_return"), f"ent_sampen_{w}"))
        adv.append(("ENT_FRACTAL_DIM", {"window": w}, series_method(ent._compute_fractal_dimension, "close_return"),
                    f"ent_fractal_dim_{w}"))
    for w in ent.hurst_windows:
        adv.append(("ENT_HURST", {"window": w}, series_method(ent._compute_hurst, "close_return"), f"ent_hurst_{w}"))
    for w in ent.perm_windows:
        adv.append(("ENT_PERM", {"window": w}, series_method(ent._compute_permutation_entropy, "close_return"), f"ent_perm_{w}"))
    for alpha in tr.cvar_alphas:
        for w in tr.windows:
            adv.append(("TR_CVAR", {"alpha": alpha, "window": w}, returns_method(tr._compute_cvar),
                        f"tr_cvar_{int(round(float(alpha) * 100))}pct_{w}"))
    for w in tr.rv_windows:
        for name, col in (("TR_RV_UP", "tr_rv_up"), ("TR_RV_DOWN", "tr_rv_down"), ("TR_RSJ", "tr_rsj")):
            adv.append((name, {"window": w}, returns_method(tr._compute_rv_decomposition), f"{col}_{w}"))
        adv.append(("TR_UD_VOL_RATIO", {"window": w}, returns_method(tr._compute_ud_vol_ratio), f"tr_ud_vol_ratio_{w}"))
    for w in tr.windows:
        adv.append(("TR_GPR", {"window": w}, returns_method(tr._compute_gpr), f"tr_gpr_{w}"))
    for w in (55, 100):
        adv.append(("TR_JB", {"window": w}, returns_method(tr._compute_jarque_bera), f"tr_jb_{w}"))
    for w in tr.mdd_windows:
        adv.append(("TR_MDD", {"window": w}, lambda frame: tr._compute_max_drawdown(frame["close"].astype(float)),
                    f"tr_mdd_{w}"))
    grouped: Dict[str, Entry] = {}
    for name, params, method, column in adv:
        entry = grouped.setdefault(name, Entry(name, ()))
        entry.cases.append(Case(params, _column_fn(method, column), gt_history=600))
    for entry in grouped.values():
        entry.period_keys = _period_keys([c.params for c in entry.cases])
        entries.append(entry)
    return entries


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------
def _case_period(entry: Entry, case: Case) -> Optional[float]:
    values = [float(case.params[k]) for k in entry.period_keys if k in case.params]
    return max(values) if values else None


def _row_key(indicator: str, params: Dict[str, Any], source: Any) -> str:
    return json.dumps([indicator, sorted((str(k), str(v)) for k, v in (params or {}).items()), str(source)])


_PROCESS_CACHE: Dict[str, Any] = {}


def _cached_catalog() -> List[Any]:
    """每個（子）程序只建一次 catalog（逐指標細分任務時避免重複建構）。"""
    if "catalog" not in _PROCESS_CACHE:
        _PROCESS_CACHE["catalog"] = build_catalog()
    return _PROCESS_CACHE["catalog"]


def _cached_frame(sym: str, tf: str) -> pd.DataFrame:
    key = f"frame|{sym}|{tf}"
    if key not in _PROCESS_CACHE:
        _PROCESS_CACHE[key] = load_frame(sym, tf)
    return _PROCESS_CACHE[key]


def _series_rows(task: Tuple[Any, ...]) -> List[Dict[str, Any]]:
    """單一 (週期, 標的) 之量測列（可於子程序執行：catalog 於本程序重建）。``seed`` 非空時沿用其已量得之 K
    （不重跑多窗量測），``exhaustive`` 時再以 `verify_exhaustive` 逐起點驗證並必要時提升 K。"""
    tf, sym, only, eval_window, threshold, cap, positions, seed, exhaustive = task[:9]
    budget_s = task[9] if len(task) > 9 else None
    entries = [e for e in _cached_catalog() if not only or e.name in only]
    frame = _cached_frame(sym, tf)
    rows: List[Dict[str, Any]] = []
    t0 = time.time()
    deadline = (t0 + float(budget_s)) if (exhaustive and budget_s) else None
    for entry in entries:
        for case in entry.cases:
            period = _case_period(entry, case)
            start = int(period) if period else 1
            prior = (seed or {}).get(_row_key(entry.name, case.params, case.source))
            if prior is not None:
                res = {k: v for k, v in prior.items()
                       if k not in ("indicator", "symbol", "timeframe", "params", "source", "period", "ratio")}
            else:
                res = measure_case(case, frame, eval_window, threshold, cap, start, positions)
            if exhaustive and res.get("k") and entry.name in WINDOW_ONLY_ANALYTIC:
                # 純窗口型：K＝窗口長度（取多窗量測值與窗口長度之大者；多窗量測值大於窗口即表示非純窗口 ⇒ 拒收）
                window_k = int(period) if period else int(res["k"])
                if int(res["k"]) > window_k:
                    raise ValueError(f"{entry.name} {case.params} 多窗量測 K={res['k']} > 窗口長度 {window_k}："
                                     "不符純窗口型假設，須移出 WINDOW_ONLY_ANALYTIC 改走窮舉")
                res["k_multi_window"] = res["k"]
                res["k"] = window_k
                res["exhaustive"] = {"skipped": "window_only_analytic", "k_rule": "window_length", "passed": True}
            elif exhaustive and res.get("k"):
                ex = verify_exhaustive(case, frame, int(res["k"]), eval_window, threshold, cap, deadline=deadline,
                                       label=f"{tf} {sym} {entry.name} {case.params}")
                res["k_multi_window"] = res["k"]
                res["k"] = int(ex["k"])
                res["exhaustive"] = ex
                if not ex["passed"] and not ex.get("no_admissible_starts"):
                    res["converged"] = False  # 起點集合為空者保留多窗之已收斂量測（v47），但不計窮舉通過
            rows.append({"indicator": entry.name, "symbol": sym, "timeframe": tf, "params": case.params,
                         "source": case.source, "period": period, **res,
                         "ratio": (res["k"] / period) if (res.get("k") and period) else None})
    print(f"[measure] {tf} {sym}: {len(entries)} entries in {time.time() - t0:.1f}s", flush=True)
    return rows


class PreflightRefused(RuntimeError):
    """逐起點窮舉開跑前估時超過上限（2026-09-30 事故：七項純窗口重指標單項 67–135 CPU 小時，7 程序卡 8 小時無一完成）。"""

    def __init__(self, refused: List[Dict[str, Any]]):
        super().__init__(f"{len(refused)} 項預估超過上限")
        self.refused = refused


class StallAborted(RuntimeError):
    """平行執行中超過上限時間無任何一項完成。`context`：已完成／未完成數、執行中項目、續跑檔、耗時（寫入中止收據）。"""

    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.context = dict(context or {})


class TaskBudgetExceeded(RuntimeError):
    """逐起點窮舉之單項執行超過預算（`--max-task-cpu-hours`）：開跑前估時只為掃描輪下界，執行中以實際耗時設上界。"""

    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.context = dict(context or {})

    def __reduce__(self):  # 子程序拋出時可 pickle 回主程序
        return (TaskBudgetExceeded, (str(self), self.context))


# 純窗口型：輸出只依固定窗內之值（`rolling(w).apply(f, raw=True)`、f 無跨窗狀態、輸入為報酬或來源欄之局部轉換）⇒
# 所需預熱＝窗口長度，與起點無關，不做逐起點窮舉（諮詢 r37 三家；五週期三標的多窗量測值皆等於窗口長度）。
# 具名封閉清單：新條目未列入者一律照窮舉（未知歸帶狀態型）；機械歸類器屬 FFSTORE 接續計算分類（SPEC §N）。
WINDOW_ONLY_ANALYTIC = frozenset({
    "ENT_SHANNON", "ENT_APEN", "ENT_SAMPEN", "ENT_FRACTAL_DIM", "ENT_HURST", "ENT_PERM", "TR_CVAR",
})


def preflight_estimate(tasks: Sequence[Tuple[Any, ...]], eval_window: int) -> List[Dict[str, Any]]:
    """逐起點窮舉之開跑前估時：每 (週期, 條目) 以首個標的之真實資料對每個 case 實測單次呼叫耗時
    （切片長 K＋評估窗、取序列中段），乘以該標的之可採起點數 n−E−2K+1。只為掃描輪之下界估計（確認輪、升 K 另計），
    用於擋下數量級不可行者，非精確排程。"""
    timing: Dict[Tuple[str, str], List[Tuple[int, float]]] = {}
    out: List[Dict[str, Any]] = []
    for t in tasks:
        tf, sym, only, seed = t[0], t[1], t[2], t[7]
        if only[0] in WINDOW_ONLY_ANALYTIC:  # 純窗口型不窮舉，不估
            continue
        key = (tf, only[0])
        if key not in timing:
            entry = next(e for e in _cached_catalog() if e.name == only[0])
            frame = _cached_frame(sym, tf)
            n, mid = len(frame), len(frame) // 2
            per_case = []
            for case in entry.cases:
                prior = (seed or {}).get(_row_key(entry.name, case.params, case.source)) or {}
                k = int(prior.get("k") or _case_period(entry, case) or 1)
                lo = max(0, mid - k)
                t0 = time.perf_counter()
                try:
                    case.fn(frame.iloc[lo:min(n, mid + eval_window)])
                except Exception:  # noqa: BLE001 — 過短輸入等：以 0 計，交實跑處理
                    pass
                per_case.append((k, time.perf_counter() - t0))
            timing[key] = per_case
        n = len(_cached_frame(sym, tf))
        est = sum(dt * max(0, n - eval_window - 2 * k + 1) for k, dt in timing[key])
        out.append({"timeframe": tf, "symbol": sym, "indicator": only[0], "est_cpu_s": round(est, 1),
                    "per_call_s": round(max((dt for _, dt in timing[key]), default=0.0), 4), "rows": n,
                    "cases": [{"k": k, "per_call_s": round(dt, 5), "starts": max(0, n - eval_window - 2 * k + 1)}
                              for k, dt in timing[key]]})
    return out


def run(symbols: Sequence[str], timeframes: Sequence[str], eval_window: int, threshold: float, cap: int,
        only: Optional[Sequence[str]] = None, positions: int = 1, *, seed_rows: Optional[List[Dict[str, Any]]] = None,
        exhaustive: bool = False, workers: int = 1, partial_log: Optional[Path] = None,
        max_task_cpu_s: float = 7200.0, max_stall_s: float = 1800.0
        ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    entries = [e for e in build_catalog() if not only or e.name in only]
    seeds: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for r in seed_rows or []:
        seeds.setdefault((r["timeframe"], r["symbol"]), {})[_row_key(r["indicator"], r["params"], r["source"])] = r
    # 逐 (週期, 標的, 指標) 細分任務：單程序與平行同一 pending 集合（v55，審查 r39 codex P1-03：估時閘於單程序亦生效）；
    # 末元素為逐項執行預算（秒，窮舉時生效；v55 codex P1-04：估時只為下界，執行中超預算即中止＝實際耗時之上界）
    tasks = [(tf, sym, [e.name], eval_window, threshold, cap, positions, seeds.get((tf, sym)), exhaustive,
              max_task_cpu_s) for tf in timeframes for sym in symbols for e in entries]
    rows: List[Dict[str, Any]] = []
    from concurrent.futures import ProcessPoolExecutor

    # 續跑檔：每完成一項即追加（task 鍵＋指紋＋列）；指紋＝本腳本內容＋任務參數（不含標的／週期／指標以外之差異
    # 即不沿用），重啟時只沿用指紋相同者。
    import hashlib

    script_sha = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    done_rows: Dict[str, List[Dict[str, Any]]] = {}

    def task_key(t: Tuple[Any, ...]) -> str:
        payload = [script_sha, t[0], t[1], t[2], t[3], t[4], t[5], t[6], t[8],
                   json.dumps(t[7], sort_keys=True, default=str) if t[7] else None]
        return hashlib.sha256(json.dumps(payload, default=str).encode()).hexdigest()

    if partial_log is not None and partial_log.exists():
        for line in partial_log.read_text(encoding="utf-8").splitlines():
            rec = json.loads(line)
            done_rows[rec["key"]] = rec["rows"]
    pending = []
    for t in tasks:
        if task_key(t) in done_rows:
            rows.extend(done_rows[task_key(t)])
        else:
            pending.append(t)
    print(f"[resume] reused {len(tasks) - len(pending)}/{len(tasks)} tasks from partial log", flush=True)
    if exhaustive and pending:
        estimates = preflight_estimate(pending, eval_window)
        refused = [e for e in estimates if e["est_cpu_s"] > max_task_cpu_s]
        total = sum(e["est_cpu_s"] for e in estimates)
        print(f"[preflight] tasks={len(estimates)} est_total_cpu_h={total / 3600:.1f} "
              f"est_wall_h≈{total / 3600 / workers:.1f} limit_per_task_cpu_h={max_task_cpu_s / 3600:.2f}", flush=True)
        if refused:
            for e in sorted(refused, key=lambda r: -r["est_cpu_s"]):
                print(f"[preflight] REFUSED {e['timeframe']} {e['symbol']} {e['indicator']} "
                      f"est_cpu_h={e['est_cpu_s'] / 3600:.1f}", flush=True)
            raise PreflightRefused(refused)
    started = time.time()
    finished_tasks: List[str] = []

    def label(t: Tuple[Any, ...]) -> str:
        return f"{t[0]} {t[1]} {t[2][0]}"

    def record(t: Tuple[Any, ...], got: List[Dict[str, Any]]) -> None:
        rows.extend(got)
        finished_tasks.append(label(t))
        if partial_log is not None:
            with open(partial_log, "a", encoding="utf-8") as fh:
                fh.write(json.dumps({"key": task_key(t), "task": [t[0], t[1], t[2][0]], "rows": got},
                                    default=str) + "\n")
        print(f"[progress] {len(finished_tasks)}/{len(pending)} {label(t)} elapsed={time.time() - started:.0f}s",
              flush=True)

    def abort_context(running: List[str]) -> Dict[str, Any]:
        return {"completed": len(finished_tasks), "pending": len(pending) - len(finished_tasks), "running": running,
                "partial_log": str(partial_log) if partial_log is not None else None,
                "elapsed_s": round(time.time() - started, 1)}

    if workers <= 1:
        for t in pending:  # 單程序：逐項執行預算即上界（無平行等待，故無停滯判定）
            try:
                got = _series_rows(t)
            except TaskBudgetExceeded as exc:
                raise TaskBudgetExceeded(str(exc), abort_context([label(t)])) from None
            record(t, got)
        return adopt(entries, rows, timeframes), rows

    from concurrent.futures import FIRST_COMPLETED, wait

    pool = ProcessPoolExecutor(max_workers=workers)
    try:
        futures = {pool.submit(_series_rows, t): t for t in pending}
        remaining = set(futures)
        last_done = time.time()
        while remaining:
            finished, remaining = wait(remaining, timeout=min(60.0, max_stall_s), return_when=FIRST_COMPLETED)
            if not finished:
                if time.time() - last_done >= max_stall_s:
                    stuck = sorted(label(futures[f]) for f in remaining if f.running())
                    print(f"[STALL] 已 {time.time() - last_done:.0f}s 無任何一項完成；執行中：{stuck}", flush=True)
                    raise StallAborted(f"無進度 {max_stall_s:.0f}s", abort_context(stuck))
                continue
            last_done = time.time()
            for fut in finished:
                try:
                    got = fut.result()
                except TaskBudgetExceeded as exc:
                    raise TaskBudgetExceeded(str(exc), abort_context([label(futures[fut])])) from None
                record(futures[fut], got)
    except BaseException:
        for proc in list(getattr(pool, "_processes", {}).values()):  # 停滯／超預算／中斷：終止仍在算之子程序
            proc.terminate()
        pool.shutdown(wait=False, cancel_futures=True)
        raise
    pool.shutdown(wait=True)
    return adopt(entries, rows, timeframes), rows


def _compact_row(r: Dict[str, Any]) -> Dict[str, Any]:
    """收據列精簡：保留判定與重播所需欄位；窮舉細節只留最終輪摘要（逐起點明細不入收據）。"""
    keep = ("indicator", "symbol", "timeframe", "params", "source", "period", "k", "k_floor", "err", "converged",
            "reliable", "test_finite", "gt_finite", "gt_history", "ratio", "k_multi_window")
    out = {k: r.get(k) for k in keep if k in r}
    ex = r.get("exhaustive")
    if ex:
        if ex.get("skipped") or "rounds" not in ex:
            out["exhaustive"] = dict(ex)  # 純窗口解析列或已精簡之列
        else:
            last = (ex.get("rounds") or [{}])[-1]
            out["exhaustive"] = {"k": ex.get("k"), "passed": ex.get("passed"), "fast_path": ex.get("fast_path"),
                                 "starts": last.get("starts"), "worst": last.get("worst"),
                                 "worst_start": last.get("worst_start"),
                                 "scan_fails": (ex.get("rounds") or [{}])[0].get("fails")}
        # b4 審碼 r1 codex P1-01：舊收據中起點集合為空而記 passed 者一律改記 no_admissible_starts
        if not out["exhaustive"].get("skipped") and out["exhaustive"].get("starts") == 0:
            out["exhaustive"]["passed"] = False
            out["exhaustive"]["no_admissible_starts"] = True
    return out


def merge_measurements(receipts: Sequence[Path], partial_logs: Sequence[Path],
                       partial_timeframes: Sequence[str]) -> List[Dict[str, Any]]:
    """正式合併（v55，審查 r39 codex P1-05：表不得依賴外部合併步驟）：多份量測收據＋續跑檔（限列名週期）之列，
    同一實例（指標、參數、來源、週期、標的）有窮舉結果者取窮舉列（窮舉 K ≥ 多窗 K），否則取多窗列；
    同類多列衝突時取 K 最大者（保守），K 同則取內容序最小者——結果與輸入順序無關（v55，審查 r40 codex P1-02）。"""
    best: Dict[str, Dict[str, Any]] = {}

    def rank(row: Dict[str, Any]) -> Tuple[int, int]:
        k = int(row["k"]) if row.get("converged") and row.get("k") is not None else -1
        return (1 if "exhaustive" in row else 0, k)

    def add(r: Dict[str, Any]) -> None:
        key = json.dumps([r["indicator"], sorted((str(k), str(v)) for k, v in (r.get("params") or {}).items()),
                          str(r.get("source")), r["timeframe"], r["symbol"]])
        row = _compact_row(r)
        if key not in best:
            best[key] = row
            return
        cur = best[key]
        rc, rn = rank(cur), rank(row)
        if rn > rc or (rn == rc and json.dumps(row, sort_keys=True, default=str)
                                < json.dumps(cur, sort_keys=True, default=str)):
            best[key] = row

    for path in receipts:
        for r in json.loads(Path(path).read_text(encoding="utf-8"))["rows"]:
            add(r)
    for path in partial_logs:
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            rec = json.loads(line)
            if rec["task"][0] in set(partial_timeframes):
                for r in rec["rows"]:
                    add(r)
    out = list(best.values())
    for row in out:  # 純窗口型：同窮舉模式之規則（K＝窗口長度；量測值大於窗口即拒收）
        if row["indicator"] in WINDOW_ONLY_ANALYTIC and row.get("converged") and "exhaustive" not in row:
            window_k = int(row["period"]) if row.get("period") else int(row["k"])
            if int(row["k"]) > window_k:
                raise ValueError(f"{row['indicator']} {row['params']} {row['timeframe']} {row['symbol']} "
                                 f"量測 K={row['k']} > 窗口長度 {window_k}：不符純窗口型假設")
            row["k_multi_window"], row["k"] = row["k"], window_k
            row["exhaustive"] = {"skipped": "window_only_analytic", "k_rule": "window_length", "passed": True}
    return out


def coverage_meta(rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """表 `_meta.exhaustive_start_verification`：由實際列逐（週期, 標的）計數窮舉通過／純窗口解析／僅多窗。"""
    counts: Dict[str, Dict[str, Dict[str, int]]] = {}
    for r in rows:
        ex = r.get("exhaustive") or {}
        kind = ("window_only_analytic" if ex.get("skipped") == "window_only_analytic"
                else "exhaustive_no_admissible_starts" if ex.get("no_admissible_starts") or ex.get("starts") == 0
                else "exhaustive_passed" if ex.get("passed") else "exhaustive_failed" if ex else "multi_window_only")
        slot = counts.setdefault(r["timeframe"], {}).setdefault(r["symbol"], {})
        slot[kind] = slot.get(kind, 0) + 1
    return {"scope": "逐可採起點窮舉（verify_exhaustive）；純窗口型 WINDOW_ONLY_ANALYTIC 之 K＝窗口長度；"
                     "採用值＝各實例量測取最大",
            "window_only_analytic": sorted(WINDOW_ONLY_ANALYTIC),
            "counts": {tf: dict(sorted(v.items())) for tf, v in sorted(counts.items())}}


def _param_defaults(entry: Entry) -> Dict[str, Any]:
    """條目之非週期參數預設值（SPEC v47）：TA-Lib 指標取其函式預設參數中非 period_keys 者；自訂與進階欄為空。"""
    from momentum.FeatureEngineering.atomic.talib_wrapper import TALibWrapper

    TALibWrapper.initialize()
    spec = TALibWrapper.INDICATOR_REGISTRY.get(entry.name)
    if spec is None:
        return {}
    return {k: v for k, v in dict(spec.default_params).items() if k not in set(entry.period_keys)}


def _k_by_params(entry: Entry, rows: Sequence[Dict[str, Any]], by_tf: Dict[str, Optional[float]],
                 timeframes: Sequence[str], defaults: Dict[str, Any]) -> Dict[str, int]:
    """SPEC v46／v47（R10 實測根數優先）：每組生產參數（全參數正規鍵，含預設值）之 K＝各週期「已收斂量測之最大 K」
    取最大；某週期該組無已收斂量測時以該週期係數×該組最大週期補（無條件進位）。r31 codex P1-01：不再只取
    「可信」量測——已收斂之不可信量測（前史 < 2K）亦為實測下界，採用值不得低於任一已收斂量測。"""
    from momentum.FeatureEngineering.preprocessing.stable_mask import canonical_params

    per_key: Dict[str, Dict[str, int]] = {}
    periods: Dict[str, float] = {}
    for r in rows:
        key = canonical_params(r["params"], defaults)
        periods[key] = float(r["period"])
        slot = per_key.setdefault(key, {})
        if r["converged"]:
            slot[r["timeframe"]] = max(slot.get(r["timeframe"], 0), int(r["k"]))
    out: Dict[str, int] = {}
    for key, measured in per_key.items():
        candidates = []
        for tf in timeframes:
            if tf in measured:
                candidates.append(measured[tf])
            elif by_tf.get(tf) is not None:
                candidates.append(int(math.ceil(periods[key] * float(by_tf[tf]))))
        if candidates:
            out[key] = int(max(candidates))
    return dict(sorted(out.items()))


def adopt(entries: Sequence[Entry], rows: Sequence[Dict[str, Any]], timeframes: Sequence[str]) -> Dict[str, Any]:
    indicators: Dict[str, Any] = {}
    for entry in entries:
        mine = [r for r in rows if r["indicator"] == entry.name]
        record: Dict[str, Any] = {"family": entry.family, "warmup_class": entry.warmup_class,
                                  "period_keys": list(entry.period_keys)}
        if entry.warmup_class == "cumulative":
            indicators[entry.name] = record
            continue
        # r31 codex P1-01：採用值取「已收斂」量測（含前史 < 2K 之不可信者——其量得 K 仍為收斂所需之實測下界）
        converged = [r for r in mine if r["converged"]]
        defaults = _param_defaults(entry)
        from momentum.FeatureEngineering.preprocessing.stable_mask import variant_key

        record["param_defaults"] = defaults
        # r32 codex P1-01：只登記「有已收斂量測」之非週期變體（嘗試過而未收斂或無收據列者不得放行）
        record["variants"] = sorted({variant_key(r["params"], entry.period_keys, defaults) for r in converged})
        if entry.period_keys:
            by_tf = {tf: max((r["ratio"] for r in converged if r["timeframe"] == tf), default=None) for tf in timeframes}
            record["factors_by_timeframe"] = {tf: (round(v, 4) if v is not None else None) for tf, v in by_tf.items()}
            measured = [v for v in by_tf.values() if v is not None]
            factor = max(measured) if measured else None
            record["recommended_factor"] = None if factor is None else float(math.ceil(max(1.0, factor) * 100) / 100)
            record["k_by_params"] = _k_by_params(entry, mine, by_tf, timeframes, defaults)
        else:
            by_tf = {tf: max((r["k"] for r in converged if r["timeframe"] == tf), default=None) for tf in timeframes}
            record["k_by_timeframe"] = by_tf
            measured = [v for v in by_tf.values() if v is not None]
            record["k"] = int(max(measured)) if measured else None
        record["max_K_observed"] = max((r["k"] for r in converged), default=None)
        record["measurements"] = len(mine)
        record["unreliable_or_unconverged"] = sum(1 for r in mine if not r["reliable"])
        indicators[entry.name] = record
    for name, parts in COMPONENT_FLOOR.items():
        rec = indicators.get(name)
        floors = [indicators[p]["recommended_factor"] for p in parts if indicators.get(p, {}).get("recommended_factor")]
        if rec and rec.get("recommended_factor") is not None and floors and rec["recommended_factor"] < max(floors):
            rec["measured_factor"] = rec["recommended_factor"]
            rec["recommended_factor"] = max(floors)
            rec["component_floor"] = list(parts)
        if rec and rec.get("k_by_params"):
            # 實測根數亦不得低於元件於同組參數之 K（元件條目之 k_by_params 或比例公式）
            from momentum.FeatureEngineering.preprocessing.stable_mask import k_for_params

            for key in list(rec["k_by_params"]):
                params = {kv.split("=")[0]: float(kv.split("=")[1]) for kv in key.split(",")}
                comp_k = [k_for_params(indicators[p], params, tuple(params)) for p in parts if p in indicators]
                comp_k = [k for k in comp_k if k is not None]
                if comp_k and rec["k_by_params"][key] < max(comp_k):
                    rec.setdefault("measured_k_by_params", {})[key] = rec["k_by_params"][key]
                    rec["k_by_params"][key] = int(max(comp_k))
                    rec["component_floor"] = list(parts)
    for name, (part, period) in COMPONENT_K_FLOOR.items():
        rec = indicators.get(name)
        comp = indicators.get(part, {}).get("recommended_factor")
        if rec and rec.get("k") is not None and comp:
            floor = int(math.ceil(period * comp))
            if rec["k"] < floor:
                rec["measured_k"] = rec["k"]
                rec["k"] = floor
                rec["component_floor"] = [part, period]
    return indicators


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--threshold", type=float, default=0.005)
    ap.add_argument("--eval-window", type=int, default=1000)
    ap.add_argument("--eval-positions", type=int, default=20,
                    help="每條序列之等距評估窗數（FFSTAT v52 多評估窗協定；1＝改前單窗）")
    ap.add_argument("--market", default="crypto", help="量測資料之市場（adapter.market）；寫入表 _meta.market_scopes")
    ap.add_argument("--max-K-cap", type=int, default=4000)
    ap.add_argument("--symbols", nargs="+", default=DEFAULT_SYMBOLS)
    ap.add_argument("--timeframes", nargs="+", default=DEFAULT_TIMEFRAMES)
    ap.add_argument("--only", nargs="*", default=None, help="只量測列名之條目（除錯用；不寫表）")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    ap.add_argument("--receipt", type=Path, default=None)
    ap.add_argument("--no-write", action="store_true")
    ap.add_argument("--adopt-from", type=Path, default=None,
                    help="不重量：自既有量測收據之逐筆紀錄重算採用值（採用規則變更時用；收據與表之量測資料不變）")
    ap.add_argument("--exhaustive", action="store_true",
                    help="FFSTAT v53：量得 K 後逐可採起點窮舉驗證（verify_exhaustive），不合即提升 K")
    ap.add_argument("--seed-receipt", type=Path, default=None,
                    help="沿用既有量測收據之逐筆 K 為起點（不重跑多窗量測），僅做 --exhaustive 驗證")
    ap.add_argument("--workers", type=int, default=1, help="(週期, 標的) 平行子程序數")
    ap.add_argument("--partial-log", type=Path, default=None,
                    help="續跑檔（jsonl）：平行模式每完成一項即追加；重啟時沿用指紋相同之已完成項")
    ap.add_argument("--max-task-cpu-hours", type=float, default=2.0,
                    help="逐起點窮舉每項預算：開跑前估時超過即整批拒跑（exit 2）；執行中超過即中止（exit 4）")
    ap.add_argument("--merge-receipts", nargs="*", type=Path, default=None,
                    help="不重量：合併多份量測收據（同一實例有窮舉者取窮舉列）後產表與收據（v55 正式合併）")
    ap.add_argument("--merge-partial-logs", nargs="*", type=Path, default=None,
                    help="合併模式另讀之續跑檔（jsonl），只取 --merge-partial-timeframes 列名之週期")
    ap.add_argument("--merge-partial-timeframes", nargs="*", default=None)
    ap.add_argument("--max-stall-minutes", type=float, default=30.0,
                    help="平行執行中超過此分鐘數無任何一項完成即中止（exit 3）")
    args = ap.parse_args()

    started = time.time()

    def abort_receipt(code: int, kind: str, payload: Dict[str, Any]) -> None:
        if args.receipt:
            args.receipt.parent.mkdir(parents=True, exist_ok=True)
            args.receipt.write_text(json.dumps({"schema_version": 1, "exit_code": code, "abort": kind,
                                                "command": " ".join(sys.argv), **payload},
                                               ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    if args.merge_receipts:
        rows = merge_measurements(args.merge_receipts, args.merge_partial_logs or [],
                                  args.merge_partial_timeframes or [])
        # v55（審查 r40 codex P1-03）：合併輸入須涵蓋 --symbols × --timeframes 之每一格且每個條目皆有列，否則 fail-closed
        catalog = build_catalog()
        # b4 審碼 r1 codex P1-02：逐 catalog case 之完整鍵（指標、參數、來源）× 週期 × 標的比對，缺任一 case 即 fail-closed
        present = {(_row_key(r["indicator"], r["params"], r["source"]), r["timeframe"], r["symbol"]) for r in rows}
        missing_slots = sorted(f"{e.name} {c.params} {c.source} {tf} {sym}" for e in catalog for c in e.cases
                               for tf in args.timeframes for sym in args.symbols
                               if (_row_key(e.name, c.params, c.source), tf, sym) not in present)
        if missing_slots:
            print(f"[FINAL] MERGE_COVERAGE_MISSING {len(missing_slots)} 格：{missing_slots[:20]}；未寫表", flush=True)
            abort_receipt(5, "merge_coverage_missing", {"missing": missing_slots})
            return 5
        table = adopt(catalog, rows, args.timeframes)
    elif args.adopt_from is not None:
        prior = json.loads(args.adopt_from.read_text(encoding="utf-8"))
        rows = prior["rows"]
        args.symbols, args.timeframes = prior["meta"]["symbols"], prior["meta"]["timeframes"]
        table = adopt(build_catalog(), rows, args.timeframes)
    else:
        seed_rows = json.loads(args.seed_receipt.read_text(encoding="utf-8"))["rows"] if args.seed_receipt else None
        try:
            table, rows = run(args.symbols, args.timeframes, args.eval_window, args.threshold, args.max_K_cap,
                              args.only, args.eval_positions, seed_rows=seed_rows, exhaustive=args.exhaustive,
                              workers=args.workers, partial_log=args.partial_log,
                              max_task_cpu_s=args.max_task_cpu_hours * 3600, max_stall_s=args.max_stall_minutes * 60)
        except PreflightRefused as exc:
            print(f"[FINAL] PREFLIGHT_REFUSED {len(exc.refused)} 項預估超過每項上限 {args.max_task_cpu_hours} CPU 小時；"
                  "未計算、未寫表", flush=True)
            abort_receipt(2, "preflight_refused", {"preflight_refused": exc.refused})
            return 2
        except StallAborted as exc:
            print(f"[FINAL] STALL_ABORTED {exc}；未寫表（已完成者在 --partial-log）", flush=True)
            abort_receipt(3, "stall", {"message": str(exc), **exc.context})
            return 3
        except TaskBudgetExceeded as exc:
            print(f"[FINAL] TASK_BUDGET_EXCEEDED {exc}；未寫表（已完成者在 --partial-log）", flush=True)
            abort_receipt(4, "task_budget_exceeded", {"message": str(exc), **exc.context})
            return 4
    missing = sorted(n for n, r in table.items() if r["warmup_class"] != "cumulative"
                     and r.get("recommended_factor") is None and r.get("k") is None)
    doc = {
        "_meta": {
            "generated_by": "scripts/verify_l1_warmup_requirements.py",
            "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
            "symbols": list(args.symbols),
            "timeframes": list(args.timeframes),
            "data_source": {"1h": "data_cache/feature_klines", "5m/4h/12h/1d": "data_cache/feature_klines_longhist"},
            "scale_normalized_error_threshold": args.threshold,
            "eval_window_bars": args.eval_window,
            "eval_positions": args.eval_positions,
            "exhaustive_start_verification": (coverage_meta(rows) if any("exhaustive" in r for r in rows)
                                              else False),
            "market_scopes": [args.market],
            "reliability": "K <= eval_start/2（ground truth 前史 ≥ 2K）者方入採用值",
            "principle": ("Minimum warmup K such that max|test - infinite_history_gt| over the eval window is less "
                          "than THRESHOLD * max(P75(|gt|), std(gt)); ground truth finite but test non-finite = inf."),
            "usage": ("K = ceil(max(params[k] for k in period_keys) * recommended_factor); period_keys 為空者取 k；"
                      "cumulative 無收斂點（K＝0）。見 momentum/FeatureEngineering/atomic/warmup_lookup.py"),
            "elapsed_seconds": round(time.time() - started, 1),
        },
        "indicators": {name: table[name] for name in sorted(table)},
    }
    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(json.dumps({
            "schema_version": 1,
            "command": "PYTHONPATH=. venv/bin/python " + " ".join(["scripts/verify_l1_warmup_requirements.py"] + sys.argv[1:]),
            "exit_code": 1 if missing else 0,
            "missing_adoption": missing,
            "meta": doc["_meta"],
            "rows": [_compact_row(r) for r in rows],
        }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    if not args.no_write and not args.only:
        with open(args.output, "w", encoding="utf-8") as f:
            yaml.safe_dump(doc, f, sort_keys=False, allow_unicode=True, default_flow_style=False)
        print(f"[FINAL] wrote {args.output}")
    print(f"[FINAL] entries={len(table)} missing_adoption={missing} elapsed={time.time() - started:.1f}s")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
