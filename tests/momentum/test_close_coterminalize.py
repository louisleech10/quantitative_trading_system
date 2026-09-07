"""EVTALIGN Task 1.1（B）：label 生成前把 close 裁到 feature 尾——守衛一字不改。

SPEC：`docs/GAP3_EVENT_ALIGNMENT_SPEC.md` Task 1.1　TODO：Task 1.1

逐條對應 TODO Task 1.1 驗證：
- 截短案例之 label 與同尾案例 **逐值 ==**（NaN 位置與數值皆同）→ `test_stage2_truncated_*`
- `inspect.getsource(validate_alignment)` 之 sha256 與改前相同 → `test_guard_untouched_*`
- spy：stage0 與 stage2 各恰呼叫 `_coterminalize_close` 一次 → `test_both_call_sites_*`
- 切分 golden（purge／embargo／split_row_fingerprint／retained_event_ids）逐值 == → `test_split_golden_*`

mutation（`handoffs/20260907-evtalign-mutate.py --phase 1`）：B1 helper no-op ⇒ truncated 紅；
B2 只接 stage2 ⇒ both_call_sites 紅；B3 動守衛 ⇒ guard_untouched 紅；C0 只改註解 ⇒ 全綠（對照組）。
"""

from __future__ import annotations

import hashlib
import inspect
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from momentum.Analysis import ic_filter_orchestrator as orch_mod
from momentum.Analysis.ic_config_schema import load_ic_config
from momentum.Analysis.ic_filter_orchestrator import (
    ICFilterOrchestrator,
    _coterminalize_close,
    _resolve_effective_label_horizon,
)
from momentum.core.contracts import AlignmentViolationError, validate_alignment

REPO = Path(__file__).resolve().parents[2]

#: 改前（commit 097dae40 之 HEAD）`inspect.getsource(validate_alignment)` 之 sha256。
#: 守衛任一字改動（含註解）⇒ 本值變 ⇒ 紅。B 之全部承諾建立在「守衛沒動」上。
GUARD_SHA256 = "9c8aeb6911516f8959aad3959f501bc998788fa460b26a61e94772ed3cc6f187"

BASE_S = 1_704_067_200
STEP_S = 43_200  # 12h
N_FEAT = 157      # _validate_input 要求 ≥ 100 列
N_CLOSE = 200     # 截短：feature 之後 K 線還多 43 根（使用者：「K線比特徵多也很合理吧」）
_CLOSE_FULL = np.linspace(100.0, 200.0, N_CLOSE)


class _Reader:
    """前 n 根 close；n=N_CLOSE 為截短情形、n=N_FEAT 為同尾情形，兩者前 N_FEAT 值逐位元組相同。"""

    def __init__(self, n: int):
        self.n = n

    def read_klines(self, _symbol, _timeframe):
        index = pd.Index(BASE_S + np.arange(self.n, dtype=np.int64) * STEP_S, name="timestamp")
        return pd.DataFrame({"close": _CLOSE_FULL[: self.n]}, index=index)


def _features() -> pd.DataFrame:
    index = pd.Index(BASE_S + np.arange(N_FEAT, dtype=np.int64) * STEP_S, name="timestamp")
    return pd.DataFrame({"f1": np.arange(N_FEAT, dtype=np.float64)}, index=index)


_META = {"symbol": "BTCUSDT", "timeframe": "12h", "f1": {"name": "f1", "category": "trend", "layer": 1}}


def test_helper_truncated_reduces_to_coterminal_and_empty_feature_index_raises():
    idx = pd.date_range("2024-01-01", periods=100, freq="1h")
    close = pd.Series(np.arange(100, dtype=float), index=idx)
    feat = idx[:57]
    trimmed = _coterminalize_close(close, feat)
    assert trimmed.index.equals(feat) and np.array_equal(trimmed.to_numpy(), close.to_numpy()[:57])
    # K 線尾早於 feature 尾 ⇒ no-op（交守衛照舊判定；本票不改該情形）
    assert _coterminalize_close(close.iloc[:30], feat).equals(close.iloc[:30])
    with pytest.raises(AlignmentViolationError, match="feature_index is empty"):
        _coterminalize_close(close, idx[:0])


