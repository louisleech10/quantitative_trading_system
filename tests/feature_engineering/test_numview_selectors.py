"""NUMVIEW Task 0.2（選擇子登記閘，全範圍 AST）與 Task 4.4（選擇子閘與身分之連動閘）之驗收（docs/NUMVIEW_SPEC.md）。

契約＝`momentum/FeatureEngineering/contracts/numeric_view.json`（SPEC §C 唯一真相源）。本檔不寫任何分類判斷（Task 0.2
「不可做」：只讀契約），只用 SPEC 點名之字面：類別 `value_affecting`／`output_only`／`non_value`／`certified_equal`、
Task 0.2 所列 `output_only` 封閉五鍵、`FFACT_FEATURE_REGISTRY_PATH`、`FFACT_L7_CODEC_UPGRADE`、`FFACT_L3_PERSIST_MODE`、
既有機制名 `FeatureFactory.L2_ROUTE_CERTIFIED`。

驗證（Task 0.2）：AST 掃描 `git ls-files 'momentum/*.py' 'api/*.py'` 之全部字串常值符合 `^FFACT_[A-Z0-9_]+$` 者
（不設檔案白名單；`os.getenv`、`os.environ[...]`、`selector(...)`、寫入子行程環境者一律為字串常值）＝契約 `selectors`
鍵集（多 ⇒「未登記」紅、少 ⇒「過期登記」紅）；分類讀契約 `selector_classes`：除 `output_only_keys` 外一律
`value_affecting`，`output_only_keys` 恰為 SPEC 五鍵且標 `output_only`；無 `non_value`；`certified_equal` 只限既有
`L2_ROUTE_CERTIFIED` 機制（現為空集合 ⇒ 實際不得有）；`FFACT_FEATURE_REGISTRY_PATH` 為 `value_affecting`；每鍵具非空
`reason`、`parser` 與 `_sources`（`path:line`，該行含該鍵）；`memory_budget.SELECTORS ∪ NON_ARM_FFACT_KEYS ⊆ selectors`；
`capability_flags.values` 非空；掃描＋全部檢查 < 10 秒。
驗證（Task 4.4）：`numeric_view.resolve_numeric_fingerprint` 實際讀取之環境鍵集合（以記錄存取之 Mapping 觀測）＝契約
`value_affecting` 鍵集合（`output_only` 鍵不得被讀）。
邊界：03（Task 0.2 邊界①）鍵名以 f-string／串接組成 ⇒ AST 另掃 `JoinedStr`／`BinOp`／`.format` 含 `FFACT_` 前綴者即紅；
04（Task 0.2 邊界②）`api/` 只寫入子行程環境而不讀之鍵同樣須登記；55（Task 4.4 邊界①）契約有不屬
{`value_affecting`、`output_only`（限 SPEC 五鍵）、`certified_equal`（限 L2 機制）} 之類別 ⇒ 紅；56（Task 4.4 邊界②）
能力旗標新增即須被解析器讀取。
mutation（Task 0.2）：於 `feature_preprocessor.py` 暫加 `os.getenv("FFACT_NUMVIEW_MUTANT")`（經掃描器讀檔接縫注入，不改
實檔）⇒ 紅；契約刪 `FFACT_L7_CODEC_UPGRADE` ⇒ 紅；任一鍵標 `non_value` ⇒ 紅；`output_only` 集合增一鍵／減一鍵 ⇒ 紅；
任一鍵標 `certified_equal` 而非經 `L2_ROUTE_CERTIFIED` ⇒ 紅。（SPEC 另列「`FFACT_CGSA_WORK_DIR` 改入鹽 ⇒ Task 4.2 ⑦(e)
紅」由 `tests/feature_engineering/test_numview_cgsa_workdir.py`／Task 4.2 之測試承擔，本檔不重做。）
mutation（Task 4.4）：契約新增一個 `value_affecting` 鍵而解析器未讀 ⇒ 紅；契約將任一鍵改標 `non_value` ⇒ 紅。

測試接縫（實作須提供）：
- `numeric_view.load_contract()` 每次呼叫時讀檔（測試以 monkeypatch 換回傳值注入契約 mutant）。
- `numeric_view.resolve_numeric_fingerprint(*, preprocessing_config, environ, capabilities)` 只經傳入之 `environ`
  （以 `environ.get(key)`／`environ[key]`／`key in environ` 逐鍵查；迭代整個 environ 亦記為讀取其中全部鍵）讀環境，
  不得另讀 `os.environ`；能力旗標只經傳入之 `capabilities` 讀取（逐旗標查）。本檔以空 environ（全部取預設）呼叫一次。
- 契約 `selectors.<KEY>`：`{"class", "parser", "reason", "_sources": [path:line…]}`；`certified_equal` 者另須
  `"certified_by": "L2_ROUTE_CERTIFIED"`（本檔定義之欄名）。
純 JSON／AST 級（秒級，不生成）；實作前應為紅（契約值未填、解析器為 NotImplementedError）；不得以 skip／xfail 暫避。
"""

