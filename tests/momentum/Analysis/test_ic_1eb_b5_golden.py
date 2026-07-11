"""IC 1e+1b B5 Golden 三腿：G-1 不變 / G-3 fail-closed（G-2 由腳本產 diff）。

G-1：handoffs/ic1eb_baseline 預物化 inputs 重放新路徑，非顯著性五 hash +
feature order + series hash 相等。
G-3：樣本不足 / 全 NaN / std=0 → p=NaN → stage5 p 閘 fail；SelectionScope 違約 raise；
xsec labels 單軸仍 raise（比對 baseline expected_raise_runs；缺件 fail-closed）。
"""

from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from momentum.Analysis.ic_config_schema import load_ic_config  # noqa: E402
from momentum.Analysis.ic_filter_orchestrator import ICFilterOrchestrator  # noqa: E402
from momentum.Analysis.statistical_validator import compute_hac_ic_statistics  # noqa: E402
from momentum.core.contracts import SelectionScope  # noqa: E402
from scripts.ic1eb_b5_replay import (  # noqa: E402
    BASELINE_DIR,
    FAST_RUN,
    SLOW_RUNS,
    assert_g1_invariant,
    load_manifest,
    patch_persist_outputs,
    replay_run,
    run_xsec_labels_raise,
    verify_inputs_integrity,
)

pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")


def _baseline_available() -> bool:
    return (BASELINE_DIR / "baseline_manifest.json").is_file()


@pytest.fixture(scope="module")
def baseline_manifest():
    if not _baseline_available():
        pytest.skip("ic1eb baseline absent (skip-if-absent)")
    patch_persist_outputs()
    manifest = load_manifest()
    verify_inputs_integrity(manifest)
    return manifest


def _run_names(manifest: dict) -> list[str]:
    return sorted((manifest.get("runs") or {}).keys())


# ── G-1 ──────────────────────────────────────────────────────────────────────


def test_g1_fast_btc_12h_f754_invariant(baseline_manifest) -> None:
    """G-1 快顆：long_BTCUSDT_12h_f754aad4（不掛 slow_stat，PR 常跑）。"""
    entry = baseline_manifest["runs"][FAST_RUN]
    result = replay_run(baseline_manifest, FAST_RUN)
    assert_g1_invariant(entry, result)


@pytest.mark.slow_stat
@pytest.mark.parametrize(
    "run_name",
    sorted(SLOW_RUNS),
)
def test_g1_slow_runs_invariant(baseline_manifest, run_name: str) -> None:
    """G-1 其餘 12 顆（含 1h/full/event/xsec），掛 slow_stat。"""
    if run_name not in baseline_manifest["runs"]:
        pytest.skip(f"run missing in manifest: {run_name}")
    entry = baseline_manifest["runs"][run_name]
    result = replay_run(baseline_manifest, run_name)
    assert_g1_invariant(entry, result)


def test_g1_manifest_covers_13_runs(baseline_manifest) -> None:
    names = _run_names(baseline_manifest)
    assert len(names) == 13
    assert FAST_RUN in names
    assert SLOW_RUNS.issubset(set(names))
    assert set(names) == {FAST_RUN} | SLOW_RUNS


# ── G-3 ──────────────────────────────────────────────────────────────────────


