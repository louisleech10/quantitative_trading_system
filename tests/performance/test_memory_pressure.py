"""
L3 / L6.5 記憶體壓力測試 v2 — 快速版

策略：
  Phase 1: 純數學估算（零 RAM 開銷）
  Phase 2: L3 micro-bench（小規模實測，找實際 RSS 與估算的比值）
  Phase 3: L6.5 子步驟分段剖析（跳過 L3，直接用合成的寬 DataFrame）
  Phase 4: 找 OOM 邊界（漸進式放大直到 RSS > 安全線）

使用方式：
  PYTHONPATH="$PWD" venv/bin/python tests/performance/test_memory_pressure.py
"""

from __future__ import annotations

import gc
import os
import resource
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_current_rss_mb() -> float:
    """取得即時 RSS (macOS: bytes, Linux: KB)"""
    try:
        import psutil
        return psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)
    except ImportError:
        usage = resource.getrusage(resource.RUSAGE_SELF)
        if sys.platform == "darwin":
            return usage.ru_maxrss / (1024 * 1024)
        return usage.ru_maxrss / 1024


def df_size_mb(df: pd.DataFrame) -> float:
    return df.memory_usage(deep=True).sum() / (1024 * 1024)


def make_df(n_rows: int, n_cols: int, seed: int = 42) -> pd.DataFrame:
    np.random.seed(seed)
    data = np.random.randn(n_rows, n_cols).astype(np.float64)
    for j in range(n_cols):
        data[: np.random.randint(5, 50), j] = np.nan
    return pd.DataFrame(data, columns=[f"f{i:05d}" for i in range(n_cols)])


# ---------------------------------------------------------------------------
# Phase 1: 純數學估算
# ---------------------------------------------------------------------------

def phase1_estimation():
    print("\n" + "=" * 70)
    print("  Phase 1: 純數學估算 (零記憶體開銷)")
    print("=" * 70)

    configs = [
        ("目前配置 (10w×10a)", 960, 52_000, 10, 10),
        ("精簡配置 (4w×5a)",   960, 52_000,  4,  5),
        ("最小配置 (3w×4a)",   960, 52_000,  3,  4),
        ("1h 短資料 (10w×10a)", 960, 10_000, 10, 10),
    ]

    print(f"\n  {'情境':<25} {'L1 輸入':<15} {'L3 輸出欄位':<15} {'L3 DF (MB)':<12} {'L3+L6.5 峰值':<15} {'8GB可行?'}")
    print(f"  {'-'*97}")

    for name, n_cols, n_rows, n_win, n_agg in configs:
        l3_out_cols = n_cols * n_win * n_agg
        l3_bytes = n_rows * l3_out_cols * 8
        l3_mb = l3_bytes / (1024 * 1024)
        # L6.5 peak: rank_transform creates a rolling object ≈ same size as input
        # winsorization: in-place, ~0 extra
        # zscore: 2 × rolling objects ≈ 2 × input size
        # Peak ≈ input + 2× (rolling temp) ≈ 3 × L3 output
        l65_peak_mb = l3_mb * 3
        total_peak_mb = l3_mb + l65_peak_mb  # simplification
        feasible = "✅" if total_peak_mb < 6000 else "❌ OOM"

        print(f"  {name:<25} {n_rows:>6,}×{n_cols:<6} {l3_out_cols:>12,}  {l3_mb:>10,.0f}  {total_peak_mb:>12,.0f}   {feasible}")

    # 找安全邊界: 在 52K 行下，多少 L1 欄位可以承受 10w×10a？
    print(f"\n  === OOM 安全邊界 (52K rows, 記憶體上限=6GB) ===")
    for n_win, n_agg, label in [(10, 10, "10w×10a"), (4, 5, "4w×5a"), (3, 4, "3w×4a")]:
        # target: n_cols * n_win * n_agg * 52000 * 8 * 4 (peak factor) < 6GB
        max_cols = int(6_000 * 1024 * 1024 / (52_000 * n_win * n_agg * 8 * 4))
        print(f"  {label}: 最多 {max_cols} 個 L1 特徵 (L3 輸出 {max_cols * n_win * n_agg:,} 欄位)")

    print(f"\n  結論: 目前 960×10×10 = 96,000 欄位 × 52K 行 ≈ 38 GB → 在 8GB M1 上必然 OOM")


# ---------------------------------------------------------------------------
# Phase 2: L3 micro-bench
# ---------------------------------------------------------------------------

