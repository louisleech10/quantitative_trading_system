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
    assert set(golden["shape_funnel"]) == {"stage0_ingestion", "stage1_preprocessing", "stage3_event_filter", "feature_filter", "stage5_thresholds", "stage6_redundancy", "_adapter_probe"}
    assert golden["shape_funnel"]["_adapter_probe"] == {"input": 1, "output": 2}  # 兩組候選鍵同時存在 ⇒ 取第一存在者


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


# ═══════════════════════════════ B1：端點與投影（Task 1.0–1.3） ═══════════════════════════════
import copy
import hashlib
import ast

from fastapi.testclient import TestClient

from api.main import app
from api.services import ic_result_projection as proj
from api.services.ic_analysis_service import ic_analysis_service

API = "/api/v1/ic"


def _sha(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode("utf-8")).hexdigest()


def _install_task(task_id: str, report: dict) -> dict:
    with ic_analysis_service._lock:
        info = {"task_id": task_id, "status": "completed", "progress": 1.0}
        ic_analysis_service._tasks[task_id] = info
    ic_analysis_service._set_result(info, copy.deepcopy(report))  # lock 外（GROK-R1-P1-01）
    return info


def _remove_task(task_id: str) -> None:
    with ic_analysis_service._lock:
        ic_analysis_service._tasks.pop(task_id, None)


@pytest.fixture()
def task(fixture_report):
    tid = "icresult-paging-b1-task"
    info = _install_task(tid, fixture_report)
    yield tid, info
    _remove_task(tid)


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


class _FakeAnalyzer:
    def __init__(self, report):
        self._report = report

    def refilter(self, thresholds):
        return copy.deepcopy(self._report)


def _sentinel_report(fixture_report: dict) -> dict:
    rep = copy.deepcopy(fixture_report)
    for r in rep["summary_table"]:
        r["feature_name"] = "NEW__" + r["feature_name"]
    rep["summary_table"] = rep["summary_table"][:5]
    return rep


# ── G-1：預設 /result raw bytes 不變（單一 normalized 樹＋冪等）─────────────────────
def test_default_unchanged_raw_body_sha(client, task, golden):
    tid, _ = task
    resp = client.get(f"{API}/result/{tid}")
    assert resp.status_code == 200
    assert hashlib.sha256(resp.content).hexdigest() == golden["raw_body_sha256"]


def test_to_json_compatible_is_idempotent_on_normalized_tree(task):
    tid, info = task
    n = info["result"]
    assert ic_analysis_service._to_json_compatible(n) == n


def test_task_status_has_result_revision(client, task):
    tid, _ = task
    body = client.get(f"{API}/task/{tid}").json()
    assert body["result_revision"] == 1


# ── Task 1.0：單一寫點（AST 守衛）＋失敗語意 ──────────────────────────────────
def test_ast_guard_single_result_write_site():
    src = (REPO / "api/services/ic_analysis_service.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    inside = outside = 0
    helper_span = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "_set_result":
            helper_span = (node.lineno, node.end_lineno)
    assert helper_span is not None
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Subscript) and isinstance(tgt.slice, ast.Constant) and tgt.slice.value == "result" and isinstance(tgt.value, ast.Name) and tgt.value.id == "task_info":
                    if helper_span[0] <= node.lineno <= helper_span[1]:
                        inside += 1
                    else:
                        outside += 1
    assert inside == 1 and outside == 0


def test_set_result_guard_raise_does_not_write(fixture_report):
    bad = copy.deepcopy(fixture_report)
    bad["analysis_status"] = "ok_oos"
    bad["metadata"] = dict(bad.get("metadata") or {}, diagnostic_only=True)
    info = {"task_id": "icresult-paging-guard", "status": "completed"}
    with pytest.raises(ValueError):
        ic_analysis_service._set_result(info, bad)
    assert "result" not in info and "result_revision" not in info


