"""FRAMEPATH Task 1.1：CGSA 輸出改前／改後逐位元不變（docs/FRAMEPATH_SPEC.md §G、Task 1.1）。

基準＝`tests/_golden/framepath/cgsa_fingerprint.json`（`scripts/freeze_framepath_baseline.py freeze` 於 HEAD
6e07e0ad 凍結）。每格以同一 `run_cell` 重跑，`compare_cell` 逐項無容差比對；記憶體以 `memory_guard._Readings`
取樣、每格峰值 < 2 GB。真實 kline、單組串行（本檔各格依序執行，不得與其他重型生成並行）。

M1–M4 mutation（`feature_naming.tag_timeframe` 少標一週期、`_combine_layers` 對 `layer4_input` 回傳空表、L7 落盤前
改 float64、manifest 新增未登記鍵）於暫存工作樹實跑，收據 `handoffs/run_receipts/<date>-framepath-b1-mutation.txt`；
本檔之 `test_mutation_*` 驗比對器本身對該四類差異之鑑別力（不需生成）。
"""

from __future__ import annotations

import copy
import inspect
import json
import re
from pathlib import Path

import pytest

from momentum.FeatureEngineering.feature_storage import COMPLETENESS_FIELD_NAMES
from scripts import freeze_framepath_baseline as fb

REPO = Path(__file__).resolve().parents[2]
BASELINE = REPO / fb.BASELINE_REL


@pytest.fixture(scope="module")
def baseline():
    return json.loads(BASELINE.read_text(encoding="utf-8"))


def test_baseline_frozen_at_head_with_all_cells(baseline):
    assert baseline["head_commit"].startswith(fb.HEAD_COMMIT_PREFIX)
    assert tuple(baseline["cells"]) == fb.CELLS


@pytest.mark.parametrize("cell", fb.CELLS)
def test_cell_matches_frozen_baseline(baseline, tmp_path, cell):
    fresh = fb.run_cell(cell, tmp_path)
    assert fb.memory_gate_errors(cell, fresh["memory"]) == []
    assert fb.compare_cell(baseline["cells"][cell]["fingerprint"], fresh["fingerprint"]) == []


def test_boundary_01_resume_cell_equals_single_tf_cell(baseline):
    c1 = baseline["cells"]["C1"]["fingerprint"]
    c5 = baseline["cells"]["C5"]["fingerprint"]
    assert fb.compare_cell({k: v for k, v in c1.items() if k != "path_receipt"},
                           {k: v for k, v in c5.items() if k != "path_receipt"}) == []


def test_boundary_02_run_status_per_cell(baseline):
    for cell in fb.CELLS:
        fp = baseline["cells"][cell]["fingerprint"]
        if cell in fb.PARTIAL_CELLS:
            assert fp["run_status"] == "partial", cell
            secondary = baseline["cells"][cell]["receipt"]["dropped_timeframe"]
            failed = set(fp["completeness"].get("failed_timeframes", [])) | set(fp.get("skipped_timeframes", []))
            assert secondary in failed, cell
        else:
            assert fp["run_status"] == "complete", cell


def test_boundary_03_memory_gates_in_frozen_baseline(baseline):
    for cell in fb.CELLS:
        mem = baseline["cells"][cell]["memory"]
        assert fb.memory_gate_errors(cell, mem) == [], cell
        assert 0 < mem["peak_bytes"] < fb.PEAK_LIMIT_BYTES and mem["readings"] > 0 and mem["seconds"] > 0
    assert baseline["cells"]["C6"]["memory"]["non_root_member_seen"] is True


def test_boundary_04_c9_preconditions_recorded(baseline):
    receipt = baseline["cells"]["C9"]["receipt"]
    assert receipt["legacy_kline_dir"] and receipt["deleted_readback"] == "missing"


def test_boundary_05_compare_domain_rejects_forbidden_and_non_scalar(tmp_path):
    domain = json.loads((REPO / fb.COMPARE_DOMAIN_REL).read_text(encoding="utf-8"))
    for key in ("run_status", "quality_status", "failure_reasons", "config_hash", *COMPLETENESS_FIELD_NAMES):
        bad = copy.deepcopy(domain)
        bad["exclude"].append({"path": key, "category": "timestamp", "source": "t"})
        p = tmp_path / f"bad_{key}.json"
        p.write_text(json.dumps(bad), encoding="utf-8")
        with pytest.raises(fb.FramepathBaselineError):
            fb.load_compare_domain(p)
    bad = copy.deepcopy(domain)
    bad["exclude"].append({"path": "created_at", "category": "semantic", "source": "t"})
    p = tmp_path / "bad_cat.json"
    p.write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(fb.FramepathBaselineError):
        fb.load_compare_domain(p)
    ok = fb.load_compare_domain()
    with pytest.raises(fb.FramepathBaselineError):
        fb.filter_manifest({"created_at": {"nested": 1}}, ok)


def test_boundary_06_injected_readings_refused(monkeypatch, tmp_path):
    from momentum.FeatureEngineering import memory_guard

    monkeypatch.setenv(memory_guard.READINGS_ENV, str(tmp_path / "readings.jsonl"))
    with pytest.raises(fb.FramepathBaselineError):
        fb.run_cell("C1", tmp_path)


def test_boundary_07_comparator_has_no_timeframe_or_symbol_literals():
    src = inspect.getsource(fb.compare_cell) + inspect.getsource(fb.filter_manifest)
    assert not re.search(r"""["']\d+[mhdwM]["']""", src)
    assert not re.search(r"USDT|BTC|ETH", src)


def _synthetic_pair():
    fp = {k: None for k in fb.FINGERPRINT_KEYS}
    fp.update({"column_names_sha256": "a", "column_count": 2, "row_count": 3, "time_index_sha256": "t",
               "columns": {"x": {"nan": "n1", "inf": "i1", "values": "v1"}, "y": {"nan": "n2", "inf": "i2", "values": "v2"}},
               "stationarity_decisions_sha256": "d", "manifest_sha256": "m", "run_status": "complete",
               "completeness": {}, "failure_reasons": [], "path_receipt": {"l3": "streaming"}})
    return fp, copy.deepcopy(fp)


def test_mutation_compare_detects_value_mask_and_manifest_changes():
    base, fresh = _synthetic_pair()
    assert fb.compare_cell(base, fresh) == []
    for mutate in (
        lambda f: f["columns"]["x"].__setitem__("values", "v1-float64"),        # M3 類：值位元
        lambda f: f["columns"].pop("y"),                                         # M2 類：欄消失
        lambda f: f.__setitem__("column_names_sha256", "a-untagged"),            # M1 類：欄名
        lambda f: f.__setitem__("manifest_sha256", "m-extra-key"),               # M4 類：manifest
        lambda f: f["columns"]["y"].__setitem__("nan", "n2x"),
    ):
        changed = copy.deepcopy(fresh)
        mutate(changed)
        assert fb.compare_cell(base, changed) != []


def test_mutation_unregistered_manifest_key_changes_digest():
    domain = fb.load_compare_domain()
    manifest = {"run_status": "complete", "created_at": "2026-10-08T00:00:00", "updated_at": "x"}
    extra = dict(manifest, framepath_unregistered_key=1)
    assert fb.manifest_sha256(manifest, domain) != fb.manifest_sha256(extra, domain)
    later = dict(manifest, created_at="2027-01-01T00:00:00", updated_at="y")
    assert fb.manifest_sha256(manifest, domain) == fb.manifest_sha256(later, domain)
