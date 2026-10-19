"""FFDSTAR Task 1.5（docs/FFDSTAR_SPEC.md）：紀錄讀取函式 `FeatureReader.load_provenance_v2`。

受測物：`momentum/FeatureEngineering/feature_reader.py`（經 `_parse_manifest_file` 之單一 manifest 邊界）與
`run_provenance.read_provenance_table`。期望值一律測試端以 pyarrow 自讀紀錄檔；竄改／舊 run／路徑逃逸一律在 tmp 複本上做。
實作前應為紅；不得以 skip／xfail 暫避。
"""

from __future__ import annotations

import builtins
import io
import json
import shutil
from pathlib import Path
from typing import Any, List, Tuple

import pandas as pd
import pyarrow.parquet as pq
import pytest

from momentum.FeatureEngineering import run_provenance as rp
from tests.feature_engineering import preprov_helpers as ph

pytestmark = pytest.mark.requires_kline


@pytest.fixture(scope="module")
def runs(tmp_path_factory: pytest.TempPathFactory) -> ph.RunCache:
    return ph.RunCache(tmp_path_factory.mktemp("preprov_reader"))


def _reader(features_root: Path) -> Any:
    from momentum.FeatureEngineering.feature_reader import FeatureReader

    return FeatureReader(str(features_root))


def _load(handle: ph.RunHandle, artifact_kind: str, features_root: Path = None) -> pd.DataFrame:
    root = features_root if features_root is not None else handle.features_root
    return _reader(root).load_provenance_v2(handle.symbol, handle.tf, handle.config_hash, artifact_kind)


def _copy(handle: ph.RunHandle, tmp_path: Path) -> Tuple[Path, Path]:
    """複製 run 至 tmp 之同構 features 根；回傳 (features 根, run 目錄)。"""
    root = tmp_path / "features"
    run_dir = root / handle.symbol / handle.tf / handle.config_hash
    shutil.copytree(handle.run_dir, run_dir, symlinks=True)
    return root, run_dir


def _edit_manifest(run_dir: Path, edit: Any) -> None:
    path = run_dir / ph.MANIFEST_NAME
    manifest = json.loads(path.read_text(encoding="utf-8"))
    edit(manifest)
    path.write_text(json.dumps(manifest), encoding="utf-8")


