"""FFDSTAR／PRE-PROV b4（docs/FFDSTAR_SPEC.md §G 證法、Task 3.1）：結構重凍工具 `scripts/preprov_refreeze.py` 之剝除／
雜湊／收尾邏輯，與 `scripts/_manifest_listing.declared_run_snapshot_files` 之紀錄檔宣告（b4 F）。

只用合成 manifest JSON 與佔位檔驗「剝除與雜湊」及列檔守衛之邏輯（不涉任何特徵值；真實 run 之重凍由工具本身於真實 kline
上執行）。期望值一律於測試內以 canonical JSON 獨立重算，不呼叫受測之雜湊組裝函式自證。
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Dict

import pytest

from scripts import _manifest_listing as ml
from scripts import freeze_failopen_baseline as fo
from scripts import freeze_framepath_baseline as fpb
from scripts import preprov_refreeze as pr

RUN_REL = "BTCUSDT/1h/abc/feature_manifest.json"


def _canon(obj: Any) -> str:
    """獨立重算之 canonical sha256（同 framepath 凍結之定義：sort_keys、(",", ":")、ensure_ascii=False）。"""
    text = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _old_manifest(created: str = "2026-10-01T00:00:00") -> Dict[str, Any]:
    return {
        "created_at": created, "updated_at": created, "config_hash": "abc", "complete": True,
        "generation_metadata": {"source_registry_manifest": "/tmp/x/manifest.json", "n": 1},
        "artifacts": {"raw": {"complete": True, "groups": {"g": {"path": "raw/g.parquet", "columns": ["a"]}},
                              "metadata": {"source_registry_manifest": "/tmp/x/manifest.json"}}},
    }


def _new_manifest(**kw: Any) -> Dict[str, Any]:
    m = _old_manifest(**kw)
    m["artifacts"]["raw"]["content_sha256"] = "c" * 64
    m["artifacts"]["raw"]["provenance"] = {"path": "provenance/raw_columns.parquet", "sha256": "d" * 64,
                                           "row_count": 1, "contract_version": 1, "summary": {}, "groups": {}}
    return m


def _frozen_value(manifest: Dict[str, Any]) -> str:
    """改前之凍結值（獨立：手動剔除 compare_domain 之四個時間戳／絕對路徑鍵後 canonical）。"""
    m = copy.deepcopy(manifest)
    for key in ("created_at", "updated_at"):
        m.pop(key)
    m["generation_metadata"].pop("source_registry_manifest")
    m["artifacts"]["raw"]["metadata"].pop("source_registry_manifest")
    return _canon({RUN_REL: m})


@pytest.fixture(scope="module")
def domain() -> Dict[str, Any]:
    return fpb.load_compare_domain()


def _fp(manifest_sha: str, **over: Any) -> Dict[str, Any]:
    fp = {"column_names_sha256": "n", "column_count": 1, "row_count": 3, "time_index_sha256": "t",
          "columns": {"a": {"values": "v"}}, "result_columns": {"names_sha256": "r", "columns": {}},
          "stationarity_decisions_sha256": "s", "manifest_sha256": manifest_sha, "run_status": "complete",
          "completeness": {}, "failure_reasons": [], "path_receipt": {"manifests": [RUN_REL]}}
    fp.update(over)
    return fp


# ---------------------------------------------------------------------------------------------- 剝除（framepath）

def test_strip_manifest_removes_only_new_keys() -> None:
    new = _new_manifest()
    before = copy.deepcopy(new)
    assert pr.strip_manifest(new) == _old_manifest()
    assert new == before, "剝除不得改動輸入"


def test_framepath_stripped_equals_frozen_across_timestamps(domain: Dict[str, Any]) -> None:
    """改後 manifest（時間戳不同、多兩新鍵）剝除後依原算法重算＝改前凍結值；全值≠凍結值；差異路徑恰為兩新鍵。"""
    frozen = _frozen_value(_old_manifest())
    stripped, full, diffs = pr.framepath_manifest_values({RUN_REL: _new_manifest(created="2026-10-20T01:02:03")},
                                                         domain)
    assert stripped == frozen
    assert full != frozen and full == _frozen_value(_new_manifest())
    assert sorted(diffs) == [f"{RUN_REL}#artifacts.raw.content_sha256", f"{RUN_REL}#artifacts.raw.provenance"]
    assert all(pr.is_structural_manifest_path(p) for p in diffs)


def test_framepath_item_equal_and_new_value(domain: Dict[str, Any]) -> None:
    frozen = _frozen_value(_old_manifest())
    new = _new_manifest()
    full = _frozen_value(new)
    item = pr.framepath_item("C1", _fp(frozen), _fp(full), {RUN_REL: new}, domain)
    assert item["equal"] is True and item["changed"] is True
    assert (item["frozen_before"], item["stripped_recomputed"], item["new_value"]) == (frozen, frozen, full)
    assert item["other_diffs"] == []


def test_framepath_item_other_change_not_equal(domain: Dict[str, Any]) -> None:
    """manifest 另多非新鍵之鍵 ⇒ 剝除值≠凍結值；其他 fingerprint 項不同、或盤上全值≠子行程值、或記憶體閘錯 ⇒ 不等。"""
    frozen = _frozen_value(_old_manifest())
    extra = _new_manifest()
    extra["generation_metadata"]["new_flag"] = 1
    item = pr.framepath_item("C1", _fp(frozen), _fp(_frozen_value(extra)), {RUN_REL: extra}, domain)
    assert item["equal"] is False and item["stripped_recomputed"] != frozen and item["other_diffs"] == []
    new = _new_manifest()
    item = pr.framepath_item("C1", _fp(frozen), _fp(_frozen_value(new), row_count=4), {RUN_REL: new}, domain)
    assert item["equal"] is False and any(d.startswith("row_count") for d in item["other_diffs"])
    item = pr.framepath_item("C1", _fp(frozen), _fp("0" * 64), {RUN_REL: new}, domain)
    assert item["equal"] is False
    item = pr.framepath_item("C1", _fp(frozen), _fp(frozen), {RUN_REL: _old_manifest()}, domain,
                             memory_errors=["C1：峰值過高"])
    assert item["equal"] is False


def test_framepath_item_without_feature_manifest_must_be_unchanged(domain: Dict[str, Any]) -> None:
    """無落盤 feature manifest 之格（C7 registry、C9 拒絕）：值須原樣（不變即 equal、變則不等）。"""
    assert pr.framepath_item("C9", _fp("z"), _fp("z"), None, domain)["equal"] is True
    assert pr.framepath_item("C9", _fp("z"), _fp("y"), None, domain)["equal"] is False


def test_mutation_strip_misses_key_not_equal(domain: Dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation：剝除漏一個新鍵（`provenance`）⇒ 剝除值≠凍結值 ⇒ equal=false。"""
    frozen = _frozen_value(_old_manifest())
    new = _new_manifest()
    assert pr.framepath_item("C1", _fp(frozen), _fp(_frozen_value(new)), {RUN_REL: new}, domain)["equal"] is True
    monkeypatch.setattr(pr, "STRIPPED_KEYS", ("content_sha256",))
    item = pr.framepath_item("C1", _fp(frozen), _fp(_frozen_value(new)), {RUN_REL: new}, domain)
    assert item["equal"] is False and item["stripped_recomputed"] != frozen


