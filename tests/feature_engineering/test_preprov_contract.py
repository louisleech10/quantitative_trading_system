"""FFDSTAR Task 1.1（docs/FFDSTAR_SPEC.md）：離開路徑盤點之契約 JSON 驗收。

契約＝`momentum/FeatureEngineering/contracts/run_provenance.json`（唯一真相源）；本檔不列舉任何狀態值，值集一律讀契約。
③ 之「實際紀錄中出現之值」取自 §V 全格（`preprov_helpers.CELLS`）與本檔之單元案例之落盤紀錄、manifest 群組表與
前處理器紀錄；真實 kline 短窗、同模組同格只生成一次。實作前應為紅；不得以 skip／xfail 暫避。
"""

from __future__ import annotations

import copy
import re
from typing import Any, Dict, List, Mapping, Set, Tuple

import pytest

from momentum.FeatureEngineering import run_provenance as rp
from tests.feature_engineering import ffstat_helpers as fsh
from tests.feature_engineering import preprov_helpers as ph

pytestmark = pytest.mark.requires_kline

_SOURCE_RE = re.compile(r"^(?P<path>[^:\s]+):(?P<line>\d+)$")
_PREPROCESSOR = "momentum/FeatureEngineering/preprocessing/feature_preprocessor.py"


@pytest.fixture(scope="module")
def runs(tmp_path_factory: pytest.TempPathFactory) -> ph.RunCache:
    return ph.RunCache(tmp_path_factory.mktemp("preprov_contract"))


# ---------------------------------------------------------------------------------------------- oracle（純函式）

def source_violations(spec: Mapping[str, Any]) -> List[str]:
    """① 每個值集非空；每值恰有 `_sources`（非空清單）；每個 `path:line` 指向 repo 內存在之檔之非註解非空行；
    `_sources` 不得有值集外之鍵。"""
    out: List[str] = []
    for path in ph.enum_paths(spec):
        node = ph.enum_node(path, spec)
        values, sources = list(node["values"]), dict(node["_sources"])
        if not values:
            out.append(f"{path}: 值集為空")
        for extra in sorted(set(sources) - set(values)):
            out.append(f"{path}: _sources 有值集外之鍵 {extra!r}")
        for value in values:
            refs = sources.get(value)
            if not isinstance(refs, list) or not refs:
                out.append(f"{path}.{value}: 無 _sources")
                continue
            for ref in refs:
                m = _SOURCE_RE.match(str(ref))
                if not m:
                    out.append(f"{path}.{value}: _sources 格式非 path:line：{ref!r}")
                    continue
                target = ph.REPO / m["path"]
                if not target.is_file():
                    out.append(f"{path}.{value}: 檔不存在 {ref}")
                    continue
                lines = target.read_text(encoding="utf-8").splitlines()
                n = int(m["line"])
                text = lines[n - 1].strip() if 1 <= n <= len(lines) else ""
                if not text or text.startswith("#"):
                    out.append(f"{path}.{value}: {ref} 為空行或註解行")
    return out


def pattern_violations(spec: Mapping[str, Any]) -> List[str]:
    """② 每個值合契約 `value_pattern`。"""
    pattern = re.compile(str(spec["value_pattern"]))
    return [f"{path}: {value!r}" for path in ph.enum_paths(spec)
            for value in ph.contract_values(path, spec) if not pattern.fullmatch(str(value))]


def coverage_violations(spec: Mapping[str, Any], observed: Mapping[str, Set[str]]) -> List[str]:
    """③ 觀測值 ⊆ 契約值集；契約每值至少被觀測一次，否則須列於 `_unreachable`（鍵＝`<值集路徑>.<值>` 或值本身，
    值須含至少一個 `path:line` 碼證）。"""
    out: List[str] = []
    unreachable = dict(spec.get("_unreachable") or {})
    for path in ph.enum_paths(spec):
        values = set(ph.contract_values(path, spec))
        seen = set(observed.get(path, set()))
        for value in sorted(seen - values):
            out.append(f"{path}: 觀測值 {value!r} 不在契約")
        for value in sorted(values - seen):
            reason = unreachable.get(f"{path}.{value}", unreachable.get(value))
            if reason is None:
                out.append(f"{path}: 契約值 {value!r} 無任何格／單元案例產出且未列 _unreachable")
            elif not re.search(r"[\w./-]+\.\w+:\d+", json_text(reason)):
                out.append(f"{path}: _unreachable {value!r} 無 path:line 碼證")
    return out


