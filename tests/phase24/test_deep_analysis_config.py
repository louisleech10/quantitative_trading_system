"""Phase 2.4 / IC1C T5 — deep analysis config + Net IC cost validator。

舊斷言為何錯(SPEC §V / TODO Task 2.1 T5):
- `config.net_ic_analysis.default_cost_bps == 5` — 固化寫死成本回退;
  5.0 bps 預設已拔;無成本唯一表示=cost_enabled=False;cost_bps 預設 None。
- YAML/api_override 以 `default_cost_bps` 合併 — 鍵已刪,改 cost_enabled+cost_bps。
"""

from __future__ import annotations

import pytest

from momentum.Analysis.deep_analysis_types import DeepAnalysisReport, SkippedResult
from momentum.Analysis.ic_config_schema import (
    ICConfig,
    LongShortAnalysisConfig,
    NetICAnalysisConfig,
    load_ic_config,
)


def test_deep_analysis_types_instantiation():
    skipped = SkippedResult(module_name="test", reason="r", error_type="INSUFFICIENT_DATA")
    report = DeepAnalysisReport()

    assert skipped.module_name == "test"
    assert report.total_modules == 10
    assert report.completed_count == 0


def test_ic_config_contains_deep_analysis_sections():
    config = ICConfig()
    # 舊 stopgap 斷言 `enabled is False` 為何錯: F5.2 已 flip enabled=True
    # (PIT 乾淨後恢復預設 ON;stopgap 止血結束)。
    assert config.factor_return.enabled is True
    assert config.factor_centrality.enabled is True
    assert config.trend_analysis.enabled is True
    assert config.parameter_sensitivity.enabled is True
    assert config.rolling_oos.enabled is True
    # B-strict:無 default_cost_bps;預設 cost_enabled=False, cost_bps=None
    assert config.net_ic_analysis.cost_enabled is False
    assert config.net_ic_analysis.cost_bps is None
    assert not hasattr(config.net_ic_analysis, "default_cost_bps") or not getattr(
        type(config.net_ic_analysis), "model_fields", {}
    ).get("default_cost_bps")


def test_net_ic_cost_validator() -> None:
    """T5:schema 層 cost_bps 域檢(非 None 一律驗;enabled 另驗非 None)。"""
    # 合法:disabled + None
    ok = NetICAnalysisConfig(cost_enabled=False, cost_bps=None)
    assert ok.cost_enabled is False
    assert ok.cost_bps is None

    # 合法:enabled + 域內
    ok2 = NetICAnalysisConfig(cost_enabled=True, cost_bps=7.0)
    assert ok2.cost_bps == 7.0

    # 0 非法
    with pytest.raises(ValueError, match="cost_bps"):
        NetICAnalysisConfig(cost_enabled=True, cost_bps=0.0)

    # 上界
    with pytest.raises(ValueError, match="cost_bps"):
        NetICAnalysisConfig(cost_enabled=False, cost_bps=1000.1)

    # NaN 即使 disabled 也拒(T-F7)
    with pytest.raises(ValueError, match="cost_bps"):
        NetICAnalysisConfig(cost_enabled=False, cost_bps=float("nan"))

    # inf
    with pytest.raises(ValueError, match="cost_bps"):
        NetICAnalysisConfig(cost_enabled=True, cost_bps=float("inf"))

    # enabled 缺 bps
    with pytest.raises(ValueError, match="cost_enabled"):
        NetICAnalysisConfig(cost_enabled=True, cost_bps=None)


def test_mutation_m10_config_drop_validator(monkeypatch: pytest.MonkeyPatch) -> None:
    """M10 config 層:拿掉 cost_bps 域檢 → 0 應拒卻被接受 → 好測試紅。

    變異體以生產 ``NetICAnalysisConfig.model_fields`` 重建（欄位與預設隨生產同步），
    只剝除 field/model validator；再讓真正的 ``test_net_ic_cost_validator`` 跑在
    變異 schema 上，須以 ``pytest.raises`` 未觸發之 Failed 失敗——證明原測試會紅。
    """
    from pydantic import create_model

    raised = False
    real_cls = NetICAnalysisConfig
    loose_cls = create_model(
        "_LooseNetICAnalysisConfig",
        **{name: (field.annotation, field) for name, field in real_cls.model_fields.items()},
    )

    import tests.phase24.test_deep_analysis_config as this_mod

    monkeypatch.setattr(this_mod, "NetICAnalysisConfig", loose_cls)

    # 前提：變異體確實接受 cost_bps=0（validator 已剝除）
    with pytest.raises(AssertionError):
        raised = False
        try:
            this_mod.NetICAnalysisConfig(cost_enabled=True, cost_bps=0.0)
        except ValueError:
            raised = True
        assert raised, "cost_bps=0 must raise ValueError at config layer"
    # 前提：變異體欄位集合與生產一致（只差 validator）
    assert set(loose_cls.model_fields) == set(real_cls.model_fields)

    # 核心：真正的守護測試跑在變異 schema 上必紅
    with pytest.raises(pytest.fail.Exception):
        this_mod.test_net_ic_cost_validator()

    # 對照：還原生產 schema 後同一測試通過（排除測試本身恆紅）
    monkeypatch.undo()
    assert this_mod.NetICAnalysisConfig is real_cls
    this_mod.test_net_ic_cost_validator()


def test_long_short_quantile_overlap_rejected():
    with pytest.raises(ValueError):
        LongShortAnalysisConfig(
            num_quantiles=5,
            long_quantiles=[4, 5],
            short_quantiles=[5],
        )


def test_long_short_quantile_non_overlap_ok():
    config = LongShortAnalysisConfig(
        num_quantiles=5,
        long_quantiles=[4, 5],
        short_quantiles=[1, 2],
    )
    assert config.num_quantiles == 5


def test_load_ic_config_three_layer_merge_deep_analysis(tmp_path):
    default_path = tmp_path / "ic_config.yaml"
    user_path = tmp_path / "user_ic_config.yaml"

    default_path.write_text(
        """
version: '1.0'
factor_return:
  enabled: true
  num_quantiles: 5
net_ic_analysis:
  cost_enabled: false
  cost_bps: null
""".strip(),
        encoding="utf-8",
    )
    user_path.write_text(
        """
factor_return:
  num_quantiles: 3
""".strip(),
        encoding="utf-8",
    )

    config = load_ic_config(
        default_path=str(default_path),
        user_path=str(user_path),
        api_override={"net_ic_analysis": {"cost_enabled": True, "cost_bps": 10}},
    )

    assert config.factor_return.num_quantiles == 3
    assert config.net_ic_analysis.cost_enabled is True
    assert config.net_ic_analysis.cost_bps == 10