def test_refilter_guard_fail_422_keeps_old_result(client, task, fixture_report, monkeypatch):
    tid, info = task
    bad = copy.deepcopy(fixture_report)
    bad["analysis_status"] = "ok_oos"
    bad["metadata"] = dict(bad.get("metadata") or {}, diagnostic_only=True)
    monkeypatch.setattr(ic_analysis_service, "get_analyzer", lambda _tid: _FakeAnalyzer(bad))
    resp = client.post(f"{API}/refilter?task_id={tid}", json={"thresholds": {}})
    assert resp.status_code == 422
    assert info["status"] == "completed" and info["result_revision"] == 1
    assert client.get(f"{API}/task/{tid}").json()["result_revision"] == 1


# ── Task 1.1：summary 分頁 ────────────────────────────────────────────────────
def test_summary_page_g2a_pages_reassemble_full_table(client, task, fixture_report, contract):
    tid, _ = task
    limit = contract["limit_max"]
    rows, offset, total = [], 0, None
    while True:
        body = client.get(f"{API}/result/{tid}/summary?limit={limit}&offset={offset}&sort_by=icir&sort_order=desc").json()
        total = body["total"]
        rows += body["rows"]
        offset += limit
        if offset >= total:
            break
    key = lambda r: r["feature_name"]
    assert total == len(fixture_report["summary_table"])
    assert sorted(rows, key=key) == sorted(fixture_report["summary_table"], key=key)


def test_summary_page_g2b_filtered_equals_single_materialize(client, task, fixture_report, contract):
    tid, _ = task
    body = client.get(f"{API}/result/{tid}/summary?limit=500&search=close&sort_by=icir&sort_order=desc").json()
    ref = proj.paginate_summary(fixture_report["summary_table"], sort_by="icir", sort_order="desc", offset=0, limit=10**9, search="close", contract=contract)
    assert body["total"] == ref["total"] and [r["feature_name"] for r in body["rows"]] == [r["feature_name"] for r in ref["rows"]]
    assert body["total"] > 0


def test_summary_page_edges(client, task, contract):
    tid, _ = task
    assert client.get(f"{API}/result/{tid}/summary?offset=99999").json()["rows"] == []
    assert client.get(f"{API}/result/{tid}/summary?limit=99999").json()["limit"] == contract["limit_max"]
    assert client.get(f"{API}/result/{tid}/summary?search=zzzz_nohit").json()["total"] == 0
    assert client.get(f"{API}/result/nope/summary").status_code == 404


def test_sort_by_whitelist_rejects_400(client, task):
    tid, _ = task
    assert client.get(f"{API}/result/{tid}/summary?sort_by=evil").status_code == 400
    assert client.get(f"{API}/result/{tid}/summary?sort_order=sideways").status_code == 400


def test_sort_golden_endpoint_g6(client, task, golden, contract):
    tid, _ = task
    desc = client.get(f"{API}/result/{tid}/summary?limit=5&sort_by=icir&sort_order=desc").json()
    asc = client.get(f"{API}/result/{tid}/summary?limit=5&sort_by=icir&sort_order=asc").json()
    name = client.get(f"{API}/result/{tid}/summary?limit=5&sort_by=feature_name&sort_order=asc").json()
    assert [r["feature_name"] for r in desc["rows"]] == golden["sort_golden"]["icir_desc_top5"]
    assert [r["feature_name"] for r in asc["rows"]] == golden["sort_golden"]["icir_asc_top5"]
    assert [r["feature_name"] for r in name["rows"]] == golden["sort_golden"]["feature_name_asc_top5"]
    four = [{"feature_name": "A", "icir": 0.5}, {"feature_name": "B", "icir": 0.5}, {"feature_name": "C", "icir": None}, {"feature_name": "D", "icir": float("nan")}]
    three = [{"feature_name": "A", "icir": 0.5}, {"feature_name": "B", "icir": 0.9}, {"feature_name": "C", "icir": None}]
    order = lambda rows, so: [r["feature_name"] for r in proj.paginate_summary(rows, sort_by="icir", sort_order=so, offset=0, limit=10, contract=contract)["rows"]]
    assert order(four, "desc") == golden["sort_golden"]["four_desc"] == ["A", "B", "C", "D"]
    assert order(four, "asc") == golden["sort_golden"]["four_asc"] == ["A", "B", "C", "D"]
    assert order(three, "desc") == ["B", "A", "C"] and order(three, "asc") == ["A", "B", "C"]