def json_text(obj: Any) -> str:
    import json

    return obj if isinstance(obj, str) else json.dumps(obj, ensure_ascii=False)


def observed_from_table(table: Any, spec: Mapping[str, Any]) -> Dict[str, Set[str]]:
    out: Dict[str, Set[str]] = {}
    for column, path in ph.record_enum_columns(spec).items():
        if column in table.columns:
            out.setdefault(path, set()).update(str(v) for v in table[column].dropna().unique())
    return out


def observed_from_groups(groups: Mapping[str, Mapping[str, Any]]) -> Dict[str, Set[str]]:
    out: Dict[str, Set[str]] = {"group_arm_values": set(), "group_status_values": set()}
    for info in groups.values():
        for key, path in (("arm", "group_arm_values"), ("fallback", "group_arm_values"), ("status", "group_status_values")):
            if info.get(key) is not None:
                out[path].add(str(info[key]))
    return out


def observed_from_records(records: Mapping[Tuple[str, str], Mapping[str, Any]], spec: Mapping[str, Any]) -> Dict[str, Set[str]]:
    out: Dict[str, Set[str]] = {}
    for record in records.values():
        for column, path in ph.record_enum_columns(spec).items():
            if record.get(column) is not None:
                out.setdefault(path, set()).add(str(record[column]))
    return out


def merge(into: Dict[str, Set[str]], more: Mapping[str, Set[str]]) -> None:
    for key, values in more.items():
        into.setdefault(key, set()).update(values)


def observed_from_run(handle: ph.RunHandle, spec: Mapping[str, Any]) -> Dict[str, Set[str]]:
    out: Dict[str, Set[str]] = {}
    manifest = ph.load_manifest(handle.run_dir)
    for kind in ("raw", "processed"):
        if kind in manifest.get("artifacts", {}):
            merge(out, observed_from_table(ph.provenance_table(handle.run_dir, kind), spec))
            merge(out, observed_from_groups(manifest["artifacts"][kind]["provenance"]["groups"]))
    return out


# ---------------------------------------------------------------------------------------------- 單元案例（真實特徵）

def _fracdiff_early_exit_line() -> int:
    """`_apply_fractional_differencing` 內 `if not HAS_STATSMODELS:` 之行號（碼證比對錨點）。"""
    lines = (ph.REPO / _PREPROCESSOR).read_text(encoding="utf-8").splitlines()
    start = next(i for i, t in enumerate(lines) if "def _apply_fractional_differencing(" in t)
    return next(i for i in range(start, len(lines)) if "if not HAS_STATSMODELS" in lines[i]) + 1


def statsmodels_unavailable_records(runs: ph.RunCache, monkeypatch: pytest.MonkeyPatch) -> Dict[Tuple[str, str], Dict[str, Any]]:
    """邊界①：statsmodels 不可用 ⇒ fracdiff 於入口早退；以真實 run 之 L1 特徵欄跑單一前處理器。"""
    from momentum.factories import create_feature_factory
    from momentum.FeatureEngineering.preprocessing import feature_preprocessor as fpm

    handle = runs.get("h1_stat_off")
    frame, layers = ph.real_feature_frame(handle, 6, layer="L1")
    factory = create_feature_factory(cache_dir=ph.KLINE_DIR, validate_continuity=False)
    config = factory._resolve_config(copy.deepcopy(ph.CELLS["h1_stat_on"]["payload"])).preprocessing.model_dump()
    monkeypatch.setattr(fpm, "HAS_STATSMODELS", False)
    pre = fpm.FeaturePreprocessor(config, column_layer_map=layers)
    fsh.attach_unit_calibration(pre, frame)
    pre.transform(frame)
    return ph.preprocessor_records(pre)