from __future__ import annotations

import ast
from collections import abc
import copy
import json
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterator, List, Mapping, Set, Tuple

import pytest

from momentum.FeatureEngineering import memory_budget as mb
from momentum.FeatureEngineering import numeric_view as nv
from momentum.FeatureEngineering.feature_config import PreprocessingConfig
from momentum.FeatureEngineering.feature_factory import FeatureFactory

REPO = Path(__file__).resolve().parents[2]
RAW_CONTRACT: Dict[str, Any] = json.loads(nv.CONTRACT_PATH.read_text(encoding="utf-8"))

KEY_RE = re.compile(r"^FFACT_[A-Z0-9_]+$")
#: 動態組鍵偵測：常值片段以 `FFACT_` 起首之鍵前綴收尾（其後接非常值）
_DYN_TAIL_RE = re.compile(r"FFACT_[A-Z0-9_]*$")
_DYN_FORMAT_RE = re.compile(r"FFACT_[A-Z0-9_]*(\{|%)")
_SOURCE_RE = re.compile(r"^(?P<path>[^:\s]+):(?P<line>\d+)$")

#: SPEC 點名之類別字面（先斷言其屬契約 `selector_classes.values`）
VALUE_AFFECTING = "value_affecting"
OUTPUT_ONLY = "output_only"
NON_VALUE = "non_value"
CERTIFIED_EQUAL = "certified_equal"
#: SPEC Task 0.2 之 `output_only` 封閉清單（增列須改 SPEC）
SPEC_OUTPUT_ONLY_KEYS = frozenset({
    "FFACT_CGSA_WORK_DIR", "FFACT_API_LOG_PATH", "FFACT_CHILD_METRICS_PATH", "FFACT_LAYER_METRICS_PATH",
    "FFACT_UVICORN_ACCESS_LOG",
})
#: 既有認證機制（`feature_factory.py:1803`）
L2_MECHANISM_NAME = "L2_ROUTE_CERTIFIED"
CERTIFIED_BY_FIELD = "certified_by"
MUTANT_TARGET_FILE = "momentum/FeatureEngineering/preprocessing/feature_preprocessor.py"
MUTANT_KEY = "FFACT_NUMVIEW_MUTANT"
TIME_BUDGET_SECONDS = 10.0


# ---------------------------------------------------------------------------------------------- 掃描器（純 AST）

def _tracked_sources() -> List[str]:
    """`git ls-files 'momentum/*.py' 'api/*.py'`（SPEC Task 0.2 範圍；不得以檔案白名單縮小）。"""
    out = subprocess.run(["git", "ls-files", "momentum/*.py", "api/*.py"], cwd=REPO, capture_output=True,
                         text=True, check=True).stdout.split()
    return sorted(out)


def _read_source(rel: str) -> str:
    """掃描器讀檔之唯一入口（mutation 以 monkeypatch 換之，不改實檔）。"""
    return (REPO / rel).read_text(encoding="utf-8")


def _is_env_like(node: ast.AST) -> bool:
    if isinstance(node, ast.Attribute):
        return node.attr in ("environ", "env")
    if isinstance(node, ast.Name):
        return node.id in ("environ", "env") or node.id.endswith("_env") or node.id.endswith("env_overrides")
    return False


@dataclass
class ScanResult:
    keys: Dict[str, List[str]] = field(default_factory=dict)       # 鍵 → 出現位置（path:line）
    dynamic: List[str] = field(default_factory=list)               # 動態組鍵之位置
    api_reads: Set[str] = field(default_factory=set)               # api/ 直接讀環境之鍵
    api_writes: Set[str] = field(default_factory=set)              # api/ 寫入環境（含子行程／暫設環境）之鍵
    files: int = 0