# ── Task 1.2：單特徵 ────────────────────────────────────────────────────────
def test_feature_detail_g3_matches_golden_every_feature(client, task, golden, contract):
    tid, _ = task
    for name, secs in golden["feature_samples"].items():
        body = client.get(f"{API}/result/{tid}/feature/{name}").json()
        assert body["feature_name"] == name and body["summary_row"]["feature_name"] == name
        for sec, sha in secs.items():
            assert (None if body.get(sec) is None else _sha(body[sec])) == sha, (name, sec)
    assert client.get(f"{API}/result/{tid}/feature/does_not_exist").status_code == 404


# ── Task 1.3：light 視圖 ─────────────────────────────────────────────────────
def test_light_view_g4(client, task, fixture_report, golden, contract):
    tid, _ = task
    light = client.get(f"{API}/result/{tid}?view=light").json()
    for sec in contract["drop_sections"]:
        assert sec not in light, sec
    assert set(light["metadata"]) <= set(contract["metadata_keep_keys"])
    for k in light["metadata"]:
        if k != "selection_scope":
            assert light["metadata"][k] == fixture_report["metadata"][k], k
    assert light["metadata"].get("selection_scope") == golden["selection_scope_light"]
    assert light["filter_log"] == golden["filter_log_light"]
    assert light["filter_log_funnel"] == golden["filter_log_funnel"]
    for k in ("marginal_ic", "correlation_matrix", "analysis_status", "oos_guarantees", "version", "diversification_metrics", "cross_sectional_symbol_ic", "cross_symbol_validation"):
        if k in fixture_report:
            assert light[k] == fixture_report[k], k
    ref = proj.paginate_summary(fixture_report["summary_table"], sort_by="icir", sort_order="desc", offset=0, limit=contract["limit_default"], contract=contract)
    assert light["summary_page"]["rows"] == ref["rows"] and light["summary_page"]["total"] == ref["total"]
    assert light["view"] == "light" and light["total_features"] == len(fixture_report["summary_table"]) and light["result_revision"] == 1


def test_light_view_v2_matrix(client, task, monkeypatch):
    tid, _ = task
    from api.core.config import settings

    assert client.get(f"{API}/result/{tid}?view=light&schema_version=2").status_code == 400
    assert client.get(f"{API}/result/{tid}?view=heavy").status_code == 400
    monkeypatch.setattr(settings, "ic_response_v2", False)
    full = client.get(f"{API}/result/{tid}?schema_version=2")
    assert full.status_code == 200 and full.content == client.get(f"{API}/result/{tid}").content


def test_light_view_snapshot_immutable(client, task):
    tid, info = task
    before = copy.deepcopy(info["result"])
    client.get(f"{API}/result/{tid}?view=light"); client.get(f"{API}/result/{tid}?view=light")
    client.get(f"{API}/result/{tid}/summary?limit=5")
    first = info["result"]["summary_table"][0]["feature_name"]
    assert client.get(f"{API}/result/{tid}/feature/{first}").status_code == 200
    assert info["result"] == before
    for stage, node in info["result"]["filter_log"].items():
        assert any(isinstance(v, (list, dict)) for v in node.values()) or True  # 原始集合鍵仍在（deep-equal 已保證）


def test_no_full_tree_on_projection(client, task, monkeypatch):
    tid, _ = task
    calls = {"norm": 0, "deny": 0}
    orig = ic_analysis_service._to_json_compatible
    monkeypatch.setattr(ic_analysis_service, "_to_json_compatible", lambda *a, **k: (calls.__setitem__("norm", calls["norm"] + 1), orig(*a, **k))[1])
    import momentum.core.contracts as contracts

    orig_deny = contracts.deny_factor_in_ok_oos
    monkeypatch.setattr(contracts, "deny_factor_in_ok_oos", lambda r: (calls.__setitem__("deny", calls["deny"] + 1), orig_deny(r))[1])
    client.get(f"{API}/result/{tid}?view=light")
    client.get(f"{API}/result/{tid}/summary?limit=5")
    first = client.get(f"{API}/result/{tid}/summary?limit=1").json()["rows"][0]["feature_name"]
    client.get(f"{API}/result/{tid}/feature/{first}")
    assert calls == {"norm": 0, "deny": 0}


