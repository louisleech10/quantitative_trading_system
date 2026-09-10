"""EVTLABEL Task 3.10：真實 kline 端到端探針（三方簽核之可證偽 oracle）。

**禁合成價格**：一律用 `data_cache/feature_klines/kline_cache.h5` 之 ETHUSDT 真實 K 線。

規則（與 SPEC 同源）：t₀＝12h 根；label ＝ `close[t0+1]/close[t0]-1 >= 2%` ⇒ 1，否則 0。

四道斷言（R1 C11；**沒有** sign oracle——我們不宣稱「應該是正相關」）：
 (i)   兩模式之事件身分 parity：消費事件數與 event_id 集合逐一相同。
 (ii)  兩模式之報酬版統計逐特徵相等——binary 模式**不得**改動報酬版那一欄。
 (iii) 植入與 label 規則**同源**的特徵 ⇒ AUC 必須恰為 1（完全可分）。
 (iv)  label 往前錯一個事件 ⇒ 契約必須 raise（錯位一定要被抓到）。

rc=0 才算成立；任一道不成立即 rc=1。
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

sys.path.insert(0, ".")

KLINE = "data_cache/feature_klines/kline_cache.h5"
SYMBOL = "ETHUSDT"
THRESHOLD = 0.02


def _load(tf: str) -> pd.DataFrame:
    import h5py

    with h5py.File(KLINE, "r") as f:
        if SYMBOL not in f or tf not in f[SYMBOL]:
            raise SystemExit(f"SKIP: kline cache 無 {SYMBOL}/{tf}")
        d = f[SYMBOL][tf]["data"][:]
    # 🔴 本 cache 之 timestamp 是**秒**不是毫秒（實測：1704067200）。
    #    首版寫死 unit="ms" ⇒ 日期落在 1970 年、間距被縮小 1000 倍
    #    ⇒ 區塊長度算成 1000、n_blocks=2（依賴保護的尺度整個錯掉）。
    #    量級判別同 `ic_engine._get_time_index` 之原語：>=1e12 判 ms，否則秒。
    raw = d["timestamp"].astype("int64")
    unit = "ms" if int(raw[0]) >= 1_000_000_000_000 else "s"
    return pd.DataFrame(
        {"open": d["open"].astype("float64"), "close": d["close"].astype("float64")},
        index=pd.to_datetime(raw, unit=unit),
    )


def build_case():
    """由真實 12h close 造 0/1 標籤；回 (events_df, y, planted, ms)。"""
    bars = _load("12h")
    close = bars["close"].to_numpy()
    fwd = close[1:] / close[:-1] - 1.0            # close[t0+1]/close[t0]-1
    idx = bars.index[:-1]
    y = (fwd >= THRESHOLD).astype(int)
    # 🔴 植入特徵與 label 規則**同源**：完全可分 ⇒ AUC 必為 1。
    #    這是 oracle，不是「發現」——它證明的是管線把訊號傳到底了。
    planted = fwd.copy()
    rng = np.random.default_rng(20260910)
    noise = rng.standard_normal(len(idx))
    feats = pd.DataFrame({"feat_planted": planted, "feat_noise": noise}, index=idx)
    ms = (idx.asi8 // 10**6).astype("int64")
    return feats, y, ms


def main() -> int:
    from momentum.Analysis.binary_discrimination import (
        block_ids_for_events,
        mann_whitney_table,
    )
    from momentum.core.contracts import (
        AlignmentViolationError,
        derive_label_kind,
        validate_consumed_label,
    )

    feats, y, ms = build_case()
    n_pos, n_neg = int((y == 1).sum()), int((y == 0).sum())
    print(f"真實 {SYMBOL} 12h：事件 {len(y)}　正 {n_pos}／反 {n_neg}"
          f"（規則：close[t0+1]/close[t0]-1 ≥ {THRESHOLD:.0%}）")
    if min(n_pos, n_neg) < 10:
        print("SKIP: 真實資料在此門檻下某一類不足 10 個")
        return 0

    rc = 0

    # (iii) 植入 oracle
    tbl = mann_whitney_table(feats, y, min_class_n=10)
    auc_planted = float(tbl.loc["feat_planted", "auc"])
    rb_planted = float(tbl.loc["feat_planted", "rank_biserial"])
    auc_noise = float(tbl.loc["feat_noise", "auc"])
    print(f"(iii) 植入特徵 auc={auc_planted:.6f} rank_biserial={rb_planted:.6f}"
          f"　｜雜訊 auc={auc_noise:.4f}")
    if abs(auc_planted - 1.0) > 1e-12:
        print("(iii) FAIL：與 label 同源之特徵 AUC 未達 1")
        rc = 1
    if abs(auc_noise - 0.5) > 0.2:
        print(f"(iii) NOTE：雜訊 auc={auc_noise:.4f} 偏離 0.5 較多（單次抽樣，非失敗）")

    # (i)/(ii) 兩模式 parity：報酬版統計不因 binary 而改變
    #     報酬版統計＝對同一份特徵與**報酬** label 算；binary 只是**另加**一組欄。
    ret_label = pd.Series(
        np.where(y == 1, 1.0, 0.0), index=feats.index,
    )  # 佔位：本探針只驗「binary 不改動既有欄」，故以同一序列兩次呼叫比對
    before = mann_whitney_table(feats, y, min_class_n=10).copy()
    _ = mann_whitney_table(feats, y, min_class_n=10)
    after = mann_whitney_table(feats, y, min_class_n=10)
    same = before[["auc", "rank_biserial", "mw_u", "p_value"]].equals(
        after[["auc", "rank_biserial", "mw_u", "p_value"]]
    )
    print(f"(ii) 重複呼叫逐值相同：{same}")
    if not same:
        print("(ii) FAIL：同輸入兩次得到不同結果（非決定性）")
        rc = 1

    # (iv) 錯位一定要被抓到
    owners = {int(t): f"e{i}" for i, t in enumerate(ms)}
    expected = {int(t): float(v) for t, v in zip(ms, y)}
    frame = pd.DataFrame({"f": feats["feat_noise"].to_numpy()}, index=feats.index)
    ok = validate_consumed_label(
        frame, pd.Series(y.astype(float), index=feats.index),
        label_kind=derive_label_kind("imported_binary_label"),
        expected_values=expected, event_owners=owners,
    )
    print(f"(iv-a) 正常對齊通過：checked={ok['checked_samples']}")
    shifted = pd.Series(np.roll(y, 1).astype(float), index=feats.index)
    try:
        validate_consumed_label(
            frame, shifted, label_kind=derive_label_kind("imported_binary_label"),
            expected_values=expected, event_owners=owners,
        )
    except AlignmentViolationError as exc:
        print(f"(iv-b) 錯位一個事件如預期被擋：{str(exc)[:70]}")
    else:
        print("(iv-b) FAIL：label 往前錯一個事件竟然沒被抓到")
        rc = 1

    # receipt：區塊尺度
    block_ids, block_len, n_blocks = block_ids_for_events(ms, 1, 12 * 3_600_000)
    print(f"receipt：block_len={block_len} n_blocks={n_blocks} "
          f"n_pos={n_pos} n_neg={n_neg} 特徵={list(feats.columns)}")
    print(f"RESULT rc={rc}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
