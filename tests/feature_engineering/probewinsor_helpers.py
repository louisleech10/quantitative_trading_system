"""PROBEWINSOR（docs/PROBEWINSOR_SPEC.md §G、§V）驗收與凍結共用：設定格、單格真實生成、比較鍵、呼叫點真值表。

設定格之唯一定義＝`tests/_golden/probewinsor/contract.json`；錨點基準＝`tests/_golden/probewinsor/baseline.json`
（`scripts/freeze_probewinsor_baseline.py` 於錨點碼態產出，之後只讀）。單格生成之一切寫入隔離於該格暫存目錄
（cwd、feature registry、CGSA 工作目錄、系統暫存；同 `fftfmeta_golden_helpers.prepare_env` 之隔離語意），結束即刪。
"""
from __future__ import annotations

import contextlib
import copy
import hashlib
import json
import os
import resource
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

REPO = Path(__file__).resolve().parents[2]
CONTRACT_PATH = REPO / "tests" / "_golden" / "probewinsor" / "contract.json"
BASELINE_PATH = REPO / "tests" / "_golden" / "probewinsor" / "baseline.json"

FIXED_ENV = {
    "FFACT_LAYER1_PARALLEL": "0",
    "FFACT_USE_CGSA": "1",
    "FFACT_USE_POLARS": "1",
    "FFACT_L3_PERSIST_MODE": "streaming",
    "FFACT_MULTI_TF_PARALLEL": "0",
}


def contract() -> Dict[str, Any]:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def baseline() -> Dict[str, Any]:
    """錨點基準；不存在 ⇒ FileNotFoundError（Task 1.0 未完成之驗收一律紅）。"""
    return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))


# 凍結之輸入（Task 1.0 來源證明）：產生 baseline 之碼與設定（含生成時經 `config/` symlink 讀取之受版控 YAML）；寫入時須與
# HEAD 一致，並記其 blob 於 baseline
INPUT_PATHSPECS = ("tests/feature_engineering", "tests/_golden/probewinsor/contract.json",
                   "scripts/freeze_probewinsor_baseline.py", "config")
_CONTRACT_REL = "tests/_golden/probewinsor/contract.json"
_PRODUCTION_ROOTS = ("momentum", "api")


def _ls_tree(commit: str, specs: Any) -> Dict[str, str]:
    """`git ls-tree -r <commit> -- <specs>` → {路徑: blob sha}（略 `__pycache__`）；失敗即 RuntimeError。"""
    import subprocess

    proc = subprocess.run(["git", "ls-tree", "-r", "-z", commit, "--", *specs], cwd=str(REPO), capture_output=True,
                          text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"git ls-tree {commit} 失敗：{proc.stderr.strip()}")
    out: Dict[str, str] = {}
    for entry in proc.stdout.split("\0"):
        if not entry:
            continue
        meta, path = entry.split("\t", 1)
        if "__pycache__" not in path:
            out[path] = meta.split()[2]
    return out


# 執行期可能讀入之檔案類型（未追蹤檢查之範圍；.DS_Store、log、.bak 等不會被讀入者不計）
LOADABLE_SUFFIXES = (".py", ".yaml", ".yml", ".json", ".toml", ".csv", ".npy", ".parquet", ".h5", ".pkl")


def production_py_digest(commit: str) -> str:
    """該提交之 `momentum/`、`api/` 全部 .py（路徑與 blob）之 sha256——生產碼之身分（Task 1.0 錨點）。"""
    tree = _ls_tree(commit, _PRODUCTION_ROOTS)
    lines = "".join(f"{p} {b}\n" for p, b in sorted(tree.items()) if p.endswith(".py"))
    return hashlib.sha256(lines.encode("utf-8")).hexdigest()


