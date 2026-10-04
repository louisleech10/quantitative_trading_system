"""ICFIRSTALIGN 乙 Phase 1：三處時間軸與位置選窗（docs/ICFIRSTALIGN_SPEC.md v17 Task 1.1–1.3）。

真實 kline S2（BTCUSDT 12h、精簡 L1、CGSA persist）；一切寫入隔離於 tmp。
實作前應為紅：IC 讀回未接 sidecar（等長拒用／不等長靜默全 NaN）、選欄讀回無 `attach_row_index`、
processed 無自身 sidecar 且覆寫根 time_range、位置鍵選窗仍被接受。
mutant 一律以「HEAD 之原實作」或「改壞之版本」替換生產符號，斷言結果翻轉。
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import pytest

from momentum.Analysis.ic_engine import ICEngine
from momentum.core.contracts import AlignmentViolationError
from momentum.core.icfirstalign_errors import RowIndexArtifactMissingError, RowIndexLengthMismatchError
from momentum.FeatureEngineering.feature_reader import FeatureReader
from momentum.FeatureEngineering.feature_storage import FeatureStorage
from tests.feature_engineering import icfirstalign_helpers as h

pytestmark = pytest.mark.timeout(600)

POSITIONAL_KEYS = tuple(h.CONTRACT["positional_selection_keys"])


# ---------------------------------------------------------------- fixtures

@pytest.fixture(scope="module")
def s2(tmp_path_factory: pytest.TempPathFactory) -> Dict[str, Any]:
    """模組共用之 S2 run（唯讀使用；破壞性測試另跑 `fresh_s2`）。"""
    mp = pytest.MonkeyPatch()
    tmp = tmp_path_factory.mktemp("icfa_timeaxis_s2")
    root = h.isolated(mp, tmp)
    _, result = h.generate_s2(root)
    config_hash = str(result.metadata["config_hash"])
    yield {"root": root, "config_hash": config_hash, "reader": FeatureReader(str(root)),
           "run_dir": h.run_dir(root, config_hash)}
    mp.undo()


@pytest.fixture()
def fresh_s2(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Dict[str, Any]:
    root = h.isolated(monkeypatch, tmp_path)
    _, result = h.generate_s2(root)
    config_hash = str(result.metadata["config_hash"])
    return {"root": root, "config_hash": config_hash, "reader": FeatureReader(str(root)),
            "run_dir": h.run_dir(root, config_hash)}


def _sidecar(run: Dict[str, Any], kind: str = "raw") -> pd.DatetimeIndex:
    """測試端獨立讀 sidecar（不經 reader）：manifest 指定之 parquet 之 int64 epoch 秒。"""
    manifest = json.loads((run["run_dir"] / "feature_manifest.json").read_text(encoding="utf-8"))
    node = manifest["row_index"] if kind == "raw" else manifest["artifacts"]["processed"]["row_index"]
    values = pq.read_table(str(run["run_dir"] / node["path"]), columns=["timestamp"]).column("timestamp").to_numpy()
    return pd.DatetimeIndex(pd.to_datetime(values, unit="s"))


def _all_raw_columns(run: Dict[str, Any]) -> list:
    manifest = run["reader"].load_manifest_v2(h.SYMBOL, h.PRIMARY, run["config_hash"], artifact_kind="raw")
    cols: list = []
    for info in manifest["artifacts"]["raw"]["groups"].values():
        cols.extend(info.get("columns", []))
    return cols


def _ic(run: Dict[str, Any], label: pd.Series, **kwargs: Any):
    kwargs.setdefault("label_horizon", "1")
    kwargs.setdefault("selection_window", {"start": str(label.index.min()), "end": str(label.index.max())})
    return ICEngine({"methods": ["spearman"]}).compute_ic_from_l7_raw(
        h.SYMBOL, h.PRIMARY, run["config_hash"], label, feature_reader=run["reader"], ic_threshold=0.0, **kwargs)


# HEAD（eb1aae1e）之原實作，作 mutant 用（逐字搬自 momentum/Analysis/ic_engine.py 與 feature_reader.py）
def _head_align_label_to_group(label: pd.Series, group_df: pd.DataFrame) -> pd.Series:
    label_series = label if isinstance(label, pd.Series) else pd.Series(label)
    label_name = label_series.name or "label"
    if label_series.index.equals(group_df.index):
        return label_series.rename(label_name)
    if len(label_series) == len(group_df):
        raise AlignmentViolationError("label/group index mismatch with equal length; refusing positional alignment")
    return label_series.reindex(group_df.index).rename(label_name)


def _head_apply_selection_window(features_df: pd.DataFrame, label: pd.Series,
                                 selection_window: Optional[Dict[str, Any]]) -> Tuple[pd.DataFrame, pd.Series]:
    if not selection_window:
        return features_df, label
    start_pos = selection_window.get("start_pos", selection_window.get("start_index"))
    end_pos = selection_window.get("end_pos", selection_window.get("end_index"))
    if isinstance(start_pos, int) or isinstance(end_pos, int):
        start = max(int(start_pos or 0), 0)
        end = int(end_pos) if isinstance(end_pos, int) else len(features_df)
        end = max(min(end, len(features_df)), start)
        return features_df.iloc[start:end], label.iloc[start:end]
    return features_df, label


def _head_load_row_index_v2(self: FeatureReader, symbol: str, tf: str, config_hash: str,
                            artifact_kind: str = "raw") -> Optional[pd.DatetimeIndex]:
    manifest, base_dir, _ = self._resolve_manifest_v2(symbol=symbol, tf=tf, config_hash=config_hash,
                                                       artifact_kind=artifact_kind)
    row_index = manifest.get("row_index")
    if row_index is None:
        return None
    path = self._resolve_manifest_relative_path(base_dir, row_index.get("path"))
    values = pq.read_table(str(path), columns=["timestamp"]).column("timestamp").to_numpy()
    return pd.DatetimeIndex(pd.to_datetime(values, unit="s"))


# ---------------------------------------------------------------- Task 1.1 IC 讀回接時間軸

def test_ic_scores_match_independent_oracle_s2(s2: Dict[str, Any]) -> None:
    """§G IC-first oracle（S2）：引擎 IC 分數與測試端獨立 Spearman 逐欄相等（atol 1e-12）。"""
    label = h.forward_return_label()
    cols = _all_raw_columns(s2)
    features = s2["reader"].load_columns_v2(h.SYMBOL, h.PRIMARY, s2["config_hash"], cols)
    features.index = _sidecar(s2)
    sidecar = _sidecar(s2)
    label_in = label.loc[label.index.intersection(sidecar)]
    expected = h.oracle_spearman(features, label_in)
    got = _ic(s2, label).ic_scores
    assert set(got) == set(expected)
    a = np.array([got[c] for c in sorted(expected)], dtype=np.float64)
    b = np.array([expected[c] for c in sorted(expected)], dtype=np.float64)
    assert np.isfinite(b).sum() > 0
    assert np.allclose(a, b, rtol=0, atol=1e-12, equal_nan=True)


def test_ic_readback_group_index_equals_raw_sidecar(s2: Dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    """IC 讀回群組索引與 raw sidecar exact 相等（spy `_align_label_to_group` 收到之群組）。"""
    seen: list = []
    real = ICEngine._align_label_to_group

    def spy(label: pd.Series, group_df: pd.DataFrame) -> pd.Series:
        seen.append(group_df.index.copy())
        return real(label, group_df)

    monkeypatch.setattr(ICEngine, "_align_label_to_group", staticmethod(spy))
    _ic(s2, h.forward_return_label())
    assert seen
    sidecar = _sidecar(s2)
    for idx in seen:
        pd.testing.assert_index_equal(idx, sidecar, exact=True)


def test_boundary_01_ic_readback_sidecar_missing_raises_named(fresh_s2: Dict[str, Any]) -> None:
    """Task 1.1 邊界①：raw sidecar 缺 ⇒ `RowIndexArtifactMissingError`。"""
    manifest = json.loads((fresh_s2["run_dir"] / "feature_manifest.json").read_text(encoding="utf-8"))
    (fresh_s2["run_dir"] / manifest["row_index"]["path"]).unlink()
    with pytest.raises(RowIndexArtifactMissingError):
        _ic(fresh_s2, h.forward_return_label())


def test_boundary_02_label_without_intersection_raises_alignment(s2: Dict[str, Any]) -> None:
    """Task 1.1 邊界②：label 時間戳與群組時間戳無交集 ⇒ `AlignmentViolationError`（不得靜默全 NaN）。"""
    label = h.forward_return_label()
    shifted = label.copy()
    shifted.index = shifted.index + pd.Timedelta(hours=3)  # 12h 格點外：與 sidecar 無交集
    with pytest.raises(AlignmentViolationError):
        _ic(s2, shifted, selection_window={"start": str(shifted.index.min()), "end": str(shifted.index.max())})


def test_boundary_03_empty_selection_window_keeps_empty_selection(s2: Dict[str, Any]) -> None:
    """Task 1.1 邊界③：選窗內無列（群組選後為空）⇒ 既有空選擇語意：無例外、無選中欄。"""
    label = h.forward_return_label()
    result = _ic(s2, label, selection_window={"start": "2030-01-01", "end": "2030-12-31"})
    assert result.selected == []


def test_boundary_04_split_id_only_semantics_unchanged(s2: Dict[str, Any]) -> None:
    """Task 1.1 邊界④：只給 split_id 不給 selection_window ⇒ 既有語意（全窗）不變。"""
    label = h.forward_return_label()
    full = _ic(s2, label).ic_scores
    only_split = ICEngine({"methods": ["spearman"]}).compute_ic_from_l7_raw(
        h.SYMBOL, h.PRIMARY, s2["config_hash"], label, feature_reader=s2["reader"], ic_threshold=0.0,
        label_horizon="1", split_id="split-a").ic_scores
    assert set(full) == set(only_split)
    assert np.allclose([full[c] for c in sorted(full)], [only_split[c] for c in sorted(full)],
                       rtol=0, atol=0, equal_nan=True)


@pytest.mark.parametrize("key", POSITIONAL_KEYS)
def test_positional_selection_key_rejected(s2: Dict[str, Any], key: str) -> None:
    """位置鍵選窗拒用（`start_pos`／`end_pos`／`start_index`／`end_index`）⇒ ValueError。"""
    with pytest.raises(ValueError):
        _ic(s2, h.forward_return_label(), selection_window={key: 0})


def test_mixed_positional_and_time_keys_rejected(s2: Dict[str, Any]) -> None:
    """位置鍵與時間鍵混用 ⇒ ValueError。"""
    with pytest.raises(ValueError):
        _ic(s2, h.forward_return_label(), selection_window={"start": "2025-01-01", "end_pos": 100})


def test_mutation_ic_readback_without_sidecar_index(s2: Dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    """omission mutant：IC 讀回不設 sidecar index（`ICEngine._attach_row_index` 改恆等）⇒ 拒用而非算出分數。"""
    monkeypatch.setattr(ICEngine, "_attach_row_index", staticmethod(lambda group_df, row_index: group_df))
    with pytest.raises(AlignmentViolationError):
        _ic(s2, h.forward_return_label())


def test_mutation_restore_reindex_branch_silently_all_nan(s2: Dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant：恢復 HEAD 之 reindex 分支 ⇒ 時間戳無交集之 label 不拋錯、IC 全 NaN（邊界② 之斷言因而翻轉）。"""
    monkeypatch.setattr(ICEngine, "_align_label_to_group", staticmethod(_head_align_label_to_group))
    label = h.forward_return_label()
    shifted = label.copy()
    shifted.index = shifted.index + pd.Timedelta(hours=3)
    result = _ic(s2, shifted, selection_window={"start": str(shifted.index.min()), "end": str(shifted.index.max())})
    assert all(not np.isfinite(v) for v in result.ic_scores.values())


