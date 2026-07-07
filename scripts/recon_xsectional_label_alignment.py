"""投偵察確認腳本：cross_sectional 標籤對齊 F1 回歸 + 修法驗證（真實資料）。

用真實 data_cache/features (BTC/ETH/BCH ×12h e53e2290) + 真實 kline_cache.h5，
證明：
  1. 現況 _append_cross_sectional_labels 邏輯對 DatetimeIndex features 產全 NaN 標籤（F1）。
  2. 修法（kline int64-ts → datetime 對齊）→ 標籤有值、forward 正確、末列 NaN、per-symbol 各異。
退出碼 0 = 兩者皆如預期（bug 重現 + 修法有效）。
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from momentum.factories import (
    create_feature_library,
    create_kline_storage_manager,
    create_label_generator,
)

SYMS = ["BTCUSDT", "ETHUSDT", "BCHUSDT"]
TF = "12h"
CH = "e53e22906c35363757f4cd49d27f973e"
KLINE_DIR = "data_cache/feature_klines"


def _build_cross_index() -> pd.DataFrame:
    lib = create_feature_library()
    frames = []
    for sym in SYMS:
        ri = lib._reader.load_row_index_v2(sym, TF, CH, artifact_kind="raw")
        if ri is None:
            print(f"SKIP: 無 row_index sidecar for {sym}")
            sys.exit(0)
        idx = pd.DatetimeIndex(ri)
        df = pd.DataFrame({"feat_dummy": np.arange(len(idx), dtype=float)}, index=idx)
        df.index.name = "timestamp"
        df["_symbol"] = sym
        frames.append(df)
    return pd.concat(frames, axis=0).set_index("_symbol", append=True)


def _current_logic(cross: pd.DataFrame) -> int:
    """鏡像現況 _append_cross_sectional_labels（RangeIndex kline reindex 到 DatetimeIndex）。"""
    kr = create_kline_storage_manager(cache_dir=KLINE_DIR)
    lg = create_label_generator()
    w = cross.copy()
    for sym in SYMS:
        raw = kr.read_klines(sym, TF)
        lab = lg.generate_returns_by_type(raw["close"], 1, "log")  # RangeIndex
        mask = w.index.get_level_values(1) == sym
        si = w.index[mask].droplevel(1)
        w.loc[mask, "return_1"] = lab.reindex(si).to_numpy()
    return int(w["return_1"].notna().sum())


def _fixed_logic(cross: pd.DataFrame) -> tuple[int, bool, bool, dict]:
    """修法：kline timestamp int64(秒) → DatetimeIndex 後 reindex。"""
    kr = create_kline_storage_manager(cache_dir=KLINE_DIR)
    lg = create_label_generator()
    w = cross.copy()
    forward_ok = True
    last_nan_ok = True
    for sym in SYMS:
        raw = kr.read_klines(sym, TF)
        close = raw["close"].copy()
        close.index = pd.DatetimeIndex(pd.to_datetime(raw["timestamp"], unit="s"))
        lab = lg.generate_returns_by_type(close, 1, "log")
        mask = w.index.get_level_values(1) == sym
        si = w.index[mask].droplevel(1)
        aligned = lab.reindex(si)
        w.loc[mask, "return_1"] = aligned.to_numpy()
        # forward 驗證
        ts = si[100]
        pos = close.index.get_loc(ts)
        manual = np.log(close.iloc[pos + 1] / close.iloc[pos])
        forward_ok &= bool(np.isclose(manual, aligned.iloc[100]))
        last_nan_ok &= bool(np.isnan(aligned.iloc[-1]))
    # per-symbol distinctness at a shared timestamp
    t0 = cross.index.get_level_values(0).unique()[500]
    per_sym = {s: float(w.xs((t0, s))["return_1"]) for s in SYMS}
    distinct = len({round(v, 8) for v in per_sym.values()}) == len(SYMS)
    return int(w["return_1"].notna().sum()), forward_ok and last_nan_ok, distinct, per_sym


def main() -> int:
    cross = _build_cross_index()
    total = len(cross)
    cur_nonnan = _current_logic(cross)
    fix_nonnan, fix_dir_ok, fix_distinct, per_sym = _fixed_logic(cross)

    print(f"cross rows total: {total}")
    print(f"[F1 現況邏輯] return_1 非 NaN: {cur_nonnan}/{total}")
    print(f"[修法] return_1 非 NaN: {fix_nonnan}/{total}")
    print(f"[修法] forward+末列NaN 正確: {fix_dir_ok}")
    print(f"[修法] per-symbol 標籤各異(無跨界污染): {fix_distinct} | {per_sym}")

    bug_reproduced = cur_nonnan == 0
    fix_effective = fix_nonnan > total * 0.9 and fix_dir_ok and fix_distinct
    print(f"RESULT bug_reproduced={bug_reproduced} fix_effective={fix_effective}")
    return 0 if (bug_reproduced and fix_effective) else 1


if __name__ == "__main__":
    sys.exit(main())
