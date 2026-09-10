"""EVTLABEL G-6：survivor payload golden 凍結（`--write`）與比對（預設）。

SPEC §G G-6：P3 動工前以 `return_rule` 事件 run 與全域 run 各凍結一份 canonical bytes
（去 `generated_at`）＋ sha256、欄集、null mask、檔案大小；P3 改後逐項相等，
任一新鍵／排序漂移 ⇒ FAIL。

🔴 **誠實邊界（B4 動工前補記）**：G-6 原文寫「P3 動工前」凍結，實際是在 **B3 之後、B4 之前**
凍結的。B3（Task 3.1）已為 `sample_scope.event` 加了 `statistic_kind`／`label_binary` 兩鍵
（`return_rule` 與全域路徑皆為 `null`）。因此本 golden 的基準含那兩個 null 鍵。
這不影響 G-6 的用途——它要擋的是 **B4 起的 binary 工作**讓 `return_rule`／全域 payload 漂移。

用法：
  venv/bin/python scripts/freeze_evtlabel_survivor_golden.py --write   # 凍結
  venv/bin/python scripts/freeze_evtlabel_survivor_golden.py           # 比對（rc≠0 即漂移）
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
GOLDEN_DIR = REPO / "tests/golden/evtlabel"


def _canonical(payload: dict) -> bytes:
    """去掉會漂的欄位後之 canonical bytes（排序鍵、無空白）。"""
    clean = json.loads(json.dumps(payload))
    clean.pop("generated_at", None)
    return json.dumps(clean, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _null_mask(node, prefix=""):
    """遞迴記錄哪些路徑是 null——新鍵預設 null 時，只比 sha 會漏掉語意變化。"""
    out = {}
    if isinstance(node, dict):
        for k, v in node.items():
            out.update(_null_mask(v, f"{prefix}.{k}" if prefix else k))
    elif node is None:
        out[prefix] = True
    return out


def _build(kind: str) -> dict:
    from tests.momentum.Analysis.test_survivor_contract import _build_kwargs, _ctx, _event_kwargs

    if kind == "event_return_rule":
        kw = _event_kwargs(_ctx())
        kw["report_meta"] = {**kw["report_meta"],
                             "event_filter": {"applied": True, "label_source": "event_label_value"}}
    else:
        kw, _ = _build_kwargs()
    import momentum.Analysis.survivor_contract as sc

    return sc.build_survivor_output(**kw)


def _snapshot(payload: dict) -> dict:
    raw = _canonical(payload)
    return {
        "sha256": hashlib.sha256(raw).hexdigest(),
        "size_bytes": len(raw),
        "top_keys": sorted(payload.keys()),
        "event_keys": sorted((payload.get("sample_scope") or {}).get("event") or {}),
        "null_paths": sorted(_null_mask(payload)),
    }


def main() -> int:
    write = "--write" in sys.argv
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    rc = 0
    for kind in ("event_return_rule", "global"):
        path = GOLDEN_DIR / f"survivor_{kind}.json"
        snap = _snapshot(_build(kind))
        if write:
            path.write_text(json.dumps(snap, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
            print(f"WROTE {path.name}: sha={snap['sha256'][:12]} size={snap['size_bytes']} "
                  f"event_keys={len(snap['event_keys'])} nulls={len(snap['null_paths'])}")
            continue
        if not path.exists():
            print(f"G6 FAIL: golden 不存在（未凍結）: {path}")
            rc = 1
            continue
        want = json.loads(path.read_text(encoding="utf-8"))
        for field in ("sha256", "size_bytes", "top_keys", "event_keys", "null_paths"):
            if snap[field] != want[field]:
                print(f"G6 FAIL {kind}.{field}: golden={want[field]!r} now={snap[field]!r}")
                rc = 1
        if rc == 0:
            print(f"G6 PASS {kind}: sha={snap['sha256'][:12]} size={snap['size_bytes']}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
