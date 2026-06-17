"""Claude 自產 — 真實 L1 特徵 fixed-vs-WF d* 配對下游 IC 實驗（三方都指出的裁判測試）。

read-only,不進生產路徑。忠於生產:用 FeatureFactory 真實生成 L1 + 生產 _find_min_d + 生產 fracdiff 權重/卷積。
隔離變因:fixed vs WF 唯一差異 = d* 是否隨時間 PIT 重估。
下游:每個非平穩 L1 特徵 fracdiff 後 vs 次根 close log-return 的 Spearman IC;配對 ΔIC=IC_wf-IC_fixed。
裁決:ΔIC 是否穩定 >雜訊(sign test + median|ΔIC| + frac|ΔIC|>0.01)。
"""
from __future__ import annotations

import time
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from momentum.factories import create_feature_factory
from momentum.DataExtraction.kline_storage import KlineStorageManager
from momentum.FeatureEngineering.preprocessing.feature_preprocessor import (
    FeaturePreprocessor, _frac_diff_convolve,
)

SYMBOLS = ["BTCUSDT", "ETHUSDT", "ADAUSDT"]
TF = "1h"
CAL = 500            # calibration / rolling window
INTERVAL = 500       # WF 重估間隔
BURN = 800           # IC 計算 burn-in
MAX_COLS = 80        # 每 symbol 取樣非平穩 L1 欄上限(控時間)
WTHRESH = 1e-5
SEED = 42

PP_CFG = {"calibration_bars": CAL, "causal_preprocessing": True,
          "fractional_differencing": {"enabled": True, "weight_threshold": WTHRESH, "precision": 0.02},
          "adf_differencing": {"enabled": True, "sample_size": CAL}}


def fracdiff_fixed(vals: np.ndarray, d: float) -> np.ndarray:
    """因果 fracdiff,NaN 處理與生產 _find_min_d 的 _filled_slice 一致(first_valid + ffill)。"""
    w = FeaturePreprocessor._get_weights_ffd(d, WTHRESH, max_width=0)
    wlen = len(w)
    n = len(vals)
    out = np.full(n, np.nan)
    finite = np.isfinite(vals)
    if not finite.any():
        return out
    first_valid = int(np.argmax(finite))
    raw_slice = vals[first_valid:]
    if not np.all(np.isfinite(raw_slice)):
        raw_slice = pd.Series(raw_slice, dtype=float).ffill().to_numpy(dtype=np.float64)
    if raw_slice.size < wlen:
        return out
    conv = _frac_diff_convolve(raw_slice, w)
    out[first_valid + wlen - 1: first_valid + raw_slice.size] = conv
    return out


def fracdiff_wf(vals: np.ndarray, pp: FeaturePreprocessor) -> np.ndarray:
    """每 INTERVAL 段,d* 由 rolling [seg-CAL, seg) (PIT) 估;段內輸出用該 d* 的因果卷積。"""
    n = len(vals)
    out = np.full(n, np.nan)
    seg_starts = list(range(CAL, n, INTERVAL))
    # 暖機段 [0, CAL): 用首 CAL d*
    d0 = pp._find_min_d(pd.Series(vals[:CAL]))
    bounds = [(0, CAL, d0)]
    for ss in seg_starts:
        d = pp._find_min_d(pd.Series(vals[ss - CAL:ss]))   # PIT: 只用過去
        end = min(ss + INTERVAL, n)
        bounds.append((ss, end, d))
    for (lo, hi, d) in bounds:
        # 因果卷積整段算好再切 [lo,hi):與 fixed 同一卷積核,只差 d* 隨段變
        tmp = fracdiff_fixed(vals, d)   # out[i] 因果(僅用 ≤i),PIT 成立
        out[lo:hi] = tmp[lo:hi]
    return out


def ic(feat: np.ndarray, fwd: np.ndarray) -> float:
    m = np.isfinite(feat) & np.isfinite(fwd)
    if m.sum() < 100:
        return np.nan
    r, _ = spearmanr(feat[m], fwd[m])
    return float(r)


