"""GAP-3 UX Task 5.0 — 事件型表格指標詞彙 SoT 之 loader。

字面唯一住在 `momentum/Analysis/contracts/event_metrics_glossary.json`；本檔**只讀不寫**，
且不得在此複列任何 term／definition 字面（複列即第二份副本，正是本 Task「不可做」所禁）。

頂層鍵即指標鍵；以 `_` 起首者為後設欄（`_doc`／`_version`）。**這是唯一的排除規則**——
不寫成「排除 _doc 與 _version」那種逐一列舉的黑名單，因為黑名單永遠列不完
（後設欄一旦新增就會被誤當指標，而那正是 fail-closed 檢查會誤紅的形態）。

fail-closed（Task 5.0 邊界②）：任一指標鍵缺 `definition` ⇒ `raise`，不回半套字典。
理由＝前端 tooltip 之唯一來源就是這裡，靜默給空字串會讓「沒有定義」看起來像「沒有 tooltip」。
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Dict, Optional

_GLOSSARY_PATH = Path(__file__).resolve().parents[1] / "contracts" / "event_metrics_glossary.json"
_GLOSSARY_CACHE: Optional[dict] = None

#: 每個指標鍵**必備**之欄位（缺任一即 fail-closed）。
REQUIRED_TERM_FIELDS = ("term", "definition", "formula_ref")


def _is_metadata_key(key: str) -> bool:
    """後設欄之唯一判準：鍵以 `_` 起首。"""
    return str(key).startswith("_")


def load_metrics_glossary() -> Dict[str, Dict[str, str]]:
    """讀指標詞彙 SoT（只回指標鍵；後設欄不回）。

    每次回傳**深拷貝**（沿 `load_condition_engine_contract` 之慣例：caller 改寫不得污染 SoT）。

    Raises:
        ValueError: 任一指標鍵之值不是物件，或缺 `term`／`definition`／`formula_ref`，
            或該欄不是非空字串。
    """
    global _GLOSSARY_CACHE
    if _GLOSSARY_CACHE is None:
        with _GLOSSARY_PATH.open("r", encoding="utf-8") as f:
            raw = json.load(f)
        terms = {k: v for k, v in raw.items() if not _is_metadata_key(k)}
        if not terms:
            raise ValueError("event_metrics_glossary.json 沒有任何指標鍵（只有後設欄）")
        for key, entry in sorted(terms.items()):
            if not isinstance(entry, dict):
                raise ValueError(f"event_metrics_glossary.json：指標鍵 {key} 之值須為物件，實得 {type(entry).__name__}")
            for field in REQUIRED_TERM_FIELDS:
                value = entry.get(field)
                if not isinstance(value, str) or not value.strip():
                    raise ValueError(f"event_metrics_glossary.json：指標鍵 {key} 缺 {field}（或為空字串）——fail-closed，不回半套詞彙表")
        _GLOSSARY_CACHE = terms
    return copy.deepcopy(_GLOSSARY_CACHE)
