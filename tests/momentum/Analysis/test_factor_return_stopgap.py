"""IC1C-FR-STOPGAP Phase 1: default-off 三態 + factory consumer allowlist + mutation probes.

SPEC/TODO: docs/IC1CFR_STOPGAP_{SPEC,TODO}.md Task 1.1 / 1.3 / §V M1/M1b.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest

from momentum.Analysis.factor_return_sanitizer import has_finite_numeric_leaf
from momentum.Analysis.ic_config_schema import ICConfig
from momentum.Analysis.ic_filter_orchestrator import ICFilterOrchestrator

REPO_ROOT = Path(__file__).resolve().parents[3]
FACTORY_ALLOWLIST_PATH = (
    REPO_ROOT / "handoffs" / "ic1cfr_stopgap_baseline" / "factory_allowlist.txt"
)


def _build_orchestrator(*, preset: str = "intermediate") -> ICFilterOrchestrator:
    raw = ICConfig().model_dump(by_alias=True)
    raw["feature_tiers"]["active_preset"] = preset
    config = ICConfig.model_validate(raw)
    orch = ICFilterOrchestrator(config)

    n = 120
    index = pd.date_range("2024-01-01", periods=n, freq="12h")
    rng = np.random.default_rng(7)
    features = pd.DataFrame(
        {
            "feat_a": rng.normal(size=n),
            "feat_b": rng.normal(size=n),
        },
        index=index,
        dtype=float,
    )
    labels = pd.Series(
        0.02 * features["feat_a"] + rng.normal(scale=0.01, size=n),
        index=index,
        name="future_return",
        dtype=float,
    )
    orch._ic_cache = {
        "features_df": features,
        "label_series": labels,
        "metadata": {},
        "icir": {name: {"icir": 0.1, "ic_mean": 0.02} for name in features.columns},
        "rolling_ic": {
            name: {"30": (0.01 * features[name].rolling(10, min_periods=1).mean()).tolist()}
            for name in features.columns
        },
        "ic_decay": {},
        "grouped_ic": {},
        "event_info": {},
        "stage0_log": {},
        "preproc_log": {},
    }
    orch._monotonicity_cache = {name: {} for name in features.columns}
    orch._filtered_features_df = features.copy()
    orch._report = {
        "summary_table": [
            {"feature_name": "feat_a", "ic_mean": 0.04},
            {"feature_name": "feat_b", "ic_mean": 0.02},
        ],
        "turnover_analysis": {
            "feat_a": {"quantile_turnover": 0.2},
            "feat_b": {"quantile_turnover": 0.3},
        },
    }
    return orch


def _assert_union_unavailable(body: Any) -> None:
    assert isinstance(body, dict)
    assert body.get("status") == "unavailable"
    assert body.get("value") is None
    reason = str(body.get("reason") or "")
    assert "legacy_misaligned_factor_return_shape" in reason or (
        "ls_returns_timestamp_misaligned" in reason
    )
    assert not has_finite_numeric_leaf(body)


def _assert_union_ok(body: Any) -> None:
    assert isinstance(body, dict)
    assert body.get("status") == "ok"
    assert body.get("reason") is None
    value = body.get("value") or {}
    assert isinstance(value, dict)
    assert value.get("schema_version") == "fr_full_v1"
    assert "ls_returns_timestamp_misaligned" not in str(body.get("reason"))


# ---------------------------------------------------------------------------
# Task 1.1 — default-off 三態
# ---------------------------------------------------------------------------


def test_default_off_not_run() -> None:
    """預設 request → summary not_run + 無 results 節。"""
    orch = _build_orchestrator()
    report = orch.run_deep_analysis()
    assert report.module_summary.get("factor_returns") == "not_run"
    assert "factor_returns" not in report.results


@pytest.mark.parametrize("preset", ["intermediate", "advanced"])
def test_pure_tier_not_run(preset: str) -> None:
    """純 tier(無 force/override)→ not_run;證 tier 排除 factor_return 強制。"""
    orch = _build_orchestrator(preset=preset)
    applied = orch._apply_tier_config(orch._config)
    assert applied.factor_return.enabled is False
    report = orch.run_deep_analysis()
    assert report.module_summary.get("factor_returns") == "not_run"
    assert "factor_returns" not in report.results


def test_explicit_enable_completed() -> None:
    """F2: force + override 兩路徑 → §U ok + summary completed + 不入 errors。"""
    # path A: force_modules
    orch_force = _build_orchestrator()
    report_force = orch_force.run_deep_analysis(force_modules=["factor_returns"])
    assert report_force.module_summary.get("factor_returns") == "completed"
    _assert_union_ok(report_force.results.get("factor_returns"))
    assert "factor_returns" not in [e.module_name for e in report_force.deep_analysis_errors]

    # path B: config_override modules enabled=true
    orch_ov = _build_orchestrator()
    report_ov = orch_ov.run_deep_analysis(
        config_override={"factor_return": {"enabled": True}},
    )
    assert report_ov.module_summary.get("factor_returns") == "completed"
    _assert_union_ok(report_ov.results.get("factor_returns"))
    assert "factor_returns" not in [e.module_name for e in report_ov.deep_analysis_errors]


def test_deep_off_not_run() -> None:
    """deep 全域關 → force 亦 not_run(force 不跨 :1601 早退)。"""
    orch = _build_orchestrator(preset="foundation")
    report = orch.run_deep_analysis(force_modules=["factor_returns"])
    assert report.module_summary.get("factor_returns") == "not_run"
    assert "factor_returns" not in report.results


def test_runner_returns_ok_union_internal() -> None:
    """F1.1+F2: runner 真計算回 §U ok union;出口 sanitizer 放行 ok。"""
    orch = _build_orchestrator()
    # test-config: 降 min_samples 使 120-bar fixture 可過 production 預設 30 門檻即可
    result = orch._run_factor_return(["feat_a"], orch._config)
    assert isinstance(result, dict)
    assert result.get("status") == "ok"
    assert (result.get("value") or {}).get("schema_version") == "fr_full_v1"
    assert "feat_a" in orch._factor_return_series
    assert isinstance(orch._factor_return_series["feat_a"].ls_return, pd.Series)


# ---------------------------------------------------------------------------
# Task 1.3 — factory / direct consumer allowlist
# ---------------------------------------------------------------------------


def _load_frozen_allowlist(path: Path) -> dict[str, set[str]]:
    factory_callers: set[str] = set()
    direct_consumers: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("factory_caller|"):
            factory_callers.add(line.split("|", 1)[1])
        elif line.startswith("direct_consumer|"):
            direct_consumers.add(line.split("|", 1)[1])
    return {"factory_callers": factory_callers, "direct_consumers": direct_consumers}


def test_factor_return_consumer_allowlist() -> None:
    """現況 AST scan ⊆ B0 凍結 allowlist;scanner 與 freeze 腳本共用。"""
    assert FACTORY_ALLOWLIST_PATH.is_file(), f"missing {FACTORY_ALLOWLIST_PATH}"
    frozen = _load_frozen_allowlist(FACTORY_ALLOWLIST_PATH)

    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    from ic1cfr_stopgap_freeze import (  # type: ignore[import-not-found]
        compare_consumer_allowlist,
        scan_factor_return_consumers_ast,
    )

    norm = scan_factor_return_consumers_ast()
    extra_callers, extra_direct = compare_consumer_allowlist(norm, frozen)
    assert not extra_callers, f"new factory callers outside allowlist: {extra_callers}"
    assert not extra_direct, f"new direct consumers outside allowlist: {extra_direct}"


def test_consumer_guard_catches_import_alias(tmp_path: Path) -> None:
    """自證:``from ... import FactorReturnAnalyzer as FRA; FRA(...)`` 必紅。"""
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    from ic1cfr_stopgap_freeze import (  # type: ignore[import-not-found]
        compare_consumer_allowlist,
        scan_factor_return_consumers_ast,
    )

    sneak = tmp_path / "sneak_alias_consumer.py"
    sneak.write_text(
        "from momentum.Analysis.factor_return_analyzer import FactorReturnAnalyzer as FRA\n"
        "x = FRA({})\n",
        encoding="utf-8",
    )
    # scan only tmp_path by temporarily using roots override via direct AST helper
    from ic1cfr_stopgap_freeze import _ast_collect_calls_in_file, DIRECT_CLASS_NAME  # type: ignore[import-not-found]

    hits = _ast_collect_calls_in_file(
        sneak, target_names=frozenset({DIRECT_CLASS_NAME})
    )
    assert hits, "AST must detect FRA(...) alias ctor"
    # 對照 allowlist:把 tmp 命中伪装成 rel path 後 compare 必 extra
    fake_current = {
        "factory_callers": [],
        "direct_consumers": [f"tests/_sneak_alias.py:{hits[0][0]}:{hits[0][1]}"],
    }
    frozen = _load_frozen_allowlist(FACTORY_ALLOWLIST_PATH)
    _extra_c, extra_d = compare_consumer_allowlist(fake_current, frozen)
    assert extra_d, f"alias ctor must be outside allowlist, got extra={extra_d!r}"


def test_consumer_guard_catches_multi_ctor_same_line(tmp_path: Path) -> None:
    """自證:同一 allowlisted 行追加第二 ctor(count>凍結)必紅。"""
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    from ic1cfr_stopgap_freeze import (  # type: ignore[import-not-found]
        DIRECT_CLASS_NAME,
        _ast_collect_calls_in_file,
        compare_consumer_allowlist,
    )

    sneak = tmp_path / "multi_ctor.py"
    # 同行兩個 ctor
    sneak.write_text(
        "from momentum.Analysis.factor_return_analyzer import FactorReturnAnalyzer\n"
        "a, b = FactorReturnAnalyzer({}), FactorReturnAnalyzer({})\n",
        encoding="utf-8",
    )
    hits = _ast_collect_calls_in_file(
        sneak, target_names=frozenset({DIRECT_CLASS_NAME})
    )
    assert len(hits) == 2, f"expected 2 Call hits on same line, got {hits!r}"
    # 凍結假裝只允許 path:line 一次 → count 2 > 1 → red
    line = hits[0][0]
    fake_current = {
        "factory_callers": [],
        "direct_consumers": [
            f"momentum/factories.py:{line}:{hits[0][1]}",
            f"momentum/factories.py:{line}:{hits[1][1]}",
        ],
    }
    # 凍結只含該 line 一次
    frozen = {
        "factory_callers": set(),
        "direct_consumers": {f"momentum/factories.py:{line}"},
    }
    _extra_c, extra_d = compare_consumer_allowlist(fake_current, frozen)
    assert extra_d, f"second ctor on same line must exceed allowlist count: {extra_d!r}"


# ---------------------------------------------------------------------------
# Mutation probes(基線綠 → 注入紅 → 還原;章程 B1.1)
# ---------------------------------------------------------------------------


def test_mutation_m1_restore_compute_batch(monkeypatch: pytest.MonkeyPatch) -> None:
    """M1:runner 直出 legacy 裸 map + 繞出口 sanitizer → explicit ok 斷言紅。

    出口 sanitizer 為第二道防線:僅假 runner 時 sanitize 仍會擋裸 map。
    必須同時拆除兩層才再現「legacy 有限 FR 直出」回歸。
    """

    def fake_run(self, selected_features, config):  # type: ignore[no-untyped-def]
        return {
            "feat_a": {
                "long_short_mean_return": 0.42,
                "risk_metrics": {"sharpe": 1.1, "max_drawdown": -0.05},
            }
        }

    def passthrough_sanitize(report: Any) -> Any:
        return report

    monkeypatch.setattr(ICFilterOrchestrator, "_run_factor_return", fake_run)
    monkeypatch.setattr(
        ICFilterOrchestrator,
        "_sanitize_deep_report_factor_returns",
        staticmethod(passthrough_sanitize),
    )
    with pytest.raises(AssertionError):
        test_explicit_enable_completed()


def test_mutation_m1b_drop_tier_exclusion(monkeypatch: pytest.MonkeyPatch) -> None:
    """M1b:移除 tier 排除 → pure-tier not_run 斷言紅。"""
    real_apply = ICFilterOrchestrator._apply_tier_config

    def no_exclusion(self, config):  # type: ignore[no-untyped-def]
        applied = real_apply(self, config)
        # 模擬舊行為:tier 強制 factor_return=True
        data = applied.model_dump(by_alias=True)
        if isinstance(data.get("factor_return"), dict):
            data["factor_return"]["enabled"] = True
        return ICConfig.model_validate(data)

    monkeypatch.setattr(ICFilterOrchestrator, "_apply_tier_config", no_exclusion)
    with pytest.raises(AssertionError):
        test_pure_tier_not_run("intermediate")


# M2 (bypass sanitizer) lives in tests/api/test_ic_deep_analysis.py with sanitizer suite.