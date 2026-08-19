"""ICHC Task 5.1 — IC wiring 三規則機檢（由 scripts/ic_wiring_check.sh 包裝）。

規則（封閉集合機械比對，禁散文判斷）：
  R1a 前端 toggle key 全集（PRESET_TOGGLES）⊆ getEffectiveConfig 消費集 ∪ allowlist
  R1b getEffectiveConfig 映射鍵 ⊆ 後端可消費集（STAGE_OVERRIDE_PATHS ∪ deep module 名
      ∪ 顯式轉名表——store 內註記的 UI 邊界唯一轉名點）
  R2  allowlist lifecycle：每條目之 key 必須仍存在於其宣告檔（過期即紅）；
      已判死配置（dead_config 類）不得重現於 schema（防復發）
  R3  report 節組裝禁裸空 dict 字面（節鍵＝契約 report_sections；GAP-2 起讀契約）
誠實邊界（具名殘留，非本檢查涵蓋）：全 schema 欄位 consumer 掃描（AST 級）未實作，
  R2 僅承載 allowlist 生命週期＋已判幽靈防復發；升級路徑=另立票。
exit code：0=綠；1=違規；2=環境/輸入異常（fail-closed）。
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
# 測試覆寫走 argv 旗標（--store/--orch/--schema/--allowlist），禁 env（B-43：env 可被外部 shell 汙染）
_args = dict(zip(sys.argv[1::2], sys.argv[2::2]))
STORE = Path(_args.get("--store", REPO / "frontend/src/store/icAnalysisStore.ts"))
ORCH = Path(_args.get("--orch", REPO / "momentum/Analysis/ic_filter_orchestrator.py"))
SCHEMA = Path(_args.get("--schema", REPO / "momentum/Analysis/ic_config_schema.py"))
ALLOWLIST = Path(_args.get("--allowlist", REPO / "scripts/ic_wiring_allowlist.json"))

# GAP-2 Task 4.3：R3 節鍵改讀契約 SoT（消除五／六節漂移；新節自動涵蓋）
def _load_report_sections() -> tuple:
    import sys as _sys

    _sys.path.insert(0, str(REPO))
    from momentum.Analysis.ic_config_schema import load_report_contract

    return tuple(load_report_contract()["report_sections"].keys())


REPORT_SECTIONS = _load_report_sections()
# UI 邊界顯式轉名（store 註記「唯一轉名點」）：前端鍵 → 後端 override 路徑存在即視為已消費
EXPLICIT_RENAMES = {"fdr_correction": "significance.fdr.enabled"}


def die(code: int, msg: str) -> None:
    print(f"[ic_wiring_check] {msg}")
    sys.exit(code)


def main() -> None:
    for path in (STORE, ORCH, SCHEMA):
        if not path.exists():
            die(2, f"掃描目標缺席（fail-closed）：{path}")
    if not ALLOWLIST.exists():
        die(1, f"allowlist 缺席（fail-closed）：{ALLOWLIST}")

    try:
        allowlist = json.loads(ALLOWLIST.read_text(encoding="utf-8"))
        entries = allowlist["entries"]
        assert isinstance(entries, list)
    except Exception as exc:  # noqa: BLE001
        die(1, f"allowlist 壞損（fail-closed）：{exc}")

    store_src = STORE.read_text(encoding="utf-8")
    orch_src = ORCH.read_text(encoding="utf-8")
    schema_src = SCHEMA.read_text(encoding="utf-8")

    # 前端 toggle 全集：PRESET_TOGGLES 區塊內 `key: true|false`
    preset_block = re.search(
        r"const PRESET_TOGGLES[\s\S]*?\n\};", store_src
    )
    if not preset_block:
        die(2, "抓不到 PRESET_TOGGLES 區塊")
    toggle_keys = set(re.findall(r"^\s{4}(\w+): (?:true|false),", preset_block.group(0), re.M))

    # getEffectiveConfig 消費集：stageOverrides + moduleOverrides 映射鍵
    eff_block = re.search(r"getEffectiveConfig[\s\S]*?moduleOverrides[\s\S]*?\n    \};", store_src)
    if not eff_block:
        die(2, "抓不到 getEffectiveConfig 區塊")
    consumed_keys = set(re.findall(r"(\w+): Boolean\(state\.featureToggles\.(\w+)\)", eff_block.group(0)))
    consumed_frontend = {src for _, src in consumed_keys}
    mapped_backend = {dst for dst, _ in consumed_keys}

    # 後端可消費集：STAGE_OVERRIDE_PATHS ∪ MODULE_ENABLED_PATHS 鍵 ∪ deep module 名
    stage_block = re.search(r"STAGE_OVERRIDE_PATHS[\s\S]*?\n\}", orch_src)
    stage_keys = set(re.findall(r'"(\w+)":\s*\(', stage_block.group(0))) if stage_block else set()
    module_block = re.search(r"MODULE_ENABLED_PATHS[\s\S]*?\n\}", orch_src)
    module_cfg_keys = set(re.findall(r'"(\w+)":\s*\(', module_block.group(0))) if module_block else set()
    module_names = set(re.findall(r'\("(\w+)", self\._run_\w+\)', orch_src))
    backend_keys = stage_keys | module_cfg_keys | module_names | set(EXPLICIT_RENAMES)

    allow_keys = {e["key"] for e in entries}
    problems: list[str] = []

    # R1a
    for key in sorted(toggle_keys - consumed_frontend - allow_keys):
        problems.append(f"R1a 幽靈 toggle：{key}（PRESET_TOGGLES 有、getEffectiveConfig 無、allowlist 未列）")
    # R1b
    for key in sorted(mapped_backend - backend_keys):
        problems.append(f"R1b 前端映射鍵無後端消費：{key}")
    # R2 lifecycle
    file_cache: dict[str, str] = {}
    for entry in entries:
        key, file_rel = entry.get("key"), entry.get("file")
        if not key or not file_rel:
            problems.append(f"R2 allowlist 條目欄位缺：{entry}")
            continue
        target = REPO / file_rel
        if not target.exists():
            problems.append(f"R2 allowlist 宣告檔缺席：{file_rel}（key={key}）")
            continue
        src = file_cache.setdefault(file_rel, target.read_text(encoding="utf-8"))
        if entry.get("kind") == "dead_config":
            if re.search(rf"\b{re.escape(key)}\b", schema_src):
                problems.append(f"R2 已判死配置重現 schema：{key}（防復發）")
        else:
            if not re.search(rf"\b{re.escape(key)}\b", src):
                problems.append(f"R2 allowlist 條目過期（key 已不存在）：{key} @ {file_rel}")
    # R3
    for section in REPORT_SECTIONS:
        if re.search(rf'"{section}":\s*\{{\}},', orch_src):
            problems.append(f"R3 report 節裸空 dict 字面：{section}")

    if problems:
        for p in problems:
            print(f"[ic_wiring_check] ✗ {p}")
        die(1, f"未過：{len(problems)} 項violations")
    print(
        f"[ic_wiring_check] ✓ R1a({len(toggle_keys)} toggles)/R1b({len(mapped_backend)} mapped)/"
        f"R2({len(entries)} allowlist)/R3({len(REPORT_SECTIONS)} sections) 全綠"
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
