"""IC1C-FR-FULL F2: factor_returns 輸出邊界 sanitizer(momentum-side 純函式).

§U discriminator:
- ok union(有 status==\"ok\" + value.schema_version)→放行(冪等)
- unavailable union → 放行/正規化(冪等)
- 無 status 裸 legacy map → 擋,reason=`legacy_misaligned_factor_return_shape`
- module_summary 與 results 狀態同步(ok→completed;unavailable→unavailable)
- summary 三欄(factor_return_ls_mean / factor_return_sharpe /
  factor_return_max_drawdown)→ null(由 reporter unwrap 重算)
- completed_count / skipped_count 依 module_summary 重算

禁 import api。
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

# §C L54⑬: legacy 擋用新 reason;ok 路徑禁 ls_returns_timestamp_misaligned
LEGACY_MISALIGNED_REASON = "legacy_misaligned_factor_return_shape"
# 舊 stopgap reason 保留別名,僅供文件/對照;新 placeholder 用 LEGACY_MISALIGNED_REASON
UNAVAILABLE_REASON = LEGACY_MISALIGNED_REASON

FR_SCHEMA_VERSION = "fr_full_v1"

FACTOR_RETURNS_PLACEHOLDER: dict[str, Any] = {
    "status": "unavailable",
    "value": None,
    "reason": LEGACY_MISALIGNED_REASON,
}

# reporter summary CSV / export 三欄(sanitize 時清掉,由 unwrap 重填)
_SUMMARY_NULL_KEYS: frozenset[str] = frozenset(
    {
        "factor_return_ls_mean",
        "factor_return_sharpe",
        "factor_return_max_drawdown",
    }
)

_FACTOR_RETURNS_KEY = "factor_returns"

# module_summary 狀態字串:not_run / unavailable / completed 在 discriminator 下可保留;
# 最終以 _sync_module_summary_with_results 對齊 results.factor_returns.status
_PRESERVE_SUMMARY_STATUSES: frozenset[str] = frozenset(
    {"not_run", "unavailable", "completed"}
)


def is_ok_factor_returns_union(value: Any) -> bool:
    """§U ok: status==ok 且 value.schema_version 存在."""
    if not isinstance(value, dict):
        return False
    if value.get("status") != "ok":
        return False
    inner = value.get("value")
    if not isinstance(inner, dict):
        return False
    return "schema_version" in inner


def is_unavailable_factor_returns_union(value: Any) -> bool:
    return isinstance(value, dict) and value.get("status") == "unavailable"


def unwrap_factor_returns_features(payload: Any) -> dict[str, Any] | None:
    """ok union → ``value.features``;否則 None(unavailable/legacy/缺欄)."""
    if not is_ok_factor_returns_union(payload):
        return None
    inner = payload.get("value")
    if not isinstance(inner, dict):
        return None
    features = inner.get("features")
    if not isinstance(features, dict):
        return None
    return features


def sanitize_factor_returns(payload: Any) -> Any:
    """遞迴 sanitize factor_returns;冪等 pure function。

    - ok §U union → 原樣放行
    - unavailable §U union → 正規化佔位(冪等)
    - 無 status 裸 map → legacy 佔位
    - module_summary 與 results 同步
    - summary 三欄 → None
    - completed_count / skipped_count 重算
    """
    cleaned = _sanitize_node(payload)
    cleaned = _sync_module_summary_with_results(cleaned)
    return _recompute_status_counts(cleaned)


def _is_results_style_factor_returns(value: Any) -> bool:
    """判斷 factor_returns 值是否為 results 節(非 module_summary 字串狀態)."""
    if isinstance(value, str):
        return False
    if value is None:
        return False
    return True


def _discriminate_factor_returns_value(value: Any) -> Any:
    """對 results 風格 factor_returns 套 discriminator;回傳替換後的值."""
    if not _is_results_style_factor_returns(value):
        return value
    # ok union → 放行(含有限葉)
    if is_ok_factor_returns_union(value):
        # 保證 reason is None(ok 路徑禁舊 misaligned reason)
        out = dict(value)
        out["status"] = "ok"
        if out.get("reason") is not None:
            out["reason"] = None
        return out
    # 已是 unavailable union → 冪等正規化
    if is_unavailable_factor_returns_union(value):
        reason = value.get("reason")
        if not isinstance(reason, str) or not reason:
            reason = LEGACY_MISALIGNED_REASON
        return {
            "status": "unavailable",
            "value": None,
            "reason": reason,
        }
    # status 存在但非 ok/unavailable(畸形)或無 status 裸 map → 擋
    return dict(FACTOR_RETURNS_PLACEHOLDER)


def _normalize_summary_status(status: Any) -> Any:
    """module_summary / module_statuses 的 factor_returns 狀態初步正規化.

    completed 暫保留,最終由 _sync_module_summary_with_results 對齊 results。
    """
    if not isinstance(status, str):
        return status
    if status in _PRESERVE_SUMMARY_STATUSES:
        return status
    # failed / skipped 等 → unavailable
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
        is_module_summary = (
            "factor_returns" in node
            and isinstance(node.get("factor_returns"), str)
            and all(isinstance(v, str) or v is None for v in node.values())
            and not any(
                k in node for k in ("results", "module_summary", "deep_analysis_summary")
            )
            and not any(k in _SUMMARY_NULL_KEYS for k in node)
            and not any(isinstance(v, (dict, list)) for v in node.values())
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
                    elif mk_str == _FACTOR_RETURNS_KEY and _is_results_style_factor_returns(
                        mv
                    ):
                        # 誤把 results 塞進 summary → 走 discriminator 後若 ok 則 completed
                        disc = _discriminate_factor_returns_value(mv)
                        if is_ok_factor_returns_union(disc):
                            ms[mk_str] = "completed"
                        else:
                            ms[mk_str] = "unavailable"
                    else:
                        ms[mk_str] = _sanitize_node(mv)
                out[key_str] = ms
                continue
            if key_str == _FACTOR_RETURNS_KEY:
                if _is_results_style_factor_returns(value):
                    out[key_str] = _discriminate_factor_returns_value(value)
                elif isinstance(value, str):
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
        return [_sanitize_node(item) for item in node]
    if isinstance(node, tuple):
        return tuple(_sanitize_node(item) for item in node)
    if isinstance(node, (str, int, float, bool, type(None))):
        return node
    try:
        return deepcopy(node)
    except Exception:  # noqa: BLE001
        return node


def _fr_status_to_module_status(fr_status: Any) -> str | None:
    """results/top-level factor_returns.status → module_summary/statuses 字串."""
    if fr_status == "ok":
        return "completed"
    if fr_status == "unavailable":
        return "unavailable"
    return None


def _locate_factor_returns_node(node: dict[str, Any]) -> dict[str, Any] | None:
    """自 envelope(results.*) 或 flat 頂層取出 factor_returns dict."""
    results = node.get("results")
    if isinstance(results, dict):
        fr = results.get(_FACTOR_RETURNS_KEY)
        if isinstance(fr, dict) and "status" in fr:
            return fr
    top = node.get(_FACTOR_RETURNS_KEY)
    if isinstance(top, dict) and "status" in top:
        return top
    return None


def _sync_module_summary_with_results(node: Any) -> Any:
    """對齊 module_summary / module_statuses 與 factor_returns.status.

    - ok → completed
    - unavailable → unavailable(禁 ghost completed)
    - 支援 envelope(``results.factor_returns``)與 flat(頂層 ``factor_returns``)
    - results 無 FR 節 → 保留既有 not_run / 缺省
    """
    if isinstance(node, list):
        return [_sync_module_summary_with_results(x) for x in node]
    if isinstance(node, tuple):
        return tuple(_sync_module_summary_with_results(x) for x in node)
    if not isinstance(node, dict):
        return node

    out: dict[str, Any] = {
        str(k): _sync_module_summary_with_results(v) for k, v in node.items()
    }

    fr = _locate_factor_returns_node(out)
    if fr is not None:
        mapped = _fr_status_to_module_status(fr.get("status"))
        if mapped is not None:
            ms = out.get("module_summary")
            if isinstance(ms, dict):
                ms2 = dict(ms)
                ms2[_FACTOR_RETURNS_KEY] = mapped
                out["module_summary"] = ms2

            # flat serialize 路徑用 module_statuses 清單,不得殘 completed
            statuses = out.get("module_statuses")
            if isinstance(statuses, list):
                synced: list[Any] = []
                for item in statuses:
                    if (
                        isinstance(item, dict)
                        and item.get("module_name") == _FACTOR_RETURNS_KEY
                    ):
                        item2 = dict(item)
                        item2["status"] = mapped
                        synced.append(item2)
                    else:
                        synced.append(item)
                out["module_statuses"] = synced

    # 頂層 deep report 亦可能 results 嵌在 deep_analysis_report
    deep = out.get("deep_analysis_report")
    if isinstance(deep, dict):
        out["deep_analysis_report"] = _sync_module_summary_with_results(deep)

    return out


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
    try:
        import numpy as np

        if isinstance(obj, (np.integer, np.floating)):
            import math

            return math.isfinite(float(obj))
    except Exception:  # noqa: BLE001
        pass
    return False


def assert_no_finite_in_factor_returns_subtree(payload: Any) -> None:
    """遞迴掃描 payload 內 factor_returns 子樹,禁有限 numeric leaf.

    F2 ⑮:ok §U union **豁免**(僅 legacy 裸 map / unavailable 畸形斷言)。
    """
    if isinstance(payload, dict):
        for key, value in payload.items():
            if str(key) == _FACTOR_RETURNS_KEY:
                if isinstance(value, str):
                    continue
                # ok union 放行有限葉
                if is_ok_factor_returns_union(value):
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
