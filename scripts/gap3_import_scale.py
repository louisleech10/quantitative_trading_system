#!/usr/bin/env python
"""GAP-3 T-3 偵察＋B5.1 規模 receipt：萬級事件走 validate→align→dedupe→split（＋事件後報酬表 bootstrap），
實測牆鐘與峰值 RSS，寫 `handoffs/run_receipts/gap3_import_scale.json`（記錄型；不私定門檻——TODO W10）。

事件為合成（章程 §F：合成的是事件序列非價格），bars 為真實 kline（ETHUSDT 1h）。
用法：venv/bin/python scripts/gap3_import_scale.py [--n 10000] [--write]
"""

from __future__ import annotations

import argparse
import json
import resource
import sys
import time
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from momentum.factories import create_event_sample_pipeline  # noqa: E402
from momentum.Analysis.event_samples.pipeline import EventPipelineConfig  # noqa: E402
from momentum.Analysis.event_samples.tables import event_forward_return_table  # noqa: E402
from momentum.Analysis.event_samples.types import EventSplitConfig  # noqa: E402
from tests.momentum.event_samples.helpers import load_bars  # noqa: E402
from tests.momentum.event_samples.test_import_contract import make_event  # noqa: E402

OUT = REPO / "handoffs" / "run_receipts" / "gap3_import_scale.json"


def _rss_mb() -> float:
    ru = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return float(ru / (1024 * 1024)) if sys.platform == "darwin" else float(ru / 1024)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=10000)
    ap.add_argument("--tf", default="1h")
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()

    bars = load_bars("ETHUSDT", (a.tf,))
    g = bars["ETHUSDT"][a.tf]
    ot = g["open_time_ms"].to_numpy()
    rng = np.random.default_rng(20260821)
    idxs = np.sort(rng.choice(np.arange(300, len(ot) - 50), size=min(a.n, len(ot) - 350), replace=False))
    events = [make_event(i, t0=int(ot[x]), timeframe=a.tf, label=int(i % 2)) for i, x in enumerate(idxs)]

    t = {}
    rss0 = _rss_mb()
    p = create_event_sample_pipeline()
    t0 = time.perf_counter()
    df, fails = p.validate(events)
    t["validate_s"] = time.perf_counter() - t0
    assert df is not None, fails[:3]
    t0 = time.perf_counter()
    res = p.run(events, bars, EventPipelineConfig(split=EventSplitConfig(test_fraction=0.3, tier_min_test_events=0)))
    t["align_dedupe_split_s"] = time.perf_counter() - t0
    t0 = time.perf_counter()
    tbl = event_forward_return_table(res.manifest, res.receipts, bars, res.split_plan,
                                     {"horizons": [1, 2, 4], "seed": 1, "n_boot": 200})
    t["forward_return_table_bootstrap_s"] = time.perf_counter() - t0
    total = sum(t.values())

    # API 路徑（CODEX-R1-P1-03）：同一 workload 經 /case/import-events/json（validate_only）實測牆鐘／RSS；落檔目錄導到暫存
    api_path = {"status": "skipped"}
    try:
        import tempfile
        from fastapi.testclient import TestClient
        from api.main import app
        from api.services import case_import_service as svc_mod

        with tempfile.TemporaryDirectory() as td:
            svc_mod._event_import_service = svc_mod.EventImportService(storage_dir=Path(td) / "events")
            client = TestClient(app)
            rss_api0 = _rss_mb()
            t0 = time.perf_counter()
            r = client.post("/api/v1/case/import-events/json", json={"records": events, "validate_only": False})
            api_s = time.perf_counter() - t0
            body = r.json() if r.status_code == 200 else {"error": r.text[:300]}
            api_path = {"status": "ok" if r.status_code == 200 else "failed", "http_status": r.status_code,
                        "endpoint": "/api/v1/case/import-events/json", "n_records": len(events), "wall_clock_s": round(api_s, 3),
                        "peak_rss_mb_after": round(_rss_mb(), 1), "rss_before_mb": round(rss_api0, 1),
                        "n_valid": body.get("n_valid"), "stored": bool(body.get("stored_path"))}
    except Exception as exc:  # noqa: BLE001 —— API 路徑量測失敗不遮 direct receipt，如實記錄
        api_path = {"status": "failed", "error": repr(exc)[:300]}

    receipt = {
        "api_path": api_path,
        "n_events": int(len(events)), "timeframe": a.tf, "symbol": "ETHUSDT", "n_bars": int(len(ot)),
        "wall_clock_s": round(total, 3), "stages_s": {k: round(v, 3) for k, v in t.items()},
        "peak_rss_mb": round(_rss_mb(), 1), "rss_before_mb": round(rss0, 1),
        "n_aligned": res.summary["n_aligned"], "n_align_failures": res.summary["n_align_failures"],
        "n_clusters": res.manifest.summary["n_clusters"], "n_train": res.summary["n_train"], "n_test": res.summary["n_test"],
        "bootstrap": {"n_boot": 200, "horizons": [1, 2, 4], "status": tbl.get("capability_status", "ok")},
        "python": sys.version.split()[0], "platform": sys.platform, "generated_by": "scripts/gap3_import_scale.py",
        "note": "記錄型 receipt（W10）；事件合成、bars 真實；效能門檻若需另走 SPEC amendment",
    }
    print(json.dumps(receipt, ensure_ascii=False, indent=1))
    if a.write:
        OUT.write_text(json.dumps(receipt, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
        print(f"[gap3_import_scale] wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
