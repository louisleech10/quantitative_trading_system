"""PRE-PROV（docs/FFDSTAR_SPEC.md Task 2.2）：IC ingest 快取（h5 與 `_meta.json`）依 run 身分失效。

改前缺陷（SPEC §RISK (a)）：快取鍵＝`{symbol}_{tf}_{config_hash or latest}`，h5 只在缺檔或命名世代過期時重寫、
`_meta.json` 存在即永不重寫 ⇒ 同 config_hash 重生之 run 被舊快取取代，IC 分析之特徵值非本次 run。

驗證（SPEC Task 2.2 驗證①②③ ⇒ boundary_01–03）：①同身分第二次呼叫沿用（不重寫，以寫入計數與 mtime 斷言）；
②真實短窗 run 重生而值改變（隔離 kline 副本中改一根 K 線）⇒ h5 與 meta 皆重寫，且 orchestrator 讀得之
`metadata_json` 身分為新值；③舊格式快取（無身分屬性）⇒ 重寫。邊界（⇒ boundary_04–05）：①快取目錄不存在；
②h5 損毀（OSError）⇒ 重寫。mutation：沿用條件拿掉 `content_sha256` ⇒ ②紅；只重寫 h5 不重寫 meta ⇒ ②紅。

隔離：`_materialize_features_for_ic` 之快取目錄寫死相對路徑 `data_cache/reports/ic_ingest_cache`
（ic_analysis_service.py:3287），另以相對路徑讀 `data_cache/features/<sym>/<tf>/<hash>/feature_catalog_cache.parquet`
（:3396，僅讀、缺則略）；服務建構時 `create_feature_library()` 之預設根亦相對 cwd（feature_storage.py:688 會 mkdir、
feature_registry.py:19）。故每案 `monkeypatch.chdir(tmp)` 後才建服務，並把服務之 FeatureLibrary 換成指向該 run
隔離特徵根之實例——絕不寫入專案 data_cache。
身分 oracle 以測試端自 manifest 原文逐鍵取值（不經待測之 `resolve_run_identity`）；鍵集取自契約。
資料：真實 kline 短窗生成（`preprov_helpers`；格 `h1_stat_on`，原始與「改一根 K 線」各生成一次）。
"""

from __future__ import annotations

import copy
import dataclasses
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import h5py
import numpy as np
import pandas as pd
import pytest

from api.services.ic_analysis_service import ICAnalysisService
from momentum.Analysis.ic_config_schema import load_ic_config
from momentum.Analysis.ic_filter_orchestrator import ICFilterOrchestrator
from momentum.factories import stamp_h5_feature_naming_version
from momentum.FeatureEngineering import run_provenance as rp
from momentum.FeatureEngineering.feature_library import FeatureLibrary
from momentum.FeatureEngineering.feature_reader import FeatureReader
from momentum.FeatureEngineering.feature_registry import FeatureRegistry
from momentum.FeatureEngineering.feature_storage import FeatureStorage
from tests.feature_engineering import preprov_helpers as ph

pytestmark = pytest.mark.timeout(2400)

REPO = Path(__file__).resolve().parents[2]
CONTRACT: Dict[str, Any] = json.loads(rp.CONTRACT_PATH.read_text(encoding="utf-8"))
IDENTITY_KEYS: List[str] = list(CONTRACT["run_identity_keys"])
# SPEC D5 之身分物件於交接 h5 `metadata_json` 與 `_meta.json` 內之鍵名（SPEC 未明定；與報告／倖存者同名）
IDENTITY_KEY = "ff_run_identity"
CELL = "h1_stat_on"
CACHE_REL = Path("data_cache/reports/ic_ingest_cache")
OLD_NS = 1_600_000_000_000_000_000  # 沿用判定前把快取檔 mtime 撥回之固定值（重寫即不等於此值）


# ---------------------------------------------------------------- oracle 與工具


