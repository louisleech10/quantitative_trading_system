"""T1 — NetICAnalyzer B-strict 全重寫(IC1C Phase 1)。

舊斷言為何錯(逐條,SPEC §V / TODO 防假綠):
- assert result["net_ic"]... : net_ic=相關係數減報酬率,量綱無意義;鍵全樹禁止。
- default_cost_bps=5/0/50 驅動 : 寫死成本回退;無成本唯一表示=cost_enabled=False;0 非法。
- compute_net_ic(...) : 函式已刪,混減公式不得再存在。
- profitable_after_cost is False/bool : 1c 無 canonical 報酬分子,必須 unavailable union,不得以 IC 正負代填。
- summary profitable_count/total 搭配混減 net_ic : profitable 只計 evaluable(1c 恒 0)。
- factor_returns 注入 → net_factor_return 有序列 : 1c 忽略注入,恒 unavailable(1c-FR)。
- cost_sensitivity 含 net_ic 鍵 / 自訂 scenarios 覆蓋硬編表 : 改為 §T 階梯+cost_drag_return。
- test_compute_net_factor_return_empty_aligned : 非錯舊斷言;deprecated 函式仍在,
  空對齊行為須守;phase25 刪近重複時遺失,移植入 T1 而非丟棄。
"""

from __future__ import annotations

import json
import math
from typing import Any

import numpy as np
import pandas as pd
import pytest

from momentum.Analysis.ic_config_schema import ICConfig, NetICAnalysisConfig
from momentum.Analysis.ic_filter_orchestrator import ICFilterOrchestrator
from momentum.Analysis.net_ic_analyzer import NetICAnalyzer
from tests.momentum.Analysis.test_net_ic_schema_profiles import (
    CAPACITY_KEYS,
    COST_SEMANTICS,
    SCHEMA_COST_ENABLED,
    SCHEMA_GROSS_ONLY,
    SCHEMA_SKIPPED,
    TURNOVER_SEMANTICS,
    UNAVAILABLE_REASON,
)


def _walk_keys(obj: Any, found: set[str] | None = None) -> set[str]:
    if found is None:
        found = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            found.add(str(k))
            _walk_keys(v, found)
    elif isinstance(obj, list):
        for item in obj:
            _walk_keys(item, found)
    return found


def _assert_union_unavailable(payload: Any) -> None:
    assert isinstance(payload, dict)
    assert set(payload.keys()) == {"status", "value", "reason"}
    assert payload["status"] == "unavailable"
    assert payload["value"] is None
    assert isinstance(payload["reason"], str) and payload["reason"]


def _assert_capacity(cap: Any) -> None:
    assert isinstance(cap, dict)
    assert set(cap.keys()) == CAPACITY_KEYS
    usd = cap["estimated_capacity_usd"]
    assert usd is None or (isinstance(usd, (int, float)) and math.isfinite(float(usd)))
    assert isinstance(cap["capacity_tier"], str)
    assert cap["calibration"] == "uncalibrated"


def test_no_net_ic_key_anywhere() -> None:
    analyzer = NetICAnalyzer({"cost_enabled": True, "cost_bps": 10.0})
    result = analyzer.batch_analyze(
        {"f1": {"gross_ic": 0.05}, "f2": {"gross_ic": 0.02}},
        {"f1": 1.5, "f2": 0.3},
    )
    keys = _walk_keys(result)
    assert "net_ic" not in keys
    # 序列化亦不得出現
    text = json.dumps(result, allow_nan=False)
    assert '"net_ic"' not in text


def test_cost_drag_hand_calc() -> None:
    """手算 oracle:(10/1e4)*1.5 == 0.0015(無 ×2)。"""
    assert NetICAnalyzer.compute_cost_drag(10.0, 1.5) == pytest.approx(0.0015)
    analyzer = NetICAnalyzer({"cost_enabled": True, "cost_bps": 10.0})
    out = analyzer.batch_analyze({"f1": {"gross_ic": 0.05}}, {"f1": 1.5})
    assert out["features"]["f1"]["cost_drag_return"] == pytest.approx(0.0015)


