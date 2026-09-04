#!/usr/bin/env python
"""GAP-3 `G3-D2` — `label_value` golden 之 **freeze／check CLI**（`D-001` §G）。

用法::

    venv/bin/python scripts/gap3_label_golden.py --check "tests/golden/gap3_label/*.json"
    venv/bin/python scripts/gap3_label_golden.py --init                 # 建尚不存在之登記案例
    venv/bin/python scripts/gap3_label_golden.py --freeze "…*.json" --force   # 重凍既有檔

`--check` rc=0 ⇔ 全部案例逐項相符；任一不符 ⇒ rc=1 並列出 event_id 與 diff。

🔴 **`--freeze` 無 `--force` 會拒絕覆寫既有檔**：重凍是有後果的動作（凍結值就是驗收基準），
必須是**顯式**的一次，並在 commit message 具名改了什麼、為什麼合法。

🔴 **手算法（唯一）**：凍結時之值來自生產函式對真實 kline 之一次執行；
「值對不對」由 `tests/momentum/event_samples/test_gap3_analysis_label_producer.py` 之
D0 段以**獨立手算**（直接自同一 bar 表取 `bars[field]@open_time` 與 `close@close_time` 相除）
釘住。本 CLI 只負責**凍結與比對**，不另寫報酬公式（那會變成測兩份實作是否一致）。
"""

from __future__ import annotations

import argparse
import glob as globmod
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tests.golden.gap3_label import cases as case_registry  # noqa: E402
from tests.golden.gap3_label.loader import (  # noqa: E402
    check_golden,
    freeze_payload,
    load_golden,
)

GOLDEN_DIR = REPO / "tests" / "golden" / "gap3_label"


def _bars():
    from tests.momentum.event_samples.helpers import load_bars
    return load_bars(case_registry.SYMBOL, (case_registry.TF,))


def _write(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )


def cmd_init(force: bool) -> int:
    bars = _bars()
    rc = 0
    for item in case_registry.resolved_cases(bars):
        path = GOLDEN_DIR / item["file_name"]
        if path.exists() and not force:
            print(f"SKIP (已存在，需 --force 才重凍): {path.name}")
            continue
        payload = freeze_payload(item["meta"], bars)
        _write(path, payload)
        n_nan = len(payload["nan_event_ids"])
        print(f"FROZEN {path.name}: n_events={len(payload['events'])} nan={n_nan} "
              f"hash={payload['analysis_alignment_receipt_hash'][:16]}")
    return rc


def cmd_freeze(pattern: str, force: bool) -> int:
    paths = sorted(Path(p) for p in globmod.glob(pattern))
    if not paths:
        print(f"FREEZE: glob 無命中: {pattern!r}（fail-closed）")
        return 1
    bars = _bars()
    by_id = {str(c["file_name"]): c for c in case_registry.CASES}
    rc = 0
    for p in paths:
        if p.name == "loader.py" or p.suffix != ".json":
            continue
        if p.name not in by_id:
            print(f"FREEZE-FAIL {p.name}: 不在 cases.py 登記處（禁凍未登記案例）")
            rc = 1
            continue
        if not force:
            print(f"FREEZE-REFUSED {p.name}: 既有檔重凍須 --force（並於 commit message 具名）")
            rc = 1
            continue
        old = json.loads(p.read_text(encoding="utf-8"))
        item = next(i for i in case_registry.resolved_cases(bars) if i["file_name"] == p.name)
        payload = freeze_payload(item["meta"], bars)
        changed = sorted(k for k in payload if old.get(k) != payload[k])
        _write(p, payload)
        print(f"REFROZEN {p.name}: 變動鍵={changed or '（無）'} "
              f"hash={payload['analysis_alignment_receipt_hash'][:16]}")
    return rc


def cmd_check(pattern: str) -> int:
    paths = sorted(Path(p) for p in globmod.glob(pattern) if p.endswith(".json"))
    if not paths:
        # 🔴 glob 無命中 ⇒ **FAIL**，不是「沒事」：驗收命令若 typo 就會靜默全綠。
        print(f"CHECK: glob 無命中: {pattern!r}（fail-closed）")
        return 1
    bars = _bars()
    rc = 0
    for p in paths:
        try:
            case = load_golden(p)
            report = check_golden(case, bars)
        except Exception as exc:  # loader／run 之 fail-closed 一律計為紅
            print(f"FAIL {p.name}: {type(exc).__name__}: {exc}")
            rc = 1
            continue
        if report.ok:
            print(f"PASS {p.name}: n_events={len(case.events)} nan={len(case.nan_event_ids)}")
        else:
            rc = 1
            print(f"FAIL {p.name}:")
            for d in report.diffs:
                print(f"    - {d}")
    print(f"GOLDEN CHECK {'PASS' if rc == 0 else 'FAIL'}: {len(paths)} case(s)")
    return rc


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="GAP-3 label_value golden freeze/check")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", metavar="GLOB")
    g.add_argument("--freeze", metavar="GLOB")
    g.add_argument("--init", action="store_true")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args(argv)
    if args.init:
        return cmd_init(args.force)
    if args.freeze:
        return cmd_freeze(args.freeze, args.force)
    return cmd_check(args.check)


if __name__ == "__main__":
    sys.exit(main())