def expected_identity(manifest: Dict[str, Any], artifact_kind: str = "raw") -> Dict[str, Any]:
    """測試端獨立 oracle：自 manifest 原文逐鍵取 run 身分（同 tests/feature_engineering/test_preprov_identity.py）。"""
    node = (manifest.get("artifacts") or {}).get(artifact_kind) or {}
    prov = node.get("provenance")
    out = {
        "symbol": manifest.get("symbol"),
        "tf": manifest.get("tf"),
        "config_hash": manifest.get("config_hash"),
        "feature_schema_hash": node.get("feature_schema_hash", manifest.get("feature_schema_hash")),
        "feature_naming_version": manifest.get("feature_naming_version"),
        "artifact_kind": artifact_kind,
        "content_sha256": node.get("content_sha256"),
        "provenance_sha256": prov.get("sha256") if isinstance(prov, dict) else None,
    }
    assert set(out) == set(IDENTITY_KEYS), "契約 run_identity_keys 改動須同步本 oracle"
    return out


def read_manifest(run: Any) -> Dict[str, Any]:
    return json.loads((Path(run.run_dir) / FeatureReader.V2_MANIFEST_NAME).read_text(encoding="utf-8"))


def library_for(run: Any) -> FeatureLibrary:
    root = Path(run.features_root)
    registry_path = root / "registry.json"
    assert registry_path.is_file(), f"前提不成立：隔離特徵根無 registry（{registry_path}）"
    return FeatureLibrary(FeatureRegistry(registry_path), FeatureStorage(str(root)), feature_reader=FeatureReader(str(root)))


def cache_paths(run: Any, hash_key: Optional[str] = None) -> Dict[str, Path]:
    """快取檔之可讀前綴（SPEC：檔名保留可讀前綴）；`hash_key=None` ⇒ 該 run 之 config_hash。"""
    key = f"{run.symbol}_{run.tf}_{hash_key or run.config_hash}".replace("/", "_")
    return {"h5": CACHE_REL / f"{key}.h5", "meta": CACHE_REL / f"{key}_meta.json"}


def h5_identity(orchestrator: ICFilterOrchestrator, path: Any) -> Any:
    """orchestrator 讀交接 h5 所得之 metadata（`_load_features_hdf5` 之 `metadata_json`）內之身分。"""
    _df, metadata = orchestrator._load_features_hdf5(str(path))
    return metadata.get(IDENTITY_KEY)


def meta_identity(path: Any) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8")).get(IDENTITY_KEY)


def age(*paths: Path) -> None:
    for p in paths:
        os.utime(p, ns=(OLD_NS, OLD_NS))


def was_rewritten(path: Path) -> bool:
    return path.stat().st_mtime_ns != OLD_NS


def write_head_format_cache(paths: Dict[str, Path], run: Any, df: pd.DataFrame) -> None:
    """改前碼態（HEAD）之快取格式：h5 根屬性只有命名世代、無任何身分；meta 只有 symbol／timeframe／config_hash 與逐欄項。
    逐位元仿 `ICAnalysisService._write_features_h5`／`_build_ic_metadata_from_run` 之 HEAD 寫法（不呼叫待測函式，
    免其簽名於實作後改變）。"""
    paths["h5"].parent.mkdir(parents=True, exist_ok=True)
    timestamps = df.index.view("int64") // 10**9 if isinstance(df.index, pd.DatetimeIndex) else np.arange(len(df))
    with h5py.File(paths["h5"], "w") as handle:
        stamp_h5_feature_naming_version(handle.attrs)
        group = handle.create_group(f"{run.symbol}/{run.tf}")
        group.create_dataset("features", data=df.to_numpy(dtype=np.float32), compression="gzip")
        group.create_dataset("timestamps", data=timestamps, compression="gzip")
        group.create_dataset("feature_names", data=np.array(df.columns.tolist(), dtype=object),
                             dtype=h5py.string_dtype(encoding="utf-8"))
    meta: Dict[str, Any] = {"symbol": run.symbol, "timeframe": run.tf, "config_hash": run.config_hash}
    for name in df.columns:
        meta[str(name)] = {"name": str(name), "category": "unknown", "layer": 1}
    paths["meta"].write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")