def phase2_l3_microbench():
    from momentum.FeatureEngineering.operators.rolling_aggregator import RollingAggregator

    print("\n" + "=" * 70)
    print("  Phase 2: L3 RollingAggregator 微基準 (小規模)")
    print("=" * 70)

    configs = [
        ("10w×10a (full)", {"enabled": True,
            "windows": [3, 5, 8, 13, 21, 34, 55, 89, 144, 233],
            "aggregators": ["slope", "std", "mean", "rank", "zscore", "skew", "kurt", "min", "max", "range"],
            "apply_to": "all"}),
        ("4w×5a (reduced)", {"enabled": True,
            "windows": [5, 13, 34, 89],
            "aggregators": ["mean", "std", "rank", "slope", "range"],
            "apply_to": "all"}),
        ("3w×3a (minimal)", {"enabled": True,
            "windows": [13, 34, 89],
            "aggregators": ["mean", "std", "rank"],
            "apply_to": "all"}),
    ]

    # 用 50 cols × 5K rows — 小到不會 OOM，大到能測出趨勢
    n_rows = 5_000
    n_cols = 50

    for label, cfg in configs:
        df = make_df(n_rows, n_cols)
        gc.collect()
        rss0 = get_current_rss_mb()
        t0 = time.perf_counter()

        agg = RollingAggregator(cfg)
        result = agg.compute_all(df)

        elapsed = time.perf_counter() - t0
        rss1 = get_current_rss_mb()
        out_mb = df_size_mb(result)
        in_mb = df_size_mb(df)

        n_w = len(cfg["windows"])
        n_a = len(cfg["aggregators"])
        multiplier = result.shape[1] / n_cols

        print(f"\n  [{label}] {df.shape} → {result.shape}")
        print(f"    DF: {in_mb:.1f} MB → {out_mb:.1f} MB (×{multiplier:.0f})")
        print(f"    RSS delta: {rss1 - rss0:.1f} MB, 耗時: {elapsed:.1f}s")
        print(f"    外推 960 cols × 52K rows: {out_mb * (960 / n_cols) * (52_000 / n_rows):.0f} MB")

        del result, df
        gc.collect()


# ---------------------------------------------------------------------------
# Phase 3: L6.5 子步驟剖析（跳過 L3，直接用合成 wide DF）
# ---------------------------------------------------------------------------

def phase3_l65_profiling():
    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

    print("\n" + "=" * 70)
    print("  Phase 3: L6.5 子步驟剖析")
    print("=" * 70)

    l65_config = {
        "mode": "replace",
        "winsorization": {"method": "sigma", "sigma_k": 3.0, "apply_to": "all"},
        "rank_transform": {"enabled": True, "window": 252, "apply_to": "all"},
        "adaptive_zscore": {"enabled": True, "windows": [100, 252], "epsilon": 1e-8, "apply_to": "all"},
    }

    # 測試不同欄位數的 L6.5（行數固定 10K 來加快速度）
    n_rows = 10_000
    test_sizes = [500, 2_000, 5_000]

    for n_cols in test_sizes:
        print(f"\n  --- {n_rows:,} rows × {n_cols:,} cols ---")
        df = make_df(n_rows, n_cols)
        preprocessor = FeaturePreprocessor(l65_config)

        steps = [
            ("winsorization", preprocessor._apply_winsorization),
            ("rank_transform", preprocessor._apply_rank_transform),
            ("adaptive_zscore", preprocessor._apply_adaptive_zscore),
        ]

        current = df.copy()
        for step_name, step_fn in steps:
            gc.collect()
            rss0 = get_current_rss_mb()
            t0 = time.perf_counter()

            try:
                current = step_fn(current)
                elapsed = time.perf_counter() - t0
                rss1 = get_current_rss_mb()
                out_mb = df_size_mb(current)

                # 外推到 52K rows × 20K cols (精簡 L3 的典型輸出)
                scale_factor = (52_000 / n_rows) * (20_000 / n_cols) if n_cols < 20_000 else (52_000 / n_rows)
                extrapolated_time = elapsed * scale_factor

                print(f"    [{step_name:>16}] {current.shape}, "
                      f"RSS Δ{rss1 - rss0:>+7.1f} MB, "
                      f"{elapsed:>6.2f}s "
                      f"(→52K×20K: ≈{extrapolated_time:.0f}s)")

            except MemoryError as e:
                print(f"    [{step_name:>16}] ❌ OOM: {e}")
                break

        del current, df
        gc.collect()


# ---------------------------------------------------------------------------
# Phase 4: OOM 邊界探測
# ---------------------------------------------------------------------------

