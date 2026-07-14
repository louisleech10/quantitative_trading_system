"""IC1C-FR-STOPGAP: factor_returns 輸出邊界 sanitizer(momentum-side 純函式).

遞迴把任意 payload 中的 ``factor_returns`` 節換成 §U union 佔位,
summary 三欄(factor_return_ls_mean / factor_return_sharpe /
factor_return_max_drawdown)→ null。冪等;禁 import api。

狀態一致性(B1 退修):
- results 風格 factor_returns → §U unavailable 佔位
- module_summary.factor_returns 字串若為 legacy completed/非 not_run 終態
  → 轉 unavailable(not_run 保留)
- module_statuses 清單形態中 factor_returns 條目同規則
- completed_count / skipped_count / deep_analysis_summary.completed|skipped
  依 module_summary / module_statuses 重算(unavailable 不計 completed/skipped)
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

UNAVAILABLE_REASON = "ls_returns_timestamp_misaligned (1c-FR-FULL)"

FACTOR_RETURNS_PLACEHOLDER: dict[str, Any] = {
    "status": "unavailable",
    "value": None,
    "reason": UNAVAILABLE_REASON,
}

# reporter summary CSV / export 三欄
_SUMMARY_NULL_KEYS: frozenset[str] = frozenset(
    {
        "factor_return_ls_mean",
        "factor_return_sharpe",
        "factor_return_max_drawdown",
    }
)

_FACTOR_RETURNS_KEY = "factor_returns"

# module_summary 狀態字串:not_run 為 default-off 合法終態,不改;
# 其餘(含 legacy completed)在 results 已下架時改 unavailable
_PRESERVE_SUMMARY_STATUSES: frozenset[str] = frozenset({"not_run", "unavailable"})


def sanitize_factor_returns(payload: Any) -> Any:
    """遞迴 sanitize factor_returns 有限值洩漏;冪等 pure function。

    - dict 鍵 ``factor_returns`` results 節 → §U 佔位
    - module_summary.factor_returns 字串 → unavailable(除非 not_run)
    - module_statuses 清單 entry → 同上
    - dict 鍵屬 summary 三欄 → None
    - completed_count / skipped_count / deep_analysis_summary 計數重算
    - list/tuple 遞迴;其他葉值原樣
    """
    cleaned = _sanitize_node(payload)
    return _recompute_status_counts(cleaned)


def _is_results_style_factor_returns(value: Any) -> bool:
    """判斷 factor_returns 值是否為 results 節(需換佔位),而非 module_summary 字串狀態."""
    if isinstance(value, str):
        # module_summary.factor_returns = "not_run"|"unavailable"|...
        return False
    if value is None:
        return False
    # dict/list 等皆視為 results 節或 legacy 有限 payload
    return True


def _normalize_summary_status(status: Any) -> Any:
    """module_summary / module_statuses 的 factor_returns 狀態正規化."""
    if not isinstance(status, str):
        return status
    if status in _PRESERVE_SUMMARY_STATUSES:
        return status
    # legacy completed / failed / skipped 等 → unavailable(下架語意)
    return "unavailable"


def _sanitize_module_status_entry(entry: Any) -> Any:
    """module_statuses 清單元素:{module_name, status}."""
    if not isinstance(entry, dict):
        return _sanitize_node(entry)
    name = entry.get("module_name")
    out = {str(k): _sanitize_node(v) for k, v in entry.items()}
    if name == _FACTOR_RETURNS_KEY and "status" in out:
        out["status"] = _normalize_summary_status(out["status"])
    return out


def _sanitize_node(node: Any) -> Any:
    if isinstance(node, dict):
        out: dict[str, Any] = {}
        # module_summary 特殊處理:factor_returns 字串狀態正規化
        is_module_summary = (
            "factor_returns" in node
            and isinstance(node.get("factor_returns"), str)
            and all(
                isinstance(v, str) or v is None
                for v in node.values()
            )
            and not any(k in node for k in ("results", "module_summary", "deep_analysis_summary"))
            and not any(k in _SUMMARY_NULL_KEYS for k in node)
            and not any(
                isinstance(v, (dict, list)) for v in node.values()
            )
        )
        for key, value in node.items():
            key_str = str(key)
            if key_str == "module_statuses" and isinstance(value, list):
                out[key_str] = [_sanitize_module_status_entry(item) for item in value]
                continue
            if key_str == "module_summary" and isinstance(value, dict):
                ms: dict[str, Any] = {}
                for mk, mv in value.items():
                    mk_str = str(mk)
                    if mk_str == _FACTOR_RETURNS_KEY and isinstance(mv, str):
                        ms[mk_str] = _normalize_summary_status(mv)
                    elif mk_str == _FACTOR_RETURNS_KEY and _is_results_style_factor_returns(mv):
                        ms[mk_str] = "unavailable"
                    else:
                        ms[mk_str] = _sanitize_node(mv)
                out[key_str] = ms
                continue
            if key_str == _FACTOR_RETURNS_KEY:
                if _is_results_style_factor_returns(value):
                    out[key_str] = dict(FACTOR_RETURNS_PLACEHOLDER)
                elif isinstance(value, str):
                    # 裸 module_summary 風格或誤嵌字串:正規化狀態
                    if is_module_summary or key_str == _FACTOR_RETURNS_KEY:
                        out[key_str] = _normalize_summary_status(value)
                    else:
                        out[key_str] = value
                else:
                    out[key_str] = value
                continue
            if key_str in _SUMMARY_NULL_KEYS:
                out[key_str] = None
                continue
            out[key_str] = _sanitize_node(value)
        return out
    if isinstance(node, list):
        # 可能是 module_statuses 清單(在父層已處理);一般 list 遞迴
        return [_sanitize_node(item) for item in node]
    if isinstance(node, tuple):
        return tuple(_sanitize_node(item) for item in node)
    # 葉:原樣(含 None/str/bool/number);不 deepcopy 不可變葉
    if isinstance(node, (str, int, float, bool, type(None))):
        return node
    # 其餘(numpy scalar 等)淺拷即可;避免對未知物件 deepcopy 失敗
    try:
        return deepcopy(node)
    except Exception:  # noqa: BLE001
        return node


def _statuses_from_payload(node: Any) -> dict[str, str] | None:
    """自 payload 抽取 module 狀態 map(module_summary 或 module_statuses)."""
    if not isinstance(node, dict):
        return None
    summary = node.get("module_summary")
    if isinstance(summary, dict) and summary:
        out: dict[str, str] = {}
        for k, v in summary.items():
            if isinstance(v, str):
                out[str(k)] = v
        if out:
            return out
    statuses = node.get("module_statuses")
    if isinstance(statuses, list) and statuses:
        out2: dict[str, str] = {}
        for item in statuses:
            if not isinstance(item, dict):
                continue
            name = item.get("module_name")
            status = item.get("status")
            if isinstance(name, str) and isinstance(status, str):
                out2[name] = status
        if out2:
            return out2
    return None


def _count_status(statuses: dict[str, str], target: str) -> int:
    return sum(1 for s in statuses.values() if s == target)


def _recompute_status_counts(node: Any) -> Any:
    """重算 completed_count/skipped_count 與 deep_analysis_summary 對應欄.

    unavailable / not_run 均不計 completed/skipped(與 orchestrator 尾端計數一致).
    """
    if not isinstance(node, dict):
        if isinstance(node, list):
            return [_recompute_status_counts(x) for x in node]
        return node

    out: dict[str, Any] = {}
    for k, v in node.items():
        out[str(k)] = _recompute_status_counts(v)

    statuses = _statuses_from_payload(out)
    if statuses is not None:
        completed = _count_status(statuses, "completed")
        skipped = _count_status(statuses, "skipped")
        if "completed_count" in out:
            out["completed_count"] = completed
        if "skipped_count" in out:
            out["skipped_count"] = skipped
        das = out.get("deep_analysis_summary")
        if isinstance(das, dict):
            das2 = dict(das)
            if "completed" in das2:
                das2["completed"] = completed
            if "skipped" in das2:
                das2["skipped"] = skipped
            out["deep_analysis_summary"] = das2

    return out


def has_finite_numeric_leaf(obj: Any) -> bool:
    """偵測任意嵌套結構是否含有限 numeric leaf(測試/gate 共用)。"""
    if isinstance(obj, dict):
        return any(has_finite_numeric_leaf(v) for v in obj.values())
    if isinstance(obj, (list, tuple)):
        return any(has_finite_numeric_leaf(v) for v in obj)
    if isinstance(obj, bool):
        return False
    if isinstance(obj, (int, float)):
        import math

        return math.isfinite(float(obj))
    # numpy scalar
    try:
        import numpy as np

        if isinstance(obj, (np.integer, np.floating)):
            import math

            return math.isfinite(float(obj))
    except Exception:  # noqa: BLE001
        pass
    return False


def assert_no_finite_in_factor_returns_subtree(payload: Any) -> None:
    """遞迴掃描 payload 內所有 factor_returns 子樹,禁任何有限 numeric leaf.

    用於 AI/Markdown/export oracle;比字面禁字更強,防 size/samples 等 meta 假綠。
    """
    if isinstance(payload, dict):
        for key, value in payload.items():
            if str(key) == _FACTOR_RETURNS_KEY:
                if isinstance(value, str):
                    # status 字串無 numeric leaf
                    continue
                if has_finite_numeric_leaf(value):
                    raise AssertionError(
                        f"finite numeric leaf in factor_returns subtree: {value!r}"
                    )
            else:
                assert_no_finite_in_factor_returns_subtree(value)
    elif isinstance(payload, (list, tuple)):
        for item in payload:
            assert_no_finite_in_factor_returns_subtree(item)
