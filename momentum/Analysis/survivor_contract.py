"""GAP-2b 倖存因子輸出契約——loader（Task 1.0）。

契約單一真相源＝``momentum/Analysis/contracts/ic_survivor_contract.json``；
本模組**不**複列任何鍵名／枚舉／reason 字面，只負責 fail-closed 載入與頂層鍵集檢查。
resolver／validator／``build_survivor_output`` 於 Task 3.1 加入本檔。

冷啟動注意：頂層鍵集於本檔以 frozenset 鎖死（與 TODO Task 1.0 步驟 1 一致）；
契約檔多鍵／少鍵一律 ``ContractValidationError``（不 fallback、不吞）。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from momentum.Analysis.ic_config_schema import ContractValidationError

__all__ = [
    "SURVIVOR_CONTRACT_PATH",
    "SURVIVOR_CONTRACT_TOP_KEYS",
    "load_survivor_contract",
]

SURVIVOR_CONTRACT_PATH = Path(__file__).parent / "contracts" / "ic_survivor_contract.json"

# 頂層鍵集（恰為此集合；TODO Task 1.0 步驟 1）。B4 若增鍵須同步本集合與測試 ①（可見）。
SURVIVOR_CONTRACT_TOP_KEYS = frozenset(
    {
        "version",
        "_doc",
        "capability_status_ref",
        "reasons",
        "algorithm_version",
        "survivor_file_keys",
        "sample_scope_keys",
        "sample_scope_kind_values",
        "event_definition_keys",
        "event_identity_keys",
        "split_keys",
        "row_identity_keys",
        "provenance_keys",
        "survivor_record_keys",
        "marginal_ic_section_keys",
        "statistic_values",
        "projection_space_values",
        "weights_method_values",
        "view_values",
        "fit_scope_values",
        "selection_sample_values",
        "oos_semantics_values",
        "independent_oos_validation_allowed",
        "survivor_output_status_keys",
    }
)

_contract_cache: Optional[Dict[str, Any]] = None


def load_survivor_contract(path: Optional[Path] = None) -> Dict[str, Any]:
    """載入倖存者契約 SoT（fail-closed）。

    - ``path`` 預設為 ``SURVIVOR_CONTRACT_PATH``；傳入其他路徑（測試 tamper 用）時不走 cache。
    - 檔缺／JSON 壞／非 mapping ⇒ ``ContractValidationError``。
    - 頂層鍵集必須 **恰等於** ``SURVIVOR_CONTRACT_TOP_KEYS``；多鍵或少鍵皆 raise。
    - ``independent_oos_validation_allowed`` 必須恰為 ``[False]``（version=1 之硬約束）。
    - 回傳 dict（不解析 ``capability_status_ref``；resolver 於 Task 3.1）。
    """
    global _contract_cache
    use_cache = path is None
    if use_cache and _contract_cache is not None:
        return _contract_cache

    contract_path = SURVIVOR_CONTRACT_PATH if path is None else Path(path)
    if not contract_path.is_file():
        raise ContractValidationError(f"survivor contract missing: {contract_path}")
    try:
        with contract_path.open("r", encoding="utf-8") as file:
            contract = json.load(file)
    except json.JSONDecodeError as exc:
        raise ContractValidationError(
            f"survivor contract is not valid JSON: {contract_path}: {exc}"
        ) from exc
    if not isinstance(contract, dict):
        raise ContractValidationError(
            f"survivor contract must be a mapping: {contract_path}"
        )

    keys = frozenset(contract.keys())
    if keys != SURVIVOR_CONTRACT_TOP_KEYS:
        missing = sorted(SURVIVOR_CONTRACT_TOP_KEYS - keys)
        extra = sorted(keys - SURVIVOR_CONTRACT_TOP_KEYS)
        raise ContractValidationError(
            "survivor contract top-level keys mismatch: "
            f"missing={missing} extra={extra} ({contract_path})"
        )
    if contract.get("independent_oos_validation_allowed") != [False]:
        raise ContractValidationError(
            "survivor contract independent_oos_validation_allowed must be [false] "
            f"(got {contract.get('independent_oos_validation_allowed')!r})"
        )

    if use_cache:
        _contract_cache = contract
    return contract
