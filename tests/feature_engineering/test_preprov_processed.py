"""FFDSTAR Task 1.4（docs/FFDSTAR_SPEC.md）：processed 紀錄檔（post-IC）。

受測物：`FeaturePreprocessor.transform_selected`（post-IC 前處理器沿用 Task 1.2 容器）、`FeatureStorage.write_processed`、
`FeatureFactory.run_ic_first`（`feature_factory.py:2986` 寫入點、`cleanup_raw`）。真實 kline 短窗 IC-first run；
紀錄檔一律測試端自讀（pyarrow）與自算 sha256。實作前應為紅；不得以 skip／xfail 暫避。
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any, Dict

import pandas as pd
import pyarrow.parquet as pq
import pytest

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


# ---------------------------------------------------------------------------------------------- 驗證

def test_verification_01_processed_records_per_selected_column(runs: ph.RunCache) -> None:
    """① 真實短窗 IC-first 後 processed 紀錄逐選欄恰一筆（＝processed 群組欄、⊆ IC 選欄），群組臂＝SPEC 點名之 `polars`。"""
    spec = ph.contract()
    handle = runs.get("ic_first")
    table = ph.provenance_table(handle.run_dir, "processed")
    names = list(table["output_column"])
    processed_cols = ph.group_columns(handle.run_dir, "processed")
    selected = set(ph.observation(handle).result_metadata["selected_features"])
    assert names and len(names) == len(set(names))
    assert set(names) == set(processed_cols) and set(names) <= selected
    polars = ph.spec_named("post_ic_arm_polars", spec)
    groups = ph.provenance_pointer(handle.run_dir, "processed")["groups"]
    assert groups and all(g["arm"] == polars for g in groups.values())
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
    assert pre.transform_selected(absent, groups, config.preprocessing, arm="polars") == {}
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
