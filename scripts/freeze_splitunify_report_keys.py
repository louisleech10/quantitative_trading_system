"""SPLITUNIFY B4 R2：凍結報告之「整數葉鍵集」——**名稱無關**的 deny-by-default。

出生理由（B4 review R2，codex／composer／grok **三家獨立打穿**）：
R1 我做的掃描用「鍵名含 `test`」當候選判準，三家各自實跑證明
`n_oos_events`／`holdout_hits`／`validation_segment_n` 這類**改個名字就完全逃掉**
（grok `ESCAPE_COUNT=9`、composer `7/7 escape keys evaded scanner`、codex `ESCAPED=True`）。

🔴 教訓：**名稱與值都推不出語意**。加寬正則（`events|hits|count|_n$`）只是把逃逸門檻
抬高一點，攻擊者叫它 `foo` 就又過了——那是黑名單思維，本專案已明訂「黑名單永遠列不完」。
可證偽的做法只有一種：**把現況凍起來，新鍵一律紅**，由人在 diff 上判語意。

本檔凍的是**正規化後的 dotted path 集合**（三種 run 各一份）：
  · list 索引 → `[*]`
  · per-item 容器（`coverage_analysis`／`per_feature`）之下一層名字 → `*`
新增／刪除任何一個整數葉都會讓 `tests/api/test_splitunify_disclosure.py` 轉紅，
訊息逐條指名。合法新增 ⇒ 跑 `--write` 重凍，**並在 commit 訊息說明新鍵的語意**。

用法：
  `venv/bin/python scripts/freeze_splitunify_report_keys.py`          # 比對（rc=1 表示漂了）
  `venv/bin/python scripts/freeze_splitunify_report_keys.py --write`  # 重凍
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

FROZEN = REPO / "tests" / "golden" / "splitunify" / "report_int_keys.json"

#: 這些容器之下一層是**資料命名**（特徵名），不是結構鍵 ⇒ 一律折成 `*`。
PER_ITEM_CONTAINERS = ("coverage_analysis", "per_feature")

CTX = {
    "event_manifest_hash": "1" * 64,
    "label_definition_hash": "2" * 64,
    "decision_time_rule": "t0_open_minus_k_bars",
    "feature_cutoff_rule": "max_close_ms_le_decision_at",
    "label_window_rule": "close_to_close:horizon_bars=2",
    "control_kind": "user_labeled_same_trigger",
}


def normalize_path(path: str) -> str:
    """list 索引與 per-item 容器下的名字折成 `*`（其餘保持原樣）。"""
    out = re.sub(r"\[\d+\]", "[*]", path)
    for container in PER_ITEM_CONTAINERS:
        out = re.sub(r"(^|\.)" + container + r"\.[^.]+", r"\1" + container + ".*", out)
    return out


def int_leaf_paths(node, prefix: str = "") -> set:
    """整份報告中所有「整數葉」之正規化 path（`bool` 不算整數）。"""
    found = set()
    if isinstance(node, dict):
        for key, value in node.items():
            path = (prefix + "." + str(key)) if prefix else str(key)
            if isinstance(value, int) and not isinstance(value, bool):
                found.add(normalize_path(path))
            found |= int_leaf_paths(value, path)
    elif isinstance(node, list):
        for i, value in enumerate(node):
            found |= int_leaf_paths(value, prefix + "[" + str(i) + "]")
    return found


def build_reports() -> dict:
    """三種 run：正常事件、降級事件、全域。回 {run_kind: sorted(paths)}。"""
    import numpy as np

    from tests.momentum.helpers.ichc_run import feature_index, run_analyze

    idx = feature_index(80)
    rng = np.random.default_rng(20260911 + 80)
    label_values = {
        int(t.value // 10 ** 6): float(v)
        for t, v in zip(idx, rng.normal(0, 0.02, len(idx)))
    }
    owners = {t: "ev%03d" % i for i, t in enumerate(label_values)}
    event_kwargs = dict(
        event_timestamps=list(label_values), event_label_values=label_values,
        event_label_owners=owners, event_context=CTX,
    )
    runs = {
        "event": ({"event_filter": {"enabled": True, "min_events": 30, "min_test_events": 0}}, event_kwargs),
        "degraded": ({"event_filter": {"enabled": True, "min_events": 30, "min_test_events": 10000}}, event_kwargs),
        "global": ({"event_filter": {"enabled": False}}, {}),
    }
    return {
        kind: sorted(int_leaf_paths(run_analyze(cfg, **kwargs)))
        for kind, (cfg, kwargs) in runs.items()
    }


DOC = (
    "報告之整數葉鍵集（正規化 path）。新增／刪除任一鍵都會讓 "
    "tests/api/test_splitunify_disclosure.py 轉紅——這是**名稱無關**的 deny-by-default"
    "（B4 review R2：三家證明『鍵名含 test』的判準可被改名逃逸）。"
    "合法新增 ⇒ 跑 scripts/freeze_splitunify_report_keys.py --write 重凍，"
    "並在 commit 訊息說明新鍵的語意；若它帶「驗證段事件數」語意，"
    "還必須進 split_unify.json 之 test_segment_count_keys。"
)


def main() -> int:
    write = "--write" in sys.argv
    current = build_reports()
    if write:
        FROZEN.parent.mkdir(parents=True, exist_ok=True)
        FROZEN.write_text(
            json.dumps({"_doc": DOC, "runs": current}, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        total = sum(len(v) for v in current.values())
        print("FROZE %d paths -> %s" % (total, FROZEN.relative_to(REPO)))
        for kind, paths in sorted(current.items()):
            print("  %-10s %d" % (kind, len(paths)))
        return 0

    if not FROZEN.exists():
        print("FROZEN MISSING: %s——首次請跑 `--write`" % FROZEN, file=sys.stderr)
        return 1
    frozen = json.loads(FROZEN.read_text(encoding="utf-8"))["runs"]
    bad = False
    for kind in sorted(set(frozen) | set(current)):
        added = sorted(set(current.get(kind, [])) - set(frozen.get(kind, [])))
        removed = sorted(set(frozen.get(kind, [])) - set(current.get(kind, [])))
        if added or removed:
            bad = True
            print("✗ %s: 新增 %s；消失 %s" % (kind, added, removed), file=sys.stderr)
    if bad:
        print("REPORT KEY DRIFT——新的整數鍵必須先登記語意（見本檔 _doc）", file=sys.stderr)
        return 1
    print("REPORT KEYS OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