def phase4_oom_boundary():
    from momentum.FeatureEngineering.operators.rolling_aggregator import RollingAggregator

    print("\n" + "=" * 70)
    print("  Phase 4: OOM 邊界探測 (漸進式放大)")
    print("=" * 70)

    # 用精簡配置（4w×5a），增加 input 欄位數直到接近 OOM
    reduced_cfg = {
        "enabled": True,
        "windows": [5, 13, 34, 89],
        "aggregators": ["mean", "std", "rank", "slope", "range"],
        "apply_to": "all",
    }

    n_rows = 5_000  # 短序列加速
    safe_limit_mb = 4000  # 給 OS 保留充足空間

    print(f"  配置: 4 windows × 5 aggregators = ×20 倍")
    print(f"  固定行數: {n_rows:,}, 漸增欄位數")
    print(f"  安全上限: {safe_limit_mb} MB\n")

    for n_cols in [50, 100, 200, 400, 600, 800]:
        estimated_out_cols = n_cols * 4 * 5
        estimated_mb = (n_rows * estimated_out_cols * 8) / (1024 * 1024)

        if estimated_mb > safe_limit_mb:
            print(f"  {n_cols:>4} cols → {estimated_out_cols:>6,} out → {estimated_mb:>7.0f} MB (預估) → ⚠️ 跳過")
            continue

        df = make_df(n_rows, n_cols)
        gc.collect()
        rss0 = get_current_rss_mb()
        t0 = time.perf_counter()

        try:
            agg = RollingAggregator(reduced_cfg)
            result = agg.compute_all(df)
            elapsed = time.perf_counter() - t0
            rss1 = get_current_rss_mb()
            out_mb = df_size_mb(result)
            print(f"  {n_cols:>4} cols → {result.shape[1]:>6,} out → "
                  f"DF {out_mb:>7.0f} MB, RSS Δ{rss1 - rss0:>+7.0f} MB, {elapsed:>5.1f}s ✅")
            del result
        except MemoryError:
            print(f"  {n_cols:>4} cols → ❌ OOM!")
            break
        finally:
            del df
            gc.collect()

    # 同樣測 L6.5
    print(f"\n  --- L6.5 邊界探測 (固定 {n_rows:,} rows) ---")

    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor
    l65_config = {
        "mode": "replace",
        "winsorization": {"method": "sigma", "sigma_k": 3.0, "apply_to": "all"},
        "rank_transform": {"enabled": True, "window": 252, "apply_to": "all"},
        "adaptive_zscore": {"enabled": True, "windows": [100, 252], "epsilon": 1e-8, "apply_to": "all"},
    }

    for n_cols in [500, 1_000, 2_000, 5_000, 10_000]:
        estimated_mb = (n_rows * n_cols * 8 * 3) / (1024 * 1024)  # ~3× for rolling temps
        if estimated_mb > safe_limit_mb:
            print(f"  {n_cols:>6,} cols → {estimated_mb:>7.0f} MB (預估峰值) → ⚠️ 跳過")
            continue

        df = make_df(n_rows, n_cols)
        gc.collect()
        rss0 = get_current_rss_mb()
        t0 = time.perf_counter()

        try:
            pp = FeaturePreprocessor(l65_config)
            result = pp.transform(df)
            elapsed = time.perf_counter() - t0
            rss1 = get_current_rss_mb()
            out_mb = df_size_mb(result)
            print(f"  {n_cols:>6,} cols → RSS Δ{rss1 - rss0:>+7.0f} MB, {elapsed:>6.1f}s ✅")
            del result
        except MemoryError:
            print(f"  {n_cols:>6,} cols → ❌ OOM!")
            break
        finally:
            del df
            gc.collect()


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def print_summary():
    print("\n" + "=" * 70)
    print("  壓力測試總結 & 建議")
    print("=" * 70)

    print("""
  📊 數學事實:
    ┌──────────────────────────────────────────────────────────────────┐
    │ 目前配置: 960 L1特徵 × 10w × 10a = 96,000 L3 欄位               │
    │ 52K rows × 96K cols × 8 bytes = ~38 GB                          │
    │ 加上 L6.5 rolling temps → 峰值 ≈ 76-114 GB                      │
    │                                                                  │
    │ 💀 8GB M1 根本不可能                                              │
    └──────────────────────────────────────────────────────────────────┘

  🔧 修正方案 (按優先順序):

  1. [必做] 減少 L3 配置規模
     ├─ windows: [3,5,8,13,21,34,55,89,144,233] → [5,13,34,89] (4個)
     ├─ aggregators: 10個 → ["mean","std","rank","slope","range"] (5個)
     └─ 960 × 4 × 5 = 19,200 欄位 × 52K = ~7.6 GB → 仍然偏大

  2. [必做] apply_to 改為選擇性
     ├─ 不是所有 960 個 L1 特徵都需要滾動聚合
     ├─ 只對 top-IC 或人工選定的特徵做 rolling
     └─ 例如只取 200 個 → 200 × 4 × 5 = 4,000 欄位 = ~1.6 GB ✅

  3. [建議] float32 降精度
     └─ 全 float64 → float32: 記憶體直接砍半

  4. [建議] L3 streaming mode
     └─ 每 chunk 計算後立即寫入 HDF5，不在記憶體中累積完整 DF

  5. [建議] L6.5 分批處理
     └─ 對 20K+ 欄位的 rank_transform/zscore，分 chunk 逐批處理

  安全目標: 峰值 RSS < 4 GB (給 OS + Python overhead 留 4 GB)
  """)


def main():
    print(f"  System: {sys.platform}, Python {sys.version.split()[0]}")
    print(f"  PID: {os.getpid()}, 起始 RSS: {get_current_rss_mb():.0f} MB")

    try:
        import psutil
        mem = psutil.virtual_memory()
        print(f"  RAM: {mem.total / (1024**3):.1f} GB total, {mem.available / (1024**3):.1f} GB available")
    except ImportError:
        print(f"  (psutil 不可用)")

    phase1_estimation()
    phase2_l3_microbench()
    phase3_l65_profiling()
    phase4_oom_boundary()
    print_summary()


if __name__ == "__main__":
    main()
