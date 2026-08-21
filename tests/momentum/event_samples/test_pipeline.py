"""Task B5.1 組合殼驗證：factories 出口；validate 不 raise 回 failures；run 全鏈記帳守恆（真實 kline）；
scenario 混值 loud；全部對齊失敗 loud；feature_config=None 不物化。"""

from __future__ import annotations

import pytest

from momentum.factories import create_event_sample_pipeline
from momentum.Analysis.event_samples.import_contract import ContractValidationError
from momentum.Analysis.event_samples.pipeline import EventPipelineConfig, EventSamplePipeline
from momentum.Analysis.event_samples.types import EventSplitConfig
from tests.momentum.event_samples.helpers import load_bars, make_event

BASE = 1704067200000
H12 = 43200000


@pytest.fixture(scope="module")
def bars():
    return load_bars("ETHUSDT", ("12h",))


def test_factories_single_outlet_and_contract_readonly():
    """TODO §0-6-⑦：factories 只新增 `create_event_sample_pipeline()` 一個出口；契約經 pipeline 方法唯讀（CODEX-R1-P2-05／GROK-R1-P1-03）。"""
    import re
    from pathlib import Path
    p = create_event_sample_pipeline()
    assert isinstance(p, EventSamplePipeline)
    assert "required_fields" in p.import_contract()
    assert "allowed_filtering_params" in p.condition_engine_contract()
    src = (Path(__file__).resolve().parents[3] / "momentum" / "factories.py").read_text(encoding="utf-8")
    assert len(re.findall(r"^def create_event_|^def create_condition_", src, flags=re.M)) == 1
    # 唯讀：改寫回傳不污染
    c = p.condition_engine_contract()
    c["allowed_filtering_params"].append("evil")
    assert "evil" not in p.condition_engine_contract()["allowed_filtering_params"]


def test_analyze_tables_includes_all_bars_event_membership(bars):
    """U11 全 K 線：analyze_tables 呼叫 B2.5 evaluate_all_bars（rule＝事件成員）；固定分母＋基率並排；批內多值 ⇒ not_computed 帶 reason。"""
    p = create_event_sample_pipeline()
    evs = [make_event(i, t0=BASE + x * H12, label=i % 2) for i, x in enumerate([300, 420, 560, 700, 820, 940])]
    res = p.run_with_params(evs, bars, test_fraction=0.4, tier_min_test_events=0)
    seg = {"ETHUSDT": {"12h": bars["ETHUSDT"]["12h"].iloc[:1200].reset_index(drop=True)}}
    t = p.analyze_tables(res, seg, horizons=(1, 2), n_boot=10)
    ab = t["all_bars_evaluation"]
    assert ab["statistic_kind"] == "all_bars_evaluation" and ab["capability_status"] == "ok"
    assert ab["counts"]["n_total"] == 1200 and ab["counts"]["n_eligible"] == 1200 - 2
    assert ab["label_id"] == "event_membership" and ab["overall"]["prevalence_learn"] == pytest.approx(0.5)
    assert ab["overall"]["signal_frequency"] == pytest.approx(6 / 1198, abs=1e-12)   # 6 個事件 t0 根 score=1
    assert "common" in ab and ab["common"]["formal_pooled_inference_allowed"] is False
    # 批內 direction 多值 ⇒ not_computed
    mixed = [make_event(i, t0=BASE + x * H12, label=i % 2, direction=("short" if i % 3 == 0 else "long")) for i, x in enumerate([300, 420, 560])]
    import pandas as pd
    fake = res
    fake.events = pd.DataFrame(mixed).assign(decision_offset_bars=0)
    t2 = p.analyze_tables(fake, seg, horizons=(1,), n_boot=10)
    assert t2["all_bars_evaluation"]["capability_status"] == "not_computed" and t2["all_bars_evaluation"]["reason"] == "batch_not_single_valued"


def test_validate_returns_failures_without_raise():
    p = create_event_sample_pipeline()
    df, fails = p.validate([make_event(0, label=1), make_event(1, label=0)])
    assert df is not None and fails == []
    df2, fails2 = p.validate([make_event(0, t0=1704067200, label=1)])
    assert df2 is None and {f["reason"] for f in fails2} >= {"invalid_timestamp_unit"}


def test_run_full_chain_accounting(bars):
    p = create_event_sample_pipeline()
    evs = [make_event(i, t0=BASE + x * H12, label=i % 2) for i, x in enumerate([300, 301, 420, 560, 700, 2000000])]  # 末筆 t0 不在網格 ⇒ 對齊失敗
    res = p.run(evs, bars, EventPipelineConfig(split=EventSplitConfig(test_fraction=0.4, tier_min_test_events=0)))
    s = res.summary
    assert s["n_input"] == 6 and s["n_aligned"] == 5 and s["n_align_failures"] == 1 and s["accounting_ok"]
    assert s["align_failures_by_reason"] == {"no_boundary_match": 1}
    assert len(res.events) == 5 and res.manifest.summary["n_events_raw"] == 5
    assert s["n_train"] + s["n_test"] + s["n_purged"] == 5
    assert res.features is None and s["features"] is None
    assert s["dedupe"]["policy"]["primary"] == "cluster_first"


def test_run_loud_on_invalid_mixed_scenario_and_all_failed(bars):
    p = create_event_sample_pipeline()
    with pytest.raises(ContractValidationError):
        p.run([make_event(0, t0=1704067200, label=1), make_event(1, label=0)], bars, EventPipelineConfig())
    with pytest.raises(ValueError, match="scenario"):
        p.run([make_event(0, t0=BASE + 300 * H12, label=1, scenario="A"), make_event(1, t0=BASE + 420 * H12, label=0, scenario="C")],
              bars, EventPipelineConfig(split=EventSplitConfig(tier_min_test_events=0)))
    with pytest.raises(ValueError, match="全部事件對齊失敗"):
        p.run([make_event(0, t0=BASE + 1, label=1), make_event(1, t0=BASE + 2, label=0)], bars, EventPipelineConfig())
