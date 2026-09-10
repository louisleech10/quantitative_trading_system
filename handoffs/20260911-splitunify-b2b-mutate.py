"""SPLITUNIFY B2b mutation 自證：逐條改壞 `split_projection.py`，確認對應測試**真的紅**。

用法：`venv/bin/python handoffs/20260911-splitunify-b2b-mutate.py`
規約（EVTLABEL 沿用）：**紅只認 rc=1**；rc=5（沒收到測試）不算紅；
對照組 `C0`（只改註解）必須仍綠。工作區須對 HEAD 乾淨（改檔前後自行還原）。
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TARGET = REPO / "momentum" / "Analysis" / "event_samples" / "split_projection.py"
#: M-SU-7 之錨點在共用實作那一側（B2b 把 clusters 真抽出到 event_split.py，不再複製）。
CLUSTER_TARGET = REPO / "momentum" / "Analysis" / "event_samples" / "event_split.py"
TESTS = REPO / "tests" / "momentum" / "Analysis" / "test_splitunify_derive.py"

#: (id, 說明, old, new, 期望紅的 -k 選擇器)；M-SU-7 改在 CLUSTER_TARGET 上動刀
MUTANTS = [
    (
        "M-SU-1",
        "投影二態化（purged 併入 assignments 的 train）",
        '            purge_rows.append({"event_id": rec["event_id"], "reason": _PURGE_REASON})\n            continue',
        '            assign_rows.append({"event_id": rec["event_id"], "symbol": rec["symbol"], "split_label": "train"})\n            continue',
        "answer_window or three_state",
    ),
    (
        "M-SU-2",
        "train/test plan 之 symbol 不同時不再擋（邊界本身跨批）",
        "    if len(plan_symbols) > 1:",
        "    if False:",
        "plan_symbols_differ",
    ),
    (
        "M-SU-3",
        "plan 未帶 symbol 時不再擋（無身份即無法證明邊界屬於本批）",
        "    if not plan_symbols:",
        "    if False:",
        "plan_without_symbol",
    ),
    (
        "M-SU-4",
        "成員判定改用 time_bounds 閉區間（隔離區事件會被誤判成 train）",
        "        in_train = cutoff in train_ms",
        "        in_train = int(train_plan.time_bounds[0]) <= cutoff <= int(train_plan.time_bounds[1])",
        "membership_set",
    ),
    (
        "M-SU-5",
        "未匹配時間戳預設歸 train（非 purged）",
        '            purge_rows.append({"event_id": rec["event_id"], "reason": _PURGE_REASON})\n\n    assignments',
        '            assign_rows.append({"event_id": rec["event_id"], "symbol": rec["symbol"], "split_label": "train"})\n\n    assignments',
        "unmatched_timestamp",
    ),
    (
        "M-SU-6",
        "同時落兩態時靜默取 train",
        "        if in_train and in_test:\n            raise ValueError(",
        "        if False:\n            raise ValueError(",
        "dual_membership",
    ),
    (
        "M-SU-7",
        "clusters 抄舊 plan 而非由 manifest 重算（權重改全 1）",
        '        "cluster_weight": _cluster_weight(counts.astype(float)),',
        '        "cluster_weight": 1.0,',
        "clusters",
    ),
    (
        "M-SU-13",
        "🔴 拿掉第一段答案窗 purge（只留集合成員判定）",
        '        if in_train and int(rec["label_end_ms"]) >= test_start_ms:',
        "        if False:",
        "answer_window",
    ),
    (
        "M-SU-14",
        "🔴 test_start_ms 誤減 embargo（H1 對齊 fixture 上會假綠，需近邊界 fixture）",
        "    test_start_ms = int(index_ms[test_rows[0]])",
        "    test_start_ms = int(index_ms[test_rows[0]]) - int(getattr(test_plan, 'embargo', 0)) * 3_600_000",
        "answer_window",
    ),
    (
        "M-SU-15",
        "build_event_keys 移除 validate=1:1（重複 event_level 不再擋）",
        'on="event_id", how="inner", validate="1:1"',
        'on="event_id", how="inner"',
        "build_event_keys",
    ),
    (
        "M-SU-16",
        "plan-symbol 身份檢查拿掉（只看基數）",
        "    if symbols and symbols != plan_symbols:",
        "    if False:",
        "plan_symbol_mismatch",
    ),
    (
        "M-SU-17",
        "manifest ID 對帳拿掉（餵另一批 manifest 也通過）",
        "    if key_ids != man_ids:",
        "    if False:",
        "manifest_id_mismatch or superset",
    ),
    (
        "M-SU-18",
        "混合單位不再擋（逐元素改回 np.all）",
        "    return assert_epoch_ms_array(np.asarray(idx), role=\"split_projection: feature_index\")",
        "    return np.asarray(idx, dtype=\"int64\")",
        "mixed_unit",
    ),
    (
        "M-SU-19",
        "負／越界 row index 不再擋",
        "    train_rows = assert_positional_rows(",
        "    train_rows = np.asarray(  # MUTANT\n        ",
        "negative_row_index or out_of_range",
    ),
    (
        "M-SU-20",
        "答案窗 `>=` 改成 `>`（恰等於邊界時漏 purge）",
        '        if in_train and int(rec["label_end_ms"]) >= test_start_ms:',
        '        if in_train and int(rec["label_end_ms"]) > test_start_ms:',
        "answer_window",
    ),
    (
        "C0",
        "對照組：只改註解",
        "🔴 **純函式**：無 log、無 I/O",
        "🔴 (C0 對照組) **純函式**：無 log、無 I/O",
        None,
    ),
]


def _run(selector: str | None) -> int:
    cmd = ["venv/bin/python", "-m", "pytest", "-q", str(TESTS.relative_to(REPO))]
    if selector:
        cmd += ["-k", selector]
    return subprocess.run(cmd, cwd=REPO, capture_output=True, text=True).returncode


def main() -> int:
    original = TARGET.read_text(encoding="utf-8")
    cluster_original = CLUSTER_TARGET.read_text(encoding="utf-8")
    backup = Path(tempfile.mkdtemp()) / "split_projection.py.bak"
    backup.write_text(original, encoding="utf-8")

    uncovered: list[str] = []
    try:
        for mid, desc, old, new, selector in MUTANTS:
            src_check = cluster_original if mid == "M-SU-7" else original
            if old not in src_check:
                print(f"  ✗ {mid}: **錨點不存在**——mutation 從未套用（假綠）：{desc}")
                uncovered.append(mid)
                continue
            tgt = CLUSTER_TARGET if mid == "M-SU-7" else TARGET
            src = cluster_original if mid == "M-SU-7" else original
            tgt.write_text(src.replace(old, new, 1), encoding="utf-8")
            rc = _run(selector)
            tgt.write_text(src, encoding="utf-8")
            if mid == "C0":
                ok = rc == 0
                print(f"  {'✓' if ok else '✗'} {mid}: 對照組 rc={rc}（期望 0）")
                if not ok:
                    uncovered.append(mid)
            else:
                ok = rc == 1  # 🔴 紅只認 rc=1；rc=5＝沒收到測試，不算紅
                print(f"  {'✓' if ok else '✗'} {mid}: rc={rc}（期望 1）— {desc}")
                if not ok:
                    uncovered.append(mid)
    finally:
        TARGET.write_text(backup.read_text(encoding="utf-8"), encoding="utf-8")
        CLUSTER_TARGET.write_text(cluster_original, encoding="utf-8")
        shutil.rmtree(backup.parent, ignore_errors=True)

    print(f"\nUNCOVERED={len(uncovered)}" + (f" → {uncovered}" if uncovered else ""))
    return 1 if uncovered else 0


if __name__ == "__main__":
    sys.exit(main())