# ---------------------------------------------------------------------------------------------- 驗證

def test_verification_00_load_contract_is_the_file() -> None:
    """`run_provenance.load_contract()` 回傳契約檔本身（單一真相源；不得另組）。"""
    assert rp.CONTRACT_PATH == ph.CONTRACT_PATH
    assert rp.load_contract() == ph.contract()


def test_verification_01_sources_point_to_code_lines() -> None:
    """① 每個狀態值之 `_sources` 之每個 `path:line` 指向非註解非空行（且值集非空）。"""
    assert source_violations(ph.contract()) == []


def test_verification_02_values_match_pattern() -> None:
    """② 契約值皆合 `value_pattern`。"""
    spec = ph.contract()
    assert spec["value_pattern"] == "^[a-z][a-z0-9_]*$"
    assert all(ph.contract_values(p, spec) for p in ph.enum_paths(spec)), "值集為空 ⇒ ② 空轉"
    assert pattern_violations(spec) == []


def test_verification_03_observed_values_subset_and_covered(runs: ph.RunCache, monkeypatch: pytest.MonkeyPatch) -> None:
    """③ §V 全格之實際紀錄值集 ⊆ 契約；契約每值至少被一格或單元案例產出，否則列 `_unreachable` 附碼證。"""
    spec = ph.contract()
    observed: Dict[str, Set[str]] = {}
    for cell in ph.CELLS:
        for handle in runs.all_of(cell):
            merge(observed, observed_from_run(handle, spec))
            pre = ph.observation(handle).l65_preprocessor
            if pre is not None:
                merge(observed, observed_from_records(ph.preprocessor_records(pre), spec))
                merge(observed, observed_from_groups(ph.preprocessor_groups(pre)))
    merge(observed, observed_from_run(runs.get("h12h1_native_fallback"), spec))
    merge(observed, observed_from_run(runs.get("ic_first_empty"), spec))
    merge(observed, observed_from_records(statsmodels_unavailable_records(runs, monkeypatch), spec))
    assert sum(len(v) for v in observed.values()) > 0, "未觀測到任何值 ⇒ ③ 空轉"
    assert coverage_violations(spec, observed) == []


# ---------------------------------------------------------------------------------------------- 邊界

def test_boundary_01_statsmodels_unavailable_fracdiff_early_exit(runs: ph.RunCache, monkeypatch: pytest.MonkeyPatch) -> None:
    """邊界①：statsmodels 不可用之 fracdiff 早退——每欄恰一筆紀錄、fracdiff 未套用（d 為 null），其 fracdiff 狀態值之
    `_sources` 含該早退點（`_apply_fractional_differencing` 之 `if not HAS_STATSMODELS` 起兩行內）。"""
    spec = ph.contract()
    records = statsmodels_unavailable_records(runs, monkeypatch)
    assert records, "無紀錄 ⇒ 早退未記"
    anchor = _fracdiff_early_exit_line()
    statuses = {str(r["fractional_differencing"]) for r in records.values()}
    assert len(statuses) == 1, statuses
    status = statuses.pop()
    assert status in ph.contract_values("step_status_values.fractional_differencing", spec)
    refs = ph.enum_node("step_status_values.fractional_differencing", spec)["_sources"][status]
    hits = [r for r in refs if str(r).startswith(_PREPROCESSOR + ":") and anchor <= int(str(r).rsplit(":", 1)[1]) <= anchor + 2]
    assert hits, f"值 {status!r} 之 _sources {refs} 不含早退點 {_PREPROCESSOR}:{anchor}"
    assert all(r.get("d") is None and r.get("fracdiff") is not True for r in records.values())