def production_resource_digest(commit: str) -> str:
    """該提交之 `momentum/`、`api/` 全部受版控之非 .py 檔（執行期讀取之 YAML／JSON 等資源；略 `__pycache__`）之路徑與
    blob 之 sha256——生產碼身分之另一半（與 `production_py_digest` 合為全部受版控檔；Task 1.0 錨點）。"""
    tree = _ls_tree(commit, _PRODUCTION_ROOTS)
    lines = "".join(f"{p} {b}\n" for p, b in sorted(tree.items()) if not p.endswith(".py"))
    return hashlib.sha256(lines.encode("utf-8")).hexdigest()


def kline_sha256() -> str:
    """真實 kline（contract `kline_dir`/kline_cache.h5）之 sha256。"""
    digest = hashlib.sha256()
    with (REPO / contract()["kline_dir"] / "kline_cache.h5").open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


_THREAD_ENV = ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS",
               "NUMEXPR_NUM_THREADS", "NUMBA_NUM_THREADS", "NUMBA_THREADING_LAYER", "PYTHONHASHSEED")


def environment_versions() -> Dict[str, Any]:
    """生成之執行環境：平台（作業系統、架構、Python 實作與編譯器）、數值套件版本、numpy 之 BLAS／LAPACK 後端、
    numba 執行緒層與數、執行緒相關環境變數；baseline 記之、驗收核對與目前相同（環境不同之逐位元比較無意義）。"""
    import importlib.metadata as md
    import platform

    out: Dict[str, Any] = {
        "python": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "python_compiler": platform.python_compiler(),
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
    }
    for dist in ("numpy", "pandas", "numba", "polars", "TA-Lib", "scipy", "pyarrow", "llvmlite"):
        try:
            out[dist] = md.version(dist)
        except md.PackageNotFoundError:
            out[dist] = "absent"
    try:
        import numpy as np

        config = np.show_config(mode="dicts")
        deps = (config or {}).get("Build Dependencies", {})
        out["numpy_blas"] = {k: {f: (deps.get(k) or {}).get(f) for f in ("name", "version", "openblas configuration")}
                             for k in ("blas", "lapack")}
    except Exception as exc:  # noqa: BLE001 — 取不到即記錄原因（仍可比對）
        out["numpy_blas"] = f"unavailable: {type(exc).__name__}"
    try:
        import numba

        out["numba_threading_layer_config"] = str(numba.config.THREADING_LAYER)
        out["numba_num_threads"] = int(numba.config.NUMBA_NUM_THREADS)
    except Exception as exc:  # noqa: BLE001
        out["numba_threading"] = f"unavailable: {type(exc).__name__}"
    out["thread_env"] = {name: os.environ.get(name) for name in _THREAD_ENV}
    return out


def contract_at(commit: str) -> Dict[str, Any]:
    """該提交自身之契約（不讀工作樹）。"""
    return json.loads(_git_show(commit, _CONTRACT_REL))


def _git_show(rev: str, path: str) -> str:
    import subprocess

    proc = subprocess.run(["git", "show", f"{rev}:{path}"], cwd=str(REPO), capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"git show {rev}:{path} 失敗")
    return proc.stdout


def input_blobs(commit: str) -> Dict[str, str]:
    """`INPUT_PATHSPECS` 於該提交之全部檔（路徑 → blob sha）；取不到即 RuntimeError。"""
    return _ls_tree(commit, INPUT_PATHSPECS)


def absent_symbol_violations(commit: str, reader: Optional[Any] = None) -> List[str]:
    """改前碼之內容證明（§P Task 1.0）：**該提交自身之** contract 之 `anchor_absent_symbols`（不讀工作樹，防凍結當下改
    清單）須非空，且所列 [路徑, 字面] 於該提交之檔案內容皆不得出現；回傳違反清單（空＝該提交為本票生產改動前之碼）。
    `reader(commit, path) -> str` 預設 `git show`；讀檔失敗列為違反（fail-closed）。"""
    read = reader or _git_show
    try:
        symbols = json.loads(read(commit, _CONTRACT_REL))["anchor_absent_symbols"]
    except Exception as exc:  # noqa: BLE001 — 讀不到該提交之清單即無法證明改前
        return [f"{commit}:{_CONTRACT_REL} 之 anchor_absent_symbols 讀取失敗：{exc}"]
    if not symbols:
        return [f"{commit}:{_CONTRACT_REL} 之 anchor_absent_symbols 為空"]
    out: List[str] = []
    for path, needle in symbols:
        try:
            text = read(commit, path)
        except Exception as exc:  # noqa: BLE001 — 讀不到即無法證明改前
            out.append(f"{commit}:{path} 讀取失敗：{exc}")
            continue
        if needle in text:
            out.append(f"{commit}:{path} 已含本票生產符號 {needle!r}")
    return out