def test_breakeven_unavailable_1c() -> None:
    analyzer = NetICAnalyzer({"cost_enabled": True, "cost_bps": 10.0})
    out = analyzer.batch_analyze({"f1": {"gross_ic": 0.05}}, {"f1": 1.5})
    feat = out["features"]["f1"]
    _assert_union_unavailable(feat["breakeven_cost_bps"])
    _assert_union_unavailable(feat["profitable_after_cost"])
    _assert_union_unavailable(feat["net_factor_return"])
    assert UNAVAILABLE_REASON in feat["net_factor_return"]["reason"]


def test_no_default_cost_fallback() -> None:
    """禁 default_cost_bps=5 回退;空 config → GROSS_ONLY。"""
    analyzer = NetICAnalyzer({})
    out = analyzer.batch_analyze({"f1": {"gross_ic": 0.05}}, {"f1": 0.3})
    feat = out["features"]["f1"]
    assert set(feat.keys()) == SCHEMA_GROSS_ONLY
    assert "cost_bps" not in feat
    assert "cost_drag_return" not in feat


def test_summary_contract_b_strict() -> None:
    analyzer = NetICAnalyzer({"cost_enabled": True, "cost_bps": 10.0})
    out = analyzer.batch_analyze(
        {"f1": {"gross_ic": 0.05}, "f2": {"gross_ic": 0.02}},
        {"f1": 1.5, "f2": 0.3},
    )
    summary = out["summary"]
    assert summary["total_analyzed"] == 2
    assert summary["evaluable_count"] == 0
    assert summary["profitable_count"] == 0
    assert "avg_cost_drag_return" in summary
    assert summary["avg_cost_drag_return"] == pytest.approx(
        (0.0015 + NetICAnalyzer.compute_cost_drag(10.0, 0.3)) / 2.0
    )
    assert "avg_ic_loss_pct" not in summary
    assert "rank_correlation_gross_vs_net" not in summary

    # GROSS_ONLY:avg_cost_drag_return 鍵不存在
    gross = NetICAnalyzer({}).batch_analyze(
        {"f1": {"gross_ic": 0.05}}, {"f1": 0.3}
    )
    assert "avg_cost_drag_return" not in gross["summary"]


def test_unavailable_union_shape() -> None:
    analyzer = NetICAnalyzer({"cost_enabled": True, "cost_bps": 7.0})
    out = analyzer.batch_analyze({"f1": {"gross_ic": 0.01}}, {"f1": 0.5})
    for key in ("net_factor_return", "breakeven_cost_bps", "profitable_after_cost"):
        _assert_union_unavailable(out["features"]["f1"][key])


def test_finite_invariants() -> None:
    """capacity 子樹 strict-JSON 可序列化+鍵集合恰等+calibration。"""
    analyzer = NetICAnalyzer({"cost_enabled": True, "cost_bps": 10.0})
    out = analyzer.batch_analyze(
        {
            "f1": {"gross_ic": 0.05, "avg_daily_volume_usd": 1_000_000},
            "f2": {"gross_ic": 0.02},
        },
        {"f1": 0.2, "f2": 0.7},
    )
    for name, feat in out["features"].items():
        if feat.get("skipped"):
            continue
        _assert_capacity(feat["capacity"])
        assert set(feat.keys()) == SCHEMA_COST_ENABLED
        assert math.isfinite(float(feat["cost_drag_return"]))
        assert math.isfinite(float(feat["cost_bps"]))
        assert feat["cost_semantics"] == COST_SEMANTICS
        assert feat["turnover_semantics"] == TURNOVER_SEMANTICS
    # JSON strict
    json.dumps(out, allow_nan=False)


def test_negative_turnover_skipped() -> None:
    """注入 turnover=-0.2 → SKIPPED reason=negative_turnover;禁 clamp。"""
    analyzer = NetICAnalyzer({"cost_enabled": True, "cost_bps": 10.0})
    out = analyzer.batch_analyze({"f1": {"gross_ic": 0.05}}, {"f1": -0.2})
    feat = out["features"]["f1"]
    assert set(feat.keys()) == SCHEMA_SKIPPED
    assert feat["skipped"] is True
    assert feat["reason"] == "negative_turnover"


