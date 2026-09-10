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

TOGGLE_CONTRACT = Path(
    _args.get("--toggle-contract", REPO / "momentum/Analysis/contracts/ui_stage_toggles.json")
)


def _load_toggle_contract() -> tuple:
    """票 TIERTOGGLE：UI 開關鍵集之單一真相源（stage／module 兩集合）。

    讀不到或缺鍵 ⇒ 回空集合，讓上游的 store↔契約對證條件不成立而**維持舊行為**
    （舊 regex 抓不到 ⇒ R1a 照報），不會因為契約檔壞掉就靜默放行。
    """
    try:
        data = json.loads(TOGGLE_CONTRACT.read_text(encoding="utf-8"))
        return frozenset(data["stage_keys"]), frozenset(data["module_keys"])
    except Exception:  # noqa: BLE001
        return frozenset(), frozenset()


def _ts_string_array(src: str, name: str):
    """抓 `export const <name> = [ 'a', 'b' ] as const;` 之字串字面集合；抓不到回 None。"""
    block = re.search(rf"const {re.escape(name)}\s*=\s*\[([\s\S]*?)\]\s*as const;", src)
    if not block:
        return None
    return frozenset(re.findall(r"'([\w]+)'", block.group(1)))
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
    # 🔴 票 TIERTOGGLE（2026-09-10）：`getEffectiveConfig` 已改為**依契約鍵集迴圈**取值
    #    （`pick(STAGE_TOGGLE_KEYS)` / `pick(MODULE_TOGGLE_KEYS)`），不再逐鍵手寫
    #    `x: Boolean(state.featureToggles.x)` ⇒ 上面那條 regex 一個也抓不到，
    #    整組 toggle 會被誤報成 R1a 幽靈（本檢查因此自 `e8903c28` 起紅）。
    #    修法**不是**放寬：改成讀 store 實際迴圈的那兩個陣列，並要求它們與契約檔
    #    `ui_stage_toggles.json` 逐值相同——store 私自加鍵而契約沒登記 ⇒ 仍然紅。
    contract_stage, contract_module = _load_toggle_contract()
    store_stage = _ts_string_array(store_src, "STAGE_TOGGLE_KEYS")
    store_module = _ts_string_array(store_src, "MODULE_TOGGLE_KEYS")
    if store_stage is not None and store_module is not None:
        if store_stage != contract_stage:
            die(1, f"STAGE_TOGGLE_KEYS 與契約檔不符：store−契約={sorted(store_stage - contract_stage)} 契約−store={sorted(contract_stage - store_stage)}")
        if store_module != contract_module:
            die(1, f"MODULE_TOGGLE_KEYS 與契約檔不符：store−契約={sorted(store_module - contract_module)} 契約−store={sorted(contract_module - store_module)}")
        # 迴圈取值＝鍵名兩端相同（無轉名）⇒ 前端消費集與後端映射集皆為該鍵集。
        looped = store_stage | store_module
        if "pick(STAGE_TOGGLE_KEYS)" in eff_block.group(0) and "pick(MODULE_TOGGLE_KEYS)" in eff_block.group(0):
            consumed_frontend |= looped
            mapped_backend |= looped

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