def _scan_tree(rel: str, tree: ast.AST, result: ScanResult) -> None:
    in_api = rel.startswith("api/")
    env_dict_ids: Set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and "env" in node.name.lower():
            for sub in ast.walk(node):
                if isinstance(sub, ast.Dict):
                    env_dict_ids.add(id(sub))
        if isinstance(node, ast.keyword) and node.arg and "env" in node.arg.lower() and isinstance(node.value, ast.Dict):
            env_dict_ids.add(id(node.value))
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and KEY_RE.match(node.value):
            result.keys.setdefault(node.value, []).append(f"{rel}:{node.lineno}")
        if isinstance(node, ast.JoinedStr):
            parts = node.values
            for i, part in enumerate(parts):
                if (isinstance(part, ast.Constant) and isinstance(part.value, str) and i + 1 < len(parts)
                        and isinstance(parts[i + 1], ast.FormattedValue) and _DYN_TAIL_RE.search(part.value)):
                    result.dynamic.append(f"{rel}:{node.lineno} JoinedStr {part.value!r}")
        if isinstance(node, ast.BinOp):
            left = node.left
            if isinstance(left, ast.Constant) and isinstance(left.value, str):
                if isinstance(node.op, ast.Add) and _DYN_TAIL_RE.search(left.value):
                    result.dynamic.append(f"{rel}:{node.lineno} BinOp+ {left.value!r}")
                if isinstance(node.op, ast.Mod) and _DYN_FORMAT_RE.search(left.value):
                    result.dynamic.append(f"{rel}:{node.lineno} BinOp% {left.value!r}")
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "format"
                and isinstance(node.func.value, ast.Constant) and isinstance(node.func.value.value, str)
                and _DYN_FORMAT_RE.search(node.func.value.value)):
            result.dynamic.append(f"{rel}:{node.lineno} format {node.func.value.value!r}")
        if not in_api:
            continue
        # api/ 讀寫位置（邊界 04）
        if isinstance(node, ast.Call) and node.args and isinstance(node.args[0], ast.Constant):
            key = node.args[0].value
            if isinstance(key, str) and KEY_RE.match(key):
                func = node.func
                name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
                owner = func.value if isinstance(func, ast.Attribute) else None
                if name == "getenv" or (name in ("get", "pop") and owner is not None and _is_env_like(owner)):
                    result.api_reads.add(key)
                if name == "setdefault" and owner is not None and _is_env_like(owner):
                    result.api_writes.add(key)
        if isinstance(node, ast.Subscript) and _is_env_like(node.value):
            key_node = node.slice.value if isinstance(node.slice, ast.Index) else node.slice  # type: ignore[attr-defined]
            if isinstance(key_node, ast.Constant) and isinstance(key_node.value, str) and KEY_RE.match(key_node.value):
                if isinstance(node.ctx, ast.Store):
                    result.api_writes.add(key_node.value)
                else:
                    result.api_reads.add(key_node.value)
        if isinstance(node, ast.Compare) and isinstance(node.left, ast.Constant) and isinstance(node.left.value, str):
            if KEY_RE.match(node.left.value) and any(isinstance(op, (ast.In, ast.NotIn)) for op in node.ops) \
                    and any(_is_env_like(c) for c in node.comparators):
                result.api_reads.add(node.left.value)
        if isinstance(node, ast.Dict) and id(node) in env_dict_ids:
            for k in node.keys:
                if isinstance(k, ast.Constant) and isinstance(k.value, str) and KEY_RE.match(k.value):
                    result.api_writes.add(k.value)


#: 逐檔掃描結果快取，鍵＝（路徑, 檔文全文）：文字一變即重掃（mutation 注入之文字不會命中原檔之快取）
_FILE_SCAN_CACHE: Dict[Tuple[str, str], ScanResult] = {}


def _scan_file(rel: str, text: str) -> ScanResult:
    cached = _FILE_SCAN_CACHE.get((rel, text))
    if cached is None:
        cached = ScanResult()
        _scan_tree(rel, ast.parse(text, filename=rel), cached)
        _FILE_SCAN_CACHE[(rel, text)] = cached
    return cached


def scan_repo() -> ScanResult:
    """全範圍 AST 掃描（`_tracked_sources()` 之每一檔；讀檔一律經 `_read_source`，每次呼叫皆重讀檔文）。"""
    result = ScanResult()
    for rel in _tracked_sources():
        part = _scan_file(rel, _read_source(rel))
        for key, locs in part.keys.items():
            result.keys.setdefault(key, []).extend(locs)
        result.dynamic.extend(part.dynamic)
        result.api_reads |= part.api_reads
        result.api_writes |= part.api_writes
        result.files += 1
    return result


# ---------------------------------------------------------------------------------------------- 檢查（只讀契約）

def _selectors(contract: Mapping[str, Any]) -> Dict[str, Mapping[str, Any]]:
    return {k: v for k, v in contract["selectors"].items() if not str(k).startswith("_")}


def registration_violations(scan: ScanResult, contract: Mapping[str, Any]) -> List[str]:
    """掃描鍵集合＝契約 `selectors` 鍵集；空集合亦判違規（不得以兩邊皆空通過）。"""
    found = set(scan.keys)
    registered = set(_selectors(contract))
    out = [f"未登記：{k}（{scan.keys[k][0]}）" for k in sorted(found - registered)]
    out += [f"過期登記：{k}（契約有、碼中無）" for k in sorted(registered - found)]
    if not found:
        out.append("掃描未見任何 FFACT_ 鍵（掃描器失效）")
    if not registered:
        out.append("契約 selectors 為空（Task 0.2 未填）")
    return out


