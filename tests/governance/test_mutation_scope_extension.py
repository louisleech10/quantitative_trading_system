"""TODOFMT Task 1.1：mutation 靜態檢查擴至量化三層之獨立入口（docs/TODOFMT_SPEC.md Task 1.1）。

真陽性斷言分兩段、皆只跑靜態器：(i) 量化層 fatal 集合恰為 §A 具名之 12 支；
(ii) 治理層扣除 gov_check 第 6 段既有三檔後之 fatal 集合恰為具名之 27 支（不新增排除）。
名單屬「現行啟發式之 fatal 名單」，**不是**空心探針（§A 更正；分類器另票 RESID-1）。
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tests.governance import _todofmt_anchor as anchor

REPO_ROOT = Path(__file__).resolve().parents[2]
ENTRY = REPO_ROOT / "scripts" / "mutation_scope_static.sh"
SEG6_LITERAL = "[gov_check] ✓ 探針健檢通過("

QUANT_FATAL = {
    "tests/momentum/Analysis/strategy_validation/test_wiring_check.py::test_mutation_1_contract_adds_unassembled_section",
    "tests/momentum/Analysis/strategy_validation/test_wiring_check.py::test_mutation_2_invented_reason_keyword",
    "tests/momentum/Analysis/strategy_validation/test_wiring_check.py::test_mutation_3_invented_reason_dict_form",
    "tests/momentum/Analysis/strategy_validation/test_wiring_check.py::test_mutation_4_section_only_in_docstring_and_comment",
    "tests/momentum/Analysis/strategy_validation/test_wiring_check.py::test_mutation_5_dynamic_reason_fstring_is_unresolved",
    "tests/momentum/Analysis/strategy_validation/test_wiring_check.py::test_mutation_5b_variable_holding_fstring_is_unresolved",
    "tests/momentum/Analysis/strategy_validation/test_wiring_check.py::test_mutation_6_dead_branch_does_not_count",
    "tests/momentum/Analysis/strategy_validation/test_wiring_check.py::test_mutation_n1_dead_enum_via_unused_constant_or_docstring_is_red",
    "tests/momentum/Analysis/strategy_validation/test_wiring_check.py::test_mutation_n1_non_whitelisted_passthrough_is_unresolved",
    "tests/momentum/Analysis/test_factor_return_analyzer.py::test_mutation_pos",
    "tests/momentum/Analysis/test_ic_data_cache_hermetic.py::test_mutation_redirect_disabled_caught",
    "tests/momentum/Analysis/test_ic_persist_redirect_unit.py::test_mutation_disable_redirect_internal",
}

GOV_FATAL = {
    "tests/governance/test_completeness_idlike_heading.py::test_mutation_removing_arity_breaks_structural_passthrough",
    "tests/governance/test_completeness_idlike_heading.py::test_mutation_removing_guard_lets_trailing_finding_id_escape",
    "tests/governance/test_cxrun_selfcheck_prompt.py::test_mutation_removing_selfcheck_case_turns_red",
    "tests/governance/test_doc_format_precheck.py::test_mutation_blank_touch_check_removed_turns_red",
    "tests/governance/test_doc_format_precheck.py::test_mutation_dext_anchor_check_removed_turns_red",
    "tests/governance/test_doc_format_precheck.py::test_mutation_hollow3_narrowing_leaks_to_spec_turns_red",
    "tests/governance/test_doc_format_precheck.py::test_mutation_nested_glob_restored_turns_red",
    "tests/governance/test_doc_format_precheck.py::test_mutation_precheck_exit_code_swallowed_turns_red",
    "tests/governance/test_doc_format_precheck.py::test_mutation_precheck_routing_removed_turns_red",
    "tests/governance/test_doc_format_precheck.py::test_mutation_synth_route_placed_after_early_exit_turns_red",
    "tests/governance/test_factkey_write_guard.py::test_mutation_removing_fixture_guard_lets_it_through",
    "tests/governance/test_gate_structured_verdict.py::test_mutation_restore_loose_regex_turns_red",
    "tests/governance/test_gov_check_cheap_first.py::test_mutation_removing_early_exit_makes_pytest_run",
    "tests/governance/test_gov_check_cheap_first.py::test_mutation_removing_g7_script_turns_red",
    "tests/governance/test_gov_check_dep_failclosed.py::test_mutation_restore_conditional_mount_check_turns_red",
    "tests/governance/test_gov_check_dep_failclosed.py::test_mutation_restore_conditional_skip_turns_red",
    "tests/governance/test_gov_enforcement_registry.py::test_mutation_removing_closure_binding_lets_it_through",
    "tests/governance/test_govb1_contract_matrix.py::test_mutation_g5_g6_empty_extract_fails",
    "tests/governance/test_govb1_expected_delta.py::test_mutation_d_remove_kind_binding_turns_green",
    "tests/governance/test_govb1_expected_delta.py::test_mutation_d_remove_miss_brief_turns_green",
    "tests/governance/test_govb1_expected_delta.py::test_mutation_p1_01_remove_empty_spec_guard_turns_green",
    "tests/governance/test_govb1_expected_delta.py::test_mutation_p2_02_remove_fence_exclusion_turns_green",
    "tests/governance/test_govb1_expected_delta.py::test_mutation_r2_p1_01_remove_eof_guard_turns_green",
    "tests/governance/test_spec_xref_check.py::test_mutation_disabling_check_turns_red",
    "tests/governance/test_spec_xref_check.py::test_mutation_removing_generated_exclusion_turns_red",
    "tests/governance/test_spec_xref_check.py::test_mutation_removing_structure_validation_turns_red",
    "tests/governance/test_synth_attribution_hook.py::test_mutation_disabling_id_check_turns_red",
}

_FATAL_RE = re.compile(r"^  · (\S+::[A-Za-z0-9_]+)")
_HOLLOW = "def test_mutation_hollow():\n    assert True\n"
_REAL = "def test_mutation_real(monkeypatch):\n    monkeypatch.setattr('os.sep', '/')\n    assert 1 == 1\n"


def _run_entry(root: Path | None = None) -> tuple[int, set[str], str]:
    """執行入口；root 給定時執行其下之入口複本（迷你 repo），否則執行模組層級 ENTRY。"""
    script = (root / "scripts" / "mutation_scope_static.sh") if root else ENTRY
    proc = subprocess.run(["bash", str(script)], capture_output=True, text=True, check=False)
    names = {m.group(1) for line in proc.stdout.splitlines() if (m := _FATAL_RE.match(line))}
    return proc.returncode, names, proc.stdout + proc.stderr


def _mini_repo(tmp_path: Path, probes: dict[str, str]) -> Path:
    root = tmp_path / "repo"
    (root / "scripts").mkdir(parents=True)
    shutil.copy(ENTRY, root / "scripts" / "mutation_scope_static.sh")
    shutil.copy(REPO_ROOT / "scripts" / "mutation_probe_static.py", root / "scripts" / "mutation_probe_static.py")
    (root / "scripts" / "gov_check.sh").write_text(
        'LEGACY_PROBE_DEBT="tests/governance/test_verify_gate.py"\n', encoding="utf-8"
    )
    for rel, body in probes.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")
    return root


def test_true_positive_i_quant_fatal_set_is_the_named_12() -> None:
    _, names, out = _run_entry()
    quant = {n for n in names if not n.startswith("tests/governance/")}
    assert quant == QUANT_FATAL, out


def test_true_positive_ii_governance_fatal_set_is_the_named_27() -> None:
    _, names, out = _run_entry()
    gov = {n for n in names if n.startswith("tests/governance/")}
    assert gov == GOV_FATAL, out


def test_boundary_01_quant_layer_has_no_probe_files(tmp_path: Path) -> None:
    root = _mini_repo(tmp_path, {"tests/governance/test_g.py": _REAL})
    rc, names, out = _run_entry(root)
    assert rc == 0 and names == set(), out


def test_boundary_02_only_tests_api_has_probes(tmp_path: Path) -> None:
    root = _mini_repo(tmp_path, {"tests/api/test_a.py": _HOLLOW})
    rc, names, out = _run_entry(root)
    assert rc == 1 and names == {"tests/api/test_a.py::test_mutation_hollow"}, out


def test_boundary_03_seg6_pass_literal_present_in_l_and_x() -> None:
    at_l = anchor.show(anchor.design_freeze_commit(), "scripts/gov_check.sh") or ""
    at_x = anchor.read_x("scripts/gov_check.sh") or ""
    assert SEG6_LITERAL in at_l and SEG6_LITERAL in at_x


def test_boundary_04_fatal_names_listed(tmp_path: Path) -> None:
    root = _mini_repo(tmp_path, {"tests/momentum/test_m.py": _HOLLOW, "tests/feature_engineering/test_f.py": _HOLLOW})
    rc, names, out = _run_entry(root)
    assert rc == 1 and names == {
        "tests/momentum/test_m.py::test_mutation_hollow",
        "tests/feature_engineering/test_f.py::test_mutation_hollow",
    }, out


def test_boundary_05_non_fatal_probe_not_listed(tmp_path: Path) -> None:
    root = _mini_repo(tmp_path, {"tests/momentum/test_m.py": _REAL, "tests/api/test_a.py": _HOLLOW})
    rc, names, out = _run_entry(root)
    assert names == {"tests/api/test_a.py::test_mutation_hollow"}, out


def test_boundary_06_missing_directories_do_not_crash(tmp_path: Path) -> None:
    root = _mini_repo(tmp_path, {})
    rc, names, out = _run_entry(root)
    assert rc == 0 and names == set(), out


def test_legacy_three_files_are_excluded_via_gov_check_list(tmp_path: Path) -> None:
    root = _mini_repo(tmp_path, {"tests/governance/test_verify_gate.py": _HOLLOW})
    rc, names, out = _run_entry(root)
    assert names == set(), out


def test_mutation_dropping_tests_api_from_selection_turns_red(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """選檔移除 tests/api ⇒ 只有 tests/api 有探針之情形不再列出（邊界②之測試有鑑別力）。"""
    src = ENTRY.read_text(encoding="utf-8")
    anchor_txt = "for d in tests/momentum tests/api tests/feature_engineering; do"
    assert src.count(anchor_txt) == 1
    mutant = tmp_path / "mutant_entry.sh"
    mutant.write_text(src.replace(anchor_txt, "for d in tests/momentum tests/feature_engineering; do"), encoding="utf-8")
    monkeypatch.setattr(sys.modules[__name__], "ENTRY", mutant)
    root = _mini_repo(tmp_path, {"tests/api/test_a.py": _HOLLOW})
    rc, names, out = _run_entry(root)
    assert names == set(), f"mutation 未生效：{out}"
