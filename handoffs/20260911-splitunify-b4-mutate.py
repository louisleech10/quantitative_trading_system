"""SPLITUNIFY B4 mutation 自證：逐條改壞**揭露**，確認對應測試真的紅。

用法：`venv/bin/python handoffs/20260911-splitunify-b4-mutate.py`

規約（B2b／B3 沿用）：**紅只認 rc=1**；rc=5（沒收到測試）不算紅；`C0` 對照組必須仍綠；
錨點不存在＝mutation 從未套用＝假綠，計入 UNCOVERED。

🔴 B4 的錯法不是「算錯」也不是「接錯」，而是**講錯**——同一個問題給兩個答案、
   或把「沒得算」講成「算出來是零」。每條 mutant 都對應其中一種講法。
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

PROJECTION = REPO / "momentum" / "Analysis" / "event_samples" / "split_projection.py"
ORCH = REPO / "momentum" / "Analysis" / "ic_filter_orchestrator.py"
PREVIEW = REPO / "momentum" / "core" / "split_preview.py"
AUTHORITY = REPO / "frontend" / "src" / "lib" / "splitAuthority.ts"

PYTEST_DISCLOSURE = "tests/api/test_splitunify_disclosure.py"
VITEST_AUTHORITY = "src/lib/splitAuthority.test.ts"

MUTANTS = [
    (
        "M-SU-9",
        "同時暴露兩個**不同**的驗證段事件數（孿生鍵比 canonical 多 1）",
        ORCH,
        '                metadata["split_unify"] = build_split_unify_disclosure(',
        '                metadata.setdefault("ic_train_test_split", {})["test_events"] = test_events + 1\n'
        '                metadata["split_unify"] = build_split_unify_disclosure(',
        ("pytest", PYTEST_DISCLOSURE, "exactly_one_test_count_key"),
    ),
    (
        "M-SU-B4-2",
        "fail-closed 時把 n_test 填 0 而不是 null（假數字）",
        PROJECTION,
        '        return {\n            "n_test": None,\n            "split_authority": authority,',
        '        return {\n            "n_test": 0,\n            "split_authority": authority,',
        ("pytest", PYTEST_DISCLOSURE, "fail_closed_is_null_not_zero"),
    ),
    (
        "M-SU-B4-3",
        "per_symbol_counts 與 n_test 矛盾時不再擋",
        PROJECTION,
        "    if counts and total != n:",
        "    if False:",
        ("pytest", PYTEST_DISCLOSURE, "contradicting_per_symbol_counts"),
    ),
    (
        "M-SU-B4-4",
        "reason 不再對證契約封閉集合（可自造字面）",
        PROJECTION,
        "    if reason is not None and reason not in FAIL_CLOSED_REASONS:",
        "    if False:",
        ("pytest", PYTEST_DISCLOSURE, "unregistered_reason"),
    ),
    (
        "M-SU-B4-5",
        "boundary_hash 不再排序（同一段換個列舉順序就變不同雜湊）",
        PREVIEW,
        "    payload = json.dumps(sorted(ints), separators=(\",\", \":\"))",
        "    payload = json.dumps(ints, separators=(\",\", \":\"))",
        ("pytest", PYTEST_DISCLOSURE, "boundary_hash_is_order_insensitive"),
    ),
    (
        "M-SU-B4-6",
        "boundary_hash 只吃筆數不吃時刻（換掉一個時刻仍同雜湊）",
        PREVIEW,
        "    payload = json.dumps(sorted(ints), separators=(\",\", \":\"))",
        "    payload = json.dumps(len(ints), separators=(\",\", \":\"))",
        ("pytest", PYTEST_DISCLOSURE, "boundary_hash_changes_with_membership"),
    ),
    (
        "M-SU-B4-7",
        "全域 run 也寫 split_unify（G-2：全域報告不再逐位元組不變）",
        ORCH,
        "            if is_event_label_consumed(event_info):\n                # stage3 後 features_df 只剩實際被消費之事件列",
        "            if True:\n                # stage3 後 features_df 只剩實際被消費之事件列",
        ("pytest", PYTEST_DISCLOSURE, "absent_on_global_run"),
    ),
    (
        "M-SU-B4-8",
        "前端把 null 顯示成 0（畫面上的假數字）",
        AUTHORITY,
        "    countText: hasCount ? String(n) : '無',",
        "    countText: hasCount ? String(n) : '0',",
        ("vitest", VITEST_AUTHORITY, None),
    ),
    (
        "M-SU-B4-9",
        "前端值集改成手打第二份（與契約漂移不會被發現）",
        AUTHORITY,
        "export const SPLIT_AUTHORITY_VALUES: readonly string[] = CONTRACT.split_authority_values;",
        "export const SPLIT_AUTHORITY_VALUES: readonly string[] = ['kline_holdout', 'event_local'];",
        ("vitest", VITEST_AUTHORITY, None),
    ),
    # ── B4 review R1 收斂後追加（三家獨立命中之四類）──────────────────────
    (
        "M-SU-B4-10",
        "deny-by-default 掃描退回只掃 metadata（未登記的新鍵不會被抓到）",
        REPO / "tests" / "api" / "test_splitunify_disclosure.py",
        "    unregistered = sorted(set(_scan_test_int_paths(report)) - _registry_paths())",
        "    unregistered = sorted(set(_scan_test_int_paths(report.get('metadata', {}))) - _registry_paths())",
        ("pytest", PYTEST_DISCLOSURE, "denylist_catches_injected_key or no_unregistered"),
    ),
    (
        "M-SU-B4-11",
        "n_test 之型別／值域閘拿掉（-1 與 3.7 都會被寫進報告）",
        PROJECTION,
        "    n = _strict_count(n_test, role=\"n_test\")",
        "    n = int(n_test)",
        ("pytest", PYTEST_DISCLOSURE, "rejects_bad_n_test"),
    ),
    (
        "M-SU-B4-12",
        "n_test>0 卻沒有 per_symbol_counts 時不再擋（無歸屬的數字）",
        PROJECTION,
        "    if n > 0 and not counts:",
        "    if False:",
        ("pytest", PYTEST_DISCLOSURE, "empty_counts_with_positive_n_test"),
    ),
    (
        "M-SU-B4-13",
        "boundary_hash 不再拒 datetime-like（同一組時刻兩個雜湊）",
        PREVIEW,
        '    if raw.dtype.kind in ("M", "m"):',
        "    if False:",
        ("pytest", PYTEST_DISCLOSURE, "boundary_hash_rejects_datetime_like"),
    ),
    (
        "M-SU-B4-14",
        "boundary_hash 不再拒重複時刻",
        PREVIEW,
        "    if len(set(ints)) != len(ints):",
        "    if False:",
        ("pytest", PYTEST_DISCLOSURE, "boundary_hash_rejects_duplicates"),
    ),
    (
        "M-SU-B4-15",
        "降級路徑之孿生鍵給出**不同**的數字（oos_downgrade.test_rows 比 canonical 多 1）",
        ORCH,
        '                            "test_rows": int(test_mask.sum()),\n'
        '                            "min_test_rows": None,',
        '                            "test_rows": int(test_mask.sum()) + 1,\n'
        '                            "min_test_rows": None,',
        ("pytest", PYTEST_DISCLOSURE, "exactly_one_test_count_key"),
    ),
    (
        "M-SU-B4-16",
        "前端把「全域 run 不適用」與「舊 artifact 缺鍵」混為一談（都不渲染）",
        AUTHORITY,
        "    if (options?.hasSplitMetadata) {",
        "    if (false) {",
        ("vitest", VITEST_AUTHORITY, None),
    ),
    # ── B4 review R2 收斂後追加：名稱無關之 deny-by-default 是否承重 ──────────
    (
        "M-SU-B4-17",
        "掃描退回「鍵名含 test」的舊判準（三家的改名逃逸會重新逃掉）",
        REPO / "scripts" / "freeze_splitunify_report_keys.py",
        "            if isinstance(value, int) and not isinstance(value, bool):",
        '            if isinstance(value, int) and not isinstance(value, bool) and "test" in str(key).lower():',
        ("pytest", PYTEST_DISCLOSURE, "frozen_inventory_catches_renamed_escape"),
    ),
    (
        "M-SU-B4-18",
        "報告新增一個未登記的整數鍵（模擬未來有人加 n_oos_events）",
        ORCH,
        '                metadata["split_unify"] = build_split_unify_disclosure(',
        '                metadata["n_oos_events"] = int(test_mask.sum()) + 18\n'
        '                metadata["split_unify"] = build_split_unify_disclosure(',
        ("pytest", PYTEST_DISCLOSURE, "report_int_keys_match_frozen_inventory"),
    ),
    (
        "M-SU-B4-19",
        "事件批缺揭露時退回「不適用」（閉合確認輪 COMPOSER-R2-P2-02：後端回歸被掩蓋）",
        AUTHORITY,
        "    if (options?.isEventRun) {",
        "    if (false) {",
        ("vitest", VITEST_AUTHORITY, None),
    ),
    (
        "C0",
        "只改註解（對照組，必須仍綠）",
        PROJECTION,
        "#: `event_keys` 之必填欄（SPEC C-4；R3 之 E2）。",
        "#: `event_keys` 之必填欄（SPEC C-4；R3 之 E2）。C0 對照組。",
        ("pytest", PYTEST_DISCLOSURE, None),
    ),
]


def _run(spec) -> int:
    kind, path, selector = spec
    if kind == "pytest":
        cmd = ["venv/bin/python", "-m", "pytest", "-q", path]
        if selector:
            cmd += ["-k", selector]
        return subprocess.run(cmd, cwd=REPO, capture_output=True, text=True).returncode
    cmd = ["npm", "--prefix", "frontend", "run", "test", "--", "--run", path]
    return subprocess.run(cmd, cwd=REPO, capture_output=True, text=True).returncode


def main() -> int:
    targets = {m[2] for m in MUTANTS}
    originals = {t: t.read_text(encoding="utf-8") for t in targets}
    backup_dir = Path(tempfile.mkdtemp(prefix="splitunify-b4-mutate-"))
    for t, src in originals.items():
        (backup_dir / t.name).write_text(src, encoding="utf-8")

    uncovered: list[str] = []
    try:
        for mid, desc, target, old, new, spec in MUTANTS:
            src = originals[target]
            if old not in src:
                print(f"  ✗ {mid}: **錨點不存在**——mutation 從未套用（假綠）：{desc}")
                uncovered.append(mid)
                continue
            target.write_text(src.replace(old, new, 1), encoding="utf-8")
            rc = _run(spec)
            target.write_text(src, encoding="utf-8")
            expected = 0 if mid == "C0" else 1
            ok = rc == expected
            print(f"  {'✓' if ok else '✗'} {mid}: rc={rc}（期望 {expected}）— {desc}")
            if not ok:
                uncovered.append(mid)
    finally:
        for t in targets:
            t.write_text((backup_dir / t.name).read_text(encoding="utf-8"), encoding="utf-8")
        shutil.rmtree(backup_dir, ignore_errors=True)

    print(f"\nUNCOVERED={len(uncovered)}" + (f" → {uncovered}" if uncovered else ""))
    return 1 if uncovered else 0


if __name__ == "__main__":
    sys.exit(main())
