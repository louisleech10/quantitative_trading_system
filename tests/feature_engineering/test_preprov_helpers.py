"""FFDSTAR Task 1.6（docs/FFDSTAR_SPEC.md §G「讀取方式先行」）：測試輔助與凍結腳本改依 manifest 宣告讀取。

受測物：`tests/feature_engineering/preprov_helpers.declared_feature_files`（依 manifest 列群組檔之單一函式）與 §G
所列之凍結腳本／測試輔助之讀法。真實 kline 短窗 run（同模組同格只生成一次）；run 目錄之竄改一律在 tmp 複本上做。
實作前應為紅；不得以 skip／xfail 暫避。
"""

from __future__ import annotations

import ast
import shutil
from pathlib import Path
from typing import Callable, List

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from tests.feature_engineering import preprov_helpers as ph

pytestmark = pytest.mark.requires_kline

#: §G 列名之「以檔名掃描 run 目錄取特徵」讀法所在檔（至少；Task 1.6 以 grep 窮舉後可增列）
SECTION_G_READERS = (
    "scripts/freeze_failopen_baseline.py",
    "scripts/freeze_framepath_baseline.py",
    "tests/feature_engineering/ffstat_helpers.py",
)
_SCAN_PATTERNS = {"*", "*.parquet", "raw/*.parquet", "**/*.parquet"}


@pytest.fixture(scope="module")
def runs(tmp_path_factory: pytest.TempPathFactory) -> ph.RunCache:
    return ph.RunCache(tmp_path_factory.mktemp("preprov_helpers"))


def _copy_run(handle: ph.RunHandle, tmp_path: Path) -> Path:
    target = tmp_path / "run_copy"
    shutil.copytree(handle.run_dir, target, symlinks=True)
    return target


def _plant_undeclared(run_dir: Path, artifact_kind: str = "raw") -> Path:
    path = run_dir / artifact_kind / "undeclared_extra.parquet"
    pq.write_table(pa.table({"close_1h_trend_EMA_8": pa.array([1.0, 2.0], type=pa.float32())}), path)
    return path


def rejects_undeclared(listing: Callable[..., List[Path]], run_dir: Path) -> bool:
    """oracle：artifact 目錄下有未宣告 parquet 時，listing 必拋錯（不得把它當特徵檔列出）。"""
    planted = _plant_undeclared(run_dir)
    try:
        files = listing(run_dir, "raw")
    except ValueError:
        return True
    finally:
        planted.unlink(missing_ok=True)
    return planted not in [Path(p) for p in files]


def scan_calls(path: Path) -> List[str]:
    """檔內 `.rglob(...)`／`.glob(...)` 以掃描型樣式字面呼叫者（行號:樣式）。"""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out: List[str] = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr in ("rglob", "glob") and node.args
                and isinstance(node.args[0], ast.Constant) and node.args[0].value in _SCAN_PATTERNS):
            out.append(f"{node.lineno}:{node.func.attr}({node.args[0].value!r})")
    return out


# ---------------------------------------------------------------------------------------------- 驗證

def test_verification_01_declared_listing_matches_artifact_files_on_clean_run(runs: ph.RunCache) -> None:
    """乾淨 run（無非宣告檔）：宣告群組檔集合＝raw 目錄之 parquet 集合；依宣告讀之值指紋與逐檔讀者相同（讀法替換不改值）。"""
    handle = runs.get("h1_stat_off")
    declared = {p.resolve() for p in ph.declared_group_files(handle.run_dir, "raw")}
    on_disk = {p.resolve() for p in (handle.run_dir / "raw").glob("*.parquet")}
    assert declared and declared == on_disk
    fps = ph.value_fingerprints(handle.run_dir, "raw")["columns"]
    direct = {n for p in on_disk for n in pq.read_schema(str(p)).names if n not in ph.NON_FEATURE_COLUMNS}
    assert set(fps) == direct
    row_index = handle.run_dir / ph.row_index_rel(ph.load_manifest(handle.run_dir), "raw")
    assert row_index in ph.declared_feature_files(handle.run_dir, "raw")


def test_verification_02_section_g_readers_are_manifest_driven() -> None:
    """§G 所列凍結腳本與測試輔助不得再以檔名掃描 run 目錄取特徵（rglob／glob 之掃描型樣式為 0），且改經
    `declared_feature_files` 依 manifest 宣告讀取（不得以「排除特定檔名」代替）。"""
    offenders = {rel: scan_calls(ph.REPO / rel) for rel in SECTION_G_READERS}
    assert {k: v for k, v in offenders.items() if v} == {}
    missing = [rel for rel in SECTION_G_READERS
               if "declared_feature_files" not in (ph.REPO / rel).read_text(encoding="utf-8")]
    assert missing == []