def selector_class_violations(contract: Mapping[str, Any], certified_mechanism: frozenset) -> List[str]:
    """分類：類別值集讀契約；除 `output_only_keys` 外一律 `value_affecting`；`output_only_keys` 恰為 SPEC 五鍵且標
    `output_only`；不得 `non_value`；`certified_equal` 只限 `L2_ROUTE_CERTIFIED` 機制（非空且該鍵 `certified_by` 指之）；
    `FFACT_FEATURE_REGISTRY_PATH` 須 `value_affecting`。"""
    out: List[str] = []
    classes_node = contract["selector_classes"]
    classes = list(classes_node.get("values") or [])
    for literal in (VALUE_AFFECTING, OUTPUT_ONLY):
        if literal not in classes:
            out.append(f"selector_classes.values 缺 SPEC 類別 {literal!r}")
    output_only = set(classes_node.get("output_only_keys") or [])
    if output_only != SPEC_OUTPUT_ONLY_KEYS:
        out.append(f"output_only_keys 與 SPEC 五鍵不等：多 {sorted(output_only - SPEC_OUTPUT_ONLY_KEYS)}、"
                   f"少 {sorted(SPEC_OUTPUT_ONLY_KEYS - output_only)}")
    for key, sel in sorted(_selectors(contract).items()):
        cls = sel.get("class") if isinstance(sel, Mapping) else None
        if cls not in classes:
            out.append(f"{key}：類別 {cls!r} 不屬 selector_classes.values")
        if cls == NON_VALUE:
            out.append(f"{key}：標 non_value（本票不設排除）")
        elif cls == CERTIFIED_EQUAL:
            if not certified_mechanism or sel.get(CERTIFIED_BY_FIELD) != L2_MECHANISM_NAME:
                out.append(f"{key}：標 certified_equal 而非經既有 {L2_MECHANISM_NAME} 機制所登錄")
        elif cls == OUTPUT_ONLY:
            if key not in SPEC_OUTPUT_ONLY_KEYS or key not in output_only:
                out.append(f"{key}：標 output_only 而不屬 SPEC 封閉五鍵／output_only_keys")
        elif cls != VALUE_AFFECTING:
            out.append(f"{key}：類別 {cls!r} 非 value_affecting／output_only／certified_equal")
        if key in output_only and cls != OUTPUT_ONLY:
            out.append(f"{key}：列於 output_only_keys 而類別為 {cls!r}")
        if key in SPEC_OUTPUT_ONLY_KEYS and cls != OUTPUT_ONLY:
            out.append(f"{key}：SPEC 五鍵之一而類別為 {cls!r}")
    registry = _selectors(contract).get("FFACT_FEATURE_REGISTRY_PATH")
    if not isinstance(registry, Mapping) or registry.get("class") != VALUE_AFFECTING:
        out.append("FFACT_FEATURE_REGISTRY_PATH 須登記為 value_affecting")
    return out


def selector_field_violations(contract: Mapping[str, Any]) -> List[str]:
    """每鍵：非空 `reason`、`parser`；`_sources` 非空，皆 `path:line`、檔與行存在、該行含該鍵。"""
    out: List[str] = []
    cache: Dict[str, List[str]] = {}
    for key, sel in sorted(_selectors(contract).items()):
        if not isinstance(sel, Mapping):
            out.append(f"{key}：登記非物件")
            continue
        for fld in ("reason", "parser"):
            if not isinstance(sel.get(fld), str) or not sel.get(fld).strip():
                out.append(f"{key}：缺非空 {fld}")
        sources = sel.get("_sources")
        if not isinstance(sources, list) or not sources:
            out.append(f"{key}：缺 _sources")
            continue
        for ref in sources:
            m = _SOURCE_RE.match(str(ref))
            if m is None:
                out.append(f"{key}：{ref!r} 非 path:line")
                continue
            path = m.group("path")
            if path not in cache:
                target = REPO / path
                cache[path] = target.read_text(encoding="utf-8").splitlines() if target.is_file() else []
            lines = cache[path]
            n = int(m.group("line"))
            if not 1 <= n <= len(lines):
                out.append(f"{key}：{ref} 檔或行不存在")
            elif key not in lines[n - 1]:
                out.append(f"{key}：{ref} 之行不含該鍵")
    return out


def memory_budget_violations(contract: Mapping[str, Any]) -> List[str]:
    """`memory_budget.SELECTORS ∪ NON_ARM_FFACT_KEYS ⊆ selectors`。"""
    union = set(mb.SELECTORS) | set(mb.NON_ARM_FFACT_KEYS)
    return [f"memory_budget 之 {k} 未登記於契約 selectors" for k in sorted(union - set(_selectors(contract)))]


def capability_violations(contract: Mapping[str, Any]) -> List[str]:
    values = list(contract["capability_flags"].get("values") or [])
    return [] if values else ["capability_flags.values 為空（Task 0.2 未填）"]


def dynamic_key_violations(scan: ScanResult) -> List[str]:
    return [f"鍵名非常值（須改為字串常值）：{loc}" for loc in scan.dynamic]


