"""L7 dead feature filter 單元 + 邊界 + safety invariant 測試。

對應 docs/NAN_REDUCTION_STRATEGY.md §5.3 與 PLAN §2.4 / §2.6 / §2.8。

關鍵 invariants：
    I-1 Per-column 粒度（frozenset[str]，非 group_id）
    I-2 必須讀過實際資料；空 df → 空 dead_set
    I-3 Output ⊆ Input
    I-4 disable → no-op
"""

from __future__ import annotations

import time

import numpy as np
import pandas as pd
import pytest

from momentum.FeatureEngineering.utils.dead_feature_filter import (
    DeadFeatureDiagnostic,
    dead_column_mask,
    drop_dead_columns,
    find_dead_columns,
)


# ─── 功能性測試 ─────────────────────────────────────────────────


class TestConstantColumns:
    """nunique<2 的欄位應被列入 constant_cols"""

    def test_all_zeros(self) -> None:
        df = pd.DataFrame({"a": [0.0] * 1000, "b": np.random.randn(1000)})
        dead, diag = find_dead_columns(df, min_valid_samples=100)
        assert "a" in dead
        assert "a" in diag.constant_cols
        assert "b" not in dead

    def test_all_same_value(self) -> None:
        df = pd.DataFrame({"a": [42.0] * 500, "b": np.random.randn(500)})
        dead, diag = find_dead_columns(df, min_valid_samples=100)
        assert "a" in diag.constant_cols
        assert "b" not in dead

    def test_all_nan_column(self) -> None:
        # nunique(dropna=True) == 0 < 2 → constant
        df = pd.DataFrame({"a": [np.nan] * 500, "b": np.random.randn(500)})
        dead, diag = find_dead_columns(df, min_valid_samples=100)
        assert "a" in diag.constant_cols  # nunique=0 < 2
        # all-NaN 同時也是 sparse（valid_count=0），但 dead_set 用 union 不重複
        assert "a" in dead
        # diag.total_dropped 用 union 避免重複
        assert diag.total_dropped >= 1


class TestSparseColumns:
    """valid_count<min_valid_samples 的欄位應被列入 sparse_cols"""

    def test_50_valid_out_of_20000_with_min_100(self) -> None:
        np.random.seed(42)
        col = np.full(20000, np.nan)
        col[:50] = np.random.randn(50) * 10 + np.arange(50)  # 50 distinct values
        df = pd.DataFrame({"a": col, "b": np.random.randn(20000)})
        dead, diag = find_dead_columns(df, min_valid_samples=100)
        assert "a" in diag.sparse_cols
        assert "a" in dead

    def test_150_valid_out_of_20000_with_min_100_NOT_dropped(self) -> None:
        """150 > 100 → 保留"""
        np.random.seed(42)
        col = np.full(20000, np.nan)
        col[:150] = np.random.randn(150) * 10 + np.arange(150)
        df = pd.DataFrame({"a": col})
        dead, diag = find_dead_columns(df, min_valid_samples=100)
        assert "a" not in dead
        assert "a" not in diag.sparse_cols
        assert "a" not in diag.constant_cols

    def test_boundary_exactly_min_valid_samples(self) -> None:
        """valid_count == min_valid_samples → NOT dropped (邊界 `<`，非 `<=`)"""
        col = np.full(1000, np.nan)
        col[:100] = np.arange(100)  # 100 distinct
        df = pd.DataFrame({"a": col})
        dead, _ = find_dead_columns(df, min_valid_samples=100)
        assert "a" not in dead

    def test_boundary_min_valid_minus_one(self) -> None:
        """valid_count == min_valid_samples - 1 → dropped"""
        col = np.full(1000, np.nan)
        col[:99] = np.arange(99)  # 99 distinct
        df = pd.DataFrame({"a": col})
        dead, diag = find_dead_columns(df, min_valid_samples=100)
        assert "a" in diag.sparse_cols