def present_symbol_violations() -> List[str]:
    """實作後之反向證明：contract `anchor_absent_symbols` 所列字面於工作樹之生產檔皆須存在（清單確為本票之生產符號、
    非空殼）；回傳違反清單。"""
    out: List[str] = []
    symbols = contract()["anchor_absent_symbols"]
    if not symbols:
        return ["anchor_absent_symbols 為空"]
    for path, needle in symbols:
        target = REPO / path
        if not target.is_file() or needle not in target.read_text(encoding="utf-8"):
            out.append(f"{path} 不含 {needle!r}")
    return out


def cell_by_id(cell_id: str) -> Dict[str, Any]:
    for cell in contract()["cells"]:
        if cell["id"] == cell_id:
            return dict(cell)
    raise KeyError(f"contract 無此格：{cell_id}")


def family_of(cell: Dict[str, Any]) -> Dict[str, Any]:
    return dict(contract()["families"][cell["family"]])


def _deep_merge(base: Dict[str, Any], extra: Dict[str, Any]) -> Dict[str, Any]:
    out = copy.deepcopy(base)
    for key, value in extra.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = copy.deepcopy(value)
    return out


def cell_payload(cell: Dict[str, Any], *, fracdiff: Optional[bool] = None, adf: Optional[bool] = None) -> Dict[str, Any]:
    """格之 config_override：族之 base payload（s2＝`icfirstalign_helpers.s2_payload`、fast＝`fftfmeta_golden_helpers.fast_payload`）
    ＋族之 extras＋格之總開關／縮尾子開關；fracdiff／adf 未指定 ⇒ 取族之 `stationarity`（缺＝False；開啟時 apply_to
    ＝non_stationary，同 `ffstat_helpers.stat_payload`）；真值表另行指定。"""
    fam_st = bool(family_of(cell).get("stationarity", False))
    fracdiff = fam_st if fracdiff is None else fracdiff
    adf = fam_st if adf is None else adf
    fam = family_of(cell)
    if fam["base"] == "s2":
        from tests.feature_engineering import icfirstalign_helpers as ih

        payload = ih.s2_payload(list(fam["training"]))
    elif fam["base"] == "fast":
        from tests.feature_engineering import fftfmeta_golden_helpers as fg

        payload = fg.fast_payload(list(fam["training"]), max_nan_ratio=1.0)
    else:
        raise ValueError(f"未知 base：{fam['base']}")
    payload["timeframes"] = {"primary": fam["primary"], "training": list(fam["training"]),
                             "alignment_mode": "open_minus"}
    payload = _deep_merge(payload, fam.get("extras") or {})
    pre = payload["preprocessing"]
    pre["enabled"] = bool(cell["pp"])
    pre["winsorization"] = {**(pre.get("winsorization") or {}), "enabled": bool(cell["winsor"])}
    for step, on in (("fractional_differencing", fracdiff), ("adf_differencing", adf)):
        pre[step] = {**(pre.get(step) or {}), "enabled": bool(on)}
        if on:
            pre[step]["apply_to"] = "non_stationary"
    return payload


