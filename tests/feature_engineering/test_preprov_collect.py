"""FFDSTAR Task 1.2（docs/FFDSTAR_SPEC.md）：前處理器之逐欄執行狀態收集。

受測物：`FeaturePreprocessor` 之 run 層級執行紀錄容器（存取點經 `preprov_helpers.preprocessor_records`／
`preprocessor_groups` 單一假設點）、`_merge_decisions_from`、`FeatureFactory._capture_stationarity_decisions`。
真實 kline 短窗 run（同模組同格只生成一次）；單元案例之特徵值取自真實 run 之落盤欄（非合成）。
實作前應為紅；不得以 skip／xfail 暫避。
"""

from __future__ import annotations

import copy
from typing import Any, Dict, List, Mapping, Sequence, Tuple

import numpy as np
import pytest

from momentum.FeatureEngineering import run_provenance as rp
from tests.feature_engineering import ffstat_helpers as fsh
from tests.feature_engineering import preprov_helpers as ph

pytestmark = pytest.mark.requires_kline

Key = Tuple[str, str]


@pytest.fixture(scope="module")
def runs(tmp_path_factory: pytest.TempPathFactory) -> ph.RunCache:
    return ph.RunCache(tmp_path_factory.mktemp("preprov_collect"))


# ---------------------------------------------------------------------------------------------- oracle

def l65_input_keys(obs: ph.Observation) -> List[Key]:
    """觀測到之 L6.5 輸入欄（(原生週期, L6.5 所見欄名)；保留重複以驗無碰撞）。"""
    return [(tf, col) for cols, _arr, tf, _layer in obs.l65_inputs.values() for col in cols]


def record_violations(records: Mapping[Key, Mapping[str, Any]], inputs: Sequence[Key],
                      spec: Mapping[str, Any]) -> List[str]:
    """① 每個輸入欄恰一筆紀錄（無多無缺）、各步驟狀態皆非 null 且屬契約值集。"""
    out: List[str] = []
    if len(inputs) != len(set(inputs)):
        out.append("L6.5 輸入鍵有重複（鍵碰撞）")
    missing, extra = sorted(set(inputs) - set(records)), sorted(set(records) - set(inputs))
    if missing:
        out.append(f"缺紀錄 {len(missing)} 欄（例 {missing[:3]}）")
    if extra:
        out.append(f"多出紀錄 {len(extra)} 欄（例 {extra[:3]}）")
    for key, record in records.items():
        for step in spec["steps"]:
            value = record.get(step)
            if value is None or value not in ph.contract_values(f"step_status_values.{step}", spec):
                out.append(f"{key}.{step}={value!r} 不屬契約")
    return out


def _preprocessor_config(cell: str) -> Dict[str, Any]:
    from momentum.factories import create_feature_factory

    factory = create_feature_factory(cache_dir=ph.KLINE_DIR, validate_continuity=False)
    return factory._resolve_config(copy.deepcopy(ph.CELLS[cell]["payload"])).preprocessing.model_dump()


def _unit_preprocessor(runs: ph.RunCache, *, nan_history: bool) -> Tuple[Any, Any]:
    """真實 run（h1_stat_off）之 L1 特徵欄 ＋ 平穩化開啟之前處理器；`nan_history` ⇒ 校準前史全無有效值。"""
    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

    frame, layers = ph.real_feature_frame(runs.get("h1_stat_off"), 6, layer="L1")
    pre = FeaturePreprocessor(_preprocessor_config("h1_stat_on"), column_layer_map=layers)
    history = frame.copy()
    if nan_history:
        history.loc[:, :] = np.nan
    fsh.attach_unit_calibration(pre, history)
    return pre, frame


def conflict_raises(owner: Any, child: Any) -> bool:
    try:
        owner._merge_decisions_from(child)
    except rp.ProvenanceConflictError:
        return True
    return False


