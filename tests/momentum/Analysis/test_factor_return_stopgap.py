"""IC1C-FR-FULL F5.1: stopgap 測試反轉(unavailable→ok §U)+E2E+consumer allowlist.

SPEC/TODO: docs/IC1CFR_FULL_{SPEC,TODO}.md Task F5.1; 延續 stopgap Phase 1 骨架.
每條改寫處註記「舊斷言為何錯」。
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest

from momentum.Analysis.ic_config_schema import ICConfig
from momentum.Analysis.ic_filter_orchestrator import ICFilterOrchestrator

REPO_ROOT = Path(__file__).resolve().parents[3]
FACTORY_ALLOWLIST_PATH = (
    REPO_ROOT / "handoffs" / "ic1cfr_stopgap_baseline" / "factory_allowlist.txt"
)


def _build_orchestrator(
    *,
    preset: str = "intermediate",
    factor_return_enabled: bool | None = None,
    cost_enabled: bool = False,
    cost_bps: float | None = None,
) -> ICFilterOrchestrator:
    """建 orchestrator。

    factor_return_enabled:
      None → 沿用 schema 預設(F5.2 前 False / 後 True);
      其餘顯式覆寫,使測案不依賴 flip 時點。
    """
    raw = ICConfig().model_dump(by_alias=True)
    raw["feature_tiers"]["active_preset"] = preset
    if factor_return_enabled is not None:
        raw["factor_return"]["enabled"] = bool(factor_return_enabled)
    # test-config: 降 min_samples 使 120-bar fixture 可過
    raw["factor_return"]["min_samples"] = 30
    raw["factor_return"]["warmup_periods"] = 20
    if cost_enabled:
        raw["net_ic_analysis"]["cost_enabled"] = True
        raw["net_ic_analysis"]["cost_bps"] = (
            float(cost_bps) if cost_bps is not None else 10.0
        )
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


def _assert_union_ok(body: Any) -> None:
    """§U ok 形狀。

    舊: status==unavailable + reason 含 legacy_misaligned/ls_returns_timestamp_misaligned
    + 無 finite leaf。
    舊為何錯: F0 重建 PIT 序列後 runner 真算 ok;sanitizer 放行 ok union;再斷言
    unavailable 會把正確 FULL 路徑判紅(stopgap 止血語意已過時)。
    """
    assert isinstance(body, dict)
    assert body.get("status") == "ok", f"expected ok, got {body!r}"
    assert body.get("reason") is None
    value = body.get("value") or {}
    assert isinstance(value, dict)
    assert value.get("schema_version") == "fr_full_v1"
    assert value.get("semantics") == "single_asset_factor_timing_ls"
    assert "ls_returns_timestamp_misaligned" not in str(body.get("reason") or "")
    assert "legacy_misaligned_factor_return_shape" not in str(body.get("reason") or "")


# ---------------------------------------------------------------------------
# Task 1.1 / F5.1 — 三態(改寫: enabled=False → not_run; enabled=True → ok)
# ---------------------------------------------------------------------------


def test_default_off_not_run() -> None:
    """顯式 enabled=False → summary not_run + 無 results 節。

    舊: 依賴 schema 預設 False 即 not_run。
    舊為何不穩: F5.2 flip 後預設 True,同測會假紅;改為顯式 False 鎖定 not_run 語意。
    """
    orch = _build_orchestrator(factor_return_enabled=False)
    report = orch.run_deep_analysis()
    assert report.module_summary.get("factor_returns") == "not_run"
    assert "factor_returns" not in report.results


@pytest.mark.parametrize("preset", ["intermediate", "advanced"])
def test_pure_tier_respects_enabled_flag(preset: str) -> None:
    """純 tier: enabled 旗標決定是否入 run(不靠 force)。

    舊: assert applied.enabled is False + not_run(假設 schema 永遠 False)。
    舊為何錯: F1.2~F4 機械鎖使預設 False;F5.2 flip 後 intermediate/advanced
    純 tier 應入 run。本測顯式測兩態,不綁死預設。
    """
    # 關: not_run
    orch_off = _build_orchestrator(preset=preset, factor_return_enabled=False)
    applied_off = orch_off._apply_tier_config(orch_off._config)
    assert applied_off.factor_return.enabled is False
    report_off = orch_off.run_deep_analysis()
    assert report_off.module_summary.get("factor_returns") == "not_run"
    assert "factor_returns" not in report_off.results

    # 開: completed + §U ok
    orch_on = _build_orchestrator(preset=preset, factor_return_enabled=True)
    applied_on = orch_on._apply_tier_config(orch_on._config)
    assert applied_on.factor_return.enabled is True
    report_on = orch_on.run_deep_analysis()
    assert report_on.module_summary.get("factor_returns") == "completed"
    _assert_union_ok(report_on.results.get("factor_returns"))


def test_explicit_enable_completed() -> None:
    """force + override 兩路徑 → §U ok + summary completed + 不入 errors。

    舊: force 後仍 assert unavailable(stopgap 擋 legacy 形狀)。
    舊為何錯: F0+F1+F2 後 force 真算 ok union;再斷言 unavailable 假紅。
    """
    # path A: force_modules(即使 schema enabled=False 也可 force 入模組)
    orch_force = _build_orchestrator(factor_return_enabled=False)
    report_force = orch_force.run_deep_analysis(force_modules=["factor_returns"])
    assert report_force.module_summary.get("factor_returns") == "completed"
    _assert_union_ok(report_force.results.get("factor_returns"))
    assert "factor_returns" not in [e.module_name for e in report_force.deep_analysis_errors]

    # path B: config_override modules enabled=true
    orch_ov = _build_orchestrator(factor_return_enabled=False)
    report_ov = orch_ov.run_deep_analysis(
        config_override={"factor_return": {"enabled": True}},
    )
    assert report_ov.module_summary.get("factor_returns") == "completed"
    _assert_union_ok(report_ov.results.get("factor_returns"))
    assert "factor_returns" not in [e.module_name for e in report_ov.deep_analysis_errors]


def test_deep_off_not_run() -> None:
    """deep 全域關(foundation) → force 亦 not_run(force 不跨 :1601 早退)。"""
    orch = _build_orchestrator(preset="foundation", factor_return_enabled=True)
    report = orch.run_deep_analysis(force_modules=["factor_returns"])
    assert report.module_summary.get("factor_returns") == "not_run"
    assert "factor_returns" not in report.results


def test_runner_returns_ok_union_internal() -> None:
    """F1.1+F2: runner 真計算回 §U ok union;出口 sanitizer 放行 ok。

    舊: runner 回 unavailable reason=ls_returns_timestamp_misaligned。
    舊為何錯: 序列時間對齊已修;runner 回 ok+series owner。
    """
    orch = _build_orchestrator(factor_return_enabled=True)
    result = orch._run_factor_return(["feat_a"], orch._config)
    assert isinstance(result, dict)
    assert result.get("status") == "ok"
    assert (result.get("value") or {}).get("schema_version") == "fr_full_v1"
    assert "feat_a" in orch._factor_return_series
    assert isinstance(orch._factor_return_series["feat_a"].ls_return, pd.Series)


def test_e2e_deep_run_breakeven_ok_with_cost() -> None:
    """F5.1 併 composer F4-1: factor_returns+net_ic+cost_enabled → breakeven ok。

    E2E deep run 斷言 breakeven_cost_bps.status==ok 且 evaluable_count>0。
    """
    orch = _build_orchestrator(
        factor_return_enabled=True,
        cost_enabled=True,
        cost_bps=10.0,
    )
    report = orch.run_deep_analysis(
        force_modules=["factor_returns", "net_ic_analysis"],
    )
    assert report.module_summary.get("factor_returns") == "completed"
    _assert_union_ok(report.results.get("factor_returns"))

    net = report.results.get("net_ic_analysis")
    assert isinstance(net, dict)
    # net_ic 本體可能是 plain dict(非 §U envelope);features 內三鍵為 §U
    features = net.get("features") or {}
    assert features, f"net_ic features empty: {net!r}"
    # 至少一個 feature breakeven ok
    ok_breakeven = [
        name
        for name, feat in features.items()
        if isinstance(feat, dict)
        and isinstance(feat.get("breakeven_cost_bps"), dict)
        and feat["breakeven_cost_bps"].get("status") == "ok"
    ]
    assert ok_breakeven, f"no breakeven ok in {features!r}"
    summary = net.get("summary") or {}
    assert int(summary.get("evaluable_count") or 0) > 0


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
    """現況 AST scan ⊆ 凍結 allowlist;scanner 與 freeze 腳本共用。"""
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
    from ic1cfr_stopgap_freeze import _ast_collect_calls_in_file, DIRECT_CLASS_NAME  # type: ignore[import-not-found]

    hits = _ast_collect_calls_in_file(
        sneak, target_names=frozenset({DIRECT_CLASS_NAME})
    )
    assert hits, "AST must detect FRA(...) alias ctor"
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
    sneak.write_text(
        "from momentum.Analysis.factor_return_analyzer import FactorReturnAnalyzer\n"
        "a, b = FactorReturnAnalyzer({}), FactorReturnAnalyzer({})\n",
        encoding="utf-8",
    )
    hits = _ast_collect_calls_in_file(
        sneak, target_names=frozenset({DIRECT_CLASS_NAME})
    )
    assert len(hits) == 2, f"expected 2 Call hits on same line, got {hits!r}"
    line = hits[0][0]
    fake_current = {
        "factory_callers": [],
        "direct_consumers": [
            f"momentum/factories.py:{line}:{hits[0][1]}",
            f"momentum/factories.py:{line}:{hits[1][1]}",
        ],
    }
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
    """M1b:移除 foundation deep 關閉 → foundation 仍應靠 deep_enabled 護欄。

    舊 M1b:對 intermediate 強設 enabled=True 使 pure-tier not_run 紅。
    現 pure-tier 已改兩態;改對 foundation:若繞過 deep_enabled 全關,force 仍 not_run
    的契約由 test_deep_off_not_run 覆蓋。此測保留:把 intermediate enabled 強 True
    後 pure-tier-off 斷言必須紅(證明測有牙)。
    """
    real_apply = ICFilterOrchestrator._apply_tier_config

    def force_on(self, config):  # type: ignore[no-untyped-def]
        applied = real_apply(self, config)
        data = applied.model_dump(by_alias=True)
        if isinstance(data.get("factor_return"), dict):
            data["factor_return"]["enabled"] = True
        return ICConfig.model_validate(data)

    monkeypatch.setattr(ICFilterOrchestrator, "_apply_tier_config", force_on)
    with pytest.raises(AssertionError):
        # enabled=False 建構,但 apply 被 monkey 成 True → off 支路紅
        orch = _build_orchestrator(preset="intermediate", factor_return_enabled=False)
        applied = orch._apply_tier_config(orch._config)
        assert applied.factor_return.enabled is False