def tracked_config_files() -> List[str]:
    """`config/` 下受版控之檔（`git ls-files -z -- config`；頂層，不含子目錄）；取不到即 RuntimeError。"""
    import subprocess

    proc = subprocess.run(["git", "ls-files", "-z", "--", "config"], cwd=str(REPO), capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"git ls-files config 失敗：{proc.stderr.strip()}")
    files = sorted(p for p in proc.stdout.split("\0") if p)
    if not files or any(p.count("/") != 1 for p in files):
        raise RuntimeError(f"config 受版控檔不符預期（須為頂層檔且非空）：{files[:5]}")
    return files


@contextlib.contextmanager
def isolated(work: Path) -> Iterator[Path]:
    """單格寫入隔離：固定環境、cwd 移至 work（`config/` 下只以 symlink 連結受版控之設定檔）、feature registry、CGSA 工作目錄、
    系統暫存與 d* 快取（`FeaturePreprocessor._d_star_cache_dir` 固定指向專案 data_cache，與 cwd 無關 ⇒ 另行導向，
    同 `ffstat_helpers.prepare_stat_env`）皆落 work 之下；離開時還原環境並刪 work。"""
    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    # 只連結受版控之 config 檔：使用者本機之未追蹤設定（如 user_scan_config.yaml，ConfigManager 會合併）不得進入生成
    (work / "config").mkdir()
    for rel in tracked_config_files():
        (work / rel).symlink_to(REPO / rel)
    (work / "sys_tmp").mkdir()
    dstar = work / "dstar_cache"
    dstar.mkdir()
    saved_dstar = FeaturePreprocessor.__dict__["_d_star_cache_dir"]
    env = {**FIXED_ENV,
           "FFACT_FEATURE_REGISTRY_PATH": str(work / "features" / "registry.json"),
           "FFACT_CGSA_WORK_DIR": str(work / "cgsa_work")}
    saved_env = {k: os.environ.get(k) for k in env}
    saved_cwd = os.getcwd()
    saved_tmp = tempfile.tempdir
    try:
        os.environ.update(env)
        os.chdir(work)
        tempfile.tempdir = str(work / "sys_tmp")
        FeaturePreprocessor._d_star_cache_dir = staticmethod(lambda: dstar)
        yield work
    finally:
        FeaturePreprocessor._d_star_cache_dir = saved_dstar
        tempfile.tempdir = saved_tmp
        os.chdir(saved_cwd)
        for key, value in saved_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        shutil.rmtree(work, ignore_errors=True)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _canon(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, default=str)


def _find_key(node: Any, key: str) -> Any:
    """深度優先取第一個名為 key 之值（成品 manifest 與 result.metadata 之鍵位置依層而異）。"""
    if isinstance(node, dict):
        if key in node:
            return node[key]
        for value in node.values():
            found = _find_key(value, key)
            if found is not None:
                return found
    elif isinstance(node, list):
        for value in node:
            found = _find_key(value, key)
            if found is not None:
                return found
    return None


def record_of(factory: Any, result: Any, features_root: Path) -> Dict[str, Any]:
    """§G baseline 內容（每格）：探測狀態取自工廠實例，公開輸出取自成品。"""
    from tests.feature_engineering.ffstat_helpers import public_fingerprints

    metadata = result.metadata if isinstance(getattr(result, "metadata", None), dict) else {}
    docs: List[Any] = [metadata]
    for path in sorted(features_root.rglob("*.json")):
        try:
            docs.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            continue

    def first(key: str) -> Any:
        for doc in docs:
            value = _find_key(doc, key)
            if value is not None:
                return value
        return None

    late_bound = getattr(factory, "_public_warmup_late", None)
    late = sorted(late_bound[1]) if late_bound else None
    fingerprints = public_fingerprints(features_root)
    stable_start = first("stable_start")
    return {
        "config_hash": metadata.get("config_hash"),
        "output_window": metadata.get("output_window"),
        "rounds": [dict(r) for r in (getattr(factory, "_public_warmup_probe", None) or [])],
        "probe_late_count": None if late is None else len(late),
        "probe_late_sha256": None if late is None else _sha("\n".join(late)),
        "first_finite_sha256": _sha(_canon(getattr(factory, "_public_warmup_first_finite", None) or {})),
        "columns": sorted(fingerprints),
        "fingerprints": fingerprints,
        "stable_start_sha256": None if stable_start is None else _sha(_canon(stable_start)),
        "warmup_insufficient_columns": sorted(first("warmup_insufficient_columns") or []),
        "quality_status": first("quality_status"),
    }