def main() -> None:
    rng = np.random.default_rng(SEED)
    pp = FeaturePreprocessor(PP_CFG)
    f = create_feature_factory(cache_dir="data_cache/feature_klines", validate_continuity=False)
    cfg = f._resolve_config(None)
    all_rows = []
    for sym in SYMBOLS:
        t0 = time.perf_counter()
        l0 = f._layer0_data_ingestion(sym, TF, cfg)
        close = l0["close"].astype(float).to_numpy() if "close" in l0 else None
        fwd = np.full(len(close), np.nan)
        fwd[:-1] = np.log(close[1:] / close[:-1])    # 次根 log-return
        L1 = f._execute_layer1_6("Layer 1", f._layer1_atomic_indicators, l0, cfg).data
        # 選非平穩欄: fixed d* > 0 且數值欄
        num_cols = [c for c in L1.columns if np.issubdtype(L1[c].dtype, np.number)]
        targets = []
        for c in num_cols:
            v = L1[c].to_numpy(dtype=float)
            if np.isfinite(v).sum() < CAL * 2:
                continue
            d = pp._find_min_d(pd.Series(v[:CAL]))
            if d > 0:                                  # 非平穩 → fracdiff 目標
                targets.append((c, d))
        if len(targets) > MAX_COLS:
            idx = rng.choice(len(targets), MAX_COLS, replace=False)
            targets = [targets[i] for i in sorted(idx)]
        for (c, d_fix) in targets:
            v = L1[c].to_numpy(dtype=float)
            ff = fracdiff_fixed(v, d_fix)
            fw = fracdiff_wf(v, pp)
            ic_f = ic(ff[BURN:], fwd[BURN:])
            ic_w = ic(fw[BURN:], fwd[BURN:])
            if np.isfinite(ic_f) and np.isfinite(ic_w):
                all_rows.append({"symbol": sym, "col": c, "d_fix": round(d_fix, 4),
                                 "ic_fixed": ic_f, "ic_wf": ic_w, "dIC": ic_w - ic_f})
        print(f"[{sym}] L1 {L1.shape} targets={len(targets)} time={time.perf_counter()-t0:.1f}s", flush=True)

    df = pd.DataFrame(all_rows)
    pd.set_option("display.width", 200)
    print("\n================ 真實 L1 fixed-vs-WF d* 配對 IC ================")
    print(f"n_features(配對成功)={len(df)}")
    g = df.groupby("symbol").agg(
        n=("dIC", "size"),
        ic_fixed_absmean=("ic_fixed", lambda x: np.mean(np.abs(x))),
        ic_wf_absmean=("ic_wf", lambda x: np.mean(np.abs(x))),
        dIC_mean=("dIC", "mean"),
        dIC_medabs=("dIC", lambda x: np.median(np.abs(x))),
    ).round(5)
    print(g.to_string())
    d = df["dIC"].to_numpy()
    pos = int((d > 0).sum()); neg = int((d < 0).sum())
    print(f"\nPOOLED: n={len(d)} dIC_mean={d.mean():.5f} median|dIC|={np.median(np.abs(d)):.5f} "
          f"|dIC|>0.01 比例={np.mean(np.abs(d) > 0.01):.2%}")
    print(f"sign: WF較佳={pos} fixed較佳={neg}  (sign test 接近 50/50 = 無方向性增益)")
    # 用 |IC| 比較(訊號強度)
    abs_gain = np.abs(df['ic_wf'].to_numpy()) - np.abs(df['ic_fixed'].to_numpy())
    print(f"|IC| 增益(WF-fixed) mean={abs_gain.mean():.5f} median={np.median(abs_gain):.5f} "
          f">0 比例={np.mean(abs_gain>0):.2%}")
    print("\n裁決依據: dIC_mean 在雜訊內 + sign≈50/50 + |IC|增益≈0 → WF 無下游價值")


if __name__ == "__main__":
    main()
