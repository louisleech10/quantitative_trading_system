"""靜態 inventory gate；刻意不使用 pytest collect-only。"""

from __future__ import annotations

import ast
import re
from pathlib import Path


REDIRECT_FILES = (
    "tests/momentum/test_ic_e2e.py",
    "tests/momentum/test_ic_feature_filter.py",
    "tests/momentum/Analysis/test_ic_1a_cut1_golden.py",
    "tests/api/test_ic_analysis_api.py",
    "tests/api/test_ic_deep_analysis.py",
    "tests/api/test_export_api.py",
    "tests/momentum/Analysis/test_lightgbm_analyzer.py",
    "tests/momentum/Analysis/test_lightgbm_edge_cases.py",
    "tests/momentum/Analysis/test_xgboost_protocol_methods.py",
    "tests/momentum/test_lightgbm_analyzer_phase3.py",
    "tests/momentum/test_xgboost_protocol_methods_phase3.py",
    "tests/test_feature_factory_e2e.py",
)

EXPECTED_CALLERS = {
    # ── 2026-08-24 刷新（六個新呼叫端；刷新前本閘因清單過期而長期紅）──────────
    # 本閘之職責就是「新呼叫端出現要被看見」，所以**維持 `==` 不放寬**；
    # 新增檔案時要一併登記，那是刻意的摩擦，不是缺陷。
    "tests/api/test_ic_la1_degraded_gate.py",              # IC-LA1 降級閘
    "tests/golden/la0/build_after_and_attribution.py",     # LA-0 after/attribution 產生器
    "tests/golden/la1/gen_baseline.py",                    # LA-1 baseline 產生器
    "tests/momentum/Analysis/test_gap2_stage6b_wiring.py",  # GAP-2 stage6b 接線
    "tests/momentum/helpers/ichc_run.py",                  # ICHC 測試 harness（本身會呼叫 analyze）
    "tests/momentum/test_la1_lookahead.py",                # IC-LA1 lookahead
    # ── 2026-10-18 補登（TESTREG Task 4.4；860724f0／0058e3c6 新增之呼叫端）──
    "tests/momentum/Analysis/test_evtlabel_isolation_channel.py",  # EVTLABEL 隔離通道
    "tests/momentum/Analysis/test_icfirstalign_fu2.py",            # ICFIRSTALIGN FU2
    "tests/momentum/Analysis/test_evtlabel_e2e_realkline.py",      # EVTLABEL 3.10 真實 K 線端到端
    "tests/momentum/Analysis/test_splitunify_stage3_observation.py",  # SPLITUNIFY stage3 觀測（Task 4.4 同批改寫）
    # ── 2026-11-17 補登（TESTSEL I1d1；逐檔確認不寫正式資料，隔離方式附註）────
    "tests/api/test_gap3_oos_downgrade.py",                         # GAP-3（aeb85794）：各段打樁＋_suppress_persist ⇒ 不落檔
    "tests/api/test_icperf_feature_filter_split_metadata.py",       # ICPERF（f124b440）：cwd 移至 tmp（_prepare_cwd 只連結唯讀輸入）
    "tests/momentum/Analysis/test_icperf_diversification_constraint.py",  # ICPERF：呼叫 analyze 之兩測試皆 ic_persist_redirect
    "tests/momentum/Analysis/test_icperf_rolling_numerics.py",      # ICPERF（2fbe7598）：呼叫 analyze 之兩測試皆 ic_persist_redirect
    "tests/momentum/Analysis/test_icperf_hac45_size.py",            # ICPERF（eb0fd6f1）：LongShortAnalyzer.analyze 純計算、無寫檔
    "tests/momentum/Analysis/test_icperf_regime_robust.py",         # ICPERF（f70dc16b）：analyze／refilter 之測試皆 ic_persist_redirect
    "tests/momentum/Analysis/test_icperf_trend_wiring.py",          # ICPERF（54def887）：實例 _persist_outputs 換無作用
    "tests/momentum/test_ic_golden_inputs_names_opaque.py",         # FF-NAME（0b196320）：reporter 三寫出導 tmp
    # ── 原有 ────────────────────────────────────────────────────────────────
    "tests/api/test_ic_run_selector.py",
    "tests/fixtures/gen_ic_run_selector_baseline.py",
    "tests/golden/ic_phase1_1a_cut1/freeze_baseline.py",
    "tests/golden/ic_phase1_1a_cut1/freeze_baseline_new.py",
    "tests/golden/ic_phase1_contract/freeze_baseline.py",
    "tests/golden/la0/gen_baseline.py",  # LA-0 B0 baseline generator
    "tests/momentum/Analysis/test_ic_1a_cut1_golden.py",
    "tests/momentum/Analysis/test_ic_1a_cut1_oos.py",
    "tests/momentum/Analysis/test_ic_1a_cut1_split.py",
    "tests/momentum/Analysis/test_long_short_analyzer.py",
    "tests/momentum/test_ic_1eb_b2_wiring.py",
    "tests/momentum/test_ic_1eb_b4_fullstack.py",
    "tests/momentum/test_ic_e2e.py",
    "tests/momentum/test_ic_feature_filter.py",
    "tests/momentum/test_ic_filter_orchestrator.py",
    "tests/momentum/test_la0_b4_orchestrator.py",  # LA-0 B4 refilter/deep-key
    "tests/phase25/test_long_short_analyzer.py",
    "tests/phase26/test_deep_analysis_integration.py",
}