def test_boundary_02_columns_outside_fracdiff_layers(runs: ph.RunCache) -> None:
    """邊界②：目標層外之欄（fracdiff 不涵蓋）——其 fracdiff 狀態值屬契約、且不同於實際 fracdiff 之欄之狀態值；d 為 null。"""
    from momentum.core.config import get_fracdiff_layers

    spec = ph.contract()
    handle = runs.get("h1_stat_on")
    table = ph.provenance_table(handle.run_dir, "raw").set_index("output_column")
    layers = get_fracdiff_layers()
    layer_of = {ph.output_name(c, tf): layer for cols, _a, tf, layer in ph.observation(handle).l65_inputs.values()
                for c in cols}
    outside = sorted(n for n, layer in layer_of.items() if "ALL" not in layers and layer not in layers)
    applied = table.index[table["fracdiff"].fillna(False).astype(bool)]
    assert outside and len(applied), "目標層外或已套用 fracdiff 之欄為空 ⇒ 邊界空轉"
    outside_status = set(table.loc[outside, "fractional_differencing"].astype(str))
    applied_status = set(table.loc[applied, "fractional_differencing"].astype(str))
    assert outside_status <= set(ph.contract_values("step_status_values.fractional_differencing", spec))
    assert not outside_status & applied_status
    assert table.loc[outside, "d"].isna().all()


def test_boundary_03_stationarity_off_null_decisions(runs: ph.RunCache) -> None:
    """邊界③：平穩化關閉——平穩化決策欄全 null；fracdiff／ADF 步驟狀態各為單一契約值，且不同於平穩化開啟格中實際套用之值。"""
    spec = ph.contract()
    off = ph.provenance_table(runs.get("h1_stat_off").run_dir, "raw")
    on = ph.provenance_table(runs.get("h1_stat_on").run_dir, "raw")
    assert set(ph.STATIONARITY_DECISION_COLUMNS) <= set(spec["record_columns"])
    assert len(off) > 0
    for column in ph.STATIONARITY_DECISION_COLUMNS:
        assert off[column].isna().all(), column
    applied = on["fracdiff"].fillna(False).astype(bool)
    for step in ("fractional_differencing", "adf_differencing"):
        values = set(off[step].astype(str))
        assert len(values) == 1 and values <= set(ph.contract_values(f"step_status_values.{step}", spec)), (step, values)
    assert not set(off["fractional_differencing"].astype(str)) & set(on.loc[applied, "fractional_differencing"].astype(str))


# ---------------------------------------------------------------------------------------------- mutation

def test_mutation_contract_missing_observed_value_breaks_subset(runs: ph.RunCache, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation（SPEC Task 1.1）：契約刪一個實際會出現之值 ⇒ ③ 之 oracle 轉紅。"""
    spec = ph.contract()
    observed = observed_from_run(runs.get("h1_stat_on"), spec)
    path = next(p for p in ph.enum_paths(spec) if observed.get(p))
    value = sorted(observed[path])[0]
    mutant = copy.deepcopy(spec)
    node = ph.enum_node(path, mutant)
    node["values"] = [v for v in node["values"] if v != value]
    node["_sources"].pop(value, None)
    monkeypatch.setattr(rp, "load_contract", lambda: mutant)
    assert coverage_violations(rp.load_contract(), {path: {value}}) != []
    assert not [v for v in coverage_violations(spec, {path: {value}}) if "不在契約" in v]


def test_mutation_source_pointing_to_comment_line_is_caught(monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation：某值之 `_sources` 改指註解行 ⇒ ① 之 oracle 轉紅。"""
    spec = ph.contract()
    lines = (ph.REPO / _PREPROCESSOR).read_text(encoding="utf-8").splitlines()
    comment = next(i + 1 for i, t in enumerate(lines) if t.strip().startswith("#"))
    mutant = copy.deepcopy(spec)
    path = ph.enum_paths(mutant)[0]
    node = ph.enum_node(path, mutant)
    node["values"] = list(node["values"]) or ["mutant_value"]
    node["_sources"] = {v: [f"{_PREPROCESSOR}:{comment}"] for v in node["values"]}
    monkeypatch.setattr(rp, "load_contract", lambda: mutant)
    assert any("註解行" in v for v in source_violations(rp.load_contract()))
