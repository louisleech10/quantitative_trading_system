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
# schema 硬需求：五鍵齊全（path/index/old/new/class）；old/new 可 null 但鍵須存在
REQUIRED_ROW_KEYS = frozenset({"path", "index", "old", "new", "class"})
REQUIRED_FORMAT_KEYS = REQUIRED_ROW_KEYS


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
        """B4 掃描用 machine line。"""
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


def validate_allowlist_schema(allowlist: dict[str, Any]) -> list[str]:
    """檢查 allowlist schema（B0：rows 可空）。"""
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
    # index: int | str | list（exact locator）；禁缺鍵、禁 null
    if "index" in row and row["index"] is None:
        errors.append(f"{loc}: index must not be null")
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
