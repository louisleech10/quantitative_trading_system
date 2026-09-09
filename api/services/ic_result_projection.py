# ICRESULT_PAGING 投影純函式（docs/ICRESULT_PAGING_SPEC.md §C-6～8）
"""IC 結果投影：分頁／單特徵／light 視圖＋排序索引快取。

- 全部只讀 contract（`momentum/Analysis/contracts/ic_result_paging_contract.json`），不讀檔、不重算、不改 source。
- 參考實作＝`handoffs/20260909-probe-icresult-golden.py`（golden 由其產生；本模組須逐值相等，測試鎖）。
- 不變式：任何函式**不得**就地改寫傳入的 report（snapshot 不可變，SPEC §C-7）。
"""
from __future__ import annotations

import math
import threading
from collections import OrderedDict
from typing import Any, Dict, List, Mapping, Optional, Tuple

import numpy as np


class SortByNotAllowed(ValueError):
    """`sort_by`／`sort_order` 不在 contract 白名單（route ⇒ 400）。"""


# ── 排序契約（§C-8）────────────────────────────────────────────────────────────
def _missing(v: Any) -> bool:
    if v is None or isinstance(v, bool):
        return True
    if isinstance(v, (int, float)):
        return not math.isfinite(float(v))
    return True


def sort_key(row: Mapping[str, Any], field: str, sort_order: str, contract: Mapping[str, Any]) -> Tuple:
    """缺值兩向沉底；主鍵依 sort_order；並列以 feature_name 升冪；字串欄純字串序。"""
    name = str(row.get("feature_name", ""))
    if field in contract["sort_policy"]["string_fields"]:
        return (0, name, name)  # 字串欄由 build_sort_index 以 reverse 處理 desc；此鍵只供 asc／tie-break
    v = row.get(field)
    if _missing(v):
        return (1, 0.0, name)  # 兩向沉底
    f = float(v)
    return (0, f if sort_order == "asc" else -f, name)


def _validate_sort(sort_by: str, sort_order: str, contract: Mapping[str, Any]) -> None:
    if sort_by not in contract["sort_fields"]:
        raise SortByNotAllowed(f"sort_by not allowed: {sort_by}")
    if sort_order not in contract["sort_order_values"]:
        raise SortByNotAllowed(f"sort_order not allowed: {sort_order}")


# ── 排序索引快取（§C-9：int32、每 task ≤ 8、process-wide ≤ 32 task）──────────────
class _SortIndexCache:
    def __init__(self, max_keys_per_task: int, max_tasks: int) -> None:
        self._lock = threading.Lock()
        self._tasks: "OrderedDict[str, OrderedDict[tuple, np.ndarray]]" = OrderedDict()
        self._max_keys = max_keys_per_task
        self._max_tasks = max_tasks

    def get_or_build(self, key: tuple, builder) -> np.ndarray:
        task_id = key[0]
        with self._lock:
            per = self._tasks.get(task_id)
            if per is not None and key in per:
                per.move_to_end(key)
                self._tasks.move_to_end(task_id)
                return per[key]
        idx = builder()
        with self._lock:
            per = self._tasks.get(task_id)
            if per is None:
                per = OrderedDict()
                self._tasks[task_id] = per
                while len(self._tasks) > self._max_tasks:
                    self._tasks.popitem(last=False)
                if task_id not in self._tasks:  # 自己被淘汰（不可能，但 fail-safe）
                    self._tasks[task_id] = per
            per[key] = idx
            per.move_to_end(key)
            self._tasks.move_to_end(task_id)
            while len(per) > self._max_keys:
                per.popitem(last=False)
        return idx

    def invalidate_task(self, task_id: str) -> None:
        with self._lock:
            self._tasks.pop(task_id, None)

    def cache_bytes(self) -> int:
        with self._lock:
            return int(sum(arr.nbytes for per in self._tasks.values() for arr in per.values()))

    def task_ids(self) -> List[str]:
        with self._lock:
            return list(self._tasks.keys())

    def keys_for(self, task_id: str) -> List[tuple]:
        with self._lock:
            return list(self._tasks.get(task_id, {}).keys())


