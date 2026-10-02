"""FFSTAT SPEC v60 Task 4.2：截斷 MR 負控制之捕獲邊界（秒級、不生成、無 K 線）。

`ff_truncation_mr_helpers._expect_causal_gate_failure` 以 traceback 之 gate 函式名判定「由哪個 gate 拋出」。
本檔以**真實 gate 函式**對小 parquet 製造各 gate 之失敗，驗：因果 gate（欄集合、主值、fracdiff atol 值、warmup NaN mask、
metadata）之失敗被收；經抽樣層覆蓋守衛之失敗、訊息為覆蓋守衛者被拒；尾擾動 fracdiff 控制（只收欄集合／d*）拒收值 gate。
（審查 r2：改前以訊息前綴判定，warmup／numpy atol／裸 assert 之真實訊息被誤拒。）
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from tests.feature_engineering import ff_truncation_mr_helpers as h


def _pair(tmp_path: Path, full_cols: dict, trunc_cols: dict, *, full_meta=None, trunc_meta=None) -> h.TruncationPair:
    full_dir, trunc_dir = tmp_path / "full", tmp_path / "trunc"
    full_dir.mkdir()
    trunc_dir.mkdir()
    pd.DataFrame(full_cols).to_parquet(full_dir / "1h_L1_trend_EMA_5_L65.parquet")
    pd.DataFrame(trunc_cols).to_parquet(trunc_dir / "1h_L1_trend_EMA_5_L65.parquet")
    n = len(next(iter(trunc_cols.values())))
    return h.TruncationPair(
        warmup=1, n_trunc=n,
        full=h.GenerationArtifacts(full_dir, tmp_path / "rf", full_meta or {"symbol": "A", "timeframe": "1h"},
                                   {"row_count": n + 1}, n + 1),
        trunc=h.GenerationArtifacts(trunc_dir, tmp_path / "rt", trunc_meta or {"symbol": "A", "timeframe": "1h"},
                                    {"row_count": n}, n),
    )


@pytest.fixture(autouse=True)
def _skip_preparation(monkeypatch: pytest.MonkeyPatch) -> None:
    """準備證據（真實生成產物之抽樣層覆蓋）於本檔之小 parquet 不適用；本檔只驗捕獲邊界本身。"""
    monkeypatch.setattr(h, "_assert_mr_preparation", lambda pair, **kwargs: None)


def test_fracdiff_atol_values_gate_failure_is_accepted(tmp_path: Path) -> None:
    pair = _pair(tmp_path, {"close_fracdiff": np.array([0.0, 1.0, 2.0, 9.0], np.float32)},
                 {"close_fracdiff": np.array([0.0, 1.0, 3.0], np.float32)})
    check = lambda: h._assert_values_gate(pair.full.raw_dir, pair.trunc.raw_dir, warmup=1, n_trunc=3, atol=1e-8,
                                          column_filter=h._is_fracdiff_column)  # noqa: E731
    got = h._expect_causal_gate_failure(pair, check)
    assert got.startswith("_assert_values_gate:")


def test_warmup_nan_mask_failure_is_accepted(tmp_path: Path) -> None:
    pair = _pair(tmp_path, {"close_fracdiff": np.array([0.0, 1.0, 2.0, 9.0], np.float32)},
                 {"close_fracdiff": np.array([np.nan, 1.0, 2.0], np.float32)})
    check = lambda: h._assert_warmup_nan_masks_equal(pair.full.raw_dir, pair.trunc.raw_dir, warmup=1,  # noqa: E731
                                                     n_trunc=3)
    got = h._expect_causal_gate_failure(pair, check)
    assert got.startswith("_assert_warmup_nan_masks_equal:")


def test_metadata_gate_failure_is_accepted(tmp_path: Path) -> None:
    pair = _pair(tmp_path, {"x": np.zeros(4, np.float32)}, {"x": np.zeros(3, np.float32)},
                 full_meta={"symbol": "A", "timeframe": "1h"}, trunc_meta={"symbol": "B", "timeframe": "1h"})
    got = h._expect_causal_gate_failure(pair, lambda: h._assert_metadata_gate(pair.full, pair.trunc))
    assert got.startswith("_assert_metadata_gate:")


def test_columns_gate_failure_is_accepted(tmp_path: Path) -> None:
    pair = _pair(tmp_path, {"a_fracdiff": np.zeros(4, np.float32)}, {"b_fracdiff": np.zeros(3, np.float32)})
    check = lambda: h._assert_columns_gate(pair.full.raw_dir, pair.trunc.raw_dir, strict=True)  # noqa: E731
    got = h._expect_causal_gate_failure(pair, check, allowed_gates=h._FRACDIFF_PRE_VALUES_GATES)
    assert got.startswith("_assert_columns_gate:")


def test_layer_coverage_failure_is_rejected(tmp_path: Path) -> None:
    pair = _pair(tmp_path, {"x": np.zeros(4, np.float32)}, {"x": np.zeros(3, np.float32)})

    def check() -> None:
        def _assert_values_gate_main() -> None:  # 同名內層：模擬經主值 gate 進入覆蓋守衛之路徑
            h._assert_mutation_layer_coverage(["close_trend_EMA_5"], {"close_trend_EMA_5": ("1h_L1.parquet", "L1")})
        _assert_values_gate_main()

    with pytest.raises(AssertionError, match="抽樣覆蓋守衛"):
        h._expect_causal_gate_failure(pair, check)


def test_coverage_guard_message_is_rejected(tmp_path: Path) -> None:
    pair = _pair(tmp_path, {"x": np.zeros(4, np.float32)}, {"x": np.zeros(3, np.float32)})

    def check() -> None:
        def _assert_values_gate_main() -> None:
            raise AssertionError("coverage guard failed: 10% < 95%")
        _assert_values_gate_main()

    with pytest.raises(AssertionError, match="非因果 gate"):
        h._expect_causal_gate_failure(pair, check)


def test_fracdiff_tail_control_rejects_values_gate(tmp_path: Path) -> None:
    pair = _pair(tmp_path, {"close_fracdiff": np.array([0.0, 1.0, 2.0, 9.0], np.float32)},
                 {"close_fracdiff": np.array([0.0, 1.0, 3.0], np.float32)})
    check = lambda: h._assert_values_gate(pair.full.raw_dir, pair.trunc.raw_dir, warmup=1, n_trunc=3, atol=1e-8,
                                          column_filter=h._is_fracdiff_column)  # noqa: E731
    with pytest.raises(AssertionError, match="不由允許之 gate"):
        h._expect_causal_gate_failure(pair, check, allowed_gates=h._FRACDIFF_PRE_VALUES_GATES)


def test_non_gate_assertion_is_rejected(tmp_path: Path) -> None:
    pair = _pair(tmp_path, {"x": np.zeros(4, np.float32)}, {"x": np.zeros(3, np.float32)})

    def check() -> None:
        raise AssertionError("values something")  # 訊息像值 gate，但非由 gate 函式拋出

    with pytest.raises(AssertionError, match="不由允許之 gate"):
        h._expect_causal_gate_failure(pair, check)


def test_pre_start_rows_selects_only_before_start() -> None:
    idx = pd.date_range("2025-12-01", periods=10, freq="h", tz="UTC")
    df = pd.DataFrame({"close": np.arange(10.0), "timestamp": idx.asi8 // 10**9})
    assert list(h._pre_start_rows(df, "2025-12-01 05:00:00", 100)) == [0, 1, 2, 3, 4]
    out = h._patch_kline_pre_start_ohlcv(df, start_iso="2025-12-01 05:00:00", bars=100, delta=1e6)
    assert (out["close"].to_numpy()[5:] == df["close"].to_numpy()[5:]).all()
    assert (out["close"].to_numpy()[:5] != df["close"].to_numpy()[:5]).all()


def _mask_pair(tmp_path: Path, full_vals: np.ndarray, trunc_vals: np.ndarray) -> h.TruncationPair:
    return _pair(tmp_path, {"close_trend_EMA_5_Mean_W13": full_vals.astype(np.float32)},
                 {"close_trend_EMA_5_Mean_W13": trunc_vals.astype(np.float32)})


@pytest.mark.parametrize("direction", ["trunc_tail_nan", "full_tail_nan"])
def test_main_values_gate_rejects_mask_only_asymmetry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                                     direction: str) -> None:
    """v61：比較窗內 NaN mask 不對稱（低 fill_rate 亦然）必為主值 gate 之因果失敗（改前只印 informational ⇒ L3 置中窗洩漏存活）。"""
    base = np.arange(21.0)
    tail = np.r_[np.arange(14.0), [np.nan] * 6]
    full, trunc = (np.r_[base[:20], 99.0], tail) if direction == "trunc_tail_nan" else (np.r_[tail, 99.0], base[:20])
    pair = _mask_pair(tmp_path, full, trunc)
    monkeypatch.setattr(h, "_assert_mutation_layer_coverage", lambda *a, **k: None)
    check = lambda: h._assert_values_gate_main(pair.full.raw_dir, pair.trunc.raw_dir, warmup=0, n_trunc=20)  # noqa: E731
    got = h._expect_causal_gate_failure(pair, check)
    assert got.startswith("_assert_values_gate_main:") and "NaN mask mismatch" in got


def test_main_values_gate_accepts_equal_sparse_mask(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """兩側缺在同位置之稀疏欄（fill 50%）照常通過（v61 不誤殺）。"""
    sparse = np.where(np.arange(21) % 2, np.nan, np.arange(21.0))
    pair = _mask_pair(tmp_path, sparse, sparse[:20])
    monkeypatch.setattr(h, "_assert_mutation_layer_coverage", lambda *a, **k: None)
    monkeypatch.setattr(h, "COVERAGE_COLUMN_FRACTION", 0.0)
    h._assert_values_gate_main(pair.full.raw_dir, pair.trunc.raw_dir, warmup=0, n_trunc=20)
