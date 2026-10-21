"""NUMVIEW Task 0.1（docs/NUMVIEW_SPEC.md）：數值政策契約 JSON 與讀取模組之驗收。

契約＝`momentum/FeatureEngineering/contracts/numeric_view.json`（SPEC §C 唯一真相源）；本檔不列舉任何值集之值，
只列 SPEC Task 0.1「改法」所點名之段名與入口名（結構），值一律讀契約。
驗證（SPEC Task 0.1）：①JSON 自洽（必要段齊、值合樣式 `^[a-z][a-z0-9_]*$`）；②`post_ic_arm_values ⊆
run_provenance.json group_arm_values.values`；③每個 `_sources` 之 `path:line` 存在且該行含引用字面；
④`ic_first_context.POST_IC_ARM == post_ic_arm("ic_first")`。
邊界：01 契約缺段 ⇒ `load_contract` 拋 `NumericPolicyError`（不回預設）；02 契約值含大寫或空白 ⇒ ①之檢查判違規。
mutation：`post_ic_arm_values` 加入 run_provenance 無之值 ⇒ ②紅；`_sources` 行號偏移一行 ⇒ ③紅。
測試接縫：`numeric_view.load_contract` 於呼叫時讀模組屬性 `CONTRACT_PATH`（測試以 monkeypatch 改指暫存檔）。
純 JSON／AST 級（秒級）；實作前應為紅（契約值未填、函式為 NotImplementedError）；不得以 skip／xfail 暫避。
"""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterator, List, Mapping, Tuple

import pytest

from momentum.FeatureEngineering import ic_first_context
from momentum.FeatureEngineering import numeric_view as nv

REPO = Path(__file__).resolve().parents[2]
RAW_CONTRACT: Dict[str, Any] = json.loads(nv.CONTRACT_PATH.read_text(encoding="utf-8"))
RUN_PROVENANCE: Dict[str, Any] = json.loads(
    (REPO / "momentum/FeatureEngineering/contracts/run_provenance.json").read_text(encoding="utf-8"))

#: SPEC Task 0.1「改法」所列契約段（結構，非值集）＋ `version`／`value_pattern`
REQUIRED_SECTIONS: Tuple[str, ...] = (
    "version", "value_pattern",
    "post_ic_entries", "post_ic_arm_values", "post_ic_arm_reachability", "processed_codec_mapping",
    "cgsa_work_identity", "auto_resolutions", "research_arms", "zscore_windows_policy", "winsor_method_values",
    "winsor_method_missing_key", "selectors", "selector_classes", "capability_flags", "library_versions",
    "algorithm_versions", "fingerprint_sections", "config_hash_salt", "run_identity_new_keys", "manifest_keys",
    "ic_page_output_attrs", "ic_page_response_keys", "ic_page_view_identity",
)
#: SPEC 正文點名之 post-IC 入口（`post_ic_entries.ic_first`、`post_ic_entries.ic_page_apply_transforms`）
REQUIRED_ENTRIES: Tuple[str, ...] = ("ic_first", "ic_page_apply_transforms")
#: 入口之臂政策欄（恰一）
ENTRY_POLICY_FIELDS: Tuple[str, ...] = ("arm", "arm_ref", "arm_policy")
#: SPEC Task 0.1 ①之值樣式（契約 `value_pattern` 須逐字等於此，防契約自行放寬）
SPEC_VALUE_PATTERN = "^[a-z][a-z0-9_]*$"
#: 受樣式約束之值集（`values` 清單）路徑
PATTERN_VALUE_LISTS: Tuple[str, ...] = (
    "post_ic_arm_values", "research_arms", "winsor_method_values", "selector_classes", "capability_flags",
    "library_versions", "fingerprint_sections",
)
#: 鍵即值之段（鍵受樣式約束）
PATTERN_KEYED_SECTIONS: Tuple[str, ...] = ("post_ic_entries", "post_ic_arm_reachability", "algorithm_versions")
#: Task 0.1 須填（非空）之值集：其餘段由 Task 0.2／4.x 填，其非空性由各該測試檔斷言
TASK01_NONEMPTY_LISTS: Tuple[str, ...] = ("post_ic_arm_values", "winsor_method_values", "selector_classes")