_CACHE: Optional[_SortIndexCache] = None
_CACHE_GUARD = threading.Lock()


def sort_index_cache(contract: Mapping[str, Any]) -> _SortIndexCache:
    """module-level 單例（process-wide）。"""
    global _CACHE
    with _CACHE_GUARD:
        if _CACHE is None:
            cfg = contract["sort_index_cache"]
            _CACHE = _SortIndexCache(int(cfg["max_keys_per_task"]), int(cfg["max_tasks_process_wide"]))
        return _CACHE


def _key_part(v: Optional[str]) -> str:
    return "\x00None" if v is None else v


def _filtered_positions(rows: List[Mapping[str, Any]], pass_class: Optional[str], search: Optional[str]) -> List[int]:
    needle = search.lower() if search else None
    out: List[int] = []
    for i, r in enumerate(rows):
        if pass_class is not None and r.get("pass_class") != pass_class:
            continue
        if needle is not None and needle not in str(r.get("feature_name", "")).lower():
            continue
        out.append(i)
    return out


def build_sort_index(rows: List[Mapping[str, Any]], *, sort_by: str, sort_order: str, pass_class: Optional[str], search: Optional[str], contract: Mapping[str, Any]) -> np.ndarray:
    positions = _filtered_positions(rows, pass_class, search)
    if sort_by in contract["sort_policy"]["string_fields"]:
        # §C-8「純字串比較」＝ Python 字串序；desc 即 reverse（B1 review GROK-R1-P2-01：字元碼取負會讓前綴名錯序）
        order = sorted(positions, key=lambda i: str(rows[i].get("feature_name", "")), reverse=(sort_order == "desc"))
    else:
        order = sorted(positions, key=lambda i: sort_key(rows[i], sort_by, sort_order, contract))
    idx = np.asarray(order, dtype=np.int32)
    return idx


def paginate_summary(rows: List[Mapping[str, Any]], *, sort_by: str, sort_order: str, offset: int, limit: int, pass_class: Optional[str] = None, search: Optional[str] = None, contract: Mapping[str, Any], task_id: Optional[str] = None, revision: Optional[int] = None) -> Dict[str, Any]:
    """分頁投影（純：不改 rows）；`task_id`＋`revision` 皆給時走排序索引快取。"""
    _validate_sort(sort_by, sort_order, contract)
    limit = max(1, min(int(limit), int(contract["limit_max"])))
    offset = max(0, int(offset))

    def _build() -> np.ndarray:
        return build_sort_index(rows, sort_by=sort_by, sort_order=sort_order, pass_class=pass_class, search=search, contract=contract)

    if task_id is not None and revision is not None:
        # None（不篩）與 ""（精確空字串）語意不同，不得合併成同一 key（B1 review CODEX-R1-P1-01）
        key = (task_id, revision, sort_by, sort_order, _key_part(pass_class), _key_part(search))
        ordered = sort_index_cache(contract).get_or_build(key, _build)
    else:
        ordered = _build()
    page = ordered[offset: offset + limit]
    return {
        "total": int(len(ordered)),
        "offset": offset,
        "limit": limit,
        "sort_by": sort_by,
        "sort_order": sort_order,
        "rows": [rows[int(i)] for i in page],
    }


# ── light 投影規則（§C-6）──────────────────────────────────────────────────────
def collections_to_counts(node: Any) -> Any:
    """目標 dict 節點之**私有副本**：直接子鍵 list／dict → `<key>_count`；標量原樣；非 dict ⇒ 原樣。"""
    if not isinstance(node, dict):
        return node
    out: Dict[str, Any] = {}
    for k, v in node.items():
        if isinstance(v, (list, dict)):
            out[f"{k}_count"] = len(v)
        else:
            out[k] = v
    return out


