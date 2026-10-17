"""FF-NAME Task 2.6 — 值不變驗收（docs/FFNAME_SPEC.md §G、Task 2.6）。🔴 真實 kline reference run（重型；單組串行）。

§G 通過條件（v13）：①映射後欄集合相等（例外只准⑤之 L2 合併差集與⑥之新增 lag 欄，兩者逐筆列入收據）②每欄四雜湊全等 ③改名數 > 0
④新 run 全部欄名 parse 成功且 `format(parse(n)) == n` ⑤L2 配對簽名集合經映射後相等，差集只准為「同 canonical 身分之
舊兩分支重複」且逐筆列入收據 ⑥L4 lag 輸入集合＝L1 群組欄＋raw 欄（`volume_*_volume_VolumeMA-Ratio_*`、
`ohlc_*_pattern_BullishCount_*` 由此新增 lag），新增 lag 欄逐筆列入收據並驗其值＝輸入位移
⑦manifest `feature_naming_version == CURRENT`。收據 `handoffs/run_receipts/ffname-value-invariance.json` 之值雜湊不符數 == 0。
邊界：任一通過條件不等 ⇒ FAIL（回本 Phase，不得改 golden 遷就）。不以欄數相等代替逐欄雜湊。
mutation：§V ⑫§G 映射改為字串 replace（⑤必紅）。
"""

from __future__ import annotations

import collections
import copy
import fnmatch
import json
import re
from typing import Any, Dict, List, Set, Tuple

import numpy as np
import pytest

import momentum.FeatureEngineering.feature_naming as fn
from momentum.FeatureEngineering.feature_reader import FeatureReader
from tests.feature_engineering.ffname_helpers import (
    BASELINE_PATH,
    G6_GLOBS,
    VALUE_RECEIPT,
    drop_last_op,
    group_layer,
    last_op_name,
    load_freeze_module,
    ops_tuple,
    roundtrip_ok,
)
from tests.feature_engineering.fftfmeta_golden_helpers import prepare_env

freeze = load_freeze_module()
_FP_KEYS = ("dtype", "shape", "nan_sha256", "value_sha256")


@pytest.fixture(scope="module")
def baseline() -> Dict[str, Any]:
    return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def current(tmp_path_factory) -> Dict[str, Any]:
    tmp = tmp_path_factory.mktemp("ffname_value_invariance")
    with pytest.MonkeyPatch.context() as mp:
        prepare_env(mp, tmp, FFACT_MULTI_TF_PARALLEL="0")
        return freeze.run_reference(tmp, record_parts=False)


def _parts(baseline: Dict[str, Any]):
    return {row["old_name"]: freeze.NamingPart(**{**row, "params": tuple(tuple(m) for m in (row.get("params") or ())),
                                                  "ops": tuple(row.get("ops") or ())})
            for row in baseline["parts"]}


def _mapping(baseline: Dict[str, Any]) -> Dict[str, str]:
    parts = _parts(baseline)
    return freeze.derive_mapping(parts, {k: p.tf for k, p in parts.items()})


def _l2_merge_dups(baseline, current, mapping) -> Set[str]:
    """舊兩分支重複：多個舊名映到同一新名者（同 canonical 身分），除第一筆外之舊名。"""
    seen: Dict[str, str] = {}
    dups: Set[str] = set()
    for old in sorted(baseline["columns"]):
        new = mapping[old]
        if new in seen:
            dups.add(old)
        else:
            seen[new] = old
    return dups


def _new_lag_cols(current: Dict[str, Any], mapped: Set[str]) -> Set[str]:
    """⑥ 新增 lag 欄：新 run 有、映射集無，且最外層 op 為 Lag、輸入（去 Lag）屬 L1 群組欄或 raw 欄。"""
    groups = current["manifest_groups"]
    l1 = {c for gid, cols in groups.items() if group_layer(gid) == "L1" for c in cols}
    out = set()
    for c in current["columns"]:
        if c in mapped:
            continue
        ident = fn.parse_feature_name(c)
        if last_op_name(ident) != "Lag":
            continue
        base = drop_last_op(ident)
        if fn.format_feature_name(base) in l1 or base.category == "raw":
            out.add(c)
    return out