# ---------------------------------------------------------------------------------------------- failopen

def _entries(prov: bool = False, manifest_sha: str = "m" * 64) -> Dict[str, Any]:
    files = [{"root": "registry", "path": ".align.npy", "size": 8, "sha256": "1" * 64},
             {"root": "registry", "path": "manifest.json", "size": 9, "sha256": manifest_sha},
             {"root": "abc", "path": "feature_manifest.json", "size": 10, "sha256": manifest_sha},
             {"root": "abc", "path": "raw/g.parquet", "size": 11, "sha256": "2" * 64}]
    if prov:
        files.append({"root": "abc", "path": "provenance/raw_columns.parquet", "size": 12, "sha256": "3" * 64})
    blob = json.dumps(files, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return {"files": files, "file_count": len(files), "aggregate_sha256": hashlib.sha256(blob).hexdigest()}


def _record(artifacts: Dict[str, Any], **over: Any) -> Dict[str, Any]:
    rec = {"merged_L7": {"canonical_sha256": "L"}, "group_set_sha256": "G", "feature_count": 5,
           "config_hash": "abc", "artifacts": artifacts}
    rec.update(over)
    return rec


def test_failopen_strip_and_entrywise_equal() -> None:
    """改後清單多 `provenance/` 項、兩 manifest 位元組不同（時間戳）⇒ 剝除後逐項等於凍結；aggregate 依原算法重算。"""
    frozen, fresh = _entries(), _entries(prov=True, manifest_sha="n" * 64)
    stripped = pr.strip_artifacts(fresh)
    assert stripped["file_count"] == 4
    assert stripped["aggregate_sha256"] == fo._sha256_json(stripped["files"])
    item = pr.failopen_item("BTCUSDT/multi", _record(frozen), _record(fresh))
    assert item["equal"] is True and item["new_value"]["file_count"] == 5
    assert set(item["diff_paths"]) == {"abc/provenance/raw_columns.parquet", "abc/feature_manifest.json",
                                       "registry/manifest.json"}
    assert item["_artifacts"] == fresh


def test_failopen_data_or_value_change_not_equal() -> None:
    frozen = _entries()
    changed = _entries(prov=True)
    changed["files"][3]["sha256"] = "9" * 64
    assert pr.failopen_item("BTCUSDT/multi", _record(frozen), _record(changed))["equal"] is False
    assert pr.failopen_item("BTCUSDT/multi", _record(frozen),
                            _record(_entries(prov=True), feature_count=6))["equal"] is False
    extra = _entries(prov=True)
    extra["files"].append({"root": "abc", "path": "raw/x.parquet", "size": 1, "sha256": "4" * 64})
    assert pr.failopen_item("BTCUSDT/multi", _record(frozen), _record(extra))["equal"] is False
    assert pr.failopen_item("BTCUSDT/multi", _record(_entries(prov=True)),
                            _record(_entries(prov=True)))["equal"] is False, "凍結清單已含 provenance 項 ⇒ 拒"


def test_mutation_failopen_strip_misses_provenance(monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation：剝除未剔 `provenance/` 項 ⇒ 逐項比多檔 ⇒ equal=false。"""
    monkeypatch.setattr(pr, "PROVENANCE_DIR", "no-such-dir")
    assert pr.failopen_item("BTCUSDT/multi", _record(_entries()), _record(_entries(prov=True)))["equal"] is False


# ---------------------------------------------------------------------------------------------- 收尾（寫檔）

def _framepath_doc(manifest_sha: str) -> Dict[str, Any]:
    return {"schema": "framepath-cgsa-fingerprint/1", "cells": {"C1": {"fingerprint": _fp(manifest_sha),
                                                                       "memory": {}, "receipt": {}}}}


def test_finalize_mismatch_writes_no_golden(tmp_path: Path, domain: Dict[str, Any]) -> None:
    """任一項不等 ⇒ rc=1、凍結檔位元組不變、收據段 written=false、exit_code=1。"""
    golden = tmp_path / "golden.json"
    golden.write_text(pr.framepath_dumps(_framepath_doc("old")), encoding="utf-8")
    before = golden.read_bytes()
    item = pr.framepath_item("C1", _fp("old"), _fp("x"), {RUN_REL: _new_manifest()}, domain)
    assert item["equal"] is False
    receipt_path = tmp_path / "receipt.json"
    rc = pr.finalize("framepath", golden, pr.FRAMEPATH_REL, before, "h" * 40, [item], "cmd",
                     pr.load_receipt(receipt_path), receipt_path)
    assert rc == 1 and golden.read_bytes() == before
    section = json.loads(receipt_path.read_text(encoding="utf-8"))["files"][0]
    assert (section["written"], section["exit_code"], section["sha256_after"]) == \
        (False, 1, hashlib.sha256(before).hexdigest())


def test_finalize_equal_rewrites_only_structural_field(tmp_path: Path, domain: Dict[str, Any]) -> None:
    frozen = _frozen_value(_old_manifest())
    new = _new_manifest()
    golden = tmp_path / "golden.json"
    golden.write_text(pr.framepath_dumps(_framepath_doc(frozen)), encoding="utf-8")
    before = golden.read_bytes()
    item = pr.framepath_item("C1", _fp(frozen), _fp(_frozen_value(new)), {RUN_REL: new}, domain)
    receipt_path = tmp_path / "receipt.json"
    rc = pr.finalize("framepath", golden, pr.FRAMEPATH_REL, before, "h" * 40, [item], "cmd",
                     pr.load_receipt(receipt_path), receipt_path)
    assert rc == 0
    after = json.loads(golden.read_text(encoding="utf-8"))
    expected = _framepath_doc(frozen)
    expected["cells"]["C1"]["fingerprint"]["manifest_sha256"] = _frozen_value(new)
    assert after == expected
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    section = receipt["files"][0]
    assert receipt["schema_version"] == 1 and section["written"] is True and section["exit_code"] == 0
    assert section["sha256_before"] == hashlib.sha256(before).hexdigest()
    assert section["sha256_after"] == hashlib.sha256(golden.read_bytes()).hexdigest()
    assert set(section["items"][0]) >= {"frozen_before", "stripped_recomputed", "equal", "new_value", "diff_paths"}


# ---------------------------------------------------------------------------------------------- F：紀錄檔宣告

def _run_dir(tmp_path: Path, *, pointer: Any = "provenance/raw_columns.parquet", prov_file: bool = True) -> Path:
    run = tmp_path / "run"
    (run / "raw").mkdir(parents=True)
    (run / "raw" / "g.parquet").write_bytes(b"g")
    (run / "timestamps.parquet").write_bytes(b"t")
    node: Dict[str, Any] = {"path": "raw", "groups": {"g": {"path": "raw/g.parquet"}}}
    if pointer is not None:
        node["provenance"] = {"path": pointer}
    manifest = {"row_index": {"path": "timestamps.parquet"}, "artifacts": {"raw": node}}
    (run / ml.MANIFEST_NAME).write_text(json.dumps(manifest), encoding="utf-8")
    if prov_file:
        (run / "provenance").mkdir()
        (run / "provenance" / "raw_columns.parquet").write_bytes(b"p")
    return run


def test_snapshot_includes_declared_provenance(tmp_path: Path) -> None:
    run = _run_dir(tmp_path)
    rels = [str(p.relative_to(run)) for p in ml.declared_run_snapshot_files(run)]
    assert rels == sorted(["feature_manifest.json", "provenance/raw_columns.parquet", "raw/g.parquet",
                           "timestamps.parquet"])
    assert ml.declared_feature_files_of_run(run) == [run / "raw" / "g.parquet", run / "timestamps.parquet"]


def test_snapshot_legacy_run_unchanged(tmp_path: Path) -> None:
    """舊 run（無 provenance 宣告、無紀錄檔）⇒ 快照集合不含紀錄檔（與改前同）。"""
    run = _run_dir(tmp_path, pointer=None, prov_file=False)
    rels = [str(p.relative_to(run)) for p in ml.declared_run_snapshot_files(run)]
    assert rels == ["feature_manifest.json", "raw/g.parquet", "timestamps.parquet"]


def test_snapshot_undeclared_provenance_raises(tmp_path: Path) -> None:
    """紀錄檔存在但 manifest 未宣告、或宣告外多一個 provenance 檔 ⇒ ValueError（守衛照舊）。"""
    with pytest.raises(ValueError):
        ml.declared_run_snapshot_files(_run_dir(tmp_path / "a", pointer=None))
    run = _run_dir(tmp_path / "b")
    (run / "provenance" / "extra.parquet").write_bytes(b"x")
    with pytest.raises(ValueError):
        ml.declared_run_snapshot_files(run)


def test_snapshot_bad_provenance_pointer(tmp_path: Path) -> None:
    """宣告路徑不在 provenance/ 下或逃逸 ⇒ ValueError；宣告檔不存在 ⇒ FileNotFoundError。"""
    with pytest.raises(ValueError):
        ml.declared_run_snapshot_files(_run_dir(tmp_path / "a", pointer="raw/g.parquet"))
    with pytest.raises(ValueError):
        ml.declared_run_snapshot_files(_run_dir(tmp_path / "b", pointer="../x.parquet"))
    with pytest.raises(FileNotFoundError):
        ml.declared_run_snapshot_files(_run_dir(tmp_path / "c", prov_file=False))


def test_failopen_artifact_hashes_include_declared_provenance(tmp_path: Path) -> None:
    """failopen 快照（`_artifact_hashes`）含宣告之紀錄檔項（重凍新值之結構即此）。"""
    run = _run_dir(tmp_path)
    paths = [e["path"] for e in fo._artifact_hashes(run)["files"]]
    assert "provenance/raw_columns.parquet" in paths

# ------------------------------------------------------------------------- registry 工作目錄：整組全死之源頭釋放（b4 failopen 實跑）

def _registry_dir(tmp_path: Path, groups: Dict[str, Dict[str, Any]]) -> Path:
    """registry 工作目錄：`groups`＝group_id → {npy（是否留檔）, parquet_path}。"""
    work = tmp_path / "registry"
    work.mkdir(parents=True)
    payload = []
    for gid, spec in groups.items():
        npy = f"{gid}.npy"
        if spec.get("npy", True):
            (work / npy).write_bytes(b"n")
        payload.append({"group_id": gid, "columns": ["c"], "npy_path": npy, "shards": [],
                        "alignment": None, "parquet_path": spec.get("parquet_path")})
    (work / ml.REGISTRY_MANIFEST_NAME).write_text(json.dumps({"groups": payload}), encoding="utf-8")
    return work


def _set_prov_groups(run: Path, groups: Dict[str, str]) -> None:
    """於 `_run_dir` 之 raw 節點紀錄指標寫入群組表（group_id → status）。"""
    manifest = json.loads((run / ml.MANIFEST_NAME).read_text(encoding="utf-8"))
    manifest["artifacts"]["raw"]["provenance"]["groups"] = {
        gid: {"arm": "native_tf", "fallback": [], "status": status, "failure_reason": None}
        for gid, status in groups.items()
    }
    (run / ml.MANIFEST_NAME).write_text(json.dumps(manifest), encoding="utf-8")


def test_registry_all_dead_group_release_accepted(tmp_path: Path) -> None:
    """整組全死群組（同 run 紀錄群組表狀態 all_dead_dropped）⇒ 源頭 npy 缺而未綁 parquet 仍屬合法釋放。"""
    work = _registry_dir(tmp_path, {"12h_L1_pattern_A": {"npy": False}, "12h_L1_pattern_B": {}})
    rels = [p.name for p in ml.declared_registry_files(work, {"12h_L1_pattern_A"})]
    assert rels == sorted([ml.REGISTRY_MANIFEST_NAME, "12h_L1_pattern_B.npy"])


def test_registry_missing_npy_not_released_raises(tmp_path: Path) -> None:
    """缺檔群組不在整組全死集合（他群組在、空集合、未給）⇒ 仍 FileNotFoundError（不放寬其他缺檔）。"""
    work = _registry_dir(tmp_path, {"12h_L1_pattern_A": {"npy": False}})
    for released in ({"12h_L1_pattern_B"}, set(), None):
        with pytest.raises(FileNotFoundError):
            ml.declared_registry_files(work, released)


def test_registry_parquet_bound_release_unchanged(tmp_path: Path) -> None:
    """已綁 parquet_path 之群組（L7 落盤後釋放）缺 npy 照舊合法，與整組全死集合無關。"""
    work = _registry_dir(tmp_path, {"1h_L1_trend_EMA": {"npy": False, "parquet_path": "/x/raw/g.parquet"}})
    assert [p.name for p in ml.declared_registry_files(work)] == [ml.REGISTRY_MANIFEST_NAME]


def test_all_dead_groups_of_run_reads_only_all_dead_status(tmp_path: Path) -> None:
    """只取狀態恰為 all_dead_dropped 之群組；無紀錄指標之舊 run ⇒ 空集合；群組表非物件 ⇒ ValueError。"""
    run = _run_dir(tmp_path / "a")
    _set_prov_groups(run, {"g1": "all_dead_dropped", "g2": "ok", "g3": "ratio_unsafe_passthrough"})
    assert ml.all_dead_groups_of_run(run) == {"g1"}
    assert ml.all_dead_groups_of_run(_run_dir(tmp_path / "b", pointer=None, prov_file=False)) == set()
    bad = _run_dir(tmp_path / "c")
    manifest = json.loads((bad / ml.MANIFEST_NAME).read_text(encoding="utf-8"))
    manifest["artifacts"]["raw"]["provenance"]["groups"] = ["g1"]
    (bad / ml.MANIFEST_NAME).write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError):
        ml.all_dead_groups_of_run(bad)


def test_combined_hashes_use_l7_run_all_dead_groups(tmp_path: Path) -> None:
    """failopen 多週期快照：registry 之整組全死缺檔以同組 L7 run 紀錄群組表認定（實跑反例之回歸：多週期 run 之
    generation_metadata 無 column_set_reasons，唯一來源為紀錄群組表）。"""
    work = _registry_dir(tmp_path / "w", {"12h_L1_pattern_A": {"npy": False}})
    run = _run_dir(tmp_path / "r")
    _set_prov_groups(run, {"12h_L1_pattern_A": "all_dead_dropped"})
    paths = [e["path"] for e in fo._combined_artifact_hashes(work, run)["files"]]
    assert ml.REGISTRY_MANIFEST_NAME in paths and "provenance/raw_columns.parquet" in paths
    _set_prov_groups(run, {"12h_L1_pattern_A": "ok"})
    with pytest.raises(FileNotFoundError):
        fo._combined_artifact_hashes(work, run)