def patch_everywhere(monkeypatch: pytest.MonkeyPatch, name: str, original: Any, replacement: Any) -> int:
    """把 momentum／api 已載入模組中綁定到 `original` 之 `name` 一律換成 `replacement`（mutant 不依賴實作之 import 形式）。"""
    hits = 0
    for module in list(sys.modules.values()):
        modname = getattr(module, "__name__", "") or ""
        if modname.startswith(("momentum", "api")) and getattr(module, name, None) is original:
            monkeypatch.setattr(module, name, replacement)
            hits += 1
    return hits


# ---------------------------------------------------------------- fixtures


@pytest.fixture(scope="module")
def orchestrator() -> ICFilterOrchestrator:
    """讀交接 h5 用；設定以絕對路徑載入（不依賴 cwd）。"""
    return ICFilterOrchestrator(load_ic_config(default_path=str(REPO / "config" / "ic_config.yaml"),
                                               user_path=str(REPO / "config" / "user_ic_config.yaml")))


@pytest.fixture(scope="module")
def run_a(tmp_path_factory: pytest.TempPathFactory) -> Any:
    """真實 kline 短窗 run（原始資料）。"""
    return ph.generate_short_run(tmp_path_factory.mktemp("preprov_ingest_a"), CELL)


@pytest.fixture(scope="module")
def run_b(tmp_path_factory: pytest.TempPathFactory, run_a: Any) -> Any:
    """同設定重生、但隔離 kline 副本中改一根 K 線（靠近窗尾，避開前段校準）之 run。"""
    root = tmp_path_factory.mktemp("preprov_ingest_b")
    axis = FeatureReader(str(run_a.features_root)).load_row_index_v2(run_a.symbol, run_a.tf, run_a.config_hash)
    assert axis is not None and len(axis) > 5, "前提不成立：run A 無時間軸"
    kline = ph.copy_kline_with_one_bar_changed(root / "kline", symbol=run_a.symbol, tf=run_a.tf, when=str(axis[-3]))
    return ph.generate_short_run(root, CELL, symbol=run_a.symbol, kline_path=kline)


@pytest.fixture()
def cwd_tmp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """cwd 移到 tmp：相對路徑之快取目錄、catalog 讀取與預設特徵根全部落在 tmp。"""
    monkeypatch.chdir(tmp_path)
    return tmp_path


def make_service(library: FeatureLibrary) -> ICAnalysisService:
    service = ICAnalysisService()
    service._feature_library = library  # noqa: SLF001 — 服務之特徵根換成該 run 之隔離根
    return service


@pytest.fixture()
def h5_writes(monkeypatch: pytest.MonkeyPatch) -> List[str]:
    """`_write_features_h5` 之呼叫計數（照實寫入，不假裝）。"""
    real = ICAnalysisService._write_features_h5
    calls: List[str] = []

    def counting(path: Any, *args: Any, **kwargs: Any) -> Any:
        calls.append(str(path))
        return real(path, *args, **kwargs)

    monkeypatch.setattr(ICAnalysisService, "_write_features_h5", staticmethod(counting))
    return calls


def _regeneration_case(orchestrator: ICFilterOrchestrator, run_a: Any, run_b: Any, h5_writes: List[str]) -> Dict[str, Any]:
    """驗證②之 oracle 輸入：同 (symbol, tf, config_hash) 先以 run A 物化，再換成重生之 run B 物化。"""
    exp_a, exp_b = expected_identity(read_manifest(run_a)), expected_identity(read_manifest(run_b))
    assert run_a.config_hash == run_b.config_hash, "前提不成立：改一根 K 線之重生應得同一 config_hash（設定身分）"
    assert exp_a["content_sha256"] and exp_b["content_sha256"], "前提不成立：manifest 無 content_sha256（Task 1.3 未落地）"
    assert exp_a["content_sha256"] != exp_b["content_sha256"], "前提不成立：改一根 K 線後內容身分未變"
    service = make_service(library_for(run_a))
    service._materialize_features_for_ic(run_a.symbol, run_a.tf, run_a.config_hash)
    paths = cache_paths(run_a)
    assert h5_identity(orchestrator, paths["h5"]) == exp_a and meta_identity(paths["meta"]) == exp_a
    age(paths["h5"], paths["meta"])
    h5_writes.clear()
    service._feature_library = library_for(run_b)  # noqa: SLF001 — 「重生」：同鍵之 run 內容已換
    service._materialize_features_for_ic(run_b.symbol, run_b.tf, run_b.config_hash)
    return {
        "exp_a": exp_a, "exp_b": exp_b,
        "h5_rewritten": was_rewritten(paths["h5"]), "meta_rewritten": was_rewritten(paths["meta"]),
        "h5_writes": len(h5_writes),
        "h5_identity": h5_identity(orchestrator, paths["h5"]), "meta_identity": meta_identity(paths["meta"]),
    }


