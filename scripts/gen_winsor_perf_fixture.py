"""生成 P0 winsor byte-identical 測試的固定輸入 fixture(FF_CAUSAL_PERF_FIX SPEC §G)。

確定性:從真實 ETH 1h kline 衍生 20352×N float64 矩陣,無隨機、無未來洩漏(僅作 kernel
輸入,衍生方式寫死)。輸出 .npy + .sha256 進 repo,測試不依賴 gitignored data_cache。

執行:source venv/bin/activate && python scripts/gen_winsor_perf_fixture.py
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import h5py
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
KLINE = ROOT / "data_cache/feature_klines/kline_cache.h5"
OUT_NPY = ROOT / "tests/_fixtures/winsor_input_eth1h.npy"
OUT_SHA = ROOT / "tests/_fixtures/winsor_input_eth1h.sha256"

N_COLS = 32  # 寫死;20352×32 float64 ≈ 5.2 MB committed


def _derive(close: np.ndarray) -> np.ndarray:
    """寫死的確定性衍生:close + 多 lag log-return + 多窗 rolling mean,湊滿 N_COLS。

    目的:讓 kernel 測到多種分布的欄(含 NaN 暖機),非作真實特徵,故無洩漏顧慮。
    """
    n = close.shape[0]
    cols: list[np.ndarray] = [close.copy()]
    # log-returns at increasing lags
    for lag in (1, 2, 3, 6, 12, 24, 48, 168):
        r = np.full(n, np.nan, dtype=np.float64)
        r[lag:] = np.log(close[lag:] / close[:-lag])
        cols.append(r)
    # rolling means at increasing windows (causal, NaN warmup)
    for w in (3, 6, 12, 24, 48, 96, 168, 252):
        m = np.full(n, np.nan, dtype=np.float64)
        csum = np.cumsum(close)
        m[w - 1 :] = (csum[w - 1 :] - np.concatenate(([0.0], csum[:-w]))) / w
        cols.append(m)
    # first differences at increasing lags
    for lag in (1, 2, 5, 10, 20):
        d = np.full(n, np.nan, dtype=np.float64)
        d[lag:] = close[lag:] - close[:-lag]
        cols.append(d)
    # scaled / centred deterministic transforms to fill to N_COLS
    base_extra = [
        close * 0.5,
        close - close.mean(),
        np.sqrt(np.abs(close)),
        np.cbrt(close),
        close ** 2 / close.max(),
    ]
    cols.extend(arr.astype(np.float64) for arr in base_extra)
    while len(cols) < N_COLS:
        # deterministic filler: lagged close
        lag = len(cols)
        c = np.full(n, np.nan, dtype=np.float64)
        c[lag:] = close[:-lag]
        cols.append(c)
    mat = np.column_stack(cols[:N_COLS]).astype(np.float64)
    return np.ascontiguousarray(mat)


def main() -> None:
    if not KLINE.is_file():
        raise SystemExit(f"kline cache 不存在:{KLINE}")
    with h5py.File(KLINE, "r") as f:
        data = f["ETHUSDT/1h/data"][:]
    close = data["close"].astype(np.float64)
    if close.shape[0] != 20352:
        raise SystemExit(f"預期 20352 列,實得 {close.shape[0]}")
    mat = _derive(close)
    assert mat.shape == (20352, N_COLS), mat.shape
    OUT_NPY.parent.mkdir(parents=True, exist_ok=True)
    np.save(OUT_NPY, mat, allow_pickle=False)
    digest = hashlib.sha256(OUT_NPY.read_bytes()).hexdigest()
    OUT_SHA.write_text(digest + "\n", encoding="utf-8")
    print(f"wrote {OUT_NPY} shape={mat.shape} dtype={mat.dtype}")
    print(f"sha256={digest}")


if __name__ == "__main__":
    main()
