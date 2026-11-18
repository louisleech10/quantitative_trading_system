"""PRE-RED Task 3.1：允許仍紅名稱集合之精確集合與可收集性（docs/PRERED_SPEC.md Task 3.1）。

`tests/_golden/prered/allowed_red.json`：每列 `{node, owner_ticket, reason, trigger, state}`。
- 精確集合：JSON 之 (node, owner_ticket, reason, state) 必須**逐列等於**本檔 EXPECTED（不以子字串比對）；
  任何新增、刪除、改歸屬皆須同 commit 改本檔，使變更必經審碼。
- 可收集：每列 node 之 `<檔>::<函式>[<參數>]` 須經 `pytest --collect-only -q` 實際收集到（參數化 id 逐字比對）。
- owner_ticket 須為 docs/TICKET_ORDER.md 表內之票名或 PRE-RED；reason／state 為封閉值。
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ALLOWED = REPO_ROOT / "tests" / "_golden" / "prered" / "allowed_red.json"
TICKET_ORDER = REPO_ROOT / "docs" / "TICKET_ORDER.md"
REASONS = {"blocked-by", "user-ruling", "needs-research"}
STATES = {"pending-approval", "owned-by-later-ticket"}

# ICFIRSTALIGN b4（2026-10-08）：F-2 原設定跑完、BTCUSDT/1h 與多週期重凍（使用者 2026-10-04 核可③）後 9 列實跑全綠而刪；
# 重凍（使用者 2026-10-03 核可）後之狀態：五支 pending 列已刪；多週期基準與 config_hash 釘值歸 F-2；
# 刪除舊特徵 run（使用者 2026-10-03 核可）所致之紅經 red census 實跑列入（收據 handoffs/run_receipts/20261003-prered-red-census.txt）
EXPECTED = {
    ("tests/momentum/test_feature_library_config_hash.py::test_load_multi_without_config_hashes_byte_stable", "FFSTORE", "user-ruling", "owned-by-later-ticket"),
    ("tests/momentum/test_feature_library_config_hash.py::test_load_with_config_hash_disambig", "FFSTORE", "user-ruling", "owned-by-later-ticket"),
    ("tests/momentum/test_feature_library_config_hash.py::test_load_without_config_hash_matches_find_latest_materialized", "FFSTORE", "user-ruling", "owned-by-later-ticket"),
    ("tests/momentum/test_ic_cross_sectional_cut2.py::test_cross_sectional_e2e_real_path_append_and_analyze", "FFSTORE", "user-ruling", "owned-by-later-ticket"),
    # TESTSEL I10 G4（2026-11-13，b2 審碼 r2 CODEX-R2-P1-03）：RegimeDetector 短序列 fallback 未來洩漏之可見已知紅
    ("tests/momentum/test_la1_pit_small_scale.py::test_short_series_fallback_labels_equal_full_run_prefix", "ICPATH", "blocked-by", "owned-by-later-ticket"),
    # TESTSEL I10 G1（2026-11-13）：FFTFMETA 非主週期失敗語意被 FFSTAT 預熱恆開（d229336e）之公開域預載破壞（產品缺陷，歸 FFPROD）
    ("tests/test_multi_tf_generator.py::test_canonical_completeness_three_paths_four_cases[cgsa_serial-skip]", "FFPROD", "blocked-by", "owned-by-later-ticket"),
    ("tests/test_multi_tf_generator.py::test_canonical_completeness_three_paths_four_cases[cgsa_serial-failed]", "FFPROD", "blocked-by", "owned-by-later-ticket"),
    ("tests/test_multi_tf_generator.py::test_canonical_completeness_three_paths_four_cases[cgsa_parallel-skip]", "FFPROD", "blocked-by", "owned-by-later-ticket"),
    ("tests/test_multi_tf_generator.py::test_canonical_completeness_three_paths_four_cases[cgsa_parallel-failed]", "FFPROD", "blocked-by", "owned-by-later-ticket"),
    ("tests/test_multi_tf_generator.py::test_boundary_19_canonical_completeness_parallel_error_fail_closed", "FFPROD", "blocked-by", "owned-by-later-ticket"),
    ("tests/momentum/Analysis/test_icperf_compare_units.py::test_boundary_01_response_leaf_unit", "ICPERF", "blocked-by", "owned-by-later-ticket"),
    ("tests/momentum/Analysis/test_icperf_compare_units.py::test_boundary_02_json_file_field_unit_and_sha_not_separate", "ICPERF", "blocked-by", "owned-by-later-ticket"),
    ("tests/momentum/Analysis/test_icperf_compare_units.py::test_boundary_03_json_fields_equal_sha_differs_is_hard_failure", "ICPERF", "blocked-by", "owned-by-later-ticket"),
    ("tests/momentum/Analysis/test_icperf_compare_units.py::test_boundary_04_file_only_one_side_unit", "ICPERF", "blocked-by", "owned-by-later-ticket"),
    ("tests/momentum/Analysis/test_icperf_compare_units.py::test_boundary_05_opaque_and_asymmetric_parse_sha_unit", "ICPERF", "blocked-by", "owned-by-later-ticket"),
    ("tests/momentum/Analysis/test_icperf_compare_units.py::test_boundary_06_hdf5_object_unit_and_bytes_only_hard_failure", "ICPERF", "blocked-by", "owned-by-later-ticket"),
    ("tests/momentum/Analysis/test_icperf_compare_units.py::test_boundary_07_features_pit_selected_stage_removed_item_units", "ICPERF", "blocked-by", "owned-by-later-ticket"),
    ("tests/momentum/Analysis/test_icperf_compare_units.py::test_boundary_08_non_declarable_hard_failures", "ICPERF", "blocked-by", "owned-by-later-ticket"),
    ("tests/momentum/Analysis/test_icperf_compare_units.py::test_boundary_09_volatile_json_excluded_no_unit_no_failure", "ICPERF", "blocked-by", "owned-by-later-ticket"),
    ("tests/momentum/Analysis/test_icperf_compare_units.py::test_boundary_10_units_consistent_with_human_messages", "ICPERF", "blocked-by", "owned-by-later-ticket"),
    ("tests/momentum/Analysis/test_icperf_compare_units.py::test_boundary_11_l4_pass_when_three_conditions_hold", "ICPERF", "blocked-by", "owned-by-later-ticket"),
    ("tests/momentum/Analysis/test_icperf_compare_units.py::test_boundary_12_l4_actual_not_subset_of_declared", "ICPERF", "blocked-by", "owned-by-later-ticket"),
    ("tests/momentum/Analysis/test_icperf_compare_units.py::test_boundary_13_l4_parent_declaration_does_not_cover_leaf", "ICPERF", "blocked-by", "owned-by-later-ticket"),
    ("tests/momentum/Analysis/test_icperf_compare_units.py::test_boundary_14_l4_actual_unit_without_oracle", "ICPERF", "blocked-by", "owned-by-later-ticket"),
    ("tests/momentum/Analysis/test_icperf_compare_units.py::test_boundary_15_l4_declared_unchanged_needs_closed_reason", "ICPERF", "blocked-by", "owned-by-later-ticket"),
    ("tests/momentum/Analysis/test_icperf_compare_units.py::test_boundary_16_l4_hard_failures_block", "ICPERF", "blocked-by", "owned-by-later-ticket"),
    ("tests/momentum/Analysis/test_icperf_compare_units.py::test_boundary_17_source_identity_missing_both_sides_hard_failure", "ICPERF", "blocked-by", "owned-by-later-ticket"),
    ("tests/momentum/Analysis/test_icperf_compare_units.py::test_boundary_18_hdf5_volatile_attrs_excluded", "ICPERF", "blocked-by", "owned-by-later-ticket"),
    ("tests/momentum/Analysis/test_icperf_compare_units.py::test_boundary_19_l4_declared_unit_with_invalid_shape_rejected", "ICPERF", "blocked-by", "owned-by-later-ticket"),
    ("tests/momentum/Analysis/test_icperf_compare_units.py::test_boundary_20_hdf5_object_branches[added]", "ICPERF", "blocked-by", "owned-by-later-ticket"),
    ("tests/momentum/Analysis/test_icperf_compare_units.py::test_boundary_20_hdf5_object_branches[dtype]", "ICPERF", "blocked-by", "owned-by-later-ticket"),
    ("tests/momentum/Analysis/test_icperf_compare_units.py::test_boundary_20_hdf5_object_branches[kind]", "ICPERF", "blocked-by", "owned-by-later-ticket"),
    ("tests/momentum/Analysis/test_icperf_compare_units.py::test_boundary_20_hdf5_object_branches[removed]", "ICPERF", "blocked-by", "owned-by-later-ticket"),
    ("tests/momentum/Analysis/test_icperf_compare_units.py::test_boundary_20_hdf5_object_branches[shape]", "ICPERF", "blocked-by", "owned-by-later-ticket"),
    ("tests/momentum/Analysis/test_icperf_compare_units.py::test_boundary_21_json_field_added_or_removed[added]", "ICPERF", "blocked-by", "owned-by-later-ticket"),
    ("tests/momentum/Analysis/test_icperf_compare_units.py::test_boundary_21_json_field_added_or_removed[removed]", "ICPERF", "blocked-by", "owned-by-later-ticket"),
    ("tests/momentum/Analysis/test_icperf_compare_units.py::test_boundary_22_source_identity_missing_one_side_hard_failure[current]", "ICPERF", "blocked-by", "owned-by-later-ticket"),
    ("tests/momentum/Analysis/test_icperf_compare_units.py::test_boundary_22_source_identity_missing_one_side_hard_failure[frozen]", "ICPERF", "blocked-by", "owned-by-later-ticket"),
    ("tests/momentum/Analysis/test_icperf_compare_units.py::test_boundary_23_parent_id_rejected_even_when_sets_match", "ICPERF", "blocked-by", "owned-by-later-ticket"),
    ("tests/momentum/Analysis/test_icperf_compare_units.py::test_boundary_24_golden_unit_universe_lists_finest_units", "ICPERF", "blocked-by", "owned-by-later-ticket"),
    ("tests/momentum/Analysis/test_icperf_compare_units.py::test_mutation_unit_key_collapse_flips_l4", "ICPERF", "blocked-by", "owned-by-later-ticket"),
    ("tests/momentum/Analysis/test_icperf_cpcv_full_paths.py::test_boundary_01_default_is_full_mode", "ICPERF", "blocked-by", "owned-by-later-ticket"),
    ("tests/momentum/Analysis/test_icperf_cpcv_full_paths.py::test_boundary_02_explicit_sampling_reports_actual_and_total", "ICPERF", "blocked-by", "owned-by-later-ticket"),
    ("tests/momentum/Analysis/test_icperf_cpcv_full_paths.py::test_boundary_03_full_mode_summary_not_sampled", "ICPERF", "blocked-by", "owned-by-later-ticket"),
    ("tests/momentum/Analysis/test_icperf_cpcv_full_paths.py::test_boundary_04_config_default_null", "ICPERF", "blocked-by", "owned-by-later-ticket"),
    ("tests/momentum/Analysis/test_icperf_cpcv_full_paths.py::test_boundary_05_api_request_default_and_no_arbitrary_cap", "ICPERF", "blocked-by", "owned-by-later-ticket"),
    ("tests/momentum/Analysis/test_icperf_cpcv_full_paths.py::test_boundary_06_validate_response_reports_path_summary", "ICPERF", "blocked-by", "owned-by-later-ticket"),
    ("tests/momentum/Analysis/test_icperf_cpcv_full_paths.py::test_boundary_07_full_mode_split_is_lazy", "ICPERF", "blocked-by", "owned-by-later-ticket"),
    ("tests/momentum/Analysis/test_icperf_cpcv_full_paths.py::test_boundary_08_validate_consumes_split_lazily", "ICPERF", "blocked-by", "owned-by-later-ticket"),
    ("tests/momentum/Analysis/test_icperf_data_warning_codes.py::test_boundary_01_contract_registers_existing_and_new_codes", "ICPERF", "blocked-by", "owned-by-later-ticket"),
    ("tests/momentum/Analysis/test_icperf_data_warning_codes.py::test_boundary_02_small_sample_detail_keys_match_product", "ICPERF", "blocked-by", "owned-by-later-ticket"),
    ("tests/momentum/Analysis/test_icperf_data_warning_codes.py::test_boundary_03_all_product_codes_registered", "ICPERF", "blocked-by", "owned-by-later-ticket"),
    ("tests/momentum/Analysis/test_icperf_data_warning_codes.py::test_boundary_04_frontend_types_match_contract", "ICPERF", "blocked-by", "owned-by-later-ticket"),
    ("tests/momentum/Analysis/test_icperf_data_warning_codes.py::test_boundary_05_api_response_roundtrip_and_rejects_unregistered", "ICPERF", "blocked-by", "owned-by-later-ticket"),
    # TESTSEL I1d1（2026-11-17）：同檔第 9 條（契約 codes:{} 空殼之施工前紅）補登；ICPERF 研究擷取檔依賴（只於整合樹紅）
    ("tests/momentum/Analysis/test_icperf_data_warning_codes.py::test_boundary_06_new_codes_detail_cover_d_fields", "ICPERF", "blocked-by", "owned-by-later-ticket"),
    ("tests/momentum/Analysis/test_icperf_correctness.py::test_correctness_coverage_closed_over_response_keys", "ICPERF", "blocked-by", "owned-by-later-ticket"),
    ("tests/momentum/Analysis/test_icperf_data_warning_codes.py::test_boundary_07_precedence_registered_and_matches_product", "ICPERF", "blocked-by", "owned-by-later-ticket"),
    ("tests/momentum/Analysis/test_icperf_data_warning_codes.py::test_boundary_08_fixed_lag_and_ewc_codes_mutually_exclusive", "ICPERF", "blocked-by", "owned-by-later-ticket"),
    ("tests/momentum/Analysis/test_icperf_data_warning_codes.py::test_mutation_product_detail_key_dropped_detected", "ICPERF", "blocked-by", "owned-by-later-ticket"),
    ("tests/momentum/Analysis/test_icperf_gate.py::test_boundary_15_measured_ids_cover_inventory", "ICPERF", "blocked-by", "owned-by-later-ticket"),
    ("tests/momentum/Analysis/test_icperf_gate.py::test_boundary_16_three_points_per_entry", "ICPERF", "blocked-by", "owned-by-later-ticket"),
    ("tests/momentum/Analysis/test_icperf_gate.py::test_boundary_17_criteria_fields_and_rules", "ICPERF", "blocked-by", "owned-by-later-ticket"),
    ("tests/momentum/Analysis/test_icperf_gate.py::test_boundary_18_scale_points_within_budget", "ICPERF", "blocked-by", "owned-by-later-ticket"),
    ("tests/momentum/Analysis/test_icperf_gate.py::test_boundary_19_over_ten_minutes_two_points_annotated", "ICPERF", "blocked-by", "owned-by-later-ticket"),
    ("tests/momentum/Analysis/test_icperf_gate.py::test_boundary_20_rss_meter_and_chunk_cap_recorded", "ICPERF", "blocked-by", "owned-by-later-ticket"),
    ("tests/momentum/Analysis/test_icperf_hac_fixed_lag.py::test_boundary_01_ic_series_small_n_computes_with_warning[1]", "ICPERF", "blocked-by", "owned-by-later-ticket"),
    ("tests/momentum/Analysis/test_icperf_hac_fixed_lag.py::test_boundary_01_ic_series_small_n_computes_with_warning[5]", "ICPERF", "blocked-by", "owned-by-later-ticket"),
    ("tests/momentum/Analysis/test_icperf_hac_fixed_lag.py::test_boundary_01_ic_series_small_n_computes_with_warning[6]", "ICPERF", "blocked-by", "owned-by-later-ticket"),
    ("tests/momentum/Analysis/test_icperf_hac_fixed_lag.py::test_boundary_01_ic_series_small_n_computes_with_warning[7]", "ICPERF", "blocked-by", "owned-by-later-ticket"),
    ("tests/momentum/Analysis/test_icperf_hac_fixed_lag.py::test_boundary_04_ic_series_constant_degenerate", "ICPERF", "blocked-by", "owned-by-later-ticket"),
    ("tests/momentum/Analysis/test_icperf_hac_fixed_lag.py::test_boundary_05_validator_entry_small_n_computes_with_warning[1]", "ICPERF", "blocked-by", "owned-by-later-ticket"),
    ("tests/momentum/Analysis/test_icperf_hac_fixed_lag.py::test_boundary_05_validator_entry_small_n_computes_with_warning[5]", "ICPERF", "blocked-by", "owned-by-later-ticket"),
    ("tests/momentum/Analysis/test_icperf_hac_fixed_lag.py::test_boundary_05_validator_entry_small_n_computes_with_warning[6]", "ICPERF", "blocked-by", "owned-by-later-ticket"),
    ("tests/momentum/Analysis/test_icperf_hac_fixed_lag.py::test_boundary_05_validator_entry_small_n_computes_with_warning[7]", "ICPERF", "blocked-by", "owned-by-later-ticket"),
    ("tests/momentum/Analysis/test_icperf_limit_l1_coverage.py::test_every_declared_row_is_an_l0_l1_row", "ICPERF", "blocked-by", "owned-by-later-ticket"),
    ("tests/momentum/Analysis/test_icperf_limit_l1_coverage.py::test_l1a_rows_fully_covered", "ICPERF", "blocked-by", "owned-by-later-ticket"),
    ("tests/momentum/Analysis/test_icperf_limit_l1_coverage.py::test_l1b_rows_fully_covered", "ICPERF", "blocked-by", "owned-by-later-ticket"),
    ("tests/momentum/Analysis/test_icperf_limit_l1_coverage.py::test_l1c_rows_fully_covered", "ICPERF", "blocked-by", "owned-by-later-ticket"),
    ("tests/feature_engineering/test_ffprod_decisions.py::test_boundary_07_retain_choice_has_empty_changed_targets", "FFPROD", "blocked-by", "owned-by-later-ticket"),
    ("tests/feature_engineering/test_ffprod_decisions.py::test_decisions_cover_every_measured_candidate", "FFPROD", "blocked-by", "owned-by-later-ticket"),
    ("tests/feature_engineering/test_ffprod_decisions.py::test_decisions_match_measured_options", "FFPROD", "blocked-by", "owned-by-later-ticket"),
    ("tests/feature_engineering/test_ffprod_decisions.py::test_every_decision_cites_user_ruling", "FFPROD", "blocked-by", "owned-by-later-ticket"),
    ("tests/feature_engineering/test_ffprod_gate.py::test_gate_regenerated_cells_match_frozen[C_BTCUSDT_1h]", "FFPROD", "blocked-by", "owned-by-later-ticket"),
    ("tests/feature_engineering/test_numview_acceptance.py::test_gate_new_freeze_bitwise_equal_at_current_code[A_BTCUSDT_12h]", "FFPROD", "blocked-by", "owned-by-later-ticket"),
    ("tests/feature_engineering/test_numview_acceptance.py::test_gate_new_freeze_bitwise_equal_at_current_code[A_BTCUSDT_1h]", "FFPROD", "blocked-by", "owned-by-later-ticket"),
    ("tests/feature_engineering/test_numview_acceptance.py::test_gate_new_freeze_bitwise_equal_at_current_code[A_BTCUSDT_4h]", "FFPROD", "blocked-by", "owned-by-later-ticket"),
    ("tests/feature_engineering/test_numview_acceptance.py::test_gate_new_freeze_bitwise_equal_at_current_code[A_SOLUSDT_1h]", "FFPROD", "blocked-by", "owned-by-later-ticket"),
    ("tests/feature_engineering/test_numview_acceptance.py::test_gate_new_freeze_bitwise_equal_at_current_code[B_BTCUSDT_1h_4h]", "FFPROD", "blocked-by", "owned-by-later-ticket"),
    ("tests/feature_engineering/test_numview_acceptance.py::test_gate_new_freeze_bitwise_equal_at_current_code[C_BTCUSDT_1h]", "FFPROD", "blocked-by", "owned-by-later-ticket"),
    ("tests/feature_engineering/test_failopen_correctness.py::test_v3_multi_tf_btc_matches_frozen_baseline", "FFPROD", "blocked-by", "owned-by-later-ticket"),
    ("tests/feature_engineering/test_fftfmeta_golden.py::test_golden_degraded_single_tf_manifest_matches_task_record", "FFPROD", "blocked-by", "owned-by-later-ticket"),
    ("tests/feature_engineering/test_fftfmeta_golden.py::test_golden_multi_tf_features_unchanged_and_timeframes_canonical", "FFPROD", "blocked-by", "owned-by-later-ticket"),
    # TESTSEL I1g（2026-11-18）：NUMVIEW 落選分支 27 條改收集期條件跳過（決定紀錄 retain）、failopen v8 未限定版刪檔後刪列
    # TESTSEL I1d1（2026-11-17）：perf 三族欄（FF-NAME category 段）與 talib 註冊數（2247c394 別名）修測試後刪列
    # TESTSEL 合回 main（2026-11-18）：testreg hook 牆鐘門檻條，main 合回前即紅（中位 1.66–2.23 s ＞ 1 s），歸 TESTREG
    ("tests/registry/test_testreg_write_guard.py::test_boundary_05_helper_backprop_wall_clock_median_under_1s[comment_appended]", "TESTREG", "blocked-by", "owned-by-later-ticket"),
    ("tests/registry/test_testreg_write_guard.py::test_boundary_05_helper_backprop_wall_clock_median_under_1s[fixture_docstring_added]", "TESTREG", "blocked-by", "owned-by-later-ticket"),
    ("tests/registry/test_testreg_write_guard.py::test_boundary_05_helper_backprop_wall_clock_median_under_1s[import_added]", "TESTREG", "blocked-by", "owned-by-later-ticket"),
    ("tests/registry/test_testreg_write_guard.py::test_boundary_05_helper_backprop_wall_clock_median_under_1s[unchanged]", "TESTREG", "blocked-by", "owned-by-later-ticket"),
    ("tests/registry/test_testreg_write_guard.py::test_boundary_06_pytest_ini_wall_clock[classes_narrowed]", "TESTREG", "blocked-by", "owned-by-later-ticket"),
    ("tests/registry/test_testreg_write_guard.py::test_boundary_06_pytest_ini_wall_clock[files_narrowed]", "TESTREG", "blocked-by", "owned-by-later-ticket"),
    ("tests/registry/test_testreg_write_guard.py::test_boundary_06_pytest_ini_wall_clock[functions_narrowed]", "TESTREG", "blocked-by", "owned-by-later-ticket"),
    ("tests/registry/test_testreg_write_guard.py::test_boundary_06_pytest_ini_wall_clock[functions_superset]", "TESTREG", "blocked-by", "owned-by-later-ticket"),
    ("tests/registry/test_testreg_write_guard.py::test_boundary_06_pytest_ini_wall_clock[marker_added]", "TESTREG", "blocked-by", "owned-by-later-ticket"),
    ("tests/registry/test_testreg_write_guard.py::test_boundary_06_pytest_ini_wall_clock[testpaths_narrowed]", "TESTREG", "blocked-by", "owned-by-later-ticket"),
    ("tests/registry/test_testreg_write_guard.py::test_boundary_07_route_wall_clock_hook_and_precommit[catalog_trailing_newline]", "TESTREG", "blocked-by", "owned-by-later-ticket"),
    ("tests/registry/test_testreg_write_guard.py::test_boundary_07_route_wall_clock_hook_and_precommit[manifest_trailing_newline]", "TESTREG", "blocked-by", "owned-by-later-ticket"),
    ("tests/registry/test_testreg_write_guard.py::test_boundary_07_route_wall_clock_hook_and_precommit[test_file_comment]", "TESTREG", "blocked-by", "owned-by-later-ticket"),
    ("tests/registry/test_testreg_write_guard.py::test_boundary_07c_conftest_pytest_plugins_change_wall_clock[plugins_reordered]", "TESTREG", "blocked-by", "owned-by-later-ticket"),
    ("tests/registry/test_testreg_write_guard.py::test_boundary_07d_test_file_class_base_change_wall_clock", "TESTREG", "blocked-by", "owned-by-later-ticket"),
    ("tests/registry/test_testreg_write_guard.py::test_boundary_07e_plugin_fixture_change_wall_clock[assert_removed]", "TESTREG", "blocked-by", "owned-by-later-ticket"),
    ("tests/registry/test_testreg_write_guard.py::test_boundary_07e_plugin_fixture_change_wall_clock[comment_added]", "TESTREG", "blocked-by", "owned-by-later-ticket"),
    ("tests/registry/test_testreg_write_guard.py::test_boundary_07f_autouse_plugin_fixture_change_wall_clock[assert_added]", "TESTREG", "blocked-by", "owned-by-later-ticket"),
    ("tests/registry/test_testreg_write_guard.py::test_boundary_07f_autouse_plugin_fixture_change_wall_clock[assert_removed]", "TESTREG", "blocked-by", "owned-by-later-ticket"),
    ("tests/registry/test_testreg_write_guard.py::test_boundary_07f_autouse_plugin_fixture_change_wall_clock[assert_weakened]", "TESTREG", "blocked-by", "owned-by-later-ticket"),
    ("tests/registry/test_testreg_write_guard.py::test_boundary_07f_autouse_plugin_fixture_change_wall_clock[helper_assert_removed]", "TESTREG", "blocked-by", "owned-by-later-ticket"),
    ("tests/registry/test_testreg_write_guard.py::test_boundary_07g_widely_imported_helper_decrease_wall_clock", "TESTREG", "blocked-by", "owned-by-later-ticket"),
}


def _rows() -> list[dict]:
    return json.loads(ALLOWED.read_text(encoding="utf-8"))


def _ticket_names() -> set[str]:
    text = TICKET_ORDER.read_text(encoding="utf-8")
    names = set()
    for line in text.splitlines():
        # 列號含小寫子步（9a、9b、9a-1；2026-10-27 起）：原 `[0-9B]+` 認不得 ⇒ ICPERF／NOCAP／TESTSEL 被誤判不在排序表
        m = re.match(r"^\|\s*[0-9B][0-9A-Za-z-]*\s*\|\s*([A-Z][A-Z0-9-]*)", line)
        if m:
            names.add(m.group(1))
    return names | {"PRE-RED"}


def _collected(paths: list[str]) -> set[str]:
    # pytest.ini 之 addopts 含 -v 與匯入設定：不得以 -o addopts= 清除（conftest 會載入失敗）；以 -qq 抵銷 -v 取 node id
    r = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-qq", "-p", "no:cacheprovider", *paths],
                       cwd=REPO_ROOT, capture_output=True, text=True, check=False)
    return {ln.strip() for ln in r.stdout.splitlines() if "::" in ln}


def _problems(rows: list[dict]) -> list[str]:
    out: list[str] = []
    keys = [(r.get("node"), r.get("owner_ticket"), r.get("reason"), r.get("state")) for r in rows]
    if len(keys) != len(set(keys)) or len({k[0] for k in keys}) != len(keys):
        out.append("重複列或重複 node")
    if set(keys) != EXPECTED:
        out.append(f"集合不等：多 {sorted(set(keys) - EXPECTED)}；少 {sorted(EXPECTED - set(keys))}")
    tickets = _ticket_names()
    for r in rows:
        if r.get("reason") not in REASONS:
            out.append(f"reason 非封閉值：{r}")
        if r.get("state") not in STATES:
            out.append(f"state 非封閉值：{r}")
        if r.get("owner_ticket") not in tickets:
            out.append(f"owner_ticket 不在排序表：{r}")
        if not str(r.get("trigger") or "").strip():
            out.append(f"trigger 為空：{r}")
    files = sorted({str(r.get("node", "")).split("::", 1)[0] for r in rows})
    collected = _collected([f for f in files if (REPO_ROOT / f).is_file()])
    for r in rows:
        if r.get("node") not in collected:
            out.append(f"node 收集不到：{r.get('node')}")
    return out


def test_allowed_red_exact_set_and_collectable() -> None:
    assert _problems(_rows()) == []


def test_allowed_red_rejects_green_node_with_valid_metadata() -> None:
    """鑑別力：加入合法 metadata 之綠節點 ⇒ 集合不等。"""
    rows = _rows() + [{"node": "tests/api/test_batch_alias.py::test_patch_batch_alias_deleting_returns_409",
                       "owner_ticket": "FRAMEPATH", "reason": "user-ruling", "trigger": "x", "state": "owned-by-later-ticket"}]
    assert any(p.startswith("集合不等") for p in _problems(rows))


def test_allowed_red_rejects_empty_and_unknown_node() -> None:
    assert any(p.startswith("集合不等") for p in _problems([]))
    rows = _rows()
    rows[0] = {**rows[0], "node": rows[0]["node"] + "_no_such"}
    assert any(p.startswith("node 收集不到") for p in _problems(rows))


def test_allowed_red_rejects_fake_parametrize_id() -> None:
    rows = _rows()
    rows[0] = {**rows[0], "node": rows[0]["node"] + "[no-such-param]"}
    assert any(p.startswith("node 收集不到") for p in _problems(rows))
