#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ICRESULT_PAGING Task 0.1：改前投影 golden（SPEC §G）。

    venv/bin/python handoffs/20260909-probe-icresult-golden.py --write   # 產 fixture_report.json＋full_report_projection.json
    venv/bin/python handoffs/20260909-probe-icresult-golden.py --check   # 重算並比對（rc=0 相同）

golden 內容（全部由「預設 GET /result/{id} 之 JSON body」推導，不抽樣）：
  raw_body_sha256      ：fixture_report.json 載入 fake task 後，TestClient GET /result/{id} 之 response.content sha256（G-1）
  report_canonical_sha ：ichc_run.canonical_sha(body)（輔助）
  summary_rows／feature_set_sha256／section_key_sha256／feature_samples{name:{段:sha}}（G-2／G-3）
  sort_golden          ：contract sort_policy comparator 產生（G-6）——icir desc／asc 首 5 列＋4 列並列 fixture＋3 列 fixture
  filter_log_light／filter_log_funnel（fixture）＋shape_funnel（shape_fixture）（G-4c／G-8）
本檔的 comparator／投影純函式是 contract 的參考實作；B1 的 api/services/ic_result_projection.py 須與之逐值相等（測試鎖）。
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
GOLDEN_DIR = REPO / "tests/golden/icresult_paging"
FIXTURE_REPORT = GOLDEN_DIR / "fixture_report.json"
GOLDEN = GOLDEN_DIR / "full_report_projection.json"
SHAPE = GOLDEN_DIR / "shape_fixture.json"
FAKE_TASK_ID = "icresult-paging-golden-fixture"


def _sha(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode("utf-8")).hexdigest()


# ── contract 參考實作（B1 模組須與此逐值相等）───────────────────────────────────
def _missing(v: Any) -> bool:
    if v is None or isinstance(v, bool):
        return True
    if isinstance(v, (int, float)):
        return not math.isfinite(float(v))
    return True  # 非數值一律視為缺值（sort_policy.missing_definition）


def sort_key(row: Dict[str, Any], field: str, sort_order: str, contract: Dict[str, Any]) -> Tuple:
    name = str(row.get("feature_name", ""))
    if field in contract["sort_policy"]["string_fields"]:
        return (0, name, name)
    v = row.get(field)
    if _missing(v):
        return (1, 0.0, name)  # 兩向沉底
    f = float(v)
    return (0, f if sort_order == "asc" else -f, name)


def sort_rows(rows: List[Dict[str, Any]], field: str, sort_order: str, contract: Dict[str, Any]) -> List[Dict[str, Any]]:
    if field in contract["sort_policy"]["string_fields"]:
        return sorted(rows, key=lambda r: str(r.get("feature_name", "")), reverse=(sort_order == "desc"))
    return sorted(rows, key=lambda r: sort_key(r, field, sort_order, contract))


def collections_to_counts(node: Any) -> Any:
    """對目標 dict 節點之私有副本：直接子鍵 list／dict → `<key>_count`；標量原樣；非 dict ⇒ 原樣。"""
    if not isinstance(node, dict):
        return node
    out: Dict[str, Any] = {}
    for k, v in node.items():
        if isinstance(v, (list, dict)):
            out[f"{k}_count"] = len(v)
        else:
            out[k] = v
    return out


def apply_count_paths(report: Dict[str, Any], contract: Dict[str, Any]) -> Dict[str, Any]:
    """依 contract.collection_to_count_paths 回傳「僅受影響節點被替換」的新頂層 dict；source 不動。"""
    out = dict(report)
    for spec in contract["collection_to_count_paths"]:
        path = spec["path"]
        if len(path) == 2 and path[1] == "*":
            parent = out.get(path[0])
            if isinstance(parent, dict):
                out[path[0]] = {k: collections_to_counts(v) for k, v in parent.items()}
        elif len(path) == 2:
            parent = out.get(path[0])
            if isinstance(parent, dict) and isinstance(parent.get(path[1]), dict):
                new_parent = dict(parent)
                new_parent[path[1]] = collections_to_counts(parent[path[1]])
                out[path[0]] = new_parent
    return out


