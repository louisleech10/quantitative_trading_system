"""ICRESULT_PAGING（docs/ICRESULT_PAGING_SPEC.md）測試：Task 0.1 contract／golden／gate parser（B0）；B1 端點測試於同檔續增。

golden：tests/golden/icresult_paging/{fixture_report,full_report_projection,shape_fixture}.json
探針：handoffs/20260909-probe-icresult-golden.py（參考實作，B1 模組須與之逐值相等）
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
GOLDEN_DIR = REPO / "tests/golden/icresult_paging"
CONTRACT = REPO / "momentum/Analysis/contracts/ic_result_paging_contract.json"
GATE = REPO / "scripts/icresult_paging_phase_gate.sh"

# SPEC §A receipt：前端＋後端讀取之 metadata 鍵（必須 ⊆ keep_keys）
CONSUMED_META_KEYS = {
    "event_filter", "oos_downgrade", "isolation", "ic_window_disclosure", "period_alignment",
    "ic_train_test_split", "n_timestamps", "n_symbols", "mode", "survivor_output", "compute_warnings",
    "selection_scope", "symbol", "timeframe", "config_hash",
}


def _probe():
    spec = importlib.util.spec_from_file_location("icresult_golden_probe", REPO / "handoffs/20260909-probe-icresult-golden.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def contract() -> dict:
    from api.models.ic_models import load_ic_result_paging_contract

    return load_ic_result_paging_contract()


@pytest.fixture(scope="module")
def golden() -> dict:
    return json.loads((GOLDEN_DIR / "full_report_projection.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def fixture_report() -> dict:
    return json.loads((GOLDEN_DIR / "fixture_report.json").read_text(encoding="utf-8"))


# ── Task 0.1：contract ─────────────────────────────────────────────────────────
def test_contract_is_single_source_and_well_formed(contract):
    raw = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert contract == raw
    assert len(contract["sort_fields"]) >= 5 and {"icir", "ic_mean", "p_value", "feature_name"} <= set(contract["sort_fields"])
    assert contract["sort_order_values"] == ["asc", "desc"]
    assert len(contract["drop_sections"]) == 7 and "rolling_ic_series" in contract["drop_sections"] and "grouped_ic" in contract["drop_sections"]
    assert set(contract["per_feature_sections"]) == set(contract["drop_sections"]) - {"summary_table"}
    assert contract["limit_default"] == 50 and contract["limit_max"] == 500
    assert [p["path"] for p in contract["collection_to_count_paths"]] == [["filter_log", "*"], ["metadata", "selection_scope"]]
    assert contract["funnel_stage_adapter"]["dict_count_key"] == "count"


def test_metadata_keep_keys_cover_consumers_and_exclude_feature_names(contract, fixture_report):
    keep = set(contract["metadata_keep_keys"])
    assert CONSUMED_META_KEYS <= keep, CONSUMED_META_KEYS - keep
    names = {r["feature_name"] for r in fixture_report["summary_table"]}
    assert keep & names == set()
    # fixture metadata 中的 per-feature 描述子必不在白名單（IP-RESID-1 之污染不得進 light）
    descriptors = {k for k, v in fixture_report["metadata"].items() if isinstance(v, dict) and set(v) == {"category", "layer", "name"}}
    assert descriptors & keep == set()


# ── Task 0.1：golden 自證 ────────────────────────────────────────────────────
def test_golden_matches_live_default_result_and_projection_reference(golden, fixture_report, contract):
    """G-1 前置：fixture 載入 fake task → 預設 /result raw body sha == golden；其餘投影欄位由參考實作重算相等。"""
    import hashlib

    probe = _probe()
    body = probe.default_result_bytes(fixture_report)
    assert hashlib.sha256(body).hexdigest() == golden["raw_body_sha256"]
    live = probe.build_golden(json.loads(body), golden["raw_body_sha256"], contract)
    for k in golden:
        assert live[k] == golden[k], k


def test_sort_golden_semantics(golden):
    """G-6：缺值兩向沉底、並列以名升冪（SPEC §C-8）。"""
    sg = golden["sort_golden"]
    assert sg["four_desc"] == ["A", "B", "C", "D"] and sg["four_asc"] == ["A", "B", "C", "D"]
    assert sg["three_desc"] == ["B", "A", "C"] and sg["three_asc"] == ["A", "B", "C"]
    assert len(sg["icir_desc_top5"]) == 5


def test_funnel_shape_fixture_matches_expected(golden):
    """G-8：六 stage 全鎖；stage5 dict 含 count=0 ⇒ 0（非 len=2）；stage3／stage1 皆 null。"""
    assert golden["shape_funnel"] == golden["shape_expected_funnel"]
    assert golden["shape_funnel"]["stage5_thresholds"] == {"input": 39346, "output": 0}
    assert golden["shape_funnel"]["stage3_event_filter"] == {"input": None, "output": None}
    assert set(golden["shape_funnel"]) == {"stage0_ingestion", "stage1_preprocessing", "stage3_event_filter", "feature_filter", "stage5_thresholds", "stage6_redundancy"}


def test_collections_to_counts_does_not_mutate_source(fixture_report, contract):
    """R6 U2：計數只作用於私有副本，source 原始集合鍵仍在。"""
    import copy

    probe = _probe()
    before = copy.deepcopy(fixture_report)
    light_fl = probe.apply_count_paths(fixture_report, contract)["filter_log"]
    assert fixture_report == before
    for stage, node in fixture_report["filter_log"].items():
        for k, v in node.items():
            if isinstance(v, (list, dict)):
                assert f"{k}_count" in light_fl[stage] and k not in light_fl[stage]


# ── Task 0.1：phase gate parser（三態文法）──────────────────────────────────────
@pytest.mark.parametrize(
    "content,require_pass,expected_rc",
    [
        ("SIZE_GATE=PASS\nSIZE_REASON=measured\n", 0, 0),
        ("SIZE_GATE=BLOCKED\nSIZE_REASON=artifact missing\n", 0, 0),
        ("SIZE_GATE=BLOCKED\n", 1, 1),
        ("SIZE_GATE=FAIL\n", 0, 1),
        ("SIZE_REASON=x\n", 0, 1),
        ("SIZE_GATE=PASS\nSIZE_GATE=PASS\n", 0, 1),
        ("SIZE_GATE=MAYBE\n", 0, 1),
    ],
)
def test_phase_gate_parser(tmp_path: Path, content: str, require_pass: int, expected_rc: int):
    f = tmp_path / "out.txt"
    f.write_text(content, encoding="utf-8")
    cmd = ["bash", str(GATE), "--parse", "SIZE_GATE", str(f)] + (["--require-pass"] if require_pass else [])
    rc = subprocess.run(cmd, cwd=str(REPO), capture_output=True, text=True).returncode
    assert rc == expected_rc


def test_size_probe_emits_single_token_line():
    """B0：投影模組尚不存在 ⇒ 恰一行 SIZE_GATE=BLOCKED，rc=2（唯一文法）。"""
    out = subprocess.run([sys.executable, str(REPO / "handoffs/20260909-probe-icresult-size.py")], cwd=str(REPO), capture_output=True, text=True)
    lines = [ln for ln in out.stdout.splitlines() if ln.startswith("SIZE_GATE=")]
    assert len(lines) == 1 and lines[0].split("=")[1] in {"PASS", "FAIL", "BLOCKED"}
    assert out.returncode == {"PASS": 0, "FAIL": 1, "BLOCKED": 2}[lines[0].split("=")[1]]
