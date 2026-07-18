"""LA-2 attribution allowlist validator（SPEC §G / TODO Task 0.2）。

diff vs allowlist：unlisted = FAIL。
row 格式 = exact JSON path + index + old/new discriminator。
≥5 wash mutation 打紅（見 test_attribution_validator.py）。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, Sequence

# TODO Task 0.2 class_enum（8 類）
CLASS_ENUM = frozenset(
    {
        "P2-1-disable",
        "P2-2-oot",
        "P2-2-scope-tag",
        "P2-3a-factor-loud",
        "P2-3a-proxy-causal",
        "P2-3b-pattern-trainmask",
        "P2-3b-promotion-guard",
        "P2-3c-regime-remove",
    }
)

# P2-1-disable = raise-only（禁 old/new 數值洗綠）
RAISE_ONLY_CLASSES = frozenset({"P2-1-disable"})

# schema 硬需求：五鍵齊全（path/index/old/new/class）；old/new 可 null 但鍵須存在
REQUIRED_ROW_KEYS = frozenset({"path", "index", "old", "new", "class"})
REQUIRED_FORMAT_KEYS = REQUIRED_ROW_KEYS

# §0.6-APPENDIX C：28 path eval_scope enum
EVAL_SCOPE_ENUM = frozenset({"oot", "cv_oof", "in_sample_research_only"})
CONSUMER_ENUM = frozenset({"deny", "ok", "research_only"})
EXPECTED_EVAL_SCOPE_PATH_COUNT = 28

# §0.6-APPENDIX C canonical path 集合（精確集合比對；換 phantom/增刪 → FAIL）
CANONICAL_EVAL_SCOPE_PATHS: frozenset[str] = frozenset(
    {
        "/model_performance/in_sample_train_auc",
        "/model_performance/fit_pool_auc",
        "/model_performance/overfitting_score",
        "/model_performance/precision",
        "/model_performance/recall",
        "/model_performance/f1_score",
        "/model_performance/cv_auc_mean",
        "/model_performance/cv_auc_std",
        "/model_performance/oot_auc",
        "/model_performance/calibration_curve",
        "/model_performance/brier_score",
        "/model_performance/ece",
        "/model_performance/pr_curve",
        "/model_performance/pr_auc",
        "/model_performance/precision_at_k",
        "/model_performance/recommend_k",
        "/model_performance/expectancy",
        "/model_performance/sharpe_proxy",
        "/model_performance/bootstrap_ci",
        "/model_performance/predictions/train",
        "/model_performance/predictions/oot",
        "/model_performance/feature_importance",
        "/model_performance/feature_importance_all",
        "/model_performance/permutation_importance",
        "/model_performance/fold_importance_stability",
        "/model_performance/shap_sample",
        "/model_performance/regime_analysis",
        "/model_performance/cross_symbol_validation",
    }
)
assert len(CANONICAL_EVAL_SCOPE_PATHS) == EXPECTED_EVAL_SCOPE_PATH_COUNT


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


def validate_eval_scope_field_map(allowlist: dict[str, Any]) -> list[str]:
    """檢查 §0.6-C eval_scope_field_map：精確 28-path 集合 + scope/consumer enum。

    B0-F3：不只數 count——path 換 phantom / 增刪任一 → schema error FAIL。
    """
    errors: list[str] = []
    fmap = allowlist.get("eval_scope_field_map")
    if not isinstance(fmap, dict):
        return ["missing or non-object eval_scope_field_map"]
    actual_paths = set(fmap.keys())
    if actual_paths != CANONICAL_EVAL_SCOPE_PATHS:
        missing = sorted(CANONICAL_EVAL_SCOPE_PATHS - actual_paths)
        extra = sorted(actual_paths - CANONICAL_EVAL_SCOPE_PATHS)
        errors.append(
            "eval_scope_field_map path set != §0.6-C canonical set "
            f"(count={len(actual_paths)} expected={EXPECTED_EVAL_SCOPE_PATH_COUNT}; "
            f"missing={missing}; extra={extra})"
        )
    if len(fmap) != EXPECTED_EVAL_SCOPE_PATH_COUNT:
        errors.append(
            f"eval_scope_field_map must have exactly "
            f"{EXPECTED_EVAL_SCOPE_PATH_COUNT} paths, got {len(fmap)}"
        )
    for path, body in fmap.items():
        if not isinstance(path, str) or not path.startswith("/model_performance/"):
            errors.append(f"eval_scope path must start with /model_performance/: {path!r}")
        if path not in CANONICAL_EVAL_SCOPE_PATHS:
            errors.append(
                f"eval_scope path not in §0.6-C canonical set (phantom?): {path!r}"
            )
        if not isinstance(body, dict):
            errors.append(f"eval_scope_field_map[{path!r}] must be object")
            continue
        scope = body.get("eval_scope")
        consumer = body.get("consumer")
        if scope not in EVAL_SCOPE_ENUM:
            errors.append(
                f"eval_scope_field_map[{path!r}].eval_scope invalid: {scope!r}"
            )
        if consumer not in CONSUMER_ENUM:
            errors.append(
                f"eval_scope_field_map[{path!r}].consumer invalid: {consumer!r}"
            )
    return errors


def validate_allowlist_schema(allowlist: dict[str, Any]) -> list[str]:
    """檢查 allowlist schema（B0：rows 可空 + eval_scope_field_map 28 path）。"""
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
        if len(class_enum) != len(CLASS_ENUM):
            errors.append(
                f"class_enum must have exactly {len(CLASS_ENUM)} entries, "
                f"got {len(class_enum)}"
            )
    rows = allowlist.get("rows")
    if rows is None:
        errors.append("missing rows")
    elif not isinstance(rows, list):
        errors.append("rows must be list")
    else:
        for i, row in enumerate(rows):
            errors.extend(_format_errors_for_row(row, loc=f"allowlist.rows[{i}]"))
    errors.extend(validate_eval_scope_field_map(allowlist))
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
    if "index" in row and row["index"] is None:
        errors.append(f"{loc}: index must not be null")
    if "index" in row and row["index"] == "*":
        errors.append(f"{loc}: index wildcard '*' forbidden (element-exact required)")
    if "index" in row and isinstance(row["index"], str) and "*" in row["index"]:
        errors.append(
            f"{loc}: index must not contain wildcard '*': {row['index']!r}"
        )
    if "class" in row and row["class"] not in CLASS_ENUM:
        errors.append(f"{loc}: class not in class_enum: {row.get('class')!r}")
    # raise-only class 不得帶數值 old/new 洗綠（T5）
    if row.get("class") in RAISE_ONLY_CLASSES:
        behavior = row.get("behavior")
        if behavior is not None and behavior != "raises":
            errors.append(
                f"{loc}: raise-only class must have behavior='raises', got {behavior!r}"
            )
        # 允許 old/new 為 null；若兩者皆為數值 → FAIL
        old, new = row.get("old"), row.get("new")
        if isinstance(old, (int, float)) and isinstance(new, (int, float)):
            errors.append(
                f"{loc}: raise-only class {row.get('class')!r} must not carry "
                f"numeric old/new value wash"
            )
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
    """比對 diff 列表與 allowlist rows；unlisted → unexpected FAIL。"""
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
    return ValidationResult(
        ok=ok,
        unexpected=unexpected,
        format_errors=format_errors,
        messages=messages,
    )


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


def allowlist_rows_fingerprint(allowlist: dict[str, Any]) -> str:
    """rows 的 canonical sha256（排序鍵穩定；B4 擅擴閘門用）。"""
    import hashlib

    rows = allowlist.get("rows")
    if not isinstance(rows, list):
        rows = []
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


# ---------------------------------------------------------------------------
# Wash mutation helpers（≥5；可證偽）
# ---------------------------------------------------------------------------
WASH_CASE_NAMES = (
    "control_path_inject_diff",
    "track2_fullsample_claim_oot",
    "delete_loud_claim_tagged",
    "wrong_class_swap",
    "unauthorized_allowlist_expand",
)


def apply_wash_mutation(
    wash_case: str,
    allowlist: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """回傳 (forged_diffs, allowlist_for_validate) 供 wash 負例。

    ① control_path_inject_diff — 竄改 control 塞 diff
    ② track2_fullsample_claim_oot — 軌2 全樣本值標成已修 OOT
    ③ delete_loud_claim_tagged — 刪 loud 欄稱已標
    ④ wrong_class_swap — wrong-class swap
    ⑤ unauthorized_allowlist_expand — 擅擴 allowlist
    """
    import copy

    al = copy.deepcopy(allowlist)
    if wash_case == "control_path_inject_diff":
        diffs = [
            {
                "path": "control.regime_pit.labels_sha256",
                "index": "BTCUSDT/1h",
                "old": "a" * 64,
                "new": "b" * 64,
                "class": "P2-3c-regime-remove",
            }
        ]
        return diffs, al

    if wash_case == "track2_fullsample_claim_oot":
        # 把 in-sample 樂觀值偽造成 oot 已修
        diffs = [
            {
                "path": "model.model_performance.train_auc",
                "index": "BTCUSDT/1h",
                "old": 0.99,
                "new": 0.55,
                "class": "P2-2-oot",
            }
        ]
        return diffs, al

    if wash_case == "delete_loud_claim_tagged":
        # 仿 LA-1 delete_redflag_claim_p13_closed：
        # 先 seed 合法 P2-3a-factor-loud row → strip → 送同一 loud diff → 必 FAIL
        # （真測 missing attribution；禁 B0 rows=[] 時空轉 unlisted）
        seed = {
            "path": "factor.oos_guarantees",
            "index": "root",
            "old": None,
            "new": False,
            "class": "P2-3a-factor-loud",
        }
        seeded_rows = list(al.get("rows") or []) + [seed]
        assert any(r.get("class") == "P2-3a-factor-loud" for r in seeded_rows)
        # strip loud 列（刪 loud claim 後 allowlist 不再認可）
        stripped_rows = [
            r for r in seeded_rows if r.get("class") != "P2-3a-factor-loud"
        ]
        assert not any(r.get("class") == "P2-3a-factor-loud" for r in stripped_rows)
        al["rows"] = stripped_rows
        # 仍呈 factor loud 已標（missing attribution）
        diffs = [dict(seed)]
        return diffs, al

    if wash_case == "wrong_class_swap":
        # 若 rows 空：先種一筆合法 row，再以錯 class 比對
        seed = {
            "path": "pattern.threshold_value_sha256",
            "index": "BTCUSDT/1h",
            "old": "oldhash",
            "new": "newhash",
            "class": "P2-3b-pattern-trainmask",
        }
        al["rows"] = list(al.get("rows") or []) + [seed]
        swapped = {
            "path": seed["path"],
            "index": seed["index"],
            "old": seed["old"],
            "new": seed["new"],
            "class": "P2-3a-factor-loud",  # wrong class
        }
        return [swapped], al

    if wash_case == "unauthorized_allowlist_expand":
        # 外部 diff 未列於 allowlist → unlisted；同時可測 fingerprint 擅擴
        expanded = copy.deepcopy(al)
        expanded["rows"] = list(expanded.get("rows") or []) + [
            {
                "path": "phantom.unauthorized",
                "index": "x",
                "old": 1,
                "new": 2,
                "class": "P2-2-scope-tag",
            }
        ]
        # 用原 allowlist 驗證 phantom diff → unlisted FAIL
        diffs = [
            {
                "path": "phantom.unauthorized",
                "index": "x",
                "old": 1,
                "new": 2,
                "class": "P2-2-scope-tag",
            }
        ]
        return diffs, al  # al 未擴 → unlisted

    raise ValueError(f"unknown wash_case: {wash_case!r}")