def cond1(baseline, current, mapping) -> List[str]:
    """①：映射後欄集合相等；例外只准⑤之 L2 合併差集（多舊名映到同一新名，須皆為 derived）與⑥之新增 lag 欄。"""
    mapped = {mapping[o] for o in baseline["columns"]}
    cur = set(current["columns"])
    extra = cur - mapped - _new_lag_cols(current, mapped)
    missing = mapped - cur
    non_l2_merge = [o for o in _l2_merge_dups(baseline, current, mapping) if fn.parse_feature_name(mapping[o]).kind != "derived"]
    return (sorted(f"extra:{c}" for c in extra) + sorted(f"missing:{c}" for c in missing)
            + sorted(f"merge_not_l2:{o}" for o in non_l2_merge))


def cond2(baseline, current, mapping) -> List[str]:
    bad = []
    for old, fp in baseline["columns"].items():
        new = mapping[old]
        got = current["columns"].get(new)
        if got is None or any(fp[k] != got[k] for k in _FP_KEYS):
            bad.append(f"{old}->{new}")
    return bad


def _mapped_pair_signatures(baseline, mapping) -> List[Tuple[str, str, str]]:
    return [(mapping[a], mapping[b], op) for a, b, op in (tuple(x) for x in baseline["l2_pairs"])]


def l2_merged_signatures(baseline, mapping) -> List[Tuple[str, str, str]]:
    """⑤ 之合併差集：多個舊配對簽名映到同一新簽名（同 canonical 身分之舊兩分支重複）。"""
    counts = collections.Counter(_mapped_pair_signatures(baseline, mapping))
    return sorted(sig for sig, n in counts.items() if n > 1)


def cond5(baseline, current, mapping) -> List[str]:
    """⑤：映射後配對簽名集合（同新簽名之舊重複已收斂）== 新 run 配對簽名集合；其餘任何差集＝FAIL。"""
    mapped = set(_mapped_pair_signatures(baseline, mapping))
    cur = {tuple(x) for x in current["l2_pairs"]}
    return sorted(map(str, mapped ^ cur))


def cond6(current) -> List[str]:
    groups = current["manifest_groups"]
    l1 = {c for gid, cols in groups.items() if group_layer(gid) == "L1" for c in cols}
    raw = {i for i in current["l4_lag_inputs"] if fn.parse_feature_name(i).category == "raw"}
    inputs = set(current["l4_lag_inputs"])
    return sorted(inputs ^ (l1 | raw))


# ---------------------------------------------------------------- §G 通過條件

def test_condition_1_column_set_equal_after_mapping(baseline, current):
    assert cond1(baseline, current, _mapping(baseline)) == []


def test_condition_2_four_hashes_equal_per_column(baseline, current):
    assert cond2(baseline, current, _mapping(baseline)) == []


def test_condition_3_rename_count_positive(baseline):
    mapping = _mapping(baseline)
    assert sum(1 for o, n in mapping.items() if o != n) > 0


def test_condition_4_all_new_names_roundtrip(current):
    bad = [c for c in current["columns"] if not roundtrip_ok(c)]
    assert bad == [], bad[:20]


def test_condition_5_l2_pair_signatures_equal_modulo_merge(baseline, current):
    assert cond5(baseline, current, _mapping(baseline)) == []