def all_task02_violations(scan: ScanResult, contract: Mapping[str, Any]) -> List[str]:
    return (registration_violations(scan, contract)
            + selector_class_violations(contract, FeatureFactory.L2_ROUTE_CERTIFIED)
            + selector_field_violations(contract) + memory_budget_violations(contract)
            + capability_violations(contract) + dynamic_key_violations(scan))


# ---------------------------------------------------------------------------------------------- Task 4.4：解析器讀取紀錄

class RecordingMapping(abc.Mapping):
    """記錄每個被存取之鍵（`__getitem__`／`get`／`__contains__`；迭代 ⇒ 記為讀取其中全部鍵）。"""

    def __init__(self, data: Mapping[str, Any]) -> None:
        self._data = dict(data)
        self.accessed: Set[str] = set()

    def __getitem__(self, key: str) -> Any:
        self.accessed.add(key)
        return self._data[key]

    def get(self, key: str, default: Any = None) -> Any:
        self.accessed.add(key)
        return self._data.get(key, default)

    def __contains__(self, key: object) -> bool:
        self.accessed.add(str(key))
        return key in self._data

    def __iter__(self) -> Iterator[str]:
        self.accessed.update(self._data)
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)


def _preprocessing_config() -> Dict[str, Any]:
    """真實生產預設前處理設定（`FactoryConfig.preprocessing` 之 default_factory＝`PreprocessingConfig()`，
    `feature_config.py:617`；`FactoryConfig()` 有必填欄位不能無參數建構）。"""
    return PreprocessingConfig().model_dump()


def record_resolver_reads() -> Tuple[Set[str], Set[str]]:
    """以空 environ（全部取預設）與契約全部能力旗標為 True 呼叫解析器一次；回傳（環境鍵讀取集合、能力旗標讀取集合）。"""
    contract = nv.load_contract()
    environ = RecordingMapping({})
    capabilities = RecordingMapping({flag: True for flag in contract["capability_flags"]["values"]})
    nv.resolve_numeric_fingerprint(preprocessing_config=_preprocessing_config(), environ=environ,
                                   capabilities=capabilities)
    return set(environ.accessed), set(capabilities.accessed)


def resolver_link_violations(env_read: Set[str], caps_read: Set[str]) -> List[str]:
    """解析器所讀之環境鍵＝契約 `value_affecting` 鍵集；契約每個能力旗標皆被讀；類別違規一併列（邊界 55）。
    契約一律經 `nv.load_contract()` 讀（mutation 以 monkeypatch 換之）。"""
    contract = nv.load_contract()
    out = selector_class_violations(contract, FeatureFactory.L2_ROUTE_CERTIFIED)
    expected = {k for k, sel in _selectors(contract).items()
                if isinstance(sel, Mapping) and sel.get("class") == VALUE_AFFECTING}
    if not expected:
        out.append("契約無 value_affecting 鍵（Task 0.2 未填）")
    out += [f"解析器未讀 value_affecting 鍵：{k}" for k in sorted(expected - env_read)]
    out += [f"解析器讀了非 value_affecting 之鍵：{k}" for k in sorted(env_read - expected)]
    flags = set(contract["capability_flags"].get("values") or [])
    if not flags:
        out.append("capability_flags.values 為空")
    out += [f"解析器未讀能力旗標：{f}" for f in sorted(flags - caps_read)]
    return out


@pytest.fixture(scope="module")
def resolver_reads() -> Tuple[Set[str], Set[str]]:
    return record_resolver_reads()


def _first_value_affecting_key(contract: Mapping[str, Any]) -> str:
    keys = sorted(k for k, sel in _selectors(contract).items()
                  if isinstance(sel, Mapping) and sel.get("class") == VALUE_AFFECTING)
    assert keys, "契約無 value_affecting 鍵（Task 0.2 未填）⇒ 本案無對象"
    return keys[0]


# ---------------------------------------------------------------------------------------------- 驗證（Task 0.2）

def test_scanned_keys_equal_contract_selectors() -> None:
    """Task 0.2：掃描所得 `FFACT_*` 字串常值集合＝契約 `selectors` 鍵集（未登記／過期登記皆紅）。"""
    assert registration_violations(scan_repo(), nv.load_contract()) == []


def test_scan_covers_full_git_scope_without_whitelist() -> None:
    """Task 0.2「不可做」：掃描範圍＝`git ls-files 'momentum/*.py' 'api/*.py'` 全部（含 preprocessing／storage／core
    config），且確實見到 SPEC 點名之鍵（`FFACT_L7_CODEC_UPGRADE` 於 `momentum/core/config.py`）。"""
    files = _tracked_sources()
    for rel in ("momentum/core/config.py", MUTANT_TARGET_FILE, "momentum/FeatureEngineering/feature_storage.py",
                "api/main.py"):
        assert rel in files, rel
    scan = scan_repo()
    assert scan.files == len(files)
    assert any(loc.startswith("momentum/core/config.py:") for loc in scan.keys.get("FFACT_L7_CODEC_UPGRADE", []))


