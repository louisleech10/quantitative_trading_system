"""LA-1 attribution_validator 測（TODO Task 0.2 + B0-fix + Task 4.1 wash）。

1. 空 diff PASS
2. 未列 diff FAIL
3. 格式錯 row（缺 path/index/old/new/class）FAIL
4. wrong-value（同 path/index 錯 old/new）FAIL
5. wrong-class（同 path/index/old/new 錯 class）FAIL
6. B4 wash mutations ×5（parametrize；in-memory 竄改 → validator FAIL）
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from tests.golden.la1.attribution_validator import (
    CLASS_ENUM,
    FIVE_PATH_CLASSES,
    ZERO_DIFF_JUSTIFICATIONS_KEY,
    AttributionValidationError,
    _row_key,
    allowlist_rows_fingerprint,
    artifact_symbol_tf,
    baseline_has_path,
    baseline_parent_has_skipped,
    load_allowlist,
    symbol_tf_from_index,
    validate_allowlist_not_expanded,
    validate_allowlist_not_expanded_or_raise,
    validate_allowlist_paths_against_baseline,
    validate_allowlist_schema,
    validate_b4_attribution,
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


def _inject_live_paths_for_added_keys(
    baselines: list[dict[str, Any]],
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """由 baseline 複製並注入 added_key path 的 leaf，供雙錨 live 側 schema 測。"""
    lives = [copy.deepcopy(b) for b in baselines]
    for row in rows:
        if row.get("added_key") is not True:
            continue
        path = row.get("path")
        if not isinstance(path, str) or not path:
            continue
        parts = path.split(".")
        # 優先注入到已有 parent skipped 的 baseline 副本
        injected = False
        for lv in lives:
            if baseline_parent_has_skipped(lv, path):
                cur: Any = lv
                for part in parts[:-1]:
                    assert isinstance(cur, dict) and part in cur
                    cur = cur[part]
                assert isinstance(cur, dict)
                cur[parts[-1]] = row.get("new")
                injected = True
                break
        if not injected:
            # fallback：掛在第一份 live 上建 path（僅供單元；正式列應有 skipped parent）
            cur = lives[0]
            for part in parts[:-1]:
                if not isinstance(cur, dict):
                    break
                cur = cur.setdefault(part, {})
            if isinstance(cur, dict):
                cur[parts[-1]] = row.get("new")
    return lives


def test_allowlist_json_loads() -> None:
    """sanity：attribution_allowlist.json 可 json.load（B3 可含 P1-3-obs rows）。"""
    payload = json.loads(ALLOWLIST_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload.get("rows"), list)
    assert "schema_version" in payload
    baseline_btc = json.loads(BTC_BASELINE_PATH.read_text(encoding="utf-8"))
    baseline_eth = json.loads(ETH_BASELINE_PATH.read_text(encoding="utf-8"))
    # added_key 雙錨需 live：由 baseline 注入 result 形狀 leaf
    lives = _inject_live_paths_for_added_keys(
        [baseline_btc, baseline_eth], payload["rows"]
    )
    # 多 symbol 聯集：P1-2 long_short 的 ETH feature path 僅存在於 ETH baseline
    errs = validate_allowlist_schema(
        payload, baseline=[baseline_btc, baseline_eth], live=lives
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
    added_key_rows = 0
    for row in payload["rows"]:
        assert set(row.keys()) >= {"path", "index", "old", "new", "class"}
        assert row.get("index") != "*"
        if row.get("class") == "P1-3-obs":
            assert row["path"] in p13_paths
            p13_news.add((row["path"], row["new"]))
        elif row.get("class") in FIVE_PATH_CLASSES:
            if row.get("added_key") is True:
                # skipped→result：雙錨必須在 row index 同一 symbol/TF artifact 內成立
                added_key_rows += 1
                row_st = symbol_tf_from_index(row["index"])
                assert row_st is not None, row["index"]
                same_bases = [
                    b
                    for b in (baseline_btc, baseline_eth)
                    if artifact_symbol_tf(b) == row_st
                ]
                same_lives = [
                    lv for lv in lives if artifact_symbol_tf(lv) == row_st
                ]
                assert same_bases, (row["path"], row_st)
                assert any(
                    baseline_parent_has_skipped(b, row["path"]) for b in same_bases
                ), (row["path"], row_st)
                assert same_lives and any(
                    baseline_has_path(lv, row["path"]) for lv in same_lives
                ), (row["path"], row_st)
            else:
                # F-B1-001：一般 five-path path 必須存在於 BTC∪ETH baseline
                assert baseline_has_path(baseline_btc, row["path"]) or baseline_has_path(
                    baseline_eth, row["path"]
                ), row["path"]
            if row.get("class") == "P1-2":
                p12_rows += 1
    # allowlist-supp2：TRENDMODE rec/nq ×2 特徵 = 4 筆 added_key
    assert added_key_rows == 4, added_key_rows
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


def test_added_key_skipped_to_result_dual_anchor_positive() -> None:
    """allowlist-supp2：skipped→result 轉型 path 可標 added_key；雙錨齊 → PASS。"""
    baseline_eth = json.loads(ETH_BASELINE_PATH.read_text(encoding="utf-8"))
    feat = "close_12h_cycle_HT-TRENDMODE_Sign"
    parent = f"long_short.features.{feat}"
    rec_path = f"{parent}.recommendation"
    # baseline 為 skipped 形狀
    assert baseline_parent_has_skipped(baseline_eth, rec_path)
    assert not baseline_has_path(baseline_eth, rec_path)

    live = copy.deepcopy(baseline_eth)
    live["long_short"]["features"][feat] = {
        "recommendation": "不建議",
        "num_quantiles_used": 5,
    }
    assert baseline_has_path(live, rec_path)

    allow = {
        "schema_version": "la1_attr_v1",
        "class_enum": sorted(CLASS_ENUM),
        "rows": [
            {
                "path": rec_path,
                "index": f"ETHUSDT/12h/{feat}",
                "old": None,
                "new": "不建議",
                "class": "P1-2",
                "added_key": True,
            }
        ],
    }
    errs = validate_allowlist_paths_against_baseline(
        allow, baseline=baseline_eth, live=live
    )
    assert not errs, errs
    errs_schema = validate_allowlist_schema(
        allow, baseline=baseline_eth, live=live
    )
    assert not errs_schema, errs_schema


def test_added_key_phantom_missing_skipped_anchor_fails() -> None:
    """phantom added_key：無 baseline parent skipped → 必紅。"""
    baseline_eth = json.loads(ETH_BASELINE_PATH.read_text(encoding="utf-8"))
    # 選一個 baseline 上非 skipped 的 feature
    feats = (baseline_eth.get("long_short") or {}).get("features") or {}
    non_skipped = None
    for name, body in feats.items():
        if isinstance(body, dict) and body.get("skipped") is not True:
            if "recommendation" in body or "long_ic" in body:
                non_skipped = name
                break
    assert non_skipped, "need a non-skipped long_short feature in ETH baseline"
    phantom_path = f"long_short.features.{non_skipped}.phantom_added_leaf"
    assert not baseline_parent_has_skipped(baseline_eth, phantom_path)

    live = copy.deepcopy(baseline_eth)
    live["long_short"]["features"][non_skipped]["phantom_added_leaf"] = 1

    allow = {
        "schema_version": "la1_attr_v1",
        "class_enum": sorted(CLASS_ENUM),
        "rows": [
            {
                "path": phantom_path,
                "index": f"ETHUSDT/12h/{non_skipped}",
                "old": None,
                "new": 1,
                "class": "P1-2",
                "added_key": True,
            }
        ],
    }
    errs = validate_allowlist_paths_against_baseline(
        allow, baseline=baseline_eth, live=live
    )
    assert errs, "phantom added_key without skipped parent must FAIL"
    assert any("skipped=true anchor" in e for e in errs), errs


def test_added_key_phantom_missing_live_path_fails() -> None:
    """phantom added_key：baseline skipped 在但 live 無 path → 必紅。"""
    baseline_eth = json.loads(ETH_BASELINE_PATH.read_text(encoding="utf-8"))
    feat = "close_12h_cycle_HT-TRENDMODE_Sign"
    rec_path = f"long_short.features.{feat}.recommendation"
    assert baseline_parent_has_skipped(baseline_eth, rec_path)
    # live 仍是 skipped 形狀，無 recommendation
    live = copy.deepcopy(baseline_eth)
    assert not baseline_has_path(live, rec_path)

    allow = {
        "schema_version": "la1_attr_v1",
        "class_enum": sorted(CLASS_ENUM),
        "rows": [
            {
                "path": rec_path,
                "index": f"ETHUSDT/12h/{feat}",
                "old": None,
                "new": "不建議",
                "class": "P1-2",
                "added_key": True,
            }
        ],
    }
    errs = validate_allowlist_paths_against_baseline(
        allow, baseline=baseline_eth, live=live
    )
    assert errs, "added_key without live path must FAIL"
    assert any("not present in live" in e for e in errs), errs


def test_added_key_requires_live_artifact() -> None:
    """added_key 未供 live → dual-anchor FAIL（fail-closed）。"""
    baseline_eth = json.loads(ETH_BASELINE_PATH.read_text(encoding="utf-8"))
    feat = "close_12h_cycle_HT-TRENDMODE_Sign"
    rec_path = f"long_short.features.{feat}.recommendation"
    allow = {
        "schema_version": "la1_attr_v1",
        "class_enum": sorted(CLASS_ENUM),
        "rows": [
            {
                "path": rec_path,
                "index": f"ETHUSDT/12h/{feat}",
                "old": None,
                "new": "不建議",
                "class": "P1-2",
                "added_key": True,
            }
        ],
    }
    errs = validate_allowlist_paths_against_baseline(allow, baseline=baseline_eth)
    assert errs
    assert any("requires live" in e for e in errs), errs
    # 未標 added_key 的同 path 仍走 baseline 存在性 → 亦紅
    allow_plain = copy.deepcopy(allow)
    del allow_plain["rows"][0]["added_key"]
    errs_plain = validate_allowlist_paths_against_baseline(
        allow_plain, baseline=baseline_eth
    )
    assert errs_plain
    assert any("not present in baseline" in e for e in errs_plain), errs_plain


def test_added_key_wrong_symbol_cross_artifact_phantom_fails() -> None:
    """SUPP-CODEX-1：ETH 真 added_key path + index 改 BTCUSDT/1h/* → 必紅。

    雙錨不得跨 artifact 配對：path 錨在 ETH、index 指 BTC 時，即使同時供
    BTC+ETH baseline 與含 ETH live path，schema 仍必須 FAIL。
    """
    baseline_btc = json.loads(BTC_BASELINE_PATH.read_text(encoding="utf-8"))
    baseline_eth = json.loads(ETH_BASELINE_PATH.read_text(encoding="utf-8"))
    feat = "close_12h_cycle_HT-TRENDMODE_Sign"
    rec_path = f"long_short.features.{feat}.recommendation"
    assert baseline_parent_has_skipped(baseline_eth, rec_path)
    assert not baseline_parent_has_skipped(baseline_btc, rec_path)

    live_eth = copy.deepcopy(baseline_eth)
    live_eth["long_short"]["features"][feat] = {
        "recommendation": "不建議",
        "num_quantiles_used": 5,
    }
    live_btc = copy.deepcopy(baseline_btc)
    assert baseline_has_path(live_eth, rec_path)
    assert not baseline_has_path(live_btc, rec_path)

    # 真 ETH path + 錯 symbol index（codex 反例）
    phantom = {
        "schema_version": "la1_attr_v1",
        "class_enum": sorted(CLASS_ENUM),
        "rows": [
            {
                "path": rec_path,
                "index": "BTCUSDT/1h/phantom",
                "old": None,
                "new": "不建議",
                "class": "P1-2",
                "added_key": True,
            }
        ],
    }
    errs = validate_allowlist_paths_against_baseline(
        phantom,
        baseline=[baseline_btc, baseline_eth],
        live=[live_btc, live_eth],
    )
    assert errs, "wrong-symbol/cross-artifact phantom added_key must FAIL"
    assert any(
        "no matching baseline symbol/tf" in e
        or "missing baseline parent skipped=true anchor on symbol/tf" in e
        or "no matching live symbol/tf" in e
        or "not present in live JSON for symbol/tf" in e
        for e in errs
    ), errs
    # 正對照：正確 ETH index → 雙錨 PASS
    good = copy.deepcopy(phantom)
    good["rows"][0]["index"] = f"ETHUSDT/12h/{feat}"
    errs_good = validate_allowlist_paths_against_baseline(
        good,
        baseline=[baseline_btc, baseline_eth],
        live=[live_btc, live_eth],
    )
    assert not errs_good, errs_good


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


# ---------------------------------------------------------------------------
# B4 Task 4.1 — 5 wash mutations（parametrize；in-memory → validator FAIL）
# ---------------------------------------------------------------------------
# 凍結 fingerprint = **literal 常數**（B4 supp+supp2 雙家授權後 re-stamp）
# 禁止從 live allowlist 自算 expected（same-count replace 會自動洗成新基準）。
# 來源：allowlist-supp(384)+supp2(+37 BTC P1-1, +4 added_key) → rows=421
#      → allowlist_rows_fingerprint(...) = 2e0991f4…b32888
FROZEN_ALLOWLIST_GIT_REF = "B4-supp2"
FROZEN_ALLOWLIST_ROWS_SHA256 = (
    "2e0991f45e2d155cd2a683528f338778bca6750f53feacb4f721666173b32888"
)
# 契約鎖：B4 收口後 rows 基數（防靜默 append 換綠）
FROZEN_ALLOWLIST_ROW_COUNT = 421

WASH_CASES = (
    "early_mask_impersonate_p1_1",
    "control_path_inject_diff",
    "delete_redflag_claim_p13_closed",
    "wrong_side_swap",
    "unauthorized_allowlist_expand",
)


def test_b4_allowlist_frozen_fingerprint() -> None:
    """B4 擅擴閘門基準：磁碟 allowlist fingerprint/row count == dba5716 literal。"""
    al = load_allowlist(ALLOWLIST_PATH)
    assert len(al.get("rows") or []) == FROZEN_ALLOWLIST_ROW_COUNT
    fp = allowlist_rows_fingerprint(al)
    assert fp == FROZEN_ALLOWLIST_ROWS_SHA256, (
        f"allowlist rows fingerprint drifted from {FROZEN_ALLOWLIST_GIT_REF} "
        f"literal (got={fp})"
    )
    # policy 宣告（禁 B4 期 append；亦禁 b4_rebaseline_new_only 擅改）
    policy = al.get("policy") or {}
    assert policy.get("forbid_append_after_b4_start") is True
    assert policy.get("b4_rebaseline_new_only") is not True
    assert validate_allowlist_not_expanded(
        al, frozen_fingerprint=FROZEN_ALLOWLIST_ROWS_SHA256
    ) == []


@pytest.mark.parametrize("wash_case", WASH_CASES, ids=list(WASH_CASES))
def test_wash_mutation_rejects(wash_case: str, allowlist: dict) -> None:
    """SPEC §G ≥5 wash：每支 in-memory 竄改 → validator FAIL（可重放）。

    ① early_mask_impersonate_p1_1 — 竄 early mask 冒充 P1-1（wrong-value）
    ② control_path_inject_diff — control 路徑塞 diff（bull unlisted）
    ③ delete_redflag_claim_p13_closed — 刪紅標 allowlist 後稱 P1-3 closed
    ④ wrong_side_swap — 同五鍵錯 class
    ⑤ unauthorized_allowlist_expand — 擅擴 allowlist 洗 unlisted
    """
    if wash_case == "early_mask_impersonate_p1_1":
        # 真 path 但 new 被竄成假 membership hash → wrong-value / unlisted
        real = next(
            r
            for r in allowlist["rows"]
            if r.get("class") == "P1-1"
            and str(r.get("path", "")).endswith("membership_sha256")
        )
        forged = {
            "path": real["path"],
            "index": real["index"],
            "old": real["old"],
            "new": "0" * 64,  # 冒充 early-mask 改寫後 hash
            "class": "P1-1",
        }
        result = validate_diffs([forged], allowlist)
        assert result.ok is False
        assert result.unexpected_count >= 1
        with pytest.raises(AttributionValidationError):
            validate_diffs_or_raise([forged], allowlist)

    elif wash_case == "control_path_inject_diff":
        # bull 為 control（P1-1 只動 high/low）；塞 control diff 必 unlisted
        control_diff = {
            "path": "regime_rule.mask_membership.regimes.bull.true_count",
            "index": "bull",
            "old": 10720,
            "new": 10719,
            "class": "P1-1",
        }
        result = validate_diffs([control_diff], allowlist)
        assert result.ok is False
        assert result.unexpected_count == 1
        with pytest.raises(AttributionValidationError):
            validate_diffs_or_raise([control_diff], allowlist)

    elif wash_case == "delete_redflag_claim_p13_closed":
        # 刪除全部 P1-3-obs 後仍呈 analysis_status 紅標 diff → FAIL
        stripped = copy.deepcopy(allowlist)
        stripped["rows"] = [
            r for r in (stripped.get("rows") or []) if r.get("class") != "P1-3-obs"
        ]
        assert not any(r.get("class") == "P1-3-obs" for r in stripped["rows"])
        red_flag = {
            "path": "analysis_status",
            "index": "root",
            "old": None,
            "new": "degraded_full_sample",
            "class": "P1-3-obs",
        }
        result = validate_diffs([red_flag], stripped)
        assert result.ok is False
        assert result.unexpected_count == 1
        with pytest.raises(AttributionValidationError):
            validate_diffs_or_raise([red_flag], stripped)

    elif wash_case == "wrong_side_swap":
        # 真 P1-1 五鍵 old/new，class 洗成 P1-2
        real = next(r for r in allowlist["rows"] if r.get("class") == "P1-1")
        swapped = {
            "path": real["path"],
            "index": real["index"],
            "old": real["old"],
            "new": real["new"],
            "class": "P1-2",
        }
        result = validate_diffs([swapped], allowlist)
        assert result.ok is False
        assert result.unexpected_count == 1
        with pytest.raises(AttributionValidationError):
            validate_diffs_or_raise([swapped], allowlist)

    elif wash_case == "unauthorized_allowlist_expand":
        # 擅擴 allowlist 塞 control 列，意圖洗 unlisted → freeze 閘門 FAIL
        expanded = copy.deepcopy(allowlist)
        wash_row = {
            "path": "regime_rule.mask_membership.regimes.bull.true_count",
            "index": "bull",
            "old": 10720,
            "new": 99999,
            "class": "P1-1",
        }
        expanded["rows"] = list(expanded.get("rows") or []) + [wash_row]
        freeze_errs = validate_allowlist_not_expanded(
            expanded, frozen_fingerprint=FROZEN_ALLOWLIST_ROWS_SHA256
        )
        assert freeze_errs, "expanded allowlist must fail freeze gate"
        with pytest.raises(AttributionValidationError):
            validate_allowlist_not_expanded_or_raise(
                expanded, frozen_fingerprint=FROZEN_ALLOWLIST_ROWS_SHA256
            )
        # 即便 diff 對上擴充列，B4 收口仍 FAIL（freeze + 不接受擅擴）
        b4 = validate_b4_attribution(
            [wash_row],
            expanded,
            frozen_fingerprint=FROZEN_ALLOWLIST_ROWS_SHA256,
        )
        assert b4.ok is False
        # freeze FAIL 不得只印 UNEXPECTED=0 冒充通過
        assert b4.machine_line().startswith("FAIL"), b4.machine_line()
        assert "format_errors=" in b4.machine_line()
        # 對照：未擴充時同一 control diff 亦 unlisted FAIL
        bare = validate_diffs([wash_row], allowlist)
        assert bare.ok is False

    else:  # pragma: no cover
        raise AssertionError(f"unknown wash_case {wash_case!r}")


def test_b4_freeze_fail_machine_line_not_unexpected_zero() -> None:
    """B4-CODEX-4：錯 freeze fingerprint → machine line 含 FAIL，非裸 UNEXPECTED=0。"""
    al = load_allowlist(ALLOWLIST_PATH)
    bad = validate_b4_attribution(
        [],
        al,
        frozen_fingerprint="0" * 64,
    )
    assert bad.ok is False
    assert bad.format_errors
    line = bad.machine_line()
    assert line.startswith("FAIL"), line
    assert line != "UNEXPECTED=0"
    assert "format_errors=" in line


def test_b4_unenumerated_field_mutation_unexpected() -> None:
    """B4-CODEX-4：未枚舉 path 的 mutation 必進對帳 → UNEXPECTED≥1。"""
    al = load_allowlist(ALLOWLIST_PATH)
    # 用 control 側 bull.true_rate（非 P1-1 修改路徑；supp2 已列 high/low true_rate）
    unlisted = {
        "path": "regime_rule.mask_membership.regimes.bull.true_rate",
        "index": "bull",
        "old": 0.5,
        "new": 0.999999999999,
        "class": "P1-1",
    }
    allow_keys = {
        _row_key(r) for r in (al.get("rows") or []) if isinstance(r, dict)
    }
    assert _row_key(unlisted) not in allow_keys
    result = validate_diffs([unlisted], al)
    assert result.ok is False
    assert result.unexpected_count >= 1
    assert result.machine_line() == f"UNEXPECTED={result.unexpected_count}"
    with pytest.raises(AttributionValidationError):
        validate_diffs_or_raise([unlisted], al)