def _real_decision(runs: ph.RunCache) -> Tuple[Key, Dict[str, Any], Dict[str, Any]]:
    pre = ph.observation(runs.get("h1_stat_on")).l65_preprocessor
    key, record = next(iter(pre.stationarity_decisions().items()))
    return key, dict(record), dict(pre._config)


# ---------------------------------------------------------------------------------------------- 驗證

def test_verification_01_each_input_column_exactly_one_record(runs: ph.RunCache) -> None:
    """① 真實短窗群組：每個 L6.5 輸入欄恰一筆、各步驟狀態皆屬契約（平穩化開與關兩格）。"""
    spec = ph.contract()
    for cell in ("h1_stat_on", "h1_stat_off"):
        obs = ph.observation(runs.get(cell))
        inputs = l65_input_keys(obs)
        assert inputs, f"{cell}：無 L6.5 輸入 ⇒ ① 空轉"
        assert record_violations(ph.preprocessor_records(obs.l65_preprocessor), inputs, spec) == [], cell


def test_verification_02_native_success_and_fallback(runs: ph.RunCache) -> None:
    """② native 成功與回退各一案：成功群組之臂屬契約且無回退值；回退案（native 載入列數不符）之同群組帶回退值
    （屬契約群組臂值集）且臂不同於成功案；回退群組之欄仍各恰一筆紀錄。"""
    spec = ph.contract()
    arms = set(ph.contract_values("group_arm_values", spec))
    ok_obs = ph.observation(runs.get("h12h1_multi"))
    native = sorted(g for g, ok in ok_obs.native_groups.items() if ok)
    assert native
    ok_groups = ph.preprocessor_groups(ok_obs.l65_preprocessor)
    for gid in native:
        assert ok_groups[gid]["arm"] in arms and ok_groups[gid]["fallback"] is None, gid
    fb_obs = ph.observation(runs.get("h12h1_native_fallback"))
    fb_groups = ph.preprocessor_groups(fb_obs.l65_preprocessor)
    fell_back = sorted(fb_obs.native_shortened)
    assert fell_back and not any(fb_obs.native_groups.get(g) for g in fell_back)
    for gid in fell_back:
        assert fb_groups[gid]["fallback"] in arms, gid
        if gid in ok_groups:
            assert (fb_groups[gid]["arm"], fb_groups[gid]["fallback"]) != (ok_groups[gid]["arm"], None), gid
    assert record_violations(ph.preprocessor_records(fb_obs.l65_preprocessor), l65_input_keys(fb_obs), spec) == []


def test_verification_03_conflicting_merge_raises(runs: ph.RunCache) -> None:
    """③ 同鍵而值不逐項相同 ⇒ `_merge_decisions_from` 與 `_capture_stationarity_decisions` 皆拋
    `ProvenanceConflictError`；逐項相同則冪等（不拋、值不變）。"""
    from momentum.factories import create_feature_factory
    from momentum.FeatureEngineering.feature_naming import tag_timeframe
    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

    key, record, config = _real_decision(runs)
    changed = dict(record, d=(record.get("d") or 0.0) + 0.25)
    owner, child = FeaturePreprocessor(config), FeaturePreprocessor(config)
    owner._decisions[key], child._decisions[key] = dict(record), changed
    assert conflict_raises(owner, child)
    same_owner, same_child = FeaturePreprocessor(config), FeaturePreprocessor(config)
    same_owner._decisions[key], same_child._decisions[key] = dict(record), dict(record)
    assert not conflict_raises(same_owner, same_child)
    assert same_owner.stationarity_decisions()[key] == FeaturePreprocessor.stationarity_decisions(same_child)[key]
    factory = create_feature_factory(cache_dir=ph.KLINE_DIR, validate_continuity=False)
    factory.last_stationarity_decisions = {tag_timeframe(key[1], key[0]): changed}
    with pytest.raises(rp.ProvenanceConflictError):
        factory._capture_stationarity_decisions(same_owner, None)


# ---------------------------------------------------------------------------------------------- 邊界