def apply_count_paths(report: Mapping[str, Any], contract: Mapping[str, Any]) -> Dict[str, Any]:
    """依 contract.collection_to_count_paths 回傳新頂層 dict；只替換受影響節點；source 不動。"""
    out: Dict[str, Any] = dict(report)
    for spec in contract["collection_to_count_paths"]:
        path = spec["path"]
        if len(path) == 2 and path[1] == "*":
            parent = out.get(path[0])
            if isinstance(parent, dict):
                out[path[0]] = {k: collections_to_counts(v) for k, v in parent.items()}
        elif len(path) == 2:
            parent = out.get(path[0])
            if isinstance(parent, dict) and isinstance(parent.get(path[1]), dict):
                new_parent = dict(parent)
                new_parent[path[1]] = collections_to_counts(parent[path[1]])
                out[path[0]] = new_parent
    return out


def _funnel_value(stage: Mapping[str, Any], keys: List[str], count_key: str) -> Optional[int]:
    for k in keys:
        if k in stage:
            v = stage[k]
            if isinstance(v, bool):
                return None
            if isinstance(v, int):
                return v
            if isinstance(v, dict):
                if count_key in v and isinstance(v[count_key], int):
                    return int(v[count_key])
                return len(v)
            if isinstance(v, list):
                return len(v)
            return None
    return None


def funnel_from_filter_log(filter_log: Any, adapter: Mapping[str, Any]) -> Dict[str, Dict[str, Optional[int]]]:
    """漏斗 adapter（§C-6 (iv)）——**必須吃計數前的原始 filter_log**。"""
    if not isinstance(filter_log, dict):
        return {}
    out: Dict[str, Dict[str, Optional[int]]] = {}
    for stage, node in filter_log.items():
        if not isinstance(node, dict):
            out[stage] = {"input": None, "output": None}
            continue
        out[stage] = {
            "input": _funnel_value(node, adapter["input_keys"], adapter["dict_count_key"]),
            "output": _funnel_value(node, adapter["output_keys"], adapter["dict_count_key"]),
        }
    return out


def project_light_view(report: Mapping[str, Any], contract: Mapping[str, Any], *, task_id: Optional[str] = None, revision: Optional[int] = None) -> Dict[str, Any]:
    """light 視圖：刪七段、metadata 白名單、集合→計數（私有副本）、funnel（先於計數）、summary_page 首頁、附加鍵。"""
    funnel = funnel_from_filter_log(report.get("filter_log"), contract["funnel_stage_adapter"])
    drop = set()
    for sec in contract["drop_sections"]:
        drop.add(sec)
    out = {k: v for k, v in report.items() if k not in drop}
    meta = report.get("metadata")
    if isinstance(meta, dict):
        keep = contract["metadata_keep_keys"]
        out["metadata"] = {k: meta[k] for k in keep if k in meta}
    out = apply_count_paths(out, contract)
    rows = report.get("summary_table") or []
    out["summary_page"] = paginate_summary(
        list(rows), sort_by="icir", sort_order="desc", offset=0, limit=int(contract["limit_default"]),
        contract=contract, task_id=task_id, revision=revision,
    )
    out["filter_log_funnel"] = funnel
    out["view"] = "light"
    out["total_features"] = int(len(rows))
    out["result_revision"] = revision
    return out


def project_feature(report: Mapping[str, Any], name: str, contract: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
    """單特徵投影：contract.per_feature_sections 各段（grouped_ic → {group: value}）＋summary_row；不存在 ⇒ None。"""
    rows = report.get("summary_table") or []
    summary_row = next((r for r in rows if r.get("feature_name") == name), None)
    if summary_row is None:
        return None
    out: Dict[str, Any] = {"feature_name": name, "summary_row": summary_row}
    for sec in contract["per_feature_sections"]:
        node = report.get(sec)
        if not isinstance(node, dict):
            out[sec] = node if _is_section_status(node) else None
            continue
        if _is_section_status(node):
            out[sec] = node
        elif sec == "grouped_ic":
            out[sec] = {g: (v.get(name) if isinstance(v, dict) else None) for g, v in node.items()}
        else:
            out[sec] = node.get(name)
    return out


def _is_section_status(node: Any) -> bool:
    return isinstance(node, dict) and isinstance(node.get("status"), str)  # 與前端 isSectionStatus 同判準