def _flip_one_byte(path: Path) -> None:
    data = bytearray(path.read_bytes())
    data[len(data) // 2] ^= 0xFF
    path.write_bytes(bytes(data))


def tamper_detected(handle: ph.RunHandle, tmp_path: Path) -> bool:
    """oracle：紀錄檔竄改一位元組 ⇒ `ProvenanceIntegrityError`（偵出回 True）。"""
    root, run_dir = _copy(handle, tmp_path)
    _flip_one_byte(run_dir / ph.provenance_pointer(run_dir, "raw")["path"])
    try:
        _load(handle, "raw", root)
    except rp.ProvenanceIntegrityError:
        return True
    except Exception:  # noqa: BLE001 — 竄改後 parquet 解析失敗等非具名錯誤不算偵出（須具名完整性錯誤）
        return False
    return False


# ---------------------------------------------------------------------------------------------- 驗證

def test_verification_01_roundtrip_bitwise(runs: ph.RunCache) -> None:
    """正常讀回與寫入表逐位元相同（期望＝測試端 pyarrow 自讀紀錄檔）。"""
    handle = runs.get("h1_stat_on")
    expected = ph.provenance_table(handle.run_dir, "raw")
    assert len(expected) > 0
    pd.testing.assert_frame_equal(_load(handle, "raw"), expected, check_exact=True)


def test_verification_02_tampered_byte_raises(runs: ph.RunCache, tmp_path: Path) -> None:
    """竄改紀錄檔一位元組 ⇒ `ProvenanceIntegrityError`。"""
    assert tamper_detected(runs.get("h1_stat_on"), tmp_path)


def test_verification_03_legacy_run_raises_missing(runs: ph.RunCache, tmp_path: Path) -> None:
    """舊 run（manifest 無 `provenance` 物件）⇒ `ProvenanceMissingError`（D6）。"""
    handle = runs.get("h1_stat_on")
    root, run_dir = _copy(handle, tmp_path)
    _edit_manifest(run_dir, lambda m: [m["artifacts"]["raw"].pop(k, None) for k in ("provenance", "content_sha256")])
    with pytest.raises(rp.ProvenanceMissingError):
        _load(handle, "raw", root)


@pytest.mark.parametrize("escape", ["../escaped/raw_columns.parquet", "provenance/../../escaped/raw_columns.parquet",
                                    "ABSOLUTE"])
def test_verification_04_path_escape_rejected(runs: ph.RunCache, tmp_path: Path, escape: str) -> None:
    """路徑含 `..` 或為絕對路徑（逃逸 run 目錄）⇒ 拒讀（`ProvenanceIntegrityError`）；逃逸目標放真檔，使只剩路徑檢查可擋。"""
    handle = runs.get("h1_stat_on")
    root, run_dir = _copy(handle, tmp_path)
    real = run_dir / ph.provenance_pointer(run_dir, "raw")["path"]
    outside = run_dir.parent / "escaped" / real.name
    outside.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(real, outside)
    target = str(outside) if escape == "ABSOLUTE" else escape

    def edit(m: Any) -> None:
        m["artifacts"]["raw"]["provenance"]["path"] = target

    _edit_manifest(run_dir, edit)
    with pytest.raises(rp.ProvenanceIntegrityError):
        _load(handle, "raw", root)


def test_verification_05_reader_does_not_rehash_feature_files(runs: ph.RunCache, monkeypatch: pytest.MonkeyPatch) -> None:
    """嚴禁慢閘：讀取端不得重算特徵檔雜湊——讀紀錄期間不以 Python 開啟任何宣告群組檔。"""
    handle = runs.get("h1_stat_on")
    groups = {str(p.resolve()) for p in ph.declared_group_files(handle.run_dir, "raw")}
    opened: List[str] = []
    real_open, real_io_open = builtins.open, io.open

    def spy_open(file: Any, *args: Any, **kwargs: Any) -> Any:
        opened.append(str(Path(str(file)).resolve()) if isinstance(file, (str, Path)) else str(file))
        return real_open(file, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", spy_open)
    monkeypatch.setattr(io, "open", spy_open)
    _load(handle, "raw")
    monkeypatch.setattr(builtins, "open", real_open)
    monkeypatch.setattr(io, "open", real_io_open)
    assert not set(opened) & groups


# ---------------------------------------------------------------------------------------------- 邊界

def test_boundary_01_raw_and_processed_kinds(runs: ph.RunCache) -> None:
    """邊界①：processed 與 raw 兩種 artifact 皆可讀，且各等於自讀之對應紀錄檔（不得互換）。"""
    handle = runs.get("ic_first")
    processed = _load(handle, "processed")
    pd.testing.assert_frame_equal(processed, ph.provenance_table(handle.run_dir, "processed"), check_exact=True)
    raw = _load(handle, "raw")
    pd.testing.assert_frame_equal(raw, ph.provenance_table(handle.run_dir, "raw"), check_exact=True)
    assert set(processed["output_column"]) != set(raw["output_column"])


def test_boundary_02_raw_deleted_run_reads_raw_record(runs: ph.RunCache) -> None:
    """邊界②：raw 已刪之 run 讀 raw 紀錄——照常讀回（紀錄檔不在 raw/ 內）。"""
    handle = runs.get("ic_first")
    assert not (handle.run_dir / "raw").exists()
    raw = _load(handle, "raw")
    assert len(raw) > 0
    pd.testing.assert_frame_equal(raw, pq.read_table(str(ph.provenance_file(handle.run_dir, "raw"))).to_pandas(),
                                  check_exact=True)


def _output_size_module() -> Any:
    """`scripts/preprov_output_size.py`（Task 3.2 量測腳本；scripts 非套件，以檔案路徑載入）。"""
    import importlib.util

    spec = importlib.util.spec_from_file_location("preprov_output_size", ph.REPO / "scripts" / "preprov_output_size.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _manifest_and_records_copy(handle: ph.RunHandle, tmp_path: Path) -> Path:
    """真實 run 之 manifest 與其宣告之紀錄檔複本（不複製特徵檔；量測腳本只讀 manifest 與紀錄檔）。"""
    run_dir = tmp_path / "run_copy"
    run_dir.mkdir()
    shutil.copy2(handle.run_dir / ph.MANIFEST_NAME, run_dir / ph.MANIFEST_NAME)
    for node in ph.load_manifest(handle.run_dir)["artifacts"].values():
        rel = Path(str(node["provenance"]["path"]))
        (run_dir / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(handle.run_dir / rel, run_dir / rel)
    return run_dir


@pytest.mark.parametrize("breakage", ["missing_pointer", "missing_record", "unreadable_metadata"])
def test_output_size_script_fails_closed_on_broken_provenance(runs: ph.RunCache, tmp_path: Path, breakage: str) -> None:
    """Task 3.2 邊界③（CODEX-R5-P2-04）：`--full-run-dir` 之 run 任一 artifact 缺 `provenance` 指標／紀錄檔不存在／parquet
    metadata 不可讀 ⇒ `main` 回 1、收據 `exit_code`＝1 且含 error、無 `full_feature_run`（不以 0 位元組累計）。
    正對照：同一複本破壞前 `measure_run` 成立且紀錄位元組合計 > 0。"""
    module = _output_size_module()
    run_dir = _manifest_and_records_copy(runs.get("h1_stat_on"), tmp_path)
    measured = module.measure_run(run_dir)
    assert measured["record_bytes_total"] > 0 and set(measured["artifacts"]) == {"raw"}
    record = run_dir / ph.provenance_pointer(run_dir, "raw")["path"]
    if breakage == "missing_pointer":
        _edit_manifest(run_dir, lambda m: m["artifacts"]["raw"].pop("provenance"))
    elif breakage == "missing_record":
        record.unlink()
    else:
        record.write_bytes(b"not a parquet file")
    with pytest.raises(module.MeasurementError):
        module.measure_run(run_dir)
    out = tmp_path / "output_size.json"
    assert module.main(["--full-run-dir", str(run_dir), "--out", str(out)]) == 1
    receipt = json.loads(out.read_text(encoding="utf-8"))
    assert receipt["exit_code"] == 1 and "MeasurementError" in receipt["error"]
    assert "full_feature_run" not in receipt and "needs_user_reapproval" not in receipt
    assert receipt["cells"] == {}


# ---------------------------------------------------------------------------------------------- mutation

def test_mutation_skip_sha_check(runs: ph.RunCache, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """mutation（SPEC Task 1.5）：略過 sha256 比對（雜湊恆回宣告值）⇒ 竄改案轉紅。"""
    handle = runs.get("h1_stat_on")
    declared = ph.provenance_pointer(handle.run_dir, "raw")["sha256"]
    assert tamper_detected(handle, tmp_path / "real")
    monkeypatch.setattr(rp, "file_sha256", lambda path: declared)
    assert not tamper_detected(handle, tmp_path / "mutant")