def test_mutation_positional_key_accepted(s2: Dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant：恢復 HEAD 之 `_apply_selection_window`（收 start_pos）且不拒位置鍵 ⇒ 無 ValueError、算出結果。"""
    monkeypatch.setattr(ICEngine, "_apply_selection_window", staticmethod(_head_apply_selection_window))
    monkeypatch.setattr(ICEngine, "_reject_positional_selection", staticmethod(lambda selection_window: None))
    result = _ic(s2, h.forward_return_label(), selection_window={"start_pos": 0, "end_pos": 500})
    assert isinstance(result.ic_scores, dict)


# ---------------------------------------------------------------- Task 1.2 選欄讀回接時間軸

def test_selected_readback_index_equals_raw_sidecar(s2: Dict[str, Any]) -> None:
    cols = _all_raw_columns(s2)[:5]
    frame = s2["reader"].load_columns_v2(h.SYMBOL, h.PRIMARY, s2["config_hash"], cols, attach_row_index=True)
    pd.testing.assert_index_equal(frame.index, _sidecar(s2), exact=True)


def test_boundary_01_selected_no_match_returns_empty_with_empty_datetimeindex(s2: Dict[str, Any]) -> None:
    frame = s2["reader"].load_columns_v2(h.SYMBOL, h.PRIMARY, s2["config_hash"], ["__no_such_column__"],
                                         attach_row_index=True)
    assert frame.empty and isinstance(frame.index, pd.DatetimeIndex) and len(frame.index) == 0


def test_boundary_02_selected_sidecar_missing_raises_named(fresh_s2: Dict[str, Any]) -> None:
    manifest = json.loads((fresh_s2["run_dir"] / "feature_manifest.json").read_text(encoding="utf-8"))
    (fresh_s2["run_dir"] / manifest["row_index"]["path"]).unlink()
    with pytest.raises(RowIndexArtifactMissingError):
        fresh_s2["reader"].load_columns_v2(h.SYMBOL, h.PRIMARY, fresh_s2["config_hash"],
                                           _all_raw_columns(fresh_s2)[:3], attach_row_index=True)


def test_boundary_03_attach_false_bytes_equal_head(s2: Dict[str, Any]) -> None:
    """Task 1.2 邊界③：`attach_row_index=False` ⇒ 與 HEAD 讀法（pq 讀＋解碼＋concat）逐位元組相等。"""
    cols = _all_raw_columns(s2)[:5]
    got = s2["reader"].load_columns_v2(h.SYMBOL, h.PRIMARY, s2["config_hash"], cols, attach_row_index=False)
    manifest = s2["reader"].load_manifest_v2(h.SYMBOL, h.PRIMARY, s2["config_hash"], artifact_kind="raw")
    frames = []
    for info in manifest["artifacts"]["raw"]["groups"].values():
        need = [c for c in cols if c in set(info.get("columns", []))]
        if need:
            table = pq.read_table(str(s2["run_dir"] / "raw" / Path(info.get("path") or info.get("file")).name),
                                  columns=need)
            frames.append(s2["reader"]._decode_l7_encoded_table(table).to_pandas())
    expected = pd.concat(frames, axis=1)
    pd.testing.assert_frame_equal(got, expected, check_exact=True)
    assert isinstance(got.index, pd.RangeIndex)


def test_reversed_sidecar_triggers_time_order_guard(fresh_s2: Dict[str, Any]) -> None:
    """倒序 sidecar ⇒ `transform_selected` 之時間序守衛拋 ValueError。"""
    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

    manifest = json.loads((fresh_s2["run_dir"] / "feature_manifest.json").read_text(encoding="utf-8"))
    path = fresh_s2["run_dir"] / manifest["row_index"]["path"]
    table = pq.read_table(str(path))
    import pyarrow as pa

    reversed_ts = pa.array(table.column("timestamp").to_numpy()[::-1])
    pq.write_table(table.set_column(0, "timestamp", reversed_ts), str(path))
    frame = fresh_s2["reader"].load_columns_v2(h.SYMBOL, h.PRIMARY, fresh_s2["config_hash"],
                                               _all_raw_columns(fresh_s2)[:3], attach_row_index=True)
    with pytest.raises(ValueError):
        FeaturePreprocessor({"winsorization": {"enabled": False}}).transform_selected(list(frame.columns), {"g": frame})


def test_mutation_selected_readback_shifted_axis(s2: Dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    """omission mutant：選欄讀回接另一條同長嚴格遞增軸（sidecar 平移一根）⇒ exact equality 斷言失敗。"""
    real = FeatureReader.load_row_index_v2

    def shifted(self: FeatureReader, *args: Any, **kwargs: Any) -> pd.DatetimeIndex:
        return real(self, *args, **kwargs) + pd.Timedelta(hours=12)

    monkeypatch.setattr(FeatureReader, "load_row_index_v2", shifted)
    frame = s2["reader"].load_columns_v2(h.SYMBOL, h.PRIMARY, s2["config_hash"], _all_raw_columns(s2)[:3],
                                         attach_row_index=True)
    with pytest.raises(AssertionError):
        pd.testing.assert_index_equal(frame.index, _sidecar(s2), exact=True)


# ---------------------------------------------------------------- Task 1.3 processed 時間軸

def _processed_groups(run: Dict[str, Any], drop_head: int = 0) -> Tuple[Dict[str, pd.DataFrame], pd.DatetimeIndex]:
    cols = _all_raw_columns(run)[:4]
    frame = run["reader"].load_columns_v2(h.SYMBOL, h.PRIMARY, run["config_hash"], cols)
    axis = _sidecar(run)
    frame = frame.iloc[drop_head:].reset_index(drop=True)
    return {"sel": frame}, axis[drop_head:]


def _write_processed(run: Dict[str, Any], groups: Dict[str, pd.DataFrame], axis: pd.DatetimeIndex) -> None:
    FeatureStorage(str(run["root"])).write_processed(h.SYMBOL, h.PRIMARY, run["config_hash"], groups, row_index=axis)


def _root_fields(run: Dict[str, Any]) -> Dict[str, Any]:
    manifest = json.loads((run["run_dir"] / "feature_manifest.json").read_text(encoding="utf-8"))
    return {k: manifest.get(k) for k in ("time_range", "row_count", "row_index")}


def test_write_processed_keeps_root_time_range_row_count_row_index(fresh_s2: Dict[str, Any]) -> None:
    before = _root_fields(fresh_s2)
    groups, axis = _processed_groups(fresh_s2)
    _write_processed(fresh_s2, groups, axis)
    assert _root_fields(fresh_s2) == before


def test_processed_sidecar_equals_raw_rows(fresh_s2: Dict[str, Any]) -> None:
    groups, axis = _processed_groups(fresh_s2)
    _write_processed(fresh_s2, groups, axis)
    pd.testing.assert_index_equal(_sidecar(fresh_s2, "processed"), _sidecar(fresh_s2, "raw"), exact=True)


def test_processed_with_different_row_count_reads_own_sidecar(fresh_s2: Dict[str, Any]) -> None:
    groups, axis = _processed_groups(fresh_s2, drop_head=10)
    _write_processed(fresh_s2, groups, axis)
    got = fresh_s2["reader"].load_row_index_v2(h.SYMBOL, h.PRIMARY, fresh_s2["config_hash"], artifact_kind="processed")
    pd.testing.assert_index_equal(got, axis, exact=True)
    assert len(got) != len(_sidecar(fresh_s2, "raw"))


def _browse(run: Dict[str, Any], monkeypatch: pytest.MonkeyPatch):
    """Feature Factory 正式瀏覽接縫：`_load_task_context`（經 `get_result` 取 manifest 路徑）→ schema／欄／時間軸。"""
    from api.services.feature_factory_service import FeatureFactoryService

    service = FeatureFactoryService.__new__(FeatureFactoryService)
    manifest_path = run["run_dir"] / "feature_manifest.json"
    monkeypatch.setattr(service, "get_result", lambda task_id: {
        "hdf5_path": str(manifest_path),
        "metadata": {"symbol": h.SYMBOL, "timeframe": h.PRIMARY, "config_hash": run["config_hash"]}})
    context = service._load_task_context("probe-task")
    schema = service._load_hdf5_schema(context)
    df = service._load_cgsa_features_df(context)
    service._attach_cgsa_row_index(context, df)
    return schema, df


def test_browse_processed_columns_rows_and_axis_from_same_artifact(fresh_s2: Dict[str, Any],
                                                                   monkeypatch: pytest.MonkeyPatch) -> None:
    """審碼 b1 r1 codex P1-02：processed 列數異於 raw 時，正式瀏覽之欄、列數與時間軸皆取自 processed 節點
    （不得 processed 欄配 raw 列數／raw 軸）。"""
    groups, axis = _processed_groups(fresh_s2, drop_head=10)
    _write_processed(fresh_s2, groups, axis)
    schema, df = _browse(fresh_s2, monkeypatch)
    processed_cols = [c for frame in groups.values() for c in frame.columns]
    assert schema["row_count"] == len(axis) != len(_sidecar(fresh_s2, "raw"))
    assert sorted(schema["feature_names"]) == sorted(processed_cols)
    assert len(df) == len(axis)
    pd.testing.assert_index_equal(pd.DatetimeIndex(df.index), axis, check_names=False, exact=True)


def test_mutation_browse_reads_mixed_root(fresh_s2: Dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant：瀏覽不投影（直接用根）⇒ processed 欄配 raw 列數（上一測試之列數斷言翻轉）。"""
    from api.services.feature_factory_service import FeatureFactoryService

    groups, axis = _processed_groups(fresh_s2, drop_head=10)
    _write_processed(fresh_s2, groups, axis)
    monkeypatch.setattr(FeatureFactoryService, "_select_l7_v2_artifact", classmethod(lambda cls, m: (m, "raw")))
    service = FeatureFactoryService.__new__(FeatureFactoryService)
    monkeypatch.setattr(service, "get_result", lambda task_id: {
        "hdf5_path": str(fresh_s2["run_dir"] / "feature_manifest.json"),
        "metadata": {"symbol": h.SYMBOL, "timeframe": h.PRIMARY}})
    schema = service._load_hdf5_schema(service._load_task_context("probe-task"))
    assert schema["row_count"] == len(_sidecar(fresh_s2, "raw")) != len(axis)


def test_processed_axis_readable_after_cleanup_raw(fresh_s2: Dict[str, Any]) -> None:
    groups, axis = _processed_groups(fresh_s2)
    _write_processed(fresh_s2, groups, axis)
    shutil.rmtree(fresh_s2["run_dir"] / "raw")
    got = fresh_s2["reader"].load_row_index_v2(h.SYMBOL, h.PRIMARY, fresh_s2["config_hash"], artifact_kind="processed")
    pd.testing.assert_index_equal(got, axis, exact=True)


def test_boundary_01_processed_empty_selection_sidecar_len0(fresh_s2: Dict[str, Any]) -> None:
    """Task 1.3 邊界①：空選擇 ⇒ processed sidecar 長度 0、品質標記 empty_selection、raw 身分不變。"""
    before = _root_fields(fresh_s2)
    _write_processed(fresh_s2, {}, pd.DatetimeIndex([]))
    got = fresh_s2["reader"].load_row_index_v2(h.SYMBOL, h.PRIMARY, fresh_s2["config_hash"], artifact_kind="processed")
    assert len(got) == 0
    manifest = json.loads((fresh_s2["run_dir"] / "feature_manifest.json").read_text(encoding="utf-8"))
    assert manifest["artifacts"]["processed"]["quality_status"] == "empty_selection"
    assert _root_fields(fresh_s2) == before


def test_boundary_02_processed_row_index_length_mismatch_raises(fresh_s2: Dict[str, Any]) -> None:
    groups, axis = _processed_groups(fresh_s2)
    with pytest.raises(RowIndexLengthMismatchError):
        _write_processed(fresh_s2, groups, axis[:-1])


def test_boundary_03_raw_sidecar_format_unchanged(fresh_s2: Dict[str, Any]) -> None:
    """Task 1.3 邊界③：raw sidecar 格式不變（單欄 timestamp、int64 epoch 秒；根 row_index 之鍵不變）。"""
    manifest = json.loads((fresh_s2["run_dir"] / "feature_manifest.json").read_text(encoding="utf-8"))
    table = pq.read_table(str(fresh_s2["run_dir"] / manifest["row_index"]["path"]))
    assert table.column_names == ["timestamp"] and str(table.schema.field("timestamp").type) == "int64"
    keys_before = set(manifest["row_index"])
    groups, axis = _processed_groups(fresh_s2)
    _write_processed(fresh_s2, groups, axis)
    after = json.loads((fresh_s2["run_dir"] / "feature_manifest.json").read_text(encoding="utf-8"))
    assert set(after["row_index"]) == keys_before


def test_write_processed_requires_row_index(fresh_s2: Dict[str, Any]) -> None:
    groups, _ = _processed_groups(fresh_s2)
    with pytest.raises(TypeError):
        FeatureStorage(str(fresh_s2["root"])).write_processed(h.SYMBOL, h.PRIMARY, fresh_s2["config_hash"], groups)


def test_mutation_processed_overwrites_root_time_range(fresh_s2: Dict[str, Any],
                                                        monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant：恢復 HEAD 之「processed 寫入覆寫 manifest 根之 row_count／time_range」（實作之保護位於
    `_build_feature_manifest_v2`，故 mutant 於該處還原 HEAD 行為）⇒ 根欄位改變而被斷言抓到。

    實作後修訂（b1）：原 mutant 只替換 `write_processed`，而根欄位保護實作於 manifest 合併層，替換上層
    函式已無法還原 HEAD 行為；processed 軸亦改與 raw 列數不同（drop_head=10），使覆寫可觀測。
    """
    real_build = FeatureStorage._build_feature_manifest_v2

    def head_build(self: FeatureStorage, **kw: Any) -> Dict[str, Any]:
        manifest = real_build(self, **kw)
        if kw.get("artifact_kind") == "processed":
            manifest["row_count"] = kw["row_count"]
            manifest["time_range"] = kw["time_range"]
        return manifest

    before = _root_fields(fresh_s2)
    monkeypatch.setattr(FeatureStorage, "_build_feature_manifest_v2", head_build)
    groups, axis = _processed_groups(fresh_s2, drop_head=10)
    _write_processed(fresh_s2, groups, axis)
    assert _root_fields(fresh_s2) != before


def test_mutation_processed_reads_root_axis(fresh_s2: Dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    """omission mutant：讀回恢復 HEAD（不分 artifact_kind、退回根軸）⇒ 不同列數之 processed 軸不等而被抓到。"""
    groups, axis = _processed_groups(fresh_s2, drop_head=10)
    _write_processed(fresh_s2, groups, axis)
    monkeypatch.setattr(FeatureReader, "load_row_index_v2", _head_load_row_index_v2)
    got = fresh_s2["reader"].load_row_index_v2(h.SYMBOL, h.PRIMARY, fresh_s2["config_hash"], artifact_kind="processed")
    with pytest.raises(AssertionError):
        pd.testing.assert_index_equal(got, axis, exact=True)
