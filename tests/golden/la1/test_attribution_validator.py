"""LA-1 B0: attribution_validator 測（TODO Task 0.2 + B0-fix）。

1. 空 diff PASS
2. 未列 diff FAIL
3. 格式錯 row（缺 path/index/old/new/class）FAIL
4. wrong-value（同 path/index 錯 old/new）FAIL
5. wrong-class（同 path/index/old/new 錯 class）FAIL
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from tests.golden.la1.attribution_validator import (
    CLASS_ENUM,
    AttributionValidationError,
    load_allowlist,
    validate_allowlist_schema,
    validate_diffs,
    validate_diffs_or_raise,
)

LA1_DIR = Path(__file__).resolve().parent
ALLOWLIST_PATH = LA1_DIR / "attribution_allowlist.json"


def _populated_allowlist() -> dict[str, Any]:
    """內嵌 allowlist（含一筆 predeclare 列），供 wrong-value / wrong-class 負例。"""
    return {
        "schema_version": "la1_attr_v1",
        "class_enum": sorted(CLASS_ENUM),
        "rows": [
            {
                "path": "regime_rule.per_regime.high_vol.per_feature.feat_a.ic",
                "index": 0,
                "old": 1,
                "new": 2,
                "class": "P1-1",
            }
        ],
    }


@pytest.fixture(scope="module")
def allowlist() -> dict:
    data = load_allowlist(ALLOWLIST_PATH)
    errs = validate_allowlist_schema(data)
    assert not errs, errs
    assert data.get("rows") == []
    assert set(data.get("class_enum") or []) == {
        "P1-1",
        "P1-1b",
        "P1-1c",
        "P1-2",
        "P1-3-obs",
    }
    return data


def test_empty_diff_passes(allowlist: dict) -> None:
    """空 diff + B0 空 rows → PASS。"""
    result = validate_diffs([], allowlist)
    assert result.ok is True
    assert result.unexpected_count == 0
    assert result.machine_line() == "UNEXPECTED=0"


def test_unlisted_diff_fails(allowlist: dict) -> None:
    """未列於 allowlist 的 diff → FAIL（unlisted=unexpected）。"""
    diffs = [
        {
            "path": "regime_rule.per_regime.high_vol.per_feature.feat_a.ic",
            "index": 0,
            "old": 0.12,
            "new": 0.01,
            "class": "P1-1",
        }
    ]
    result = validate_diffs(diffs, allowlist)
    assert result.ok is False
    assert result.unexpected_count == 1
    assert result.machine_line() == "UNEXPECTED=1"
    with pytest.raises(AttributionValidationError):
        validate_diffs_or_raise(diffs, allowlist)


def test_malformed_row_missing_path_or_index_fails(allowlist: dict) -> None:
    """格式錯 row：缺 path 或 index → FAIL。"""
    missing_path = [{"index": 0, "old": 1, "new": 2, "class": "P1-1"}]
    r1 = validate_diffs(missing_path, allowlist)
    assert r1.ok is False
    assert any("path" in e for e in r1.format_errors)

    missing_index = [
        {
            "path": "long_short.features.x.recommendation",
            "old": "雙向交易",
            "new": "不建議",
            "class": "P1-2",
        }
    ]
    r2 = validate_diffs(missing_index, allowlist)
    assert r2.ok is False
    assert any("index" in e for e in r2.format_errors)


def test_malformed_row_missing_old_new_or_class_fails(allowlist: dict) -> None:
    """格式錯 row：缺 old / new / class → FAIL（五鍵 schema）。"""
    base = {
        "path": "regime_rule.x",
        "index": 0,
        "old": 1,
        "new": 2,
        "class": "P1-1",
    }
    for missing in ("old", "new", "class"):
        row = {k: v for k, v in base.items() if k != missing}
        result = validate_diffs([row], allowlist)
        assert result.ok is False, f"expected fail when missing {missing}"
        assert any(missing in e for e in result.format_errors), result.format_errors


def test_wrong_value_fails() -> None:
    """同 path+index、錯 old/new → 不可洗過（wrong-value 負例）。"""
    allowlist = _populated_allowlist()
    assert not validate_allowlist_schema(allowlist)

    # 正確五鍵 match → PASS
    ok_diff = [
        {
            "path": "regime_rule.per_regime.high_vol.per_feature.feat_a.ic",
            "index": 0,
            "old": 1,
            "new": 2,
            "class": "P1-1",
        }
    ]
    ok = validate_diffs(ok_diff, allowlist)
    assert ok.ok is True
    assert ok.unexpected_count == 0

    # wrong-value：path/index/class 同，old/new 不同 → unexpected
    bad_value = [
        {
            "path": "regime_rule.per_regime.high_vol.per_feature.feat_a.ic",
            "index": 0,
            "old": 999,
            "new": -999,
            "class": "P1-1",
        }
    ]
    result = validate_diffs(bad_value, allowlist)
    assert result.ok is False
    assert result.unexpected_count == 1
    with pytest.raises(AttributionValidationError):
        validate_diffs_or_raise(bad_value, allowlist)


def test_wrong_class_fails() -> None:
    """同 path+index+old/new、錯 class → 不可洗過（wrong-class 負例）。"""
    allowlist = _populated_allowlist()
    bad_class = [
        {
            "path": "regime_rule.per_regime.high_vol.per_feature.feat_a.ic",
            "index": 0,
            "old": 1,
            "new": 2,
            "class": "P1-2",  # allowed is P1-1
        }
    ]
    result = validate_diffs(bad_class, allowlist)
    assert result.ok is False
    assert result.unexpected_count == 1
    with pytest.raises(AttributionValidationError):
        validate_diffs_or_raise(bad_class, allowlist)


def test_allowlist_json_loads() -> None:
    """sanity：attribution_allowlist.json 可 json.load。"""
    payload = json.loads(ALLOWLIST_PATH.read_text(encoding="utf-8"))
    assert payload["rows"] == []
    assert "schema_version" in payload