class TestNotDeadHighNaNRatio:
    """**核心契約**：高 NaN ratio 但 valid_count 足夠 → 保留（不以 NaN ratio 為標準）"""

    def test_60pct_nan_but_distinct_values_kept(self) -> None:
        np.random.seed(1)
        rows = 20000
        col = np.random.randn(rows)
        # 60% NaN: 留下 8000 valid，distinct values 遠超 100
        nan_idx = np.random.choice(rows, int(rows * 0.6), replace=False)
        col[nan_idx] = np.nan
        df = pd.DataFrame({"a": col})
        dead, _ = find_dead_columns(df, min_valid_samples=100)
        assert "a" not in dead, "60% NaN with many distinct values should NOT be dead"

    def test_99pct_nan_but_100_valid_kept(self) -> None:
        """99% NaN 但仍有 100 個有效值 → 保留"""
        rows = 20000
        col = np.full(rows, np.nan)
        col[:200] = np.random.randn(200)  # 200 valid（>= 100）
        df = pd.DataFrame({"a": col})
        dead, _ = find_dead_columns(df, min_valid_samples=100)
        assert "a" not in dead


# ─── DeadFeatureDiagnostic ─────────────────────────────────────


class TestDiagnostic:
    def test_total_dropped_uses_union_no_double_count(self) -> None:
        # 整欄 NaN 同時是 constant_cols + sparse_cols → total_dropped 應只算一次
        df = pd.DataFrame({"a": [np.nan] * 1000})
        dead, diag = find_dead_columns(df, min_valid_samples=100)
        assert diag.total_dropped == 1  # 不重複

    def test_total_dropped_sums_disjoint(self) -> None:
        df = pd.DataFrame({
            "constant_col": [42.0] * 5000,        # constant 但 valid_count=5000
            "sparse_col": [1.0, 2.0, 3.0] + [np.nan] * 4997,  # sparse 但 nunique=3
        })
        dead, diag = find_dead_columns(df, min_valid_samples=100)
        assert diag.total_dropped == 2

    def test_empty_diagnostic_defaults(self) -> None:
        diag = DeadFeatureDiagnostic()
        assert diag.constant_cols == ()
        assert diag.sparse_cols == ()
        assert diag.total_dropped == 0


# ─── 安全 invariant 契約測試（PLAN §2.6/§2.8）──────────────────


class TestSafetyInvariants:
    """這些測試強制驗證安全 invariants — 失敗即破壞「絕不誤殺好特徵」契約。"""

    def test_I1_returns_frozenset_of_str(self) -> None:
        """I-1: 回傳 type 為 frozenset[str]（非 list/set/dict）"""
        df = pd.DataFrame({"a": [1.0] * 1000, "b": np.random.randn(1000)})
        dead, _ = find_dead_columns(df, min_valid_samples=100)
        assert isinstance(dead, frozenset)
        for item in dead:
            assert isinstance(item, str)
        assert "a" in dead  # constant column
        assert "b" not in dead

    def test_I2_empty_df_returns_empty(self) -> None:
        """I-2: 空 df 直接回傳空 set（never assume dead without reading data）"""
        dead, diag = find_dead_columns(pd.DataFrame(), min_valid_samples=100)
        assert dead == frozenset()
        assert diag.total_dropped == 0

    def test_I2_none_input_returns_empty(self) -> None:
        dead, diag = find_dead_columns(None, min_valid_samples=100)  # type: ignore[arg-type]
        assert dead == frozenset()
        assert diag.total_dropped == 0

    def test_I3_output_subset_of_input(self) -> None:
        """I-3: drop_dead_columns 的 output 欄位 ⊆ input 欄位"""
        np.random.seed(0)
        for _ in range(100):
            n_cols = np.random.randint(1, 50)
            df = pd.DataFrame(
                np.random.randn(np.random.randint(10, 200), n_cols),
                columns=[f"col_{i}" for i in range(n_cols)],
            )
            # 隨機注入 dead columns
            for col in df.columns:
                if np.random.rand() < 0.3:
                    df[col] = np.nan  # 整欄 NaN
            input_cols = set(df.columns)
            dead, _ = find_dead_columns(df, min_valid_samples=10)
            result = drop_dead_columns(df, dead)
            assert set(result.columns).issubset(input_cols), (
                "I-3 violated: result has columns not in input"
            )

    def test_I4_disabled_returns_empty_no_matter_what(self) -> None:
        """I-4: enabled=False 等同 no-op（無論 df 內容）"""
        # 即使 df 全是 dead 也回傳空
        df_all_nan = pd.DataFrame({"a": [np.nan] * 1000, "b": [0.0] * 1000})
        dead, diag = find_dead_columns(df_all_nan, min_valid_samples=100, enabled=False)
        assert dead == frozenset()
        assert diag.total_dropped == 0

    def test_never_kill_good_features_contract(self) -> None:
        """關鍵契約：100 個明顯有效欄位 → 0 個被列入 dead"""
        rows = 5000
        good_df = pd.DataFrame({
            f"good_col_{i}": np.random.randn(rows)
            for i in range(100)
        })
        dead, diag = find_dead_columns(good_df, min_valid_samples=100)
        assert len(dead) == 0
        assert diag.total_dropped == 0

    def test_drop_does_not_add_columns(self) -> None:
        """I-3 加強：drop 後欄位數 == input - dead_set ∩ input"""
        df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        result = drop_dead_columns(df, frozenset({"a"}))
        assert list(result.columns) == ["b"]

    def test_drop_preserves_relative_order(self) -> None:
        """I-3 加強：欄位順序保持 input 的相對順序（不重排）"""
        df = pd.DataFrame({
            "z_first": [1, 2, 3],
            "a_second": [4, 5, 6],
            "m_third": [7, 8, 9],
        })
        result = drop_dead_columns(df, frozenset({"a_second"}))
        assert list(result.columns) == ["z_first", "m_third"]


