"""LA-1 attribution allowlist validator（SPEC §G / TODO Task 0.2）。

diff vs allowlist：unlisted = FAIL。
row 格式 = exact JSON path + index + old/new discriminator。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Optional, Sequence

CLASS_ENUM = frozenset({"P1-1", "P1-1b", "P1-1c", "P1-2", "P1-3-obs"})
# 五路徑 baseline（gen_baseline PATH_KEYS）歸因 class；P1-3-obs 為 report-root 非 five-path
FIVE_PATH_CLASSES = frozenset({"P1-1", "P1-1b", "P1-1c", "P1-2"})
# schema 硬需求：五鍵齊全（path/index/old/new/class）；old/new 可 null 但鍵須存在
REQUIRED_ROW_KEYS = frozenset({"path", "index", "old", "new", "class"})
REQUIRED_FORMAT_KEYS = REQUIRED_ROW_KEYS
# Task 1.5：diff 數 0 時 machine-readable 說明（optional top-level）
ZERO_DIFF_JUSTIFICATIONS_KEY = "zero_diff_justifications"


@dataclass
class ValidationResult:
    """驗證結果。"""

    ok: bool
    unexpected: list[dict[str, Any]] = field(default_factory=list)
    format_errors: list[str] = field(default_factory=list)
    messages: list[str] = field(default_factory=list)

    @property
    def unexpected_count(self) -> int:
        return len(self.unexpected)

    def machine_line(self) -> str:
        """B4 掃描用 machine line。

        成功路徑：``UNEXPECTED=0``（僅 overall ok 時可當綠燈）。
        freeze/format FAIL 時**禁止**只印 ``UNEXPECTED=0`` 冒充通過：
        先以 ``FAIL format_errors=N`` 短路標示 overall failure。
        """
        if self.format_errors:
            return (
                f"FAIL format_errors={len(self.format_errors)} "
                f"UNEXPECTED={self.unexpected_count}"
            )
        return f"UNEXPECTED={self.unexpected_count}"


class AttributionValidationError(ValueError):
    """allowlist / diff 驗證失敗。"""


def load_allowlist(path: Path | str) -> dict[str, Any]:
    """載入 attribution_allowlist.json。"""
    p = Path(path)
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise AttributionValidationError("allowlist root must be object")
    return data


def baseline_has_path(baseline: Any, path: str) -> bool:
    """dotted JSON path 是否存在於 baseline 物件（逐段 dict key）。"""
    if not isinstance(path, str) or not path:
        return False
    cur: Any = baseline
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return False
        cur = cur[part]
    return True


def _resolve_dotted_path(root: Any, path: str) -> tuple[bool, Any]:
    """解析 dotted path；回傳 (found, value)。"""
    if not isinstance(path, str) or not path:
        return False, None
    cur: Any = root
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return False, None
        cur = cur[part]
    return True, cur


def parent_path_of(path: str) -> Optional[str]:
    """dotted path 的 parent（最後一段之前）；無 parent → None。"""
    if not isinstance(path, str) or "." not in path:
        return None
    return path.rsplit(".", 1)[0]


def baseline_parent_has_skipped(
    baseline: Any,
    path: str,
) -> bool:
    """path 的 parent dict 是否在 baseline 標記 skipped=true（skipped→result 轉型錨）。

    僅認可嚴格 True（JSON true / Python True）；缺鍵、false、非 bool → False。
    """
    parent = parent_path_of(path)
    if parent is None:
        return False
    found, node = _resolve_dotted_path(baseline, parent)
    if not found or not isinstance(node, dict):
        return False
    return node.get("skipped") is True


def symbol_tf_from_index(index: Any) -> Optional[str]:
    """row index 前綴 ``{SYMBOL}/{tf}``（可後接 ``/feature``）。

    例：``ETHUSDT/12h/close_…`` → ``ETHUSDT/12h``；``BTCUSDT/1h`` → ``BTCUSDT/1h``。
    缺兩段式 symbol/tf → None（fail-closed 供 added_key）。
    """
    if not isinstance(index, str):
        return None
    parts = [p for p in index.split("/") if p]
    if len(parts) < 2:
        return None
    return f"{parts[0]}/{parts[1]}"


def artifact_symbol_tf(artifact: Any) -> Optional[str]:
    """baseline/live artifact 的 ``symbol``+``timeframe`` → ``SYMBOL/tf``。"""
    if not isinstance(artifact, dict):
        return None
    symbol = artifact.get("symbol")
    timeframe = artifact.get("timeframe")
    if not isinstance(symbol, str) or not isinstance(timeframe, str):
        return None
    if not symbol or not timeframe:
        return None
    return f"{symbol}/{timeframe}"


def _filter_artifacts_by_symbol_tf(
    artifacts: Sequence[dict[str, Any]],
    symbol_tf: str,
) -> list[dict[str, Any]]:
    """只保留 symbol/tf 與 row index 所指相同的 artifact。"""
    return [a for a in artifacts if artifact_symbol_tf(a) == symbol_tf]


def _as_dict_list(
    obj: dict[str, Any] | Sequence[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    if obj is None:
        return []
    if isinstance(obj, dict):
        return [obj]
    if isinstance(obj, Sequence) and not isinstance(obj, (str, bytes)):
        return [b for b in obj if isinstance(b, dict)]
    return []


def validate_allowlist_paths_against_baseline(
    allowlist: dict[str, Any],
    baseline: dict[str, Any] | Sequence[dict[str, Any]],
    *,
    classes: frozenset[str] | None = None,
    live: dict[str, Any] | Sequence[dict[str, Any]] | None = None,
) -> list[str]:
    """每筆 five-path class row 的 path 閘門。

    預設：path 必須存在於 baseline JSON（可為單一或 list 聯集）。
    例外（``added_key: true``，僅限 skipped→result 轉型）：
      雙錨（缺一即 FAIL，防 phantom；**必須綁 row index 同一 symbol/TF**）：
        ① 在 index 所指 symbol/TF 的 baseline 上，parent 有 ``skipped is True``
        ② 在**同一** symbol/TF 的 live 上，path 存在（``live`` 必供；未供 → FAIL）
      cross-artifact / wrong-symbol index（例如 path 錨在 ETH、index 寫 BTC）→ FAIL。
    未標 added_key 且 path 不在 baseline → schema FAIL。
    P1-3-obs 為 report-root 欄位，不在 gen_baseline 五路徑內，預設略過。
    """
    target = classes if classes is not None else FIVE_PATH_CLASSES
    baselines = _as_dict_list(baseline)
    lives = _as_dict_list(live)
    if not baselines:
        return ["baseline path check: no valid baseline object(s)"]
    errors: list[str] = []
    rows = allowlist.get("rows")
    if not isinstance(rows, list):
        return errors
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        cls = row.get("class")
        if cls not in target:
            continue
        path = row.get("path")
        if not isinstance(path, str):
            errors.append(f"allowlist.rows[{i}]: path must be str for baseline check")
            continue
        added_key = row.get("added_key", False)
        if added_key is True:
            row_st = symbol_tf_from_index(row.get("index"))
            if row_st is None:
                errors.append(
                    f"allowlist.rows[{i}]: added_key requires index with "
                    f"SYMBOL/tf prefix (got {row.get('index')!r}; class={cls!r})"
                )
                continue
            same_baselines = _filter_artifacts_by_symbol_tf(baselines, row_st)
            same_lives = _filter_artifacts_by_symbol_tf(lives, row_st)
            # 雙錨 ① same-symbol baseline parent skipped
            if not same_baselines:
                errors.append(
                    f"allowlist.rows[{i}]: added_key path {path!r} index {row_st!r} "
                    f"has no matching baseline symbol/tf artifact (class={cls!r})"
                )
            elif not any(
                baseline_parent_has_skipped(b, path) for b in same_baselines
            ):
                errors.append(
                    f"allowlist.rows[{i}]: added_key path {path!r} missing baseline "
                    f"parent skipped=true anchor on symbol/tf {row_st!r} "
                    f"(class={cls!r})"
                )
            # 雙錨 ② same-symbol live path
            if not lives:
                errors.append(
                    f"allowlist.rows[{i}]: added_key path {path!r} requires live "
                    f"artifact for dual-anchor check (class={cls!r})"
                )
            elif not same_lives:
                errors.append(
                    f"allowlist.rows[{i}]: added_key path {path!r} index {row_st!r} "
                    f"has no matching live symbol/tf artifact (class={cls!r})"
                )
            elif not any(baseline_has_path(lv, path) for lv in same_lives):
                errors.append(
                    f"allowlist.rows[{i}]: added_key path {path!r} not present in "
                    f"live JSON for symbol/tf {row_st!r} (class={cls!r})"
                )
            continue
        if added_key not in (False, None):
            errors.append(
                f"allowlist.rows[{i}]: added_key must be true|false|absent, "
                f"got {added_key!r}"
            )
            continue
        if not any(baseline_has_path(b, path) for b in baselines):
            errors.append(
                f"allowlist.rows[{i}]: path {path!r} not present in baseline JSON "
                f"(class={cls!r})"
            )
    return errors


def validate_zero_diff_justifications(allowlist: dict[str, Any]) -> list[str]:
    """檢查 optional `zero_diff_justifications`（TODO Task 1.5 diff 0 說明）。

    形狀：
      - 缺鍵：合法（B0 / 尚未宣告零 diff class）
      - 值必須為 object
      - key ∈ CLASS_ENUM
      - value = non-empty str **或** object 含 non-empty str `reason`
        （可附 `evidence` 等自由欄位）
    """
    errors: list[str] = []
    if ZERO_DIFF_JUSTIFICATIONS_KEY not in allowlist:
        return errors
    body = allowlist[ZERO_DIFF_JUSTIFICATIONS_KEY]
    if not isinstance(body, dict):
        return [
            f"{ZERO_DIFF_JUSTIFICATIONS_KEY} must be object, got {type(body).__name__}"
        ]
    for key, val in body.items():
        if key not in CLASS_ENUM:
            errors.append(
                f"{ZERO_DIFF_JUSTIFICATIONS_KEY}.{key!r}: class not in class_enum"
            )
            continue
        if isinstance(val, str):
            if not val.strip():
                errors.append(
                    f"{ZERO_DIFF_JUSTIFICATIONS_KEY}.{key}: reason string must be non-empty"
                )
        elif isinstance(val, dict):
            reason = val.get("reason")
            if not isinstance(reason, str) or not reason.strip():
                errors.append(
                    f"{ZERO_DIFF_JUSTIFICATIONS_KEY}.{key}: object must contain "
                    f"non-empty str 'reason'"
                )
        else:
            errors.append(
                f"{ZERO_DIFF_JUSTIFICATIONS_KEY}.{key}: must be str or object "
                f"with reason, got {type(val).__name__}"
            )
    return errors


def validate_allowlist_schema(
    allowlist: dict[str, Any],
    *,
    baseline: dict[str, Any] | Sequence[dict[str, Any]] | None = None,
    live: dict[str, Any] | Sequence[dict[str, Any]] | None = None,
) -> list[str]:
    """檢查 allowlist schema（B0：rows 可空）。

    baseline 若提供：five-path class 的每 row path 必須存在於 baseline
    （可為單一物件或 list/tuple 聯集，如 BTC∪ETH）。
    單 baseline 語意保留：任一 path 在該物件查不到 → FAIL。
    ``added_key: true`` 列（skipped→result）改走雙錨：baseline parent
    skipped=true + path 在 live，且兩錨必須落在 row index 所指**同一
    symbol/TF** artifact（見 ``validate_allowlist_paths_against_baseline``）。
    若含 `zero_diff_justifications`：鍵/值形狀須合法（Task 1.5）。
    """
    errors: list[str] = []
    if "schema_version" not in allowlist:
        errors.append("missing schema_version")
    class_enum = allowlist.get("class_enum")
    if not isinstance(class_enum, list) or not class_enum:
        errors.append("class_enum must be non-empty list")
    else:
        for c in class_enum:
            if c not in CLASS_ENUM:
                errors.append(f"unknown class_enum entry: {c!r}")
        missing = CLASS_ENUM - set(class_enum)
        if missing:
            errors.append(f"class_enum missing required: {sorted(missing)}")
    rows = allowlist.get("rows")
    if rows is None:
        errors.append("missing rows")
    elif not isinstance(rows, list):
        errors.append("rows must be list")
    else:
        for i, row in enumerate(rows):
            errors.extend(_format_errors_for_row(row, loc=f"allowlist.rows[{i}]"))
    errors.extend(validate_zero_diff_justifications(allowlist))
    if baseline is not None:
        errors.extend(
            validate_allowlist_paths_against_baseline(
                allowlist, baseline, live=live
            )
        )
    return errors


def _format_errors_for_row(row: Any, loc: str) -> list[str]:
    errors: list[str] = []
    if not isinstance(row, dict):
        return [f"{loc}: row must be object"]
    for key in REQUIRED_FORMAT_KEYS:
        if key not in row:
            errors.append(f"{loc}: missing required key {key!r}")
    if "path" in row and not isinstance(row["path"], str):
        errors.append(f"{loc}: path must be str")
    # index: int | str | list（exact locator）；禁缺鍵、禁 null、禁 wildcard
    if "index" in row and row["index"] is None:
        errors.append(f"{loc}: index must not be null")
    # B3-ATTR-02：element-exact 契約 — 拒 index 字面 "*" / 萬用字元
    if "index" in row and row["index"] == "*":
        errors.append(f"{loc}: index wildcard '*' forbidden (element-exact required)")
    if "index" in row and isinstance(row["index"], str) and "*" in row["index"]:
        errors.append(
            f"{loc}: index must not contain wildcard '*': {row['index']!r}"
        )
    # class 必存在且 ∈ enum（鍵缺由 REQUIRED_FORMAT_KEYS 報）
    if "class" in row and row["class"] not in CLASS_ENUM:
        errors.append(f"{loc}: class not in class_enum: {row.get('class')!r}")
    return errors


def _normalize_scalar(value: Any) -> Any:
    """old/new/index 等 discriminator 正規化，供 exact match key 使用。"""
    if isinstance(value, list):
        return tuple(_normalize_scalar(v) for v in value)
    if isinstance(value, dict):
        return tuple(
            sorted((str(k), _normalize_scalar(v)) for k, v in value.items())
        )
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return int(value)
    if isinstance(value, float):
        # 整數值 float 與 int 對齊（JSON 1 vs 1.0）
        if value.is_integer():
            return int(value)
        return float(value)
    return value


def _row_key(row: dict[str, Any]) -> tuple[Any, ...]:
    """diff / allowlist 對帳鍵：path + index + old + new + class（全五鍵）。"""
    path = row.get("path")
    index_key = _normalize_scalar(row.get("index"))
    old_key = _normalize_scalar(row.get("old"))
    new_key = _normalize_scalar(row.get("new"))
    class_key = row.get("class")
    return (path, index_key, old_key, new_key, class_key)


def _normalize_diff_row(row: Any, loc: str) -> tuple[Optional[dict[str, Any]], list[str]]:
    errs = _format_errors_for_row(row, loc=loc)
    if errs:
        return None, errs
    assert isinstance(row, dict)
    # 五鍵必存在（schema）；old/new 可為 null
    normalized = {
        "path": row["path"],
        "index": row["index"],
        "old": row["old"],
        "new": row["new"],
        "class": row["class"],
    }
    return normalized, []


def validate_diffs(
    diffs: Sequence[dict[str, Any]],
    allowlist: dict[str, Any],
    *,
    require_class_on_diff: bool = True,
) -> ValidationResult:
    """比對 diff 列表與 allowlist rows；unlisted → unexpected FAIL。

    Parameters
    ----------
    diffs:
        每筆需含 path + index + old + new + class（五鍵 exact match）。
    allowlist:
        已 load 的 allowlist 文件。
    require_class_on_diff:
        預設 True；class 已屬 REQUIRED_FORMAT_KEYS，此旗標保留相容。
    """
    schema_errs = validate_allowlist_schema(allowlist)
    if schema_errs:
        return ValidationResult(
            ok=False,
            format_errors=schema_errs,
            messages=list(schema_errs),
        )

    format_errors: list[str] = []
    allowed_keys: set[tuple[Any, ...]] = set()
    for i, row in enumerate(allowlist.get("rows") or []):
        if not isinstance(row, dict):
            format_errors.append(f"allowlist.rows[{i}]: not object")
            continue
        row_errs = _format_errors_for_row(row, loc=f"allowlist.rows[{i}]")
        if row_errs:
            format_errors.extend(row_errs)
            continue
        allowed_keys.add(_row_key(row))

    unexpected: list[dict[str, Any]] = []
    normalized_diffs: list[dict[str, Any]] = []
    for i, raw in enumerate(diffs):
        norm, errs = _normalize_diff_row(raw, loc=f"diff[{i}]")
        if errs:
            format_errors.extend(errs)
            continue
        assert norm is not None
        if require_class_on_diff and norm.get("class") not in CLASS_ENUM:
            format_errors.append(
                f"diff[{i}]: class missing or invalid: {norm.get('class')!r}"
            )
            continue
        normalized_diffs.append(norm)
        key = _row_key(norm)
        if key not in allowed_keys:
            unexpected.append(norm)

    messages: list[str] = []
    if format_errors:
        messages.extend(format_errors)
    if unexpected:
        messages.append(
            f"unlisted diff count={len(unexpected)} "
            f"(policy unlisted_diff=unexpected)"
        )

    ok = not format_errors and not unexpected
    result = ValidationResult(
        ok=ok,
        unexpected=unexpected,
        format_errors=format_errors,
        messages=messages,
    )
    return result


def validate_diffs_or_raise(
    diffs: Sequence[dict[str, Any]],
    allowlist: dict[str, Any],
) -> ValidationResult:
    """validate_diffs；失敗 raise AttributionValidationError。"""
    result = validate_diffs(diffs, allowlist)
    print(result.machine_line())
    if not result.ok:
        detail = "; ".join(result.messages) or "validation failed"
        raise AttributionValidationError(detail)
    return result


def empty_diff_passes(allowlist: dict[str, Any]) -> ValidationResult:
    """空 diff 必 PASS（B0 rows=[] 合法）。"""
    return validate_diffs([], allowlist)


# ---------------------------------------------------------------------------
# B4 freeze：forbid_append_after_b4_start（TODO Task 4.1 / policy 閘門）
# ---------------------------------------------------------------------------
def allowlist_rows_fingerprint(allowlist: dict[str, Any]) -> str:
    """rows 的 canonical sha256（排序鍵穩定；B4 擅擴閘門用）。"""
    import hashlib

    rows = allowlist.get("rows")
    if not isinstance(rows, list):
        rows = []
    # 每 row 五鍵 + 其餘欄位；鍵排序後 dumps
    normalized: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            normalized.append({"_invalid": repr(row)})
            continue
        normalized.append({str(k): row[k] for k in sorted(row.keys())})
    payload = json.dumps(
        normalized,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
        default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def validate_allowlist_not_expanded(
    allowlist: dict[str, Any],
    *,
    frozen_fingerprint: str,
) -> list[str]:
    """B4：allowlist rows fingerprint 必須等於凍結值；擅擴/竄改 → errors。"""
    if not isinstance(frozen_fingerprint, str) or not frozen_fingerprint.strip():
        return ["frozen_fingerprint must be non-empty str"]
    live = allowlist_rows_fingerprint(allowlist)
    if live != frozen_fingerprint:
        n = len(allowlist.get("rows") or []) if isinstance(allowlist.get("rows"), list) else -1
        return [
            f"allowlist expanded or mutated after B4 freeze "
            f"(rows={n}, got_fp={live}, frozen_fp={frozen_fingerprint})"
        ]
    return []


def validate_allowlist_not_expanded_or_raise(
    allowlist: dict[str, Any],
    *,
    frozen_fingerprint: str,
) -> str:
    """validate_allowlist_not_expanded；失敗 raise AttributionValidationError。"""
    errs = validate_allowlist_not_expanded(
        allowlist, frozen_fingerprint=frozen_fingerprint
    )
    if errs:
        raise AttributionValidationError("; ".join(errs))
    return allowlist_rows_fingerprint(allowlist)


def validate_b4_attribution(
    diffs: Sequence[dict[str, Any]],
    allowlist: dict[str, Any],
    *,
    frozen_fingerprint: str | None = None,
) -> ValidationResult:
    """B4 收口：可選 freeze 閘門 + diff/allowlist 對帳；印 machine line。

    freeze/format FAIL 時 machine line 含 ``FAIL format_errors=…``，
    不會只印 ``UNEXPECTED=0`` 造成假綠。
    """
    if frozen_fingerprint is not None:
        freeze_errs = validate_allowlist_not_expanded(
            allowlist, frozen_fingerprint=frozen_fingerprint
        )
        if freeze_errs:
            result = ValidationResult(
                ok=False,
                format_errors=list(freeze_errs),
                messages=list(freeze_errs),
            )
            print(result.machine_line())
            return result
    result = validate_diffs(diffs, allowlist)
    print(result.machine_line())
    return result


# ---------------------------------------------------------------------------
# B4 recursive artifact diff（禁手選 builders；未枚舉欄位自動進對帳）
# ---------------------------------------------------------------------------
# 與 hash sibling 並存的 element dump：以 *_sha256 為 canonical 對帳鍵，略過 dump 本體
_ELEMENT_DUMP_SKIP: dict[str, str] = {
    "labels": "labels_sha256",
    "timestamps": "timestamps_sha256",
}

_LARGE_LIST_LEAF = 32  # 超過此長度的純量 list 以 sha256 作 old/new 表示


def _json_canonical_sha256(value: Any) -> str:
    import hashlib

    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
        default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def values_equal(old: Any, new: Any, *, atol: float = 1e-12) -> bool:
    """值相等：float 用 abs atol；NaN==NaN；list/dict 遞迴。"""
    if old is new:
        return True
    if isinstance(old, float) and isinstance(new, float):
        if old != old and new != new:  # NaN
            return True
        return abs(old - new) <= atol
    # JSON int/float 互通（1 vs 1.0）
    if isinstance(old, (int, float)) and isinstance(new, (int, float)):
        if isinstance(old, bool) or isinstance(new, bool):
            return old == new
        return abs(float(old) - float(new)) <= atol
    if isinstance(old, dict) and isinstance(new, dict):
        if set(old.keys()) != set(new.keys()):
            return False
        return all(values_equal(old[k], new[k], atol=atol) for k in old)
    if isinstance(old, list) and isinstance(new, list):
        if len(old) != len(new):
            return False
        return all(values_equal(a, b, atol=atol) for a, b in zip(old, new))
    return old == new


def deep_equal_json(
    old: Any,
    new: Any,
    *,
    path: str = "",
    atol: float = 1e-12,
) -> list[str]:
    """遞迴 deep-equal；回傳 mismatch 訊息列表（空=相等）。"""
    mismatches: list[str] = []

    def _walk(o: Any, n: Any, p: str) -> None:
        if isinstance(o, dict) and isinstance(n, dict):
            keys = sorted(set(o) | set(n), key=str)
            for k in keys:
                child = f"{p}.{k}" if p else str(k)
                if k not in o:
                    mismatches.append(f"{child}: missing in old (new present)")
                    continue
                if k not in n:
                    mismatches.append(f"{child}: missing in new (old present)")
                    continue
                _walk(o[k], n[k], child)
            return
        if isinstance(o, list) and isinstance(n, list):
            if len(o) != len(n):
                mismatches.append(f"{p}: list len {len(o)} != {len(n)}")
                return
            # 大 list 當 atomic leaf（避免 20k 訊息）
            if len(o) > _LARGE_LIST_LEAF:
                if not values_equal(o, n, atol=atol):
                    mismatches.append(
                        f"{p}: large-list mismatch "
                        f"sha_old={_json_canonical_sha256(o)[:16]} "
                        f"sha_new={_json_canonical_sha256(n)[:16]}"
                    )
                return
            for i, (a, b) in enumerate(zip(o, n)):
                _walk(a, b, f"{p}[{i}]")
            return
        if not values_equal(o, n, atol=atol):
            mismatches.append(f"{p}: {o!r} != {n!r}")

    _walk(old, new, path)
    return mismatches


def recursive_json_diff(
    old: Any,
    new: Any,
    *,
    path_prefix: str = "",
    class_name: str,
    index: Any = None,
    atol: float = 1e-12,
    default_index: Any = None,
) -> list[dict[str, Any]]:
    """完整 JSON 樹 recursive diff → attribution row 列表。

    - dict：遍歷 key 聯集（未枚舉欄位自動進對帳）
    - 純量 leaf：float abs atol=1e-12；NaN==NaN
    - 大 list：atomic leaf，old/new 以 canonical sha256 表示（避免巨型 payload）
    - xgboost ``labels``/``timestamps`` element dump：若 sibling ``*_sha256`` 存在則略過
      （以 hash 欄為 canonical；防雙重表示假 UNEXPECTED）
    """
    diffs: list[dict[str, Any]] = []

    def _leaf_payload(value: Any) -> Any:
        if isinstance(value, list) and len(value) > _LARGE_LIST_LEAF:
            return {
                "_sha256": _json_canonical_sha256(value),
                "_len": len(value),
            }
        return value

    def _emit(path: str, o: Any, n: Any, idx: Any) -> None:
        if values_equal(o, n, atol=atol):
            return
        diffs.append(
            {
                "path": path,
                "index": idx if idx is not None else (default_index if default_index is not None else path),
                "old": _leaf_payload(o),
                "new": _leaf_payload(n),
                "class": class_name,
            }
        )

    def _walk(o: Any, n: Any, path: str, idx: Any) -> None:
        # 一端缺失
        if o is None and n is None:
            return
        if isinstance(o, dict) and isinstance(n, dict):
            keys = sorted(set(o) | set(n), key=str)
            for k in keys:
                # element dump skip if sibling hash present in either side
                skip_hash = _ELEMENT_DUMP_SKIP.get(str(k))
                if skip_hash is not None and (skip_hash in o or skip_hash in n):
                    continue
                child_path = f"{path}.{k}" if path else str(k)
                ov = o.get(k)
                nv = n.get(k)
                if k not in o:
                    _emit(child_path, None, nv, idx)
                    continue
                if k not in n:
                    _emit(child_path, ov, None, idx)
                    continue
                _walk(ov, nv, child_path, idx)
            return
        if isinstance(o, dict) != isinstance(n, dict):
            _emit(path, o, n, idx)
            return
        if isinstance(o, list) and isinstance(n, list):
            _emit(path, o, n, idx)
            return
        _emit(path, o, n, idx)

    _walk(old, new, path_prefix, index)
    return diffs
