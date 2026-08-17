"""Task 2.1 — 策略驗證契約之唯一 resolver 與 validator。

SPEC ref：Task 2.1 ＋ A1-4／A1-7／A1-8／A1-13。
契約檔＝`momentum/Analysis/contracts/strategy_validation_contract.json`（16 頂層鍵）。
`capability_status` **不**在策略契約內複列，改以 `capability_status_ref` 於**執行期 dereference**
IC 契約；目標檔缺失／鍵缺失／型別不符一律 raise（fail-closed，禁回退預設枚舉）。
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional, Tuple

_CONTRACT_PATH = (
    Path(__file__).resolve().parents[1] / "contracts" / "strategy_validation_contract.json"
)
_REPO_ROOT = Path(__file__).resolve().parents[3]

# JSON 型別名 → Python 型別（契約用字串描述型別，避免在 JSON 內放 Python 物件）
_TYPE_MAP: Dict[str, tuple] = {
    "str": (str,),
    "int": (int,),
    "float": (float, int),  # JSON 之 1 與 1.0 皆視為 float 相容
    "bool": (bool,),
    "null": (type(None),),
}

# 契約頂層鍵集合（Task 2.1「恰 16」；A1-21 L8：loader 對集合相等 fail-closed，多／少皆 raise）。
# 只列**鍵名**，不複列任何枚舉值（`capability_status` 六值仍只在 IC 契約）。
_EXPECTED_TOP_LEVEL_KEYS: frozenset = frozenset(
    {
        "version",
        "capability_status_ref",
        "ledger_record_keys",
        "n_fields",
        "report_sections",
        "eligibility_keys",
        "annualization_source_values",
        "metric_unit_values",
        "n_semantics_values",
        "selection_metric_values",
        "t_semantics_values",
        "universe_scope_values",
        "universe_source_values",
        "variance_source_values",
        "reasons",
        "reason_conditions",
    }
)

# 快取（A1-21 L8）：以 `(mtime_ns, size)` 鍵控 ⇒ 檔變即失效；回傳 **deepcopy** ⇒ 外部改不到快取。
# 仍是模組級 memo（不宣稱「無快取」），但不可變、可失效——滿足 Rule 8 之精神。
_contract_cache: Optional[Tuple[Tuple[int, int], Dict[str, Any]]] = None


class ContractViolation(ValueError):
    """物件違反策略驗證契約（缺必填／型別不符／額外鍵／枚舉值非法）。"""


def _dereference_capability_status(ref: str) -> list:
    """解析 `<repo 相對路徑>#<頂層鍵名>`；任一步失敗即 raise（禁 fallback）。"""
    if not isinstance(ref, str) or "#" not in ref:
        raise ContractViolation(f"capability_status_ref 格式錯: {ref!r}")
    rel_path, _, key = ref.partition("#")
    target = _REPO_ROOT / rel_path
    if not target.is_file():
        raise ContractViolation(f"capability_status_ref 目標檔不存在: {target}")
    with target.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if key not in payload:
        raise ContractViolation(f"capability_status_ref 目標鍵缺失: {ref!r}")
    values = payload[key]
    if not isinstance(values, list) or not values or not all(isinstance(v, str) for v in values):
        raise ContractViolation(f"capability_status_ref 目標非非空 str list: {ref!r}")
    return list(values)


def load_strategy_validation_contract(path: Path | None = None) -> Dict[str, Any]:
    """載入策略驗證契約，並把 `capability_status_ref` 解析結果掛在 `capability_status` 鍵下。

    Args:
        path: 覆寫契約檔路徑（僅供測試 drift 偵測用；預設走 canonical 路徑）。

    Returns:
        契約 dict（含解析後之 `capability_status`）。

    Raises:
        ContractViolation: 檔缺／JSON 語法錯／ref 解析失敗／頂層鍵集合非預期。
    """
    global _contract_cache
    use_default = path is None
    target = path or _CONTRACT_PATH
    if not target.is_file():
        raise ContractViolation(f"策略驗證契約檔不存在: {target}")
    stat = target.stat()
    cache_key = (stat.st_mtime_ns, stat.st_size)
    if use_default and _contract_cache is not None and _contract_cache[0] == cache_key:
        return copy.deepcopy(_contract_cache[1])

    try:
        with target.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except json.JSONDecodeError as exc:
        raise ContractViolation(f"策略驗證契約 JSON 語法錯: {target}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ContractViolation(f"策略驗證契約須為物件: {target}")

    payload = dict(payload)
    _validate_contract_shape(payload, target)
    payload["capability_status"] = _dereference_capability_status(
        payload.get("capability_status_ref", "")
    )
    if use_default:
        _contract_cache = (cache_key, copy.deepcopy(payload))
    return payload


def _validate_contract_shape(payload: Mapping[str, Any], target: Path) -> None:
    """契約檔本身之結構檢查（A1-21 L8；load 時 fail-closed，禁 fail-open 漂移）：
    ① 頂層鍵集合恰為 `_EXPECTED_TOP_LEVEL_KEYS`（`_` 開頭之文件鍵除外）
    ② 每個 `*_values` 皆為非空 str list
    ③ `reasons` 為非空 str list 且 `set(reason_conditions) == set(reasons)`。
    """
    actual = {k for k in payload if not k.startswith("_")}
    if actual != _EXPECTED_TOP_LEVEL_KEYS:
        raise ContractViolation(
            f"策略驗證契約頂層鍵集合非預期: {target}: "
            f"missing={sorted(_EXPECTED_TOP_LEVEL_KEYS - actual)} extra={sorted(actual - _EXPECTED_TOP_LEVEL_KEYS)}"
        )
    for key in sorted(actual):
        if not key.endswith("_values"):
            continue
        values = payload[key]
        if not isinstance(values, list) or not values or not all(isinstance(v, str) for v in values):
            raise ContractViolation(f"契約枚舉 {key!r} 須為非空 str list: {target}")
    reasons = payload["reasons"]
    if not isinstance(reasons, list) or not reasons or not all(isinstance(r, str) for r in reasons):
        raise ContractViolation(f"契約 reasons 須為非空 str list: {target}")
    conditions = payload["reason_conditions"]
    if not isinstance(conditions, dict) or set(conditions) != set(reasons):
        raise ContractViolation(f"契約 reason_conditions 鍵集合須等於 reasons: {target}")


def contract_top_level_keys(contract: Mapping[str, Any] | None = None) -> set:
    """契約之頂層鍵集合（排除 `_doc` 與執行期掛上的 `capability_status`）。"""
    data = contract if contract is not None else load_strategy_validation_contract()
    return {k for k in data if not k.startswith("_") and k != "capability_status"}


def _type_ok(value: Any, allowed: Iterable[str]) -> bool:
    allowed = list(allowed)
    # bool 是 int 的子類：型別清單未含 bool 時不得讓 True 冒充 1
    if isinstance(value, bool) and "bool" not in allowed:
        return False
    for name in allowed:
        expected = _TYPE_MAP.get(name)
        if expected is None:
            raise ContractViolation(f"契約使用了未知型別名: {name!r}")
        if isinstance(value, expected):
            return True
    return False


def validate_against_contract(obj: Dict[str, Any], section: str) -> None:
    """依契約之 `report_sections[section]` 驗證：必填齊備／型別相符／無額外鍵。

    Args:
        obj: 待驗物件。
        section: `report_sections` 之節名（未知節名即 raise）。

    Raises:
        ContractViolation: 任一規則違反。
    """
    contract = load_strategy_validation_contract()
    sections = contract.get("report_sections", {})
    if section not in sections or section.startswith("_"):
        raise ContractViolation(f"未知 report section: {section!r}")
    if not isinstance(obj, dict):
        raise ContractViolation(f"section {section!r} 之待驗物件須為 dict，得到 {type(obj).__name__}")

    spec = sections[section]
    required = list(spec.get("required_keys", []))
    optional = list(spec.get("optional_keys", []))
    types: Mapping[str, Any] = spec.get("types", {})
    allow_extra = bool(spec.get("additional_properties", False))

    missing = [k for k in required if k not in obj]
    if missing:
        raise ContractViolation(f"section {section!r} 缺必填鍵: {sorted(missing)}")

    known = set(required) | set(optional)
    extra = [k for k in obj if k not in known]
    if extra and not allow_extra:
        raise ContractViolation(f"section {section!r} 含未列鍵: {sorted(extra)}")

    for key, value in obj.items():
        allowed = types.get(key)
        if allowed is None:
            continue
        if not _type_ok(value, allowed):
            raise ContractViolation(
                f"section {section!r} 之 {key!r} 型別不符: 期望 {allowed}，得到 {type(value).__name__}"
            )

    status_values = contract["capability_status"]
    if "status" in obj and obj["status"] not in status_values:
        raise ContractViolation(
            f"section {section!r} 之 status={obj['status']!r} 不在 capability_status 枚舉"
        )
    if "reason" in obj and obj["reason"]:
        if obj["reason"] not in contract["reasons"]:
            raise ContractViolation(
                f"section {section!r} 之 reason={obj['reason']!r} 不在契約 reasons（禁自創字面）"
            )
    # A1-21 L8：枚舉 membership 之**機械對映**——obj 之鍵 `k` 若契約存在 `f"{k}_values"`，
    # 非 None 之值須屬該枚舉（涵蓋 universe_scope／variance_source／n_semantics／t_semantics／
    # annualization_source／universe_source／selection_metric／metric_unit；新增枚舉自動納入，禁散落 hardcode）。
    for key, value in obj.items():
        enum_key = f"{key}_values"
        if value is None or enum_key not in contract:
            continue
        if value not in contract[enum_key]:
            raise ContractViolation(
                f"section {section!r} 之 {key}={value!r} 不在契約 {enum_key}（禁自創字面）"
            )