def _funnel_value(stage: Dict[str, Any], keys: List[str], count_key: str) -> Optional[int]:
    for k in keys:
        if k in stage:
            v = stage[k]
            if isinstance(v, bool):
                return None
            if isinstance(v, int):
                return v
            if isinstance(v, dict):
                if count_key in v and isinstance(v[count_key], int):
                    return int(v[count_key])
                return len(v)
            if isinstance(v, list):
                return len(v)
            return None
    return None


def funnel_from_filter_log(filter_log: Any, adapter: Dict[str, Any]) -> Dict[str, Dict[str, Optional[int]]]:
    if not isinstance(filter_log, dict):
        return {}
    out: Dict[str, Dict[str, Optional[int]]] = {}
    for stage, node in filter_log.items():
        if not isinstance(node, dict):
            out[stage] = {"input": None, "output": None}
            continue
        out[stage] = {
            "input": _funnel_value(node, adapter["input_keys"], adapter["dict_count_key"]),
            "output": _funnel_value(node, adapter["output_keys"], adapter["dict_count_key"]),
        }
    return out


# ── golden 產生 ───────────────────────────────────────────────────────────────
def _fake_task(client_report: Any):
    from api.services.ic_analysis_service import ic_analysis_service

    with ic_analysis_service._lock:
        prev = ic_analysis_service._tasks.get(FAKE_TASK_ID)
        ic_analysis_service._tasks[FAKE_TASK_ID] = {"status": "completed", "progress": 1.0, "result": client_report}
    return prev


def _restore(prev):
    from api.services.ic_analysis_service import ic_analysis_service

    with ic_analysis_service._lock:
        if prev is None:
            ic_analysis_service._tasks.pop(FAKE_TASK_ID, None)
        else:
            ic_analysis_service._tasks[FAKE_TASK_ID] = prev


def default_result_bytes(result_obj: Any) -> bytes:
    from fastapi.testclient import TestClient
    from api.main import app

    prev = _fake_task(result_obj)
    try:
        with TestClient(app) as client:
            resp = client.get(f"/api/v1/ic/result/{FAKE_TASK_ID}")
            assert resp.status_code == 200, resp.status_code
            return resp.content
    finally:
        _restore(prev)


def build_golden(body: Dict[str, Any], raw_sha: str, contract: Dict[str, Any]) -> Dict[str, Any]:
    from tests.momentum.helpers.ichc_run import canonical_sha

    rows = body["summary_table"]
    names = sorted(r["feature_name"] for r in rows)
    sections = {k: (sorted(v.keys()) if isinstance(v, dict) else None) for k, v in body.items()}
    feature_samples = {}
    for n in names:
        feature_samples[n] = {}
        for sec in contract["per_feature_sections"]:
            node = body.get(sec)
            if isinstance(node, dict) and n in node:
                feature_samples[n][sec] = _sha(node[n])
            elif sec == "grouped_ic" and isinstance(node, dict):
                feature_samples[n][sec] = _sha({
                    kind: ({label: (inner.get(n) if isinstance(inner, dict) else None) for label, inner in labels.items()} if isinstance(labels, dict) else None)
                    for kind, labels in node.items()
                })
            else:
                feature_samples[n][sec] = None
    four = [{"feature_name": "A", "icir": 0.5}, {"feature_name": "B", "icir": 0.5}, {"feature_name": "C", "icir": None}, {"feature_name": "D", "icir": float("nan")}]
    three = [{"feature_name": "A", "icir": 0.5}, {"feature_name": "B", "icir": 0.9}, {"feature_name": "C", "icir": None}]
    sort_golden = {
        "icir_desc_top5": [r["feature_name"] for r in sort_rows(rows, "icir", "desc", contract)[:5]],
        "icir_asc_top5": [r["feature_name"] for r in sort_rows(rows, "icir", "asc", contract)[:5]],
        "feature_name_asc_top5": [r["feature_name"] for r in sort_rows(rows, "feature_name", "asc", contract)[:5]],
        "feature_name_desc_top5": [r["feature_name"] for r in sort_rows(rows, "feature_name", "desc", contract)[:5]],
        "prefix_desc": [r["feature_name"] for r in sort_rows([{"feature_name": n} for n in ["close", "close_sma", "close_sma_20", "a", "ab"]], "feature_name", "desc", contract)],
        "four_desc": [r["feature_name"] for r in sort_rows(four, "icir", "desc", contract)],
        "four_asc": [r["feature_name"] for r in sort_rows(four, "icir", "asc", contract)],
        "three_desc": [r["feature_name"] for r in sort_rows(three, "icir", "desc", contract)],
        "three_asc": [r["feature_name"] for r in sort_rows(three, "icir", "asc", contract)],
    }
    shape = json.loads(SHAPE.read_text(encoding="utf-8"))
    return {
        "fixture_report": FIXTURE_REPORT.name,
        "raw_body_sha256": raw_sha,
        "report_canonical_sha": canonical_sha(body),
        "summary_rows": len(rows),
        "feature_set_sha256": _sha(names),
        "section_key_sha256": {k: (_sha(v) if v is not None else None) for k, v in sections.items()},
        "feature_samples": feature_samples,
        "sort_golden": sort_golden,
        "filter_log_light": apply_count_paths(body, contract)["filter_log"],
        "selection_scope_light": (apply_count_paths(body, contract).get("metadata") or {}).get("selection_scope"),
        "filter_log_funnel": funnel_from_filter_log(body.get("filter_log"), contract["funnel_stage_adapter"]),
        "shape_funnel": funnel_from_filter_log(shape["filter_log"], contract["funnel_stage_adapter"]),
        "shape_expected_funnel": shape["expected_funnel"],
    }