def test_boundary_01_group_all_ratio_unsafe(runs: ph.RunCache) -> None:
    """邊界①：群組全為 ratio-unsafe ⇒ 其每欄恰一筆、終態＝SPEC 點名之 `ratio_unsafe`、縮尾非 `applied`。"""
    from momentum.FeatureEngineering.feature_naming import is_ratio_unsafe_column

    spec = ph.contract()
    obs = ph.observation(runs.get("ratio_unsafe"))
    records = ph.preprocessor_records(obs.l65_preprocessor)
    keys = [(tf, c) for cols, _a, tf, _l in obs.l65_inputs.values()
            if cols and all(is_ratio_unsafe_column(x) for x in cols) for c in cols]
    assert keys
    terminal, applied = ph.spec_named("terminal_ratio_unsafe", spec), ph.spec_named("winsor_applied", spec)
    assert all(records[k]["terminal"] == terminal for k in keys)
    assert all(records[k]["winsorization"] != applied for k in keys)


def test_boundary_02_eligible_columns_empty(runs: ph.RunCache) -> None:
    """邊界②：`eligible_columns` 為空（校準前史全無有效值）⇒ 每欄仍恰一筆、fracdiff 未套用（d null）、其 fracdiff 狀態屬
    契約且不同於實際套用 fracdiff 之欄之狀態。"""
    spec = ph.contract()
    pre, frame = _unit_preprocessor(runs, nan_history=True)
    pre.transform(frame)
    records = ph.preprocessor_records(pre)
    inputs = [("1h", str(c)) for c in frame.columns]
    assert record_violations(records, inputs, spec) == []
    assert all(r.get("d") is None and r.get("fracdiff") is not True for r in records.values())
    on = ph.provenance_table(runs.get("h1_stat_on").run_dir, "raw")
    applied = set(on.loc[on["fracdiff"].fillna(False).astype(bool), "fractional_differencing"].astype(str))
    assert applied and not {str(r["fractional_differencing"]) for r in records.values()} & applied


def test_boundary_03_parallel_fracdiff_merge_rejects_duplicate_key(runs: ph.RunCache, monkeypatch: pytest.MonkeyPatch) -> None:
    """邊界③：parallel fracdiff 多 worker 結果合併——正常時每欄恰一筆且鍵集合同串行；同一欄出現兩份不同結果 ⇒ 拒收
    （`ProvenanceError` 上拋，不得被 parallel→serial 回退吞下）。"""
    from momentum.FeatureEngineering.preprocessing import _slow_path_parallel as spp
    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

    spec = ph.contract()
    serial, frame = _unit_preprocessor(runs, nan_history=False)
    serial.transform(frame)
    monkeypatch.setattr(FeaturePreprocessor, "_resolve_slowpath_n_jobs", lambda self: 2)
    parallel, _ = _unit_preprocessor(runs, nan_history=False)
    parallel.transform(frame)
    inputs = [("1h", str(c)) for c in frame.columns]
    assert record_violations(ph.preprocessor_records(parallel), inputs, spec) == []
    assert set(ph.preprocessor_records(parallel)) == set(ph.preprocessor_records(serial))

    real_map = spp.ParallelSlowPath.map

    def duplicating_map(self: Any, items: Any, fn: Any) -> Any:
        outputs = list(real_map(self, items, fn))
        first = next(o for o in outputs if o.get("status") == "ok")
        return outputs + [dict(first, d_star=float(first["d_star"]) + 0.1)]

    monkeypatch.setattr(spp.ParallelSlowPath, "map", duplicating_map)
    dup, _ = _unit_preprocessor(runs, nan_history=False)
    with pytest.raises(rp.ProvenanceError):
        dup.transform(frame)