def test_non_finite_turnover_skipped() -> None:
    analyzer = NetICAnalyzer({})
    out = analyzer.batch_analyze({"f1": {"gross_ic": 0.05}}, {"f1": float("nan")})
    assert out["features"]["f1"]["reason"] == "non_finite_turnover"
    assert set(out["features"]["f1"].keys()) == SCHEMA_SKIPPED


def test_gross_ic_missing_and_turnover_missing() -> None:
    analyzer = NetICAnalyzer({})
    out = analyzer.batch_analyze(
        {"f1": {"gross_ic": float("nan")}, "f2": {"gross_ic": 0.03}},
        {"f1": 0.2},
    )
    assert set(out["features"]["f1"].keys()) == SCHEMA_SKIPPED
    assert out["features"]["f1"]["reason"] == "gross_ic_missing"
    assert set(out["features"]["f2"].keys()) == SCHEMA_SKIPPED
    assert out["features"]["f2"]["reason"] == "turnover_missing"


def test_no_turnover_data() -> None:
    analyzer = NetICAnalyzer({})
    result = analyzer.batch_analyze({"f1": {"gross_ic": 0.05}}, {})
    assert result["skipped"] is True
    assert result["reason"] == "turnover_not_available"
    assert result["summary"]["evaluable_count"] == 0
    assert "avg_ic_loss_pct" not in result["summary"]


def test_zero_turnover_cost_drag() -> None:
    analyzer = NetICAnalyzer({"cost_enabled": True, "cost_bps": 10.0})
    out = analyzer.batch_analyze({"f1": {"gross_ic": 0.05}}, {"f1": 0.0})
    feat = out["features"]["f1"]
    assert feat["cost_drag_return"] == 0.0
    _assert_union_unavailable(feat["breakeven_cost_bps"])


def test_cost_bps_zero_raises() -> None:
    with pytest.raises(ValueError):
        NetICAnalyzer({"cost_enabled": True, "cost_bps": 0.0})
    with pytest.raises(ValueError):
        NetICAnalyzer({"cost_enabled": False, "cost_bps": 0.0})


def test_cost_bps_nan_raises_even_when_disabled() -> None:
    """T-F7:cost_enabled=False 仍拒非有限 cost_bps。"""
    with pytest.raises(ValueError):
        NetICAnalyzer({"cost_enabled": False, "cost_bps": float("nan")})
    with pytest.raises(ValueError):
        NetICAnalyzer({"cost_enabled": True, "cost_bps": float("inf")})


def test_cost_enabled_requires_bps() -> None:
    with pytest.raises(ValueError):
        NetICAnalyzer({"cost_enabled": True, "cost_bps": None})


def test_cost_sensitivity_ladder() -> None:
    """階梯 {c/2,c,2c,5c} clamp+round0.1+去重;值符 §T;無 net_ic。"""
    analyzer = NetICAnalyzer({"cost_enabled": True, "cost_bps": 10.0})
    rows = analyzer.cost_sensitivity_analysis(10.0, 1.5)
    bps_list = [r["cost_bps"] for r in rows]
    assert bps_list == sorted(set(bps_list))
    assert 5.0 in bps_list and 10.0 in bps_list and 20.0 in bps_list and 50.0 in bps_list
    for row in rows:
        assert set(row.keys()) == {"cost_bps", "cost_drag_return"}
        assert "net_ic" not in row
        assert row["cost_drag_return"] == pytest.approx(
            (row["cost_bps"] / 10000.0) * 1.5
        )
    out = analyzer.batch_analyze({"f1": {"gross_ic": 0.05}}, {"f1": 1.5})
    assert out["features"]["f1"]["cost_semantics"] == COST_SEMANTICS


def test_compute_net_factor_return_empty_aligned() -> None:
    """phase25 移植:deprecated compute_net_factor_return 空對齊行為守門。

    函式本體仍保留供 1c-FR;batch_analyze 不再呼叫,但空 Series 對齊
    必須回 [] + NaN mean(防日後改成本公式時靜默改 shape)。
    """
    analyzer = NetICAnalyzer(config={})
    result = analyzer.compute_net_factor_return(
        pd.Series(dtype=float), pd.Series(dtype=float)
    )
    assert result["net_return_series"] == []
    assert np.isnan(result["gross_mean"])
    assert np.isnan(result["net_mean"])
    assert np.isnan(result["cost_drag"])


