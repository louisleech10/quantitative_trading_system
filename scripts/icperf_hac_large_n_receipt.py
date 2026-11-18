#!/usr/bin/env python3
"""icperf_hac_large_n_receipt.py — ICPERF ④(c) 規模宣稱之一次性驗證收據：n＝500,000 時 `compute_hac_ic_statistics`
之資料不足警示模擬依可用記憶體分塊完成、p 正常輸出，並記峰值記憶體與耗時。

TESTSEL I10 自 `tests/momentum/Analysis/test_icperf_hac_method_bw.py::test_warning_large_n_chunked_completes` 移出：
分塊路徑（`hac_ewc._rows_per_chunk`）與 n 無分支，常規測試改以已知警示案例（n＝339、h＝24）、壓低可用記憶體走多塊路徑
並與單塊逐值比對；本腳本只保留「n＝500,000 可完成」之規模宣稱（原測試 ledger 286 秒）。

用法（重型：經共用監看與共用鎖）：
  lockf <heavy.lock> venv/bin/python scripts/run_watched.py --log <log> -- \
      venv/bin/python scripts/icperf_hac_large_n_receipt.py
寫 `handoffs/run_receipts/<UTC>-icperf-hac-large-n.json`；rc＝0 ⇔ inference_status＝ok 且 p 有限且模擬確為多塊。
何時須重跑：`momentum/Analysis/hac_ewc.py`、`momentum/Analysis/statistical_validator.py` 或本腳本改動，或數值環境指紋
（python、numpy、scipy、pandas、numba 版本）改變——收據記 `product_sha256`／`study_code_sha256`／`env_fingerprint`，由
`tests/momentum/Analysis/test_icperf_study_receipts_fresh.py` 機械判定。
生成器同原測試（seed 500、特徵 iid N(0,1)、標籤＝其後 5 期報酬和）。
"""
from __future__ import annotations

import hashlib
import json
import resource
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

N = 500_000
H_LABEL = 5
PRODUCT_FILES = ("momentum/Analysis/hac_ewc.py", "momentum/Analysis/statistical_validator.py")
#: 研究程式（本腳本自身：生成器、分塊計數與 ok 判定；不呼叫測試模組）
STUDY_CODE = ("scripts/icperf_hac_large_n_receipt.py",)
ENV_PACKAGES = ("numpy", "scipy", "pandas", "numba")


def numeric_env_fingerprint() -> dict:
    """python 版本與數值套件版本（`importlib.metadata`）。"""
    import platform
    from importlib import metadata

    return {"python": platform.python_version(), **{p: metadata.version(p) for p in ENV_PACKAGES}}


def _sha(rel: str) -> str:
    return hashlib.sha256((REPO / rel).read_bytes()).hexdigest()


def _overlap_label(rng: np.random.Generator, n: int, h: int) -> np.ndarray:
    """同測試檔 `_overlap_label`：標籤＝其後 h 期 iid 報酬和。"""
    r = rng.standard_normal(n + h)
    c = np.concatenate([[0.0], np.cumsum(r)])
    return c[1 + h: 1 + h + n] - c[1: 1 + n]


def main() -> int:
    from momentum.Analysis import hac_ewc as H
    from momentum.Analysis.statistical_validator import compute_hac_ic_statistics

    # 雜湊與環境指紋於開跑前取（＝本次實際載入之程式）
    product_sha = {p: _sha(p) for p in PRODUCT_FILES}
    study_sha = {p: _sha(p) for p in STUDY_CODE}
    env = numeric_env_fingerprint()
    rng = np.random.default_rng(500)
    x = rng.standard_normal(N)
    y = _overlap_label(rng, N, H_LABEL)
    idx = pd.RangeIndex(N)
    f, lab = pd.DataFrame({"f": x}, index=idx), pd.Series(y, index=idx)
    chunks = []
    real = H._simulate_chunk

    def _count(node, horizon, method, point, seed, r0, r1):
        chunks.append((int(node), str(point), int(r0), int(r1)))
        return real(node, horizon, method, point, seed, r0, r1)

    H._simulate_chunk = _count
    t0 = time.perf_counter()
    try:
        r = compute_hac_ic_statistics(f, lab, H_LABEL, method="pearson", alpha=0.05)["f"]
    finally:
        H._simulate_chunk = real
    wall = time.perf_counter() - t0
    per_sim: dict = {}
    for node, point, r0, r1 in chunks:
        per_sim.setdefault(f"{node}|{point}", []).append(r1 - r0)
    ok = r["inference_status"] == "ok" and bool(np.isfinite(r["p_value"])) and bool(per_sim) and all(
        len(v) > 1 for v in per_sim.values())
    head = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True,
                          check=True).stdout.strip()
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    receipt = {
        "receipt": "icperf-hac-large-n", "ts": ts, "head": head, "n": N, "horizon": H_LABEL, "seed": 500,
        "product_sha256": product_sha,
        "study_code_sha256": study_sha,
        "env_fingerprint": env,
        "rerun_when": "PRODUCT_FILES、STUDY_CODE 任一 sha256 或 env_fingerprint 與現行不符",
        "inference_status": r["inference_status"], "p_value": r["p_value"],
        "data_warning": r.get("data_warning"), "warning_not_evaluated": r.get("warning_not_evaluated"),
        "chunks_per_simulation": {k: len(v) for k, v in per_sim.items()},
        "wall_time_s": round(wall, 1), "ru_maxrss": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "ok": ok,
    }
    out = REPO / "handoffs" / "run_receipts" / f"{ts}-icperf-hac-large-n.json"
    out.write_text(json.dumps(receipt, ensure_ascii=False, indent=1, default=str) + "\n", encoding="utf-8")
    sys.stdout.write(f"[hac-large-n] ok={ok} wall={wall:.1f}s receipt={out}\n")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
