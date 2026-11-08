"""ICPERF SPEC v5.84 Task 0.6 (f)：comparator 結構化單元 ID 與 L4 差集三條件之契約測試。

被測（`scripts/icperf_freeze_baseline.py`，施工前不存在 ⇒ 本檔應為紅）：
- `compare_golden_units(frozen, current) -> {"units": [單元 ID...], "hard_failures": [str...]}`：與 `compare_golden` 同分支、
  同 volatile 排除語意；單元 ID 為 list（JSON 陣列），依 SPEC 單元 ID 段之各分支；不可宣告之差異只入 hard_failures。
- `unit_key(unit) -> str`：單元 ID 之正準字串（`json.dumps(unit, ensure_ascii=False, separators=(",", ":"))`），作對照表鍵。
- `check_l4_diff(actual, declared, oracle_by_unit, undeclared_reasons, hard_failures) -> List[str]`：L4 三條件，空＝合格。
人讀訊息（`compare_golden`／`compare_capture`）之既有語意不在本檔改動，由 `test_icperf_gate.py` 既有測試守。
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest

REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / "scripts" / "icperf_freeze_baseline.py"
REASON_CODES = ("trigger_not_hit", "input_below_old_boundary", "path_not_exercised")


def _load(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def fb() -> Any:
    return _load("icperf_freeze_baseline_units", SCRIPT)


def _units(fb: Any, frozen: Dict[str, Any], current: Dict[str, Any]) -> Dict[str, Any]:
    out = fb.compare_golden_units(frozen, current)
    assert set(out) == {"units", "hard_failures"}
    return out


def _golden(items: Dict[str, Any], volatile: List[str] = ()) -> Dict[str, Any]:
    return {"items": items, "volatile": list(volatile)}


def _write(p: Path, text: str) -> Path:
    p.write_text(text, encoding="utf-8")
    return p


# ── 單元 ID 各分支 ──────────────────────────────────────────────────────────────────────────────────────

def test_boundary_01_response_leaf_unit(fb: Any) -> None:
    a = _golden({"ic_report": {"response": fb.flatten_fields({"summary": {"ic": 0.1}}), "files": {}}})
    b = _golden({"ic_report": {"response": fb.flatten_fields({"summary": {"ic": 0.2}}), "files": {}}})
    out = _units(fb, a, b)
    assert out["units"] == [["ic_report", "response", "/summary/ic"]]
    assert out["hard_failures"] == []


def test_boundary_02_json_file_field_unit_and_sha_not_separate(fb: Any, tmp_path: Path) -> None:
    fa = _write(tmp_path / "a.json", json.dumps({"x": 1, "y": 2}))
    fc = _write(tmp_path / "c.json", json.dumps({"x": 1, "y": 3}))
    a = _golden({"ic_report": {"response": {}, "files": {"r.json": fb.describe_file(fa)}}})
    b = _golden({"ic_report": {"response": {}, "files": {"r.json": fb.describe_file(fc)}}})
    out = _units(fb, a, b)
    assert out["units"] == [["ic_report", "file", "r.json", "field", "/y"]], "欄位差只以欄位 ID 承載，整檔 sha256 不另成單元"
    assert out["hard_failures"] == []


def test_boundary_03_json_fields_equal_sha_differs_is_hard_failure(fb: Any, tmp_path: Path) -> None:
    fa = _write(tmp_path / "a.json", json.dumps({"x": 1}))
    fc = _write(tmp_path / "c.json", json.dumps({"x": 1}, indent=2))
    a = _golden({"ic_report": {"response": {}, "files": {"r.json": fb.describe_file(fa)}}})
    b = _golden({"ic_report": {"response": {}, "files": {"r.json": fb.describe_file(fc)}}})
    out = _units(fb, a, b)
    assert out["units"] == []
    assert len(out["hard_failures"]) == 1 and "r.json" in out["hard_failures"][0]


def test_boundary_04_file_only_one_side_unit(fb: Any, tmp_path: Path) -> None:
    fa = _write(tmp_path / "a.json", json.dumps({"x": 1}))
    a = _golden({"ic_report": {"response": {}, "files": {"r.json": fb.describe_file(fa)}}})
    b = _golden({"ic_report": {"response": {}, "files": {}}})
    assert _units(fb, a, b)["units"] == [["ic_report", "file", "r.json"]]


def test_boundary_05_opaque_and_asymmetric_parse_sha_unit(fb: Any, tmp_path: Path) -> None:
    ba = _write(tmp_path / "a.bin", "alpha")
    bc = _write(tmp_path / "c.bin", "beta")
    a = _golden({"ic_report": {"response": {}, "files": {"x.bin": fb.describe_file(ba)}}})
    b = _golden({"ic_report": {"response": {}, "files": {"x.bin": fb.describe_file(bc)}}})
    assert _units(fb, a, b)["units"] == [["ic_report", "file", "x.bin", "sha256"]]
    ea = _write(tmp_path / "e.json", "")
    ec = _write(tmp_path / "f.json", json.dumps({"x": 1}))
    a2 = _golden({"ic_report": {"response": {}, "files": {"r.json": fb.describe_file(ea)}}})
    b2 = _golden({"ic_report": {"response": {}, "files": {"r.json": fb.describe_file(ec)}}})
    out = _units(fb, a2, b2)
    assert out["units"] == [["ic_report", "file", "r.json", "sha256"]], "可解析性前後不一致歸整檔 sha256 單元"
    assert out["hard_failures"] == []


def test_boundary_06_hdf5_object_unit_and_bytes_only_hard_failure(fb: Any) -> None:
    obj_a = {"/d": {"kind": "dataset", "dtype": "f8", "shape": [3], "sha256": "s1", "attrs": {"u": "1"}}}
    obj_b = {"/d": {"kind": "dataset", "dtype": "f8", "shape": [3], "sha256": "s2", "attrs": {"u": "1"}}}
    a = _golden({"ic_report": {"response": {}, "files": {"t.h5": {"sha256": "h1", "hdf5": obj_a, "fields": None}}}})
    b = _golden({"ic_report": {"response": {}, "files": {"t.h5": {"sha256": "h2", "hdf5": obj_b, "fields": None}}}})
    out = _units(fb, a, b)
    assert out["units"] == [["ic_report", "file", "t.h5", "hdf5", "/d"]]
    assert out["hard_failures"] == [], "有物件差時整檔 sha256 差不另成硬失敗"
    attr_b = {"/d": dict(obj_a["/d"], attrs={"u": "2"})}
    b_attr = _golden({"ic_report": {"response": {}, "files": {"t.h5": {"sha256": "h2", "hdf5": attr_b, "fields": None}}}})
    assert _units(fb, a, b_attr)["units"] == [["ic_report", "file", "t.h5", "hdf5", "/d"]], "未排除屬性差歸物件單元"
    same_b = _golden({"ic_report": {"response": {}, "files": {"t.h5": {"sha256": "h2", "hdf5": obj_a, "fields": None}}}})
    out2 = _units(fb, a, same_b)
    assert out2["units"] == [] and len(out2["hard_failures"]) == 1, "物件全等而整檔 sha256 異 ⇒ 硬失敗"


def test_boundary_07_features_pit_selected_stage_removed_item_units(fb: Any) -> None:
    fa = {"f1": {"ic": "a", "hac_t": "b"}, "f2": {"ic": "c"}}
    fc = {"f1": {"ic": "a", "hac_t": "z"}, "f3": {"ic": "c"}}
    a = _golden({"stage5_subset": {"features": fa, "pit_labels": {"f1": {"q": 5}}, "selected": ["f1"],
                                   "stage_cols": 2, "request": {"source_sha256": "S"}},
                 "ic_report": {"response": {}, "files": {}, "removed": ["old.h5"]}})
    b = _golden({"stage5_subset": {"features": fc, "pit_labels": {"f1": {"q": 3}}, "selected": ["f3"],
                                   "stage_cols": 3, "request": {"source_sha256": "S"}},
                 "ic_report": {"response": {}, "files": {}, "removed": []}})
    units = _units(fb, a, b)["units"]
    expected = [["ic_report", "removed"], ["stage5_subset", "features", "f1", "hac_t"],
                ["stage5_subset", "features", "f2"], ["stage5_subset", "features", "f3"],
                ["stage5_subset", "pit_labels", "f1"], ["stage5_subset", "selected"], ["stage5_subset", "stage_cols"]]
    assert sorted(units) == sorted(expected)
    only_a = _golden({"ic_report": {"response": {}, "files": {}}})
    assert _units(fb, only_a, _golden({}))["units"] == [["ic_report"]]


def test_boundary_08_non_declarable_hard_failures(fb: Any, tmp_path: Path) -> None:
    a = _golden({"stage5_subset": {"request": {"source_sha256": "S1"}}})
    b = _golden({"stage5_subset": {"request": {"source_sha256": "S2"}}})
    out = _units(fb, a, b)
    assert out["units"] == [] and len(out["hard_failures"]) == 1, "交接 h5 身分不等不可宣告"
    bad = _write(tmp_path / "bad.json", "{not json")
    good = _write(tmp_path / "good.json", json.dumps({"ts": 1}))
    va = _golden({"ic_report": {"response": {}, "files": {"v.json": fb.describe_file(good)}}},
                 volatile=["ic_report:file:v.json#/ts"])
    vb = _golden({"ic_report": {"response": {}, "files": {"v.json": fb.describe_file(bad)}}})
    out2 = _units(fb, va, vb)
    assert out2["units"] == [] and len(out2["hard_failures"]) == 1, "列 volatile 之檔不可解析不可宣告"


def test_boundary_09_volatile_json_excluded_no_unit_no_failure(fb: Any, tmp_path: Path) -> None:
    fa = _write(tmp_path / "a.json", json.dumps({"ts": 1, "v": 5}))
    fc = _write(tmp_path / "c.json", json.dumps({"ts": 2, "v": 5}))
    a = _golden({"ic_report": {"response": {}, "files": {"v.json": fb.describe_file(fa)}}},
                volatile=["ic_report:file:v.json#/ts"])
    b = _golden({"ic_report": {"response": {}, "files": {"v.json": fb.describe_file(fc)}}})
    assert _units(fb, a, b) == {"units": [], "hard_failures": []}, "volatile 檔沿用現行語意，不比整檔 sha256"


def _full(fb: Any, overrides: Dict[str, Any]) -> Dict[str, Any]:
    """全部 G_ITEMS 之最小項（輸出項＝空回應與空檔集合；stage5_subset＝同一交接 h5 身分），再以 overrides 覆寫。"""
    items: Dict[str, Any] = {}
    for item in fb.G_ITEMS:
        items[item] = ({"response": {}, "files": {}} if item in fb.OUTPUT_ITEMS
                       else {"request": {"source_sha256": "S"}})
    items.update(overrides)
    return _golden(items)


def test_boundary_10_units_consistent_with_human_messages(fb: Any) -> None:
    """有單元或硬失敗 ⇔ compare_golden 有問題（兩者同分支產生，不得一邊有一邊無）。"""
    a = _full(fb, {"ic_report": {"response": fb.flatten_fields({"k": 1}), "files": {}}})
    same = _full(fb, {"ic_report": {"response": fb.flatten_fields({"k": 1}), "files": {}}})
    diff = _full(fb, {"ic_report": {"response": fb.flatten_fields({"k": 2}), "files": {}}})
    assert fb.compare_golden(a, same) == [], "前提：全部 G_ITEMS 齊備時同內容之人讀比對為空"
    assert _units(fb, a, same) == {"units": [], "hard_failures": []}
    assert fb.compare_golden(a, diff)
    assert _units(fb, a, diff) == {"units": [["ic_report", "response", "/k"]], "hard_failures": []}


def test_boundary_17_source_identity_missing_both_sides_hard_failure(fb: Any) -> None:
    a = _golden({"stage5_subset": {"request": {}}})
    b = _golden({"stage5_subset": {"request": {}}})
    out = _units(fb, a, b)
    assert out["units"] == [] and len(out["hard_failures"]) == 1, "兩側皆缺交接 h5 身分 ⇒ 硬失敗（不得放行）"


def test_boundary_18_hdf5_volatile_attrs_excluded(fb: Any) -> None:
    base = {"kind": "dataset", "dtype": "f8", "shape": [3], "sha256": "s1"}
    a = _golden({"ic_report": {"response": {}, "files": {"t.h5": {
        "sha256": "h1", "hdf5": {"/d": dict(base, attrs={"created": "t1", "u": "1"})}, "fields": None}}}},
        volatile=["ic_report:file:t.h5@/d#attr:created"])
    b_vol = _golden({"ic_report": {"response": {}, "files": {"t.h5": {
        "sha256": "h2", "hdf5": {"/d": dict(base, attrs={"created": "t2", "u": "1"})}, "fields": None}}}})
    assert _units(fb, a, b_vol) == {"units": [], "hard_failures": []}, "只改已列 volatile 屬性 ⇒ 無單元、無硬失敗"
    b_attr = _golden({"ic_report": {"response": {}, "files": {"t.h5": {
        "sha256": "h2", "hdf5": {"/d": dict(base, attrs={"created": "t2", "u": "2"})}, "fields": None}}}})
    assert _units(fb, a, b_attr)["units"] == [["ic_report", "file", "t.h5", "hdf5", "/d"]], "未列屬性仍歸物件單元"


def test_boundary_19_l4_declared_unit_with_invalid_shape_rejected(fb: Any) -> None:
    """宣告須為最細層合法 ID；格式不合法者即使集合包含與原因碼皆齊仍紅（與「集合不包含」區分）。"""
    bad = ["deep_analysis", "response"]
    problems = _check(fb, [], [bad], {}, {fb.unit_key(bad): "trigger_not_hit"})
    assert problems and any("格式" in p for p in problems)


# ── L4 差集三條件 ───────────────────────────────────────────────────────────────────────────────────────

def _check(fb: Any, actual, declared, oracle, reasons, hard=(), universe=None) -> List[str]:
    """`universe`＝新舊基準之全部最細層單元（`golden_unit_universe`）；未給時以 actual∪declared 代之（不涉父層判定之用例）。"""
    uni = list(universe) if universe is not None else list(actual) + list(declared)
    return fb.check_l4_diff(actual, declared, oracle, reasons, list(hard), universe=uni)


_H5_BASE = {"kind": "dataset", "dtype": "f8", "shape": [3], "sha256": "s1", "attrs": {}}


@pytest.mark.parametrize("change", ["added", "removed", "kind", "dtype", "shape"])
def test_boundary_20_hdf5_object_branches(fb: Any, change: str) -> None:
    objs_a = {"/d": dict(_H5_BASE)}
    if change == "added":
        objs_b = {"/d": dict(_H5_BASE), "/e": dict(_H5_BASE)}
        unit_obj = "/e"
    elif change == "removed":
        objs_a, objs_b, unit_obj = {"/d": dict(_H5_BASE), "/e": dict(_H5_BASE)}, {"/d": dict(_H5_BASE)}, "/e"
    else:
        objs_b = {"/d": dict(_H5_BASE, **{change: {"kind": "group", "dtype": "f4", "shape": [4]}[change]})}
        unit_obj = "/d"
    a = _golden({"ic_report": {"response": {}, "files": {"t.h5": {"sha256": "h1", "hdf5": objs_a, "fields": None}}}})
    b = _golden({"ic_report": {"response": {}, "files": {"t.h5": {"sha256": "h2", "hdf5": objs_b, "fields": None}}}})
    assert _units(fb, a, b) == {"units": [["ic_report", "file", "t.h5", "hdf5", unit_obj]], "hard_failures": []}


@pytest.mark.parametrize("change", ["added", "removed"])
def test_boundary_21_json_field_added_or_removed(fb: Any, tmp_path: Path, change: str) -> None:
    small = _write(tmp_path / "s.json", json.dumps({"x": 1}))
    big = _write(tmp_path / "b.json", json.dumps({"x": 1, "z": 2}))
    fa, fc = (small, big) if change == "added" else (big, small)
    a = _golden({"ic_report": {"response": {}, "files": {"r.json": fb.describe_file(fa)}}})
    b = _golden({"ic_report": {"response": {}, "files": {"r.json": fb.describe_file(fc)}}})
    assert _units(fb, a, b) == {"units": [["ic_report", "file", "r.json", "field", "/z"]], "hard_failures": []}


@pytest.mark.parametrize("side", ["frozen", "current"])
def test_boundary_22_source_identity_missing_one_side_hard_failure(fb: Any, side: str) -> None:
    has = {"stage5_subset": {"request": {"source_sha256": "S"}}}
    lacks = {"stage5_subset": {"request": {}}}
    a, b = (_golden(lacks), _golden(has)) if side == "frozen" else (_golden(has), _golden(lacks))
    out = _units(fb, a, b)
    assert out["units"] == [] and len(out["hard_failures"]) == 1, "一側缺交接 h5 身分 ⇒ 硬失敗"


def test_boundary_23_parent_id_rejected_even_when_sets_match(fb: Any) -> None:
    """actual＝declared＝父層 ID 且 oracle 齊備：父層不在新舊基準之最細層單元全集內 ⇒ 拒收（不只看 ID 長度）。"""
    parent = ["deep_analysis", "response", "/trend"]
    leaves = [["deep_analysis", "response", "/trend/a"], ["deep_analysis", "response", "/trend/b"]]
    k = fb.unit_key
    problems = _check(fb, [parent], [parent], {k(parent): "t::p"}, {}, universe=leaves)
    assert problems and any("最細層" in p or "格式" in p for p in problems)


def test_boundary_24_golden_unit_universe_lists_finest_units(fb: Any, tmp_path: Path) -> None:
    f = _write(tmp_path / "a.json", json.dumps({"x": 1, "y": {"z": 2}}))
    g = _golden({"ic_report": {"response": fb.flatten_fields({"k": 1, "m": {"n": 2}}),
                               "files": {"r.json": fb.describe_file(f)}}})
    uni = {fb.unit_key(u) for u in fb.golden_unit_universe(g, g)}
    expected = {fb.unit_key(u) for u in [["ic_report", "response", "/k"], ["ic_report", "response", "/m/n"],
                                         ["ic_report", "file", "r.json", "field", "/x"],
                                         ["ic_report", "file", "r.json", "field", "/y/z"]]}
    assert expected <= uni and fb.unit_key(["ic_report", "response", "/m"]) not in uni


def test_boundary_11_l4_pass_when_three_conditions_hold(fb: Any) -> None:
    u1 = ["deep_analysis", "response", "/marginal_ic/candidates#values"]
    u2 = ["deep_analysis", "response", "/marginal_ic/candidates#nan_mask"]
    k = fb.unit_key
    assert k(u1) == json.dumps(u1, ensure_ascii=False, separators=(",", ":"))
    problems = _check(fb, [u1], [u1, u2], {k(u1): "tests/x.py::test_a"}, {k(u2): "trigger_not_hit"})
    assert problems == []


def test_boundary_12_l4_actual_not_subset_of_declared(fb: Any) -> None:
    u1 = ["deep_analysis", "response", "/a"]
    u2 = ["deep_analysis", "response", "/trend/b"]
    k = fb.unit_key
    problems = _check(fb, [u1, u2], [u1], {k(u1): "t::a", k(u2): "t::b"}, {})
    assert problems and any("/trend/b" in p for p in problems)


def test_boundary_13_l4_parent_declaration_does_not_cover_leaf(fb: Any) -> None:
    leaf = ["deep_analysis", "response", "/trend/b"]
    parent = ["deep_analysis", "response", "/trend"]
    k = fb.unit_key
    assert _check(fb, [leaf], [parent], {k(leaf): "t::b"}, {k(parent): "trigger_not_hit"}), "宣告父層不涵蓋葉"


def test_boundary_14_l4_actual_unit_without_oracle(fb: Any) -> None:
    u1 = ["deep_analysis", "response", "/a"]
    assert _check(fb, [u1], [u1], {}, {}), "實際變動單元須有 oracle 測試 id"


def test_boundary_15_l4_declared_unchanged_needs_closed_reason(fb: Any) -> None:
    u1 = ["deep_analysis", "response", "/a"]
    u2 = ["deep_analysis", "response", "/b"]
    k = fb.unit_key
    assert _check(fb, [u1], [u1, u2], {k(u1): "t::a"}, {}), "宣告未變須附原因碼"
    assert _check(fb, [u1], [u1, u2], {k(u1): "t::a"}, {k(u2): "因為沒觸發"}), "原因碼須屬封閉集合"
    for code in REASON_CODES:
        assert _check(fb, [u1], [u1, u2], {k(u1): "t::a"}, {k(u2): code}) == []


def test_boundary_16_l4_hard_failures_block(fb: Any) -> None:
    u1 = ["deep_analysis", "response", "/a"]
    k = fb.unit_key
    assert _check(fb, [u1], [u1], {k(u1): "t::a"}, {}, hard=["r.json：序列化缺陷"])


def test_mutation_unit_key_collapse_flips_l4(fb: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """改壞 unit_key（所有單元同鍵）⇒ 原本缺 oracle 之第二單元被誤判已覆蓋，結果翻轉。"""
    u1 = ["deep_analysis", "response", "/a"]
    u2 = ["deep_analysis", "response", "/b"]
    good_key = fb.unit_key
    oracle = {good_key(u1): "t::a"}
    assert _check(fb, [u1, u2], [u1, u2], oracle, {}), "正確實作：u2 缺 oracle 須紅"
    monkeypatch.setattr(fb, "unit_key", lambda unit: "same")
    assert _check(fb, [u1, u2], [u1, u2], {"same": "t::a"}, {}) == [], "改壞後誤綠（證明測試能鑑別）"