def test_diff_allowlist_rejects_bogus_unapproved_field() -> None:
    """T1 負例:freeze allowlist 注入 bogus_unapproved_field 必紅(codex 反例)。"""
    from scripts.ic1c_freeze_baseline import self_test_allowlist_rejects_bogus

    self_test_allowlist_rejects_bogus()


def test_factor_returns_bare_series_ignored() -> None:
    """裸 Series 注入非 FactorTimingReturnSeries 形狀 → 仍 unavailable(禁 scalar/裸序列)。"""
    analyzer = NetICAnalyzer({"cost_enabled": True, "cost_bps": 10.0})
    series = pd.Series(np.linspace(0.01, 0.02, 20))
    out = analyzer.batch_analyze(
        {"f1": {"gross_ic": 0.03}},
        {"f1": 0.3},
        factor_return_series={"f1": series},  # 缺 position
    )
    _assert_union_unavailable(out["features"]["f1"]["net_factor_return"])
    _assert_union_unavailable(out["features"]["f1"]["breakeven_cost_bps"])


def test_capacity_tiers_unchanged() -> None:
    analyzer = NetICAnalyzer({})
    assert analyzer.estimate_factor_capacity(
        turnover=1.2, avg_daily_volume_usd=1_000_000
    )["capacity_tier"] == "low"
    assert analyzer.estimate_factor_capacity(
        turnover=0.2, avg_daily_volume_usd=1_000_000
    )["capacity_tier"] == "high"
    assert analyzer.estimate_factor_capacity(
        turnover=0.7, avg_daily_volume_usd=1_000_000
    )["capacity_tier"] == "medium"
    assert analyzer.estimate_factor_capacity(
        turnover=0.2, avg_daily_volume_usd=None
    )["capacity_tier"] == "unknown"


def test_schema_config_validator() -> None:
    with pytest.raises(Exception):
        NetICAnalysisConfig(cost_enabled=True, cost_bps=None)
    with pytest.raises(Exception):
        NetICAnalysisConfig(cost_enabled=False, cost_bps=0.0)
    ok = NetICAnalysisConfig(cost_enabled=True, cost_bps=7.5)
    assert ok.cost_bps == 7.5


def test_run_net_ic_orchestrator_direct() -> None:
    """T1b:最小 orchestrator 直呼 _run_net_ic。"""
    config = ICConfig()
    orch = ICFilterOrchestrator(config)
    orch._report = {
        "summary_table": [
            {"feature_name": "f1", "ic_mean": 0.05},
            {"feature_name": "f2", "ic_mean": 0.02},
        ],
        "turnover_analysis": {
            "f1": {"quantile_turnover": 1.5},
            "f2": {"quantile_turnover": 0.3},
        },
    }
    out = orch._run_net_ic(["f1", "f2"], config)
    assert "features" in out
    for feat in out["features"].values():
        if feat.get("skipped"):
            continue
        assert set(feat.keys()) == SCHEMA_GROSS_ONLY  # default cost_enabled=False
        _assert_union_unavailable(feat["net_factor_return"])
    assert "net_ic" not in _walk_keys(out)


# ---------------------------------------------------------------------------
# Mutation probes(基線綠 → 注入紅 → 還原綠;章程 B1.1)
# ---------------------------------------------------------------------------


def test_mutation_m1_restore_mixed_subtraction(monkeypatch: pytest.MonkeyPatch) -> None:
    """M1:恢復混減(IC - cost×turnover) → 手算 oracle 紅。"""

    def mixed(cost_bps: float, turnover: float) -> float:
        return float(0.05) - (float(cost_bps) / 10000.0) * float(turnover)

    monkeypatch.setattr(
        NetICAnalyzer,
        "compute_cost_drag",
        staticmethod(mixed),
    )
    with pytest.raises(AssertionError):
        assert NetICAnalyzer.compute_cost_drag(10.0, 1.5) == pytest.approx(0.0015)