def test_verification_03_undeclared_or_missing_files_raise(runs: ph.RunCache, tmp_path: Path) -> None:
    """未宣告 parquet 出現於 artifact 目錄 ⇒ ValueError；宣告檔缺 ⇒ FileNotFoundError（皆不靜默）。"""
    run_dir = _copy_run(runs.get("h1_stat_off"), tmp_path)
    assert rejects_undeclared(ph.declared_feature_files, run_dir)
    victim = ph.declared_group_files(run_dir, "raw")[0]
    victim.unlink()
    with pytest.raises(FileNotFoundError):
        ph.declared_feature_files(run_dir, "raw")


def test_verification_04_helpers_independent_of_run_provenance() -> None:
    """獨立 oracle 不得呼叫受測物：`preprov_helpers` 不 import `run_provenance`；`independent_content_sha256`
    之組成欄位與契約 `content_sha256.entry_fields` 一致（契約變更須同步改獨立實作）。"""
    tree = ast.parse((ph.REPO / "tests/feature_engineering/preprov_helpers.py").read_text(encoding="utf-8"))
    imported = {n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)} | {
        a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    imported |= {a.name for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) for a in n.names}
    assert not [m for m in imported if "run_provenance" in m]
    assert ph.contract()["content_sha256"]["entry_fields"] == ["relative_path", "columns", "row_count", "dtype",
                                                                "file_sha256"]


# ---------------------------------------------------------------------------------------------- 邊界

def test_boundary_01_processed_groups_and_processed_timestamps(runs: ph.RunCache) -> None:
    """邊界①：processed artifact 之群組與 `processed_timestamps.parquet` 皆由宣告列出。"""
    handle = runs.get("ic_first")
    manifest = ph.load_manifest(handle.run_dir)
    node = manifest["artifacts"]["processed"]
    expected = [handle.run_dir / g["path"] for g in node["groups"].values()]
    expected.append(handle.run_dir / node["row_index"]["path"])
    listed = ph.declared_feature_files(handle.run_dir, "processed")
    assert listed == expected
    assert (handle.run_dir / "processed_timestamps.parquet") in listed
    assert len(listed) >= 2


def test_boundary_02_ic_first_raw_deleted(runs: ph.RunCache) -> None:
    """邊界②：IC-first 已刪 raw 之 run——processed 照常列出；raw 之宣告檔不存在 ⇒ FileNotFoundError（不靜默回空）。"""
    handle = runs.get("ic_first")
    assert not (handle.run_dir / "raw").exists()
    assert ph.declared_feature_files(handle.run_dir, "processed")
    with pytest.raises(FileNotFoundError):
        ph.declared_feature_files(handle.run_dir, "raw")
    with pytest.raises(FileNotFoundError):
        ph.independent_content_sha256(handle.run_dir, "raw")


def test_boundary_03_multi_tf_groups(runs: ph.RunCache) -> None:
    """邊界③：多週期 run 之群組——宣告群組檔之欄涵蓋兩個週期之標記（1h、12h），與 raw 目錄 parquet 集合相同。"""
    from momentum.FeatureEngineering.feature_naming import strip_timeframe_tag

    handle = runs.get("h12h1_multi")
    names = ph.group_columns(handle.run_dir, "raw")
    tags = {n.split("_")[1] for n in names if strip_timeframe_tag(n) != n}
    assert {"1h", "12h"} <= tags
    declared = {p.resolve() for p in ph.declared_group_files(handle.run_dir, "raw")}
    assert declared == {p.resolve() for p in (handle.run_dir / "raw").glob("*.parquet")}


# ---------------------------------------------------------------------------------------------- mutation

def test_mutation_rglob_listing_accepts_undeclared_parquet(runs: ph.RunCache, monkeypatch: pytest.MonkeyPatch,
                                                            tmp_path: Path) -> None:
    """mutation（SPEC Task 1.6）：輔助函式改回 `rglob("*.parquet")` 且 run 目錄放入一個非宣告 parquet ⇒ 本檔 oracle 轉紅。"""
    run_dir = _copy_run(runs.get("h1_stat_off"), tmp_path)
    assert rejects_undeclared(ph.declared_feature_files, run_dir)

    def rglob_listing(run_dir: Path, artifact_kind: str = "raw") -> List[Path]:
        return sorted(Path(run_dir).rglob("*.parquet"))

    monkeypatch.setattr(ph, "declared_feature_files", rglob_listing)
    assert not rejects_undeclared(ph.declared_feature_files, run_dir)
