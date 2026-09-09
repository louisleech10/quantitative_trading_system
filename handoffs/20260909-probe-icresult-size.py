#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ICRESULT_PAGING G-5 尺寸／G-9 延遲探針（受控 artifact；不在 pytest 內）。

    venv/bin/python handoffs/20260909-probe-icresult-size.py            # --size（預設）
    venv/bin/python handoffs/20260909-probe-icresult-size.py --latency  # G-9

stdout 唯一文法：恰一行 `SIZE_GATE=PASS|FAIL|BLOCKED`（--size）／恰一行 `LATENCY_GATE=PASS|FAIL|BLOCKED`（--latency），
另行 `SIZE_REASON=`／`LATENCY_REASON=`、逐項 `LATENCY_<name>_p50_ms=`／`_p95_ms=`。rc：PASS 0／FAIL 1／BLOCKED 2。
receipt：handoffs/run_receipts/icresult_size_budget.log／icresult_latency.log。
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
ARTIFACT = REPO / "data_cache/reports/ic_report_ic_gatekeeper.json"
TASK_ID = "icresult-paging-size-probe"


def _emit(token: str, state: str, reason: str, extra: list[str], receipt: Path) -> int:
    lines = [f"{token}={state}", f"{token.split('_')[0]}_REASON={reason}", *extra]
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return {"PASS": 0, "FAIL": 1, "BLOCKED": 2}[state]


def main() -> int:
    mode = "latency" if "--latency" in sys.argv else "size"
    token = "LATENCY_GATE" if mode == "latency" else "SIZE_GATE"
    receipt = REPO / "handoffs/run_receipts" / ("icresult_latency.log" if mode == "latency" else "icresult_size_budget.log")
    if not ARTIFACT.is_file():
        return _emit(token, "BLOCKED", "artifact missing", [], receipt)
    try:
        from api.services import ic_result_projection as proj  # B1 才存在
    except Exception as exc:  # noqa: BLE001
        return _emit(token, "BLOCKED", f"projection missing ({type(exc).__name__})", [], receipt)
    try:
        return _run(mode, token, receipt)
    except Exception as exc:  # noqa: BLE001 — 任何 setup 失敗（app import／外部連線）皆轉 BLOCKED，維持三態唯一文法（B1 review CODEX-R1-P1-02）
        return _emit(token, "BLOCKED", f"setup failed ({type(exc).__name__}: {str(exc)[:80]})", [], receipt)


def _run(mode: str, token: str, receipt: Path) -> int:
    import os as _os
    if _os.environ.get("ICRESULT_PROBE_FORCE_SETUP_FAIL"):
        raise RuntimeError("forced setup failure (test)")
    from api.models.ic_models import load_ic_result_paging_contract
    from api.services.ic_analysis_service import ic_analysis_service
    from fastapi.testclient import TestClient
    from api.main import app

    contract = load_ic_result_paging_contract()
    report = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    with ic_analysis_service._lock:
        info = {"task_id": TASK_ID, "status": "completed", "progress": 1.0}
        ic_analysis_service._tasks[TASK_ID] = info
    ic_analysis_service._set_result(info, report)  # lock 外（GROK-R1-P1-01）
    try:
        with TestClient(app) as client:
            first = client.get(f"/api/v1/ic/result/{TASK_ID}/summary?limit=50&sort_by=icir&sort_order=desc").json()
            first_name = first["rows"][0]["feature_name"] if first["rows"] else ""
            biggest = max(report["turnover_analysis"], key=lambda n: len(json.dumps(report["turnover_analysis"][n], default=str)))
            reqs = {
                "light": f"/api/v1/ic/result/{TASK_ID}?view=light",
                "summary_icir_desc": f"/api/v1/ic/result/{TASK_ID}/summary?limit=50&sort_by=icir&sort_order=desc",
                "summary_name_asc": f"/api/v1/ic/result/{TASK_ID}/summary?limit=50&sort_by=feature_name&sort_order=asc",
                "summary_search": f"/api/v1/ic/result/{TASK_ID}/summary?limit=50&search=close",
                "summary_pass_class": f"/api/v1/ic/result/{TASK_ID}/summary?limit=50&pass_class=oos",
                "feature_first": f"/api/v1/ic/result/{TASK_ID}/feature/{first_name}",
                "feature_biggest": f"/api/v1/ic/result/{TASK_ID}/feature/{biggest}",
            }
            if mode == "size":
                budget = contract["size_budget_bytes"]
                sizes = {k: len(client.get(u).content) for k, u in reqs.items() if k in ("light", "summary_icir_desc", "feature_first", "feature_biggest")}
                extra = [f"light_bytes={sizes['light']}", f"summary50_bytes={sizes['summary_icir_desc']}", f"feature_first_bytes={sizes['feature_first']}", f"feature_biggest_bytes={sizes['feature_biggest']}"]
                ok = sizes["light"] <= budget["light"] and sizes["summary_icir_desc"] <= budget["summary_limit_50"] and max(sizes["feature_first"], sizes["feature_biggest"]) <= budget["feature"]
                return _emit(token, "PASS" if ok else "FAIL", "measured", extra, receipt)
            budget = contract["latency_budget_ms"]
            extra, ok = [], True

            def measure(url: str) -> tuple[float, float]:
                for _ in range(3):
                    client.get(url)
                xs = []
                for _ in range(20):
                    t = time.perf_counter(); client.get(url); xs.append((time.perf_counter() - t) * 1000)
                xs.sort()
                return xs[9], xs[18]

            for name, url in reqs.items():
                p50, p95 = measure(url)
                kind = "light" if name == "light" else ("summary" if name.startswith("summary") else "feature")
                extra += [f"LATENCY_{name}_p50_ms={p50:.2f}", f"LATENCY_{name}_p95_ms={p95:.2f}"]
                ok = ok and p50 <= budget[kind]["p50"] and p95 <= budget[kind]["p95"]
            # 快取命中：icir desc 第二次
            t = time.perf_counter(); client.get(reqs["summary_icir_desc"]); hit = (time.perf_counter() - t) * 1000
            extra.append(f"LATENCY_summary_cache_hit_ms={hit:.2f}")
            ok = ok and hit <= budget["summary_cache_hit_p50"]
            return _emit(token, "PASS" if ok else "FAIL", "measured", extra, receipt)
    finally:
        with ic_analysis_service._lock:
            ic_analysis_service._tasks.pop(TASK_ID, None)


if __name__ == "__main__":
    sys.exit(main())