def _regeneration_ok(case: Dict[str, Any]) -> bool:
    return (case["h5_rewritten"] and case["meta_rewritten"] and case["h5_writes"] == 1
            and case["h5_identity"] == case["exp_b"] and case["meta_identity"] == case["exp_b"])


# ---------------------------------------------------------------- 驗證①②③


def test_boundary_01_same_identity_reused_not_rewritten(
    cwd_tmp: Path, orchestrator: ICFilterOrchestrator, run_a: Any, h5_writes: List[str]
) -> None:
    """驗證①：同身分第二次呼叫沿用——h5 與 meta 皆不重寫（寫入計數 0、mtime 不變），且兩者所帶身分等於本 run。"""
    expected = expected_identity(read_manifest(run_a))
    service = make_service(library_for(run_a))
    first = service._materialize_features_for_ic(run_a.symbol, run_a.tf, run_a.config_hash)
    assert len(h5_writes) == 1, "前提不成立：首次物化未寫 h5"
    paths = cache_paths(run_a)
    assert h5_identity(orchestrator, paths["h5"]) == expected
    assert meta_identity(paths["meta"]) == expected
    meta_bytes = paths["meta"].read_bytes()
    age(paths["h5"], paths["meta"])
    h5_writes.clear()

    second = service._materialize_features_for_ic(run_a.symbol, run_a.tf, run_a.config_hash)
    assert second == first
    assert h5_writes == [], "同身分卻重寫 h5"
    assert not was_rewritten(paths["h5"]) and not was_rewritten(paths["meta"]), "同身分卻重寫快取檔（mtime 變動）"
    assert paths["meta"].read_bytes() == meta_bytes


def test_boundary_02_regenerated_run_rewrites_h5_and_meta(
    cwd_tmp: Path, orchestrator: ICFilterOrchestrator, run_a: Any, run_b: Any, h5_writes: List[str]
) -> None:
    """驗證②：同 config_hash 重生且值改變 ⇒ h5 與 meta 皆重寫；orchestrator 讀得之 `metadata_json` 身分為新值。"""
    case = _regeneration_case(orchestrator, run_a, run_b, h5_writes)
    assert case["h5_rewritten"] and case["h5_writes"] == 1, "重生後 h5 未重寫（沿用舊 run 之特徵值）"
    assert case["meta_rewritten"], "重生後 _meta.json 未重寫"
    assert case["h5_identity"] == case["exp_b"], f"orchestrator 讀得之身分非新 run：{case['h5_identity']!r}"
    assert case["meta_identity"] == case["exp_b"]
    assert _regeneration_ok(case)


def test_boundary_03_legacy_cache_without_identity_rewritten(
    cwd_tmp: Path, orchestrator: ICFilterOrchestrator, run_a: Any, h5_writes: List[str]
) -> None:
    """驗證③：改前格式之快取（h5 命名世代現行但無身分、meta 無身分）⇒ 兩者一併重寫且帶本 run 身分。"""
    expected = expected_identity(read_manifest(run_a))
    library = library_for(run_a)
    paths = cache_paths(run_a)
    write_head_format_cache(paths, run_a, library.load(run_a.symbol, run_a.tf, config_hash=run_a.config_hash))
    assert h5_identity(orchestrator, paths["h5"]) is None and meta_identity(paths["meta"]) is None
    age(paths["h5"], paths["meta"])

    make_service(library)._materialize_features_for_ic(run_a.symbol, run_a.tf, run_a.config_hash)
    assert len(h5_writes) == 1 and was_rewritten(paths["h5"]), "無身分之舊 h5 被沿用"
    assert was_rewritten(paths["meta"]), "無身分之舊 _meta.json 被沿用"
    assert h5_identity(orchestrator, paths["h5"]) == expected
    assert meta_identity(paths["meta"]) == expected