def test_boundary_04_append_mode_derived_columns_link_parent(runs: ph.RunCache) -> None:
    """邊界④：append 模式衍生欄（`_fracdiff`／`_diff1`／`_diff2`）——其紀錄列之 `parent_column`＝父欄落盤名（最長之
    「輸入欄名＋底線」前綴）、終態屬契約；輸入欄本身 `parent_column` 為 null。"""
    spec = ph.contract()
    handle = runs.get("h1_stat_on")
    obs = ph.observation(handle)
    table = ph.provenance_table(handle.run_dir, "raw").set_index("output_column")
    inputs = {ph.output_name(c, tf) for tf, c in l65_input_keys(obs)}
    derived = sorted(set(table.index) - inputs - set(obs.l7_dropped))
    assert derived, "無衍生欄 ⇒ 邊界空轉"
    terminals = set(ph.contract_values("terminal_values", spec))
    for name in derived:
        parents = [p for p in inputs if name.startswith(p + "_")]
        assert parents, name
        assert table.loc[name, "parent_column"] == max(parents, key=len), name
        assert table.loc[name, "terminal"] in terminals, name
    assert table.loc[sorted(inputs & set(table.index)), "parent_column"].isna().all()


# ---------------------------------------------------------------------------------------------- mutation

def _mutant_accessor(transform: Any) -> Any:
    """以改壞之紀錄存取點包住生產之 `execution_records`（呼叫端以 monkeypatch.setattr 換入）。"""
    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

    original = FeaturePreprocessor.execution_records
    return lambda self: transform(dict(original(self)))


def test_mutation_winsor_success_not_recorded(runs: ph.RunCache, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation：縮尾成功不記（該步狀態缺）⇒ ① 轉紅。"""
    spec = ph.contract()
    obs = ph.observation(runs.get("h1_stat_off"))
    assert record_violations(ph.preprocessor_records(obs.l65_preprocessor), l65_input_keys(obs), spec) == []

    def drop_winsor(records: Dict[Key, Dict[str, Any]]) -> Dict[Key, Dict[str, Any]]:
        key = next(iter(records))
        records[key] = {k: v for k, v in records[key].items() if k != "winsorization"}
        return records

    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

    monkeypatch.setattr(FeaturePreprocessor, "execution_records", _mutant_accessor(drop_winsor))
    assert record_violations(ph.preprocessor_records(obs.l65_preprocessor), l65_input_keys(obs), spec) != []


def test_mutation_exit_point_record_deleted(runs: ph.RunCache, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation：刪任一離開點之紀錄呼叫（該欄整筆缺）⇒ ① 轉紅。"""
    spec = ph.contract()
    obs = ph.observation(runs.get("h1_stat_on"))

    def drop_one(records: Dict[Key, Dict[str, Any]]) -> Dict[Key, Dict[str, Any]]:
        records.pop(next(iter(records)))
        return records

    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

    monkeypatch.setattr(FeaturePreprocessor, "execution_records", _mutant_accessor(drop_one))
    assert any("缺紀錄" in v for v in record_violations(ph.preprocessor_records(obs.l65_preprocessor),
                                                       l65_input_keys(obs), spec))


def test_mutation_merge_reverts_to_overwrite(runs: ph.RunCache, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation：`_merge_decisions_from` 改回覆寫（後寫勝）⇒ ③ 轉紅（衝突不再拋錯）。"""
    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

    key, record, config = _real_decision(runs)

    def overwrite(self: Any, other: Any, idx_map: Any = None) -> None:
        for k, v in other.stationarity_decisions().items():
            self._decisions[k] = dict(v)

    owner, child = FeaturePreprocessor(config), FeaturePreprocessor(config)
    owner._decisions[key], child._decisions[key] = dict(record), dict(record, d=(record.get("d") or 0.0) + 0.25)
    assert conflict_raises(owner, child)
    monkeypatch.setattr(FeaturePreprocessor, "_merge_decisions_from", overwrite)
    owner2, child2 = FeaturePreprocessor(config), FeaturePreprocessor(config)
    owner2._decisions[key], child2._decisions[key] = dict(record), dict(record, d=(record.get("d") or 0.0) + 0.25)
    assert not conflict_raises(owner2, child2)
