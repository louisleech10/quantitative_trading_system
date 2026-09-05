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
from typing import Optional

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

#: `G3-D2` D5.4：`--kind` 之封閉集合。
#: 🔴 每個 kind 提供**同名四支**（`cases` 模組、`load_golden`、`check_golden`、`freeze_payload`）
#:    ⇒ 三個子命令之流程不必分支，只換綁定；新增 kind 不必改 `cmd_*`。
#: 🔴 未知 kind 由 argparse 之 `choices` 擋（fail-closed，不預設回 `label`）。
_KINDS = ("label", "random_control")


def _bind(kind: str):
    """kind → (registry, golden_dir, load, check, freeze, `--check` 之逐案 t0 對證器)。"""
    if kind == "label":
        return (case_registry, GOLDEN_DIR, load_golden, check_golden, freeze_payload,
                _label_selector_guard)
    if kind == "random_control":
        from tests.golden.gap3_random_control import cases as rc_registry
        from tests.golden.gap3_random_control.loader import (
            check_golden as rc_check, freeze_payload as rc_freeze, load_golden as rc_load,
        )
        return (rc_registry, REPO / "tests" / "golden" / "gap3_random_control",
                rc_load, rc_check, rc_freeze, _random_control_selector_guard)
    raise ValueError(f"未知 --kind {kind!r}（封閉集合＝{_KINDS}）")  # argparse 已擋；防禦


def _label_selector_guard(case, resolved) -> Optional[str]:
    """`label` kind：凍結之 `t0_ms` 須仍等於登記處 selector 導出值。"""
    expected = [int(t) for t in resolved["meta"]["t0_ms"]]
    if list(case.t0_ms) != expected:
        return (f"凍結之 t0_ms 與登記處 selector 導出值不符"
                f"（凍結={list(case.t0_ms)[:3]}… selector={expected[:3]}…）"
                "——該案例已失去它宣稱的覆蓋，須確認 selector 意圖後重凍")
    return None


def _random_control_selector_guard(case, resolved) -> Optional[str]:
    """`random_control` kind：凍結之 `spec`／`trigger_receipts` 須仍等於登記處導出值。

    同一理由（`CODEX-R2-P1-01` 之姊妹條）：有人改了 universe 邊界或觸發索引後重凍，
    案例會**悄悄失去它宣稱的覆蓋**（例如不再跨月）而 `--check` 全綠。
    """
    meta = resolved["meta"]
    if dict(case.spec) != dict(meta["spec"]):
        return "凍結之 spec 與登記處導出值不符——universe／排除／規則已變，須確認意圖後重凍"
    if [dict(r) for r in case.trigger_receipts] != [dict(r) for r in meta["trigger_receipts"]]:
        return "凍結之 trigger_receipts 與登記處導出值不符——觸發批已變，排除區間隨之改變"
    if int(case.seed) != int(meta["seed"]):
        return f"凍結之 seed={case.seed} 與登記處 {meta['seed']} 不符"
    return None


def _bars():
    # 🔴 載入 `TFS` 全部 TF（非只 `TF`）：D1.4 起 golden 含 1h 案例，只載 12h 會讓
    #    那些案例在 `run_case` 內以 KeyError 炸開，而不是給出可讀的 diff。
    from tests.momentum.event_samples.helpers import load_bars
    return load_bars(case_registry.SYMBOL, case_registry.TFS)


def _write(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )


def _summary_line(kind: str, payload: dict) -> str:
    """一行摘要（各 kind 之關鍵欄不同；只影響輸出可讀性，不影響 rc）。"""
    if kind == "label":
        return (f"n_events={len(payload['events'])} nan={len(payload['nan_event_ids'])} "
                f"hash={payload['analysis_alignment_receipt_hash'][:16]}")
    return (f"n_drawn={payload['n_drawn']} candidates={payload['candidate_count']} "
            f"strata={len(payload['per_stratum'])} ids={payload['sample_ids_digest'][:16]}")


def cmd_init(force: bool, kind: str) -> int:
    registry, golden_dir, _load, _check, freeze, _guard = _bind(kind)
    bars = _bars()
    rc = 0
    golden_dir.mkdir(parents=True, exist_ok=True)
    for item in registry.resolved_cases(bars):
        path = golden_dir / item["file_name"]
        if path.exists() and not force:
            print(f"SKIP (已存在，需 --force 才重凍): {path.name}")
            continue
        payload = freeze(item["meta"], bars)
        _write(path, payload)
        print(f"FROZEN {path.name}: {_summary_line(kind, payload)}")
    return rc