# ---------------------------------------------------------------- 邊界①②


def test_boundary_04_cache_dir_absent(
    cwd_tmp: Path, orchestrator: ICFilterOrchestrator, run_a: Any, h5_writes: List[str]
) -> None:
    """邊界①：快取目錄不存在 ⇒ 建立並寫入 h5 與 meta，兩者帶本 run 身分。"""
    assert not (cwd_tmp / CACHE_REL).exists()
    expected = expected_identity(read_manifest(run_a))
    h5_path, meta_path = make_service(library_for(run_a))._materialize_features_for_ic(
        run_a.symbol, run_a.tf, run_a.config_hash)
    assert Path(h5_path).resolve().parent == (cwd_tmp / CACHE_REL).resolve(), "快取未落在隔離 cwd 下"
    assert len(h5_writes) == 1
    assert h5_identity(orchestrator, h5_path) == expected
    assert meta_identity(meta_path) == expected


def test_boundary_05_corrupt_h5_rewritten(
    cwd_tmp: Path, orchestrator: ICFilterOrchestrator, run_a: Any, h5_writes: List[str]
) -> None:
    """邊界②：h5 損毀（開檔 OSError）而 meta 完好帶同身分 ⇒ 不沿用、兩者一併重寫。"""
    expected = expected_identity(read_manifest(run_a))
    service = make_service(library_for(run_a))
    service._materialize_features_for_ic(run_a.symbol, run_a.tf, run_a.config_hash)
    paths = cache_paths(run_a)
    paths["h5"].write_bytes(b"not an hdf5 file")
    with pytest.raises(OSError):
        h5py.File(paths["h5"], "r")
    age(paths["h5"], paths["meta"])
    h5_writes.clear()

    service._materialize_features_for_ic(run_a.symbol, run_a.tf, run_a.config_hash)
    assert len(h5_writes) == 1 and was_rewritten(paths["h5"])
    assert was_rewritten(paths["meta"]), "h5 損毀時 meta 未一併重寫"
    assert h5_identity(orchestrator, paths["h5"]) == expected
    assert meta_identity(paths["meta"]) == expected


# ---------------------------------------------------------------- 改法補充（非編號項）


def test_legacy_run_identity_never_reused(
    cwd_tmp: Path, orchestrator: ICFilterOrchestrator, run_a: Any, h5_writes: List[str]
) -> None:
    """改法：身分為 legacy（舊 run 無 content_sha256）⇒ 快取一律不沿用（D6），連續兩次皆重寫。"""
    manifest_file = Path(run_a.run_dir) / FeatureReader.V2_MANIFEST_NAME
    original = manifest_file.read_bytes()
    legacy = copy.deepcopy(json.loads(original))
    for node in (legacy.get("artifacts") or {}).values():
        if isinstance(node, dict):
            node.pop("content_sha256", None)
            node.pop("provenance", None)
    try:
        manifest_file.write_text(json.dumps(legacy, ensure_ascii=False, indent=2), encoding="utf-8")
        service = make_service(library_for(run_a))
        service._materialize_features_for_ic(run_a.symbol, run_a.tf, run_a.config_hash)
        paths = cache_paths(run_a)
        age(paths["h5"], paths["meta"])
        h5_writes.clear()
        service._materialize_features_for_ic(run_a.symbol, run_a.tf, run_a.config_hash)
        assert len(h5_writes) == 1 and was_rewritten(paths["h5"]) and was_rewritten(paths["meta"])
        assert h5_identity(orchestrator, paths["h5"]) == expected_identity(legacy)
    finally:
        manifest_file.write_bytes(original)