_SOURCE_RE = re.compile(r"^(?P<path>[^:\s]+):(?P<line>\d+)$")


# ---------------------------------------------------------------------------------------------- oracle（純函式）

def _real(key: str) -> bool:
    return not str(key).startswith("_")


def schema_violations(contract: Mapping[str, Any]) -> List[str]:
    """①：必要段齊、Task 0.1 所填之值集非空、受約束之值與鍵合 `SPEC_VALUE_PATTERN`、入口臂政策恰一欄、
    `arm_ref` 指向存在之入口、可達性涵蓋每個臂。回傳違規清單（空＝合規）。"""
    out: List[str] = []
    for section in REQUIRED_SECTIONS:
        if section not in contract:
            out.append(f"缺段：{section}")
    if out:
        return out
    if contract["value_pattern"] != SPEC_VALUE_PATTERN:
        out.append(f"value_pattern {contract['value_pattern']!r} ≠ SPEC {SPEC_VALUE_PATTERN!r}")
    pattern = re.compile(SPEC_VALUE_PATTERN)

    def check(where: str, value: Any) -> None:
        if not isinstance(value, str) or not pattern.fullmatch(value):
            out.append(f"{where}：{value!r} 不合 {SPEC_VALUE_PATTERN}")

    for section in PATTERN_VALUE_LISTS:
        values = contract[section].get("values")
        if not isinstance(values, list):
            out.append(f"{section}.values 非清單")
            continue
        for value in values:
            check(f"{section}.values", value)
    for section in TASK01_NONEMPTY_LISTS:
        if not contract[section].get("values"):
            out.append(f"{section}.values 為空（Task 0.1 未填）")
    for section in PATTERN_KEYED_SECTIONS:
        for key in contract[section]:
            if _real(key):
                check(f"{section} 之鍵", key)
    entries = {k: v for k, v in contract["post_ic_entries"].items() if _real(k)}
    for name in REQUIRED_ENTRIES:
        if name not in entries:
            out.append(f"post_ic_entries 缺入口：{name}")
    for name, entry in entries.items():
        fields = [f for f in ENTRY_POLICY_FIELDS if f in entry]
        if len(fields) != 1:
            out.append(f"post_ic_entries.{name} 之臂政策欄須恰一（{ENTRY_POLICY_FIELDS}），實得 {fields}")
            continue
        check(f"post_ic_entries.{name}.{fields[0]}", entry[fields[0]])
        if fields[0] == "arm" and entry["arm"] not in contract["post_ic_arm_values"]["values"]:
            out.append(f"post_ic_entries.{name}.arm={entry['arm']!r} 不屬 post_ic_arm_values")
        if fields[0] == "arm_ref" and entry["arm_ref"] not in entries:
            out.append(f"post_ic_entries.{name}.arm_ref 指向不存在之入口 {entry['arm_ref']!r}")
    reach = {k: v for k, v in contract["post_ic_arm_reachability"].items() if _real(k)}
    for arm in contract["post_ic_arm_values"]["values"]:
        if arm not in reach:
            out.append(f"post_ic_arm_reachability 缺臂 {arm!r}")
    for arm, cond in reach.items():
        check(f"post_ic_arm_reachability.{arm}.condition", (cond or {}).get("condition"))
        floor = (cond or {}).get("min_selected_columns")
        if not isinstance(floor, int) or isinstance(floor, bool) or floor < 1:
            out.append(f"post_ic_arm_reachability.{arm}.min_selected_columns 須為 ≥1 之整數，實得 {floor!r}")
    for name, sel in contract["selectors"].items():
        if _real(name) and isinstance(sel, Mapping):
            check(f"selectors.{name}.class", sel.get("class"))
    missing_key = contract["winsor_method_missing_key"].get("value")
    if missing_key is None:
        out.append("winsor_method_missing_key.value 未填")
    else:
        check("winsor_method_missing_key.value", missing_key)
    return out