# ─── 邊界 ──────────────────────────────────────────────────────


class TestEdgeCases:
    def test_empty_dataframe(self) -> None:
        dead, diag = find_dead_columns(pd.DataFrame(), min_valid_samples=100)
        assert dead == frozenset()
        assert diag.total_dropped == 0

    def test_single_column_valid(self) -> None:
        df = pd.DataFrame({"a": np.random.randn(1000)})
        dead, _ = find_dead_columns(df, min_valid_samples=100)
        assert dead == frozenset()

    def test_single_column_dead(self) -> None:
        df = pd.DataFrame({"a": [0.0] * 1000})
        dead, _ = find_dead_columns(df, min_valid_samples=100)
        assert dead == frozenset({"a"})

    def test_drop_with_empty_set_returns_df(self) -> None:
        df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        result = drop_dead_columns(df, frozenset())
        assert list(result.columns) == ["a", "b"]

    def test_drop_with_nonexistent_columns_is_idempotent(self) -> None:
        df = pd.DataFrame({"a": [1, 2, 3]})
        result = drop_dead_columns(df, frozenset({"not_in_df", "also_not"}))
        assert list(result.columns) == ["a"]
        assert len(result) == 3

    def test_drop_idempotent(self) -> None:
        df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        dead = frozenset({"a"})
        once = drop_dead_columns(df, dead)
        twice = drop_dead_columns(once, dead)
        assert list(twice.columns) == list(once.columns)
        assert (twice == once).all().all()

    def test_all_columns_dead(self) -> None:
        df = pd.DataFrame({"a": [0.0] * 100, "b": [np.nan] * 100})
        dead, _ = find_dead_columns(df, min_valid_samples=100)
        result = drop_dead_columns(df, dead)
        assert len(result.columns) == 0
        assert len(result) == 100  # row 數保留

    def test_numeric_and_object_dtypes(self) -> None:
        # 混合 dtype 不應 raise
        df = pd.DataFrame({
            "num": np.random.randn(1000),
            "obj": ["x"] * 1000,
        })
        dead, diag = find_dead_columns(df, min_valid_samples=100)
        assert "obj" in diag.constant_cols  # nunique=1


# ─── 效能 baseline ────────────────────────────────────────────


