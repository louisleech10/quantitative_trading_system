#!/usr/bin/env python3
"""gap3_freeze_golden.py — GAP-3 §G-1 行為不變 golden 之凍結／對照（TODO Phase B2 前言；B2.3 動工前第一步）。

用法：
  venv/bin/python scripts/gap3_freeze_golden.py --write   # B2.3 動工前跑一次，寫 pre 檔（獨立 commit）
  venv/bin/python scripts/gap3_freeze_golden.py --check   # B2.3/B2.4/B3.2 各接線後對照；差異 ⇒ 印鍵＋diff、rc=1；pre 檔缺 ⇒ rc=2

pre 檔（唯一 baseline，路徑寫死）：handoffs/run_receipts/gap3_golden_pre.json
序列化／scrub **import 復用** `scripts/gap2_freeze_golden.py::gap2_canonical_sha`（唯一序列化實作；
scrub ①marginal_ic ②survivor_output ③時戳/路徑鍵 ⑤scope_id 正規化），**不另立 scrub 清單**（D-001 前 TODO §B B2 前言）。
--check：canonical_sha exact；summary_table 逐列逐鍵 abs≤1e-12；fixture sha256／config_hash 不符 ⇒ rc=1。
不可做：不得重新凍結換綠；不得在 scrub 清單外多刪鍵。
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from gap2_freeze_golden import _diff_summary, _extract, _fixture_sha256, _run  # noqa: E402  # 復用唯一實作

PRE_PATH = REPO / "handoffs" / "run_receipts" / "gap3_golden_pre.json"


def _write() -> int:
    with tempfile.TemporaryDirectory(prefix="gap3_golden_") as td:
        report, config_hash = _run(Path(td))
    ext = _extract(report)
    payload = {
        "fixture_sha256": _fixture_sha256(),
        "config_hash": config_hash,
        "case_id": ext["case_id"],
        "canonical_sha": ext["canonical_sha"],
        "summary_table": ext["summary_table"],
        "filter_log": ext["filter_log"],
        "generated_by": "scripts/gap3_freeze_golden.py --write",
        "serializer": "scripts/gap2_freeze_golden.py::gap2_canonical_sha",
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    PRE_PATH.parent.mkdir(parents=True, exist_ok=True)
    PRE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=1))
    print(f"[gap3_freeze_golden] wrote {PRE_PATH} canonical_sha={payload['canonical_sha']} config_hash={config_hash}")
    return 0


def _check() -> int:
    if not PRE_PATH.exists():
        print(f"[gap3_freeze_golden] pre 檔缺席：{PRE_PATH}（先 --write）")
        return 2
    pre = json.loads(PRE_PATH.read_text())
    with tempfile.TemporaryDirectory(prefix="gap3_golden_chk_") as td:
        report, config_hash = _run(Path(td))
    ext = _extract(report)
    problems = []
    if _fixture_sha256() != pre["fixture_sha256"]:
        problems.append("fixture_sha256 mismatch")
    if config_hash != pre["config_hash"]:
        problems.append(f"config_hash: pre={pre['config_hash']} live={config_hash}")
    if ext["canonical_sha"] != pre["canonical_sha"]:
        problems.append(f"canonical_sha: pre={pre['canonical_sha']} live={ext['canonical_sha']}")
    problems += _diff_summary(pre["summary_table"], ext["summary_table"])
    if ext["filter_log"] != pre["filter_log"]:
        problems.append("filter_log (stage5/stage6) mismatch")
    if problems:
        print("[gap3_freeze_golden] CHECK FAIL:")
        for p in problems:
            print("  -", p)
        return 1
    print(f"[gap3_freeze_golden] CHECK PASS canonical_sha={ext['canonical_sha']}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--write", action="store_true")
    g.add_argument("--check", action="store_true")
    a = ap.parse_args()
    return _write() if a.write else _check()


if __name__ == "__main__":
    raise SystemExit(main())