def arm_subset_violations(contract: Mapping[str, Any]) -> List[str]:
    """②：`post_ic_arm_values ⊆ run_provenance.json group_arm_values.values`（兩契約皆讀檔）；空集合亦判違規
    （Task 0.1 未填不得以空集合通過）。"""
    arms = list(contract["post_ic_arm_values"]["values"])
    if not arms:
        return ["post_ic_arm_values 為空"]
    allowed = set(RUN_PROVENANCE["group_arm_values"]["values"])
    return [f"post_ic_arm_values 之 {a!r} 不屬 run_provenance group_arm_values" for a in arms if a not in allowed]


def iter_sources(node: Any, where: str = "") -> Iterator[Tuple[str, str, str]]:
    """遍歷契約之每個 `_sources`：產出（位置, `path:line`, 引用字面）。dict 形 `{值: [refs]}` 之字面＝值；
    list 形之字面＝同物件 `_literal`，缺則為該物件之鍵名（契約 `_doc` 所定）。"""
    if isinstance(node, Mapping):
        sources = node.get("_sources")
        owner = where.rsplit(".", 1)[-1] if where else ""
        if isinstance(sources, Mapping):
            for literal, refs in sources.items():
                for ref in (refs if isinstance(refs, list) else [refs]):
                    yield where, str(ref), str(literal)
        elif isinstance(sources, list):
            literal = str(node.get("_literal", owner))
            for ref in sources:
                yield where, str(ref), literal
        for key, value in node.items():
            if key in ("_sources", "_unreachable"):
                continue
            yield from iter_sources(value, f"{where}.{key}" if where else str(key))
    elif isinstance(node, list):
        for i, value in enumerate(node):
            yield from iter_sources(value, f"{where}[{i}]")


def source_violations(contract: Mapping[str, Any]) -> List[str]:
    """③：每個 `_sources` 為 `path:line`、檔存在、行存在且含引用字面。無任何 `_sources` 亦判違規（Task 0.1 須附碼證）。"""
    out: List[str] = []
    seen = 0
    for where, ref, literal in iter_sources(contract):
        seen += 1
        m = _SOURCE_RE.match(ref)
        if m is None:
            out.append(f"{where}：{ref!r} 非 path:line")
            continue
        target = REPO / m.group("path")
        if not target.is_file():
            out.append(f"{where}：{ref} 檔不存在")
            continue
        lines = target.read_text(encoding="utf-8").splitlines()
        n = int(m.group("line"))
        if not 1 <= n <= len(lines):
            out.append(f"{where}：{ref} 行不存在")
        elif literal not in lines[n - 1]:
            out.append(f"{where}：{ref} 之行不含引用字面 {literal!r}")
    if seen == 0:
        out.append("契約無任何 _sources（Task 0.1 未附碼證）")
    return out