def test_mutation_m2_reinstate_x2(monkeypatch: pytest.MonkeyPatch) -> None:
    """M2:恢復 ×2(四腿計費) → 紅。"""

    def times2(cost_bps: float, turnover: float) -> float:
        return float((float(cost_bps) / 10000.0) * float(turnover) * 2.0)

    monkeypatch.setattr(NetICAnalyzer, "compute_cost_drag", staticmethod(times2))
    with pytest.raises(AssertionError):
        assert NetICAnalyzer.compute_cost_drag(10.0, 1.5) == pytest.approx(0.0015)


def test_mutation_m3_ic_numerator_backfill(monkeypatch: pytest.MonkeyPatch) -> None:
    """M3:以 IC 回填 net_factor_return/breakeven → union 斷言紅。"""
    real_batch = NetICAnalyzer.batch_analyze

    def polluted(self, ic_summary, turnover_data, factor_return_series=None):  # type: ignore[no-untyped-def]
        out = real_batch(self, ic_summary, turnover_data, factor_return_series)
        for feat in out.get("features", {}).values():
            if feat.get("skipped"):
                continue
            if "net_factor_return" in feat:
                feat["net_factor_return"] = {
                    "status": "ok",
                    "value": feat.get("gross_ic"),
                    "reason": None,
                }
        return out

    monkeypatch.setattr(NetICAnalyzer, "batch_analyze", polluted)
    analyzer = NetICAnalyzer({"cost_enabled": True, "cost_bps": 10.0})
    out = analyzer.batch_analyze({"f1": {"gross_ic": 0.05}}, {"f1": 1.5})
    with pytest.raises(AssertionError):
        _assert_union_unavailable(out["features"]["f1"]["net_factor_return"])


def test_mutation_m5_revive_cfg_get_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """M5:恢復 cfg.get(...,5.0) 預設成本 → 無成本應 GROSS_ONLY 紅。"""
    real_init = NetICAnalyzer.__init__

    def bad_init(self, config: dict) -> None:  # type: ignore[no-untyped-def]
        real_init(self, config)
        # 模擬舊 default:即使 cost_enabled=False 也塞 5bps 並開 cost
        self._cost_enabled = True
        self._cost_bps = float((config or {}).get("default_cost_bps", 5.0)) or 5.0

    monkeypatch.setattr(NetICAnalyzer, "__init__", bad_init)
    analyzer = NetICAnalyzer({})
    out = analyzer.batch_analyze({"f1": {"gross_ic": 0.05}}, {"f1": 0.3})
    with pytest.raises(AssertionError):
        assert set(out["features"]["f1"].keys()) == SCHEMA_GROSS_ONLY


def test_mutation_m6_ic_vs_ic_rankcorr(monkeypatch: pytest.MonkeyPatch) -> None:
    """M6:恢復 rank_correlation_gross_vs_net summary 欄 → 契約紅。"""
    real_batch = NetICAnalyzer.batch_analyze

    def with_rankcorr(self, ic_summary, turnover_data, factor_return_series=None):  # type: ignore[no-untyped-def]
        out = real_batch(self, ic_summary, turnover_data, factor_return_series)
        out["summary"]["rank_correlation_gross_vs_net"] = 0.99
        out["summary"]["avg_ic_loss_pct"] = 12.0
        return out

    monkeypatch.setattr(NetICAnalyzer, "batch_analyze", with_rankcorr)
    analyzer = NetICAnalyzer({"cost_enabled": True, "cost_bps": 10.0})
    out = analyzer.batch_analyze({"f1": {"gross_ic": 0.05}}, {"f1": 1.5})
    with pytest.raises(AssertionError):
        assert "rank_correlation_gross_vs_net" not in out["summary"]
        assert "avg_ic_loss_pct" not in out["summary"]


def test_mutation_m9_bare_null_placeholder(monkeypatch: pytest.MonkeyPatch) -> None:
    """M9:conditional metric 改裸 null → union 形狀紅。"""
    real_batch = NetICAnalyzer.batch_analyze

    def bare_null(self, ic_summary, turnover_data, factor_return_series=None):  # type: ignore[no-untyped-def]
        out = real_batch(self, ic_summary, turnover_data, factor_return_series)
        for feat in out.get("features", {}).values():
            if feat.get("skipped"):
                continue
            if "breakeven_cost_bps" in feat:
                feat["breakeven_cost_bps"] = None
        return out

    monkeypatch.setattr(NetICAnalyzer, "batch_analyze", bare_null)
    analyzer = NetICAnalyzer({"cost_enabled": True, "cost_bps": 10.0})
    out = analyzer.batch_analyze({"f1": {"gross_ic": 0.05}}, {"f1": 1.5})
    with pytest.raises(AssertionError):
        _assert_union_unavailable(out["features"]["f1"]["breakeven_cost_bps"])