def test_selector_classes_follow_spec() -> None:
    """Task 0.2：分類讀契約；除 SPEC 五鍵（`output_only`）外一律 `value_affecting`；無 `non_value`；`certified_equal`
    只限 `L2_ROUTE_CERTIFIED`（現為空集合）；`FFACT_FEATURE_REGISTRY_PATH` 為 `value_affecting`。"""
    assert selector_class_violations(nv.load_contract(), FeatureFactory.L2_ROUTE_CERTIFIED) == []


def test_selector_entries_have_reason_parser_and_sources() -> None:
    """Task 0.2：每鍵具非空 `reason`、`parser`，`_sources` 之 `path:line` 存在且該行含該鍵。"""
    assert selector_field_violations(nv.load_contract()) == []


def test_memory_budget_selectors_subset_of_contract() -> None:
    """Task 0.2：`memory_budget.SELECTORS ∪ NON_ARM_FFACT_KEYS ⊆ selectors`。"""
    assert set(mb.SELECTORS) and set(mb.NON_ARM_FFACT_KEYS)
    assert memory_budget_violations(nv.load_contract()) == []


def test_capability_flags_registered() -> None:
    """Task 0.2：非環境能力旗標登記於 `capability_flags`（非空）。"""
    assert capability_violations(nv.load_contract()) == []


def test_selector_gate_runs_under_ten_seconds() -> None:
    """Task 0.2／4.4：全範圍掃描＋全部檢查＋解析器連動檢查 < 10 秒（SPEC「嚴禁慢閘」）。"""
    started = time.monotonic()
    scan = scan_repo()
    contract = nv.load_contract()
    task02 = all_task02_violations(scan, contract)
    link = resolver_link_violations(*record_resolver_reads())
    elapsed = time.monotonic() - started
    assert elapsed < TIME_BUDGET_SECONDS, f"選擇子閘耗時 {elapsed:.2f}s ≥ {TIME_BUDGET_SECONDS}s"
    assert task02 == [] and link == [], task02 + link


# ---------------------------------------------------------------------------------------------- 驗證（Task 4.4）

def test_resolver_reads_exactly_value_affecting_keys(resolver_reads: Tuple[Set[str], Set[str]]) -> None:
    """Task 4.4：`resolve_numeric_fingerprint` 所讀環境鍵集合＝契約 `value_affecting` 鍵集合；`output_only` 不被讀。"""
    env_read, caps_read = resolver_reads
    assert not (env_read & SPEC_OUTPUT_ONLY_KEYS), sorted(env_read & SPEC_OUTPUT_ONLY_KEYS)
    assert resolver_link_violations(env_read, caps_read) == []


# ---------------------------------------------------------------------------------------------- 邊界

