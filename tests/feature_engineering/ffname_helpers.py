"""FF-NAME 驗收測試共用 helper（docs/FFNAME_SPEC.md；TODO manifest docs/manifests/FFNAME.json）。

- 資料層規則之單一落點：`tests/_golden/ffname/contract.json`（測試引用之，不另抄）。
- 真實 kline：`data_cache/feature_klines/kline_cache.h5`（經 `ffstat_helpers.kline_frame`）；禁合成 fixture。
- 一切寫入經 `fftfmeta_golden_helpers.prepare_env` 隔離於 tmp。
- 週期與標的一律取自既有 helper 常數或 kline 檔之鍵，不寫死。
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Dict, Iterable, List, Sequence, Tuple

REPO = Path(__file__).resolve().parents[2]
CONTRACT_PATH = REPO / "tests" / "_golden" / "ffname" / "contract.json"
WHITELIST_PATH = REPO / "tests" / "_golden" / "ffname" / "read_whitelist.json"
BASELINE_PATH = REPO / "tests" / "_golden" / "ffname" / "baseline.json"
BASELINE_SHA_PATH = REPO / "tests" / "_golden" / "ffname" / "baseline.sha256"
VECTORS_PATH = REPO / "tests" / "_golden" / "ffname" / "name_vectors.json"
FREEZE_SCRIPT = REPO / "scripts" / "ffname_freeze_baseline.py"
VALUE_RECEIPT = REPO / "handoffs" / "run_receipts" / "ffname-value-invariance.json"

CONTRACT: Dict[str, Any] = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
VALID = CONTRACT["spec_valid_names"]
UNTAGGED = CONTRACT["untagged_names"]
KIND_EXAMPLES = CONTRACT["kind_examples"]
G6_GLOBS = tuple(CONTRACT["g6_new_lag_globs"])
REJECT = CONTRACT["spec_reject_names"]
CATEGORIES = tuple(CONTRACT["categories"])
KINDS = tuple(CONTRACT["kinds"])
NAMING_VERSION = int(CONTRACT["naming_version"])
GATE_KEY = CONTRACT["gate"]["manifest_key"]


def load_freeze_module() -> ModuleType:
    """以檔案路徑載入凍結腳本（handoffs 下，非套件）。"""
    spec = importlib.util.spec_from_file_location("ffname_freeze_baseline", FREEZE_SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["ffname_freeze_baseline"] = module
    spec.loader.exec_module(module)
    return module


def naming() -> ModuleType:
    import momentum.FeatureEngineering.feature_naming as fn

    return fn


def is_g6_new_lag(name: str) -> bool:
    """§G ⑥ 新增 lag 欄（SPEC v21：K1 消費測試依 ⑥ 例外處理）：欄名 parse 之末 op 為 `Lag-k`，且去末 op 之基底
    （標記形）符合契約 `g6_new_lag_globs`（改前因欄名啟發式未加 lag 之 raw 衍生欄）。不可 parse 者不屬之。"""
    import dataclasses
    import fnmatch

    fn = naming()
    try:
        ident = fn.parse_feature_name(name)
    except fn.FeatureNameParseError:
        return False
    if not ident.ops or not str(ident.ops[-1]).startswith("Lag-"):
        return False
    base = fn.format_feature_name(dataclasses.replace(ident, ops=tuple(ident.ops[:-1])))
    return any(fnmatch.fnmatchcase(base, glob) for glob in G6_GLOBS)


def params_str(ident: Any) -> str:
    """身分之 params 段字串形（SPEC v13：`params: tuple[tuple[str, ...], ...]`，外層為配對成員；空 tuple 表無參數段）。"""
    return "~".join("-".join(member) for member in ident.params)


def ops_tuple(ident: Any) -> Tuple[str, ...]:
    """身分之 ops（SPEC v13：`ops: tuple[str, ...]`，每元素為一個 op 段之完整字面）。"""
    return tuple(ident.ops)


def drop_last_op(ident: Any) -> Any:
    """去掉最外層 op 之身分（frozen dataclass；kind 由 parse 機械導出，故經 format→parse 重建）。"""
    import dataclasses

    fn = naming()
    stripped = dataclasses.replace(ident, ops=tuple(ident.ops[:-1]))
    tagged = stripped.tf is not None
    return fn.parse_feature_name(fn.format_feature_name(stripped), tagged=tagged)


def last_op_name(ident: Any) -> str:
    ops = ops_tuple(ident)
    return ops[-1].split("-")[0] if ops else ""


def roundtrip_ok(name: str) -> bool:
    fn = naming()
    try:
        return fn.format_feature_name(fn.parse_feature_name(name)) == name
    except Exception:  # noqa: BLE001 — 任何拋錯皆為往返失敗
        return False


def rejects(name: str, parse=None) -> bool:
    """`parse` 對 `name` 拋 `FeatureNameParseError`（或其子類）⇒ True；接受 ⇒ False。"""
    fn = naming()
    parse = parse or fn.parse_feature_name
    try:
        parse(name)
    except fn.FeatureNameParseError:
        return True
    return False


def parse_untagged(name: str) -> Any:
    """生成期間（儲存標記前）之未標記形欄名（SPEC v13「標記前後兩形」）。"""
    return naming().parse_feature_name(str(name), tagged=False)


def untagged_roundtrip_ok(name: str, timeframe: str) -> bool:
    """未標記形：`parse(name, tagged=False)` 成功，且 `tag_timeframe` 後之完整形往返。"""
    fn = naming()
    try:
        parse_untagged(name)
        full = fn.tag_timeframe(str(name), timeframe)
        return fn.format_feature_name(fn.parse_feature_name(full)) == full
    except Exception:  # noqa: BLE001
        return False


def chain_has(exc: BaseException, exc_type: type) -> bool:
    """例外本身或其 __cause__／__context__ 鏈含 `exc_type`（呼叫端包裝時仍可判定型別）。"""
    seen = set()
    cur: BaseException | None = exc
    while cur is not None and id(cur) not in seen:
        if isinstance(cur, exc_type):
            return True
        seen.add(id(cur))
        cur = cur.__cause__ or cur.__context__
    return False


def patch_everywhere(monkeypatch: Any, original: Any, replacement: Any, prefixes: Sequence[str] = ("momentum", "api")) -> int:
    """把已載入之 momentum／api 模組中**綁定到 `original` 物件**之全部名稱換成 `replacement`；回傳替換數。
    用於 mutation：實作可能以 `from feature_naming import X` 綁名，只換來源模組屬性不足以生效。"""
    count = 0
    for mod_name, mod in list(sys.modules.items()):
        if mod is None or not mod_name.startswith(tuple(prefixes)):
            continue
        for attr, value in list(vars(mod).items()):
            if value is original:
                monkeypatch.setattr(mod, attr, replacement)
                count += 1
    return count


def kline_symbols() -> List[str]:
    """真實 kline 檔中之標的鍵（排序）；不寫死標的。"""
    import h5py

    from tests.feature_engineering.fftfmeta_golden_helpers import KLINE_DIR

    with h5py.File(Path(KLINE_DIR) / "kline_cache.h5", "r") as f:
        return sorted(str(k) for k in f.keys())


def real_slice(rows: int = 800, symbol: str | None = None, timeframe: str | None = None):
    """真實 kline 之尾段切片（DataFrame，來源欄 float64）。"""
    from tests.feature_engineering.ffstat_helpers import PRIMARY_TF, SYMBOL, kline_frame

    frame = kline_frame(symbol or SYMBOL, timeframe or PRIMARY_TF)
    return frame.iloc[-rows:].copy()


def manifest_columns(manifest: Dict[str, Any], artifact: str = "raw") -> List[str]:
    groups = manifest.get("artifacts", {}).get(artifact, {}).get("groups", {}) or manifest.get("groups", {})
    out: List[str] = []
    for info in groups.values():
        out.extend(str(c) for c in (info.get("columns") or []))
    return out


def manifest_group_columns(manifest: Dict[str, Any], artifact: str = "raw") -> Dict[str, List[str]]:
    groups = manifest.get("artifacts", {}).get(artifact, {}).get("groups", {}) or manifest.get("groups", {})
    return {str(gid): [str(c) for c in (info.get("columns") or [])] for gid, info in groups.items()}


def group_layer(group_id: str) -> str:
    """group_id `{tf}_{Lx}_...` 之層別段（週期鍵不含 `_`）。"""
    parts = str(group_id).split("_")
    return parts[1] if len(parts) > 1 else ""


def layer_of_identity(ident: Any) -> str:
    """測試 oracle：由身分推導管線層（最外層 op 決定；SPEC Task 2.4 文法）。"""
    l65 = {"fracdiff", "diff", "rank", "gaussian", "zscore"}
    l3 = {"Mean", "Std", "Min", "Max", "Range", "Slope", "Rank", "ZScore", "Skew", "Kurt"}
    l2 = {"Cross", "Ratio", "Distance", "Momentum", "BinarySignal", "SignedStrength", "TsArgmax", "TsArgmin",
          "TsRank", "DecayLinear", "TsCorr", "Sign", "Log1p", "Abs", "Clip"}
    op = last_op_name(ident)
    ops = ops_tuple(ident)
    if op in l65:
        return "layer6_5"
    if ident.category == "meta":
        return "layer6"
    if ident.category == "cross-sectional":
        return "layer5"
    if op == "Lag":
        return "layer4"
    if ops and op in l3 and "-W" in ops[-1]:
        return "layer3"
    if op in l2:
        return "layer2"
    return "layer1"


def baseline_immutability_problems(sha_path: Path = BASELINE_SHA_PATH, baseline_path: Path = BASELINE_PATH) -> List[str]:
    """審查 r13 P1-05：baseline 不可變——`baseline.sha256` 須存在且等於 baseline.json 之 sha256，
    且 `git log --format=%H -- tests/_golden/ffname/baseline.sha256` 恰 1 筆（Task 0.1 提交後不得再改）。"""
    import hashlib
    import subprocess

    if not sha_path.is_file() or not baseline_path.is_file():
        return ["missing_baseline_or_sha"]
    bad: List[str] = []
    recorded = sha_path.read_text(encoding="utf-8").strip()
    if recorded != hashlib.sha256(baseline_path.read_bytes()).hexdigest():
        bad.append("sha_mismatch")
    rel = str(sha_path.resolve().relative_to(REPO))
    log = subprocess.run(["git", "log", "--format=%H", "--", rel], cwd=str(REPO), capture_output=True, text=True)
    commits = [line for line in log.stdout.splitlines() if line.strip()]
    if log.returncode != 0 or len(commits) != 1:
        bad.append(f"sha_file_commits:{len(commits)}")
    return bad


def write_canonical_run(base: Path, frame: Any, symbol: str, timeframe: str, config_hash: str) -> Tuple[Any, Path]:
    """以正式 `FeatureStorage.write_raw` 寫一個 canonical V2 run（單一群組、欄＝`frame` 之欄、時間軸＝`frame.index`），
    並登記於 `base/registry.json`；回傳 (FeatureLibrary, manifest 路徑)。供「特徵路徑須為 canonical run」之既有
    服務測試替換任意 parquet／h5 路徑（FF-NAME Task 3.4）；值與時間軸取自呼叫端（真實 kline）。"""
    import pandas as pd

    from momentum.FeatureEngineering.feature_library import FeatureLibrary
    from momentum.FeatureEngineering.feature_reader import FeatureReader
    from momentum.FeatureEngineering.feature_registry import FeatureRegistry
    from momentum.FeatureEngineering.feature_storage import FeatureStorage

    storage = FeatureStorage(str(base))
    raw_dir = storage.write_raw(symbol, timeframe, config_hash, {"g": frame.reset_index(drop=True)},
                                row_index=pd.DatetimeIndex(frame.index))
    manifest = raw_dir.parent / "feature_manifest.json"
    registry = FeatureRegistry(Path(base) / "registry.json")
    registry.add({"symbol": symbol, "timeframe": timeframe, "config_hash": config_hash,
                  "hdf5_relative_path": str(manifest)})
    return FeatureLibrary(registry, storage, feature_reader=FeatureReader(str(base))), manifest


def register_canonical_run(manifest: Path, registry_path: Path | None = None) -> Path:
    """把以正式 writer 寫於 `<root>/<symbol>/<tf>/<config_hash>/feature_manifest.json` 之 run 登記於 registry
    （預設 `<root>/registry.json`，同正式生成之預設位置）——FF-NAME Task 3.4（v19）：canonical run＝設定特徵根下
    且 registry 有條目。回傳 manifest。"""
    import os

    from momentum.FeatureEngineering.feature_registry import FeatureRegistry

    run_dir = Path(manifest).parent
    root = run_dir.parents[2]
    env_registry = os.getenv("FFACT_FEATURE_REGISTRY_PATH", "").strip()  # 同 create_feature_library(feature_root=…)
    FeatureRegistry(registry_path or (Path(env_registry) if env_registry else root / "registry.json")).add({
        "symbol": run_dir.parent.parent.name, "timeframe": run_dir.parent.name, "config_hash": run_dir.name,
        "hdf5_relative_path": str(manifest)})
    return Path(manifest)


def iter_new_names_from_baseline() -> Iterable[str]:
    """§G 零件以新 formatter 推導之全部新名（需 Task 0.1 baseline.json）。"""
    freeze = load_freeze_module()
    data = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    for row in data["parts"]:
        part = freeze.NamingPart(**{**row, "params": tuple(tuple(m) for m in (row.get("params") or ())),
                                    "ops": tuple(row.get("ops") or ())})
        yield freeze.derive_new_name(part, row["tf"])
