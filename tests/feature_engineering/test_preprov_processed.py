"""FFDSTAR Task 1.4（docs/FFDSTAR_SPEC.md）：processed 紀錄檔（post-IC）。

受測物：`FeaturePreprocessor.transform_selected`（post-IC 前處理器沿用 Task 1.2 容器）、`FeatureStorage.write_processed`、
`FeatureFactory.run_ic_first`（`feature_factory.py:2986` 寫入點、`cleanup_raw`）。真實 kline 短窗 IC-first run；
紀錄檔一律測試端自讀（pyarrow）與自算 sha256。實作前應為紅；不得以 skip／xfail 暫避。
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Set

import pandas as pd
import pyarrow.parquet as pq
import pytest

from momentum.FeatureEngineering import numeric_view as _nv
from momentum.FeatureEngineering import run_provenance as rp
from tests.feature_engineering import preprov_helpers as ph

pytestmark = pytest.mark.requires_kline


@pytest.fixture(scope="module")
def runs(tmp_path_factory: pytest.TempPathFactory) -> ph.RunCache:
    return ph.RunCache(tmp_path_factory.mktemp("preprov_processed"))


def raw_record_survives(handle: ph.RunHandle) -> bool:
    """oracle（驗證②）：raw 已刪後 manifest raw 節點所宣告之紀錄檔仍在、sha256（自算）相符、且不在 raw/ 內。"""
    pointer = ph.load_manifest(handle.run_dir)["artifacts"]["raw"]["provenance"]
    path = handle.run_dir / str(pointer["path"])
    return (not (handle.run_dir / "raw").exists() and path.is_file()
            and ph.sha256_file(path) == pointer["sha256"] and Path(str(pointer["path"])).parts[0] != "raw")


def _raw_groups(handle: ph.RunHandle) -> Dict[str, pd.DataFrame]:
    """真實 run 之宣告 raw 群組檔 → {群組: DataFrame（UTC 時間索引）}（post-IC 單元輸入）。"""
    manifest = ph.load_manifest(handle.run_dir)
    seconds = pq.read_table(str(handle.run_dir / ph.row_index_rel(manifest, "raw"))).column("timestamp").to_numpy()
    index = pd.DatetimeIndex(pd.to_datetime(seconds, unit="s", utc=True))
    out: Dict[str, pd.DataFrame] = {}
    for gid, info in manifest["artifacts"]["raw"]["groups"].items():
        frame = pq.read_table(str(handle.run_dir / info["path"])).to_pandas()
        out[gid] = frame.drop(columns=[c for c in frame.columns if c in ph.NON_FEATURE_COLUMNS]).set_axis(index)
    return out


def processed_population_violations(names: Sequence[str], terminal_of: Mapping[str, Any], selected: Iterable[str],
                                    processed_cols: Iterable[str], absent: Iterable[str],
                                    ratio_unsafe: Iterable[str], spec: Mapping[str, Any]) -> List[str]:
    """oracle（SPEC v3 Task 1.4）：processed 紀錄之母體＝IC 選欄全集——逐選欄恰一筆；窮盡性＝processed 群組欄聯集 ∪ 選欄
    不在 raw 之欄 ∪ 入口剔除之 ratio-unsafe 欄 ＝ 選欄全集（三類互斥；各類由紀錄以外之事實導出）；三類各記其終態
    （類內單一值、類間互異、皆屬契約 `terminal_values`）。"""
    out: List[str] = []
    selected, processed = set(selected), set(processed_cols)
    absent, ratio_unsafe = set(absent), set(ratio_unsafe)
    if len(names) != len(set(names)):
        out.append("processed 紀錄有重複欄")
    if set(names) != selected:
        out.append(f"紀錄母體 ≠ 選欄全集：多 {sorted(set(names) - selected)[:3]}、缺 {sorted(selected - set(names))[:3]}")
    classes = {"已寫出 processed": processed, "選欄不在 raw": absent, "入口剔除 ratio-unsafe": ratio_unsafe}
    if processed | absent | ratio_unsafe != selected:
        out.append("processed 群組欄 ∪ 不在 raw ∪ ratio-unsafe ≠ 選欄全集")
    if (processed & absent) or (processed & ratio_unsafe) or (absent & ratio_unsafe):
        out.append("三類欄有交集")
    terminals = set(ph.contract_values("terminal_values", spec))
    seen: Dict[str, Set[str]] = {}
    for label, cols in classes.items():
        values = {str(terminal_of.get(c)) for c in cols if c in terminal_of}
        if cols and len(values) != 1:
            out.append(f"{label}：終態非單一值 {sorted(values)}")
        out.extend(f"{label}：終態 {v!r} 不屬契約" for v in sorted(values - terminals))
        seen[label] = values
    labels = [k for k in classes if classes[k]]
    for i, a in enumerate(labels):
        for b in labels[i + 1:]:
            if seen[a] & seen[b]:
                out.append(f"{a} 與 {b} 終態相同 {sorted(seen[a] & seen[b])}（未各記其終態）")
    return out


def post_ic_unit(runs: ph.RunCache, *, n_absent: int, with_ratio_unsafe: bool) -> Dict[str, Any]:
    """post-IC 單元：真實 run（`ratio_unsafe` 格：raw 含 ratio-unsafe 群組）之宣告 raw 群組 → `transform_selected`
    （polars 臂）；選欄＝3 個真實非 ratio-unsafe 欄 ＋ `n_absent` 個不在 raw 之欄名 ＋（`with_ratio_unsafe`）1 個真實
    ratio-unsafe 欄。紀錄經 `last_post_ic_execution()`（`ph.post_ic_execution`）取得；欄名＝紀錄鍵之 L6.5 所見名（post-IC
    所見即選欄之落盤名）。"""
    from momentum.factories import create_feature_factory
    from momentum.FeatureEngineering.feature_naming import is_ratio_unsafe_column
    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

    handle = runs.get("ratio_unsafe")
    groups = _raw_groups(handle)
    raw_cols = [c for frame in groups.values() for c in frame.columns]
    safe = [c for c in raw_cols if not is_ratio_unsafe_column(c)][:3]
    unsafe = [c for c in raw_cols if is_ratio_unsafe_column(c)][:1] if with_ratio_unsafe else []
    assert len(safe) == 3 and (unsafe or not with_ratio_unsafe), "真實 run 缺所需之欄 ⇒ 前提不成立"
    absent = [f"{c}_absent" for c in safe[:n_absent]]
    assert not set(absent) & set(raw_cols)
    selected = safe + absent + unsafe
    factory = create_feature_factory(cache_dir=ph.KLINE_DIR, validate_continuity=False)
    config = factory._resolve_config(copy.deepcopy(ph.CELLS["ic_first"]["payload"]))
    pre = FeaturePreprocessor(config.preprocessing.model_dump())
    processed = pre.transform_selected(selected, groups, config.preprocessing, arm=_nv.post_ic_arm("ic_first"))  # NUMVIEW Task 3.4：擇定核心（契約）
    records, exec_groups = ph.post_ic_execution(pre)
    return {"pre": pre, "selected": selected, "absent": absent, "ratio_unsafe": unsafe, "records": records,
            "groups": exec_groups, "processed_cols": [str(c) for f in processed.values() for c in f.columns]}


def unit_population_violations(unit: Mapping[str, Any], spec: Mapping[str, Any]) -> List[str]:
    names = [key[1] for key in unit["records"]]
    terminal_of = {key[1]: rec.get("terminal") for key, rec in unit["records"].items()}
    return processed_population_violations(names, terminal_of, unit["selected"], unit["processed_cols"],
                                           unit["absent"], unit["ratio_unsafe"], spec)


# ---------------------------------------------------------------------------------------------- 驗證

def test_verification_01_processed_records_per_selected_column(runs: ph.RunCache) -> None:
    """① 真實短窗 IC-first 後 processed 紀錄逐選欄恰一筆（＝processed 群組欄、⊆ IC 選欄），群組臂＝post-IC 擇定核心（NUMVIEW Task 3.4 取代 FFDSTAR Task 1.4 之 `polars` 字面；契約
    `post_ic_entries.ic_first`，須屬 PRE-PROV 契約 `group_arm_values`）。"""
    spec = ph.contract()
    handle = runs.get("ic_first")
    table = ph.provenance_table(handle.run_dir, "processed")
    names = list(table["output_column"])
    processed_cols = ph.group_columns(handle.run_dir, "processed")
    selected = set(ph.observation(handle).result_metadata["selected_features"])
    assert names and len(names) == len(set(names))
    assert set(names) == set(processed_cols) and set(names) <= selected
    from momentum.FeatureEngineering import numeric_view as nv

    core = nv.post_ic_arm("ic_first")
    assert core in ph.contract_values("group_arm_values", spec)
    groups = ph.provenance_pointer(handle.run_dir, "processed")["groups"]
    assert groups and all(g["arm"] == core for g in groups.values())
    assert ph.sha256_file(ph.provenance_file(handle.run_dir, "processed")) == \
        ph.provenance_pointer(handle.run_dir, "processed")["sha256"]


def test_verification_02_raw_record_survives_cleanup(runs: ph.RunCache) -> None:
    """② `cleanup_raw` 後 raw 紀錄檔仍在（位於 `provenance/`）且 sha256 符合 manifest；processed 節點不覆寫 raw 之紀錄指標。"""
    spec = ph.contract()
    handle = runs.get("ic_first")
    assert raw_record_survives(handle)
    raw_ptr = ph.provenance_pointer(handle.run_dir, "raw")
    proc_ptr = ph.provenance_pointer(handle.run_dir, "processed")
    assert raw_ptr["path"] == spec["files"]["raw"] and proc_ptr["path"] == spec["files"]["processed"]
    assert raw_ptr["sha256"] != proc_ptr["sha256"]


def test_verification_03_empty_selection_zero_rows(runs: ph.RunCache) -> None:
    """③ IC 選擇為空 ⇒ processed 紀錄檔存在而為零列（欄位＝契約 record_columns），狀態可區分「零選欄」
    （processed 節點 total_features＝0、quality_status＝empty_selection、紀錄指標 row_count＝0）。"""
    spec = ph.contract()
    handle = runs.get("ic_first_empty")
    table = ph.provenance_table(handle.run_dir, "processed")
    assert len(table) == 0 and list(table.columns) == list(spec["record_columns"])
    node = ph.load_manifest(handle.run_dir)["artifacts"]["processed"]
    assert node["total_features"] == 0 and node["quality_status"] == "empty_selection"
    assert node["provenance"]["row_count"] == 0


def test_verification_04_rerun_rowindex_failure_restores_or_failcloses(
        tmp_path_factory: pytest.TempPathFactory) -> None:
    """Task 1.3 ⑤b 之 processed 版（CODEX-R5-P1-01）：既有完整 IC-first run A 以同設定重跑（kline 複本改一根、processed
    row index 平移一根），於新 `processed_timestamps.parquet` 寫出後、processed 之 `_atomic_merge_feature_manifest_v2` 前
    注入 `OSError` ⇒ processed/、`processed_timestamps.parquet`、manifest processed 節點三者逐位元組回復為 run A，或 processed
    不可被 `consumer="strict"` 讀為完整；且明確不得出現「舊 processed 位元組＋新時間軸」。"""
    outcome = ph.rerun_with_injected_failure(tmp_path_factory.mktemp("preprov_processed_rerun"), "processed")
    assert outcome.before.artifact_files and outcome.before.row_index and outcome.before.manifest
    assert not (outcome.new_axis_on_disk and outcome.after.artifact_files == outcome.before.artifact_files)
    assert ph.rerun_failure_violations(outcome) == []


def test_verification_05_processed_population_is_ic_selected_set(runs: ph.RunCache) -> None:
    """SPEC v3 Task 1.4：真實短窗 IC-first 之 processed 紀錄母體＝IC 選欄全集（逐選欄恰一筆）；窮盡性＝processed 群組欄
    聯集 ∪ 選欄不在 raw（依 manifest raw 群組宣告之欄導出）∪ 選欄中 ratio-unsafe 欄 ＝ 選欄全集，三類各記其終態。"""
    from momentum.FeatureEngineering.feature_naming import is_ratio_unsafe_column

    spec = ph.contract()
    handle = runs.get("ic_first")
    selected = [str(c) for c in ph.observation(handle).result_metadata["selected_features"]]
    assert selected, "IC 選欄為空 ⇒ 空轉"
    table = ph.provenance_table(handle.run_dir, "processed")
    raw_node = ph.load_manifest(handle.run_dir)["artifacts"]["raw"]
    raw_cols = {str(c) for info in raw_node["groups"].values() for c in info.get("columns") or []}
    assert raw_cols, "manifest raw 群組無欄宣告 ⇒ 無法導出「不在 raw」"
    absent = {c for c in selected if c not in raw_cols}
    unsafe = {c for c in selected if c in raw_cols and is_ratio_unsafe_column(c)}
    names = [str(n) for n in table["output_column"]]
    terminal_of = dict(zip(names, table["terminal"]))
    assert processed_population_violations(names, terminal_of, selected, ph.group_columns(handle.run_dir, "processed"),
                                           absent, unsafe, spec) == []
    assert ph.provenance_pointer(handle.run_dir, "processed")["row_count"] == len(set(selected))


# ---------------------------------------------------------------------------------------------- 邊界

def test_boundary_01_selected_columns_absent_from_raw(runs: ph.RunCache) -> None:
    """邊界①：選欄全不在 raw ⇒ post-IC 無輸出、紀錄零筆；以之組表為零列且欄位＝契約。"""
    from momentum.factories import create_feature_factory
    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

    spec = ph.contract()
    handle = runs.get("h1_stat_off")
    factory = create_feature_factory(cache_dir=ph.KLINE_DIR, validate_continuity=False)
    config = factory._resolve_config(copy.deepcopy(ph.CELLS["ic_first"]["payload"]))
    pre = FeaturePreprocessor(config.preprocessing.model_dump())
    groups = _raw_groups(handle)
    absent = [f"{name}_absent" for name in list(next(iter(groups.values())).columns)[:3]]
    assert pre.transform_selected(absent, groups, config.preprocessing, arm=_nv.post_ic_arm("ic_first")) == {}
    records = ph.preprocessor_records(pre)
    assert records == {}
    table = rp.build_provenance_table(records, output_columns=[], column_group={}, dropped_columns={})
    assert len(table) == 0 and list(table.columns) == list(spec["record_columns"])


def test_boundary_02_gaussian_on(runs: ph.RunCache) -> None:
    """邊界②：post-IC gaussian 開啟 ⇒ processed 紀錄之 gaussian 狀態為單一契約值，且不同於 gaussian 關閉之 IC-first 格。"""
    spec = ph.contract()
    on = ph.provenance_table(runs.get("ic_first_gaussian").run_dir, "processed")
    off = ph.provenance_table(runs.get("ic_first").run_dir, "processed")
    assert len(on) and len(off)
    on_status, off_status = set(on["gaussian_normalize"].astype(str)), set(off["gaussian_normalize"].astype(str))
    assert len(on_status) == 1 and on_status <= set(ph.contract_values("step_status_values.gaussian_normalize", spec))
    assert not on_status & off_status


def test_boundary_03_selected_column_missing_from_raw_has_terminal_record(runs: ph.RunCache) -> None:
    """SPEC v3 Task 1.4（`feature_preprocessor.py:683` 附近）：選欄不在 raw ⇒ 該欄仍有恰一筆紀錄、記其專屬終態；窮盡性
    ＝processed 群組欄 ∪ 不在 raw 之欄 ＝ 選欄全集。"""
    spec = ph.contract()
    unit = post_ic_unit(runs, n_absent=2, with_ratio_unsafe=False)
    assert unit["absent"] and unit["processed_cols"]
    assert unit_population_violations(unit, spec) == []
    assert {key[1] for key in unit["records"]} >= set(unit["absent"])


def test_boundary_04_ratio_unsafe_selected_column_has_terminal_record(runs: ph.RunCache) -> None:
    """SPEC v3 Task 1.4（`feature_preprocessor.py:585` 附近）：選欄含 ratio-unsafe 欄（post-IC 入口剔除）⇒ 該欄仍有恰一筆
    紀錄、記其專屬終態（不同於已寫出與不在 raw）；窮盡性＝processed 群組欄 ∪ 不在 raw ∪ ratio-unsafe ＝ 選欄全集。"""
    spec = ph.contract()
    unit = post_ic_unit(runs, n_absent=1, with_ratio_unsafe=True)
    assert unit["ratio_unsafe"] and unit["absent"] and unit["processed_cols"]
    assert not set(unit["ratio_unsafe"]) & set(unit["processed_cols"]), "ratio-unsafe 選欄被寫入 processed ⇒ 前提不成立"
    assert unit_population_violations(unit, spec) == []
    assert {key[1] for key in unit["records"]} >= set(unit["ratio_unsafe"])


# ---------------------------------------------------------------------------------------------- mutation

def test_mutation_raw_record_inside_raw_dir(tmp_path_factory: pytest.TempPathFactory,
                                            monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation（SPEC Task 1.4）：raw 紀錄檔改放 `raw/` 內 ⇒ ② 轉紅（cleanup_raw 連同紀錄檔刪除）。"""
    spec = ph.contract()
    mutant: Dict[str, Any] = copy.deepcopy(spec)
    mutant["files"]["raw"] = "raw/" + Path(spec["files"]["raw"]).name
    monkeypatch.setattr(rp, "load_contract", lambda: copy.deepcopy(mutant))
    handle = ph.generate_short_run(tmp_path_factory.mktemp("preprov_processed_mutant"), "ic_first")
    assert not raw_record_survives(handle)