def test_latest_judged_by_resolved_identity(
    cwd_tmp: Path, orchestrator: ICFilterOrchestrator, run_a: Any, run_b: Any, h5_writes: List[str]
) -> None:
    """改法：`latest` 一律以解析後身分判定——未指定 config_hash 時 latest 快取不因同名前綴而沿用他 run 之值。"""
    service = make_service(library_for(run_a))
    h5_path, meta_path = service._materialize_features_for_ic(run_a.symbol, run_a.tf, None)
    assert h5_identity(orchestrator, h5_path) == expected_identity(read_manifest(run_a))
    age(Path(h5_path), Path(meta_path))
    h5_writes.clear()
    service._feature_library = library_for(run_b)  # noqa: SLF001
    h5_path_b, meta_path_b = service._materialize_features_for_ic(run_b.symbol, run_b.tf, None)
    exp_b = expected_identity(read_manifest(run_b))
    assert h5_identity(orchestrator, h5_path_b) == exp_b
    assert meta_identity(meta_path_b) == exp_b


# ---------------------------------------------------------------- mutation


def test_mutation_reuse_ignores_content_sha256(
    cwd_tmp: Path, orchestrator: ICFilterOrchestrator, run_a: Any, run_b: Any, h5_writes: List[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """mutant：沿用條件拿掉 `content_sha256`（身分解析處把該鍵抹成常值）⇒ 重生後沿用舊快取，驗證②翻轉。
    前提：兩 run 之身分只差 `content_sha256`（改動之 K 線在窗尾、不影響校準與紀錄檔）。"""
    exp_a, exp_b = expected_identity(read_manifest(run_a)), expected_identity(read_manifest(run_b))
    assert {k for k in IDENTITY_KEYS if exp_a[k] != exp_b[k]} == {"content_sha256"}, "前提不成立：兩 run 身分差異不只內容身分"
    real = rp.resolve_run_identity

    def blind(manifest: Any, artifact_kind: str) -> Any:
        return dataclasses.replace(real(manifest, artifact_kind), content_sha256="0" * 64)

    assert patch_everywhere(monkeypatch, "resolve_run_identity", real, blind) >= 1
    case = _regeneration_case_blind(orchestrator, run_a, run_b, h5_writes)
    assert not case["h5_rewritten"] or not case["meta_rewritten"], "mutant 下仍重寫——驗證②之 oracle 無鑑別力"


def _regeneration_case_blind(orchestrator: ICFilterOrchestrator, run_a: Any, run_b: Any, h5_writes: List[str]) -> Dict[str, Any]:
    """mutant 版之驗證②流程：同 `_regeneration_case` 但不在首次物化後斷言身分（mutant 下身分已被抹改）。"""
    service = make_service(library_for(run_a))
    service._materialize_features_for_ic(run_a.symbol, run_a.tf, run_a.config_hash)
    paths = cache_paths(run_a)
    age(paths["h5"], paths["meta"])
    h5_writes.clear()
    service._feature_library = library_for(run_b)  # noqa: SLF001
    service._materialize_features_for_ic(run_b.symbol, run_b.tf, run_b.config_hash)
    return {"h5_rewritten": was_rewritten(paths["h5"]), "meta_rewritten": was_rewritten(paths["meta"]),
            "h5_writes": len(h5_writes)}


def test_mutation_only_h5_rewritten_not_meta(
    cwd_tmp: Path, orchestrator: ICFilterOrchestrator, run_a: Any, run_b: Any, h5_writes: List[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """mutant：只重寫 h5、不重寫 meta（物化後把 `_meta.json` 之位元組與 mtime 還原為呼叫前）⇒ 驗證②翻轉。"""
    real = ICAnalysisService._materialize_features_for_ic
    meta_file = cache_paths(run_a)["meta"]

    def keep_meta(self: ICAnalysisService, symbol: str, timeframe: str, config_hash: Optional[str]) -> Any:
        before = (meta_file.read_bytes(), meta_file.stat().st_mtime_ns) if meta_file.exists() else None
        out = real(self, symbol, timeframe, config_hash)
        if before is not None:
            meta_file.write_bytes(before[0])
            os.utime(meta_file, ns=(before[1], before[1]))
        return out

    monkeypatch.setattr(ICAnalysisService, "_materialize_features_for_ic", keep_meta)
    case = _regeneration_case(orchestrator, run_a, run_b, h5_writes)
    assert not case["meta_rewritten"]
    assert case["meta_identity"] != case["exp_b"]
    assert not _regeneration_ok(case)
