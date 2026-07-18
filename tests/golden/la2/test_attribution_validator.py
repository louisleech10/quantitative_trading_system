"""LA-2 attribution_validator 測（TODO Task 0.2）。

1. 空 diff PASS
2. 未列 diff FAIL
3. 格式錯 row（缺 path/index/old/new/class）FAIL
4. wrong-value / wrong-class FAIL
5. eval_scope_field_map 28 path
6. ≥5 wash mutations 各自 FAIL
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from tests.golden.la2.attribution_validator import (
    CANONICAL_EVAL_SCOPE_PATHS,
    CLASS_ENUM,
    EXPECTED_EVAL_SCOPE_PATH_COUNT,
    WASH_CASE_NAMES,
    AttributionValidationError,
    apply_wash_mutation,
    allowlist_rows_fingerprint,
    baseline_has_path,
    load_allowlist,
    validate_allowlist_not_expanded,
    validate_allowlist_schema,
    validate_diffs,
    validate_diffs_or_raise,
    validate_eval_scope_field_map,
)

LA2_DIR = Path(__file__).resolve().parent
ALLOWLIST_PATH = LA2_DIR / "attribution_allowlist.json"


def _populated_allowlist() -> dict[str, Any]:
    """內嵌 allowlist（含一筆 predeclare 列），供 wrong-value / wrong-class 負例。"""
    base = load_allowlist(ALLOWLIST_PATH)
    return {
        "schema_version": base["schema_version"],
        "class_enum": sorted(CLASS_ENUM),
        "eval_scope_field_map": base["eval_scope_field_map"],
        "rows": [
            {
                "path": "pattern.threshold_value_sha256",
                "index": "BTCUSDT/1h",
                "old": "oldhash",
                "new": "newhash",
                "class": "P2-3b-pattern-trainmask",
            }
        ],
    }


def _assert_b1_raise_only_rows(rows: list) -> None:
    """B1 Task 1.2：恰 4 個 P2-1-disable raise-only（無 old/new 數值）。"""
    p21 = [r for r in rows if r.get("class") == "P2-1-disable"]
    assert len(p21) == 4, f"expected 4 P2-1-disable rows, got {len(p21)}"
    expected_paths = {
        "momentum/FeatureEngineering/labels/label_generator.py::generate_returns_by_type",
        "momentum/Analysis/ic_config_schema.py::return_type Literal",
        "momentum/Analysis/ic_filter_orchestrator.py:2380",
        "momentum/Analysis/ic_engine.py::_compute_returns",
    }
    assert {r["path"] for r in p21} == expected_paths
    for r in p21:
        assert r.get("behavior") == "raises"
        assert r.get("reason_code") == "LOOKAHEAD_LABEL_UNSUPPORTED"
        assert r.get("old") is None
        assert r.get("new") is None
        assert r.get("index") == "winsorized"


@pytest.fixture(scope="module")
def allowlist() -> dict:
    data = load_allowlist(ALLOWLIST_PATH)
    errs = validate_allowlist_schema(data)
    assert not errs, errs
    assert isinstance(data.get("rows"), list)
    # B0 空 rows；B1 append 4× P2-1-disable raise-only（TODO Task 1.2）
    _assert_b1_raise_only_rows(data["rows"])
    assert set(data.get("class_enum") or []) == CLASS_ENUM
    return data


def test_empty_diff_passes(allowlist: dict) -> None:
    """空 diff → PASS（allowlist 可有 B1 raise-only rows；無 unlisted）。"""
    result = validate_diffs([], allowlist)
    assert result.ok is True
    assert result.unexpected_count == 0
    assert result.machine_line() == "UNEXPECTED=0"


def test_unlisted_diff_fails(allowlist: dict) -> None:
    """未列於 allowlist 的 diff → FAIL（unlisted=unexpected）。"""
    diffs = [
        {
            "path": "pattern.threshold_value_sha256",
            "index": "BTCUSDT/1h",
            "old": "a",
            "new": "b",
            "class": "P2-3b-pattern-trainmask",
        }
    ]
    result = validate_diffs(diffs, allowlist)
    assert result.ok is False
    assert result.unexpected_count == 1
    assert result.machine_line() == "UNEXPECTED=1"
    with pytest.raises(AttributionValidationError):
        validate_diffs_or_raise(diffs, allowlist)


def test_malformed_row_missing_keys_fails(allowlist: dict) -> None:
    """格式錯 row：缺 path / index / old / new / class → FAIL。"""
    base = {
        "path": "factor.gram_schmidt.value_sha256",
        "index": 0,
        "old": 1,
        "new": 2,
        "class": "P2-3a-factor-loud",
    }
    for missing in ("path", "index", "old", "new", "class"):
        row = {k: v for k, v in base.items() if k != missing}
        result = validate_diffs([row], allowlist)
        assert result.ok is False, f"expected fail when missing {missing}"
        assert any(missing in e for e in result.format_errors), result.format_errors


def test_wrong_value_fails() -> None:
    """同 path+index、錯 old/new → 不可洗過。"""
    allowlist = _populated_allowlist()
    assert not validate_allowlist_schema(allowlist)

    ok_diff = [
        {
            "path": "pattern.threshold_value_sha256",
            "index": "BTCUSDT/1h",
            "old": "oldhash",
            "new": "newhash",
            "class": "P2-3b-pattern-trainmask",
        }
    ]
    assert validate_diffs(ok_diff, allowlist).ok is True

    bad_value = [
        {
            "path": "pattern.threshold_value_sha256",
            "index": "BTCUSDT/1h",
            "old": "oldhash",
            "new": "forged",
            "class": "P2-3b-pattern-trainmask",
        }
    ]
    result = validate_diffs(bad_value, allowlist)
    assert result.ok is False
    assert result.unexpected_count == 1


def test_wrong_class_fails() -> None:
    """同 path+index+old/new、錯 class → 不可洗過。"""
    allowlist = _populated_allowlist()
    bad_class = [
        {
            "path": "pattern.threshold_value_sha256",
            "index": "BTCUSDT/1h",
            "old": "oldhash",
            "new": "newhash",
            "class": "P2-3a-factor-loud",
        }
    ]
    result = validate_diffs(bad_class, allowlist)
    assert result.ok is False
    assert result.unexpected_count == 1


def test_allowlist_json_loads() -> None:
    """sanity：attribution_allowlist.json schema + 28 path map + B1 raise-only rows。"""
    payload = json.loads(ALLOWLIST_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload.get("rows"), list)
    _assert_b1_raise_only_rows(payload["rows"])
    assert "schema_version" in payload
    assert set(payload["class_enum"]) == CLASS_ENUM
    assert len(payload["class_enum"]) == 8
    errs = validate_allowlist_schema(payload)
    assert not errs, errs
    fmap_errs = validate_eval_scope_field_map(payload)
    assert not fmap_errs, fmap_errs
    assert len(payload["eval_scope_field_map"]) == EXPECTED_EVAL_SCOPE_PATH_COUNT
    assert set(payload["eval_scope_field_map"].keys()) == CANONICAL_EVAL_SCOPE_PATHS
    # cal/PR/Brier/ECE = cv_oof（TODO U1）
    for path in (
        "/model_performance/calibration_curve",
        "/model_performance/brier_score",
        "/model_performance/ece",
        "/model_performance/pr_curve",
        "/model_performance/pr_auc",
    ):
        assert payload["eval_scope_field_map"][path]["eval_scope"] == "cv_oof"


def test_eval_scope_path_set_exact_rejects_phantom() -> None:
    """B0-F3：path 換 phantom / 增刪 → schema FAIL（非只驗 count）。"""
    payload = load_allowlist(ALLOWLIST_PATH)
    assert not validate_eval_scope_field_map(payload)

    # 同 count：oot_auc → phantom
    mutated = copy.deepcopy(payload)
    fmap = mutated["eval_scope_field_map"]
    body = fmap.pop("/model_performance/oot_auc")
    fmap["/model_performance/phantom"] = body
    assert len(fmap) == EXPECTED_EVAL_SCOPE_PATH_COUNT
    errs = validate_eval_scope_field_map(mutated)
    assert errs, "phantom path swap must FAIL exact-set check"
    assert any("canonical" in e or "phantom" in e for e in errs)

    # 增 path
    mutated2 = copy.deepcopy(payload)
    mutated2["eval_scope_field_map"]["/model_performance/extra_path"] = {
        "eval_scope": "oot",
        "consumer": "ok",
    }
    errs2 = validate_eval_scope_field_map(mutated2)
    assert errs2
    assert any("extra" in e or "canonical" in e for e in errs2)

    # 刪 path
    mutated3 = copy.deepcopy(payload)
    del mutated3["eval_scope_field_map"]["/model_performance/oot_auc"]
    errs3 = validate_eval_scope_field_map(mutated3)
    assert errs3
    assert any("missing" in e or "canonical" in e for e in errs3)


def test_baseline_has_path_helper() -> None:
    """接線 baseline_has_path（composer MINOR-2；禁死碼）。"""
    sample = {"model": {"service_matrix": {"recommend_k": {"recommended_k": 5}}}}
    assert baseline_has_path(sample, "model.service_matrix.recommend_k") is True
    assert baseline_has_path(sample, "model.service_matrix.missing") is False
    assert baseline_has_path(sample, "") is False


def test_raise_only_class_rejects_numeric_old_new() -> None:
    """P2-1-disable raise-only：不得帶數值 old/new 洗綠。"""
    base = load_allowlist(ALLOWLIST_PATH)
    al = {
        "schema_version": base["schema_version"],
        "class_enum": sorted(CLASS_ENUM),
        "eval_scope_field_map": base["eval_scope_field_map"],
        "rows": [
            {
                "path": "momentum/FeatureEngineering/labels/label_generator.py::generate_returns_by_type",
                "index": "winsorized",
                "old": 0.01,
                "new": 0.02,
                "class": "P2-1-disable",
                "behavior": "raises",
            }
        ],
    }
    errs = validate_allowlist_schema(al)
    assert errs
    assert any("numeric old/new" in e for e in errs)


# ---------------------------------------------------------------------------
# ≥5 wash mutations（parametrize；in-memory → validator FAIL）
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("wash_case", WASH_CASE_NAMES, ids=list(WASH_CASE_NAMES))
def test_wash_mutation_rejects(wash_case: str, allowlist: dict) -> None:
    """SPEC §G ≥5 wash：每支 in-memory 竄改 → validator FAIL（可重放）。

    ① control_path_inject_diff — 竄改 control 塞 diff
    ② track2_fullsample_claim_oot — 軌2 全樣本值標成已修 OOT
    ③ delete_loud_claim_tagged — 刪 loud 欄稱已標
    ④ wrong_class_swap — wrong-class swap
    ⑤ unauthorized_allowlist_expand — 擅擴 allowlist 洗 unlisted
    """
    diffs, al = apply_wash_mutation(wash_case, allowlist)
    result = validate_diffs(diffs, al)
    assert result.ok is False, f"wash {wash_case} must FAIL"
    assert result.unexpected_count >= 1 or result.format_errors
    with pytest.raises(AttributionValidationError):
        validate_diffs_or_raise(diffs, al)

    if wash_case == "delete_loud_claim_tagged":
        # B0-F4：seed→strip 後仍呈 loud diff → missing attribution
        # （非「空表 unlisted」trivial：seed 曾存在、strip 後 class 不在 rows）
        assert result.unexpected_count >= 1
        assert any(
            d.get("class") == "P2-3a-factor-loud" for d in result.unexpected
        ), "delete_loud must surface missing P2-3a-factor-loud attribution"
        assert not any(
            r.get("class") == "P2-3a-factor-loud" for r in (al.get("rows") or [])
        ), "stripped allowlist must not retain loud rows"
        # 對照：若未 strip（seed 仍在）同一 diff 應 PASS
        seed_al = copy.deepcopy(allowlist)
        seed_al["rows"] = list(seed_al.get("rows") or []) + [
            {
                "path": "factor.oos_guarantees",
                "index": "root",
                "old": None,
                "new": False,
                "class": "P2-3a-factor-loud",
            }
        ]
        assert validate_diffs(diffs, seed_al).ok is True

    if wash_case == "unauthorized_allowlist_expand":
        # fingerprint 擅擴亦可獨立打紅
        expanded = copy.deepcopy(allowlist)
        expanded["rows"] = list(expanded.get("rows") or []) + [
            {
                "path": "phantom.unauthorized",
                "index": "x",
                "old": 1,
                "new": 2,
                "class": "P2-2-scope-tag",
            }
        ]
        frozen = allowlist_rows_fingerprint(allowlist)
        errs = validate_allowlist_not_expanded(
            expanded, frozen_fingerprint=frozen
        )
        assert errs, "expanded allowlist must fail fingerprint gate"


def test_la2_skeleton_nodeid_contract() -> None:
    """B0-F5：EXPECTED_NODEIDS 恰 12；module 內 test_* == 契約（非人工 --collect-only）。"""
    import tests.momentum.test_la2_lookahead as skel

    assert skel.EXPECTED_NODEID_COUNT == 12
    assert len(skel.EXPECTED_NODEIDS) == 12
    assert len(set(skel.EXPECTED_NODEIDS)) == 12
    declared = sorted(
        n
        for n in dir(skel)
        if n.startswith("test_") and callable(getattr(skel, n, None))
    )
    assert declared == sorted(skel.EXPECTED_NODEIDS), (
        f"skeleton test_* drift: got={declared} expected={list(skel.EXPECTED_NODEIDS)}"
    )
    for name in skel.EXPECTED_NODEIDS:
        fn = getattr(skel, name)
        assert callable(fn)
