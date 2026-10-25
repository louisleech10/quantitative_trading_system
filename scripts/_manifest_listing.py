"""依 manifest 宣告列特徵 run 之檔（FFDSTAR／PRE-PROV Task 1.6；docs/FFDSTAR_SPEC.md §G「讀取方式先行」）。

scripts/ 端之單一列檔入口（scripts 不 import tests/）：凍結腳本與量測腳本一律經本模組取 run 內之特徵檔集合，
不得再以檔名掃描 run 目錄（`rglob("*.parquet")` 等）當特徵——Task 1.3 起 run 目錄新增 `provenance/` 紀錄檔，
以檔名掃描會把紀錄檔誤當特徵讀、指紋或計數。

與 `tests/feature_engineering/preprov_helpers.declared_feature_files` 同語意（同一宣告來源、同一錯誤條件）：
- 特徵檔集合只自 manifest（`feature_manifest.json`）artifact 節點之 `groups[*].path` 與 row index 宣告導出；
- 宣告檔缺 ⇒ FileNotFoundError；artifact 目錄下有未宣告之 parquet ⇒ ValueError（不靜默忽略）。
- run 快照（`declared_run_snapshot_files`）另含 manifest 各 artifact 節點 `provenance.path` 宣告之紀錄檔（FFDSTAR b4 F；
  只認宣告，舊 run 無宣告 ⇒ 快照檔集合不變；`provenance/` 下未宣告之檔仍由未宣告檔守衛拋錯）。

不 import 生產讀取端（`momentum.FeatureEngineering.feature_reader`）之理由：生產讀取端無「列 run 內宣告檔」之公開 API
（`stream_groups_v2` 等只回讀出之資料、且需 symbol／tf／config_hash 而非任意目錄），且凍結腳本之列檔須於改前／改後
雙碼態行為一致（`scripts/ffname_refreeze.py` 雙 worktree 記錄）——依賴受測生產碼之內部函式會使列檔隨受測物漂移。
本模組只讀 manifest JSON 與 stat，不碰特徵值。

本模組之目錄掃描呼叫只作「未宣告檔守衛」與「manifest 定位」（掃描點清冊 `tests/_golden/preprov/reader_inventory.json`
登記為 unrelated），列出之檔一律來自宣告。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Set

MANIFEST_NAME = "feature_manifest.json"
REGISTRY_MANIFEST_NAME = "manifest.json"
#: FFDSTAR Task 1.3／1.4：逐欄紀錄檔所在之 run 根子目錄（契約 `run_provenance.json` 之 `files` 皆在其下）
PROVENANCE_DIR = "provenance"

#: feature run 目錄內「非 manifest 宣告、但現行生產碼確實寫入」之附屬檔（快照雜湊須含之以重現既有凍結值）。
#: 檔名 → 理由；只在實際存在時列入（不存在不報錯）。新增項須附生產碼出處。
RUN_DIR_ALLOWED_EXTRAS: Dict[str, str] = {
    "feature_manifest.json.lock": (
        "manifest 讀改寫之跨行程檔鎖（feature_storage.FeatureStorage._manifest_v2_lock 以 open('a+')＋flock 建於 run 根），"
        "非特徵、不由 manifest 宣告；現行 run 目錄確實存在，freeze_failopen_baseline 之 artifacts 雜湊"
        "（tests/_golden/failopen/baseline.json multi_tf.BTCUSDT）含之"
    ),
}


def load_manifest(run_dir: Path) -> Dict[str, Any]:
    return json.loads((Path(run_dir) / MANIFEST_NAME).read_text(encoding="utf-8"))


def _safe_rel(raw: Any) -> str:
    rel = Path(str(raw))
    if not str(raw) or rel.is_absolute() or ".." in rel.parts:
        raise ValueError(f"manifest 宣告路徑不安全：{raw!r}")
    return str(rel)


def row_index_rel(manifest: Mapping[str, Any], artifact_kind: str) -> Optional[str]:
    """artifact 之 row index 檔相對路徑：processed 取其節點之 `row_index`；raw 取節點（若有）否則根之 `row_index`。"""
    node = manifest["artifacts"][artifact_kind]
    ri = node.get("row_index") if isinstance(node.get("row_index"), dict) else None
    if ri is None and artifact_kind == "raw" and isinstance(manifest.get("row_index"), dict):
        ri = manifest["row_index"]
    return None if ri is None else _safe_rel(ri["path"])


def declared_feature_files(run_dir: Path, artifact_kind: str = "raw") -> List[Path]:
    """特徵檔集合只自 manifest 該 artifact 節點之 `groups[*].path` 與 row index 宣告導出（manifest 宣告序）。
    宣告檔缺 ⇒ FileNotFoundError；artifact 目錄下有未宣告之 parquet ⇒ ValueError（不靜默忽略）。"""
    run_dir = Path(run_dir)
    manifest = load_manifest(run_dir)
    artifacts = manifest.get("artifacts") or {}
    if artifact_kind not in artifacts:
        raise FileNotFoundError(f"manifest 無 artifact {artifact_kind!r}：{run_dir}")
    groups = artifacts[artifact_kind].get("groups") or {}
    files = [run_dir / _safe_rel(info.get("path")) for info in groups.values()]
    ri = row_index_rel(manifest, artifact_kind)
    if ri is not None:
        files.append(run_dir / ri)
    missing = [str(p) for p in files if not p.is_file()]
    if missing:
        raise FileNotFoundError(f"manifest 宣告之檔不存在：{missing[:5]}")
    art_dir = run_dir / artifact_kind
    if art_dir.exists():
        declared = {p.resolve() for p in files}
        # 未宣告檔守衛（非特徵讀取）：刻意列舉 artifact 目錄實體 parquet 以偵出 manifest 未宣告者
        undeclared = sorted(str(p) for p in art_dir.rglob("*.parquet") if p.resolve() not in declared)
        if undeclared:
            raise ValueError(f"artifact 目錄下有 manifest 未宣告之 parquet：{undeclared[:5]}")
    return files


def declared_group_files(run_dir: Path, artifact_kind: str = "raw") -> List[Path]:
    """`declared_feature_files` 去掉 row index 檔（只留群組檔）。"""
    manifest = load_manifest(run_dir)
    ri = row_index_rel(manifest, artifact_kind)
    skip = None if ri is None else (Path(run_dir) / ri).resolve()
    return [p for p in declared_feature_files(run_dir, artifact_kind) if p.resolve() != skip]


def declared_feature_files_of_run(run_dir: Path) -> List[Path]:
    """run 內全部 artifact 之宣告特徵檔（`declared_feature_files` 之聯集；路徑升冪、去重）。

    artifact 目錄已整個回收者（IC-first `cleanup_raw` 刪 `raw/`，manifest 仍留該節點）：其群組檔不復存在，只列其仍在之
    row index 宣告（raw 之 row index＝run 根 `timestamps.parquet`，回收後仍在）。"""
    run_dir = Path(run_dir)
    manifest = load_manifest(run_dir)
    out = set()
    for kind, node in (manifest.get("artifacts") or {}).items():
        art_dir = run_dir / _safe_rel((node or {}).get("path") or kind)
        if art_dir.is_dir():
            out.update(declared_feature_files(run_dir, kind))
            continue
        ri = row_index_rel(manifest, kind)
        if ri is not None and (run_dir / ri).is_file():
            out.add(run_dir / ri)
    return sorted(out)


def feature_run_dirs(root: Path) -> List[Path]:
    """features 根（或 run 目錄本身）下全部 V2 run 目錄（以 manifest 定位；不列舉特徵檔）。"""
    root = Path(root)
    if (root / MANIFEST_NAME).is_file():
        return [root]
    if not root.exists():
        return []
    # manifest 定位（非特徵讀取）
    return sorted(m.parent for m in root.rglob(MANIFEST_NAME))


def declared_feature_files_under(root: Path) -> List[Path]:
    """features 根下全部 run 之宣告特徵檔（路徑升冪；與舊 `sorted(root.rglob("*.parquet"))` 同序）。"""
    return sorted({p for run_dir in feature_run_dirs(root) for p in declared_feature_files_of_run(run_dir)})


def _guard_no_undeclared(base: Path, listed: List[Path], what: str) -> None:
    """未宣告檔守衛（非特徵讀取）：base 下任何實體檔不在 listed ⇒ ValueError（快照雜湊不得靜默漏檔或混入）。"""
    allowed = {p.resolve() for p in listed}
    # 刻意列舉 base 下全部實體檔以偵出未宣告者
    undeclared = sorted(str(p) for p in base.rglob("*") if p.is_file() and p.resolve() not in allowed)
    if undeclared:
        raise ValueError(f"{what} 有未宣告之檔：{undeclared[:5]}")


def declared_provenance_files(run_dir: Path) -> List[Path]:
    """manifest 各 artifact 節點之 `provenance.path`（FFDSTAR Task 1.3／1.4 紀錄檔指標）所宣告之紀錄檔（路徑升冪、去重）。

    只認宣告（不掃 `provenance/`）：節點無 `provenance` 物件（改前碼態之舊 run）⇒ 不列入，快照檔集合與改前逐位元相同；
    宣告路徑不安全或不在 run 根 `provenance/` 下 ⇒ ValueError；宣告檔不存在 ⇒ FileNotFoundError。紀錄檔非特徵，
    不入 `declared_feature_files*`。"""
    run_dir = Path(run_dir)
    out = set()
    for kind, node in (load_manifest(run_dir).get("artifacts") or {}).items():
        pointer = (node or {}).get("provenance") if isinstance(node, dict) else None
        if pointer is None:
            continue
        if not isinstance(pointer, dict):
            raise ValueError(f"artifact {kind!r} 之 provenance 非物件：{pointer!r}")
        rel = Path(_safe_rel(pointer.get("path")))
        if len(rel.parts) < 2 or rel.parts[0] != PROVENANCE_DIR:
            raise ValueError(f"artifact {kind!r} 之紀錄檔宣告路徑不在 {PROVENANCE_DIR}/ 下：{pointer.get('path')!r}")
        out.add(run_dir / rel)
    missing = sorted(str(p) for p in out if not p.is_file())
    if missing:
        raise FileNotFoundError(f"manifest 宣告之紀錄檔不存在：{missing[:5]}")
    return sorted(out)


def declared_run_snapshot_files(run_dir: Path) -> List[Path]:
    """feature run 目錄之快照檔集合＝宣告特徵檔（`declared_feature_files_of_run`）＋manifest 宣告之紀錄檔
    （`declared_provenance_files`；舊 run 無宣告 ⇒ 無）＋manifest 本身＋實際存在之 `RUN_DIR_ALLOWED_EXTRAS`
    （逐項附理由）；run 目錄有其他實體檔（含未宣告之 `provenance/` 檔）⇒ ValueError。路徑升冪。"""
    run_dir = Path(run_dir)
    files = set(declared_feature_files_of_run(run_dir))
    files.update(declared_provenance_files(run_dir))
    files.add(run_dir / MANIFEST_NAME)
    files.update(run_dir / name for name in RUN_DIR_ALLOWED_EXTRAS if (run_dir / name).is_file())
    listed = sorted(files)
    _guard_no_undeclared(run_dir, listed, f"run 目錄 {run_dir}")
    return listed


def _registry_file(work_dir: Path, name: Any) -> Path:
    text = str(name)
    if not text or "/" in text or "\\" in text or text in (".", ".."):
        raise ValueError(f"registry manifest 宣告檔名不安全：{name!r}")
    return work_dir / text


#: 紀錄檔群組表（manifest `artifacts.*.provenance.groups`）之「整組全死」狀態值（契約 `run_provenance.json` 群組狀態集合之一）
ALL_DEAD_GROUP_STATUS = "all_dead_dropped"


def all_dead_groups_of_run(run_dir: Path) -> Set[str]:
    """feature run manifest 各 artifact 節點 `provenance.groups` 中狀態為整組全死之來源群組 id（寫入端唯一紀錄：
    `feature_storage` 整組全 dead ⇒ 不寫 parquet、源頭仍清理，並以此狀態記於紀錄群組表）。節點無 `provenance` ⇒ 不貢獻。"""
    out: Set[str] = set()
    for kind, node in (load_manifest(Path(run_dir)).get("artifacts") or {}).items():
        groups = ((node or {}).get("provenance") or {}).get("groups") if isinstance(node, dict) else None
        if groups is None:
            continue
        if not isinstance(groups, dict):
            raise ValueError(f"artifact {kind!r} 之 provenance.groups 非物件：{type(groups).__name__}")
        out.update(str(gid) for gid, row in groups.items()
                   if isinstance(row, dict) and row.get("status") == ALL_DEAD_GROUP_STATUS)
    return out


def declared_registry_files(work_dir: Path, released_groups: Optional[Set[str]] = None) -> List[Path]:
    """CGSA registry 工作目錄之快照檔集合＝registry `manifest.json` 本身＋其宣告檔（各群組 `npy_path`、`shards[*].file`、
    `alignment.idx_map_path`）中實際存在者。宣告檔缺時只認兩種釋放：該群組已綁 `parquet_path`（經 L7 落盤後釋放），或
    群組 id 在 `released_groups`（同一次 L7 run 紀錄為整組全死之群組，見 `all_dead_groups_of_run`）；其餘 ⇒
    FileNotFoundError；工作目錄有未宣告之實體檔 ⇒ ValueError。路徑升冪。"""
    work_dir = Path(work_dir)
    released = set(released_groups or ())
    manifest_path = work_dir / REGISTRY_MANIFEST_NAME
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    files = {manifest_path}
    missing: List[str] = []
    for group in manifest.get("groups") or []:
        names = [group.get("npy_path")] + [s.get("file") for s in group.get("shards") or []]
        names.append((group.get("alignment") or {}).get("idx_map_path"))
        all_dead = str(group.get("group_id")) in released
        for name in names:
            if name is None:
                continue
            path = _registry_file(work_dir, name)
            if path.is_file():
                files.add(path)
            elif not group.get("parquet_path") and not all_dead:
                missing.append(str(path))
    if missing:
        raise FileNotFoundError(f"registry manifest 宣告之檔不存在（且未經 L7 釋放）：{sorted(set(missing))[:5]}")
    # NUMVIEW D7：CGSA 葉身分檔（檔名讀契約 `cgsa_work_identity.identity_file`）為工作目錄之宣告中繼資料
    identity = work_dir / json.loads((Path(__file__).resolve().parents[1] / "momentum" / "FeatureEngineering" / "contracts"
                                      / "numeric_view.json").read_text(encoding="utf-8"))["cgsa_work_identity"]["identity_file"]
    if identity.is_file():
        files.add(identity)
    listed = sorted(files)
    _guard_no_undeclared(work_dir, listed, f"registry 工作目錄 {work_dir}")
    return listed


def declared_feature_files_snapshot(work_dir: Path, released_groups: Optional[Set[str]] = None) -> List[Path]:
    """凍結腳本之產物快照檔集合（取代「目錄全部檔」）：feature run 目錄（有 `feature_manifest.json`）⇒
    `declared_run_snapshot_files`；CGSA registry 工作目錄（有 `manifest.json`）⇒ `declared_registry_files`（`released_groups`
    ＝同一次 L7 run 之整組全死群組）；皆無 ⇒ FileNotFoundError。"""
    work_dir = Path(work_dir)
    if (work_dir / MANIFEST_NAME).is_file():
        return declared_run_snapshot_files(work_dir)
    if (work_dir / REGISTRY_MANIFEST_NAME).is_file():
        return declared_registry_files(work_dir, released_groups)
    raise FileNotFoundError(f"{work_dir} 無 {MANIFEST_NAME} 亦無 {REGISTRY_MANIFEST_NAME}：無宣告可依")
