"""FRAMEPATH Task 1.1：CGSA 指紋基準之凍結與比對（docs/FRAMEPATH_SPEC.md §G、Task 1.1）。

於 HEAD 6e07e0ad（Phase 1 任何生產碼改動之前）以真實 `data_cache/feature_klines/kline_cache.h5` 跑設定矩陣 C1–C9，
寫 `tests/_golden/framepath/cgsa_fingerprint.json`；`tests/feature_engineering/test_framepath_invariance.py`
以同一 `run_cell` 重跑並以 `compare_cell` 逐項比對（無容差）。

設定矩陣（`stat_payload` 級精簡指標、短窗；週期取值由 `ffstat_helpers` 參數給定，比對器不寫死週期或標的）：
- C1 單週期平穩化開；C2 單週期平穩化關；C3 多週期（主週期＋一個較長次週期，`FFACT_MULTI_TF_PARALLEL=0`）平穩化開；
- C4 ＝C1 於 `FFACT_L3_PERSIST_MODE` 之 streaming 與 hybrid 各一（子格 C4-streaming、C4-hybrid）；
- C5 ＝C1 同 work dir 第二次生成（resume 命中）；C6 ＝C3 但 `FFACT_MULTI_TF_PARALLEL=1`；
- C7 ＝C1＋`persist=False`；C8 ＝C1＋`FFACT_L3_PERSIST_MODE=in_memory`；
- C9 ＝C3＋`allow_partial_timeframes=True`，真實 kline 副本刪 `<symbol>/<次週期>` 之 data dataset 並讀回確認缺失，
  子行程啟動前（kline storage 建構前）於其環境把 `LEGACY_KLINE_CACHE_DIR` 指向空受控目錄 ⇒ HEAD 為生成前具名拒絕
  （SPEC v18；非 partial），本格凍結 `run_status=refused` 與拒絕之例外型別及訊息。
- C10 ＝C2＋L4 lag 開＋L5 橫截面開（參考標的取 ffstat_helpers 之橫截面設定；SPEC v19 D1：他格皆不產 L4／L5 欄）。

每格內容（§G baseline 內容）：公開輸出欄名序列 sha256、欄數、列數、時間索引 sha256；逐欄 NaN／inf mask sha256
與 float32 值位元 sha256；平穩化決策表 sha256；manifest 經 `compare_domain.json` 篩選後之 canonical JSON sha256；
run_status、各週期 completeness 與失敗／降級原因；生成路徑收據（L3 落地模式、多週期 serial／parallel、L6.5 CGSA 臂）；
記憶體（`memory_guard._Readings`，根＝該格生成子行程，間隔 0.1 秒）峰值、讀數筆數、秒數。C7 以回傳結果與
completeness metadata 為比對對象。

凍結拒寫條件（§G、Task 1.1 邊界）：C5 與 C1 fingerprint 不等；C1–C8 任一 `run_status` 非 complete；C9 之
`run_status` 非 refused、拒絕原因未指名缺載之 `<symbol>/<次週期>`、或拒絕前留有 parquet／manifest；任一格記憶體 FAIL（讀數 `failed` 非空、`injected`
為真、無讀數、峰值 ≥ 2 GB；C6 無任一讀數含根以外成員）；`ICFA_GUARD_READINGS_FILE` 已設 ⇒ 具名拒跑。

用法：
  PYTHONPATH=. venv/bin/python scripts/freeze_framepath_baseline.py freeze   # 只准於 HEAD 6e07e0ad 碼態執行
  PYTHONPATH=. venv/bin/python scripts/freeze_framepath_baseline.py check    # 重跑並比對，列出差異
真實資料重測試：各格單組串行；委員審查期間不跑。
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
BASELINE_REL = "tests/_golden/framepath/cgsa_fingerprint.json"
COMPARE_DOMAIN_REL = "tests/_golden/framepath/compare_domain.json"
HEAD_COMMIT_PREFIX = "6e07e0ad"
# SPEC v19 D1：C10＝C2＋L4 lag 開＋L5 橫截面開（他格之 stat_payload 皆關 lag 與橫截面 ⇒ L4／L5 原無覆蓋）
CELLS = ("C1", "C2", "C3", "C4-streaming", "C4-hybrid", "C5", "C6", "C7", "C8", "C9", "C10")
LAYER_COVERAGE_CELLS = ("C10",)
# SPEC v18（實作期實測）：HEAD 於 allow_partial 下缺次週期 K 線 ⇒ 生成前具名拒絕（平穩化開：校準前置關卡
# CalibrationError；關：_resolve_public_window 之 L0 ValueError），非 partial ⇒ C9 凍結拒絕之型別與訊息
REFUSED_CELLS = ("C9",)
# SPEC v18 C4（實作期實測）：多週期平穩化開於本短窗下，12h 部分欄起始日前有效值不足校準長度 ⇒ 該等欄逐欄
# 不平穩化、run_status=partial（FF-STAT 既有語意），原因只為 calibration_insufficient_history、週期與層皆 present
CALIBRATION_PARTIAL_CELLS = ("C3", "C6")
CALIBRATION_PARTIAL_REASON = "calibration_insufficient_history:"
DSTAR_CACHE_FLAG = "dstar_cache_hit"
PEAK_LIMIT_BYTES = 2 * 1024 ** 3
SAMPLE_INTERVAL_SECONDS = 0.1
# 每格 fingerprint 之比對項（§G baseline 內容；compare_cell 逐項無容差比對）
FINGERPRINT_KEYS = (
    "column_names_sha256", "column_count", "row_count", "time_index_sha256", "columns", "result_columns",
    "stationarity_decisions_sha256", "manifest_sha256", "run_status", "completeness", "failure_reasons",
    "path_receipt",
)


class FramepathBaselineError(RuntimeError):
    """凍結／比對前置條件不成立（具名拒寫或拒跑）。"""


CODE_STATE_ROOTS = ("momentum", "api", "config")


def code_state_errors(git_runner: Any = None) -> List[str]:
    """凍結前置：工作樹之 `momentum／api／config` 須與錨點 6e07e0ad 逐位元相同——①`git rev-parse 6e07e0ad` 可解析
    ②`git diff --name-only <錨點完整 sha> -- <roots>`（以錨點為比較端、含未提交改動；不得以 HEAD 為比較端）為空
    ③`git ls-files --others --exclude-standard -- <roots>` 為空（未追蹤之原始碼亦屬碼態）；任一不成立 ⇒ 錯誤字串
    （freeze 具名拒寫、不產任何輸出）。執行時 HEAD 可為錨點之後之提交（TODO／審查提交只動 tests／docs），故判準是
    碼態而非 HEAD 值；HEAD 值只記入基準供追溯。`git_runner(args) -> (rc, stdout)` 供測試注入（審查 r17
    CODEX-R17-P1-01、r18 CODEX-R18-P1-01）。
    `__pycache__/` 下之已追蹤 numba／位元組碼快取不屬碼態（任一執行即改寫；同處置閘⑤(b)⑦之過濾，SPEC v16 A5）。"""
    run = git_runner or _git
    rc, out = run(["rev-parse", HEAD_COMMIT_PREFIX])
    if rc != 0 or not out.strip():
        return [f"無法解析錨點 {HEAD_COMMIT_PREFIX}"]
    anchor = out.strip()
    errors: List[str] = []
    rc, out = run(["diff", "--name-only", anchor, "--", *CODE_STATE_ROOTS])
    changed = [p for p in out.splitlines() if p.strip() and "/__pycache__/" not in p]
    if rc != 0:
        errors.append(f"git diff 失敗 rc={rc}")
    elif changed:
        errors.append(f"碼態與錨點 {anchor[:8]} 不同：{changed[:20]}")
    rc, out = run(["ls-files", "--others", "--exclude-standard", "--", *CODE_STATE_ROOTS])
    untracked = [p for p in out.splitlines() if p.strip() and "/__pycache__/" not in p]
    if rc != 0:
        errors.append(f"git ls-files 失敗 rc={rc}")
    elif untracked:
        errors.append(f"碼態含未追蹤原始碼：{untracked[:20]}")
    return errors


def _git(args: List[str]) -> Tuple[int, str]:
    proc = subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True)
    return proc.returncode, proc.stdout


def resolve_commits(git_runner: Any = None) -> Dict[str, str]:
    """{"code_anchor": `git rev-parse 6e07e0ad` 之完整 sha, "head_commit": `git rev-parse HEAD`}——兩次獨立解析，
    freeze 寫入基準（審查 r19 CODEX-R19-P1-02）。"""
    run = git_runner or _git
    out: Dict[str, str] = {}
    for key, rev in (("code_anchor", HEAD_COMMIT_PREFIX), ("head_commit", "HEAD")):
        rc, text = run(["rev-parse", rev])
        if rc != 0 or not text.strip():
            raise FramepathBaselineError(f"git rev-parse {rev} 失敗")
        out[key] = text.strip()
    return out


_KEY_SEGMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _path_segments(path: Any) -> List[str]:
    """compare_domain path 語法（封閉）：以 . 分隔之物件鍵；中間層可有恰一個 `*`；末段須為物件鍵。"""
    if not isinstance(path, str) or not path:
        raise FramepathBaselineError(f"compare_domain path 空或非字串：{path!r}")
    segs = path.split(".")
    if any(s != "*" and not _KEY_SEGMENT.match(s) for s in segs):
        raise FramepathBaselineError(f"compare_domain path 語法不合：{path!r}")
    if segs[-1] == "*" or segs.count("*") > 1:
        raise FramepathBaselineError(f"compare_domain path 萬用位置不合：{path!r}")
    return segs


def load_compare_domain(path: Path = REPO / COMPARE_DOMAIN_REL) -> Dict[str, Any]:
    """讀 `compare_domain.json` 並驗：category ∈ allowed_categories；path 之最後一段不屬 forbidden keys 或
    `feature_storage.COMPLETENESS_FIELD_NAMES`；path 語法只含物件鍵與單層 `*`。違反 ⇒ `FramepathBaselineError`。"""
    from momentum.FeatureEngineering.feature_storage import COMPLETENESS_FIELD_NAMES

    domain = json.loads(Path(path).read_text(encoding="utf-8"))
    allowed = set(domain.get("allowed_categories") or [])
    forbidden = set((domain.get("forbidden_exclusions") or {}).get("keys") or []) | set(COMPLETENESS_FIELD_NAMES)
    if not allowed or not forbidden:
        raise FramepathBaselineError("compare_domain 缺 allowed_categories 或 forbidden_exclusions.keys")
    exclude = domain.get("exclude")
    if not isinstance(exclude, list):
        raise FramepathBaselineError("compare_domain.exclude 須為陣列")
    for entry in exclude:
        if not isinstance(entry, dict) or set(entry) != {"path", "category", "source"}:
            raise FramepathBaselineError(f"compare_domain.exclude 項欄位不合：{entry!r}")
        segs = _path_segments(entry["path"])
        if entry["category"] not in allowed:
            raise FramepathBaselineError(f"compare_domain category 不允許：{entry['category']!r}")
        if segs[-1] in forbidden:
            raise FramepathBaselineError(f"compare_domain 不得排除 {segs[-1]!r}")
    return domain


def _drop_scalar(node: Any, segs: List[str], path: str) -> None:
    if not isinstance(node, dict):
        return  # 只走物件；不進陣列
    head, rest = segs[0], segs[1:]
    if not rest:
        if head in node:
            if isinstance(node[head], (dict, list)):
                raise FramepathBaselineError(f"排除鍵 {path} 指向物件／陣列（不得整段排除）")
            del node[head]
        return
    targets = list(node.values()) if head == "*" else ([node[head]] if head in node else [])
    for child in targets:
        _drop_scalar(child, rest, path)


def filter_manifest(manifest: Mapping[str, Any], domain: Mapping[str, Any]) -> Dict[str, Any]:
    """依 domain.exclude 刪除 manifest 中匹配之純量鍵；匹配到物件或陣列 ⇒ `FramepathBaselineError`（防祖先鍵整段排除）。"""
    out = copy.deepcopy(dict(manifest))
    for entry in domain["exclude"]:
        _drop_scalar(out, _path_segments(entry["path"]), entry["path"])
    return out


def _canonical_sha256(obj: Any) -> str:
    text = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def manifest_sha256(manifest: Mapping[str, Any], domain: Mapping[str, Any]) -> str:
    """`filter_manifest` 後之 canonical JSON（sort_keys、(",", ":")、ensure_ascii=False）utf-8 sha256。"""
    return _canonical_sha256(filter_manifest(manifest, domain))


def cell_settings(cell: str) -> Dict[str, Any]:
    """格之設定：payload（ffstat_helpers.stat_payload 系）、env 覆寫、training_tfs、persist、repeat（C5＝2）、
    allow_partial、drop_secondary（C9）。週期與標的一律取自 ffstat_helpers 常數。"""
    from tests.feature_engineering import fftfmeta_golden_helpers as fg
    from tests.feature_engineering import ffstat_helpers as fh

    if cell not in CELLS:
        raise FramepathBaselineError(f"未知設定格 {cell!r}")
    multi = cell in ("C3", "C6", "C9")
    training = list(fg.MULTI_TFS) if multi else [fh.PRIMARY_TF]
    stationarity = cell not in ("C2", *LAYER_COVERAGE_CELLS)
    payload = fh.stat_payload(training, fracdiff=stationarity, adf=stationarity,
                              cross_sectional=cell in LAYER_COVERAGE_CELLS)
    if cell in LAYER_COVERAGE_CELLS:
        payload["lag_features"] = {"enabled": True}
    env: Dict[str, str] = {"FFACT_MULTI_TF_PARALLEL": "1" if cell == "C6" else "0"}
    if cell in ("C4-streaming", "C4-hybrid"):
        env["FFACT_L3_PERSIST_MODE"] = cell.split("-", 1)[1]
    if cell == "C8":
        env["FFACT_L3_PERSIST_MODE"] = "in_memory"
    if cell == "C9":
        payload["allow_partial_timeframes"] = True
    return {
        "symbol": fh.SYMBOL,
        "primary_timeframe": fh.PRIMARY_TF,
        "training_tfs": training,
        "payload": payload,
        "env": env,
        "persist": cell != "C7",
        "repeat": 2 if cell == "C5" else 1,
        "drop_secondary": training[-1] if cell == "C9" else None,
    }


def generate_cell(cell: str, work_root: Path, *, force_regenerate_second: bool = False) -> Dict[str, Any]:
    """行程內跑一格生成並回傳 {"fingerprint", "receipt"}（不含記憶體；`run_cell` 於子行程呼叫本函式並取樣）。
    `receipt["resume_entered"]`＝第二次生成期間 `ColumnGroupRegistry.resume_from_manifest` 對本格 work dir 實際被呼叫
    （以包裝該 classmethod 之 spy 觀測，不以格名推定；另記 `resume_groups`＝其回傳 registry 之群組數，HEAD 實測已完成
    run 為 0；SPEC v16 A10）；C9 於本函式內、任何 kline storage 建構之前把 `LEGACY_KLINE_CACHE_DIR` 設為受控空目錄並於
    結束還原（行程內呼叫時測試端可直接觀測 KlineStorageManager.legacy_cache_dir；審查 r24）；只 C5 有第二次生成，其兩次皆以
    `force_regenerate=False`。`force_regenerate_second=True` 只供 mutation 測試（第二次強制重算 ⇒ resume_entered 須 False）。"""
    from _pytest.monkeypatch import MonkeyPatch

    from momentum.FeatureEngineering.core.column_group_registry import ColumnGroupRegistry
    from tests.feature_engineering import ffstat_helpers as fh

    settings = cell_settings(cell)
    work_dir = Path(work_root).resolve()
    work_dir.mkdir(parents=True, exist_ok=True)
    receipt: Dict[str, Any] = {"resume_entered": False}
    kline_dir = fh.KLINE_DIR
    mp = MonkeyPatch()
    try:
        fh.prepare_stat_env(mp, work_dir, **settings["env"])
        if settings["drop_secondary"]:
            kline_dir, c9 = _prepare_partial_kline(work_dir, settings, kline_dir)
            receipt.update(c9)
            mp.setenv("LEGACY_KLINE_CACHE_DIR", c9["legacy_kline_dir"])  # kline storage 建構前
            receipt["child_env"] = {"LEGACY_KLINE_CACHE_DIR": os.environ["LEGACY_KLINE_CACHE_DIR"]}
        force = settings["repeat"] == 1
        if cell in REFUSED_CELLS:
            try:
                fh.run_stat(work_dir, settings["payload"], persist=settings["persist"], force_regenerate=force,
                            kline_dir=kline_dir)
            except Exception as exc:  # noqa: BLE001 — 拒絕之型別與訊息即本格指紋（改後須相同）
                return {"fingerprint": _refused_fingerprint(settings, work_dir / "features", exc),
                        "receipt": receipt}
            raise FramepathBaselineError(f"{cell}：缺次週期之生成未被拒絕（HEAD 實測為具名拒絕）")
        root, _factory, result = fh.run_stat(work_dir, settings["payload"], persist=settings["persist"],
                                             force_regenerate=force, kline_dir=kline_dir)
        if settings["repeat"] == 2:
            calls: List[Tuple[str, int]] = []
            original = ColumnGroupRegistry.__dict__["resume_from_manifest"]

            def observed(cls: Any, wd: Any) -> Any:
                registry = original.__get__(None, cls)(wd)
                calls.append((str(wd), len(list(registry.iter_all())) if registry is not None else -1))
                return registry

            mp.setattr(ColumnGroupRegistry, "resume_from_manifest", classmethod(observed))
            root, _factory, result = fh.run_stat(work_dir, settings["payload"], persist=settings["persist"],
                                                 force_regenerate=force_regenerate_second, kline_dir=kline_dir)
            mine = [c for c in calls if str(work_dir) in str(Path(c[0]).resolve())]
            receipt["resume_entered"] = bool(mine)
            receipt["resume_groups"] = mine[-1][1] if mine else None
        fingerprint = _fingerprint(settings, root, result)
    finally:
        mp.undo()
    return {"fingerprint": fingerprint, "receipt": receipt}


def _prepare_partial_kline(work_dir: Path, settings: Mapping[str, Any], source_dir: str) -> Tuple[str, Dict[str, Any]]:
    """C9 前置：真實 kline 之受控複本刪 `<symbol>/<次週期>/data`（刪前存在、刪後讀回缺失）＋受控空 legacy 目錄；
    任一前置不成立 ⇒ 具名拒跑。"""
    import h5py

    symbol, tf = settings["symbol"], settings["drop_secondary"]
    source = Path(source_dir) / "kline_cache.h5"
    copy_dir = work_dir / "klines"
    copy_dir.mkdir(parents=True, exist_ok=True)
    target = copy_dir / "kline_cache.h5"
    shutil.copy2(source, target)
    dataset = f"{symbol}/{tf}"
    with h5py.File(target, "r+") as h5:
        before = "present" if f"{dataset}/data" in h5 else "missing"
        if before != "present":
            raise FramepathBaselineError(f"C9 前置不成立：{dataset}/data 於 kline 複本不存在")
        del h5[f"{dataset}/data"]
    with h5py.File(target, "r") as h5:
        after = "missing" if f"{dataset}/data" not in h5 else "present"
    if after != "missing":
        raise FramepathBaselineError(f"C9 前置不成立：{dataset}/data 刪後讀回仍存在")
    legacy = work_dir / "legacy_kline_empty"
    legacy.mkdir(parents=True, exist_ok=True)
    entries = sorted(p.name for p in legacy.iterdir())
    if entries:
        raise FramepathBaselineError(f"C9 前置不成立：受控 legacy 目錄非空 {entries}")
    return str(copy_dir), {
        "symbol": symbol, "source_kline": str(source), "kline_copy": str(target),
        "primary_timeframe": settings["primary_timeframe"], "dropped_timeframe": tf, "deleted_dataset": dataset,
        "readback_before": before, "deleted_readback": after, "legacy_kline_dir": str(legacy),
        "legacy_kline_dir_entries_at_start": entries,
    }


_NON_FEATURE_COLUMNS = ("timestamp", "__index_level_0__", "index")


def _refused_fingerprint(settings: Mapping[str, Any], root: Path, exc: BaseException) -> Dict[str, Any]:
    """拒絕格之指紋：run_status＝refused、failure_reasons＝[「例外型別: 訊息」]；落盤樹須無任何 parquet／manifest
    （拒絕前不得留產物），其餘項取空值之確定性摘要。"""
    leftovers = sorted(str(p.relative_to(root)) for p in Path(root).rglob("*")
                       if p.is_file() and (p.suffix == ".parquet" or p.name.endswith("manifest.json"))) \
        if Path(root).exists() else []
    return {
        "column_names_sha256": _canonical_sha256([]), "column_count": 0, "row_count": 0,
        "time_index_sha256": _canonical_sha256([]), "columns": {},
        "result_columns": {"names_sha256": _canonical_sha256([]), "columns": {}},
        "stationarity_decisions_sha256": _canonical_sha256({}), "manifest_sha256": _canonical_sha256({}),
        "run_status": "refused", "completeness": {"leftover_artifacts": leftovers},
        "failure_reasons": [f"{type(exc).__name__}: {exc}"],
        "path_receipt": {"l3_persist_mode": os.environ.get("FFACT_L3_PERSIST_MODE"),
                         "multi_tf": "parallel" if os.environ.get("FFACT_MULTI_TF_PARALLEL") == "1" else "serial",
                         "persist": bool(settings["persist"]), "generations": int(settings["repeat"])},
    }


def _column_fingerprint(values: Any) -> Dict[str, str]:
    """逐欄：dtype、NaN mask、inf mask（packbits）與 float32 值位元（非有限值以 0 代）sha256。"""
    import numpy as np

    raw = np.asarray(values)
    arr = raw.astype(np.float32)
    nan, inf = np.isnan(arr), np.isinf(arr)
    vals = np.where(np.isfinite(arr), arr, np.float32(0)).astype(np.float32)
    return {"dtype": str(raw.dtype), "nan": hashlib.sha256(np.packbits(nan).tobytes()).hexdigest(),
            "inf": hashlib.sha256(np.packbits(inf).tobytes()).hexdigest(),
            "values": hashlib.sha256(vals.tobytes()).hexdigest()}


def _registry_columns(manifest_path: Path, columns: Dict[str, Dict[str, str]]) -> Tuple[List[str], Dict[str, Any]]:
    """CGSA registry 工作目錄（manifest.json＋群組 .npy）之逐欄指紋寫入 `columns`（鍵＝`<group_id>/<欄名>`）；回傳
    (欄序, manifest)。manifest 缺、群組無 npy_path 或有 shards、欄數與陣列不符 ⇒ 具名拒跑（不靜默略過）。"""
    import numpy as np

    if not manifest_path.is_file():
        raise FramepathBaselineError(f"persist=False 之 registry manifest 不存在：{manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    names: List[str] = []
    for group in manifest.get("groups") or []:
        if not group.get("npy_path") or group.get("shards"):
            raise FramepathBaselineError(f"registry 群組 {group.get('group_id')} 無單一 npy（shards 未支援）")
        arr = np.load(manifest_path.parent / group["npy_path"], mmap_mode="r")
        cols = list(group.get("columns") or [])
        if arr.ndim != 2 or arr.shape[1] != len(cols):
            raise FramepathBaselineError(f"registry 群組 {group['group_id']} 欄數 {len(cols)} 與陣列 {arr.shape} 不符")
        for i, col in enumerate(cols):
            key = f"{group['group_id']}/{col}"
            if key in columns:
                raise FramepathBaselineError(f"registry 欄重複：{key}")
            names.append(key)
            columns[key] = _column_fingerprint(np.asarray(arr[:, i]))
    return names, manifest


def _fingerprint(settings: Mapping[str, Any], root: Path, result: Any) -> Dict[str, Any]:
    """§G baseline 內容（落盤者讀 L7 V2 parquet 與 manifest；C7 無落盤 ⇒ 回傳結果與 completeness metadata）。"""
    import pyarrow.parquet as pq

    from momentum.FeatureEngineering.feature_storage import COMPLETENESS_FIELD_NAMES, FeatureStorage

    md = dict(result.metadata)
    domain = load_compare_domain()
    names: List[str] = []
    columns: Dict[str, Dict[str, str]] = {}
    time_parts: List[str] = []
    manifests: Dict[str, Any] = {}
    root = Path(root)
    for p in sorted(root.rglob("*.parquet")) if root.exists() else []:
        rel = str(p.relative_to(root))
        table = pq.read_table(p)
        if p.name == "timestamps.parquet":
            time_parts.append(rel + ":" + "|".join(
                hashlib.sha256(table.column(n).to_numpy(zero_copy_only=False).tobytes()).hexdigest()
                for n in table.column_names))
            continue
        for n in table.column_names:
            if n in _NON_FEATURE_COLUMNS:
                continue
            if n in columns:
                raise FramepathBaselineError(f"欄名重複：{n}")
            names.append(n)
            columns[n] = _column_fingerprint(table.column(n).to_numpy(zero_copy_only=False))
    for m in sorted(root.rglob(FeatureStorage.L7_V2_MANIFEST_NAME)) if root.exists() else []:
        manifests[str(m.relative_to(root))] = filter_manifest(json.loads(m.read_text(encoding="utf-8")), domain)
    # 審查 r41 CODEX-R41-P1-01：回傳之 features_df 逐欄指紋（每格皆記；C7 無落盤時為其唯一之值比對對象）
    frame = result.features_df
    result_columns = {"names_sha256": _canonical_sha256([str(c) for c in frame.columns]),
                      "columns": {str(c): _column_fingerprint(frame[c].to_numpy()) for c in frame.columns}}
    if len(result_columns["columns"]) != len(frame.columns):
        raise FramepathBaselineError("回傳 features_df 欄名重複")
    index = frame.index
    time_parts.append("result_index:" + hashlib.sha256(
        index.asi8.tobytes() if hasattr(index, "asi8") else json.dumps([str(i) for i in index]).encode()).hexdigest())
    if not settings["persist"]:
        # 審查 r41 CODEX-R41-P1-01：CGSA 之 persist=False 回傳空 features_df（實測 0 欄），產出留在 registry 工作目錄之
        # 群組 .npy ⇒ C7 之值比對對象＝registry manifest（metadata.manifest_path）所列全部群組之逐欄指紋
        names, registry_manifest = _registry_columns(Path(str(md.get("manifest_path") or "")), columns)
        manifests["registry"] = filter_manifest(registry_manifest, domain)
        if len(names) != int(md.get("feature_count", -1)):
            raise FramepathBaselineError(f"registry 欄數 {len(names)} ≠ 回傳 feature_count {md.get('feature_count')}")
    completeness = {k: md.get(k) for k in COMPLETENESS_FIELD_NAMES}
    completeness["quality_status"] = md.get("quality_status")
    if "skipped_timeframes" in md:
        completeness["skipped_timeframes"] = md.get("skipped_timeframes")
    multi = len(settings["training_tfs"]) > 1
    # d* 快取命中旗標屬來源（同 work dir 第二次生成重用第一次寫入之 d* 快取），非決策值：自決策表指紋剔出、
    # 另記於 path_receipt（同格基準與改後仍逐位元比對；C5／C1 互比時與 path_receipt 一併剔除）——SPEC v18 C4
    decisions = {col: ({k: v for k, v in d.items() if k != DSTAR_CACHE_FLAG} if isinstance(d, dict) else d)
                 for col, d in (md.get("stationarity_decisions") or {}).items()}
    cache_hits = sorted(col for col, d in (md.get("stationarity_decisions") or {}).items()
                        if isinstance(d, dict) and d.get(DSTAR_CACHE_FLAG))
    return {
        "column_names_sha256": _canonical_sha256(names),
        "column_count": len(names),
        "row_count": int(len(index)),
        "time_index_sha256": hashlib.sha256("\n".join(time_parts).encode("utf-8")).hexdigest(),
        "columns": columns,
        "result_columns": result_columns,
        "stationarity_decisions_sha256": _canonical_sha256(decisions),
        "manifest_sha256": _canonical_sha256(manifests),
        "run_status": md.get("run_status"),
        "completeness": completeness,
        "failure_reasons": list(md.get("failure_reasons") or []),
        "path_receipt": {
            "l3_persist_mode": os.environ.get("FFACT_L3_PERSIST_MODE"),
            "multi_tf": ("parallel" if os.environ.get("FFACT_MULTI_TF_PARALLEL") == "1" else "serial") if multi
            else "single",
            "l65_mode": md.get("l65_mode"),
            "persist": bool(settings["persist"]),
            "generations": int(settings["repeat"]),
            "manifests": sorted(manifests),
            "dstar_cache_hits": {"count": len(cache_hits), "sha256": _canonical_sha256(cache_hits)},
        },
    }


def summarize_readings(samples: List[Mapping[str, Any]], root: int) -> Dict[str, Any]:
    """`_Readings.sample()` 逐筆讀數 → 記憶體摘要（純函式；審查 r26 CODEX-R26-P1-02）：
    {"readings": 筆數, "peak_bytes": 各筆 footprint 最大值（無讀數＝0）, "failed": 各筆 failed pid 之排序聯集,
    "injected": 任一筆 injected 為真, "non_root_member_seen": 任一筆 members 含 pid ≠ root,
    "root_missing": members 不含 root 之筆數（含 members 為空者；審查 r27）}。`run_cell` 之 memory 除 `seconds` 外須等於本函式對其實際取樣
    結果之輸出，不得另行填值。"""
    failed: set = set()
    non_root = False
    root_missing = 0
    for row in samples:
        failed.update(int(p) for p in row.get("failed") or [])
        pids = {int(m["pid"]) for m in row.get("members") or []}
        non_root = non_root or any(p != int(root) for p in pids)
        root_missing += int(int(root) not in pids)
    return {
        "readings": len(samples),
        "peak_bytes": max((int(row.get("footprint") or 0) for row in samples), default=0),
        "failed": sorted(failed),
        "injected": any(bool(row.get("injected")) for row in samples),
        "non_root_member_seen": non_root,
        "root_missing": root_missing,
    }


def run_cell(cell: str, work_root: Path) -> Dict[str, Any]:
    """於子行程跑一格生成，父行程以 `memory_guard._Readings`（根＝子行程）每 0.1 秒取樣——取樣器一律於呼叫當下以
    模組屬性 `memory_guard._Readings(memory_guard._System(), <子行程 pid>)` 建構並呼叫其 `sample()`（測試以
    monkeypatch 置換該屬性觀測實際讀數），memory＝`summarize_readings(<全部讀數>, <子行程 pid>)` 加 `seconds`；回傳
    {"fingerprint": {FINGERPRINT_KEYS…}, "memory": {"peak_bytes", "readings", "seconds", "non_root_member_seen"},
    "receipt": {"resume_entered": bool（第二次生成進入 CGSA resume 分支之觀測值，見 generate_cell；C5 須 True、其餘格須
    False——SPEC v16 A10）, …，C9 另含 symbol、source_kline、kline_copy、
    primary_timeframe、dropped_timeframe、deleted_dataset（`<symbol>/<次週期>`）、readback_before（"present"）、deleted_readback
    （"missing"）、legacy_kline_dir、legacy_kline_dir_entries_at_start（[]）、child_env（子行程實際之
    LEGACY_KLINE_CACHE_DIR）——審查 r19 CODEX-R19-P1-06}}。`ICFA_GUARD_READINGS_FILE` 已設 ⇒ 拒跑。

    子行程寫完結果檔後阻塞於 stdin，父行程見結果檔即停止取樣再關 stdin——取樣期間根行程恆存活（不取到已結束之根）。"""
    from momentum.FeatureEngineering import memory_guard

    if os.environ.get(memory_guard.READINGS_ENV, "").strip():
        raise FramepathBaselineError(f"{memory_guard.READINGS_ENV} 已設（注入讀數）⇒ 拒跑")
    work_dir = Path(work_root).resolve() / cell
    work_dir.mkdir(parents=True, exist_ok=True)
    out_json = work_dir / "cell_result.json"
    log_path = work_dir / "cell_child.log"
    env = dict(os.environ, PYTHONPATH=str(REPO))
    samples: List[Dict[str, Any]] = []
    with open(log_path, "wb") as log:
        started = time.monotonic()
        proc = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "_child", cell, str(work_dir),
                                 str(out_json)], cwd=str(REPO), env=env, stdin=subprocess.PIPE, stdout=log,
                                stderr=subprocess.STDOUT)
        try:
            sampler = memory_guard._Readings(memory_guard._System(), proc.pid)
            while not out_json.exists() and proc.poll() is None:
                samples.append(sampler.sample())
                time.sleep(SAMPLE_INTERVAL_SECONDS)
            seconds = time.monotonic() - started
        finally:
            if proc.stdin is not None:
                proc.stdin.close()
            rc = proc.wait()
    if rc != 0 or not out_json.exists():
        tail = log_path.read_text(encoding="utf-8", errors="replace")[-3000:]
        raise FramepathBaselineError(f"{cell} 子行程失敗 rc={rc}：{tail}")
    payload = json.loads(out_json.read_text(encoding="utf-8"))
    memory = summarize_readings(samples, proc.pid)
    memory["seconds"] = round(seconds, 3)
    return {"fingerprint": payload["fingerprint"], "memory": memory, "receipt": payload["receipt"]}


def _child_main(cell: str, work_dir: str, out_json: str) -> int:
    """子行程：跑一格、原子寫結果檔，之後阻塞讀 stdin 至 EOF（父行程停止取樣後關閉）。"""
    out = generate_cell(cell, Path(work_dir))
    tmp = Path(out_json + ".tmp")
    tmp.write_text(json.dumps(out, ensure_ascii=False, sort_keys=True, default=str), encoding="utf-8")
    os.replace(tmp, out_json)
    sys.stdin.read()
    return 0


def memory_gate_errors(cell: str, memory: Mapping[str, Any]) -> List[str]:
    """§G 記憶體閘：讀數 failed 非空、injected、無讀數、峰值 ≥ PEAK_LIMIT_BYTES、C6 無根以外成員、root_missing > 0
    （任一筆讀數之 members 不含根〔含空〕，審查 r26／r27）⇒ 錯誤字串。"""
    errors: List[str] = []
    if memory.get("failed") != []:
        errors.append(f"{cell}：讀數 failed 非空或缺 {memory.get('failed')!r}")
    if memory.get("injected") is not False:
        errors.append(f"{cell}：injected 非 False")
    if not isinstance(memory.get("readings"), int) or memory["readings"] <= 0:
        errors.append(f"{cell}：無讀數")
    if not isinstance(memory.get("peak_bytes"), int) or memory["peak_bytes"] >= PEAK_LIMIT_BYTES:
        errors.append(f"{cell}：峰值 {memory.get('peak_bytes')!r} ≥ {PEAK_LIMIT_BYTES} 或缺")
    if memory.get("root_missing") != 0:
        errors.append(f"{cell}：讀數缺根 {memory.get('root_missing')!r}")
    if cell == "C6" and memory.get("non_root_member_seen") is not True:
        errors.append("C6：無任一讀數含根以外成員（平行 worker 未被取樣）")
    return errors


def compare_cell(baseline: Mapping[str, Any], fresh: Mapping[str, Any]) -> List[str]:
    """逐項（FINGERPRINT_KEYS；columns 逐欄之 NaN／inf mask 與 float32 值位元 sha256）無容差比對；回傳
    「項目／欄名」差異列表（空＝相等）。不得含任何週期或標的字面。"""
    diffs: List[str] = []
    for key in FINGERPRINT_KEYS:
        if (key in baseline) != (key in fresh):
            diffs.append(f"{key}：單側缺項（基準 {key in baseline}、改後 {key in fresh}）")
            continue
        if key not in baseline:
            continue  # 兩側皆無（呼叫端明示剔除之項，如 C5／C1 比對剔除 path_receipt）
        if key == "columns":
            diffs += _column_diffs(key, baseline[key] or {}, fresh[key] or {})
        elif key == "result_columns" and isinstance(baseline[key], dict) and isinstance(fresh[key], dict):
            if baseline[key].get("names_sha256") != fresh[key].get("names_sha256"):
                diffs.append(f"{key}／names_sha256")
            diffs += _column_diffs(key, baseline[key].get("columns") or {}, fresh[key].get("columns") or {})
        elif baseline[key] != fresh[key]:
            diffs.append(f"{key}：{baseline[key]!r} != {fresh[key]!r}")
    return diffs


def _column_diffs(key: str, base_cols: Mapping[str, Any], new_cols: Mapping[str, Any]) -> List[str]:
    diffs = [f"{key}／{name}：改後缺欄" for name in sorted(set(base_cols) - set(new_cols))]
    diffs += [f"{key}／{name}：改後多欄" for name in sorted(set(new_cols) - set(base_cols))]
    for name in sorted(set(base_cols) & set(new_cols)):
        for item in sorted(set(base_cols[name]) | set(new_cols[name])):
            if base_cols[name].get(item) != new_cols[name].get(item):
                diffs.append(f"{key}／{name}／{item}")
    return diffs


def _freeze_refusals(cells: Mapping[str, Mapping[str, Any]]) -> List[str]:
    """凍結拒寫條件（Task 1.1 邊界）：C5 與 C1 fingerprint 不等、run_status 不合、C9 次週期未入 failed／skipped、
    任一格 memory_gate_errors 非空、C5 resume_entered 非 True 或他格非 False ⇒ 錯誤字串。"""
    errors: List[str] = []
    strip = lambda fp: {k: v for k, v in fp.items() if k != "path_receipt"}  # noqa: E731
    errors += [f"C5≠C1：{d}" for d in compare_cell(strip(cells["C1"]["fingerprint"]), strip(cells["C5"]["fingerprint"]))]
    for cell in CELLS:
        out = cells[cell]
        status = out["fingerprint"].get("run_status")
        if cell in REFUSED_CELLS:
            dataset = out["receipt"].get("deleted_dataset")
            reasons = out["fingerprint"].get("failure_reasons") or []
            leftovers = (out["fingerprint"].get("completeness") or {}).get("leftover_artifacts")
            if status != "refused" or not dataset or not any(dataset in r for r in reasons) or leftovers != []:
                errors.append(f"{cell}：run_status={status!r}、拒絕原因 {reasons} 未指名缺載 {dataset!r}"
                              f"或留有產物 {leftovers}")
        elif cell in CALIBRATION_PARTIAL_CELLS:
            fp = out["fingerprint"]
            comp = fp.get("completeness") or {}
            reasons = fp.get("failure_reasons") or []
            if status != "partial" or not reasons \
                    or not all(str(r).startswith(CALIBRATION_PARTIAL_REASON) for r in reasons) \
                    or comp.get("failed_timeframes") != [] or comp.get("failed_layers") != [] \
                    or comp.get("present_timeframes") != comp.get("expected_timeframes"):
                errors.append(f"{cell}：run_status={status!r}、原因 {reasons} 非僅校準前史不足或有週期／層失敗")
        elif status != "complete":
            errors.append(f"{cell}：run_status={status!r} 非 complete")
        errors += memory_gate_errors(cell, out["memory"])
        if out["receipt"].get("resume_entered") is not (cell == "C5"):
            errors.append(f"{cell}：resume_entered={out['receipt'].get('resume_entered')!r}")
    return errors


def freeze(out: Path = REPO / BASELINE_REL) -> Dict[str, Any]:
    """先以 `code_state_errors()` 核對碼態（非空 ⇒ `FramepathBaselineError`，不產任何輸出），再跑全部格、驗拒寫條件後
    寫基準：`code_anchor` 與 `head_commit` 取自 `resolve_commits()`、`code_state_errors`（[]）、python、各格
    fingerprint／memory／receipt（各格以模組屬性 `run_cell` 呼叫，拒寫條件以 `_freeze_refusals` 判定；非空 ⇒ 不寫檔）。"""
    mod = sys.modules[__name__]
    state = mod.code_state_errors()
    if state:
        raise FramepathBaselineError(f"碼態不符，拒寫：{state}")
    commits = mod.resolve_commits()
    work_root = Path(tempfile.mkdtemp(prefix="framepath_freeze_"))
    try:
        cells = {cell: mod.run_cell(cell, work_root) for cell in CELLS}
    finally:
        shutil.rmtree(work_root, ignore_errors=True)
    refusals = mod._freeze_refusals(cells)
    if refusals:
        raise FramepathBaselineError(f"凍結拒寫：{refusals}")
    baseline = {"schema": "framepath-cgsa-fingerprint/1", "spec": "docs/FRAMEPATH_SPEC.md §G、Task 1.1",
                **commits, "code_state_errors": [], "python": sys.version.split()[0], "cells": cells}
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(baseline, ensure_ascii=False, indent=1, sort_keys=False) + "\n", encoding="utf-8")
    return baseline


def check(baseline_path: Path = REPO / BASELINE_REL) -> List[str]:
    """改後重跑全部格並與基準逐項比對；回傳「格：差異」列表（空＝全等）。"""
    baseline = json.loads(Path(baseline_path).read_text(encoding="utf-8"))
    work_root = Path(tempfile.mkdtemp(prefix="framepath_check_"))
    diffs: List[str] = []
    try:
        for cell in CELLS:
            fresh = run_cell(cell, work_root)
            diffs += [f"{cell}：{d}" for d in memory_gate_errors(cell, fresh["memory"])]
            diffs += [f"{cell}：{d}" for d in compare_cell(baseline["cells"][cell]["fingerprint"], fresh["fingerprint"])]
    finally:
        shutil.rmtree(work_root, ignore_errors=True)
    return diffs


def main(argv: List[str]) -> int:
    if argv[:1] == ["_child"]:
        return _child_main(*argv[1:4])
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("action", choices=("freeze", "check"))
    args = ap.parse_args(argv)
    if args.action == "freeze":
        freeze()
        return 0
    diffs = check()
    for line in diffs:
        print(line)
    print(f"FRAMEPATH check：差異 {len(diffs)} 項")
    return 1 if diffs else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
