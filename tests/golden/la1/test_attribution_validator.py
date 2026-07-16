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
    FIVE_PATH_CLASSES,
    ZERO_DIFF_JUSTIFICATIONS_KEY,
    AttributionValidationError,
    baseline_has_path,
    load_allowlist,
    validate_allowlist_paths_against_baseline,
    validate_allowlist_schema,
    validate_diffs,
    validate_diffs_or_raise,
    validate_zero_diff_justifications,
)

LA1_DIR = Path(__file__).resolve().parent
ALLOWLIST_PATH = LA1_DIR / "attribution_allowlist.json"
BTC_BASELINE_PATH = LA1_DIR / "BTCUSDT_1h_baseline.json"
ETH_BASELINE_PATH = LA1_DIR / "ETHUSDT_12h_baseline.json"


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
    # B0 時空 rows；B1/B2/B3 可 append（schema 仍須合法）
    assert isinstance(data.get("rows"), list)
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
    """sanity：attribution_allowlist.json 可 json.load（B3 可含 P1-3-obs rows）。"""
    payload = json.loads(ALLOWLIST_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload.get("rows"), list)
    assert "schema_version" in payload
    baseline_btc = json.loads(BTC_BASELINE_PATH.read_text(encoding="utf-8"))
    baseline_eth = json.loads(ETH_BASELINE_PATH.read_text(encoding="utf-8"))
    # 多 symbol 聯集：P1-2 long_short 的 ETH feature path 僅存在於 ETH baseline
    errs = validate_allowlist_schema(
        payload, baseline=[baseline_btc, baseline_eth]
    )
    assert not errs, errs
    # B1-fix3：P1-1c 須含真實 regime_kmeans.*（非 phantom labels_sha256）
    km_rows = [
        r
        for r in payload["rows"]
        if r.get("class") == "P1-1c"
        and str(r.get("path") or "").startswith("regime_kmeans.")
    ]
    assert km_rows, "expected P1-1c regime_kmeans.* rows after B1-fix3"
    assert all(
        not str(r["path"]).startswith("regime_kmeans.labels_sha256")
        and ".value_counts." not in str(r["path"])
        for r in km_rows
    )
    assert any(str(r["path"]).endswith("value_sha256") for r in km_rows)
    # Task 1.5：P1-1b 零 diff 須 machine-readable 說明
    assert ZERO_DIFF_JUSTIFICATIONS_KEY in payload
    zdj = payload[ZERO_DIFF_JUSTIFICATIONS_KEY]
    assert "P1-1b" in zdj
    p11b = zdj["P1-1b"]
    if isinstance(p11b, dict):
        assert isinstance(p11b.get("reason"), str) and p11b["reason"].strip()
    else:
        assert isinstance(p11b, str) and p11b.strip()
    assert not any(r.get("class") == "P1-1b" for r in payload["rows"])
    # B3 append 的 P1-3-obs 必須五鍵齊全；index 禁 wildcard
    p13_paths = {
        "analysis_status",
        "oos_guarantees",
        "summary_table.pass_class",
        "filter_log.stage5_thresholds.output_features.pass_class",
        "filter_log.stage5_thresholds.pass_class",
    }
    p13_news = set()
    p12_rows = 0
    for row in payload["rows"]:
        assert set(row.keys()) >= {"path", "index", "old", "new", "class"}
        assert row.get("index") != "*"
        if row.get("class") == "P1-3-obs":
            assert row["path"] in p13_paths
            p13_news.add((row["path"], row["new"]))
        elif row.get("class") in FIVE_PATH_CLASSES:
            # F-B1-001：five-path class path 必須存在於 BTC∪ETH baseline
            assert baseline_has_path(baseline_btc, row["path"]) or baseline_has_path(
                baseline_eth, row["path"]
            ), row["path"]
            if row.get("class") == "P1-2":
                p12_rows += 1
    # Task 2.2：B2 須 append 至少一筆 P1-2 long_short diff
    assert p12_rows > 0, "expected P1-2 allowlist rows after B2"
    # B3-ATTR-01：須含 normal pass_class=oos 與 filter_log diffs
    assert ("summary_table.pass_class", "oos") in p13_news
    assert ("summary_table.pass_class", "full_sample_research_only") in p13_news
    assert (
        "filter_log.stage5_thresholds.output_features.pass_class",
        "oos",
    ) in p13_news
    assert (
        "filter_log.stage5_thresholds.output_features.pass_class",
        "full_sample_research_only",
    ) in p13_news


def test_allowlist_phantom_path_fails_baseline_schema() -> None:
    """F-B1-001：path 不在 baseline → schema FAIL（單 symbol 語意保留）。"""
    baseline = json.loads(BTC_BASELINE_PATH.read_text(encoding="utf-8"))
    # 真實鍵：xgboost_phases 有 labels_sha256；regime_kmeans 無
    assert baseline_has_path(baseline, "xgboost_phases.labels_sha256")
    assert not baseline_has_path(baseline, "regime_kmeans.labels_sha256")
    assert not baseline_has_path(baseline, "regime_fallback.labels_sha256")

    phantom = {
        "schema_version": "la1_attr_v1",
        "class_enum": sorted(CLASS_ENUM),
        "rows": [
            {
                "path": "regime_kmeans.labels_sha256",
                "index": "BTCUSDT/1h",
                "old": "a",
                "new": "b",
                "class": "P1-1c",
            }
        ],
    }
    errs = validate_allowlist_schema(phantom, baseline=baseline)
    assert errs, "expected phantom path to fail schema"
    assert any("not present in baseline" in e for e in errs), errs
    path_errs = validate_allowlist_paths_against_baseline(phantom, baseline)
    assert path_errs