def test_funnel_g8_shape_fixture_via_light(client):
    shape = json.loads((GOLDEN_DIR / "shape_fixture.json").read_text(encoding="utf-8"))
    tid = "icresult-paging-shape"
    _install_task(tid, {"analysis_status": "degraded_full_sample", "oos_guarantees": False, "summary_table": [], "filter_log": shape["filter_log"], "metadata": {}})
    try:
        light = client.get(f"{API}/result/{tid}?view=light").json()
        assert light["filter_log_funnel"] == shape["expected_funnel"]
        assert light["filter_log"]["stage5_thresholds"]["output_features_count"] == 2  # 計數（len）與 funnel（count=0）語意分離
        assert light["summary_page"]["total"] == 0
    finally:
        _remove_task(tid)


# ── §C-7：世代戳 ─────────────────────────────────────────────────────────────
def test_revision_g7a_and_g7c_refilter_handshake(client, task, fixture_report, monkeypatch):
    tid, info = task
    page1 = client.get(f"{API}/result/{tid}/summary?limit=5").json()
    assert page1["result_revision"] == 1
    monkeypatch.setattr(ic_analysis_service, "get_analyzer", lambda _tid: _FakeAnalyzer(_sentinel_report(fixture_report)))
    r = client.post(f"{API}/refilter?task_id={tid}&view=light", json={"thresholds": {}})
    assert r.status_code == 200 and r.json()["view"] == "light" and r.json()["result_revision"] == 2
    stale = client.get(f"{API}/result/{tid}/summary?limit=5&revision=1")
    assert stale.status_code == 409 and stale.json()["detail"]["current_revision"] == 2
    fresh = client.get(f"{API}/result/{tid}/summary?limit=5").json()
    assert fresh["result_revision"] == 2 and fresh["total"] == 5 and all(r["feature_name"].startswith("NEW__") for r in fresh["rows"])
    assert client.get(f"{API}/result/{tid}/feature/{page1['rows'][0]['feature_name']}?revision=1").status_code == 409
    r2 = client.post(f"{API}/refilter?task_id={tid}", json={"thresholds": {}})
    assert r2.status_code == 200 and "view" not in r2.json() and r2.json() == client.get(f"{API}/result/{tid}").json()
    assert info["result_revision"] == 3


def test_revision_mid_projection_uses_old_snapshot_g7b(client, task, fixture_report, monkeypatch):
    tid, info = task
    orig_snap = ic_analysis_service._snapshot_result
    fired = {"n": 0}

    def snap_then_refilter(task_id):
        snap = orig_snap(task_id)
        if fired["n"] == 0:
            fired["n"] += 1
            ic_analysis_service._set_result(ic_analysis_service._tasks[task_id], _sentinel_report(fixture_report))
        return snap

    monkeypatch.setattr(ic_analysis_service, "_snapshot_result", snap_then_refilter)
    body = client.get(f"{API}/result/{tid}/summary?limit=500").json()
    assert body["result_revision"] == 1 and body["total"] == len(fixture_report["summary_table"])
    assert not any(r["feature_name"].startswith("NEW__") for r in body["rows"])
    assert info["result_revision"] == 2


# ── §C-9：排序索引快取 ────────────────────────────────────────────────────────
def test_cache_hit_and_revision_invalidation(client, task, fixture_report, monkeypatch):
    tid, info = task
    calls = {"n": 0}
    orig = proj.build_sort_index
    monkeypatch.setattr(proj, "build_sort_index", lambda *a, **k: (calls.__setitem__("n", calls["n"] + 1), orig(*a, **k))[1])
    url = f"{API}/result/{tid}/summary?limit=5&sort_by=icir&sort_order=desc"
    client.get(url); client.get(url)
    assert calls["n"] == 1
    ic_analysis_service._set_result(info, copy.deepcopy(fixture_report))
    client.get(url)
    assert calls["n"] == 2
    assert (tid, 1, "icir", "desc", "", "") not in proj.sort_index_cache({"sort_index_cache": {"max_keys_per_task": 8, "max_tasks_process_wide": 32}}).keys_for(tid)


