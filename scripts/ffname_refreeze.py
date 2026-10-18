#!/usr/bin/env python3
"""FF-NAME Task 4.3 重凍工具（docs/FFNAME_SPEC.md v21 §G「重凍 golden 之處置與值 oracle」K0–K3）。

子命令：
  record   --recipe R --out JSON [--no-instrument]
           於「當前工作目錄之碼態」跑 golden 自身之設定與窗（cwd＝改前 worktree 或主樹）。掛 Task 0.1 同一組名點紀錄器
           （cwd 之 `scripts/ffname_freeze_baseline.py:_Instrument`），輸出全部組名零件、標記索引（舊標記函式對
           零件×週期之實際輸出）與該 golden 之 sidecar（K2 逐欄值指紋；K1 名雜湊之輸入）。`--no-instrument` 用於現行碼
           之 K2 新跑（只要 sidecar）。本子命令只自 cwd 匯入，不匯入主樹模組。
  mapping  --golden REL --record JSON
           （主樹）由紀錄器零件以現行 formatter 推導 golden 全部舊名之新名；查無 ⇒ 失敗（不猜）。寫
           `handoffs/run_receipts/ffname_refreeze_maps/<golden>.json`。
  rekey    --golden REL [--salt-proof JSON]
           （主樹，K1）依映射只改鍵名／名字串，值位元組不動；名雜湊欄位以該 golden 自身函式對換名後清單重算，
           重算前先以同函式對改前清單驗證等於改前值。換名後殘留任何改前舊名 ⇒ 失敗。
  k2       --golden REL --old JSON --new JSON --map JSON
           （主樹，K2）新舊碼 sidecar 依名逐欄比對（不以值多重集合代替）；§G ⑥ 新增 lag 欄驗位移後列出。
           全等 ⇒ 以新碼 sidecar 所附之 golden 內容重凍。

寫入一律隔離於暫存目錄（各 golden 原產生路徑之隔離）；不寫主樹 data_cache。
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

MAIN_REPO = Path(__file__).resolve().parents[1]
MAPS_DIR = MAIN_REPO / "handoffs" / "run_receipts" / "ffname_refreeze_maps"
# failopen 全窗 sidecar 每份數十 MB（逾 GitHub 50MB 警示線之虞）⇒ 可由 FFNAME_SIDECAR_DIR 導至版控外（收據記絕對路徑）
SIDECAR_DIR = Path(os.environ.get("FFNAME_SIDECAR_DIR") or (MAIN_REPO / "handoffs" / "run_receipts" / "ffname_refreeze_sidecars"))
RECORD_SCHEMA = "ffname-refreeze-record-v1"
MAP_SCHEMA = "ffname-refreeze-map-v1"


def _slug(rel: str) -> str:
    return rel.replace("tests/_golden/", "").replace(".json", "").replace("/", "__")


def _sha_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ================================================================ record（cwd 碼態）


def _tree() -> Path:
    return Path.cwd().resolve()


def _use_cwd_tree() -> None:
    """只自 cwd 匯入（避免主樹 scripts/ 目錄與 momentum 混入改前 worktree 之執行）。"""
    tree = str(_tree())
    script_dir = str(Path(__file__).resolve().parent)
    sys.path[:] = [tree] + [p for p in sys.path if p not in (script_dir, tree, "")]


def _load(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _per_column_fp(values: Any) -> Dict[str, str]:
    """K2 逐欄 sidecar 指紋：dtype、NaN mask sha256、值 sha256（NaN 置 0 之 little-endian 位元組）。"""
    import numpy as np

    arr = np.asarray(values)
    if arr.dtype.kind == "f":
        mask = np.isnan(arr)
        filled = np.where(mask, 0, arr)
    else:
        mask = np.zeros(arr.shape, dtype=bool)
        filled = arr
    native = np.ascontiguousarray(filled).astype(filled.dtype.newbyteorder("<"), copy=False)
    return {"dtype": str(arr.dtype), "rows": int(arr.shape[0]),
            "nan": hashlib.sha256(np.packbits(mask.astype(np.uint8)).tobytes()).hexdigest(),
            "values": hashlib.sha256(native.tobytes()).hexdigest()}


# ---- recipes：每個接收 (mp, work)；回傳 sidecar（JSON 可序列化）


def _recipe_icfa_l3(mp: Any, work: Path) -> Dict[str, Any]:
    frz = _load(_tree() / "scripts" / "freeze_icfirstalign_baseline.py", "ffname_rf_icfa")
    return {"golden_like": frz.stage_l3_default()}


def _recipe_icfa_worker(mp: Any, work: Path) -> Dict[str, Any]:
    """icfirstalign worker_counts：錄 `worker_record` 之輸入群組（層、欄名清單），供以 golden 自身函式換名後重算
    `groups_sha256`。"""
    frz = _load(_tree() / "scripts" / "freeze_icfirstalign_baseline.py", "ffname_rf_icfa_w")
    captured: Dict[str, Any] = {}
    real = frz.worker_record

    def worker_record(result: Dict[str, Any]) -> Dict[str, Any]:
        captured["groups"] = [[str(g["layer"]), [str(c) for c in g["columns"]]] for g in result.get("groups", [])]
        return real(result)

    mp.setattr(frz, "worker_record", worker_record)
    return {"golden_like": frz.stage_worker_counts(), "groups": captured.get("groups")}


def _recipe_icfa_calibration(mp: Any, work: Path) -> Dict[str, Any]:
    tmod = _load(_tree() / "tests" / "feature_engineering" / "test_icfirstalign_calibration_domain.py", "ffname_rf_icfa_cal")
    import pytest

    out: Dict[str, Any] = {}
    for winsor in (True, False):
        with pytest.MonkeyPatch.context() as inner:
            out[f"S3_winsor_{'on' if winsor else 'off'}"] = tmod._packets(work / f"cal_{winsor}", inner, winsor)
    return {"golden_like_jia": out}


def _load_ffstat_freeze() -> Any:
    """ffstat 產生腳本（模組載入時即 isolate()；其 `_isolate` 位於腳本同目錄）。同一程序只載入一次。"""
    if "ffname_rf_ffstat" in sys.modules:
        return sys.modules["ffname_rf_ffstat"]
    probe_dir = _tree() / "handoffs" / "run_receipts" / "ffstat_probes"
    if str(probe_dir) not in sys.path:
        sys.path.insert(1, str(probe_dir))
    return _load(probe_dir / "freeze_baseline.py", "ffname_rf_ffstat")


def _recipe_ffstat_baseline(mp: Any, work: Path) -> Dict[str, Any]:
    out = work / "ffstat_baseline.json"
    mod = _load_ffstat_freeze()
    argv = sys.argv
    sys.argv = ["freeze_baseline.py", "--out", str(out)]
    try:
        rc = mod.main()
    except AttributeError as exc:
        # c9737729 之 ffstat_helpers 已無 `ic_first_supplied_off`（產生腳本第三段過期）；主 run 與 auto_off 已跑完、
        # 組名零件已錄得。該段之欄名（未標記形）由前兩段之未標記零件涵蓋與否，由 mapping 之查無 fail-closed 判定。
        if "ic_first_supplied_off" not in str(exc):
            raise
        return {"partial": f"ic_first_supplied_off 段於此碼態不可執行：{exc}"}
    finally:
        sys.argv = argv
    if rc != 0:
        raise RuntimeError(f"ffstat freeze_baseline rc={rc}")
    return {"golden_like": json.loads(out.read_text(encoding="utf-8"))}


def _recipe_ffstat_nostart(mp: Any, work: Path) -> Dict[str, Any]:
    out = work / "ffstat_nostart.json"
    mod = _load(_tree() / "handoffs" / "run_receipts" / "ffstat_probes" / "freeze_baseline_nostart.py", "ffname_rf_nostart")
    argv = sys.argv
    sys.argv = ["freeze_baseline_nostart.py", "--kline-dir", str(_tree() / "data_cache" / "feature_klines"),
                "--out", str(out)]
    try:
        rc = mod.main()
    finally:
        sys.argv = argv
    if rc != 0:
        raise RuntimeError(f"nostart rc={rc}")
    doc = json.loads(out.read_text(encoding="utf-8"))
    return {"golden_like_columns": sorted(doc["columns"]), "rows": doc["rows"]}


def _g6_shift_checks(frame: Any) -> Dict[str, bool]:
    """§G ⑥ 新增 lag 欄之位移 oracle（SPEC v17：以關閉縮尾之同設定 run 比對）：值＝基底欄位移 k（NaN 對 NaN）。
    只在現行命名世代可 parse 之欄上判定（改前碼態無 ⑥ 新欄，回空）。"""
    import dataclasses
    import fnmatch

    import numpy as np

    import momentum.FeatureEngineering.feature_naming as fn

    globs = json.loads((_tree() / "tests" / "_golden" / "ffname" / "contract.json").read_text(encoding="utf-8")) \
        .get("g6_new_lag_globs", [])
    out: Dict[str, bool] = {}
    for col in map(str, frame.columns):
        try:
            ident = fn.parse_feature_name(col)
        except Exception:  # noqa: BLE001
            continue
        if not ident.ops or not str(ident.ops[-1]).startswith("Lag-"):
            continue
        base = fn.format_feature_name(dataclasses.replace(ident, ops=tuple(ident.ops[:-1])))
        if not any(fnmatch.fnmatchcase(base, g) for g in globs):
            continue
        k = int(str(ident.ops[-1]).split("-", 1)[1])
        if base not in frame.columns:
            out[col] = False
            continue
        a = np.asarray(frame[col], dtype=np.float64)
        b = np.asarray(frame[base].shift(k), dtype=np.float64)
        out[col] = bool(np.array_equal(a, b, equal_nan=True))
    return out


def _recipe_ratiounsafe(stage: str) -> Callable[[Any, Path], Dict[str, Any]]:
    def run(mp: Any, work: Path) -> Dict[str, Any]:
        frz = _load(_tree() / "scripts" / "freeze_ratiounsafe_baseline.py", "ffname_rf_ru")
        out: Dict[str, Any] = {"golden_like": frz.build(stage)}
        if stage == "after":
            # ⑥ 位移 oracle：同 S1 設定、前處理關（無縮尾）之 run
            c = frz.contract()["s1"]
            shift: Dict[str, bool] = {}
            for arm in ("off", "on"):
                frame, _n = frz.generate_raw(frz.s1_payload(arm, False), c["symbol"], c["timeframe"], int(c["days"]))
                shift.update(_g6_shift_checks(frame))
            out["g6_shift"] = shift
        return out

    return run


def _recipe_probewinsor(mp: Any, work: Path) -> Dict[str, Any]:
    """29 格逐格真實生成；錄 record_of 之名雜湊輸入（late 名單、首個有限值、stable_start、warmup_insufficient）。"""
    ph = _load(_tree() / "tests" / "feature_engineering" / "probewinsor_helpers.py", "ffname_rf_ph")
    captured: Dict[str, Any] = {}
    real_record = ph.record_of

    def record_of(factory: Any, result: Any, features_root: Path) -> Dict[str, Any]:
        rec = real_record(factory, result, features_root)
        late_bound = getattr(factory, "_public_warmup_late", None)
        docs = [result.metadata if isinstance(getattr(result, "metadata", None), dict) else {}]
        for path in sorted(Path(features_root).rglob("*.json")):
            try:
                docs.append(json.loads(path.read_text(encoding="utf-8")))
            except (OSError, ValueError):
                continue

        def first(key: str) -> Any:
            for doc in docs:
                value = ph._find_key(doc, key)
                if value is not None:
                    return value
            return None

        captured["inputs"] = {
            "late": None if not late_bound else sorted(late_bound[1]),
            "first_finite": json.loads(ph._canon(getattr(factory, "_public_warmup_first_finite", None) or {})),
            "stable_start": json.loads(ph._canon(first("stable_start"))) if first("stable_start") is not None else None,
        }
        return rec

    mp.setattr(ph, "record_of", record_of)
    cells: Dict[str, Any] = {}
    for cell in ph.contract()["cells"]:
        captured.clear()
        rec = ph.run_cell(cell, work / "probewinsor")
        cells[cell["id"]] = {"record": rec, "inputs": dict(captured.get("inputs") or {})}
    return {"cells": cells}


def _recipe_icfa_probe(mp: Any, work: Path) -> Dict[str, Any]:
    """P1／P2：以消費測試之 run 路徑（`_generate`）產生；錄每次校準域呼叫之週期、列數、欄數與末輪首個有限值、late 名單。"""
    import pytest

    tmod = _load(_tree() / "tests" / "feature_engineering" / "test_icfirstalign_calibration_domain.py", "ffname_rf_icfa_p")
    from momentum.FeatureEngineering.preprocessing import calibration as cal

    out: Dict[str, Any] = {}
    for name, (payload_fn, window) in tmod.SETTINGS.items():
        calls: List[Dict[str, Any]] = []
        real = cal.compute_calibration_domain

        def domain(factory: Any, symbol: str, timeframe: str, config: Any, klines: Any, _real=real, _calls=calls):
            rows, cols = 0, 0
            for item in _real(factory, symbol, timeframe, config, klines):
                _gid, names, _arr, index = item
                rows = max(rows, len(index))
                cols += len(names)
                yield item
            _calls.append({"timeframe": str(timeframe), "rows": rows, "columns": cols})

        with pytest.MonkeyPatch.context() as inner:
            inner.setattr(cal, "compute_calibration_domain", domain)
            factory = tmod._generate(work / f"probe_{name}", inner, payload_fn(), window)
            late = getattr(factory, "_public_warmup_late", None)
            out[name] = {
                "rounds": [dict(r) for r in factory._public_warmup_probe],
                "window": {k: str(getattr(factory._current_output_window, k, None))
                           for k in ("output_start", "output_end", "ingest_start", "max_warmup_bars", "warmup_enabled")},
                "late": sorted(late[1]) if late else None,
                "first_finite": {tf: {str(c): (None if t is None else str(t)) for c, t in m.items()}
                                 for tf, m in factory._public_warmup_first_finite.items()},
                "domain_calls": calls,
            }
    return {"probe": out}


def _recipe_fftfmeta(mp: Any, work: Path) -> Dict[str, Any]:
    import pyarrow.parquet as pq

    g = _load(_tree() / "tests" / "feature_engineering" / "fftfmeta_golden_helpers.py", "ffname_rf_fft")
    base = json.loads((_tree() / "tests" / "_golden" / "fftfmeta" / "baseline.json").read_text(encoding="utf-8"))
    refs: Dict[str, Any] = {}
    for name in ("multi", "degraded"):
        root = work / f"fftfmeta_{name}"
        os.environ["FFACT_CGSA_WORK_DIR"] = str(root / "cgsa_work")
        payload = base["references"][name]["payload"]
        art = g.run(root / "features", payload, *g.WINDOW)
        columns: Dict[str, Any] = {}
        for path in sorted(art.raw_dir.glob("*.parquet")):
            table = pq.read_table(path)
            for col in table.column_names:
                fp = g._column_fingerprint(table.column(col))
                columns[col] = {"group_file": path.name, **fp}
        refs[name] = {"payload": payload, "fingerprint": g.fingerprint(art), "columns": columns}
    return {"references": refs, "symbol": g.SYMBOL, "window": list(g.WINDOW)}


FAILOPEN_UNITS = ("BTCUSDT/12h", "ETHUSDT/12h", "BTCUSDT/1h", "ETHUSDT/1h", "BTCUSDT/multi", "ETHUSDT/multi")


def _recipe_failopen(mp: Any, work: Path) -> Dict[str, Any]:
    """failopen 單一單元（環境變數 `FFNAME_FAILOPEN_UNIT`＝`<SYM>/<TF>` 或 `<SYM>/multi`）：以該 golden 原產生函式
    （`freeze_failopen_baseline._single_tf_record`／`_multi_tf_record`，全窗）跑一次，並包裝其雜湊函式錄逐欄 sidecar
    （registry 全群組表、l1_direct、merged_L7；值指紋與欄名分開，供依名逐欄比對）。回傳該單元之 golden 紀錄。"""
    import numpy as np

    unit = os.environ.get("FFNAME_FAILOPEN_UNIT", "")
    symbol, _, kind = unit.partition("/")
    frz = _load(_tree() / "scripts" / "freeze_failopen_baseline.py", "ffname_rf_failopen")
    for name, value in frz.FIXED_ENV.items():
        os.environ[name] = value
    tables: Dict[str, Dict[str, Any]] = {"registry": {}, "l1_direct": {}, "merged_L7": {}}
    state = {"table": "registry"}
    conflicts: List[str] = []
    real_reg, real_l7, real_l1d = frz._hash_registry_table, frz._hash_l7_parquet_table, frz._l1_direct_record

    g6_arrays: Dict[str, Any] = {}
    globs = json.loads((_tree() / "tests" / "_golden" / "ffname" / "contract.json").read_text(encoding="utf-8")) \
        .get("g6_new_lag_globs", [])

    def keep_for_g6(col: str) -> bool:
        import fnmatch

        base = col.rsplit("_Lag-", 1)[0] if "_Lag-" in col else col
        return any(fnmatch.fnmatchcase(base, g) for g in globs)

    def hash_registry(registry: Any, groups: Any, index: Any, row_slice: Any = None, native_rows: Any = None):
        groups = list(groups)
        out = real_reg(registry, groups, index, row_slice, native_rows)
        dest = tables[state["table"]]
        for group in groups:
            data = np.asarray(registry.load_data_native(group.group_id))
            if row_slice is not None:
                data = data[row_slice]
            for i, col in enumerate(group.columns):
                fp = _per_column_fp(data[:, i])
                if str(col) in dest and dest[str(col)] != fp:
                    conflicts.append(f"{state['table']}:{col}")
                dest[str(col)] = fp
                # ⑥ 位移 oracle：registry 之 L1／L4 為 L6.5（縮尾）前之值 ⇒ 可直接驗 lag＝基底位移
                if state["table"] == "registry" and keep_for_g6(str(col)):
                    g6_arrays[str(col)] = np.array(data[:, i], dtype=np.float64)
        return out

    def hash_l7(feature_base: Path, sym: str, timeframe: str, config_hash: str, index: Any):
        out = real_l7(feature_base, sym, timeframe, config_hash, index)
        from momentum.FeatureEngineering.feature_reader import FeatureReader

        reader = FeatureReader(str(feature_base))
        for _g, frame in reader.stream_groups_v2(sym, timeframe, config_hash, artifact_kind="raw"):
            for col in frame.columns:
                tables["merged_L7"][str(col)] = _per_column_fp(frame[col].to_numpy(copy=False))
        return out

    def l1_direct(sym: str, timeframe: str, temp_root: Path):
        state["table"] = "l1_direct"
        try:
            return real_l1d(sym, timeframe, temp_root)
        finally:
            state["table"] = "registry"

    mp.setattr(frz, "_hash_registry_table", hash_registry)
    mp.setattr(frz, "_hash_l7_parquet_table", hash_l7)
    mp.setattr(frz, "_l1_direct_record", l1_direct)
    temp_root = work / "failopen"
    temp_root.mkdir(parents=True, exist_ok=True)
    if kind == "multi":
        record = frz._multi_tf_record(symbol, temp_root)
    elif kind:
        record = frz._single_tf_record(symbol, kind, temp_root)
    else:
        raise SystemExit("FFNAME_FAILOPEN_UNIT 未設定")
    import pandas as pd

    shift: Dict[str, bool] = {}
    by_len: Dict[Tuple[str, int], Dict[str, Any]] = {}
    for col, arr in g6_arrays.items():  # 同週期（第 2 段）且同列數者同表（多週期 registry 為各自原生時間軸）
        by_len.setdefault((col.split("_")[1] if "_" in col else "", len(arr)), {})[col] = arr
    for frame_cols in by_len.values():
        shift.update(_g6_shift_checks(pd.DataFrame(frame_cols)))
    return {"unit": unit, "unit_record": record, "tables": tables, "conflicts": conflicts, "g6_shift": shift}


RECIPES: Dict[str, Callable[[Any, Path], Dict[str, Any]]] = {
    "failopen": _recipe_failopen,
    "icfa_l3": _recipe_icfa_l3,
    "icfa_calibration": _recipe_icfa_calibration,
    "icfa_worker": _recipe_icfa_worker,
    "icfa_probe": _recipe_icfa_probe,
    "ffstat_baseline": _recipe_ffstat_baseline,
    "ffstat_nostart": _recipe_ffstat_nostart,
    "ratiounsafe_before": _recipe_ratiounsafe("before"),
    "ratiounsafe_after": _recipe_ratiounsafe("after"),
    "probewinsor": _recipe_probewinsor,
    "fftfmeta": _recipe_fftfmeta,
}

# 會先於 momentum 匯入呼叫 isolate() 之產生腳本：須先載入（由 recipe 內載入即可，紀錄器之 install 延後至 recipe 起跑後）
_LATE_INSTALL = {"ffstat_baseline"}


def record(recipe: str, out: Path, instrument: bool) -> int:
    _use_cwd_tree()
    os.environ.setdefault("PYTHONHASHSEED", "0")
    import pytest

    if recipe not in RECIPES:
        raise SystemExit(f"未知 recipe {recipe!r}；可選 {sorted(RECIPES)}")
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(_tree()), capture_output=True, text=True).stdout.strip()
    frz = _load(_tree() / "scripts" / "ffname_freeze_baseline.py", "ffname_rf_freeze") if instrument else None
    inst = frz._Instrument() if instrument else None
    started = time.time()
    work = Path(tempfile.mkdtemp(prefix=f"ffname_rf_{recipe}_"))
    with pytest.MonkeyPatch.context() as mp:
        if recipe in _LATE_INSTALL and inst is not None:
            # ffstat 產生腳本於模組載入時 isolate()：先載入，再掛紀錄器，再呼叫 main
            _load_ffstat_freeze()
        if inst is not None:
            inst.install(mp)
        sidecar = RECIPES[recipe](mp, work)
    payload: Dict[str, Any] = {"schema_version": RECORD_SCHEMA, "recipe": recipe, "tree": str(_tree()), "head": head,
                               "instrumented": bool(instrument), "elapsed_seconds": round(time.time() - started, 1),
                               "sidecar": sidecar, "work_dir": str(work)}
    if inst is not None:
        payload["parts"] = inst.rec.to_json()
        payload["tagged_index"] = _tagged_index(frz, inst)
        payload["post_ic"] = [[col, base, list(ops)] for col, (base, ops) in sorted(inst.post_ic.items())]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    print(f"[ffname-refreeze record] {recipe} head={head[:12]} instrumented={instrument} "
          f"parts={len(payload.get('parts', []))} elapsed={payload['elapsed_seconds']}s → {out}")
    return 0


def _tagged_index(frz: Any, inst: Any) -> List[List[str]]:
    """標記名 → (tf, 未標記名)：實際標記呼叫，加上以 cwd 碼態之標記函式對全部零件×本次週期集合之輸出。"""
    from momentum.FeatureEngineering import feature_naming

    rows: Set[Tuple[str, str, str]] = set()
    tfs: Set[str] = set()
    for (tf, untagged), tagged in list(inst.tag_calls.items()) + list(getattr(inst, "tag2_calls", {}).items()):
        rows.add((tagged, tf, untagged))
        tfs.add(tf)
    tag2 = None
    try:
        from momentum.FeatureEngineering.feature_factory import FeatureFactory

        tag2 = getattr(FeatureFactory, "_timeframe_tagged_name", None)
    except Exception:  # noqa: BLE001
        tag2 = None
    for row in inst.rec.to_json():
        name = row["old_name"]
        for tf in tfs:
            rows.add((feature_naming.tag_timeframe(name, tf), tf, name))
            if tag2 is not None:
                try:
                    rows.add((tag2(name, tf, set(tfs)), tf, name))
                except Exception:  # noqa: BLE001
                    pass
    return [list(r) for r in sorted(rows)]


# ================================================================ mapping（主樹）


def _freeze_mod() -> Any:
    sys.path.insert(0, str(MAIN_REPO))
    return _load(MAIN_REPO / "scripts" / "ffname_freeze_baseline.py", "ffname_freeze_baseline")


def build_mapping(record_doc: Mapping[str, Any], old_names: Iterable[str]) -> Tuple[Dict[str, str], List[str], List[str]]:
    """舊名 → 新名（現行 formatter）；回傳（映射, 查無, 歧義）。標記名經紀錄器之標記索引反查 (tf, 未標記零件)。"""
    frz = _freeze_mod()
    parts = {row["old_name"]: frz._part_from_row(row) for row in record_doc["parts"]}
    tagged: Dict[str, Set[Tuple[str, str]]] = {}
    for tagged_name, tf, untagged in record_doc.get("tagged_index", []):
        if tagged_name != untagged:
            tagged.setdefault(tagged_name, set()).add((tf, untagged))
    post_ic = {col: (base, tuple(ops)) for col, base, ops in record_doc.get("post_ic", [])}
    mapping: Dict[str, str] = {}
    missing: List[str] = []
    ambiguous: List[str] = []
    l65_derived: List[str] = []

    def resolve_part(old: str) -> Optional[Tuple[Any, Optional[str]]]:
        """(零件, tf)：標記名經標記索引、未標記名直查。"""
        cands = {c for c in tagged.get(old, set()) if c[1] in parts}
        if len(cands) == 1:
            tf, untagged = next(iter(cands))
            return parts[untagged], tf
        if not cands and old in parts:
            return parts[old], parts[old].tf
        return None

    def l65_fallback(old: str) -> Optional[str]:
        """L6.5 append 後綴欄（`_fracdiff`、`_diff<k>`、`_zscore_<w>`、`_rank`、`_gaussian`）：以 Task 0.1 紀錄器同一
        A10 剝除規則（`_L65_RES`）剝至可解析之基底零件，op 段依序追加後以現行 formatter 推導。"""
        import dataclasses

        current, ops = old, []
        while True:
            for regex, to_op in frz._L65_RES:
                match = regex.fullmatch(current)
                if match is not None:
                    ops.insert(0, to_op(match))
                    current = match["base"]
                    break
            else:
                return None
            hit = resolve_part(current)
            if hit is not None:
                part, tf = hit
                return frz.derive_new_name(dataclasses.replace(part, ops=tuple(part.ops) + tuple(ops)), tf)

    for old in sorted(set(old_names)):
        cands = {c for c in tagged.get(old, set()) if c[1] in parts}
        if len(cands) > 1:
            news = {frz.derive_new_name(parts[u], tf) for tf, u in cands}
            if len(news) > 1:
                ambiguous.append(old)
                continue
            mapping[old] = news.pop()
        elif len(cands) == 1:
            tf, untagged = next(iter(cands))
            mapping[old] = frz.derive_new_name(parts[untagged], tf)
        elif old in parts:
            mapping[old] = frz.derive_new_name(parts[old], parts[old].tf)
        elif old in post_ic and post_ic[old][0] in tagged:
            base_old, ops = post_ic[old]
            (tf, untagged), = tagged[base_old]
            import dataclasses

            part = dataclasses.replace(parts[untagged], ops=tuple(parts[untagged].ops) + ops)
            mapping[old] = frz.derive_new_name(part, tf)
        elif (derived := l65_fallback(old)) is not None:
            mapping[old] = derived
            l65_derived.append(old)
        else:
            missing.append(old)
    news = list(mapping.values())
    if len(set(news)) != len(news):
        dup = sorted({n for n in news if news.count(n) > 1})
        raise SystemExit(f"映射非單射：{dup[:10]}")
    build_mapping.l65_derived = l65_derived  # type: ignore[attr-defined]
    return mapping, missing, ambiguous


# ---- 各 golden 之舊名全集與換鍵規格


def _walk_names(node: Any, path: Tuple[str, ...], out: List[Tuple[Tuple[str, ...], str]]) -> None:
    """golden 內全部字串葉與 dict 鍵（供殘留舊名掃描）。"""
    if isinstance(node, dict):
        for k, v in node.items():
            out.append((path + ("{key}",), str(k)))
            _walk_names(v, path + (str(k),), out)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            _walk_names(v, path + (str(i),), out)
    elif isinstance(node, str):
        out.append((path, node))


def golden_old_names(rel: str, doc: Mapping[str, Any]) -> Set[str]:
    """K1 golden 之舊欄名全集（`GOLDEN_LAYOUTS` 之結構位置＋各 golden 之附加名欄位）。"""
    frz = _freeze_mod()
    names = set(frz.golden_columns(MAIN_REPO / rel))
    for spec in K1_SPECS.get(rel, {}).get("extra_name_paths", ()):
        for value in _collect_path(doc, spec):
            names.add(value)
    return names


def _collect_path(node: Any, pattern: Sequence[str]) -> List[str]:
    """pattern：`*` 任一鍵、`{K}` 鍵為名、`[]` 清單成員為名。"""
    if not pattern:
        return []
    seg, rest = pattern[0], pattern[1:]
    if seg == "{K}":
        return [str(k) for k in node] if isinstance(node, dict) and not rest else []
    if seg == "[]":
        return [v for v in node if isinstance(v, str)] if isinstance(node, list) and not rest else []
    if seg == "*":
        items = node.values() if isinstance(node, dict) else (node if isinstance(node, list) else [])
        return [v for child in items for v in _collect_path(child, rest)]
    return _collect_path(node[seg], rest) if isinstance(node, dict) and seg in node else []


def write_mapping(rel: str, record_path: Path) -> int:
    record_doc = json.loads(record_path.read_text(encoding="utf-8"))
    doc = json.loads((MAIN_REPO / rel).read_text(encoding="utf-8"))
    old = golden_old_names(rel, doc)
    mapping, missing, ambiguous = build_mapping(record_doc, old)
    out = {"schema_version": MAP_SCHEMA, "golden": rel, "recipe": record_doc["recipe"], "source_head": record_doc["head"],
           "source_tree": record_doc["tree"], "record_elapsed_seconds": record_doc.get("elapsed_seconds"),
           "golden_sha256": hashlib.sha256((MAIN_REPO / rel).read_bytes()).hexdigest(),
           "old_name_count": len(old), "mapped": len(mapping), "renamed": sum(1 for k, v in mapping.items() if k != v),
           "l65_suffix_derived": len(getattr(build_mapping, "l65_derived", [])),
           "missing": missing, "ambiguous": ambiguous, "mapping": mapping}
    MAPS_DIR.mkdir(parents=True, exist_ok=True)
    path = MAPS_DIR / f"{_slug(rel)}.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"[ffname-refreeze mapping] {rel}: 舊名 {len(old)}、映射 {len(mapping)}、改名 {out['renamed']}、"
          f"查無 {len(missing)}、歧義 {len(ambiguous)} → {path}")
    if missing[:5]:
        print(f"  查無例：{missing[:8]}")
    return 0 if not missing and not ambiguous else 1


def write_mapping_list(label: str, record_path: Path, source: Path, pattern: Sequence[str]) -> int:
    """非 golden 之舊名來源（如 FF-STAT 欄集合差異收據、死欄 golden）之映射：來源檔不改（使用者核可紀錄之 sha 不動），
    由讀取端依本映射換名。查無 ⇒ 失敗。"""
    record_doc = json.loads(record_path.read_text(encoding="utf-8"))
    doc = json.loads(source.read_text(encoding="utf-8"))
    old = set(_collect_path(doc, pattern))
    mapping, missing, ambiguous = build_mapping(record_doc, old)
    out = {"schema_version": MAP_SCHEMA, "label": label, "source": str(source.relative_to(MAIN_REPO)),
           "source_pattern": list(pattern), "recipe": record_doc["recipe"], "source_head": record_doc["head"],
           "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(), "old_name_count": len(old),
           "mapped": len(mapping), "renamed": sum(1 for k, v in mapping.items() if k != v),
           "missing": missing, "ambiguous": ambiguous, "mapping": mapping}
    MAPS_DIR.mkdir(parents=True, exist_ok=True)
    path = MAPS_DIR / f"{label}.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"[ffname-refreeze mapping-list] {label}: 舊名 {len(old)}、映射 {len(mapping)}、查無 {len(missing)} → {path}")
    return 0 if not missing and not ambiguous else 1


# ================================================================ rekey（主樹，K1）


def _detect_format(raw: bytes, doc: Any) -> Dict[str, Any]:
    """以「原樣重寫＝原位元組」確定 json.dumps 參數（換鍵後同參數寫出，避免夾帶格式差異）。"""
    for indent in (1, 2, None):
        for sort_keys in (True, False):
            for ensure_ascii in (False, True):
                text = json.dumps(doc, ensure_ascii=ensure_ascii, indent=indent, sort_keys=sort_keys)
                for tail in ("\n", ""):
                    if (text + tail).encode("utf-8") == raw:
                        return {"indent": indent, "sort_keys": sort_keys, "ensure_ascii": ensure_ascii, "tail": tail}
    raise SystemExit("無法以 json.dumps 參數重現原檔位元組（拒絕重寫，避免夾帶格式差異）")


def _rename_node(node: Any, pattern: Sequence[str], mapping: Mapping[str, str], resort: bool = True) -> Any:
    if not pattern:
        return node
    seg, rest = pattern[0], pattern[1:]
    if seg == "{K}" and isinstance(node, dict) and not rest:
        return {mapping.get(str(k), k): v for k, v in node.items()}
    if seg == "[]" and isinstance(node, list) and not rest:
        was_sorted = node == sorted(node)
        out = [mapping.get(v, v) if isinstance(v, str) else v for v in node]
        return sorted(out) if (resort and was_sorted) else out
    if seg.startswith("@") and isinstance(node, dict) and not rest:
        field = seg[1:]
        return {**node, field: mapping.get(node.get(field), node.get(field))} if isinstance(node.get(field), str) else node
    if seg == "*":
        if isinstance(node, dict):
            return {k: _rename_node(v, rest, mapping, resort) for k, v in node.items()}
        if isinstance(node, list):
            return [_rename_node(v, rest, mapping, resort) for v in node]
        return node
    if isinstance(node, dict) and seg in node:
        return {**node, seg: _rename_node(node[seg], rest, mapping, resort)}
    return node


def _values_untouched(old: Any, new: Any, mapping: Mapping[str, str], path: str = "") -> List[str]:
    """K1 值位元組不變：除名鍵／名字串／名雜湊欄位外，每個葉之值相等（鍵依映射對應）。回傳不等之路徑。"""
    bad: List[str] = []
    if isinstance(old, dict) and isinstance(new, dict):
        inv = {mapping.get(str(k), k): k for k in old}
        if set(inv) != set(new):
            return [f"{path}:keyset"]
        for nk, ok in inv.items():
            bad += _values_untouched(old[ok], new[nk], mapping, f"{path}/{nk}")
        return bad
    if isinstance(old, list) and isinstance(new, list):
        if all(isinstance(v, str) for v in old) and all(isinstance(v, str) for v in new):
            return [] if sorted(mapping.get(v, v) for v in old) == sorted(new) else [f"{path}:names"]
        if len(old) != len(new):
            return [f"{path}:len"]
        for i, (a, b) in enumerate(zip(old, new)):
            bad += _values_untouched(a, b, mapping, f"{path}/{i}")
        return bad
    if isinstance(old, str) and old in mapping:
        return [] if new == mapping[old] else [path]
    return [] if old == new else [path]


def _names_sha(names: Sequence[str]) -> str:
    return _sha_text("\n".join(names))


def _hash_fix_ratiounsafe(doc: Dict[str, Any], old_doc: Mapping[str, Any]) -> List[str]:
    """ratiounsafe：`names_sha256`＝sha256('\\n'.join(sorted names))（`scripts/freeze_ratiounsafe_baseline.py:record`）。"""
    fixed = []
    for key, rec in doc.items():
        if isinstance(rec, dict) and "names" in rec and "names_sha256" in rec:
            if _names_sha(sorted(old_doc[key]["names"])) != old_doc[key]["names_sha256"]:
                raise SystemExit(f"ratiounsafe {key}: 自身函式對改前名單重算 != 改前 names_sha256（函式不符）")
            rec["names_sha256"] = _names_sha(sorted(rec["names"]))
            fixed.append(f"{key}/names_sha256")
    return fixed


def _hash_fix_calibration(doc: Dict[str, Any], old_doc: Mapping[str, Any]) -> List[str]:
    """icfirstalign 校準封包：`column_set_digest`＝calibration.column_set_digest(欄集合)。改前先驗。"""
    sys.path.insert(0, str(MAIN_REPO))
    from momentum.FeatureEngineering.preprocessing.calibration import column_set_digest

    fixed = []
    for mode in ("jia", "yi"):
        for setting, packets in doc.get(mode, {}).items():
            for tf, packet in packets.items():
                old = old_doc[mode][setting][tf]
                cands = {"values": sorted(old["values"]), "values+empty": sorted(set(old["values"]) | set(old["empty_columns"]))}
                hit = [k for k, cols in cands.items() if column_set_digest(cols) == old["column_set_digest"]]
                if not hit:
                    raise SystemExit(f"calibration {mode}/{setting}/{tf}: 無法以自身函式重現改前 column_set_digest")
                cols = sorted(packet["values"]) if hit[0] == "values" else sorted(set(packet["values"]) | set(packet["empty_columns"]))
                packet["column_set_digest"] = column_set_digest(cols)
                fixed.append(f"{mode}/{setting}/{tf}/column_set_digest({hit[0]})")
    return fixed


def _hash_fix_probewinsor(doc: Dict[str, Any], old_doc: Mapping[str, Any], sidecar: Optional[Mapping[str, Any]],
                          mapping: Mapping[str, str], salt: Optional[Mapping[str, Any]]) -> List[str]:
    """probewinsor 每格：名雜湊欄位（probe_late_sha256、first_finite_sha256、stable_start_sha256）以
    `probewinsor_helpers.record_of` 同式對改前 worktree 錄得之輸入重算——先驗輸入之改前雜湊＝golden 值，再換名重算；
    輸入之改前雜湊與 golden 不符之格（錨點碼態與 c9737729 行為不同之格）不換、列為未重算。config_hash 依去鹽證明更新。"""
    canon = lambda obj: json.dumps(obj, sort_keys=True, ensure_ascii=False, default=str)  # noqa: E731
    out = []
    for cid, cell in doc["cells"].items():
        inputs = ((sidecar or {}).get("cells", {}).get(cid) or {}).get("inputs") or {}
        old = old_doc["cells"][cid]
        late = inputs.get("late")
        if late is not None and _names_sha(sorted(late)) == old.get("probe_late_sha256"):
            cell["probe_late_sha256"] = _names_sha(sorted(mapping.get(n, n) for n in late))
            out.append(f"{cid}/probe_late_sha256")
        elif old.get("probe_late_sha256") is not None:
            out.append(f"{cid}/probe_late_sha256:NOT_RECOMPUTED")
        ff = inputs.get("first_finite")
        if ff is not None and _sha_text(canon(ff)) == old.get("first_finite_sha256"):
            renamed = {tf: {mapping.get(c, c): t for c, t in m.items()} for tf, m in ff.items()} if ff and all(
                isinstance(v, dict) for v in ff.values()) else {mapping.get(c, c): t for c, t in ff.items()}
            cell["first_finite_sha256"] = _sha_text(canon(renamed))
            out.append(f"{cid}/first_finite_sha256")
        else:
            out.append(f"{cid}/first_finite_sha256:NOT_RECOMPUTED")
        ss = inputs.get("stable_start")
        if ss is not None and _sha_text(canon(ss)) == old.get("stable_start_sha256"):
            cell["stable_start_sha256"] = _sha_text(canon(_rename_deep_keys(ss, mapping)))
            out.append(f"{cid}/stable_start_sha256")
        elif old.get("stable_start_sha256") is not None:
            out.append(f"{cid}/stable_start_sha256:NOT_RECOMPUTED")
        if salt is not None:
            proof = salt.get(f"cells/{cid}/config_hash")
            if proof and proof["proof"] and proof["frozen"] == old["config_hash"]:
                cell["config_hash"] = proof["new_anchor"]
                out.append(f"{cid}/config_hash(salt)")
    return out


def _rename_deep_keys(node: Any, mapping: Mapping[str, str]) -> Any:
    if isinstance(node, dict):
        return {mapping.get(k, k): _rename_deep_keys(v, mapping) for k, v in node.items()}
    if isinstance(node, list):
        return [_rename_deep_keys(v, mapping) for v in node]
    return mapping.get(node, node) if isinstance(node, str) else node


K1_SPECS: Dict[str, Dict[str, Any]] = {
    "tests/_golden/icfirstalign/l3_default_arm.json": {"recipe": "icfa_l3"},
    "tests/_golden/icfirstalign/calibration_baseline.json": {
        "recipe": "icfa_calibration", "extra_name_paths": (("*", "*", "*", "shortfall", "{K}"),),
        "extra_rename": (("*", "*", "*", "shortfall", "{K}"),), "hash_fix": "calibration"},
    "tests/_golden/ffstat/baseline.json": {"recipe": "ffstat_baseline"},
    "tests/_golden/ffstat/baseline_nostart.json": {"recipe": "ffstat_nostart"},
    "tests/_golden/ratiounsafe/baseline.json": {
        "recipe": "ratiounsafe_before", "extra_name_paths": (("multi_tf_names", "names", "[]"),),
        "extra_rename": (("multi_tf_names", "names", "[]"),), "hash_fix": "ratiounsafe"},
    "tests/_golden/probewinsor/baseline.json": {
        "recipe": "probewinsor", "extra_name_paths": (("cells", "*", "warmup_insufficient_columns", "[]"),),
        "extra_rename": (("cells", "*", "warmup_insufficient_columns", "[]"),), "hash_fix": "probewinsor"},
}


def rekey(rel: str, salt_path: Optional[Path], record_path: Optional[Path], map_label: Optional[str] = None,
          patterns: Optional[Sequence[Sequence[str]]] = None) -> int:
    """K1 換鍵；`map_label`＋`patterns` 用於非 golden 之連動檔（如 FF-STAT golden 收據），映射取自 `mapping-list`。"""
    frz = _freeze_mod()
    path = MAIN_REPO / rel
    raw = path.read_bytes()
    old_doc = json.loads(raw.decode("utf-8"))
    fmt = _detect_format(raw, old_doc)
    map_doc = json.loads((MAPS_DIR / f"{map_label or _slug(rel)}.json").read_text(encoding="utf-8"))
    if map_doc.get("golden_sha256", map_doc.get("source_sha256")) != hashlib.sha256(raw).hexdigest():
        raise SystemExit(f"{rel}: 映射檔所對位元組與現檔不符（已改過？）")
    if map_doc["missing"] or map_doc["ambiguous"]:
        raise SystemExit(f"{rel}: 映射有查無／歧義，拒絕換鍵（fail-closed）")
    mapping = map_doc["mapping"]
    spec = K1_SPECS.get(rel, {})
    doc: Any = json.loads(raw.decode("utf-8"))
    layout = list(patterns) if patterns is not None else list(frz.GOLDEN_LAYOUTS[rel]) + list(spec.get("extra_rename", ()))
    for pattern in layout:
        doc = _rename_node(doc, pattern, mapping)
    fixed: List[str] = []
    kind = spec.get("hash_fix")
    if kind == "ratiounsafe":
        fixed = _hash_fix_ratiounsafe(doc, old_doc)
    elif kind == "calibration":
        fixed = _hash_fix_calibration(doc, old_doc)
    elif kind == "probewinsor":
        sidecar = json.loads(record_path.read_text(encoding="utf-8"))["sidecar"] if record_path else None
        salt = json.loads(salt_path.read_text(encoding="utf-8"))["probewinsor"] if salt_path else None
        fixed = _hash_fix_probewinsor(doc, old_doc, sidecar, mapping, salt)
    # 殘留：換名後任何字串葉／鍵仍為「會改名之舊名」⇒ 失敗
    leftovers = sorted({v for _p, v in _iter_strings(doc) if v in mapping and mapping[v] != v})
    if leftovers:
        raise SystemExit(f"{rel}: 換名後殘留舊名 {len(leftovers)}：{leftovers[:10]}")
    import fnmatch

    contract = json.loads((MAIN_REPO / "tests/_golden/ffname/contract.json").read_text(encoding="utf-8"))
    allowed = list((contract["refreeze"]["dispositions"].get(rel) or {}).get("name_hash_fields") or [])
    diffs = [p for p in _values_untouched(old_doc, doc, mapping)
             if not any(fnmatch.fnmatchcase(p.lstrip("/"), a) for a in allowed)]
    if diffs:
        raise SystemExit(f"{rel}: 值位元組有非換名之變動 {len(diffs)}：{diffs[:10]}")
    text = json.dumps(doc, ensure_ascii=fmt["ensure_ascii"], indent=fmt["indent"], sort_keys=fmt["sort_keys"]) + fmt["tail"]
    path.write_text(text, encoding="utf-8")
    report = {"golden": rel, "renamed_keys": map_doc["renamed"], "hash_fields_recomputed": fixed,
              "layout": [list(p) for p in layout],
              "old_sha256": hashlib.sha256(raw).hexdigest(), "new_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()}
    rp = MAPS_DIR / f"{map_label or _slug(rel)}.rekey.json"
    rp.write_text(json.dumps(report, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    not_recomputed = [f for f in fixed if f.endswith("NOT_RECOMPUTED")]
    print(f"[ffname-refreeze rekey] {rel}: 換名 {map_doc['renamed']}、名雜湊重算 {len(fixed) - len(not_recomputed)}、"
          f"未重算 {len(not_recomputed)} → {rp}")
    return 0


def _iter_strings(node: Any) -> Iterable[Tuple[str, str]]:
    out: List[Tuple[Tuple[str, ...], str]] = []
    _walk_names(node, (), out)
    return [("/".join(p), v) for p, v in out]


# ================================================================ k2（主樹）


def _lag_shift_ok(new_cols: Mapping[str, Any], name: str) -> Optional[str]:
    """⑥ 新增 lag 欄之形狀檢查：須 parse 為 `<基底>` 加 `Lag-k`，基底屬契約 `g6_new_lag_globs`。值位移另由
    `k2_shift_verify` 以實際 run 讀值驗（sidecar 只有雜湊）。"""
    sys.path.insert(0, str(MAIN_REPO))
    import fnmatch

    import momentum.FeatureEngineering.feature_naming as fn

    contract = json.loads((MAIN_REPO / "tests/_golden/ffname/contract.json").read_text(encoding="utf-8"))
    ident = fn.parse_feature_name(name)
    if not ident.ops or not str(ident.ops[-1]).startswith("Lag-"):
        return "not_lag"
    base = fn.format_feature_name(type(ident)(**{**ident.__dict__, "ops": tuple(ident.ops[:-1])}))
    if not any(fnmatch.fnmatchcase(base, g) for g in contract.get("g6_new_lag_globs", [])):
        return f"base_not_g6:{base}"
    return None


def k2_compare(old_cols: Mapping[str, Any], new_cols: Mapping[str, Any], mapping: Mapping[str, str],
               fields: Sequence[str]) -> Dict[str, Any]:
    """依名逐欄：舊名經映射對新名，指定欄位全等；多出之新欄須為 ⑥ 新增 lag；缺漏即不符。"""
    mismatches: List[str] = []
    missing_map = sorted(n for n in old_cols if n not in mapping)
    mapped_new = {}
    for old, rec in old_cols.items():
        new = mapping.get(old)
        if new is None:
            continue
        mapped_new[new] = old
        got = new_cols.get(new)
        if got is None:
            mismatches.append(f"missing_new:{old}->{new}")
            continue
        for f in fields:
            if rec.get(f) != got.get(f):
                mismatches.append(f"{f}:{old}->{new}")
    extra = sorted(set(new_cols) - set(mapped_new))
    g6, bad_extra = [], []
    for name in extra:
        problem = _lag_shift_ok(new_cols, name)
        (bad_extra if problem else g6).append(name if not problem else f"{name}:{problem}")
    return {"compared": len(mapped_new), "mismatches": mismatches + [f"unmapped_old:{n}" for n in missing_map]
            + [f"extra_new:{n}" for n in bad_extra], "g6_new_lag": g6}


K2_DIR = MAIN_REPO / "handoffs" / "run_receipts" / "ffname_refreeze_k2"


def _rel_or_abs(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(MAIN_REPO))
    except ValueError:
        return str(path.resolve())


def _normalize_sidecar(recipe: str, sidecar: Mapping[str, Any]) -> Dict[str, Any]:
    """K2 sidecar 正規化：{columns: 名 → 逐欄紀錄（值指紋，名無關）, scalars: 名無關之計數／窗}。"""
    if recipe == "ratiounsafe_after":
        g = sidecar["golden_like"]
        cols: Dict[str, Any] = {}
        scalars: Dict[str, Any] = {}
        for arm in ("s1_off", "s1_on"):
            rec = g[arm]
            scalars[arm] = {"n_rows": rec["n_rows"]}
            for name, dig in rec["columns"].items():
                cols.setdefault(name, {})[arm] = dig
        return {"columns": cols, "scalars": scalars}
    if recipe == "fftfmeta":
        cols, scalars = {}, {}
        for ref, body in sidecar["references"].items():
            scalars[ref] = {"allowed": body["fingerprint"]["allowed"], "n_columns": len(body["columns"])}
            for name, fp in body["columns"].items():
                cols.setdefault(name, {})[ref] = {k: v for k, v in fp.items() if k != "group_file"}
        return {"columns": cols, "scalars": scalars}
    if recipe == "failopen":
        cols = {}
        for table, entries in sidecar["tables"].items():
            for name, fp in entries.items():
                cols.setdefault(name, {})[table] = fp
        return {"columns": cols, "scalars": {"unit": sidecar["unit"], "conflicts": sidecar["conflicts"]}}
    if recipe == "icfa_probe":
        cols, scalars = {}, {}
        for p, body in sidecar["probe"].items():
            late = set(body["late"] or [])
            scalars[p] = {"rounds": body["rounds"], "window": body["window"], "late_present": body["late"] is not None,
                          "late_count": len(late),
                          "domain_calls": [[c["timeframe"], c["rows"], c["columns"]] for c in body["domain_calls"]]}
            for tf, m in body["first_finite"].items():
                for name, ts in m.items():
                    cols.setdefault(name, {})[p] = {"tf": tf, "first_finite": ts, "late": name in late}
            for name in late - {n for m in body["first_finite"].values() for n in m}:
                cols.setdefault(name, {})[p] = {"tf": None, "first_finite": None, "late": True}
        return {"columns": cols, "scalars": scalars}
    raise SystemExit(f"K2 正規化未支援 recipe {recipe!r}")


def _golden_from_new(rel: str, recipe: str, new_record: Mapping[str, Any]) -> str:
    """以現行碼新跑之結果組出 golden 文本（格式同各原產生腳本）。"""
    sc = new_record["sidecar"]
    if recipe == "failopen":
        # 單元合併入現行 golden（同 freeze_failopen_baseline.freeze_units：其餘單元原樣保留、記單元凍結 commit）
        doc = json.loads((MAIN_REPO / rel).read_text(encoding="utf-8"))
        symbol, _, kind = sc["unit"].partition("/")
        if kind == "multi":
            doc["multi_tf"][symbol] = sc["unit_record"]
        else:
            doc["single_tf"].setdefault(symbol, {})[kind] = sc["unit_record"]
        doc["environment"].setdefault("unit_commits", {})[sc["unit"]] = new_record["head"]
        return json.dumps(doc, indent=2, sort_keys=True) + "\n"
    if recipe == "ratiounsafe_after":
        return json.dumps(sc["golden_like"], ensure_ascii=False, indent=1) + "\n"
    if recipe == "fftfmeta":
        head = subprocess.run(["git", "rev-parse", "--short=12", "HEAD"], cwd=str(MAIN_REPO), capture_output=True,
                              text=True).stdout.strip()
        out = {"frozen_at_head": head, "symbol": sc["symbol"], "window": sc["window"],
               "references": {name: {"payload": body["payload"], **body["fingerprint"]}
                              for name, body in sc["references"].items()}}
        return json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True) + "\n"
    if recipe == "icfa_probe":
        sys.path.insert(0, str(MAIN_REPO))
        from scripts import freeze_icfirstalign_baseline as frz

        old = json.loads((MAIN_REPO / rel).read_text(encoding="utf-8"))
        per: Dict[str, Any] = {}
        for p, body in sc["probe"].items():
            final = body["first_finite"]
            calls = [{"timeframe": c["timeframe"], "rows": c["rows"], "columns": c["columns"],
                      "first_finite_sha256": frz._sha(sorted(final[c["timeframe"]].items()))}
                     for c in body["domain_calls"]]
            per[p] = {"domain_calls": calls, "late_names_sha256": frz._sha(sorted(body["late"])) if body["late"] else None,
                      "rounds": body["rounds"], "window": body["window"]}
        # 甲／乙於現行碼為同一路徑（消費測試以同一 run 分別對 jia、yi 比對）
        out = {"schema_version": old["schema_version"], "settings": old["settings"], "jia": per,
               "yi": copy.deepcopy(per)}
        return json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True) + "\n"
    raise SystemExit(f"K2 golden 組裝未支援 recipe {recipe!r}")


def _g6_shift_verify(recipe: str, new_record: Mapping[str, Any], g6: Sequence[str]) -> Optional[bool]:
    """⑥ 新增 lag 欄之位移：新跑於關閉縮尾（前處理關）之同設定 run 上驗 值＝基底位移 k（recipe 錄於 sidecar）。"""
    if not g6:
        return None
    checks = new_record["sidecar"].get("g6_shift") or {}
    return bool(checks) and all(checks.get(c) is True for c in g6)


def k2(rel: str, old_path: Path, new_path: Path, dry: bool = False) -> int:
    import copy as _copy  # noqa: F401

    old_record = json.loads(old_path.read_text(encoding="utf-8"))
    new_record = json.loads(new_path.read_text(encoding="utf-8"))
    recipe = old_record["recipe"]
    if new_record["recipe"] != recipe or not old_record.get("instrumented"):
        raise SystemExit("K2：新舊紀錄 recipe 不同或改前紀錄未掛紀錄器")
    old_sc, new_sc = _normalize_sidecar(recipe, old_record["sidecar"]), _normalize_sidecar(recipe, new_record["sidecar"])
    tag = _slug(rel)
    if recipe == "failopen":
        if old_record["sidecar"]["unit"] != new_record["sidecar"]["unit"]:
            raise SystemExit("failopen K2：新舊紀錄單元不同")
        tag = f"{tag}__{old_record['sidecar']['unit'].replace('/', '-')}"
    SIDECAR_DIR.mkdir(parents=True, exist_ok=True)
    old_sc_path, new_sc_path = SIDECAR_DIR / f"{tag}.old.json", SIDECAR_DIR / f"{tag}.new.json"
    for p, doc, rec in ((old_sc_path, old_sc, old_record), (new_sc_path, new_sc, new_record)):
        p.write_text(json.dumps({**doc, "head": rec["head"], "tree": rec["tree"], "recipe": recipe},
                                ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    mapping, missing, ambiguous = build_mapping(old_record, set(old_sc["columns"]))
    map_doc = {"schema_version": MAP_SCHEMA, "golden": rel, "recipe": recipe, "source_head": old_record["head"],
               "source_tree": old_record["tree"], "source_sha256": hashlib.sha256(old_sc_path.read_bytes()).hexdigest(),
               "old_name_count": len(old_sc["columns"]), "mapped": len(mapping),
               "renamed": sum(1 for a, b in mapping.items() if a != b), "missing": missing, "ambiguous": ambiguous,
               "mapping": mapping}
    MAPS_DIR.mkdir(parents=True, exist_ok=True)
    map_path = MAPS_DIR / f"{tag}.json"
    map_path.write_text(json.dumps(map_doc, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    result = k2_compare(old_sc["columns"], new_sc["columns"], mapping, fields=())
    # 逐欄紀錄整筆相等（fields 空 ⇒ 比整筆）
    mismatches = [m for m in result["mismatches"]]
    for old_name, rec in old_sc["columns"].items():
        new = mapping.get(old_name)
        if new is not None and new in new_sc["columns"] and new_sc["columns"][new] != rec:
            mismatches.append(f"column:{old_name}->{new}")
    if old_sc["scalars"] != new_sc["scalars"]:
        mismatches.append("scalars")
    if missing or ambiguous:
        mismatches.append(f"map_unmapped:{len(missing)}/{len(ambiguous)}")
    g6 = result["g6_new_lag"]
    shift_ok = _g6_shift_verify(recipe, new_record, g6)
    entry = {"path": rel, "class": "K2", "recipe": recipe, "old_head": old_record["head"], "new_head": new_record["head"],
             "old_sidecar": _rel_or_abs(old_sc_path), "new_sidecar": _rel_or_abs(new_sc_path),
             "map": str(map_path.relative_to(MAIN_REPO)), "compared": result["compared"],
             "value_hash_mismatch": len(mismatches), "mismatches": mismatches[:200], "g6_new_lag": g6,
             "g6_shift_verified": shift_ok if g6 else None,
             "old_elapsed_seconds": old_record.get("elapsed_seconds"), "new_elapsed_seconds": new_record.get("elapsed_seconds")}
    if dry:
        entry["refrozen"] = False
        entry["dry_run"] = True
    elif not mismatches and (not g6 or shift_ok):
        text = _golden_from_new(rel, recipe, new_record)
        (MAIN_REPO / rel).write_text(text, encoding="utf-8")
        entry["refrozen"] = True
    else:
        entry["refrozen"] = False
    entry["new_sha256"] = hashlib.sha256((MAIN_REPO / rel).read_bytes()).hexdigest()
    K2_DIR.mkdir(parents=True, exist_ok=True)
    (K2_DIR / f"{tag}.json").write_text(json.dumps(entry, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                                               encoding="utf-8")
    print(f"[ffname-refreeze k2] {rel}: 比對 {result['compared']} 欄、不符 {len(mismatches)}、⑥ 新 lag {len(g6)}"
          f"（位移 {'已驗' if shift_ok else ('—' if not g6 else '未驗')}）、重凍 {entry['refrozen']}")
    if mismatches:
        print(f"  不符例：{mismatches[:8]}")
    return 0 if entry["refrozen"] else 1


# ================================================================ 收據（主樹）


def _blob(rel: str, head: str) -> Optional[bytes]:
    proc = subprocess.run(["git", "show", f"{head}:{rel}"], cwd=str(MAIN_REPO), capture_output=True)
    return proc.stdout if proc.returncode == 0 else None


def write_receipt(salt_path: Path, consumers_path: Optional[Path], full_ref_path: Optional[Path]) -> int:
    """v21 收據：每檔記類別、映射來源、換名數、值位元組不變證據（K1／K3）或 sidecar 依名逐欄比對（K2）、⑥ 清單、
    鹽差去鹽重算、消費測試結果；全量 reference 往返。缺項（如 failopen K2、全量 reference 未跑）⇒ exit_code 1。"""
    contract = json.loads((MAIN_REPO / "tests/_golden/ffname/contract.json").read_text(encoding="utf-8"))["refreeze"]
    baseline = json.loads((MAIN_REPO / "tests/_golden/ffname/baseline.json").read_text(encoding="utf-8"))
    head = baseline["frozen_at_head"]
    consumers = json.loads(consumers_path.read_text(encoding="utf-8")) if consumers_path else {}
    files: List[Dict[str, Any]] = []
    ok = True
    for rel, disp in sorted(contract["dispositions"].items()):
        cls = disp["class"]
        old = _blob(rel, head)
        now = (MAIN_REPO / rel).read_bytes()
        entry: Dict[str, Any] = {"path": rel, "class": cls, "reason": disp["reason"], "consumers": disp["consumers"],
                                 "old_sha256": hashlib.sha256(old).hexdigest() if old is not None else None,
                                 "new_sha256": hashlib.sha256(now).hexdigest(),
                                 "consumer_run": consumers.get(rel)}
        if cls == "K0":
            entry["byte_identical"] = old == now
            entry["value_hash_mismatch"] = 0 if old == now else 1
        elif cls == "K1":
            mp = MAPS_DIR / f"{_slug(rel)}.json"
            rk = MAPS_DIR / f"{_slug(rel)}.rekey.json"
            if mp.is_file() and rk.is_file():
                m, r = json.loads(mp.read_text(encoding="utf-8")), json.loads(rk.read_text(encoding="utf-8"))
                entry.update({"map": str(mp.relative_to(MAIN_REPO)), "map_source": {"recipe": m["recipe"],
                              "head": m["source_head"], "elapsed_seconds": m.get("record_elapsed_seconds")},
                              "renamed_columns": m["renamed"], "missing": len(m["missing"]),
                              "l65_suffix_derived": m.get("l65_suffix_derived", 0),
                              "hash_fields_recomputed": r["hash_fields_recomputed"],
                              "value_bytes_unchanged": r["new_sha256"] == entry["new_sha256"],
                              "value_hash_mismatch": 0 if r["new_sha256"] == entry["new_sha256"] and not m["missing"] else 1})
            else:
                entry.update({"status": "pending", "value_hash_mismatch": 1})
        elif cls == "K2" and disp.get("recipe") == "failopen":
            unit_files = [K2_DIR / f"{_slug(rel)}__{u.replace('/', '-')}.json" for u in FAILOPEN_UNITS]
            if all(p.is_file() for p in unit_files):
                units = [json.loads(p.read_text(encoding="utf-8")) for p in unit_files]
                entry.update({"units": units, "value_hash_mismatch": sum(u["value_hash_mismatch"] for u in units),
                              "g6_new_lag": sorted({c for u in units for c in u["g6_new_lag"]}),
                              "g6_shift_verified": all(u["g6_shift_verified"] in (True, None) for u in units),
                              "refrozen": all(u["refrozen"] for u in units)})
                if not entry["refrozen"]:
                    entry["value_hash_mismatch"] = max(1, entry["value_hash_mismatch"])
            else:
                entry.update({"status": "pending", "value_hash_mismatch": 1,
                              "units_done": [u for u, p in zip(FAILOPEN_UNITS, unit_files) if p.is_file()]})
        elif cls == "K2":
            kp = K2_DIR / f"{_slug(rel)}.json"
            if kp.is_file():
                k = json.loads(kp.read_text(encoding="utf-8"))
                entry.update({key: k[key] for key in ("recipe", "old_head", "new_head", "old_sidecar", "new_sidecar", "map",
                                                    "compared", "value_hash_mismatch", "mismatches", "g6_new_lag",
                                                    "g6_shift_verified", "refrozen", "old_elapsed_seconds",
                                                    "new_elapsed_seconds")})
                if k["new_sha256"] != entry["new_sha256"]:
                    entry["value_hash_mismatch"] = max(1, entry["value_hash_mismatch"])
                    entry["bytes_unbound"] = True
                if not k.get("refrozen"):
                    entry["status"] = "not_refrozen"  # 如 fftfmeta：改前 golden 不能由改前碼重現（既有漂移），只做 dry 比對
                    ok = False
            else:
                entry.update({"status": "pending", "value_hash_mismatch": 1})
        elif cls == "K3":
            renames = disp["k3_renames"]

            def ren(node: Any) -> Any:
                if isinstance(node, dict):
                    return {renames.get(a, a): ren(b) for a, b in node.items()}
                if isinstance(node, list):
                    return [ren(v) for v in node]
                return node

            exact = old is not None and ren(json.loads(old.decode("utf-8"))) == json.loads(now.decode("utf-8"))
            entry.update({"k3_renames": renames, "value_bytes_unchanged": exact, "value_hash_mismatch": 0 if exact else 1})
        if entry["value_hash_mismatch"]:
            ok = False
        files.append(entry)
    salt = json.loads(salt_path.read_text(encoding="utf-8"))
    salt_entries = []
    for rel_key, group in (("tests/_golden/failopen/baseline.json", "failopen"),
                           ("tests/_golden/probewinsor/baseline.json", "probewinsor")):
        for field, v in sorted(salt[group].items()):
            if group == "failopen" and field not in contract["salt_only_fields"][rel_key]["fields"]:
                continue
            proof = v["desalted_equals_frozen"] if group == "failopen" else v["proof"]
            salt_entries.append({"path": rel_key, "field": field, "frozen": v["frozen"],
                                 "desalted": v.get("desalted_anchor", v.get("desalted")),
                                 "new": v.get("new_anchor", v["now"]), "proof": proof})
            ok = ok and proof
    full: Dict[str, Any]
    if full_ref_path and full_ref_path.is_file():
        sys.path.insert(0, str(MAIN_REPO))
        frz = _freeze_mod()
        full = frz.full_reference_record(json.loads(full_ref_path.read_text(encoding="utf-8")))
        ok = ok and full["parse_failures"] == 0 and full["roundtrip_failures"] == 0 and full["total_columns"] > 0
    else:
        full = {"status": "pending", "timeframes": contract["full_reference"]["timeframes"], "total_columns": 0,
                "parse_failures": None, "roundtrip_failures": None, "columns": []}
        ok = False
    receipt = {"schema_version": "ffname-refreeze-v21", "spec": "docs/FFNAME_SPEC.md v21 §G、Task 4.3",
               "command": "venv/bin/python scripts/ffname_refreeze.py receipt", "exit_code": 0 if ok else 1,
               "head": subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(MAIN_REPO), capture_output=True,
                                      text=True).stdout.strip(),
               "baseline_frozen_at_head": head, "files": files, "salt_only": salt_entries, "full_reference": full}
    out = MAIN_REPO / contract["receipt"]
    out.write_text(json.dumps(receipt, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    pending = [e["path"] for e in files if e.get("status") == "pending"]
    bad = [e["path"] for e in files if e["value_hash_mismatch"] and e.get("status") != "pending"]
    print(f"[ffname-refreeze receipt] exit_code={receipt['exit_code']}；待辦 {pending}；不符 {bad}；"
          f"全量 reference {full.get('status', 'done')} → {out}")
    return receipt["exit_code"]


# ================================================================ CLI


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("record")
    r.add_argument("--recipe", required=True)
    r.add_argument("--out", required=True)
    r.add_argument("--no-instrument", action="store_true")
    r.add_argument("--tree", default=None, help="碼態根目錄（改前 worktree）；預設＝cwd")
    m = sub.add_parser("mapping")
    m.add_argument("--golden", required=True)
    m.add_argument("--record", required=True)
    ml = sub.add_parser("mapping-list")
    ml.add_argument("--label", required=True)
    ml.add_argument("--record", required=True)
    ml.add_argument("--source", required=True)
    ml.add_argument("--pattern", required=True, help="以逗號分隔之路徑（`*`、`{K}`、`[]`），如 delta,added,[]")
    k = sub.add_parser("rekey")
    k.add_argument("--golden", required=True)
    k.add_argument("--salt-proof", default=None)
    k.add_argument("--record", default=None)
    k2p = sub.add_parser("k2")
    k2p.add_argument("--golden", required=True)
    k2p.add_argument("--old", required=True)
    k2p.add_argument("--new", required=True)
    k2p.add_argument("--dry", action="store_true", help="只比對、不寫 golden（改前 golden 本身與改前碼不符時用）")
    rp = sub.add_parser("receipt")
    rp.add_argument("--salt-proof", required=True)
    rp.add_argument("--consumers", default=None)
    rp.add_argument("--full-reference", default=None)
    k.add_argument("--map-label", default=None)
    k.add_argument("--patterns", default=None, help="以 ; 分隔多個路徑，每個以逗號分隔（非 golden 連動檔用）")
    args = ap.parse_args(argv)
    if args.cmd == "record":
        out = Path(args.out).resolve()
        if args.tree:
            os.chdir(args.tree)
        return record(args.recipe, out, not args.no_instrument)
    if args.cmd == "mapping":
        return write_mapping(args.golden, Path(args.record))
    if args.cmd == "k2":
        return k2(args.golden, Path(args.old), Path(args.new), dry=args.dry)
    if args.cmd == "receipt":
        return write_receipt(Path(args.salt_proof), Path(args.consumers) if args.consumers else None,
                             Path(args.full_reference) if args.full_reference else None)
    if args.cmd == "mapping-list":
        return write_mapping_list(args.label, Path(args.record), (MAIN_REPO / args.source).resolve(),
                                  args.pattern.split(","))
    if args.cmd == "rekey":
        patterns = [p.split(",") for p in args.patterns.split(";")] if args.patterns else None
        return rekey(args.golden, Path(args.salt_proof) if args.salt_proof else None,
                     Path(args.record) if args.record else None, args.map_label, patterns)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
