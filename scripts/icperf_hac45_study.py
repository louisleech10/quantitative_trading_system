#!/usr/bin/env python3
"""icperf_hac45_study.py — ICPERF Task 0.4 ㊺ 虛無拒絕率與檢定力研究之全規模一次性驗證（SPEC v5.78 ㊺ B⑥、B⑦）。

TESTSEL I10 自 `tests/momentum/Analysis/test_icperf_hac45_size.py` 移出：B⑥ 之 size 判準（每格拒絕數 ≤
Binomial(1,000, 0.05) 之 Bonferroni 上界、初判超限依預先登記規則確認一次）只在全規模有鑑別力（13 格×1,000 次，
約 1.5 小時），B⑦ 為研究輸出（9 格×1,000 次×(1 虛無＋4 δ)）。測試檔保留生成器、判定函式之秒級自驗與全部格點之
小規模接線；本腳本以同一組函式（自測試模組匯入，不另寫一份）跑全規模並寫收據。

用法（重型：須經共用監看與共用鎖）：
  lockf <heavy.lock> venv/bin/python scripts/run_watched.py --log <log> -- \
      venv/bin/python scripts/icperf_hac45_study.py b6 [b7]

輸出：`runs/icperf/hac45/<研究>.json`（逐格明細，gitignored）＋ `handoffs/run_receipts/<UTC>-icperf-hac45-<研究>.json`
（HEAD、受檢產品檔 sha256、逐格判定摘要）。rc：B⑥ 任一格 pass≠True ⇒ 1；B⑦ 任一格任一 δ 有非有限檢定力 ⇒ 1。

何時須重跑：下列受檢產品檔、研究程式（測試模組與本腳本，STUDY_CODE）任一改動，或數值環境指紋（python、numpy、scipy、
pandas、numba 版本）改變——收據之 `product_sha256`／`study_code_sha256`／`env_fingerprint` 與現行不符即過期，由
`tests/momentum/Analysis/test_icperf_study_receipts_fresh.py` 機械判定。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

#: 受檢產品碼（SPEC ㊺ 受檢對象；B⑥／B⑦ 經 b_single_rep 呼叫之模組）
PRODUCT_FILES = (
    "momentum/Analysis/ic_engine.py",
    "momentum/Analysis/ic_filter_orchestrator.py",
    "momentum/Analysis/ic_config_schema.py",
    "momentum/core/split_preview.py",
    "momentum/Analysis/factor_centrality_analyzer.py",
    "momentum/Analysis/long_short_analyzer.py",
    "momentum/Analysis/trend_analyzer.py",
    "momentum/Analysis/trend_inference.py",
    "momentum/Analysis/hac_ewc.py",
    "momentum/Analysis/pit_stats.py",
)
STUDY_TEST = "tests/momentum/Analysis/test_icperf_hac45_size.py"
#: 研究程式＝被呼叫之測試模組（生成器、判定）＋本腳本自身（編排與 ok 聚合）；任一改動即須重跑（審碼 b2 r2 群集 B）
STUDY_CODE = (STUDY_TEST, "scripts/icperf_hac45_study.py")
#: 數值環境指紋之套件（版本變動即須重跑；審碼 b2 r2 群集 B）
ENV_PACKAGES = ("numpy", "scipy", "pandas", "numba")


def numeric_env_fingerprint() -> Dict[str, str]:
    """python 版本與數值套件版本（`importlib.metadata`，不 import 套件本體）。"""
    import platform
    from importlib import metadata

    return {"python": platform.python_version(), **{p: metadata.version(p) for p in ENV_PACKAGES}}


def _sha256(rel: str) -> str:
    return hashlib.sha256((REPO / rel).read_bytes()).hexdigest()


def _head() -> str:
    return subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True,
                          check=True).stdout.strip()


def _dirty(paths) -> List[str]:
    out = subprocess.run(["git", "-C", str(REPO), "status", "--porcelain", "--", *paths], capture_output=True,
                         text=True, check=True).stdout
    return [ln for ln in out.splitlines() if ln.strip()]


def run_study(name: str) -> Dict:
    import tests.momentum.Analysis.test_icperf_hac45_size as S

    t0 = time.perf_counter()
    if name == "b6":
        cells = S._judge([S.b6_run_cell(c) for c in S.B6_GRID],
                         rerun=lambda cell, reps, extra: S.b6_run_cell(cell, reps, extra))
        ok = all(c["pass"] is True for c in cells)
        summary = [{"key": c["key"], "reps": c["reps"], "rejected": c["rejected"], "upper_bound": c["upper_bound"],
                    "verdict": c["verdict"], "pass": c["pass"]} for c in cells]
    elif name == "b7":
        import numpy as np

        cells = [S.b7_run_cell(c) for c in S.B7_GRID]
        ok = all(np.isfinite(c["size_adjusted_power"][str(d)][k])
                 for c in cells for d in S.B7_DELTAS for k in S.B7_METHODS)
        summary = [{"cell": c["cell"], "reps": c["reps"], "size_adjusted_power": {
            d: {k: v for k, v in p.items() if k in S.B7_METHODS} for d, p in c["size_adjusted_power"].items()}}
            for c in cells]
    else:
        raise SystemExit(f"未知研究：{name}（b6｜b7）")
    detail = S._write(name, {"study": name.upper(), "alpha": S.ALPHA, "cells": cells})
    return {"study": name.upper(), "ok": ok, "seconds": round(time.perf_counter() - t0, 1),
            "detail_path": str(detail.relative_to(REPO)), "cells": summary}


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("studies", nargs="+", choices=("b6", "b7"))
    args = ap.parse_args(argv)
    head = _head()
    dirty = _dirty((*PRODUCT_FILES, *STUDY_CODE))
    # 雜湊與環境指紋於開跑前取（＝本次實際載入之程式；跑中改檔不得混入收據）
    product_sha = {p: _sha256(p) for p in PRODUCT_FILES}
    study_sha = {p: _sha256(p) for p in STUDY_CODE}
    env = numeric_env_fingerprint()
    rc = 0
    for name in args.studies:
        res = run_study(name)
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        receipt = {
            "receipt": "icperf-hac45-study", "ts": ts, "head": head,
            "product_sha256": product_sha,
            "study_code_sha256": study_sha,
            "env_fingerprint": env,
            "dirty_paths_at_run": dirty,
            "rerun_when": "PRODUCT_FILES、STUDY_CODE 任一 sha256 或 env_fingerprint 與現行不符",
            **res,
        }
        out = REPO / "handoffs" / "run_receipts" / f"{ts}-icperf-hac45-{name}.json"
        out.write_text(json.dumps(receipt, ensure_ascii=False, indent=1, default=float) + "\n", encoding="utf-8")
        sys.stdout.write(f"[hac45-study] {name} ok={res['ok']} seconds={res['seconds']} receipt={out}\n")
        rc |= 0 if res["ok"] else 1
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