def test_redirect_files_have_static_marker_contract() -> None:
    for filename in REDIRECT_FILES:
        source = Path(filename).read_text(encoding="utf-8")
        assert "ic_persist_redirect" in source, filename
        ast.parse(source, filename=filename)


def test_function_only_marker_contracts() -> None:
    oos = Path("tests/momentum/Analysis/test_ic_1a_cut1_oos.py").read_text()
    assert "pytestmark" not in oos
    for name in (
        "test_fallback_insufficient_data_marks_applied_false",
        "test_oos_applied_true_when_sufficient",
    ):
        pattern = rf"@pytest\.mark\.ic_persist_redirect\s+@pytest\.mark\.usefixtures\(\"ic_persist_redirect\"\)\s+def {name}"
        assert re.search(pattern, oos), name

    service = Path("tests/api/test_ic_analysis_service.py").read_text()
    for name in (
        "test_analyze_real_run_split_validation_passes_with_real_axis",
        "test_resolve_run_path_contains_config_hash",
    ):
        assert re.search(rf"ic_persist_redirect[\s\S]{{0,120}}def {name}", service), name


def test_s9_s11_helpers_are_not_bypassed() -> None:
    export_source = Path("tests/api/test_export_api.py").read_text()
    assert export_source.count("_export_fixture_filtered_path(") == 2

    # S11：tests/test_feature_factory_e2e.py 於 aeb85794（TESTREG Task 4.4）改寫——生成改由 `_generate`（CGSA work_dir、
    # registry、features 皆導 tmp_path）承擔，`_create_e2e_factory()` 只剩定義＋1 呼叫（test_minimal_preset）。
    # 不繞過之意圖：檔內每個 create_feature_factory 呼叫只位於 S11 helper 或 `_generate`，且後者把 storage 換成 tmp_path。
    ff_source = Path("tests/test_feature_factory_e2e.py").read_text()
    assert len(re.findall(r"_create_e2e_factory\(\)", ff_source)) == 2
    assert len(re.findall(r"create_feature_factory\(\)", ff_source)) == 1
    owners = []
    tree = ast.parse(ff_source)
    for func in (n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)):
        for call in (n for n in ast.walk(func) if isinstance(n, ast.Call)):
            if isinstance(call.func, ast.Name) and call.func.id == "create_feature_factory":
                owners.append(func.name)
    assert sorted(owners) == ["_create_e2e_factory", "_generate"], owners
    generate = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "_generate")
    assert re.search(r"factory\._storage = FeatureStorage\(str\(tmp_path / ", ast.get_source_segment(ff_source, generate))


def test_sixteen_caller_inventory_is_complete() -> None:
    pattern = re.compile(r"\.(?:analyze|start_analysis|refilter)\(")
    actual: set[str] = set()
    for path in Path("tests").rglob("*.py"):
        if pattern.search(path.read_text(encoding="utf-8")):
            actual.add(str(path))
    assert actual == EXPECTED_CALLERS

