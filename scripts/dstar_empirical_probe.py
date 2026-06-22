"""Claude 自產獨立 probe：量化 fracdiff d* Option A(前500校準)是否二階。

對真實 kline,比較 full-range vs date-windowed 的:
  (a) d* Δ   —— 前500不同 → d* 不同?
  (b) 特徵值相關 —— 同輸入序列、用 d*_full vs d*_win 做 fracdiff,重疊段相關係數
  (c) IC Δ   —— fracdiff 特徵對 forward return 的 IC,兩個 d 的差
高相關 + 小 d*Δ + 小 ICΔ → Option A 二階確認。read-only,不改 product 碼。
"""
import numpy as np
import pandas as pd
import h5py
import momentum.FeatureEngineering  # 觸發 read_hdf 補丁(此處用 h5py 直讀)
from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

H5 = "data_cache/feature_klines/kline_cache.h5"
SYMBOLS = ["ADAUSDT", "BCHUSDT", "BNBUSDT", "BTCUSDT", "DOGEUSDT", "ETHUSDT", "LINKUSDT", "SOLUSDT"]
TF = "1h"


def load_close(sym: str, tf: str) -> pd.Series:
    with h5py.File(H5, "r") as f:
        arr = f[f"{sym}/{tf}/data"][:]
    ts = pd.to_datetime(arr["timestamp"], unit="s")
    return pd.Series(np.asarray(arr["close"], dtype=float), index=ts, name="close")


def main() -> None:
    pp = FeaturePreprocessor(config={})  # _find_min_d 用 _calibration_series → 前500
    ffd = FeaturePreprocessor._frac_diff_ffd

    rows = []
    for sym in SYMBOLS:
        try:
            close = load_close(sym, TF).dropna()
        except Exception as e:
            rows.append((sym, "LOAD_FAIL", str(e)[:30], "", "", "", ""))
            continue
        logc = np.log(close)
        n = len(logc)
        # date-windowed:取歷史中段一個子區間(約 6-9 個月,1h ≈ 4380-6570 bars)
        w_start = n // 3
        w_end = min(n, w_start + 6000)
        win = logc.iloc[w_start:w_end]

        d_full = pp._find_min_d(logc)
        d_win = pp._find_min_d(win)

        # 同輸入序列(full log close)、用兩個 d 做 fracdiff → 隔離「d 差異」對特徵值的影響
        frac_full = ffd(logc, d_full)
        frac_wind = ffd(logc, d_win)
        # 重疊段(windowed 涵蓋的日期)比較
        seg = slice(w_start, w_end)
        a = frac_full.iloc[seg]
        b = frac_wind.iloc[seg]
        mask = a.notna() & b.notna()
        corr = float(np.corrcoef(a[mask], b[mask])[0, 1]) if mask.sum() > 10 else np.nan

        # IC:fracdiff 特徵 vs forward 1-bar return(重疊段)
        fwd = close.pct_change().shift(-1)
        fwd_seg = fwd.iloc[seg]
        m2 = a.notna() & fwd_seg.notna()
        m3 = b.notna() & fwd_seg.notna()
        ic_full = float(np.corrcoef(a[m2], fwd_seg[m2])[0, 1]) if m2.sum() > 10 else np.nan
        ic_win = float(np.corrcoef(b[m3], fwd_seg[m3])[0, 1]) if m3.sum() > 10 else np.nan

        rows.append((sym, f"{d_full:.4f}", f"{d_win:.4f}", f"{abs(d_full-d_win):.4f}",
                     f"{corr:.5f}", f"{ic_full:+.5f}", f"{ic_win:+.5f}",
                     f"{abs(ic_full-ic_win):.5f}"))

    hdr = ("symbol", "d*_full", "d*_win", "|Δd*|", "feat_corr", "IC_full", "IC_win", "|ΔIC|")
    print("  ".join(f"{h:>9}" for h in hdr))
    for r in rows:
        print("  ".join(f"{str(c):>9}" for c in r))

    # 彙總
    dds = [float(r[3]) for r in rows if len(r) == 8 and r[3] not in ("",)]
    corrs = [float(r[4]) for r in rows if len(r) == 8]
    dics = [float(r[7]) for r in rows if len(r) == 8]
    print("\n=== 彙總 ===")
    print(f"|Δd*|  max={max(dds):.4f} mean={np.mean(dds):.4f}")
    print(f"feat_corr min={min(corrs):.5f} mean={np.mean(corrs):.5f}")
    print(f"|ΔIC|  max={max(dics):.5f} mean={np.mean(dics):.5f}")
    print("\n判讀:|Δd*|小 + feat_corr≈1 + |ΔIC|≪|IC| → Option A 二階確認")


if __name__ == "__main__":
    main()
