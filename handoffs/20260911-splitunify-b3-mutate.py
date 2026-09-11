"""SPLITUNIFY B3 mutation 自證：逐條改壞**接線**，確認對應測試真的紅。

用法：`venv/bin/python handoffs/20260911-splitunify-b3-mutate.py`

規約（EVTLABEL／B2b 沿用）：**紅只認 rc=1**；rc=5（沒收到測試）不算紅；
對照組 `C0`（只改註解）必須仍綠；錨點不存在＝mutation 從未套用＝假綠，計入 UNCOVERED。

🔴 與 B2b 那支的差別：B2b 改的是**純函式內部**，本支改的是**呼叫圖**——
   接線的錯法不是「算錯」而是「接到別的地方去了」，所以每條 mutant 都對應
   「某個呼叫點被換掉／某個守衛被跳過」，而不是數值扰動。
🔴 跨語言：前端那條跑 vitest（`npm --prefix frontend run test`），紅之判定同樣認 rc=1。
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

PIPELINE = REPO / "momentum" / "Analysis" / "event_samples" / "pipeline.py"
SERVICE = REPO / "api" / "services" / "case_import_service.py"
ORCH = REPO / "momentum" / "Analysis" / "ic_filter_orchestrator.py"
TABLES = REPO / "momentum" / "Analysis" / "event_samples" / "tables.py"
PANEL = REPO / "frontend" / "src" / "components" / "ic-analysis" / "EventTablesPanel.tsx"

PYTEST_WIRING = "tests/momentum/event_samples/test_splitunify_wiring.py"
PYTEST_STUDY_ONLY = "tests/api/test_splitunify_event_study_only.py"
PYTEST_BOUNDARY = "tests/momentum/core/test_holdout_test_row_index.py"
VITEST_PANEL = "src/components/ic-analysis/eventTablesPanelCapability.test.tsx"

#: (id, 說明, 目標檔, old, new, 跑什麼)
#: 「跑什麼」＝("pytest", 路徑, -k 選擇器或 None) 或 ("vitest", 檔案)
MUTANTS = [
    (
        "M-SU-B3-1",
        "給齊 canonical 邊界時仍走歷史 split_events（兩套切分同時活著）",
        PIPELINE,
        "        if given:\n            # 🔴 Task 3.1 要點 4",
        "        if False:\n            # 🔴 Task 3.1 要點 4",
        ("pytest", PYTEST_WIRING, "canonical_boundary"),
    ),
    (
        "M-SU-B3-2",
        "只給一半邊界參數時不再擋（靜默退回歷史切分）",
        PIPELINE,
        "        if given and len(given) != len(projection_args):",
        "        if False:",
        ("pytest", PYTEST_WIRING, "partial_boundary"),
    ),
    (
        "M-SU-B3-3",
        "投影路徑不再檢查毫秒 embargo（兩套隔離同時生效）",
        PIPELINE,
        "            if config.split.embargo_ms is not None or config.split.embargo_ms_by_symbol is not None:",
        "            if False:",
        ("pytest", PYTEST_WIRING, "embargo_must_be_none"),
    ),
    (
        "M-SU-10",
        "event-study-only 之 summary 把切分計數填回 0（假 OOS 數字）",
        PIPELINE,
        '        summary.update({\n            "split": None,\n            "execution_mode": "event_study_only",\n        })',
        '        summary.update({\n            "split": None,\n            "n_train": 0,\n            "n_test": 0,\n            "n_purged": 0,\n            "execution_mode": "event_study_only",\n        })',
        ("pytest", PYTEST_STUDY_ONLY, "summary_has_no_split_counts"),
    ),
    (
        "M-SU-B3-5",
        "無 universe 時仍按事件數切並宣稱 OOS（service 走回 run_with_params）",
        SERVICE,
        "        res = self._pipeline.run_event_study_only_with_params(records, bars)\n        embargo_applied: Optional[int] = None",
        "        res = self._pipeline.run_with_params(records, bars, test_fraction=float(req.test_fraction))\n        embargo_applied: Optional[int] = None",
        ("pytest", PYTEST_STUDY_ONLY, "production_call_count"),
    ),
    (
        "M-SU-B3-6",
        "capability reason 兩條合一（畫面分不出「我沒填宣告」與「拿不到 universe」）",
        SERVICE,
        "                "
        "\"reason\": (self._pipeline.split_blocked_capability_reason() if split_blocked\n"
        "                           else self._pipeline.canonical_universe_unavailable_reason()),",
        "                \"reason\": self._pipeline.split_blocked_capability_reason(),",
        ("pytest", PYTEST_STUDY_ONLY, "capability_reason_is_no_universe"),
    ),
    (
        "M-SU-B3-7",
        "estimand_scope 不再揭露（全樣本結果看起來像 OOS）",
        TABLES,
        '        "estimand_scope": None if event_split_plan is not None else _full_sample_estimand_scope(),',
        '        "estimand_scope": None,',
        ("pytest", PYTEST_STUDY_ONLY, "full_sample_estimand"),
    ),
    (
        "M-SU-B3-8",
        "orchestrator 不再走 canonical boundary builder（兩端各自算一次邊界）",
        ORCH,
        "    boundary = holdout_boundary(",
        "    boundary = _legacy_boundary(",
        ("pytest", PYTEST_BOUNDARY, "orchestrator_uses_this_function"),
    ),
    (
        "M-SU-B3-9",
        "畫面在 unavailable 時仍印 train／test／purge 計數（C-0 要禁的假 OOS 數字）",
        PANEL,
        "          {cap.hasSplit\n            ? `／train ${fmt(s.n_train, 0)}／test ${fmt(s.n_test, 0)}／purge ${fmt(s.n_purged, 0)}`\n            : ''}",
        "          {`／train ${fmt(s.n_train, 0)}／test ${fmt(s.n_test, 0)}／purge ${fmt(s.n_purged, 0)}`}",
        ("vitest", VITEST_PANEL, None),
    ),
    (
        "M-SU-B3-10",
        "同源對證拿掉（plan 與 feature_index 可為不同網格 ⇒ 靜默錯分）",
        REPO / "momentum" / "Analysis" / "event_samples" / "split_projection.py",
        "        if (lo, hi) != (actual_lo, actual_hi):",
        "        if False:",
        ("pytest", "tests/momentum/Analysis/test_splitunify_derive.py", "same_source"),
    ),
    (
        "M-SU-B3-13",
        "pipeline.run 走投影時不傳 tier_min_test_events（H6：設定被靜默換成 1）",
        PIPELINE,
        "                tier_min_test_events=config.split.tier_min_test_events,\n",
        "",
        ("pytest", PYTEST_WIRING, "tier_min_test_events_reaches_projection"),
    ),
    (
        "M-SU-B3-11",
        "沒切分時 n_symbols 退回從空 summary 取（單標的批寫成「0 個標的」）",
        TABLES,
        "        n_symbols = (int(manifest.table[\"symbol\"].nunique())\n"
        "                     if manifest is not None and \"symbol\" in manifest.table.columns else None)",
        "        n_symbols = int(s.get(\"n_symbols\", 0))",
        ("pytest", PYTEST_STUDY_ONLY, "common_block_has_no_fake_numbers"),
    ),
    (
        "M-SU-B3-12",
        "沒切分時 degraded 退回空清單（與 cluster_adjusted=False 互相矛盾）",
        TABLES,
        "        degraded = _degraded_flags(n_symbols, cluster_adjusted=False) if n_symbols is not None else []",
        "        degraded = []",
        ("pytest", PYTEST_STUDY_ONLY, "common_block_has_no_fake_numbers"),
    ),
    (
        "C0",
        "只改註解（對照組，必須仍綠）",
        PIPELINE,
        "logger = get_logger(__name__)",
        "logger = get_logger(__name__)  # C0 對照組：只改註解",
        ("pytest", PYTEST_WIRING, None),
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
    backup_dir = Path(tempfile.mkdtemp(prefix="splitunify-b3-mutate-"))
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
