#!/usr/bin/env python3
"""gap2_freeze_golden.py — GAP-2 §G-1 改前==改後 golden 之凍結／對照（TODO Task 4.0；B4 動工順序第一）。

用法：
  venv/bin/python scripts/gap2_freeze_golden.py --write   # 動 orchestrator 前跑一次，寫 pre 檔（獨立 commit）
  venv/bin/python scripts/gap2_freeze_golden.py --check   # 每步／收尾對照；差異 ⇒ 印鍵＋diff、rc=1；pre 檔缺 ⇒ rc=2

pre 檔（唯一 baseline，路徑寫死）：handoffs/run_receipts/gap2_golden_pre.json
  {fixture_sha256, config_hash, case_id, canonical_sha, summary_table, filter_log:{stage5_thresholds, stage6_redundancy}, generated_by, ts}
  - case_id＝helper 決定之實值（fixture meta 無 case_id ⇒ `_resolve_case_id` 回 `ic_gatekeeper`；A1-2，不改 helper）
  - canonical_sha＝`gap2_canonical_sha(report)`（本檔為**唯一**序列化實作，測試 import 之）：
      有序 scrub ① `report.pop("marginal_ic")` ② `metadata.pop("survivor_output")`
      ③ metadata 刪 filtered_features_path／filtered_generated_at／generated_at／filtered_features_written；頂層刪 generated_at
      ④ 其餘沿用 `tests/momentum/helpers/ichc_run.canonical_sha`（import 之，不重寫）
  - --check：canonical_sha exact；summary_table 逐列逐鍵 abs≤1e-12（非數值 exact）；filter_log 兩節 exact；case_id exact；
    fixture sha256 不符 ⇒ rc=1；並於兩個不同 sidefx 目錄各跑一次、兩 sha 相等（路徑無關性）。
不可做：不得重新凍結換綠；不得在 scrub 清單外多刪鍵。
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

PRE_PATH = REPO / "handoffs" / "run_receipts" / "gap2_golden_pre.json"

_META_SCRUB = ("filtered_features_path", "filtered_generated_at", "generated_at", "filtered_features_written")


def gap2_canonical_sha(report: Dict[str, Any]) -> str:
    """唯一序列化實作（scrub 清單寫死且有序；其餘沿用 ichc_run.canonical_sha）。"""
    from tests.momentum.helpers.ichc_run import canonical_sha

    r = copy.deepcopy(report)
    r.pop("marginal_ic", None)  # ①
    meta = r.get("metadata")
    if isinstance(meta, dict):
        meta.pop("survivor_output", None)  # ②
        for key in _META_SCRUB:  # ③
            meta.pop(key, None)
    r.pop("generated_at", None)  # ③ 頂層
    return canonical_sha(r)  # ④


def _fixture_sha256() -> str:
    from tests.momentum.helpers.ichc_run import fixture_paths

    h5, _ = fixture_paths()
    return hashlib.sha256(h5.read_bytes()).hexdigest()


def _run(sidefx_dir: Path) -> Tuple[Dict[str, Any], str]:
    """跑一次預設 config；回 (report, config_hash)。"""
    from momentum.factories import create_ic_analyzer  # noqa: F401  # 確保 factories 可載
    from tests.momentum.helpers.ichc_run import run_analyze

    report = run_analyze(config_override=None, sidefx_dir=sidefx_dir)
    meta = report.get("metadata") or {}
    # config_hash 取自 metadata.selection_scope.scope_id（＝f"{config_hash}:{split_label}"；orchestrator 未直接輸出 config_hash）
    scope = meta.get("selection_scope") if isinstance(meta.get("selection_scope"), dict) else {}
    scope_id = str(scope.get("scope_id") or "")
    config_hash = scope_id.split(":", 1)[0] if scope_id else ""
    return report, config_hash


def _extract(report: Dict[str, Any]) -> Dict[str, Any]:
    fl = report.get("filter_log") or {}
    meta = report.get("metadata") or {}
    return {
        "case_id": str(meta.get("case_id") or "ic_gatekeeper"),
        "canonical_sha": gap2_canonical_sha(report),
        "summary_table": list(report.get("summary_table") or []),
        "filter_log": {
            "stage5_thresholds": fl.get("stage5_thresholds"),
            "stage6_redundancy": fl.get("stage6_redundancy"),
        },
    }


def _num_close(a: Any, b: Any) -> bool:
    if isinstance(a, bool) or isinstance(b, bool):
        return a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        fa, fb = float(a), float(b)
        if math.isnan(fa) and math.isnan(fb):
            return True
        return abs(fa - fb) <= 1e-12
    return a == b


def _diff_summary(pre: List[Dict[str, Any]], live: List[Dict[str, Any]]) -> List[str]:
    out: List[str] = []
    if len(pre) != len(live):
        out.append(f"summary_table len {len(pre)} != {len(live)}")
        return out
    for i, (p, l) in enumerate(zip(pre, live)):
        keys = set(p.keys()) | set(l.keys())
        for k in sorted(keys):
            if k not in p or k not in l:
                out.append(f"summary_table[{i}].{k}: missing on one side")
            elif not _num_close(p[k], l[k]):
                out.append(f"summary_table[{i}].{k}: pre={p[k]!r} live={l[k]!r}")
    return out


def _write() -> int:
    with tempfile.TemporaryDirectory(prefix="gap2_golden_") as td:
        report, config_hash = _run(Path(td))
    ext = _extract(report)
    payload = {
        "fixture_sha256": _fixture_sha256(),
        "config_hash": config_hash,
        "case_id": ext["case_id"],
        "canonical_sha": ext["canonical_sha"],
        "summary_table": ext["summary_table"],
        "filter_log": ext["filter_log"],
        "generated_by": "scripts/gap2_freeze_golden.py --write",
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    PRE_PATH.parent.mkdir(parents=True, exist_ok=True)
    PRE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str, allow_nan=True) + "\n", encoding="utf-8")
    print(f"[gap2_freeze_golden] wrote {PRE_PATH} canonical_sha={ext['canonical_sha'][:12]}… case_id={ext['case_id']} rows={len(ext['summary_table'])}")
    return 0


def _check() -> int:
    if not PRE_PATH.is_file():
        print(f"[gap2_freeze_golden] 🔴 pre 檔缺：{PRE_PATH}", file=sys.stderr)
        return 2
    pre = json.loads(PRE_PATH.read_text(encoding="utf-8"))
    problems: List[str] = []
    fx = _fixture_sha256()
    if fx != pre.get("fixture_sha256"):
        problems.append(f"fixture_sha256 mismatch pre={pre.get('fixture_sha256')} live={fx}")
    shas: List[str] = []
    live_ext = None
    for tag in ("a", "b"):
        with tempfile.TemporaryDirectory(prefix=f"gap2_golden_{tag}_") as td:
            report, config_hash = _run(Path(td))
        ext = _extract(report)
        shas.append(ext["canonical_sha"])
        if live_ext is None:
            live_ext = ext
            if config_hash != pre.get("config_hash"):
                problems.append(f"config_hash mismatch pre={pre.get('config_hash')} live={config_hash}")
    assert live_ext is not None
    if shas[0] != shas[1]:
        problems.append(f"path-independence: sha differs across sidefx dirs {shas[0][:12]} vs {shas[1][:12]}")
    if live_ext["canonical_sha"] != pre.get("canonical_sha"):
        problems.append(f"canonical_sha mismatch pre={pre.get('canonical_sha')} live={live_ext['canonical_sha']}")
    if live_ext["case_id"] != pre.get("case_id"):
        problems.append(f"case_id mismatch pre={pre.get('case_id')} live={live_ext['case_id']}")
    problems.extend(_diff_summary(pre.get("summary_table") or [], live_ext["summary_table"]))
    for sec in ("stage5_thresholds", "stage6_redundancy"):
        if json.dumps(pre.get("filter_log", {}).get(sec), sort_keys=True, default=str) != json.dumps(live_ext["filter_log"].get(sec), sort_keys=True, default=str):
            problems.append(f"filter_log.{sec} differs")
    if problems:
        print("[gap2_freeze_golden] 🔴 CHECK FAIL:")
        for p in problems:
            print("  · " + p)
        return 1
    print(f"[gap2_freeze_golden] ✅ CHECK PASS canonical_sha={live_ext['canonical_sha'][:12]}… case_id={live_ext['case_id']} rows={len(live_ext['summary_table'])} (兩 sidefx 目錄 sha 相等)")
    return 0


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--write", action="store_true")
    g.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)
    return _write() if args.write else _check()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