def _write_contract(tmp_path: Path, contract: Mapping[str, Any]) -> Path:
    path = tmp_path / "numeric_view.json"
    path.write_text(json.dumps(contract, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------------------------- 驗證①–④

def test_contract_schema_self_consistent() -> None:
    """①：經 `load_contract` 讀得之契約必要段齊、值合樣式、Task 0.1 所填值集非空。"""
    contract = nv.load_contract()
    assert schema_violations(contract) == []


def test_contract_loader_returns_file_content() -> None:
    """`load_contract` 回傳＝契約檔內容（不另組、不補預設）。"""
    assert nv.load_contract() == RAW_CONTRACT


def test_post_ic_arm_values_subset_of_run_provenance() -> None:
    """②：`post_ic_arm_values ⊆ group_arm_values.values`（讀兩契約）。"""
    assert arm_subset_violations(nv.load_contract()) == []


def test_contract_sources_exist_and_contain_literal() -> None:
    """③：每個 `_sources` 之 `path:line` 存在且該行含引用字面。"""
    assert source_violations(nv.load_contract()) == []


def test_ic_first_post_ic_arm_equals_module_constant() -> None:
    """④：`ic_first_context.POST_IC_ARM == post_ic_arm("ic_first")`（Task 2.2 起前者改讀契約，本 Task 先斷言相等）。"""
    assert nv.post_ic_arm("ic_first") == ic_first_context.POST_IC_ARM


def test_post_ic_arm_unknown_entry_raises_policy_error() -> None:
    """未登記之入口 ⇒ `NumericPolicyError`（不回預設臂）。"""
    with pytest.raises(nv.NumericPolicyError):
        nv.post_ic_arm("numview_unregistered_entry")


# ---------------------------------------------------------------------------------------------- 邊界

@pytest.mark.parametrize("section", REQUIRED_SECTIONS)
def test_boundary_01_contract_missing_section_raises(section: str, tmp_path: Path,
                                                      monkeypatch: pytest.MonkeyPatch) -> None:
    """邊界①：契約檔缺任一必要段 ⇒ `load_contract` 拋 `NumericPolicyError`（不回預設）。"""
    broken = copy.deepcopy(RAW_CONTRACT)
    broken.pop(section)
    monkeypatch.setattr(nv, "CONTRACT_PATH", _write_contract(tmp_path, broken))
    with pytest.raises(nv.NumericPolicyError):
        nv.load_contract()


@pytest.mark.parametrize("bad_value", ["Polars", "pandas legacy"], ids=["uppercase", "space"])
def test_boundary_02_contract_value_uppercase_or_space_flagged(bad_value: str, tmp_path: Path,
                                                               monkeypatch: pytest.MonkeyPatch) -> None:
    """邊界②：契約值含大寫或空白 ⇒ ①之檢查判違規（經 `load_contract` 讀入之暫存契約）。"""
    broken = copy.deepcopy(RAW_CONTRACT)
    broken["post_ic_arm_values"]["values"] = list(broken["post_ic_arm_values"]["values"]) + [bad_value]
    monkeypatch.setattr(nv, "CONTRACT_PATH", _write_contract(tmp_path, broken))
    violations = schema_violations(nv.load_contract())
    assert any(repr(bad_value) in v for v in violations), violations


# ---------------------------------------------------------------------------------------------- mutation

def test_mutation_arm_value_outside_run_provenance_turns_subset_red(monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation：`post_ic_arm_values` 加入 run_provenance 無之值 ⇒ ②之檢查翻紅。"""
    bogus = "numview_mutant_arm"
    assert bogus not in RUN_PROVENANCE["group_arm_values"]["values"]
    mutated = copy.deepcopy(RAW_CONTRACT)
    mutated["post_ic_arm_values"]["values"] = list(mutated["post_ic_arm_values"]["values"]) + [bogus]
    monkeypatch.setattr(nv, "load_contract", lambda: copy.deepcopy(mutated))
    violations = arm_subset_violations(nv.load_contract())
    assert any(bogus in v for v in violations), violations


def test_mutation_source_line_shift_turns_sources_red(monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation：任一 `_sources` 行號偏移一行（改指該行之下一行且下一行不含引用字面）⇒ ③之檢查翻紅。"""
    refs = list(iter_sources(RAW_CONTRACT))
    assert refs, "契約無任何 _sources（Task 0.1 未附碼證）⇒ 本 mutation 無對象"
    target = None
    for where, ref, literal in refs:
        m = _SOURCE_RE.match(ref)
        if m is None:
            continue
        lines = (REPO / m.group("path")).read_text(encoding="utf-8").splitlines()
        n = int(m.group("line"))
        if n < len(lines) and literal not in lines[n]:
            target = (ref, f"{m.group('path')}:{n + 1}")
            break
    assert target is not None, "找不到下一行不含引用字面之 _sources ⇒ 無法構造偏移 mutant"
    mutated = json.loads(json.dumps(RAW_CONTRACT).replace(json.dumps(target[0]), json.dumps(target[1]), 1))
    monkeypatch.setattr(nv, "load_contract", lambda: copy.deepcopy(mutated))
    violations = source_violations(nv.load_contract())
    assert any(target[1] in v for v in violations), violations