def test_stage2_truncated_labels_equal_coterminal_labels_and_tail_nan_eq_lag():
    config = load_ic_config()
    horizon = int(_resolve_effective_label_horizon(config, None))
    orchestrator = ICFilterOrchestrator(config)

    label_trunc, df_trunc = orchestrator._stage2_label_generation(
        None, _META, config, _Reader(N_CLOSE), features_df=_features()
    )
    label_coterm, df_coterm = orchestrator._stage2_label_generation(
        None, _META, config, _Reader(N_FEAT), features_df=_features()
    )
    assert len(label_trunc) == N_FEAT and label_trunc.index.equals(label_coterm.index)
    # 逐值 ==（NaN 位置與數值皆同）：截短被**化約**為同尾，不引入任何新數值
    assert np.array_equal(label_trunc.to_numpy(), label_coterm.to_numpy(), equal_nan=True)
    assert np.array_equal(df_trunc.to_numpy(), df_coterm.to_numpy(), equal_nan=True)
    assert int(label_trunc.isna().iloc[-horizon:].sum()) == horizon
    assert not label_trunc.isna().iloc[:-horizon].any()


def test_both_call_sites_invoke_coterminalize_exactly_once(monkeypatch):
    calls: list[str] = []
    real = _coterminalize_close

    def spy(close, feature_index):
        calls.append("call")
        return real(close, feature_index)

    monkeypatch.setattr(orch_mod, "_coterminalize_close", spy)
    config = load_ic_config()
    orchestrator = ICFilterOrchestrator(config)

    # stage2（生成路徑）
    _, labels_df = orchestrator._stage2_label_generation(
        None, _META, config, _Reader(N_CLOSE), features_df=_features()
    )
    assert len(calls) == 1, "stage2 must derive the trim exactly once"

    # stage0（預載 labels 路徑；oracle close 同一支 helper、同一位置語意）
    calls.clear()
    preloaded = labels_df.copy()
    preloaded.index = pd.Index(BASE_S + np.arange(N_FEAT, dtype=np.int64) * STEP_S, name="timestamp")
    monkeypatch.setattr(orchestrator, "_load_features_hdf5", lambda _p: (_features(), {}))
    monkeypatch.setattr(orchestrator, "_load_labels_hdf5", lambda _p: preloaded)
    monkeypatch.setattr(orchestrator, "_load_meta_json", lambda _p: dict(_META))
    features_df, labels_out, _, stage0_log = orchestrator._stage0_ingestion(
        "features.h5", "labels.h5", "meta.json", config=config, kline_reader=_Reader(N_CLOSE)
    )
    assert len(calls) == 1, "stage0 must derive the trim exactly once (not trust a parameter)"
    assert len(features_df) == N_FEAT and labels_out is not None and "alignment_report" in stage0_log


def test_guard_untouched_sha256_pinned():
    src = inspect.getsource(validate_alignment)
    assert hashlib.sha256(src.encode("utf-8")).hexdigest() == GUARD_SHA256, (
        "validate_alignment 被改動——Task 1.1 之前提「守衛一字不改」失效；"
        "若改動有裁決，須同步更新 SPEC/TODO 並重釘本值"
    )


def test_split_golden_unchanged_after_trim():
    """`_build_holdout_split_plan` 不吃 close ⇒ 切分 golden（purge／embargo／fingerprint／event ids）逐值不變。"""
    probe = REPO / "handoffs" / "20260907-probe-split-baseline.py"
    golden = REPO / "tests" / "golden" / "evtalign" / "split_baseline.json"
    assert probe.is_file() and golden.is_file()
    proc = subprocess.run([sys.executable, str(probe)], cwd=str(REPO), capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout[-2000:] + proc.stderr[-2000:]
    assert "與既有 golden 相同？ **True**" in proc.stdout