def main() -> int:
    from api.models.ic_models import load_ic_result_paging_contract

    contract = load_ic_result_paging_contract()
    if "--write" in sys.argv:
        from tests.momentum.helpers.ichc_run import run_analyze

        raw_report = run_analyze(None)
        body_bytes = default_result_bytes(raw_report)
        body = json.loads(body_bytes)
        GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
        FIXTURE_REPORT.write_text(json.dumps(body, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        # 冪等：以 JSON 化後的報告當 result 再 GET，位元組須相同（單一 normalized 樹前提，SPEC §C-7）
        again = default_result_bytes(json.loads(FIXTURE_REPORT.read_text(encoding="utf-8")))
        raw_sha = hashlib.sha256(again).hexdigest()
        first_sha = hashlib.sha256(body_bytes).hexdigest()
        print(f"idempotent_default_body={'YES' if raw_sha == first_sha else 'NO'} sha={raw_sha[:12]}")
        golden = build_golden(json.loads(again), raw_sha, contract)
        GOLDEN.write_text(json.dumps(golden, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"WROTE {GOLDEN} rows={golden['summary_rows']} fixture_bytes={FIXTURE_REPORT.stat().st_size}")
        return 0 if raw_sha == first_sha else 1
    if "--rebuild" in sys.argv:
        # 不重跑 analyze：以既有 fixture_report.json 重算 golden（golden 欄位增修時用；raw sha 不變）
        fixture = json.loads(FIXTURE_REPORT.read_text(encoding="utf-8"))
        body_bytes = default_result_bytes(fixture)
        raw_sha = hashlib.sha256(body_bytes).hexdigest()
        golden = build_golden(json.loads(body_bytes), raw_sha, contract)
        GOLDEN.write_text(json.dumps(golden, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"REBUILT {GOLDEN} raw_sha={raw_sha[:12]}")
        return 0
    # --check
    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
    fixture = json.loads(FIXTURE_REPORT.read_text(encoding="utf-8"))
    body_bytes = default_result_bytes(fixture)
    raw_sha = hashlib.sha256(body_bytes).hexdigest()
    live = build_golden(json.loads(body_bytes), raw_sha, contract)
    diffs = [k for k in golden if golden[k] != live.get(k)]
    print(f"raw_body_sha golden={golden['raw_body_sha256'][:12]} live={raw_sha[:12]}")
    print("SHAPE_FUNNEL_MATCHES_EXPECTED=" + ("YES" if live["shape_funnel"] == live["shape_expected_funnel"] else "NO"))
    if diffs:
        print("CHECK FAIL diffs=" + ",".join(diffs))
        return 1
    print("CHECK PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
