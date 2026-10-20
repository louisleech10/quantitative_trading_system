"""FFDSTAR Task 1.3（docs/FFDSTAR_SPEC.md）：raw 紀錄檔、內容身分與 manifest（單一提交點）。

受測物：`FeatureStorage.write_raw_from_registry_stream`／`_atomic_merge_feature_manifest_v2`／`_build_feature_manifest_v2`
與 `momentum/FeatureEngineering/run_provenance.py`。oracle 不讀紀錄自證：紀錄檔 sha256 測試端自算、`content_sha256`
以 `preprov_helpers.independent_content_sha256` 自讀檔重算、dead-drop 欄取自生成期觀測器。
真實 kline 短窗；故障注入與 mutation 一律另起根重生。實作前應為紅；不得以 skip／xfail 暫避。
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, List, Sequence

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from momentum.FeatureEngineering import run_provenance as rp
from tests.feature_engineering import preprov_helpers as ph

pytestmark = pytest.mark.requires_kline


@pytest.fixture(scope="module")
def runs(tmp_path_factory: pytest.TempPathFactory) -> ph.RunCache:
    return ph.RunCache(tmp_path_factory.mktemp("preprov_writer"))


# ---------------------------------------------------------------------------------------------- oracle

def exhaustive_violations(names: Sequence[str], group_cols: Sequence[str], dropped: Iterable[str]) -> List[str]:
    """② 紀錄輸出欄名集合＝manifest 群組欄聯集 ∪ dead-drop 欄，逐名、無重複。"""
    out: List[str] = []
    if len(names) != len(set(names)):
        out.append("紀錄輸出欄名重複")
    if len(group_cols) != len(set(group_cols)):
        out.append("manifest 群組欄重複")
    expected = set(group_cols) | set(dropped)
    if set(names) - expected:
        out.append(f"紀錄多出 {sorted(set(names) - expected)[:3]}")
    if expected - set(names):
        out.append(f"紀錄缺 {sorted(expected - set(names))[:3]}")
    return out


def record_file_violations(handle: ph.RunHandle, artifact_kind: str = "raw") -> List[str]:
    """① 紀錄檔存在、sha256（測試端自算）＝manifest 宣告、指標鍵＝契約、契約版本相符、列數相符、zstd、不列入特徵群組。"""
    spec = ph.contract()
    out: List[str] = []
    pointer = ph.provenance_pointer(handle.run_dir, artifact_kind)
    if sorted(pointer) != sorted(spec["manifest_provenance_keys"]):
        out.append(f"provenance 物件鍵 {sorted(pointer)} ≠ 契約")
    path = ph.provenance_file(handle.run_dir, artifact_kind)
    if not path.is_file():
        return out + [f"紀錄檔不存在 {path}"]
    if ph.sha256_file(path) != pointer["sha256"]:
        out.append("紀錄檔 sha256 ≠ manifest 宣告")
    if pointer["contract_version"] != spec["version"]:
        out.append("契約版本不符")
    meta = pq.ParquetFile(str(path)).metadata
    if meta.num_rows != pointer["row_count"]:
        out.append("列數 ≠ manifest 宣告")
    codecs = {meta.row_group(i).column(j).compression for i in range(meta.num_row_groups)
              for j in range(meta.num_columns)}
    if meta.num_row_groups and codecs != {str(spec["parquet_compression"]).upper()}:
        out.append(f"壓縮 {codecs} ≠ 契約")
    groups = ph.load_manifest(handle.run_dir)["artifacts"][artifact_kind]["groups"]
    if any(str(g.get("path", "")).startswith("provenance/") for g in groups.values()):
        out.append("紀錄檔被列入特徵群組")
    return out


def raw_complete_nodes(root: Path) -> List[str]:
    """root 下所有 manifest 中 raw 節點為完整者（故障注入後應為空）。"""
    out: List[str] = []
    for manifest_path in sorted(Path(root).rglob(ph.MANIFEST_NAME)):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        raw = (manifest.get("artifacts") or {}).get("raw")
        if isinstance(raw, dict) and raw.get("complete") and manifest.get("complete"):
            out.append(str(manifest_path))
    return out


def content_entries(run_dir: Path) -> List[rp.ContentEntry]:
    """自宣告群組檔（測試端讀檔）組 `ContentEntry`（同 `independent_content_sha256` 之組成）。"""
    out: List[rp.ContentEntry] = []
    for path in ph.declared_group_files(run_dir, "raw"):
        parquet = pq.ParquetFile(str(path))
        cols = [n for n in parquet.schema_arrow.names if n not in ph.NON_FEATURE_COLUMNS]
        out.append(rp.ContentEntry(relative_path=str(path.relative_to(run_dir)), columns=tuple(cols),
                                   row_count=int(parquet.metadata.num_rows),
                                   dtype=ph._file_dtype_summary(parquet.schema_arrow, cols),
                                   file_sha256=ph.sha256_file(path)))
    return out


def shifted_row_index_sha(run_dir: Path, tmp_path: Path) -> str:
    """只改時間軸：真實 row index 整體平移一根後另存之 sha256（值與欄不變）。"""
    rel = ph.row_index_rel(ph.load_manifest(run_dir), "raw")
    seconds = pq.read_table(str(run_dir / rel)).column("timestamp").to_numpy()
    step = int(seconds[1] - seconds[0])
    target = tmp_path / "shifted_timestamps.parquet"
    pq.write_table(pa.table({"timestamp": pa.array(seconds + step, type=pa.int64())}), str(target))
    return ph.sha256_file(target)


def time_axis_distinguished(compute: Any, run_dir: Path, tmp_path: Path) -> bool:
    entries = content_entries(run_dir)
    real = ph.sha256_file(run_dir / ph.row_index_rel(ph.load_manifest(run_dir), "raw"))
    return compute(entries, real) != compute(entries, shifted_row_index_sha(run_dir, tmp_path))


def _failing_provenance_writes(monkeypatch: pytest.MonkeyPatch) -> None:
    """模擬紀錄檔目錄唯讀：寫入路徑含 `provenance` 之 parquet 一律 PermissionError（其餘照常）。"""
    real = pq.write_table

    def write_table(table: Any, where: Any, *args: Any, **kwargs: Any) -> Any:
        if "provenance" in str(where):
            raise PermissionError(f"read-only provenance dir: {where}")
        return real(table, where, *args, **kwargs)

    monkeypatch.setattr(pq, "write_table", write_table)


# ---------------------------------------------------------------------------------------------- 驗證

def test_verification_01_record_file_exists_and_sha_matches(runs: ph.RunCache) -> None:
    """① 真實短窗生成後紀錄檔存在、sha256 等於 manifest 宣告（含指標鍵、版本、列數、zstd、不列入特徵群組）。"""
    assert record_file_violations(runs.get("h1_stat_on")) == []


def test_verification_02_exhaustive_by_name(runs: ph.RunCache) -> None:
    """② 窮盡性逐名：紀錄輸出欄名＝manifest 群組欄聯集 ∪ dead-drop 欄（dead-drop 取自觀測器），無重複。"""
    for cell in ("h1_stat_on", "dead_drop"):
        handle = runs.get(cell)
        table = ph.provenance_table(handle.run_dir, "raw")
        dropped = ph.observation(handle).l7_dropped
        assert exhaustive_violations(list(table["output_column"]), ph.group_columns(handle.run_dir, "raw"),
                                     dropped) == [], cell


def test_verification_03_content_sha_independent(runs: ph.RunCache) -> None:
    """③ manifest raw 節點之 `content_sha256`＝測試內自讀檔獨立重算；`compute_content_sha256` 對同組成亦相等。"""
    handle = runs.get("h1_stat_on")
    manifest = ph.load_manifest(handle.run_dir)
    independent = ph.independent_content_sha256(handle.run_dir, "raw")
    assert manifest["artifacts"]["raw"]["content_sha256"] == independent
    row_index_sha = ph.sha256_file(handle.run_dir / ph.row_index_rel(manifest, "raw"))
    assert rp.compute_content_sha256(content_entries(handle.run_dir), row_index_sha) == independent
    assert rp.file_sha256(handle.run_dir / ph.row_index_rel(manifest, "raw")) == row_index_sha


def test_verification_03b_time_axis_only_change_changes_content_sha(runs: ph.RunCache, tmp_path: Path) -> None:
    """③（續）只改時間軸（群組檔不變）⇒ `content_sha256` 不同（row index 入內容身分）。"""
    assert time_axis_distinguished(rp.compute_content_sha256, runs.get("h1_stat_off").run_dir, tmp_path)


def test_verification_04_record_write_failure_fails_run(tmp_path_factory: pytest.TempPathFactory,
                                                        monkeypatch: pytest.MonkeyPatch) -> None:
    """④ 紀錄檔寫入失敗（唯讀）⇒ 生成失敗、manifest 無完整 raw 節點。"""
    root = tmp_path_factory.mktemp("preprov_writer_fail")
    _failing_provenance_writes(monkeypatch)
    with pytest.raises(Exception):
        ph.generate_short_run(root, "h1_stat_off")
    assert raw_complete_nodes(root) == []


def test_verification_05_merge_failure_after_install_not_readable_complete(
        tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch) -> None:
    """⑤ 舊 run 完整存在時重生、於安裝後之 manifest 合併失敗 ⇒ 該 run 不可被 `consumer="strict"` 讀為完整（D4）。"""
    from momentum.FeatureEngineering.feature_reader import FeatureReader
    from momentum.FeatureEngineering.feature_storage import FeatureStorage

    root = tmp_path_factory.mktemp("preprov_writer_merge")
    first = ph.generate_short_run(root, "h1_stat_off")
    reader = FeatureReader(str(first.features_root))
    reader.load_manifest_v2(first.symbol, first.tf, first.config_hash, "raw", consumer="strict")  # 前提：舊 run 完整
    real = FeatureStorage._atomic_merge_feature_manifest_v2

    def failing_merge(self: Any, run_dir: Path, **kwargs: Any) -> Any:
        if kwargs.get("artifact_kind") == "raw" and kwargs.get("group_manifest"):
            raise OSError("injected manifest merge failure after raw install")
        return real(self, run_dir, **kwargs)

    monkeypatch.setattr(FeatureStorage, "_atomic_merge_feature_manifest_v2", failing_merge)
    with pytest.raises(Exception):
        ph.generate_short_run(root, "h1_stat_off")
    monkeypatch.undo()
    with pytest.raises((ValueError, FileNotFoundError, rp.ProvenanceError)):
        FeatureReader(str(first.features_root)).load_manifest_v2(first.symbol, first.tf, first.config_hash, "raw",
                                                                 consumer="strict")


@pytest.mark.parametrize("retain_source", [True, False], ids=["source_retained", "source_deleted"])
def test_verification_05b_rerun_rowindex_failure_restores_or_failcloses(
        tmp_path_factory: pytest.TempPathFactory, retain_source: bool) -> None:
    """⑤b（CODEX-R5-P1-01）：既有完整 run A 以同設定重跑（kline 複本改一根、row index 平移一根），於新 row index 寫出後、
    raw 之 `_atomic_merge_feature_manifest_v2` 前注入 `OSError` ⇒ raw/、`timestamps.parquet`、manifest 三者逐位元組回復為
    run A，或 run 不可被 `consumer="strict"` 讀為完整；且明確不得出現「舊 raw 位元組＋新時間軸」。來源未刪（回復分支，
    SPEC ⑥）與來源已刪（生產預設，fail-closed 分支）各一案。"""
    outcome = ph.rerun_with_injected_failure(tmp_path_factory.mktemp("preprov_writer_rerun"), "raw",
                                             retain_source=retain_source)
    assert outcome.before.artifact_files and outcome.before.row_index and outcome.before.manifest
    assert not (outcome.new_axis_on_disk and outcome.after.artifact_files == outcome.before.artifact_files)
    assert ph.rerun_failure_violations(outcome) == []


def test_verification_06_part_id_collision_raises(tmp_path_factory: pytest.TempPathFactory,
                                                  monkeypatch: pytest.MonkeyPatch) -> None:
    """⑥ 群組 part id 寫入 `group_manifest` 前碰撞 ⇒ 拋錯（不得覆寫）；生成失敗、無完整 raw 節點。"""
    from momentum.FeatureEngineering.feature_storage import FeatureStorage

    root = tmp_path_factory.mktemp("preprov_writer_collide")
    real = FeatureStorage.__dict__["_split_large_group"].__func__

    def colliding(cls: Any, group_id: str, columns: List[str], data: Any) -> Any:
        return [("collide_part", cols, part) for _pid, cols, part in real(cls, group_id, columns, data)]

    monkeypatch.setattr(FeatureStorage, "_split_large_group", classmethod(colliding))
    with pytest.raises((rp.ProvenanceError, ValueError)):
        ph.generate_short_run(root, "h1_stat_off")
    assert raw_complete_nodes(root) == []


# ---------------------------------------------------------------------------------------------- 邊界

def test_boundary_01_dead_drop_rows(runs: ph.RunCache) -> None:
    """邊界①：dead-drop 開啟且有被剔欄——被剔欄各一列、`group_id`＝來源群組 id、終態為單一契約值且不同於保留欄之終態。"""
    spec = ph.contract()
    handle = runs.get("dead_drop")
    dropped = ph.observation(handle).l7_dropped
    table = ph.provenance_table(handle.run_dir, "raw").set_index("output_column")
    assert dropped and set(dropped) <= set(table.index)
    assert all(table.loc[n, "group_id"] == g for n, g in dropped.items())
    dead_terminals = set(table.loc[sorted(dropped), "terminal"])
    kept_terminals = set(table.loc[sorted(set(table.index) - set(dropped)), "terminal"])
    assert len(dead_terminals) == 1 and dead_terminals <= set(ph.contract_values("terminal_values", spec))
    assert not dead_terminals & kept_terminals


def test_boundary_02_multi_tf_same_name_distinguished(runs: ph.RunCache) -> None:
    """邊界②：多週期 run——同名不同週期之 L6.5 欄以落盤名區分：每個 (週期, 欄) 恰對一列、`native_timeframe`＝其週期。"""
    handle = runs.get("h12h1_multi")
    obs = ph.observation(handle)
    table = ph.provenance_table(handle.run_dir, "raw")
    assert table["output_column"].is_unique
    indexed = table.set_index("output_column")
    by_tf: dict = {}
    for cols, _a, tf, _l in obs.l65_inputs.values():
        for col in cols:
            by_tf.setdefault(col, set()).add(tf)
            assert indexed.loc[ph.output_name(col, tf), "native_timeframe"] == tf
    assert any(len(tfs) > 1 for tfs in by_tf.values()), "無同名不同週期之欄 ⇒ 邊界空轉"
    assert exhaustive_violations(list(table["output_column"]), ph.group_columns(handle.run_dir, "raw"),
                                 obs.l7_dropped) == []


def test_boundary_03_multi_symbol_worker(runs: ph.RunCache) -> None:
    """邊界③：多標的 worker 路徑——兩標的各自之紀錄檔 sha 相符、窮盡（該格 dead-drop 關閉）、內容身分獨立重算相等。"""
    for handle in runs.all_of("multi_symbol"):
        manifest = ph.load_manifest(handle.run_dir)
        assert int(manifest["generation_metadata"]["dead_dropped_cols"]) == 0
        assert record_file_violations(handle) == [], handle.symbol
        table = ph.provenance_table(handle.run_dir, "raw")
        assert exhaustive_violations(list(table["output_column"]), ph.group_columns(handle.run_dir, "raw"), ()) == []
        assert manifest["artifacts"]["raw"]["content_sha256"] == ph.independent_content_sha256(handle.run_dir, "raw")


def test_boundary_04_stationarity_off(runs: ph.RunCache) -> None:
    """邊界④：平穩化關閉——紀錄檔照常寫且 sha 相符、窮盡、平穩化決策欄全 null、縮尾狀態仍逐欄有值。"""
    handle = runs.get("h1_stat_off")
    assert record_file_violations(handle) == []
    table = ph.provenance_table(handle.run_dir, "raw")
    assert exhaustive_violations(list(table["output_column"]), ph.group_columns(handle.run_dir, "raw"),
                                 ph.observation(handle).l7_dropped) == []
    assert all(table[c].isna().all() for c in ph.STATIONARITY_DECISION_COLUMNS)
    assert table["winsorization"].notna().all()


def _empty_provenance_dirs(root: Path) -> List[str]:
    """root 下名為 `provenance` 之空目錄（安裝失敗後不得殘留）。"""
    return sorted(str(p) for p in Path(root).rglob("provenance") if p.is_dir() and not any(p.iterdir()))


@pytest.mark.parametrize("retain_source", [False, True], ids=["source_deleted", "source_retained"])
def test_boundary_05_provenance_install_failure_leaves_no_empty_dir(
        tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch, retain_source: bool) -> None:
    """邊界⑤（b4 盤點 §5 順帶發現）：新 run 之紀錄檔自暫存根安裝至 run 根（`_install_staged_run_files` 之 `os.replace`）
    失敗 ⇒ 生成失敗、run 根不殘留安裝時新建之空 `provenance/` 目錄，且 run 不可被 `consumer="strict"` 讀為完整。
    來源已刪（生產預設，不回復分支）與來源未刪（回復分支）各一案；注入點須恰觸發一次（防空轉）。"""
    import os

    from momentum.FeatureEngineering.feature_reader import FeatureReader
    from momentum.FeatureEngineering.feature_storage import FeatureStorage

    root = tmp_path_factory.mktemp("preprov_writer_prov_install")
    real_replace = os.replace
    injected: List[str] = []
    idents: List[tuple] = []

    def replace(src: Any, dst: Any, *args: Any, **kwargs: Any) -> Any:
        source = Path(str(src))
        if source.parent.name == "provenance" and source.parent.parent.name.startswith(".tmp-raw-"):
            injected.append(str(dst))
            raise OSError(f"injected provenance install failure: {dst}")
        return real_replace(src, dst, *args, **kwargs)

    real_entry = FeatureStorage.write_raw_from_registry_stream

    def entry(self: Any, symbol: str, tf: str, config_hash: str, *args: Any, **kwargs: Any) -> Any:
        idents.append((Path(self.base_path), symbol, tf, config_hash, self.feature_run_dir(symbol, tf, config_hash)))
        if retain_source:
            kwargs["cleanup_intermediate"] = False
        return real_entry(self, symbol, tf, config_hash, *args, **kwargs)

    monkeypatch.setattr(FeatureStorage, "write_raw_from_registry_stream", entry)
    monkeypatch.setattr(os, "replace", replace)
    with pytest.raises(Exception):
        ph.generate_short_run(root, "h1_stat_off")
    monkeypatch.undo()
    assert len(injected) == 1, injected
    assert len(idents) == 1, idents
    base, symbol, tf, config_hash, run_dir = idents[0]
    assert not (run_dir / "provenance").exists(), "安裝失敗後 run 根殘留安裝時新建之 provenance/"
    assert _empty_provenance_dirs(root) == []
    assert raw_complete_nodes(root) == []
    with pytest.raises((ValueError, FileNotFoundError, rp.ProvenanceError)):
        FeatureReader(str(base)).load_manifest_v2(symbol, tf, config_hash, "raw", consumer="strict")


# ---------------------------------------------------------------------------------------------- mutation

def test_mutation_content_sha_without_row_index(runs: ph.RunCache, monkeypatch: pytest.MonkeyPatch,
                                                tmp_path: Path) -> None:
    """mutation（SPEC Task 1.3）：`content_sha256` 漏 row index ⇒ 只改時間軸之案（③ 續）轉紅。"""
    run_dir = runs.get("h1_stat_off").run_dir
    real = rp.compute_content_sha256
    assert time_axis_distinguished(rp.compute_content_sha256, run_dir, tmp_path)
    monkeypatch.setattr(rp, "compute_content_sha256", lambda entries, row_index_sha256: real(entries, "0" * 64))
    assert not time_axis_distinguished(rp.compute_content_sha256, run_dir, tmp_path)


def test_mutation_record_write_swallows_exception(tmp_path_factory: pytest.TempPathFactory,
                                                  monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation（SPEC Task 1.3）：紀錄檔寫入改為吞例外 ⇒ ④ 轉紅（寫入失敗而生成照常成功、留下完整 raw 節點）。"""
    spec = ph.contract()
    real = rp.write_provenance_table

    def swallowing(table: Any, staging_dir: Path, artifact_kind: str, groups: Any) -> Any:
        try:
            return real(table, staging_dir, artifact_kind, groups)
        except Exception:  # noqa: BLE001 — 改壞之版本：吞例外並回假指標
            return rp.ProvenancePointer(path=spec["files"][artifact_kind], sha256=hashlib.sha256(b"").hexdigest(),
                                        row_count=int(len(table)), contract_version=int(spec["version"]),
                                        summary={}, groups=dict(groups))

    monkeypatch.setattr(rp, "write_provenance_table", swallowing)
    _failing_provenance_writes(monkeypatch)
    root = tmp_path_factory.mktemp("preprov_writer_swallow")
    ph.generate_short_run(root, "h1_stat_off")
    assert raw_complete_nodes(root) != []


def test_mutation_rowindex_direct_write_without_restore(tmp_path_factory: pytest.TempPathFactory,
                                                        monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation（CODEX-R5-P1-01）：寫入端改為新時間軸直寫 run 根之 `timestamps.parquet`、不備份不回復（改前碼之行為；
    monkeypatch 寫入端入口於失敗後直寫）⇒ ⑤b 之 oracle 轉紅，且紅因為「舊 raw＋新時間軸」錯配。取來源未刪之回復分支
    （來源已刪分支不回復 raw，直寫與正確行為等價、無從區分）。"""
    from momentum.FeatureEngineering.feature_storage import FeatureStorage

    monkeypatch.setattr(FeatureStorage, "write_raw_from_registry_stream",
                        ph.legacy_direct_axis_writer(FeatureStorage.write_raw_from_registry_stream, "timestamps.parquet"))
    outcome = ph.rerun_with_injected_failure(tmp_path_factory.mktemp("preprov_writer_rerun_mutant"), "raw",
                                             retain_source=True)
    assert outcome.new_axis_on_disk
    violations = ph.rerun_failure_violations(outcome)
    assert any("錯配" in v for v in violations), violations