def _assert_nan_p_fails_stage5_gate(feature_name: str, p_value: float) -> None:
    """kernel 產出 NaN p → _passes_threshold False → _apply_thresholds 以 p 閘剔除。

    其他門檻給通過值，確保 removed 歸因於 p_value（G-3 / F3）。
    """
    assert math.isnan(float(p_value)), f"{feature_name}: expected NaN p, got {p_value!r}"
    # None/NaN → False（含 inverse p 閘）
    assert ICFilterOrchestrator._passes_threshold(None, 0.05, inverse=True) is False
    assert (
        ICFilterOrchestrator._passes_threshold(float(p_value), 0.05, inverse=True)
        is False
    )

    config = load_ic_config()
    orch = ICFilterOrchestrator(config)
    summary: list[dict[str, Any]] = [
        {
            "feature_name": feature_name,
            "ic_mean": 0.5,
            "icir": 2.0,
            "p_value": float(p_value),
            "p_value_adj": float(p_value),
            "ic_hit_rate": 0.9,
            "monotonicity_score": 0.9,
            "coverage": 0.9,
        }
    ]
    passed, threshold_log = orch._apply_thresholds(
        summary,
        config.thresholds,
        alpha_effective=0.05,
        fdr_enabled=True,
    )
    assert feature_name not in passed
    removed_p = threshold_log["removed_features"]["p_value"]
    assert feature_name in removed_p, (
        f"{feature_name}: NaN p must be removed by stage5 p gate, log={threshold_log}"
    )


def test_g3_sample_insufficient_p_nan_gate() -> None:
    """n_valid < max(8, 2L) → p=NaN → stage5 p 閘 fail（fail-closed）。"""
    # n=5, h=1 → auto_bw≈2, L=2 → max(8,4)=8 > 5 → fail-closed
    n = 5
    rng = np.random.default_rng(0)
    idx = pd.RangeIndex(n)
    features = pd.DataFrame({"f": rng.normal(size=n)}, index=idx)
    label = pd.Series(rng.normal(size=n), index=idx, name="y")
    out = compute_hac_ic_statistics(features, label, horizon=1)
    assert "f" in out
    p_nan = float(out["f"]["p_value"])
    assert math.isnan(p_nan)
    # kernel NaN → stage5 p 閘整合（樣本不足）
    _assert_nan_p_fails_stage5_gate("f", p_nan)


def test_g3_all_nan_and_std0_p_nan() -> None:
    """全 NaN / std=0 → p=NaN → stage5 p 閘 fail。"""
    n = 40
    idx = pd.RangeIndex(n)
    label = pd.Series(np.linspace(-1, 1, n), index=idx)
    features = pd.DataFrame(
        {
            "all_nan": np.full(n, np.nan),
            "const": np.ones(n),
        },
        index=idx,
    )
    out = compute_hac_ic_statistics(features, label, horizon=1)
    p_all_nan = float(out["all_nan"]["p_value"])
    p_const = float(out["const"]["p_value"])
    assert math.isnan(p_all_nan)
    assert math.isnan(p_const)
    # 兩種 kernel NaN 皆接到 stage5 閘
    _assert_nan_p_fails_stage5_gate("all_nan", p_all_nan)
    _assert_nan_p_fails_stage5_gate("const", p_const)


def test_g3_selection_scope_contract_raise() -> None:
    """SelectionScope n_tests 違約 → ValueError。"""
    with pytest.raises(ValueError, match="n_tests"):
        SelectionScope(
            scope_id="g3",
            universe_features=["a", "b"],
            split_label="test",
            evaluated_features=["a"],
            n_tests=2,
            method="fdr_bh",
            base_universe_hash="x",
        )
    with pytest.raises(ValueError, match="subset"):
        SelectionScope(
            scope_id="g3b",
            universe_features=["a"],
            split_label="test",
            evaluated_features=["a", "b"],
            n_tests=2,
            method="fdr_bh",
            base_universe_hash="x",
        )


def test_g3_xsec_labels_path_still_raises(baseline_manifest) -> None:
    """xsec labels_path 單軸仍 raise；exception_type 對齊 baseline receipt。

    expected_raise receipt 缺件 → fail（fail-closed），禁止 skip。
    """
    expected = (baseline_manifest.get("expected_raise_runs") or {}).get(
        "xsec_labels_return5_12h"
    )
    if not expected:
        pytest.fail(
            "expected_raise_runs.xsec_labels_return5_12h missing "
            "(fail-closed: baseline artifact required)"
        )
    exc = run_xsec_labels_raise(baseline_manifest)
    assert type(exc).__name__ == expected["exception_type"]