def test_mutation_m10_drop_finite_guard(monkeypatch: pytest.MonkeyPatch) -> None:
    """M10(T1 層):拿掉 cost_bps 域檢 → 0 應拒卻被接受 → 好測試紅。"""
    monkeypatch.setattr(
        "momentum.Analysis.net_ic_analyzer._validate_cost_params",
        lambda *a, **k: None,
    )
    with pytest.raises(AssertionError):
        raised = False
        try:
            NetICAnalyzer({"cost_enabled": True, "cost_bps": 0.0})
        except ValueError:
            raised = True
        assert raised, "cost_bps=0 must raise ValueError"


def test_mutation_m11_restore_clamp(monkeypatch: pytest.MonkeyPatch) -> None:
    """M11:恢復 max(0,·) 對負 turnover 靜默 clamp → negative_turnover 紅。"""
    real_batch = NetICAnalyzer.batch_analyze

    def clamp_batch(self, ic_summary, turnover_data, factor_return_series=None):  # type: ignore[no-untyped-def]
        clamped = {
            k: max(0.0, float(v)) if v is not None and math.isfinite(float(v)) else v
            for k, v in turnover_data.items()
        }
        return real_batch(self, ic_summary, clamped, factor_return_series)

    monkeypatch.setattr(NetICAnalyzer, "batch_analyze", clamp_batch)
    analyzer = NetICAnalyzer({"cost_enabled": True, "cost_bps": 10.0})
    out = analyzer.batch_analyze({"f1": {"gross_ic": 0.05}}, {"f1": -0.2})
    with pytest.raises(AssertionError):
        assert out["features"]["f1"].get("reason") == "negative_turnover"
        assert set(out["features"]["f1"].keys()) == SCHEMA_SKIPPED


# ---------------------------------------------------------------------------
# F4 — series 回填 breakeven / profitable / turnover first-bar
# ---------------------------------------------------------------------------


def _make_timing_series(
    gross: list[float],
    position: list[float],
    name: str = "f1",
) -> Any:
    """建構 duck-typed FactorTimingReturnSeries(ls_return+position)。"""
    from momentum.Analysis.factor_return_analyzer import FactorTimingReturnSeries

    idx = pd.date_range("2024-01-01", periods=len(gross), freq="D")
    return FactorTimingReturnSeries(
        feature=name,
        ls_return=pd.Series(gross, index=idx, dtype=float),
        position=pd.Series(position, index=idx, dtype=float),
        index_policy="frame_dropna_intersection",
    )


def test_breakeven_hand_calc_20bps() -> None:
    """合成 gross_mean=0.001 / turnover_mean=0.5 → breakeven_cost_bps==20.0(±1e-9)。

    position 序列使 |Δp| mean = 0.5;gross 全 0.001 → mean(gross)/mean(to)*1e4 = 20.
    position e.g. [0, 0.5, 0, 0.5, 0, 0.5, 0, 0.5] → diffs abs mean?
    更直接:固定 turnover via position 設計.
    n=4: position [0, 0.5, 0, 0.5] → diff [nan,0.5,-0.5,0.5] → [0,0.5,0.5,0.5] mean=0.375
    n=2: position [0, 1] → [0, 1] mean=0.5; gross [0.001, 0.001] mean=0.001 → 20.0
    """
    art = _make_timing_series(
        gross=[0.001, 0.001],
        position=[0.0, 1.0],
        name="f1",
    )
    # 手算護欄
    from momentum.Analysis.net_ic_analyzer import position_to_turnover_series

    to = position_to_turnover_series(art.position)
    assert float(to.mean()) == pytest.approx(0.5)
    assert float(art.ls_return.mean()) == pytest.approx(0.001)

    analyzer = NetICAnalyzer({"cost_enabled": True, "cost_bps": 10.0})
    out = analyzer.batch_analyze(
        {"f1": {"gross_ic": 0.05}},
        {"f1": 0.3},  # scalar 僅 capacity/cost_drag;breakeven 用 series
        factor_return_series={"f1": art},
    )
    feat = out["features"]["f1"]
    be = feat["breakeven_cost_bps"]
    assert be["status"] == "ok"
    assert be["reason"] is None
    assert be["value"] == pytest.approx(20.0, abs=1e-9)

    nfr = feat["net_factor_return"]
    assert nfr["status"] == "ok"
    assert isinstance(nfr["value"], float) and math.isfinite(nfr["value"])

    prof = feat["profitable_after_cost"]
    assert prof["status"] == "ok"
    assert isinstance(prof["value"], bool)

    assert out["summary"]["evaluable_count"] > 0