def run_cell(cell: Dict[str, Any], work_root: Path) -> Dict[str, Any]:
    """單格真實生成（force_regenerate、persist）→ §G 記錄（另附資訊性之牆鐘與峰值 RSS）。"""
    from momentum.factories import create_feature_factory
    from momentum.FeatureEngineering.feature_storage import FeatureStorage

    spec = contract()
    fam = family_of(cell)
    start, end = fam["window"]
    with isolated(work_root / cell["id"]) as work:
        factory = create_feature_factory(cache_dir=str(REPO / spec["kline_dir"]), validate_continuity=False)
        root = work / "features"
        factory._storage = FeatureStorage(str(root))
        t0 = time.time()
        result = factory.generate_features(spec["symbol"], fam["primary"], config_override=cell_payload(cell),
                                           force_regenerate=True, start_date=start, end_date=end, persist=True)
        elapsed = time.time() - t0
        record = record_of(factory, result, root)
    record["elapsed_seconds"] = round(elapsed, 2)
    record["peak_rss_mb"] = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024 / 1024, 1)
    return record


def diff(a: Dict[str, Any], b: Dict[str, Any], keys: List[str]) -> List[str]:
    """逐鍵比較；fingerprints 逐欄列出不同之欄名。回傳差異描述清單（空＝相等）。"""
    out: List[str] = []
    for key in keys:
        if key == "fingerprints":
            fa, fb = a.get(key) or {}, b.get(key) or {}
            cols = sorted(c for c in set(fa) | set(fb) if fa.get(c) != fb.get(c))
            if cols:
                out.append(f"fingerprints: {len(cols)} 欄不同（例 {cols[:5]}）")
        elif a.get(key) != b.get(key):
            out.append(f"{key}: {a.get(key)!r} != {b.get(key)!r}")
    return out


def keys(kind: str) -> List[str]:
    return list(contract()["compare_keys"][kind])


def truth_table() -> List[Dict[str, Any]]:
    """§V 邊界 08：contract truth_table 各輸入下五個呼叫點之結果（不生成；只解析設定）。"""
    from momentum.factories import create_feature_factory
    from momentum.FeatureEngineering.feature_factory import FeatureFactory
    from momentum.FeatureEngineering.warmup_window import _collect_l65_stack_bars

    spec = contract()
    table = spec["truth_table"]
    factory = create_feature_factory(cache_dir=str(REPO / spec["kline_dir"]), validate_continuity=False)
    rows: List[Dict[str, Any]] = []
    for item in table["inputs"]:
        cell = {"id": "truth", "family": table["family"], "pp": item["pp"], "winsor": item["winsor"]}
        config = factory._resolve_config(cell_payload(cell, fracdiff=item["fracdiff"], adf=item["adf"]))
        mode = factory._resolve_l65_generation_mode(config)
        raw = factory._build_l7_raw_preprocessing_config(config) if mode != "none" else None
        preview = factory._config_manager.preview_feature_count(config)
        rows.append({
            "input": dict(item),
            "stationarity_enabled": bool(FeatureFactory._stationarity_config_enabled(config)),
            "l65_mode": mode,
            "l65_stack_bars": int(_collect_l65_stack_bars(config)),
            "raw_metadata_sha256": _sha(_canon(factory._build_l7_raw_preprocessing_metadata(config, raw, mode))),
            "preview_sha256": _sha(_canon(preview.model_dump() if hasattr(preview, "model_dump") else vars(preview))),
        })
    return rows
