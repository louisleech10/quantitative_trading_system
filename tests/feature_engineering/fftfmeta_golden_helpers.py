"""FF-TFMETA §G golden：真實 kline 小窗 run 之指紋（docs/FFTFMETA_SPEC.md §G）。

基準由 `handoffs/run_receipts/fftfmeta_probes/freeze_baseline.py` 於動工前 HEAD 凍結至
`tests/_golden/fftfmeta/baseline.json`；`test_fftfmeta_golden.py` 於改後以同參數重跑比對。
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import numpy as np
import pyarrow.parquet as pq

from momentum.factories import create_feature_factory
from momentum.FeatureEngineering.feature_storage import FeatureStorage
from tests.feature_engineering.ff_truncation_mr_helpers import (
    _ALL_ATOMIC_CATEGORIES,
    FIXED_ENV,
    GenerationArtifacts,
    _make_factory,
    _run_generation,
)

BASELINE_PATH = Path("tests/_golden/fftfmeta/baseline.json")

SYMBOL = "BTCUSDT"
PRIMARY_TF = "1h"
MULTI_TFS = ["1h", "12h"]

# 允許變動路徑與 run 位置正規化（SPEC §G v5 封閉集）之單一落點：契約 JSON
CONTRACT_PATH = Path(__file__).resolve().parents[1] / "_golden" / "fftfmeta" / "allowed_paths.json"
_CONTRACT = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
COMPLETENESS_KEYS: Tuple[str, ...] = tuple(_CONTRACT["completeness_keys"])
MANIFEST_CONTAINERS: Tuple[str, ...] = tuple(_CONTRACT["manifest_containers"])
MANIFEST_VOLATILE: Tuple[Tuple[str, ...], ...] = tuple(tuple(p) for p in _CONTRACT["manifest_volatile"])
TASK_VOLATILE: Tuple[Tuple[str, ...], ...] = tuple(tuple(p) for p in _CONTRACT["task_volatile"])
ROOT_PLACEHOLDER: str = _CONTRACT["task_root_placeholder"]


def fast_payload(training_tfs: List[str], **overrides: Any) -> Dict[str, Any]:
    """輕量真實 run 設定：只 close 資料源、L6.5 只開 winsorization（控時長；比照 test_failopen_matrix 之 fast 設定）。"""
    payload: Dict[str, Any] = {
        "timeframes": {"primary": PRIMARY_TF, "training": list(training_tfs), "alignment_mode": "open_minus"},
        "data_sources": {"enabled_sources": ["close"], "synthetic_sources": []},
        "atomic_indicators": {c: {"enabled": c == "trend"} for c in _ALL_ATOMIC_CATEGORIES},
        "operators": {"enabled": False},
        "rolling_aggregation": {"enabled": True, "windows": [5, 13]},
        "cross_sectional": {"enabled": False},
        "preprocessing": {
            "enabled": True,
            "mode": "append",
            "causal_preprocessing": True,
            "winsorization": {"enabled": True},
            "rank_transform": {"enabled": False},
            "adaptive_zscore": {"enabled": False},
            "gaussian_normalize": {"enabled": False},
            "adf_differencing": {"enabled": False},
            "fractional_differencing": {"enabled": False},
        },
        "nan_strategy": {"l7_dead_feature_drop": {"enabled": False}},
    }
    payload.update(overrides)
    return payload


def multi_tf_payload() -> Dict[str, Any]:
    """健康多週期 run 之設定（primary 1h、training 1h＋12h）。"""
    return fast_payload(list(MULTI_TFS), **HEALTHY)


def degraded_single_tf_payload() -> Dict[str, Any]:
    """降級單週期 reference：既有設定鍵 max_nan_ratio=0.0（SPEC §G）。"""
    return fast_payload([PRIMARY_TF], max_nan_ratio=0.0)


def run(features_root: Path, payload: Dict[str, Any], start_date: str, end_date: str) -> GenerationArtifacts:
    """以真實 kline 跑一次 persist=True 之 generate_features。"""
    factory = _make_factory(features_root)
    return _run_generation(
        factory,
        features_root=features_root,
        config_payload=payload,
        start_date=start_date,
        end_date=end_date,
        symbol=SYMBOL,
        primary_tf=PRIMARY_TF,
    )


# ---------------------------------------------------------------- 真實 kline 整合 run（Task 2.2／2.3／3.1／3.2）

REPO = Path(__file__).resolve().parents[2]
KLINE_DIR = str(REPO / "data_cache" / "feature_klines")
WINDOW = ("2026-01-01", "2026-01-31")
HEALTHY = {"max_nan_ratio": 1.0}  # 輕量設定之實測 nan_ratio 0.0959 超過預設基線上界 0.0158（2026-09-24 主委實跑）


def prepare_env(monkeypatch: Any, tmp_path: Path, **env: str) -> None:
    """固定環境並把一切寫入隔離到 tmp（r5 codex P1-01：不得碰專案 data_cache）；`env` 覆寫個別鍵。
    - feature registry：`FFACT_FEATURE_REGISTRY_PATH`＝tmp 下（預設為相對 cwd 之 data_cache/features/registry.json）。
    - CGSA 工作目錄：非 parallel 固定於 tmp；parallel 不設——worker 以 `_prepare_cgsa_registry(symbol, tf, "worker")`
      取目錄，設定此變數會使 worker 與主程序共用同一目錄——改把 cwd 移到 tmp，使 `Path.cwd()/data_cache/cgsa_work`
      落在 tmp 且主程序與 worker 各自分目錄；相對路徑讀取之 `config/` 以 symlink 指回 repo（kline 已為絕對路徑）。"""
    merged = {**FIXED_ENV, **env}
    for name, value in merged.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setenv("FFACT_FEATURE_REGISTRY_PATH", str(tmp_path / "features" / "registry.json"))
    monkeypatch.chdir(tmp_path)
    if not (tmp_path / "config").exists():
        (tmp_path / "config").symlink_to(REPO / "config")
    if merged.get("FFACT_MULTI_TF_PARALLEL") == "1":
        monkeypatch.delenv("FFACT_CGSA_WORK_DIR", raising=False)
    else:
        monkeypatch.setenv("FFACT_CGSA_WORK_DIR", str(tmp_path / "cgsa_work"))


def generate(tmp_path: Path, payload: Dict[str, Any], *, primary_tf: str = PRIMARY_TF, persist: bool = True):
    """真實 kline 之 generate_features；回傳 (features_root, factory, result)。"""
    root = tmp_path / "features"
    factory = create_feature_factory(cache_dir=KLINE_DIR, validate_continuity=False)
    factory._storage = FeatureStorage(str(root))
    result = factory.generate_features(
        SYMBOL, primary_tf, config_override=payload, force_regenerate=True,
        start_date=WINDOW[0], end_date=WINDOW[1], persist=persist,
    )
    return root, factory, result


def l7_manifest(root: Path, primary_tf: str, result: Any) -> Dict[str, Any]:
    path = root / SYMBOL / primary_tf / str(result.metadata["config_hash"]) / FeatureStorage.L7_V2_MANIFEST_NAME
    return json.loads(path.read_text(encoding="utf-8"))


def meta_json(root: Path, primary_tf: str) -> Dict[str, Any]:
    """frame／legacy 路徑之 `save_factory_output` 所寫 meta.json。"""
    return json.loads((root / f"{SYMBOL}_{primary_tf}_factory_meta.json").read_text(encoding="utf-8"))


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json(obj: Any) -> bytes:
    """SPEC §G canonical JSON：sort_keys、ensure_ascii=False、緊湊分隔。"""
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str).encode("utf-8")


def _drop_path(obj: Dict[str, Any], path: Iterable[str]) -> None:
    keys = list(path)
    node: Any = obj
    for key in keys[:-1]:
        if not isinstance(node, dict) or key not in node:
            return
        node = node[key]
    if isinstance(node, dict):
        node.pop(keys[-1], None)


def _manifest_containers(manifest: Dict[str, Any]) -> List[Dict[str, Any]]:
    containers = [manifest]
    artifacts = manifest.get("artifacts")
    if isinstance(artifacts, dict):
        for kind in MANIFEST_CONTAINERS:
            if isinstance(artifacts.get(kind), dict):
                containers.append(artifacts[kind])
    return containers


REGISTRY_MANIFEST_KEY: str = _CONTRACT["manifest_location_key"]  # CGSA 工作目錄之絕對路徑（run 位置字面）
REGISTRY_PLACEHOLDER: str = _CONTRACT["manifest_location_placeholder"]


def _work_dir_prefixes() -> List[str]:
    """本次 run 之 CGSA 工作目錄（`FFACT_CGSA_WORK_DIR`，未設則 `cwd/data_cache/cgsa_work`）之字面形（原形與 realpath）。"""
    import os
    base = os.environ.get("FFACT_CGSA_WORK_DIR", "").strip() or str(Path.cwd() / "data_cache" / "cgsa_work")
    forms = {base.rstrip("/"), str(Path(base).resolve()).rstrip("/")}
    return sorted(forms, key=len, reverse=True)


def _normalize_registry_path(node: Any, prefixes: List[str]) -> None:
    """只把工作目錄**前綴**換成定值；其後之相對位置與檔名保留進 digest（r5 codex P2-01：整值替換會掩蓋錯指向）。"""
    if isinstance(node, dict):
        for key, value in node.items():
            if key == REGISTRY_MANIFEST_KEY and isinstance(value, str):
                for pre in prefixes:
                    if value.startswith(pre + "/"):
                        node[key] = REGISTRY_PLACEHOLDER + value[len(pre):]
                        break
            else:
                _normalize_registry_path(value, prefixes)
    elif isinstance(node, list):
        for item in node:
            _normalize_registry_path(item, prefixes)


def strip_manifest(manifest: Dict[str, Any]) -> Dict[str, Any]:
    """去除 manifest 之允許變動路徑，並把 CGSA 工作目錄前綴換成定值。"""
    out = copy.deepcopy(manifest)
    _normalize_registry_path(out, _work_dir_prefixes())
    for container in _manifest_containers(out):
        for key in COMPLETENESS_KEYS:
            container.pop(key, None)
    for path in MANIFEST_VOLATILE:
        _drop_path(out, path)
    return out


def strip_task(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """去除 task record（＝result.metadata）之允許變動路徑。"""
    out = copy.deepcopy(metadata)
    for key in COMPLETENESS_KEYS:
        out.pop(key, None)
    for path in TASK_VOLATILE:
        _drop_path(out, path)
    return out


def allowed_values(manifest: Dict[str, Any], metadata: Dict[str, Any]) -> Dict[str, Any]:
    """允許路徑之實值（改後逐鍵比對預期用）。"""
    containers = _manifest_containers(manifest)
    names = ["root", "raw", "processed"][: len(containers)]
    return {
        "manifest": {
            name: {key: container.get(key) for key in COMPLETENESS_KEYS}
            for name, container in zip(names, containers)
        },
        "task": {key: metadata.get(key) for key in COMPLETENESS_KEYS + ("quality_thresholds",)},
    }


def _column_fingerprint(column: Any) -> Dict[str, Any]:
    values = column.to_numpy(zero_copy_only=False)
    arr = np.asarray(values)
    if arr.dtype.kind == "f":
        nan_mask = np.isnan(arr)
    else:
        nan_mask = np.asarray(column.is_null().to_numpy(zero_copy_only=False))
    native = arr.astype(arr.dtype.newbyteorder("<"), copy=False) if arr.dtype.kind in "fiub" else arr
    value_bytes = native.tobytes() if native.dtype.kind in "fiubM" else canonical_json(arr.tolist())
    return {
        "dtype": str(column.type),
        "shape": [int(arr.shape[0])],
        "nan_mask_sha256": _sha(np.packbits(nan_mask.astype(np.uint8)).tobytes() + str(len(nan_mask)).encode()),
        "values_sha256": _sha(value_bytes),
    }


def fingerprint(artifacts: GenerationArtifacts) -> Dict[str, Any]:
    """群組檔名集合、每群組之逐欄四 hash 摘要、去除允許路徑之 canonical JSON sha256、允許路徑實值。"""
    group_files = sorted(p.name for p in artifacts.raw_dir.glob("*.parquet"))
    groups: Dict[str, str] = {}
    for name in group_files:
        table = pq.read_table(artifacts.raw_dir / name)
        per_column = [[col, _column_fingerprint(table.column(col))] for col in table.column_names]
        groups[name] = _sha(canonical_json(per_column))  # 每群組＝逐欄（欄名序）四 hash 之摘要（SPEC v5 §G）
    manifest = artifacts.manifest
    features_root = str(artifacts.run_dir.parents[2])
    metadata = json.loads(canonical_json(artifacts.metadata).decode("utf-8").replace(features_root, ROOT_PLACEHOLDER))
    return {
        "group_files_sha256": _sha(canonical_json(group_files)),
        "group_count": len(group_files),
        "groups": groups,
        "manifest_stripped_sha256": _sha(canonical_json(strip_manifest(manifest))),
        "task_stripped_sha256": _sha(canonical_json(strip_task(metadata))),
        "allowed": allowed_values(manifest, metadata),
        "manifest_bytes": len(canonical_json(manifest)),
        "task_bytes": len(canonical_json(metadata)),
    }


def load_baseline() -> Dict[str, Any]:
    return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