def test_baseline_union_positive_and_negative() -> None:
    """F-B2-005：多 symbol 聯集正反例；單 baseline 缺 path 仍 FAIL。"""
    baseline_btc = json.loads(BTC_BASELINE_PATH.read_text(encoding="utf-8"))
    baseline_eth = json.loads(ETH_BASELINE_PATH.read_text(encoding="utf-8"))

    btc_feats = set(
        ((baseline_btc.get("long_short") or {}).get("features") or {}).keys()
    )
    eth_feats = set(
        ((baseline_eth.get("long_short") or {}).get("features") or {}).keys()
    )
    only_eth = sorted(eth_feats - btc_feats)
    assert only_eth, "expected at least one ETH-only long_short feature in baselines"
    feat_name = only_eth[0]
    eth_only_path = f"long_short.features.{feat_name}.long_ic"
    assert baseline_has_path(baseline_eth, eth_only_path)
    assert not baseline_has_path(baseline_btc, eth_only_path)

    row = {
        "path": eth_only_path,
        "index": "ETHUSDT/12h",
        "old": 0.0,
        "new": 0.1,
        "class": "P1-2",
    }
    allow = {
        "schema_version": "la1_attr_v1",
        "class_enum": sorted(CLASS_ENUM),
        "rows": [row],
    }

    # 正例：BTC∪ETH 聯集 → path 存在 → PASS
    errs_union = validate_allowlist_paths_against_baseline(
        allow, baseline=[baseline_btc, baseline_eth]
    )
    assert not errs_union, errs_union
    errs_schema_union = validate_allowlist_schema(
        allow, baseline=[baseline_btc, baseline_eth]
    )
    assert not errs_schema_union, errs_schema_union

    # 反例 1：僅 BTC 單 baseline → ETH-only path 查不到 → FAIL（單 symbol 語意保留）
    errs_btc_only = validate_allowlist_paths_against_baseline(allow, baseline_btc)
    assert errs_btc_only, "ETH-only path must FAIL against BTC-only baseline"
    assert any("not present in baseline" in e for e in errs_btc_only)

    # 反例 2：聯集仍找不到的 phantom → FAIL
    phantom = {
        "schema_version": "la1_attr_v1",
        "class_enum": sorted(CLASS_ENUM),
        "rows": [
            {
                "path": "long_short.features.no_such_feature_anywhere.long_ic",
                "index": "ETHUSDT/12h",
                "old": 0.0,
                "new": 0.1,
                "class": "P1-2",
            }
        ],
    }
    errs_phantom = validate_allowlist_paths_against_baseline(
        phantom, baseline=[baseline_btc, baseline_eth]
    )
    assert errs_phantom, "path missing from both baselines must FAIL"
    assert any("not present in baseline" in e for e in errs_phantom)


def test_allowlist_schema_rejects_wildcard_index() -> None:
    """B3-ATTR-02：validator 拒 index='*'（element-exact 契約）。"""
    bad = {
        "schema_version": "la1_attr_v1",
        "class_enum": sorted(CLASS_ENUM),
        "rows": [
            {
                "path": "summary_table.pass_class",
                "index": "*",
                "old": None,
                "new": "oos",
                "class": "P1-3-obs",
            }
        ],
    }
    errs = validate_allowlist_schema(bad)
    assert errs, "expected wildcard index to fail schema"
    assert any("wildcard" in e or "'*'" in e for e in errs), errs


def test_zero_diff_justifications_schema() -> None:
    """B1-fix3 / Task 1.5：zero_diff_justifications 形狀 gate。"""
    # 缺鍵 → 合法
    base = {
        "schema_version": "la1_attr_v1",
        "class_enum": sorted(CLASS_ENUM),
        "rows": [],
    }
    assert validate_zero_diff_justifications(base) == []
    assert not validate_allowlist_schema(base)

    # str reason OK
    ok_str = {
        **base,
        ZERO_DIFF_JUSTIFICATIONS_KEY: {"P1-1b": "no surface on five-path"},
    }
    assert validate_zero_diff_justifications(ok_str) == []
    assert not validate_allowlist_schema(ok_str)

    # object+reason+evidence OK
    ok_obj = {
        **base,
        ZERO_DIFF_JUSTIFICATIONS_KEY: {
            "P1-1b": {
                "reason": "kmeans samples sufficient; fallback not entered",
                "evidence": {"fallback_rule_based_calls": 0},
            }
        },
    }
    assert validate_zero_diff_justifications(ok_obj) == []
    assert not validate_allowlist_schema(ok_obj)

    # unknown class
    bad_cls = {**base, ZERO_DIFF_JUSTIFICATIONS_KEY: {"P9-x": "nope"}}
    errs = validate_zero_diff_justifications(bad_cls)
    assert errs and any("class_enum" in e for e in errs)

    # empty reason / missing reason
    bad_empty = {**base, ZERO_DIFF_JUSTIFICATIONS_KEY: {"P1-1b": "  "}}
    assert validate_zero_diff_justifications(bad_empty)
    bad_obj = {
        **base,
        ZERO_DIFF_JUSTIFICATIONS_KEY: {"P1-1b": {"evidence": {}}},
    }
    assert validate_zero_diff_justifications(bad_obj)

    # non-object body
    bad_body = {**base, ZERO_DIFF_JUSTIFICATIONS_KEY: ["P1-1b"]}
    assert validate_zero_diff_justifications(bad_body)
