"""SPLITUNIFY C10 之實測：canonical 邊界若由「特徵列 universe」與「K 線 bars universe」
各自算出，兩者是否相同？

背景：`EventSplitPlan` 唯一 producer `split_events` 只被 `pipeline.py:691` 呼叫，
其唯一生產 caller `api/services/case_import_service.py:1610` **既無 SplitPlan 也無特徵列 universe**
（`run_with_params` 不帶 `feature_config` ⇒ `_materialize` 回 None）。
故 R1 三家給的簽名（要求呼叫端持有 `feature_index`）在事件掃描端無法滿足。

候選方案 2（canonical 邊界下傳）之可行性，取決於：
    以**同一規則**、但**不同 universe**（features vs bars）算出的邊界，是否相同？

否證觀測：兩者算出的 train_end_ms／test_start_ms 不同 ⇒ 方案 2 只是把「第二份算術」換個名字，
C-2 之禁令仍被違反。
"""
import sys

sys.path.insert(0, ".")

import numpy as np
import pandas as pd

from momentum.core.split_preview import holdout_split_point, holdout_test_row_index

SYMBOL = "ETHUSDT"
TF = "1h"
FEATURE_TS = "data_cache/features/ETHUSDT/1h/4a8a0b3726cc906ab3534994605e77f5/timestamps.parquet"

# 與 IC 事件路徑同參（EVTLABEL 收工時之實值）
OOS_TEST_SIZE = 0.3
PURGE_GAP = 12      # label 窗 12h ＝ 1h 特徵 12 根
EMBARGO = 144       # 批次宣告之往後看深度


def boundary_from_index(ms: np.ndarray, *, tag: str):
    """由某個 universe 的時間戳陣列算出 canonical 邊界（train_end_ms, test_start_ms）。"""
    n = int(len(ms))
    sp = holdout_split_point(n, oos_test_size=OOS_TEST_SIZE)
    test_rows = holdout_test_row_index(
        n, oos_test_size=OOS_TEST_SIZE, purge_gap=PURGE_GAP, embargo=EMBARGO
    )
    train_end = int(ms[sp - 1]) if sp > 0 else -1
    test_start = int(ms[test_rows[0]]) if test_rows.size else -1
    print(f"[{tag}] n={n} split_point={sp} test_rows={test_rows.size} "
          f"train_end_ms={train_end} test_start_ms={test_start}")
    print(f"[{tag}] train_end={pd.to_datetime(train_end, unit='ms')} "
          f"test_start={pd.to_datetime(test_start, unit='ms')}")
    return train_end, test_start, n


def load_feature_ms() -> np.ndarray:
    """🔴 FF run 之 timestamps.parquet 為 epoch **秒**（int64），不是毫秒也不是 datetime。
    首版探針直接當 ms 用 ⇒ 日期跑到 1970——正是 CLAUDE-R1-P1-05 記的那個單位坑，
    我自己在寫這支探針時**又踩了一次**。故此處明寫單位並斷言年份合理。"""
    ts = pd.read_parquet(FEATURE_TS)
    raw = np.asarray(ts["timestamp"], dtype="int64")
    ms = raw * 1000
    year = pd.to_datetime(int(ms[0]), unit="ms").year
    assert 2015 <= year <= 2035, f"feature timestamp 單位判定錯：首筆年份={year}"
    return ms


def load_bars_ms() -> np.ndarray:
    from momentum.Analysis.event_samples.bars_source import load_bars_from_kline_cache

    bars = load_bars_from_kline_cache([SYMBOL], [TF])
    df = bars[SYMBOL][TF]
    col = "open_time_ms" if "open_time_ms" in df.columns else df.columns[0]
    return np.asarray(df[col], dtype="int64")


def main() -> int:
    feat_ms = load_feature_ms()
    bars_ms = load_bars_ms()

    f_train_end, f_test_start, f_n = boundary_from_index(feat_ms, tag="features")
    b_train_end, b_test_start, b_n = boundary_from_index(bars_ms, tag="bars")

    print()
    print(f"universe 列數差：features={f_n} bars={b_n} delta={b_n - f_n}")
    feat_set, bars_set = set(feat_ms.tolist()), set(bars_ms.tolist())
    print(f"只在 features={len(feat_set - bars_set)}　只在 bars={len(bars_set - feat_set)}")

    same = (f_train_end == b_train_end) and (f_test_start == b_test_start)
    if not same:
        print()
        print("DISPROVED：同一規則、不同 universe 算出的邊界**不同**")
        print(f"  train_end 差 {b_train_end - f_train_end} ms "
              f"（{(b_train_end - f_train_end) / 3_600_000:.2f} 小時）")
        print(f"  test_start 差 {b_test_start - f_test_start} ms "
              f"（{(b_test_start - f_test_start) / 3_600_000:.2f} 小時）")
        print("  ⇒ 候選方案 2（canonical 邊界下傳、兩端各自以自己的 universe 算）不成立：")
        print("     它仍是兩份算術，只是名字改了。C10 須改採方案 1 或 3。")
        return 1
    print()
    print("① 未裁切情境：兩個 universe 給出**相同**邊界。")

    # ② EVTALIGN 裁切情境：特徵比 K 線短（頭尾被裁）時，邊界會不會漂？
    #    `ic_filter_orchestrator` 之期間對齊會把特徵裁到與 K 線交集，
    #    裁掉的列數視資料而定——這裡掃一組代表性值，量出邊界位移。
    print()
    print("② 裁切情境（特徵頭尾各被裁 N 根，K 線 universe 不變）：")
    print(f"{'裁切N':>6} {'features_n':>11} {'train_end 位移(h)':>18} {'test_start 位移(h)':>19}")
    worst = 0.0
    for n_trim in (1, 5, 24, 168):
        trimmed = feat_ms[n_trim:-n_trim] if n_trim * 2 < len(feat_ms) else feat_ms
        t_end, t_start, t_n = _boundary_quiet(trimmed)
        d_end = (t_end - b_train_end) / 3_600_000
        d_start = (t_start - b_test_start) / 3_600_000
        worst = max(worst, abs(d_end), abs(d_start))
        print(f"{n_trim:>6} {t_n:>11} {d_end:>18.2f} {d_start:>19.2f}")

    print()
    if worst > 0:
        print(f"DISPROVED（裁切情境）：只要特徵被裁過，邊界最大位移 {worst:.2f} 小時。")
        print("  ⇒ 候選方案 2（兩端各自以自己的 universe 算 canonical 邊界）**不成立**：")
        print("     它仍是兩份算術，只是名字改了；EVTALIGN 一裁就分歧。")
        print("  ⇒ C10 須改採方案 1（投影上移到 IC 側、事件掃描端不再自產驗證段數字）")
        print("     或方案 3（事件掃描端載入同一 post-trim feature universe）。")
        return 1
    print("裁切情境下亦等價（不預期）——請檢查探針是否真的裁到。")
    return 0


def _boundary_quiet(ms: np.ndarray):
    n = int(len(ms))
    sp = holdout_split_point(n, oos_test_size=OOS_TEST_SIZE)
    rows = holdout_test_row_index(
        n, oos_test_size=OOS_TEST_SIZE, purge_gap=PURGE_GAP, embargo=EMBARGO
    )
    return (int(ms[sp - 1]) if sp > 0 else -1,
            int(ms[rows[0]]) if rows.size else -1,
            n)


if __name__ == "__main__":
    raise SystemExit(main())