class TestDeadColumnMask:
    """numpy-level dead_column_mask（CGSA streaming write 用）。"""

    def test_constant_column(self) -> None:
        arr = np.column_stack([
            np.full(1000, 42.0),          # constant → dead
            np.random.randn(1000),         # ok
        ])
        mask = dead_column_mask(arr, min_valid_samples=100)
        assert mask.tolist() == [True, False]

    def test_all_nan_column(self) -> None:
        arr = np.column_stack([
            np.full(1000, np.nan),         # all-NaN → dead
            np.random.randn(1000),
        ])
        mask = dead_column_mask(arr, min_valid_samples=100)
        assert mask.tolist() == [True, False]

    def test_sparse_50_of_20000(self) -> None:
        col = np.full(20000, np.nan)
        col[:50] = np.arange(50)
        arr = np.column_stack([col, np.random.randn(20000)])
        mask = dead_column_mask(arr, min_valid_samples=100)
        assert mask.tolist() == [True, False]

    def test_150_valid_kept(self) -> None:
        col = np.full(20000, np.nan)
        col[:150] = np.arange(150)
        arr = col.reshape(-1, 1)
        mask = dead_column_mask(arr, min_valid_samples=100)
        assert mask.tolist() == [False]

    def test_boundary_exactly_min_valid(self) -> None:
        col = np.full(1000, np.nan)
        col[:100] = np.arange(100)
        arr = col.reshape(-1, 1)
        mask = dead_column_mask(arr, min_valid_samples=100)
        assert mask.tolist() == [False]  # `<` 非 `<=`

    def test_high_nan_ratio_but_enough_valid_kept(self) -> None:
        # 60% NaN 但 valid >= min 且多 distinct → 保留（不以 NaN ratio）
        rows = 20000
        col = np.random.randn(rows)
        nan_idx = np.random.choice(rows, int(rows * 0.6), replace=False)
        col[nan_idx] = np.nan
        arr = col.reshape(-1, 1)
        mask = dead_column_mask(arr, min_valid_samples=100)
        assert mask.tolist() == [False]

    def test_empty_array(self) -> None:
        assert dead_column_mask(np.empty((10, 0)), min_valid_samples=100).tolist() == []
        assert dead_column_mask(np.empty((0, 0)), min_valid_samples=100).tolist() == []

    def test_inf_not_misjudged_constant(self) -> None:
        # 含 inf 但非常數 → nanmin < nanmax 成立 → 不誤判 dead
        col = np.random.randn(1000)
        col[5] = np.inf
        arr = col.reshape(-1, 1)
        mask = dead_column_mask(arr, min_valid_samples=100)
        assert mask.tolist() == [False]

    def test_never_kills_good_features(self) -> None:
        # I-5: 100 個明顯有效欄 → 0 dead
        arr = np.random.randn(5000, 100)
        mask = dead_column_mask(arr, min_valid_samples=100)
        assert mask.sum() == 0

    def test_does_not_mutate_input(self) -> None:
        arr = np.random.randn(1000, 5)
        snapshot = arr.copy()
        dead_column_mask(arr, min_valid_samples=100)
        assert np.array_equal(arr, snapshot, equal_nan=True)


class TestSharedStandardContract:
    """dead_column_mask（numpy）與 find_dead_columns（DataFrame）標準一致。"""

    def test_same_verdict_on_random_matrix(self) -> None:
        np.random.seed(7)
        for _ in range(30):
            rows = np.random.randint(200, 2000)
            n_cols = np.random.randint(2, 25)
            data = np.random.randn(rows, n_cols)
            # 隨機注入 constant / sparse / 正常
            for j in range(n_cols):
                r = np.random.rand()
                if r < 0.2:
                    data[:, j] = 42.0  # constant
                elif r < 0.4:
                    keep = np.random.randint(0, 100)  # sparse (<100)
                    data[keep:, j] = np.nan
            cols = [f"c{j}" for j in range(n_cols)]
            df = pd.DataFrame(data, columns=cols)

            np_mask = dead_column_mask(data, min_valid_samples=100)
            np_dead = {cols[j] for j in range(n_cols) if np_mask[j]}

            df_dead, _ = find_dead_columns(df, min_valid_samples=100)

            assert np_dead == set(df_dead), (
                f"numpy mask 與 DataFrame find_dead_columns 標準不一致: "
                f"np={np_dead} df={set(df_dead)}"
            )


class TestPerformance:
    def test_10k_cols_20k_rows_under_10_seconds(self) -> None:
        # Baseline 對 442K 特徵 × 20K row 估算：~5s × (442/10) ≈ ~220s 一次完整 dead drop
        # 此測試只是基準保護避免演算法退化（per-column Python loop 會花數百秒）
        # threshold 10s 容忍 CI 環境變化（macOS / Linux / 不同負載下 5-7s 屬正常）
        np.random.seed(42)
        n_rows = 20_000
        n_cols = 10_000
        data = np.random.randn(n_rows, n_cols)
        mask = np.random.rand(n_rows, n_cols) < 0.5
        data[mask] = np.nan
        df = pd.DataFrame(data, columns=[f"col_{i}" for i in range(n_cols)])
        t0 = time.perf_counter()
        dead, _ = find_dead_columns(df, min_valid_samples=100)
        elapsed = time.perf_counter() - t0
        assert elapsed < 10.0, f"Performance regression: took {elapsed:.2f}s for 10K×20K"
        assert isinstance(dead, frozenset)