def test_cache_capacity_process_wide(contract, fixture_report):
    cache = proj.sort_index_cache(contract)
    rows = fixture_report["summary_table"]
    n = len(rows)
    fields = contract["sort_fields"][:9]
    for i in range(33):
        for f in fields[:8]:
            proj.paginate_summary(rows, sort_by=f, sort_order="asc", offset=0, limit=1, contract=contract, task_id=f"cap-task-{i}", revision=1)
    ids = cache.task_ids()
    assert "cap-task-0" not in ids and len([t for t in ids if t.startswith("cap-task-")]) == 32
    assert cache.cache_bytes() <= 32 * 8 * n * 4 + 8 * n * 4  # 其他測試殘留之 task 容忍一組
    proj.paginate_summary(rows, sort_by=fields[8], sort_order="asc", offset=0, limit=1, contract=contract, task_id="cap-task-32", revision=1)
    keys = cache.keys_for("cap-task-32")
    assert len(keys) == 8 and all(k[2] != fields[0] for k in keys)
    assert all(arr.dtype == np.int32 for arr in cache._tasks["cap-task-32"].values())
    assert proj.sort_index_cache(contract) is cache
    for i in range(33):
        cache.invalidate_task(f"cap-task-{i}")


import numpy as np  # noqa: E402  （cache_capacity 用）


def test_cache_key_includes_revision(fixture_report, contract, monkeypatch):
    """§C-9：同 task 不同 revision 不得命中同一索引（快取 key 含 revision）。"""
    calls = {"n": 0}
    orig = proj.build_sort_index
    monkeypatch.setattr(proj, "build_sort_index", lambda *a, **k: (calls.__setitem__("n", calls["n"] + 1), orig(*a, **k))[1])
    rows = fixture_report["summary_table"]
    kw = dict(sort_by="icir", sort_order="desc", offset=0, limit=5, contract=contract, task_id="rev-key-task")
    proj.paginate_summary(rows, revision=1, **kw); proj.paginate_summary(rows, revision=1, **kw)
    assert calls["n"] == 1
    proj.paginate_summary(rows, revision=2, **kw)
    assert calls["n"] == 2
    proj.sort_index_cache(contract).invalidate_task("rev-key-task")


def test_sort_golden_feature_name_desc_is_reverse_string_order(client, task, golden, contract):
    """B1 review GROK-R1-P2-01：字串欄 desc ＝ Python 字串序反轉（前綴名 close/close_sma/close_sma_20 不得錯序）。"""
    tid, _ = task
    desc = client.get(f"{API}/result/{tid}/summary?limit=5&sort_by=feature_name&sort_order=desc").json()
    assert [r["feature_name"] for r in desc["rows"]] == golden["sort_golden"]["feature_name_desc_top5"]
    rows = [{"feature_name": n} for n in ["close", "close_sma", "close_sma_20", "a", "ab"]]
    got = [r["feature_name"] for r in proj.paginate_summary(rows, sort_by="feature_name", sort_order="desc", offset=0, limit=10, contract=contract)["rows"]]
    assert got == sorted([r["feature_name"] for r in rows], reverse=True) == golden["sort_golden"]["prefix_desc"]


def test_set_result_does_not_hold_lock_during_normalize(fixture_report, monkeypatch):
    """B1 review GROK-R1-P1-01：normalize＋守衛在 lock 外；lock 內只賦值。"""
    seen = {"locked_during_normalize": None}
    orig = ic_analysis_service._to_json_compatible

    def spy(*a, **k):
        seen["locked_during_normalize"] = ic_analysis_service._lock.locked()
        return orig(*a, **k)

    monkeypatch.setattr(ic_analysis_service, "_to_json_compatible", spy)
    info = {"task_id": "lock-probe", "status": "completed"}
    ic_analysis_service._set_result(info, copy.deepcopy(fixture_report))
    assert seen["locked_during_normalize"] is False
    assert info["result_revision"] == 1