def cmd_freeze(pattern: str, force: bool, kind: str) -> int:
    registry, _dir, _load, _check, freeze, _guard = _bind(kind)
    paths = sorted(Path(p) for p in globmod.glob(pattern))
    if not paths:
        print(f"FREEZE: glob 無命中: {pattern!r}（fail-closed）")
        return 1
    bars = _bars()
    by_id = {str(c["file_name"]): c for c in registry.CASES}
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
        item = next(i for i in registry.resolved_cases(bars) if i["file_name"] == p.name)
        payload = freeze(item["meta"], bars)
        changed = sorted(k for k in payload if old.get(k) != payload[k])
        _write(p, payload)
        print(f"REFROZEN {p.name}: 變動鍵={changed or '（無）'} {_summary_line(kind, payload)}")
    return rc


def cmd_check(pattern: str, kind: str) -> int:
    registry, _dir, load, check, _freeze, guard = _bind(kind)
    paths = sorted(Path(p) for p in globmod.glob(pattern) if p.endswith(".json"))
    if not paths:
        # 🔴 glob 無命中 ⇒ **FAIL**，不是「沒事」：驗收命令若 typo 就會靜默全綠。
        print(f"CHECK: glob 無命中: {pattern!r}（fail-closed）")
        return 1
    bars = _bars()
    # 🔴 `CODEX-R2-P1(P2)-01`（B-D1 R2）：`--check` 原本只讀 JSON 內既存之凍結值，
    #    **不驗它是否還等於 `cases.py` selector 導出之值** ⇒ 有人改了 selector（或 kline
    #    增量更新使索引指向別的 bar）後重凍，案例會**悄悄失去它宣稱的覆蓋**而 `--check` 全綠。
    #    ⇒ 在此逐檔對證（逐 kind 之對證器見 `_bind`）。登記處已移除該案例亦為紅。
    resolved = {item["file_name"]: item for item in registry.resolved_cases(bars)}
    rc = 0
    for p in paths:
        try:
            case = load(p)
            item = resolved.get(p.name)
            if item is None:
                print(f"FAIL {p.name}: 不在 cases.py 登記處（凍結檔與登記處已脫鉤）")
                rc = 1
                continue
            drift = guard(case, item)
            if drift is not None:
                print(f"FAIL {p.name}: {drift}")
                rc = 1
                continue
            report = check(case, bars)
        except Exception as exc:  # loader／run 之 fail-closed 一律計為紅
            print(f"FAIL {p.name}: {type(exc).__name__}: {exc}")
            rc = 1
            continue
        if report.ok:
            if kind == "label":
                print(f"PASS {p.name}: n_events={len(case.events)} nan={len(case.nan_event_ids)}")
            else:
                print(f"PASS {p.name}: n_drawn={case.n_drawn} candidates={case.candidate_count} "
                      f"strata={len(case.per_stratum)}")
        else:
            rc = 1
            print(f"FAIL {p.name}:")
            for d in report.diffs:
                print(f"    - {d}")
    print(f"GOLDEN CHECK {'PASS' if rc == 0 else 'FAIL'}: {len(paths)} case(s)")
    return rc


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="GAP-3 golden freeze/check（label_value ／隨機對照抽樣）")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", metavar="GLOB")
    g.add_argument("--freeze", metavar="GLOB")
    g.add_argument("--init", action="store_true")
    ap.add_argument("--force", action="store_true")
    # 🔴 `G3-D2` D5.4：封閉集合＋預設 `label`（既有 46 檔之呼叫方式**逐字不變**）。
    ap.add_argument("--kind", choices=_KINDS, default="label",
                    help="golden 家族；label＝label_value 五階段，random_control＝抽樣決定性")
    args = ap.parse_args(argv)
    if args.init:
        return cmd_init(args.force, args.kind)
    if args.freeze:
        return cmd_freeze(args.freeze, args.force, args.kind)
    return cmd_check(args.check, args.kind)


if __name__ == "__main__":
    sys.exit(main())