def test_condition_6_lag_inputs_and_new_lag_values_are_shifts(baseline, current):
    assert cond6(current) == []
    mapping = _mapping(baseline)
    new_lags = sorted(_new_lag_cols(current, {mapping[o] for o in baseline["columns"]}))
    inputs = {fn.format_feature_name(drop_last_op(fn.parse_feature_name(c))) for c in new_lags}
    for glob in G6_GLOBS:
        assert any(fnmatch.fnmatch(i, glob) for i in inputs), glob
    run = current["run"]
    reader = FeatureReader(run["base"])
    for col in new_lags:
        ident = fn.parse_feature_name(col)
        k = int(ops_tuple(ident)[-1].split("-")[1])
        base_name = fn.format_feature_name(drop_last_op(ident))
        if fn.parse_feature_name(base_name).category == "raw":
            continue  # raw 輸入不落盤為特徵欄；其 lag 由 Task 2.4 驗名稱
        frame = reader.load_columns_v2(run["symbol"], run["tf"], run["config_hash"], [col, base_name], artifact_kind="raw")
        np.testing.assert_array_equal(frame[col].to_numpy()[k:], frame[base_name].to_numpy()[:-k])


def test_receipt_lists_exceptions_one_by_one(baseline, current):
    """①⑤⑥ 之例外逐筆列入收據：L2 合併差集與新增 lag 欄與計算值相等。"""
    mapping = _mapping(baseline)
    receipt = json.loads(VALUE_RECEIPT.read_text(encoding="utf-8"))
    assert sorted(map(list, l2_merged_signatures(baseline, mapping))) == sorted(map(list, receipt["l2_merged"]))
    assert sorted(_new_lag_cols(current, {mapping[o] for o in baseline["columns"]})) == sorted(receipt["l4_new_lag"])


def test_task25_order_groups_stationarity_keys_consistent_after_mapping(baseline, current):
    """Task 2.5：§G 之欄序、group 結構、平穩化決策鍵經映射一致（合併差集與新增 lag 欄除外）。"""
    mapping = _mapping(baseline)
    dups = _l2_merge_dups(baseline, current, mapping)
    new_lags = _new_lag_cols(current, {mapping[o] for o in baseline["columns"]})
    old_order = [mapping[o] for o in baseline["column_order"] if o not in dups]
    new_order = [c for c in current["column_order"] if c not in new_lags]
    assert old_order == new_order
    old_groups = {frozenset(mapping[c] for c in cols if c not in dups) for cols in baseline["groups"].values()}
    new_groups = {frozenset(c for c in cols if c not in new_lags) for cols in current["manifest_groups"].values()}
    assert {g for g in old_groups if g} == {g for g in new_groups if g}
    assert {mapping[k] for k in baseline["stationarity_keys"]} == set(current["stationarity_keys"])


def test_condition_7_manifest_naming_version(current):
    assert current["manifest"]["feature_naming_version"] == fn.CURRENT_FEATURE_NAMING_VERSION


def test_receipt_value_mismatch_zero_and_sections():
    receipt = json.loads(VALUE_RECEIPT.read_text(encoding="utf-8"))
    for key in ("schema_version", "command", "exit_code"):
        assert key in receipt
    assert receipt["value_hash_mismatch_count"] == 0
    for key in ("renamed", "l2_merged", "l4_new_lag", "name_length_change"):
        assert key in receipt, key


# ---------------------------------------------------------------- 邊界

def test_boundary_01_any_condition_unequal_fails(baseline, current):
    """任一通過條件不等 ⇒ FAIL：擾動一欄值雜湊（真實 baseline 之複本）⇒ 條件②列出該欄。"""
    mapping = _mapping(baseline)
    perturbed = copy.deepcopy(baseline)
    victim = sorted(perturbed["columns"])[0]
    perturbed["columns"][victim]["value_sha256"] = "0" * 64
    failures = cond2(perturbed, current, mapping)
    assert failures and failures[0].startswith(f"{victim}->")


# ---------------------------------------------------------------- mutation

def test_mutation_string_replace_mapping_breaks_condition_5(baseline, current, monkeypatch):
    """§V mutation ⑫：§G 映射改為字串 replace（數字參數前之底線改連字號）⇒ 條件⑤必紅。"""
    monkeypatch.setattr(freeze, "derive_mapping",
                        lambda parts, tf_of: {o: re.sub(r"_(\d)", r"-\1", o) for o in parts})
    assert cond5(baseline, current, _mapping(baseline)) != []