def test_mutation_processed_rowindex_direct_write_without_restore(tmp_path_factory: pytest.TempPathFactory,
                                                                  monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation（CODEX-R5-P1-01）：`write_processed` 改為新時間軸直寫 run 根之 `processed_timestamps.parquet`、不備份不回復
    （改前碼之行為；monkeypatch 入口於失敗後直寫）⇒ 驗證④之 oracle 轉紅，且紅因為「舊 processed＋新時間軸」錯配。"""
    from momentum.FeatureEngineering.feature_storage import FeatureStorage

    monkeypatch.setattr(FeatureStorage, "write_processed",
                        ph.legacy_direct_axis_writer(FeatureStorage.write_processed, "processed_timestamps.parquet"))
    outcome = ph.rerun_with_injected_failure(tmp_path_factory.mktemp("preprov_processed_rerun_mutant"), "processed")
    assert outcome.new_axis_on_disk
    violations = ph.rerun_failure_violations(outcome)
    assert any("錯配" in v for v in violations), violations


def test_mutation_missing_or_ratio_unsafe_selected_not_recorded(runs: ph.RunCache,
                                                                 monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation（SPEC v3 Task 1.4）：post-IC 紀錄漏記「選欄不在 raw」與「入口剔除 ratio-unsafe」之欄（只記已寫出者＝改前
    之母體）、或兩類記成同一終態 ⇒ 母體／窮盡性 oracle 轉紅。正對照：未改壞時無違規。"""
    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

    spec = ph.contract()
    unit = post_ic_unit(runs, n_absent=1, with_ratio_unsafe=True)
    assert unit_population_violations(unit, spec) == []
    dropped = set(unit["absent"]) | set(unit["ratio_unsafe"])
    original = FeaturePreprocessor.last_post_ic_execution

    def written_only(self: Any) -> Any:
        records, groups = original(self)
        return {k: v for k, v in dict(records).items() if k[1] not in dropped}, groups

    monkeypatch.setattr(FeaturePreprocessor, "last_post_ic_execution", written_only)
    mutant = dict(unit, records=ph.post_ic_execution(unit["pre"])[0])
    assert any("母體" in v for v in unit_population_violations(mutant, spec))

    def merged_terminal(self: Any) -> Any:
        records, groups = original(self)
        records = {k: dict(v) for k, v in dict(records).items()}
        absent_key = next(k for k in records if k[1] in set(unit["absent"]))
        unsafe_key = next(k for k in records if k[1] in set(unit["ratio_unsafe"]))
        records[unsafe_key]["terminal"] = records[absent_key]["terminal"]
        return records, groups

    monkeypatch.setattr(FeaturePreprocessor, "last_post_ic_execution", merged_terminal)
    mutant = dict(unit, records=ph.post_ic_execution(unit["pre"])[0])
    assert any("未各記其終態" in v for v in unit_population_violations(mutant, spec))
