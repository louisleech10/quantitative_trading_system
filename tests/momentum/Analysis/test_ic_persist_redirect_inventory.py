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

    ff_source = Path("tests/test_feature_factory_e2e.py").read_text()
    assert len(re.findall(r"_create_e2e_factory\(\)", ff_source)) == 8
    assert len(re.findall(r"create_feature_factory\(\)", ff_source)) == 1


def test_sixteen_caller_inventory_is_complete() -> None:
    pattern = re.compile(r"\.(?:analyze|start_analysis|refilter)\(")
    actual: set[str] = set()
    for path in Path("tests").rglob("*.py"):
        if pattern.search(path.read_text(encoding="utf-8")):
            actual.add(str(path))
    assert actual == EXPECTED_CALLERS

