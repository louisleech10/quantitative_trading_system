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

# 重凍（使用者 2026-10-03 核可）後之狀態：五支 pending 列已刪；多週期基準與 config_hash 釘值歸 F-2；
# 刪除舊特徵 run（使用者 2026-10-03 核可）所致之紅經 red census 實跑列入（收據 handoffs/run_receipts/20261003-prered-red-census.txt）
EXPECTED = {
    ("tests/feature_engineering/test_failopen_manifest.py::test_persist_false_generate_features_metadata", "FRAMEPATH", "user-ruling", "owned-by-later-ticket"),
    ("tests/feature_engineering/test_b6_warmup_trim.py::test_warmup_trim_ic_first", "ICFIRSTALIGN", "blocked-by", "owned-by-later-ticket"),
    ("tests/feature_engineering/test_b6_warmup_trim.py::test_warmup_trim_ic_first_public_window_init", "ICFIRSTALIGN", "blocked-by", "owned-by-later-ticket"),
    ("tests/feature_engineering/test_failopen_correctness.py::test_v3_multi_tf_btc_matches_frozen_baseline", "ICFIRSTALIGN", "blocked-by", "owned-by-later-ticket"),
    ("tests/feature_engineering/test_failopen_producer.py::test_quality_gate_max_ratios_do_not_change_config_hash", "ICFIRSTALIGN", "blocked-by", "owned-by-later-ticket"),
    ("tests/feature_engineering/test_failopen_correctness.py::test_v6_independent_asof_oracle_matches_multi_tf_columns", "ICFIRSTALIGN", "blocked-by", "owned-by-later-ticket"),
    ("tests/feature_engineering/test_failopen_correctness.py::test_v6_backend_output_matches_independent_oracle[False]", "ICFIRSTALIGN", "blocked-by", "owned-by-later-ticket"),
    ("tests/feature_engineering/test_failopen_correctness.py::test_v6_backend_output_matches_independent_oracle[True]", "ICFIRSTALIGN", "blocked-by", "owned-by-later-ticket"),
    ("tests/feature_engineering/test_failopen_correctness.py::test_v6_close_time_oracle_matches_pipeline[False]", "ICFIRSTALIGN", "blocked-by", "owned-by-later-ticket"),
    ("tests/feature_engineering/test_failopen_correctness.py::test_v6_close_time_oracle_matches_pipeline[True]", "ICFIRSTALIGN", "blocked-by", "owned-by-later-ticket"),
    ("tests/api/test_gap3_event_analysis_horizon_purge.py::test_event_analysis_d16_discloses_event_known_at_decision_values", "FFSTORE", "user-ruling", "owned-by-later-ticket"),
    ("tests/api/test_gap3_event_analysis_horizon_purge.py::test_event_analysis_horizon_purge_10i_prepare_called_once", "FFSTORE", "user-ruling", "owned-by-later-ticket"),
    ("tests/api/test_gap3_event_analysis_horizon_purge.py::test_event_analysis_horizon_purge_13_other_symbol_events_are_excluded_loudly", "FFSTORE", "user-ruling", "owned-by-later-ticket"),
    ("tests/api/test_gap3_event_analysis_horizon_purge.py::test_event_analysis_horizon_purge_r1_divergent_purge_is_fail_closed", "FFSTORE", "user-ruling", "owned-by-later-ticket"),
    ("tests/api/test_gap3_event_analysis_horizon_purge.py::test_event_analysis_horizon_purge_r1_duplicate_cutoff_is_loud", "FFSTORE", "user-ruling", "owned-by-later-ticket"),
    ("tests/api/test_gap3_event_analysis_horizon_purge.py::test_event_analysis_horizon_purge_timeframe_seconds_identity", "FFSTORE", "user-ruling", "owned-by-later-ticket"),
    ("tests/api/test_gap3_ic_progress_fields.py::test_gap3_ic_progress_fields_populated_for_implicit_latest_and_full_analysis", "FFSTORE", "user-ruling", "owned-by-later-ticket"),
    ("tests/api/test_gap3_ic_stop_gate.py::test_gap3_ic_feature_cap_covers_cross_sectional_runs", "FFSTORE", "user-ruling", "owned-by-later-ticket"),
    ("tests/api/test_gap3_ic_stop_gate.py::test_gap3_ic_feature_cap_features_path_can_be_identifier_not_file", "FFSTORE", "user-ruling", "owned-by-later-ticket"),
    ("tests/api/test_gap3_ic_stop_gate.py::test_gap3_ic_feature_cap_gate_and_service_share_one_registry_snapshot", "FFSTORE", "user-ruling", "owned-by-later-ticket"),
    ("tests/api/test_gap3_ic_stop_gate.py::test_gap3_ic_feature_cap_message_does_not_ask_for_impossible_action", "FFSTORE", "user-ruling", "owned-by-later-ticket"),
    ("tests/api/test_gap3_ic_stop_gate.py::test_gap3_ic_feature_cap_reason_comes_from_contract_not_hardcoded", "FFSTORE", "user-ruling", "owned-by-later-ticket"),
    ("tests/api/test_gap3_ic_stop_gate.py::test_gap3_ic_feature_cap_registry_lowball_is_caught_by_manifest", "FFSTORE", "user-ruling", "owned-by-later-ticket"),
    ("tests/api/test_gap3_ic_stop_gate.py::test_gap3_ic_feature_cap_rejects_big_run_without_creating_task", "FFSTORE", "user-ruling", "owned-by-later-ticket"),
    ("tests/api/test_gap3_ic_stop_gate.py::test_gap3_ic_stop_gate_alive_no_big_matrix_loaded", "FFSTORE", "user-ruling", "owned-by-later-ticket"),
    ("tests/api/test_gap3_scan_grid.py::test_scan_grid_cell_receives_its_own_embargo_override", "FFSTORE", "user-ruling", "owned-by-later-ticket"),
    ("tests/api/test_gap3_scan_grid.py::test_scan_grid_cell_summary_is_populated_from_real_shape", "FFSTORE", "user-ruling", "owned-by-later-ticket"),
    ("tests/api/test_gap3_scan_grid.py::test_scan_grid_cell_timeout_keeps_partial_results", "FFSTORE", "user-ruling", "owned-by-later-ticket"),
    ("tests/api/test_gap3_scan_grid.py::test_scan_grid_each_cell_gets_its_own_analyzer", "FFSTORE", "user-ruling", "owned-by-later-ticket"),
    ("tests/api/test_gap3_scan_grid.py::test_scan_grid_each_cell_has_its_own_receipt_hash", "FFSTORE", "user-ruling", "owned-by-later-ticket"),
    ("tests/api/test_gap3_scan_grid.py::test_scan_grid_infeasible_cell_is_unavailable_without_killing_others", "FFSTORE", "user-ruling", "owned-by-later-ticket"),
    ("tests/api/test_gap3_scan_grid.py::test_scan_grid_shape_is_exactly_nine_cells", "FFSTORE", "user-ruling", "owned-by-later-ticket"),
    ("tests/api/test_ic_analysis_service.py::test_append_cross_sectional_labels_kline_hole_becomes_nan_not_raise", "FFSTORE", "user-ruling", "owned-by-later-ticket"),
    ("tests/api/test_ic_analysis_service.py::test_append_cross_sectional_labels_mutation_rangeindex_regresses", "FFSTORE", "user-ruling", "owned-by-later-ticket"),
    ("tests/api/test_ic_analysis_service.py::test_append_cross_sectional_labels_real_3sym_oracle", "FFSTORE", "user-ruling", "owned-by-later-ticket"),
    ("tests/api/test_splitunify_event_scan_projection.py::test_required_real_data_present_or_fail_closed", "FFSTORE", "user-ruling", "owned-by-later-ticket"),
    ("tests/momentum/test_feature_library_config_hash.py::test_load_multi_without_config_hashes_byte_stable", "FFSTORE", "user-ruling", "owned-by-later-ticket"),
    ("tests/momentum/test_feature_library_config_hash.py::test_load_with_config_hash_disambig", "FFSTORE", "user-ruling", "owned-by-later-ticket"),
    ("tests/momentum/test_feature_library_config_hash.py::test_load_without_config_hash_matches_find_latest_materialized", "FFSTORE", "user-ruling", "owned-by-later-ticket"),
    ("tests/momentum/test_ic_cross_sectional_cut2.py::test_cross_sectional_e2e_real_path_append_and_analyze", "FFSTORE", "user-ruling", "owned-by-later-ticket"),
}


def _rows() -> list[dict]:
    return json.loads(ALLOWED.read_text(encoding="utf-8"))


def _ticket_names() -> set[str]:
    text = TICKET_ORDER.read_text(encoding="utf-8")
    names = set()
    for line in text.splitlines():
        m = re.match(r"^\|\s*[0-9B]+\s*\|\s*([A-Z][A-Z0-9-]*)", line)
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