def test_turnover_first_bar_zero() -> None:
    """D6: position [0,0,-1,1] → turnover [0,0,1,2](首 bar=0 非 NaN-drop)。"""
    from momentum.Analysis.net_ic_analyzer import position_to_turnover_series

    pos = pd.Series([0.0, 0.0, -1.0, 1.0])
    to = position_to_turnover_series(pos)
    assert to.tolist() == pytest.approx([0.0, 0.0, 1.0, 2.0])
    assert not to.isna().any()


def test_zero_mean_turnover_breakeven_unavailable() -> None:
    """turnover.mean()==0 → breakeven unavailable;不得代填 0。"""
    # flat position → all turnover 0
    art = _make_timing_series(
        gross=[0.01, 0.02, -0.01],
        position=[0.0, 0.0, 0.0],
        name="f1",
    )
    analyzer = NetICAnalyzer({"cost_enabled": True, "cost_bps": 10.0})
    out = analyzer.batch_analyze(
        {"f1": {"gross_ic": 0.05}},
        {"f1": 0.0},
        factor_return_series={"f1": art},
    )
    feat = out["features"]["f1"]
    be = feat["breakeven_cost_bps"]
    _assert_union_unavailable(be)
    assert be["value"] is None
    assert "zero" in be["reason"] or "turnover" in be["reason"]
    # net 仍可算(cost*0=0)
    assert feat["net_factor_return"]["status"] == "ok"


def test_run_net_ic_with_series_owner() -> None:
    """orchestrator 有 series owner → 三鍵 ok + evaluable>0。"""
    config = ICConfig()
    # enable cost for three keys
    config.net_ic_analysis.cost_enabled = True
    config.net_ic_analysis.cost_bps = 10.0
    orch = ICFilterOrchestrator(config)
    orch._report = {
        "summary_table": [{"feature_name": "f1", "ic_mean": 0.05}],
        "turnover_analysis": {"f1": {"quantile_turnover": 0.3}},
    }
    art = _make_timing_series(
        gross=[0.001, 0.001],
        position=[0.0, 1.0],
        name="f1",
    )
    orch._factor_return_series = {"f1": art}
    out = orch._run_net_ic(["f1"], config)
    feat = out["features"]["f1"]
    assert feat["breakeven_cost_bps"]["status"] == "ok"
    assert feat["breakeven_cost_bps"]["value"] == pytest.approx(20.0, abs=1e-9)
    assert feat["net_factor_return"]["status"] == "ok"
    assert feat["profitable_after_cost"]["status"] == "ok"
    assert out["summary"]["evaluable_count"] > 0


def test_cache_hit_no_owner_net_ic_not_crash() -> None:
    """cache-hit 無 owner → net_ic unavailable 不崩(F1 護欄一致)。"""
    config = ICConfig()
    orch = ICFilterOrchestrator(config)
    orch._report = {
        "summary_table": [{"feature_name": "f1", "ic_mean": 0.05}],
        "turnover_analysis": {"f1": {"quantile_turnover": 0.3}},
    }
    orch._factor_return_series = {}
    out = orch._run_net_ic(["f1"], config)
    # 無 series → nested unavailable,非崩;payload 不宣稱 ok evaluable
    assert "features" in out
    _assert_union_unavailable(out["features"]["f1"]["net_factor_return"])
    assert out["summary"]["evaluable_count"] == 0