@pytest.mark.parametrize("sample", [
    'import os\nos.getenv(f"FFACT_{name}")\n',
    'import os\nos.getenv("FFACT_" + name)\n',
    'import os\nos.environ["FFACT_L65_%s" % name]\n',
    'import os\nos.getenv("FFACT_{}".format(name))\n',
], ids=["joinedstr", "binop_add", "binop_mod", "str_format"])
def test_boundary_03_dynamic_ffact_key_name_flagged(sample: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """邊界①（SPEC Task 0.2）：鍵名以 f-string 或串接組成 ⇒ AST 另掃 `JoinedStr`／`BinOp`（含 `.format`）含 `FFACT_`
    前綴者即紅。現行 repo 須無此類（全範圍掃描）；並以掃描器讀檔接縫於 `feature_preprocessor.py` 注入樣本，偵測器須命中。"""
    assert dynamic_key_violations(scan_repo()) == []
    original = _read_source
    this = sys.modules[__name__]
    monkeypatch.setattr(this, "_read_source",
                        lambda rel: original(rel) + ("\n" + sample if rel == MUTANT_TARGET_FILE else ""))
    violations = dynamic_key_violations(scan_repo())
    assert any(f"：{MUTANT_TARGET_FILE}:" in v for v in violations), violations


def test_boundary_04_api_child_env_write_only_keys_registered() -> None:
    """邊界②（SPEC Task 0.2）：`api/` 只寫入（子行程／暫設）環境而不讀之鍵同樣須登記（SPEC 例 `FFACT_L3_PERSIST_MODE`）。
    寫入位置＝環境物件之下標賦值、`setdefault`、名稱含 env 之函式內或 `env*=` 關鍵字之 dict 常值之鍵（如
    `api/services/feature_factory_service.py` 之 `_old_path_env_overrides`）；讀取位置＝`getenv`、環境物件之 `get`／`pop`／
    下標讀／`in`。只寫不讀之集合須非空（偵測器有效）且 ⊆ 契約 selectors。"""
    scan = scan_repo()
    write_only = scan.api_writes - scan.api_reads
    assert write_only, "api/ 只寫不讀之鍵集合為空 ⇒ 偵測器失效（現行 repo 至少有 env_overrides 之寫入）"
    registered = set(_selectors(nv.load_contract()))
    assert sorted(write_only - registered) == []
    assert "FFACT_L3_PERSIST_MODE" in registered


@pytest.mark.parametrize("bad", ["non_value", "numview_unknown_class", "certified_equal", "output_only"])
def test_boundary_55_contract_class_outside_allowed_set_red(bad: str, monkeypatch: pytest.MonkeyPatch,
                                                           resolver_reads: Tuple[Set[str], Set[str]]) -> None:
    """邊界①（SPEC Task 4.4）：本票無排除；契約有不屬 {`value_affecting`、`output_only`（限 SPEC 五鍵）、
    `certified_equal`（限既有 `L2_ROUTE_CERTIFIED` 機制）} 之鍵 ⇒ 連動閘紅。（SPEC 該句字面為「遇契約有非
    `value_affecting` 鍵即紅」，與 Task 0.2 之 `output_only` 五鍵矛盾；本案依 Task 0.2 例外解讀。）"""
    assert resolver_link_violations(*resolver_reads) == []
    mutated = copy.deepcopy(RAW_CONTRACT)
    key = _first_value_affecting_key(mutated)
    mutated["selectors"][key]["class"] = bad
    if bad not in mutated["selector_classes"]["values"]:
        mutated["selector_classes"]["values"] = list(mutated["selector_classes"]["values"]) + [bad]
    monkeypatch.setattr(nv, "load_contract", lambda: copy.deepcopy(mutated))
    violations = resolver_link_violations(*resolver_reads)
    assert any(v.startswith(f"{key}：") for v in violations), violations


def test_boundary_56_new_capability_flag_must_be_read(monkeypatch: pytest.MonkeyPatch,
                                                     resolver_reads: Tuple[Set[str], Set[str]]) -> None:
    """邊界②（SPEC Task 4.4）：契約每個能力旗標皆被解析器自 `capabilities` 讀取；新增一旗標而解析器未讀 ⇒ 紅。"""
    env_read, caps_read = resolver_reads
    flags = set(nv.load_contract()["capability_flags"]["values"])
    assert flags and flags <= caps_read, sorted(flags - caps_read)
    mutated = copy.deepcopy(RAW_CONTRACT)
    mutated["capability_flags"]["values"] = list(mutated["capability_flags"]["values"]) + ["numview_mutant_flag"]
    monkeypatch.setattr(nv, "load_contract", lambda: copy.deepcopy(mutated))
    assert "解析器未讀能力旗標：numview_mutant_flag" in resolver_link_violations(env_read, caps_read)


# ---------------------------------------------------------------------------------------------- mutation（Task 0.2）

def test_mutation_injected_getenv_in_preprocessor_is_unregistered(monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation：於 `feature_preprocessor.py` 暫加 `os.getenv("FFACT_NUMVIEW_MUTANT")`（經 `_read_source` 接縫，不改實檔）
    ⇒ 登記閘報「未登記」。"""
    assert registration_violations(scan_repo(), nv.load_contract()) == []
    original = _read_source
    monkeypatch.setattr(sys.modules[__name__], "_read_source",
                        lambda rel: original(rel) + (f'\nos.getenv("{MUTANT_KEY}")\n' if rel == MUTANT_TARGET_FILE else ""))
    violations = registration_violations(scan_repo(), nv.load_contract())
    assert any(v.startswith(f"未登記：{MUTANT_KEY}（{MUTANT_TARGET_FILE}:") for v in violations), violations


def test_mutation_contract_drops_l7_codec_upgrade(monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation：自契約刪 `FFACT_L7_CODEC_UPGRADE` ⇒ 登記閘報「未登記」。"""
    scan = scan_repo()
    assert "FFACT_L7_CODEC_UPGRADE" in scan.keys
    assert "FFACT_L7_CODEC_UPGRADE" in RAW_CONTRACT["selectors"], "契約未登記 FFACT_L7_CODEC_UPGRADE（Task 0.2 未填）"
    mutated = copy.deepcopy(RAW_CONTRACT)
    mutated["selectors"].pop("FFACT_L7_CODEC_UPGRADE")
    monkeypatch.setattr(nv, "load_contract", lambda: copy.deepcopy(mutated))
    violations = registration_violations(scan, nv.load_contract())
    assert any(v.startswith("未登記：FFACT_L7_CODEC_UPGRADE") for v in violations), violations


def test_mutation_any_key_non_value_red(monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation：任一鍵標 `non_value` ⇒ 分類檢查紅（本票不設排除）。"""
    assert selector_class_violations(RAW_CONTRACT, FeatureFactory.L2_ROUTE_CERTIFIED) == []
    mutated = copy.deepcopy(RAW_CONTRACT)
    key = _first_value_affecting_key(mutated)
    mutated["selectors"][key]["class"] = NON_VALUE
    monkeypatch.setattr(nv, "load_contract", lambda: copy.deepcopy(mutated))
    violations = selector_class_violations(nv.load_contract(), FeatureFactory.L2_ROUTE_CERTIFIED)
    assert f"{key}：標 non_value（本票不設排除）" in violations, violations


@pytest.mark.parametrize("direction", ["add_one", "remove_one"])
def test_mutation_output_only_set_differs_from_spec_five(direction: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation：契約 `output_only` 集合與 SPEC 五鍵不等（增一鍵或減一鍵；類別同步改）⇒ 紅。"""
    assert selector_class_violations(RAW_CONTRACT, FeatureFactory.L2_ROUTE_CERTIFIED) == []
    mutated = copy.deepcopy(RAW_CONTRACT)
    keys = list(mutated["selector_classes"]["output_only_keys"])
    if direction == "add_one":
        extra = _first_value_affecting_key(mutated)
        keys.append(extra)
        mutated["selectors"][extra]["class"] = OUTPUT_ONLY
    else:
        removed = sorted(SPEC_OUTPUT_ONLY_KEYS)[0]
        keys = [k for k in keys if k != removed]
        mutated["selectors"][removed]["class"] = VALUE_AFFECTING
    mutated["selector_classes"]["output_only_keys"] = keys
    monkeypatch.setattr(nv, "load_contract", lambda: copy.deepcopy(mutated))
    violations = selector_class_violations(nv.load_contract(), FeatureFactory.L2_ROUTE_CERTIFIED)
    assert any(v.startswith("output_only_keys 與 SPEC 五鍵不等") for v in violations), violations


@pytest.mark.parametrize("with_mechanism_field", [False, True], ids=["no_certified_by", "certified_by_but_empty"])
def test_mutation_certified_equal_outside_l2_mechanism(with_mechanism_field: bool,
                                                       monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation：任一鍵標 `certified_equal` 而非既有 `L2_ROUTE_CERTIFIED` 機制所登錄（未指機制；或指機制而機制為空
    集合）⇒ 紅。"""
    assert FeatureFactory.L2_ROUTE_CERTIFIED == frozenset(), "既有機制非空 ⇒ 本案前提改變，須重審"
    assert selector_class_violations(RAW_CONTRACT, FeatureFactory.L2_ROUTE_CERTIFIED) == []
    mutated = copy.deepcopy(RAW_CONTRACT)
    key = _first_value_affecting_key(mutated)
    mutated["selectors"][key]["class"] = CERTIFIED_EQUAL
    if with_mechanism_field:
        mutated["selectors"][key][CERTIFIED_BY_FIELD] = L2_MECHANISM_NAME
    if CERTIFIED_EQUAL not in mutated["selector_classes"]["values"]:
        mutated["selector_classes"]["values"] = list(mutated["selector_classes"]["values"]) + [CERTIFIED_EQUAL]
    monkeypatch.setattr(nv, "load_contract", lambda: copy.deepcopy(mutated))
    violations = selector_class_violations(nv.load_contract(), FeatureFactory.L2_ROUTE_CERTIFIED)
    assert any(v.startswith(f"{key}：標 certified_equal") for v in violations), violations


# ---------------------------------------------------------------------------------------------- mutation（Task 4.4）

def test_mutation_contract_new_value_affecting_key_not_read(monkeypatch: pytest.MonkeyPatch,
                                                            resolver_reads: Tuple[Set[str], Set[str]]) -> None:
    """mutation：契約新增一個 `value_affecting` 鍵而解析器未讀（解析器以原契約跑過）⇒ 連動閘紅。"""
    assert resolver_link_violations(*resolver_reads) == []
    mutated = copy.deepcopy(RAW_CONTRACT)
    template = dict(mutated["selectors"][_first_value_affecting_key(mutated)])
    mutated["selectors"][MUTANT_KEY] = template
    monkeypatch.setattr(nv, "load_contract", lambda: copy.deepcopy(mutated))
    assert f"解析器未讀 value_affecting 鍵：{MUTANT_KEY}" in resolver_link_violations(*resolver_reads)


def test_mutation_contract_marks_key_non_value_link_red(monkeypatch: pytest.MonkeyPatch,
                                                         resolver_reads: Tuple[Set[str], Set[str]]) -> None:
    """mutation：契約將任一鍵改標 `non_value` ⇒ 連動閘紅（類別違規，且解析器讀了非 value_affecting 之鍵）。"""
    assert resolver_link_violations(*resolver_reads) == []
    mutated = copy.deepcopy(RAW_CONTRACT)
    key = _first_value_affecting_key(mutated)
    mutated["selectors"][key]["class"] = NON_VALUE
    monkeypatch.setattr(nv, "load_contract", lambda: copy.deepcopy(mutated))
    violations = resolver_link_violations(*resolver_reads)
    assert f"{key}：標 non_value（本票不設排除）" in violations, violations
