#!/usr/bin/env python3
"""FFPROD Task 2.1：改值候選量測（SPEC `docs/FFPROD_SPEC.md` v9 Task 2.1〔含「v9 補」①–④〕、§G；設計檔
`handoffs/20261026-FFPROD-B3-MEASURE-PLAN.md`）。

v9 補：①格依候選獨有路徑選——`winsor_core_calibration` 於「格設定＋fracdiff／ADF 開」（改前基準 `stat`），另量校準域對
ratio-unsafe 欄之縮尾（選欄差異）；②差異不可達之候選（`UNREACHABLE`：d* 取樣方向）不排生成，收據記
`unreachable_difference`＋碼證＋探針格（A）一次之探針收據；③IC 翻轉只算改值欄、第 5 階段選欄由替換推導、第 6 階段不導出、
改前全欄 IC 受阻 ⇒ `blocked_by: hardware`；④L2 三取值點以 float32 後比、欄序不入判定、欄序差照記。

候選＝盤點收據（`*-ffprod-inventory.json`）之 `disposition=measure` 項（`CANDIDATES` 之鍵集合與之相等，載入時斷言）。
每選項一次獨立完整生成（各自 run 目錄），生成、子行程卡住監看與 §G 值指紋一律重用 `scripts/ffprod_freeze_baseline.py`
（`_generate_in_process`、`cell_fingerprints`、`_identity`、NUMVIEW `_watchdog`），本檔不另寫生成或指紋。
候選以探針切換（子行程內 monkeypatch，不改正式碼）；探針經 `sitecustomize`（`PYTHONPATH` 前置之暫存目錄）同裝於生成所派生之
子行程（L6.5 平行 ADF 之 loky worker 等），各行程之自證紀錄寫於 proof 目錄（`proof-<pid>.json`）。自證失敗 ⇒ 該選項收據拒寫並報錯。

子命令：`plan`（列格×選項與估時；估時讀凍結收據 `*-ffprod-freeze.json` 之格秒數）、`run`（逐選項生成＋指紋＋值差＋IC，
每完成一項原子寫入收據；可續跑：已完成者不重跑）、`ic`（IC 單獨重算）。

用法：`venv/bin/python scripts/ffprod_measure.py plan [--cell C_BTCUSDT_1h]`；
`venv/bin/python scripts/ffprod_measure.py run [--candidates l2_single_source ...] [--cell C_BTCUSDT_1h] [--receipt P]
[--work-root D] [--skip-ic]`；`venv/bin/python scripts/ffprod_measure.py ic [--force]`。
"""
from __future__ import annotations

import argparse
import contextlib
import copy
import hashlib
import importlib.util
import json
import os
import resource
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Mapping, Optional, Sequence, Set, Tuple

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

RECEIPTS_DIR = REPO / "handoffs" / "run_receipts"
INVENTORY_GLOB = "*-ffprod-inventory.json"
FREEZE_RECEIPT_GLOB = "*-ffprod-freeze.json"
RECEIPT_GLOB = "*-ffprod-candidates.json"
FREEZE_SCRIPT = REPO / "scripts" / "ffprod_freeze_baseline.py"
L2_MATRIX_PROBE = RECEIPTS_DIR / "numview_probes" / "l2_arm_matrix.py"
DEFAULT_CELL = "C_BTCUSDT_1h"
DEFAULT_WORK_ROOT = Path(os.environ.get("TMPDIR", "/tmp")) / "ffprod-measure"
SCHEMA_VERSION = 1
SPEC_PATH = REPO / "docs" / "FFPROD_SPEC.md"
#: d* 探針唯一可豁免之自證失敗（差異不可達之觀測本身）；其餘失敗或違規皆不得記 unreachable_difference
DSTAR_NO_EFFECTIVE = "dstar：無校準序列長於 N 之檢定（取樣方向無從生效）"

#: 子行程探針之環境鍵（`FFPROD_` 不屬凍結腳本之清除類前綴，生成隔離不清之）
PROBES_ENV = "FFPROD_MEASURE_PROBES"
SCRIPT_ENV = "FFPROD_MEASURE_SCRIPT"
BLOCKED_BY_HARDWARE = "hardware"
#: 卡死監看終止（log 靜默＝無 CPU 進度心跳、或牆鐘上限）：非記憶體證據，與硬體區分（SPEC v10 補③）
BLOCKED_BY_WATCHDOG = "watchdog_timeout"


class HangDetected(RuntimeError):
    """監看判定程式卡住（無 log 亦無 CPU 進度，原因非記憶體）：已留現場，整跑停止、不自動重跑——依堆疊查因修好再跑。"""


def raise_hang(target: str, watched: Any, item_dir: Path) -> None:
    path = Path(item_dir) / "stall_diagnosis.json"
    _fb()._write_atomic(path, {"target": target, "reason": watched.reason, "cause": watched.cause,
                               "wall_seconds": watched.wall_seconds, **(watched.diagnosis or {})})
    stacks = (watched.diagnosis or {}).get("stacks_file")
    raise HangDetected(f"{target}：程式卡住（{watched.reason}）——現場 {path}、Python 堆疊 {stacks}、原生堆疊 "
                       f"{(watched.diagnosis or {}).get('native_stacks')}；不自動重跑，依堆疊查因修好再跑")


def has_watchdog_timeout(obj: Any) -> bool:
    """結果中任一處受阻類別含 watchdog_timeout（監看終止之結果一律不算完成、續跑重算）。"""
    if isinstance(obj, Mapping):
        if BLOCKED_BY_WATCHDOG in str(obj.get("blocked_by") or ""):
            return True
        return any(has_watchdog_timeout(v) for v in obj.values())
    if isinstance(obj, (list, tuple)):
        return any(has_watchdog_timeout(v) for v in obj)
    return False
#: 自證紀錄之樣本上限（每行程；違規另計總數）
SAMPLE_CAP = 20
#: 逐欄指紋外置門檻（改值欄數；見 `_externalize_fingerprints`）
SIDECAR_MIN_COLUMNS = 1000

#: 改前基準（同一格之設定變體；sigma 候選之改前另以 sigma 設定生成）
BASELINES: Dict[str, Dict[str, Any]] = {
    "default": {"variant": {}, "probes": {"l2": "observe"}},
    "sigma": {"variant": {"preprocessing": {"winsorization": {"method": "sigma"}}}, "probes": {}},
    # SPEC v9 補①：校準縮尾只在平穩化開啟時執行（feature_factory.py:384）⇒ 格設定＋fracdiff／ADF 開（設定取自 NUMVIEW 判準
    # A 格類之平穩化兩步，見 `stationarity_variant`；不另寫參數）；改前另掛縮尾選欄觀測
    "stat": {"variant": "stationarity", "probes": {"winsor_core": "observe"}},
}

#: 平穩化變體之來源格（NUMVIEW 判準 A 格類之 config_override 中 fracdiff／ADF 兩步）
STATIONARITY_SOURCE_CELL = "A_BTCUSDT_1h"

#: SPEC v9 補②：差異不可達之候選（不排生成；收據記 unreachable_difference＋碼證＋A 格探針收據）
UNREACHABLE: Dict[str, Dict[str, Any]] = {
    "dstar_adf_sample_direction": {
        "evidence": [
            "momentum/FeatureEngineering/preprocessing/feature_preprocessor.py:2786（平行 d* 之 ADF sample_size＝_stationarity_n，三路同一 N）",
            "momentum/FeatureEngineering/preprocessing/feature_preprocessor.py:3544（串行 d* 之 ADF sample_size＝_stationarity_n）",
            "momentum/FeatureEngineering/preprocessing/calibration.py:179-187（d* 判定值＝起始日前恰 n 個有限值）",
            "momentum/FeatureEngineering/preprocessing/_fast_adf_numba.py:114-117（只在長於 sample_size 時截前 N）",
            "momentum/FeatureEngineering/preprocessing/_slow_path_parallel.py:121（截後 N；長度 ≤N 時恆等）",
        ],
        "probe_cell": "A_BTCUSDT_1h",
        "probe_option": "first_n",
    },
}

#: 候選（鍵集合＝盤點收據 measure 項之 `candidate_id` 集合）→ 改前基準、選項（探針模式或只 IC）、生效前提
CANDIDATES: Dict[str, Dict[str, Any]] = {
    "l2_single_source": {
        "baseline": "default",
        "options": {"polars_public": {"probes": {"l2": "polars_public"}},
                    "pandas_category": {"probes": {"l2": "pandas_category"}}},
        "requires": {"l2_arm": "L2.polars"},
        "unique_path": "L2 公開結果（compute_all_polars）vs registry 落盤（compute_category 逐類），L5／L6 吃公開結果",
    },
    "winsor_sigma_precision": {
        "baseline": "sigma",
        "options": {"float64": {"probes": {"sigma": "float64"}}},
        "requires": {"winsor_method": "sigma"},
        "unique_path": "sigma 縮尾之滾動均值／標準差（快速臂 float32 累加、pandas 臂 float64 計算後轉 float32）",
    },
    "dstar_adf_sample_direction": {
        "baseline": "default",
        "options": {"first_n": {"probes": {"dstar": "first_n"}}, "last_n": {"probes": {"dstar": "last_n"}}},
        "requires": {"stationarity": True},
        "unique_path": "d* 搜尋之 ADF 取樣（串行快速取前 N、平行取後 N；校準序列長於 N 時檢定不同列）",
    },
    "layer_dtype": {
        "baseline": "default",
        "options": {"preserve": {"probes": {"layer_dtype": "preserve"}}},
        "requires": {},
        "unique_path": "單週期層間轉 float32（多週期保留）",
    },
    "winsor_core_calibration": {
        "baseline": "stat",
        "options": {"unify_numba": {"probes": {"winsor_core": "unify_numba"}},
                    "unify_pandas": {"probes": {"winsor_core": "unify_pandas"}}},
        "requires": {"winsor_enabled": True, "stationarity": True},
        "unique_path": "同一 run 內校準域（校準前置＋公開域預熱探測）走 pandas 縮尾、公開主群組走 numba 快速核心；"
                       "另：校準域縮尾對 ratio-unsafe 欄亦作用（feature_factory.py:2523），公開快速臂跳過"
                       "（feature_preprocessor.py:1729-1740）",
    },
    "winsor_responsibility": {
        "baseline": "default",
        "options": {"ic_winsor_off": {"probes": {}, "ic_only": True}},
        "requires": {},
        "unique_path": "IC 分析前處理預設再縮尾一次（特徵階段已可縮尾）；IC 頁開關後端未讀",
    },
}

#: 候選間交互（SPEC Task 2.1 邊界②：單獨與合併各一次）
INTERACTIONS: Dict[str, Dict[str, Any]] = {
    "sigma_float64+preserve": {"baseline": "sigma", "members": ["winsor_sigma_precision", "layer_dtype"],
                               "probes": {"sigma": "float64", "layer_dtype": "preserve"}},
}

#: IC 只算前處理縮尾關（`winsor_responsibility`）之覆寫（`momentum/Analysis/ic_config_schema.py` PreprocessingConfig）
IC_WINSOR_OFF_OVERRIDE: Dict[str, Any] = {"preprocessing": {"winsorization": {"enabled": False}}}

#: 量測之 IC 一律關 IC 衰減分析（SPEC v11 補③）：翻轉與第 5 階段選欄只用 ic_mean／icir／p_value／t_stat 等欄
#: （`ic_filter_orchestrator._apply_thresholds`），衰減只入報告半衰期欄；全欄 209,053 欄時衰減逾監看上限（量測首跑實測
#: 改前全欄 IC 於衰減段 70 分鐘未完）。等同 IC 頁「foundation」層之 ic_decay 關（`icAnalysisStore.ts` PRESET_TOGGLES）
IC_MEASURE_OVERRIDE: Dict[str, Any] = {"report": {"include_decay_analysis": False}}
#: IC 結果之設定標記：收據中 IC 結果之標記不等於此值者視為未完成（續跑以現行設定重算，全量測同一設定）
IC_MEASURE_SETTINGS = "ic_decay_off"

#: 生成與 IC 之選項收據必備欄（SPEC Task 2.1 驗證段）
OPTION_REQUIRED_KEYS = ("option", "candidate", "cell", "baseline", "probe", "run_dir", "identity", "status",
                        "self_proof", "value_diff", "changed_columns", "fingerprints", "seconds", "peak_rss_bytes",
                        "output_bytes")


class SelfProofFailed(RuntimeError):
    """探針自證失敗 ⇒ 該選項收據拒寫（SPEC Task 2.1 改法）。"""


class SourceRoutingError(SelfProofFailed):
    """L2 選項探針三取值點之指紋不相等或不等於所指來源 ⇒ 該選項收據拒寫（TODO 空殼所立之名；判定見 `verify_proof`）。"""


#: 收據檔名（`<日期>` 為首次建立日；續跑沿用既有檔，見 `default_receipt_path`）
RECEIPT_NAME = "{date}-ffprod-candidates.json"
#: L2 候選之選項值域（同決定紀錄 `canonical_source`）
L2_OPTIONS = tuple(CANDIDATES["l2_single_source"]["options"])


def candidates() -> List[Dict[str, Any]]:
    """量測候選（鍵集合＝盤點收據 measure 項，見 `assert_candidate_set`）：每項 {candidate_id, baseline, options:
    {選項: {probes, ic_only, probe_paths}}, requires, unique_path}。"""
    assert_candidate_set()
    out = []
    for cid, spec in sorted(CANDIDATES.items()):
        opts = {opt: {"probes": dict(o.get("probes") or {}), "ic_only": bool(o.get("ic_only")),
                      "probe_paths": {n: f"scripts/ffprod_measure.py::_install_{n}" for n in (o.get("probes") or {})}}
                for opt, o in spec["options"].items()}
        out.append({"candidate_id": cid, "baseline": spec["baseline"], "options": opts,
                    "requires": dict(spec.get("requires") or {}), "unique_path": spec["unique_path"]})
    return out


# ============================================================================================== 載入

_MODULES: Dict[str, Any] = {}


def _load(name: str, path: Path) -> Any:
    if name not in _MODULES:
        if name in sys.modules:
            _MODULES[name] = sys.modules[name]
        else:
            spec = importlib.util.spec_from_file_location(name, path)
            if spec is None or spec.loader is None:
                raise RuntimeError(f"無法載入 {path}")
            module = importlib.util.module_from_spec(spec)
            sys.modules[name] = module
            spec.loader.exec_module(module)
            _MODULES[name] = module
    return _MODULES[name]


def _fb() -> Any:
    """凍結腳本（格定義、生成、指紋、身分、卡住監看之重用來源）。"""
    return _load("ffprod_freeze_baseline_measure", FREEZE_SCRIPT)


def _single(glob: str) -> Path:
    hits = sorted(RECEIPTS_DIR.glob(glob))
    if len(hits) != 1:
        raise RuntimeError(f"{glob} 須恰一份，實得 {[p.name for p in hits]}")
    return hits[0]


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _sha256_json(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")).hexdigest()


def inventory_measure_ids(path: Optional[Path] = None) -> List[str]:
    """盤點收據之 `disposition=measure` 項之 `candidate_id`（排序）。"""
    inv = json.loads(Path(path or _single(INVENTORY_GLOB)).read_text(encoding="utf-8"))
    out: List[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, Mapping):
            if node.get("disposition") == "measure":
                out.append(str(node["candidate_id"]))
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(inv)
    return sorted(out)


def assert_candidate_set(path: Optional[Path] = None) -> None:
    """`CANDIDATES` 之鍵集合須等於盤點收據之 measure 項集合（SPEC Task 2.1 驗證）；不等 ⇒ AssertionError。"""
    expected = inventory_measure_ids(path)
    assert sorted(CANDIDATES) == expected, f"候選集合 {sorted(CANDIDATES)} ≠ 盤點 measure 項 {expected}"
    assert len(expected) == len(set(expected)), f"盤點 measure 項有重複 candidate_id：{expected}"


# ============================================================================================== 格與計畫

def measure_cell(cell_id: str, baseline: str) -> Dict[str, Any]:
    """量測格＝凍結格清單之 `cell_id` 深合併改前基準之設定變體；id 加基準尾碼（run 目錄區隔）。"""
    fb = _fb()
    cells = {str(c["id"]): c for c in fb._CELL_SPECS}
    if cell_id not in cells:
        raise KeyError(f"格 {cell_id} 不在凍結格清單 {sorted(cells)}")
    cell = copy.deepcopy(cells[cell_id])
    cell["variant"] = fb._deep_merge(cell.get("variant") or {}, baseline_variant(baseline))
    cell["base_cell"] = cell_id
    cell["id"] = f"{cell_id}__{baseline}"
    cell.pop("declared_arm", None)
    return cell


def stationarity_variant() -> Dict[str, Any]:
    """平穩化開之設定變體：NUMVIEW 判準 A 格類 config_override（經凍結腳本 `cell_payload`）之 `preprocessing.
    fractional_differencing`／`adf_differencing` 兩步原樣（不另寫參數）；來源缺任一步或未開 ⇒ RuntimeError。"""
    fb = _fb()
    src = next(c for c in fb._CELL_SPECS if str(c["id"]) == STATIONARITY_SOURCE_CELL)
    pre = (fb.cell_payload(src).get("preprocessing") or {})
    steps = {k: copy.deepcopy(pre.get(k)) for k in ("fractional_differencing", "adf_differencing")}
    if not all(isinstance(v, Mapping) and v.get("enabled") for v in steps.values()):
        raise RuntimeError(f"{STATIONARITY_SOURCE_CELL} 之平穩化設定不完整：{steps}")
    return {"preprocessing": {"enabled": True, **steps}}


def baseline_variant(baseline: str) -> Dict[str, Any]:
    variant = BASELINES[baseline]["variant"]
    return stationarity_variant() if variant == "stationarity" else copy.deepcopy(variant)


def cell_preprocessing(cell: Mapping[str, Any]) -> Dict[str, Any]:
    return _fb()._effective_preprocessing(_fb().cell_payload(cell))


def requirement_conflicts(candidate: str, cell_id: str) -> List[str]:
    """候選之生效前提與格之有效設定相衝之描述（空＝無衝突）。依格之有效前處理（`FactoryConfig` 解析後）判定。"""
    spec = CANDIDATES[candidate]
    req = spec.get("requires") or {}
    pre = cell_preprocessing(measure_cell(cell_id, spec["baseline"]))
    out: List[str] = []
    if req.get("stationarity") and not (pre["fractional_differencing"] or pre["adf_differencing"]):
        out.append(f"{cell_id}（基準 {spec['baseline']}）之 fracdiff／ADF 皆關（{pre}）⇒ 平穩化路徑（校準前置／d* 檢定）"
                   "不執行，探針無從生效（自證必失敗）")
    if req.get("winsor_method") and pre["winsorization"]["method"] != req["winsor_method"]:
        out.append(f"{cell_id}（基準 {spec['baseline']}）縮尾 method＝{pre['winsorization']['method']} ≠ {req['winsor_method']}")
    if req.get("winsor_enabled") and not pre["winsorization"]["enabled"]:
        out.append(f"{cell_id} 縮尾關 ⇒ 縮尾核心探針無從生效")
    return out


def freeze_seconds(cell_id: str) -> Optional[float]:
    """凍結收據（`*-ffprod-freeze.json`）中該凍結格之實測生成秒數；無 ⇒ None（不以他格代替）。"""
    receipt = json.loads(_single(FREEZE_RECEIPT_GLOB).read_text(encoding="utf-8"))
    seconds = ((receipt.get("freeze") or {}).get("cells") or {}).get(cell_id, {}).get("seconds")
    return float(seconds) if isinstance(seconds, (int, float)) else None


def expected_seconds(cell: Mapping[str, Any]) -> Optional[float]:
    """該生成格之預期秒數（監看牆鐘上限之基準、plan 之估時）：取其所屬凍結格（`base_cell`）之實測秒數，且只在其預處理
    設定與該凍結格相同時；設定變體（sigma、平穩化開）無實測 ⇒ None（監看改用判準之 wall_ceiling_seconds），不以他設定或他格代替。"""
    base = str(cell.get("base_cell") or cell["id"])
    if cell_preprocessing(cell) != cell_preprocessing(measure_cell(base, "default")):
        return None
    return freeze_seconds(base)


def plan_items(cell_id: str, candidates: Optional[Sequence[str]] = None) -> List[Dict[str, Any]]:
    """將執行之項目（依序：改前基準、各候選各選項、交互）。每項 {kind, key, candidate, option, baseline, probes, ic_only,
    generation}；只列 `candidates` 所需之基準與交互（交互之成員皆在 `candidates` 時才列）。"""
    chosen = list(candidates) if candidates else sorted(CANDIDATES)
    unknown = sorted(set(chosen) - set(CANDIDATES))
    if unknown:
        raise KeyError(f"未知候選 {unknown}")
    interactions = [k for k, v in INTERACTIONS.items() if set(v["members"]) <= set(chosen)]
    needed = sorted({CANDIDATES[c]["baseline"] for c in chosen} | {INTERACTIONS[k]["baseline"] for k in interactions},
                    key=list(BASELINES).index)
    needed = [b for b in needed if any(CANDIDATES[c]["baseline"] == b for c in chosen if c not in UNREACHABLE)
              or any(INTERACTIONS[k]["baseline"] == b for k in interactions)]
    items: List[Dict[str, Any]] = []
    for bid in needed:
        items.append({"kind": "baseline", "key": f"baseline__{bid}", "candidate": None, "option": None, "baseline": bid,
                      "probes": dict(BASELINES[bid]["probes"]), "ic_only": False, "generation": True})
    for cid in chosen:
        if cid in UNREACHABLE:  # SPEC v9 補②：不排該格生成；只於探針格（A）取一次探針收據
            u = UNREACHABLE[cid]
            items.append({"kind": "unreachable", "key": f"{cid}__unreachable", "candidate": cid, "option": None,
                          "baseline": CANDIDATES[cid]["baseline"],
                          "probes": dict(CANDIDATES[cid]["options"][u["probe_option"]]["probes"]), "ic_only": False,
                          "generation": False, "probe_cell": u["probe_cell"]})
            continue
        for opt, ospec in CANDIDATES[cid]["options"].items():
            items.append({"kind": "option", "key": f"{cid}__{opt}", "candidate": cid, "option": opt,
                          "baseline": CANDIDATES[cid]["baseline"], "probes": dict(ospec.get("probes") or {}),
                          "ic_only": bool(ospec.get("ic_only")), "generation": not ospec.get("ic_only")})
    for key in interactions:
        spec = INTERACTIONS[key]
        items.append({"kind": "interaction", "key": key, "candidate": None, "option": key, "baseline": spec["baseline"],
                      "probes": dict(spec["probes"]), "ic_only": False, "generation": True,
                      "members": list(spec["members"])})
    return items


def plan(cell_id: str, candidates: Optional[Sequence[str]] = None,
         receipt: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    """計畫：逐項之估時（凍結收據該格秒數；IC 秒數未量者記 None，不估）、完成狀態（讀既有收據）與前提衝突。"""
    per_gen = freeze_seconds(cell_id)
    rows = []
    for item in plan_items(cell_id, candidates):
        done = _item_done(receipt or {}, cell_id, item)
        conflicts = [] if item["kind"] == "unreachable" or not item["candidate"] else \
            requirement_conflicts(item["candidate"], cell_id)
        row = {**{k: item[k] for k in ("kind", "key", "baseline", "probes", "ic_only", "generation")},
               "status": "done" if done else "pending", "conflicts": conflicts}
        if item["generation"]:
            # 與 run 之監看預期秒數同一規則（`expected_seconds`）；設定變體無實測 ⇒ None
            est = expected_seconds(measure_cell(cell_id, item["baseline"]))
            row["estimated_generation_seconds"] = est
            row["estimate_basis"] = "凍結格同設定" if est is not None else "設定變體：凍結收據無同設定實測，未估"
        else:
            row["estimated_generation_seconds"] = 0.0
        if item["kind"] == "unreachable":
            row.update(probe_cell=item["probe_cell"],
                       probe_estimated_seconds=expected_seconds(measure_cell(item["probe_cell"], item["baseline"])),
                       note="差異不可達（SPEC v9 補②）：不於本格生成；探針收據於 probe_cell 生成一次")
        rows.append(row)
    pending = [r for r in rows if r["status"] == "pending" and r["generation"]]
    known = [r["estimated_generation_seconds"] for r in pending if r["estimated_generation_seconds"] is not None]
    return {"cell": cell_id, "per_generation_seconds_source": f"{_single(FREEZE_RECEIPT_GLOB).name} freeze.cells.{cell_id}",
            "per_generation_seconds": per_gen, "generations_total": sum(1 for r in rows if r["generation"]),
            "generations_pending": len(pending), "estimated_pending_generation_seconds_known": sum(known),
            "generations_pending_unestimated": len(pending) - len(known),
            "ic_seconds": None, "ic_seconds_note": "IC 秒數無既有實測收據；量測時逐項記實際秒數（不估）",
            "items": rows}


# ============================================================================================== 探針（子行程內）

class _ProofLog:
    """單一行程之自證紀錄：計數、樣本、違規；寫 `<proof_dir>/proof-<pid>.json`（原子取代；違規立即寫，其餘至多每秒一次，
    行程結束時 atexit 再寫）。"""

    def __init__(self, proof_dir: Path, role: str) -> None:
        self.proof_dir = Path(proof_dir)
        self.role = role
        self.pid = os.getpid()
        self.installed: Dict[str, str] = {}
        self.bindings: Dict[str, Any] = {}
        self.counters: Dict[str, int] = {}
        self.samples: Dict[str, List[Any]] = {}
        self.violations: List[str] = []
        self.violation_count = 0
        self.overhead = 0.0
        self.extra: Dict[str, Any] = {}
        self._last = 0.0
        self._lock = threading.RLock()

    def count(self, key: str, n: int = 1) -> None:
        with self._lock:
            self.counters[key] = self.counters.get(key, 0) + n
            value = self.counters[key]
        if value & (value - 1) == 0 or time.monotonic() - self._last >= 1.0:
            self.flush()

    def sample(self, key: str, value: Any) -> None:
        with self._lock:
            bucket = self.samples.setdefault(key, [])
            if len(bucket) < SAMPLE_CAP:
                bucket.append(value)

    def violate(self, message: str) -> None:
        with self._lock:
            self.violation_count += 1
            if len(self.violations) < SAMPLE_CAP:
                self.violations.append(message)
        self.flush()

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {"pid": self.pid, "role": self.role, "installed": dict(self.installed), "bindings": dict(self.bindings),
                    "counters": dict(self.counters), "samples": copy.deepcopy(self.samples),
                    "violations": list(self.violations), "violation_count": self.violation_count,
                    "overhead_seconds": self.overhead, "extra": copy.deepcopy(self.extra)}

    def flush(self) -> None:
        try:
            self.proof_dir.mkdir(parents=True, exist_ok=True)
            path = self.proof_dir / f"proof-{self.pid}.json"
            tmp = path.with_suffix(f".tmp{threading.get_ident()}")
            tmp.write_text(json.dumps(self.snapshot(), ensure_ascii=False, default=str), encoding="utf-8")
            os.replace(tmp, path)
            self._last = time.monotonic()
        except OSError:
            pass

    @contextlib.contextmanager
    def timed(self) -> Iterator[None]:
        started = time.perf_counter()
        try:
            yield
        finally:
            with self._lock:
                self.overhead += time.perf_counter() - started


_LOG: Optional[_ProofLog] = None


def _log() -> _ProofLog:
    assert _LOG is not None, "探針未安裝"
    return _LOG


# ---------------------------------------------------------------------------------------------- 指紋工具（L2 三取值點）

def f32_fingerprints(frame: Any, chunk: int = 2000) -> Dict[str, Any]:
    """L2 取值點指紋：於共同消費 dtype float32（`FeatureFactory._ensure_float32`＝`_execute_layer1_6` 層間轉型與
    `_coerce_persistence_frame` 落盤轉型之同一函式）逐欄以 `numview_helpers.frame_fingerprints` 取 `dtype`／`nan`／
    `values_native`（分塊，不建全表副本）；欄名重複者以 `名\\x00dup<k>` 區分。回傳 {columns: {欄: {dtype,nan,values_native}},
    order: [欄], native_dtypes: [原生 dtype]}。"""
    import numpy as np
    import pandas as pd

    from tests.feature_engineering import numview_helpers as nh

    names = [str(c) for c in frame.columns]
    seen: Dict[str, int] = {}
    keys = []
    for name in names:
        k = seen.get(name, 0)
        keys.append(name if k == 0 else f"{name}\x00dup{k}")
        seen[name] = k + 1
    columns: Dict[str, Dict[str, str]] = {}
    for start in range(0, len(names), chunk):
        part = frame.iloc[:, start:start + chunk]
        arr = np.asarray(part.to_numpy(dtype=np.float32, copy=True))
        sub = pd.DataFrame(arr, columns=keys[start:start + chunk], copy=False)
        fps = nh.frame_fingerprints(sub)["columns"]
        for key in keys[start:start + chunk]:
            entry = fps[key]
            columns[key] = {"dtype": entry["dtype"], "nan": entry["nan"], "values_native": entry["values_native"]}
    return {"columns": columns, "order": keys, "native_dtypes": sorted({str(t) for t in frame.dtypes})}


def compare_points(a: Mapping[str, Any], b: Mapping[str, Any]) -> Dict[str, Any]:
    """兩取值點指紋之比較：只在一方之欄數、值或 NaN 不等之欄數、欄序是否相同（共同欄之相對順序）；`equal`＝欄集合相同且
    逐欄 dtype／nan／values_native 皆等（欄序另記，不入 `equal`：registry 依類別分群落盤，其串接序本即依類別）。"""
    ca, cb = a["columns"], b["columns"]
    only_a = sorted(set(ca) - set(cb))
    only_b = sorted(set(cb) - set(ca))
    common = [c for c in a["order"] if c in cb]
    diff_values = [c for c in common if ca[c]["values_native"] != cb[c]["values_native"] or ca[c]["dtype"] != cb[c]["dtype"]]
    diff_nan = [c for c in common if ca[c]["nan"] != cb[c]["nan"]]
    order_b = [c for c in b["order"] if c in ca]
    return {"only_first": len(only_a), "only_second": len(only_b), "diff_values": len(diff_values),
            "diff_nan": len(diff_nan), "order_equal": common == order_b,
            "examples": {"only_first": only_a[:5], "only_second": only_b[:5], "diff_values": diff_values[:5]},
            "equal": not only_a and not only_b and not diff_values and not diff_nan}


def merge_point_fps(parts: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    columns: Dict[str, Any] = {}
    order: List[str] = []
    dtypes: Set[str] = set()
    for p in parts:
        for key in p["order"]:
            if key in columns:
                key = f"{key}\x00dupR{len(order)}"
            order.append(key)
        columns.update(p["columns"])
        dtypes |= set(p.get("native_dtypes") or [])
    return {"columns": columns, "order": order, "native_dtypes": sorted(dtypes)}


# ---------------------------------------------------------------------------------------------- L2 探針

class _L2State:
    def __init__(self) -> None:
        self.points: Dict[str, Dict[str, Any]] = {}
        self.native: Dict[str, List[Dict[str, Any]]] = {}
        self.checks: List[Dict[str, Any]] = []
        self.compute_all_polars_calls = 0
        self.compute_category_calls = 0
        self.current_public: Any = None


_L2 = _L2State()


def _ctx_key(factory: Any) -> str:
    return f"{id(factory)}|{getattr(factory, '_current_timeframe', None)}|" \
           f"{'calibration' if getattr(factory, '_calibration_domain', False) else 'main'}"


def _install_l2(mode: str) -> None:
    """L2 探針。`observe`（改前；不換源）：記公開結果（`_layer2_derived_polars` 回傳＝`compute_all_polars`）、registry 落盤
    （`_persist_layer2_category_group` 所收逐類 `category_frame`）與 L5／L6 實收 L2 三取值點之指紋並兩兩比（邊界③，不判）；
    另以 NUMVIEW `compare_l2_arms` 記公開結果對各類落盤之原生值差。`polars_public`／`pandas_category`（選項）：以替代之
    `_layer2_derived_polars` 把三取值點全部路由至該選項來源（公開＝來源；落盤＝來源依類切片〔polars〕或逐類來源本身〔pandas〕），
    並於三處取指紋自證三者相等且等於來源（違規即記）。"""
    from momentum.FeatureEngineering import feature_factory as ff
    from momentum.FeatureEngineering import polars_adapter as pa

    FF = ff.FeatureFactory
    log = _log()
    eng_cls = ff._derived_operator_engine_cls()
    real_polars = FF._layer2_derived_polars
    real_persist = FF._persist_layer2_category_group
    real_l5, real_l6 = FF._layer5_cross_sectional, FF._layer6_meta_features
    real_cap, real_cc = eng_cls.compute_all_polars, eng_cls.compute_category
    matrix = _load("ffprod_numview_l2_arm_matrix", L2_MATRIX_PROBE) if mode == "observe" else None

    def cap_spy(self: Any, *args: Any, **kwargs: Any) -> Any:
        _L2.compute_all_polars_calls += 1
        log.count("l2.compute_all_polars")
        out = real_cap(self, *args, **kwargs)
        if mode == "observe":
            _L2.current_public = out  # 改前：落盤迴圈（同一 L2 呼叫內）以之比原生值差；呼叫返回即釋放
        return out

    def cc_spy(self: Any, *args: Any, **kwargs: Any) -> Any:
        _L2.compute_category_calls += 1
        log.count("l2.compute_category")
        return real_cc(self, *args, **kwargs)

    eng_cls.compute_all_polars = cap_spy  # type: ignore[assignment]
    eng_cls.compute_category = cc_spy  # type: ignore[assignment]

    def record_point(key: str, name: str, fp: Dict[str, Any]) -> None:
        _L2.points.setdefault(key, {})[name] = fp

    def persist_spy(self: Any, category: str, frame: Any) -> Any:
        if (getattr(self, "_cgsa_registry", None) is not None and getattr(self, "_current_timeframe", None)
                and frame is not None and not frame.empty):
            with log.timed():
                key = _ctx_key(self)
                pts = _L2.points.setdefault(key, {})
                pts.setdefault("registry_parts", []).append(f32_fingerprints(frame))
                if matrix is not None and _L2.current_public is not None:
                    stat = matrix.compare_l2_arms(_L2.current_public, frame)
                    stat = {k: v for k, v in stat.items() if k != "only_returned"}
                    _L2.native.setdefault(key, []).append({"category": str(category), **stat})
        return real_persist(self, category, frame)

    def check_use(self: Any, layer: str, layer2: Any) -> None:
        with log.timed():
            key = _ctx_key(self)
            pts = _L2.points.get(key) or {}
            used = f32_fingerprints(layer2) if layer2 is not None and getattr(layer2, "shape", (0, 0))[1] else None
            if used is None or "public" not in pts:
                return
            record = {"key": key, "layer": layer, "public_vs_used": compare_points(pts["public"], used)}
            if pts.get("registry_parts"):
                registry = merge_point_fps(pts["registry_parts"])
                record["public_vs_registry"] = compare_points(pts["public"], registry)
                record["registry_vs_used"] = compare_points(registry, used)
            if "source" in pts:
                record["source_vs_public"] = compare_points(pts["source"], pts["public"])
            _L2.checks.append(record)
            log.count(f"l2.use.{layer}")
            if mode != "observe":
                bad = [name for name in ("public_vs_used", "public_vs_registry", "registry_vs_used", "source_vs_public")
                       if name in record and not record[name]["equal"]]
                if bad:
                    log.violate(f"L2 {mode} {key} {layer}：取值點不等 {bad}")

    def l5_spy(self: Any, layer1: Any, layer2: Any, config: Any) -> Any:
        check_use(self, "L5", layer2)
        return real_l5(self, layer1, layer2, config)

    def l6_spy(self: Any, layer1: Any, layer2: Any, data: Any, config: Any) -> Any:
        check_use(self, "L6", layer2)
        return real_l6(self, layer1, layer2, data, config)

    if mode == "observe":
        def polars_spy(self: Any, layer1: Any, data: Any, config: Any) -> Any:
            key = _ctx_key(self)
            _L2.points[key] = {}
            _L2.current_public = None
            try:
                result = real_polars(self, layer1, data, config)
            finally:
                _L2.current_public = None
            with log.timed():
                _L2.points[key]["public"] = f32_fingerprints(result[0])
            log.count("l2.observe_calls")
            return result

        FF._layer2_derived_polars = polars_spy  # type: ignore[assignment]
        FF._persist_layer2_category_group = persist_spy  # type: ignore[assignment]
    else:
        def routed(self: Any, layer1: Any, data: Any, config: Any) -> Any:
            import pandas as pd

            key = _ctx_key(self)
            _L2.points[key] = {}
            engine = eng_cls(self._filter_operators_config(config.operators))
            specs = self._build_indicator_specs(layer1, config)
            failed: List[str] = []
            log.count(f"l2.{mode}_calls")
            if mode == "polars_public":
                before_cc = _L2.compute_category_calls
                with _polars_category_recorder(eng_cls, pa) as cat_cols:
                    try:
                        result = engine.compute_all_polars(layer1, data, specs)
                    except Exception:  # noqa: BLE001 — 同正式碼：Polars 失敗 ⇒ 空表＋all_operators 失敗
                        return pd.DataFrame(index=layer1.index), ("all_operators",), 0
                if result is None or result.empty:
                    return pd.DataFrame(index=layer1.index), (), 0
                with log.timed():
                    flat = [c for cat in eng_cls.OPERATOR_CATEGORIES for c in cat_cols.get(cat, [])]
                    if sorted(map(str, flat)) != sorted(map(str, result.columns)) or len(flat) != len(set(flat)):
                        log.violate(f"L2 polars_public {key}：類別欄記錄與公開結果欄不符或重複（記 {len(flat)}、"
                                    f"公開 {result.shape[1]}）")
                    # 來源＝compute_all_polars 回傳物件本身（公開結果即同一物件，見下方 public）
                    _L2.points[key]["source"] = f32_fingerprints(result)
                    _L2.points[key]["public"] = _L2.points[key]["source"]
                    _L2.points[key]["public_is_source_object"] = True
                present = 1
                if self._cgsa_registry is not None:
                    present = 0
                    for category in eng_cls.OPERATOR_CATEGORIES:
                        cols = [c for c in cat_cols.get(category, []) if c in result.columns]
                        if not cols:
                            continue
                        self._persist_layer2_category_group(category, result.loc[:, cols])
                        present += 1
                    if present == 0:
                        present = 1
                if _L2.compute_category_calls != before_cc:
                    log.violate(f"L2 polars_public {key}：探針內仍呼叫 compute_category "
                                f"{_L2.compute_category_calls - before_cc} 次")
            else:
                frames: List[Any] = []
                for category in eng_cls.OPERATOR_CATEGORIES:
                    try:
                        frame = engine.compute_category(layer1, data, specs, category)
                    except Exception:  # noqa: BLE001 — 同正式碼：單類失敗記入 failed、續他類
                        failed.append(category)
                        continue
                    if frame is not None and not frame.empty:
                        frames.append((category, frame))
                        with log.timed():  # 來源＝逐類 compute_category 輸出（串接前逐類取指紋）
                            _L2.points[key].setdefault("source_parts", []).append(f32_fingerprints(frame))
                result = pd.concat([f for _c, f in frames], axis=1) if frames else pd.DataFrame(index=layer1.index)
                if result.empty:
                    return result, tuple(failed), 0
                with log.timed():
                    _L2.points[key]["source"] = merge_point_fps(_L2.points[key].pop("source_parts", []))
                    _L2.points[key]["public"] = f32_fingerprints(result)
                present = 1
                if self._cgsa_registry is not None:
                    present = 0
                    for category, frame in frames:
                        self._persist_layer2_category_group(category, frame)
                        present += 1
            return result, tuple(failed), present

        FF._layer2_derived_polars = routed  # type: ignore[assignment]
        FF._persist_layer2_category_group = persist_spy  # type: ignore[assignment]
    FF._layer5_cross_sectional = l5_spy  # type: ignore[assignment]
    FF._layer6_meta_features = l6_spy  # type: ignore[assignment]
    log.bindings["l2"] = {"FeatureFactory._layer2_derived_polars": FF._layer2_derived_polars is not real_polars}


@contextlib.contextmanager
def _polars_category_recorder(eng_cls: Any, pa: Any) -> Iterator[Dict[str, List[str]]]:
    """`compute_all_polars` 期間記每類別之輸出欄（Polars 四類＝`polars_adapter` 之 ratio／diff〔Cross〕／momentum／
    distance；其餘三類＝pandas 回退之 `_compute_category_from_feature_info`）。"""
    recorded: Dict[str, List[str]] = {}
    mapping = {"polars_l2_derived_ratio": "Ratio", "polars_l2_derived_diff": "Cross",
               "polars_l2_derived_momentum": "Momentum", "polars_l2_derived_distance": "Distance"}
    saved = {name: getattr(pa, name) for name in mapping}
    real_cat = eng_cls._compute_category_from_feature_info

    def wrap(name: str, category: str) -> Callable[..., Any]:
        real = saved[name]

        def inner(*args: Any, **kwargs: Any) -> Any:
            out = real(*args, **kwargs)
            recorded.setdefault(category, []).extend(str(c) for c in out.columns)
            return out

        return inner

    def cat_spy(self: Any, *args: Any, **kwargs: Any) -> Any:
        out = real_cat(self, *args, **kwargs)
        category = kwargs.get("category", args[3] if len(args) > 3 else None)
        if out is not None and not out.empty:
            recorded.setdefault(str(category), []).extend(str(c) for c in out.columns)
        return out

    for name, category in mapping.items():
        setattr(pa, name, wrap(name, category))
    eng_cls._compute_category_from_feature_info = cat_spy
    try:
        yield recorded
    finally:
        for name, fn in saved.items():
            setattr(pa, name, fn)
        eng_cls._compute_category_from_feature_info = real_cat


# ---------------------------------------------------------------------------------------------- sigma 精度探針

def _install_sigma(mode: str) -> None:
    """`_rolling_mean_std` 改 float64 計算且不轉 float32（快速臂之 float32 輸入亦先轉 float64）；替換
    `_numba_transforms`、`feature_preprocessor`、`polars_adapter` 三處綁定（後二者以 from-import 取得）。自證：每次呼叫之計算
    輸入與回傳皆 float64、三處綁定皆為探針。"""
    import numpy as np

    from momentum.FeatureEngineering.preprocessing import _numba_transforms as nt

    assert mode == "float64", mode
    log = _log()
    real = nt._rolling_mean_std

    def probe(arr: Any, window: int, min_periods: int = 1) -> Tuple[Any, Any]:
        src_dtype = str(np.asarray(arr).dtype)
        arr64 = np.asarray(arr, dtype=np.float64)
        if nt._HAS_BN and window <= arr64.shape[0] and min_periods <= window:
            mean = nt.bn.move_mean(arr64, window=window, min_count=min_periods, axis=0)
            std = nt.bn.move_std(arr64, window=window, min_count=min_periods, axis=0, ddof=1)
            branch = "bottleneck"
        else:
            mean, std = _rolling_mean_std_f64_fallback(arr64, window, min_periods)
            branch = "cumsum"
        ok = arr64.dtype == np.float64 and mean.dtype == np.float64 and std.dtype == np.float64
        log.count("sigma.calls")
        log.count(f"sigma.input.{src_dtype}")
        log.sample("sigma.calls", {"input_dtype": src_dtype, "compute_dtype": str(arr64.dtype), "branch": branch,
                                   "mean_dtype": str(mean.dtype), "std_dtype": str(std.dtype), "shape": list(arr64.shape)})
        if not ok:
            log.violate(f"sigma：計算或回傳非 float64（{arr64.dtype}／{mean.dtype}／{std.dtype}）")
        return mean, std

    probe.__ffprod_real__ = real  # type: ignore[attr-defined]
    bindings: Dict[str, bool] = {}
    for modname in ("momentum.FeatureEngineering.preprocessing._numba_transforms",
                    "momentum.FeatureEngineering.preprocessing.feature_preprocessor",
                    "momentum.FeatureEngineering.polars_adapter"):
        module = importlib.import_module(modname)
        if hasattr(module, "_rolling_mean_std"):
            setattr(module, "_rolling_mean_std", probe)
            bindings[modname] = getattr(module, "_rolling_mean_std") is probe
    log.bindings["sigma"] = bindings
    if not all(bindings.values()) or len(bindings) != 3:
        log.violate(f"sigma：綁定未全換 {bindings}")


def _rolling_mean_std_f64_fallback(arr: Any, window: int, min_periods: int) -> Tuple[Any, Any]:
    """`_numba_transforms._rolling_mean_std` 之 cumsum 回退分支之 float64 版（只去掉 `.astype(np.float32)`）。"""
    import numpy as np

    mask = ~np.isnan(arr)
    safe = np.where(mask, arr, 0.0)
    cumsum = np.cumsum(safe, axis=0)
    cumsum2 = np.cumsum(safe ** 2, axis=0)
    cumcnt = np.cumsum(mask.astype(np.float64), axis=0)
    shifted = [np.zeros_like(x) for x in (cumsum, cumsum2, cumcnt)]
    for target, source in zip(shifted, (cumsum, cumsum2, cumcnt)):
        target[window:] = source[:-window]
    win_sum, win_sum2, win_cnt = cumsum - shifted[0], cumsum2 - shifted[1], cumcnt - shifted[2]
    mean = win_sum / np.where(win_cnt > 0, win_cnt, 1.0)
    variance = np.maximum((win_sum2 - win_cnt * mean ** 2) / np.where(win_cnt > 1, win_cnt - 1, 1.0), 0.0)
    std = np.sqrt(variance)
    no_data = win_cnt < min_periods
    mean[no_data] = np.nan
    std[no_data] = np.nan
    return mean, std


# ---------------------------------------------------------------------------------------------- d* 取樣方向探針

def dstar_slice(values: Any, sample_size: int, mode: str) -> Tuple[Any, Dict[str, int]]:
    """有限值序列取 `sample_size` 個：`first_n`＝前 N、`last_n`＝後 N；回傳 (樣本, {L, N, start, end})。"""
    import numpy as np

    clean = np.asarray(values, dtype=np.float64).reshape(-1)
    clean = clean[np.isfinite(clean)]
    n = max(1, int(sample_size))
    size = int(clean.size)
    if mode == "first_n":
        start, end = 0, min(size, n)
    elif mode == "last_n":
        start, end = max(0, size - n), size
    else:
        raise ValueError(mode)
    return clean[start:end], {"L": size, "N": n, "start": start, "end": end}


def _install_dstar(mode: str) -> None:
    """d* 之 ADF 取樣統一：串行 d* 搜尋（`FeaturePreprocessor._find_min_d` 內經 `_adf_pvalue_for_values`，原取前 N）與平行
    （`_slow_path_parallel._statsmodels_adf_pvalue`，只供 d* 搜尋之 `adf_fn`，原取後 N）皆先依 `mode` 取樣再交原函式（原函式之
    再切片於 ≤N 之輸入為恆等）。串行之 `_adf_pvalue_for_values` 另有非 d* 之呼叫（`_get_non_stationary_columns`、
    `_apply_adf_differencing`，皆先 head(N)）——只在 `_find_min_d` 執行中（執行緒區域旗標）改取樣，其餘原樣（另計次數）。
    自證：每次 d* 檢定所取列索引＝前 N（`first_n`）或後 N（`last_n`）；另記校準序列長於 N 之次數（取樣方向真生效者）。主行程另記
    `ParallelSlowPath.map` 之 n_jobs 與項數（平行有派工而 worker 無紀錄 ⇒ 自證失敗）。"""
    from momentum.FeatureEngineering.preprocessing import _slow_path_parallel as sp
    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

    log = _log()
    real_serial = FeaturePreprocessor.__dict__["_adf_pvalue_for_values"].__func__
    real_parallel = sp._statsmodels_adf_pvalue
    real_find = FeaturePreprocessor._find_min_d
    in_dstar = threading.local()

    def find_spy(self: Any, *args: Any, **kwargs: Any) -> Any:
        depth = getattr(in_dstar, "depth", 0)
        in_dstar.depth = depth + 1
        try:
            return real_find(self, *args, **kwargs)
        finally:
            in_dstar.depth = depth

    FeaturePreprocessor._find_min_d = find_spy  # type: ignore[assignment]

    def check(path: str, values: Any, sample_size: int) -> Any:
        import numpy as np

        sample, info = dstar_slice(values, sample_size, mode)
        clean = np.asarray(values, dtype=np.float64).reshape(-1)
        clean = clean[np.isfinite(clean)]
        expected = (0, min(info["L"], info["N"])) if mode == "first_n" else (max(0, info["L"] - info["N"]), info["L"])
        log.count(f"dstar.{path}.calls")
        if info["L"] > info["N"]:
            log.count(f"dstar.{path}.effective")
        log.sample(f"dstar.{path}", info)
        with log._lock:  # 探針收據（SPEC v9 補②）：L 最大值與 N 值集合
            stat = log.extra.setdefault("dstar", {}).setdefault(path, {"max_L": 0, "N_values": []})
            stat["max_L"] = max(stat["max_L"], info["L"])
            if info["N"] not in stat["N_values"]:
                stat["N_values"].append(info["N"])
        if (info["start"], info["end"]) != expected or not np.array_equal(sample, clean[expected[0]:expected[1]]):
            log.violate(f"dstar {path}：取樣列 {info} ≠ 預期 {expected}")
        return sample

    def serial(values: Any, sample_size: int = 500) -> float:
        if getattr(in_dstar, "depth", 0) <= 0:
            log.count("dstar.serial.non_dstar_calls")
            return real_serial(values, sample_size)
        return real_serial(check("serial", values, sample_size), sample_size)

    def parallel(values: Any, sample_size: int) -> float:
        return real_parallel(check("parallel", values, sample_size), sample_size)

    FeaturePreprocessor._adf_pvalue_for_values = staticmethod(serial)  # type: ignore[assignment]
    sp._statsmodels_adf_pvalue = parallel
    real_map = sp.ParallelSlowPath.map

    def map_spy(self: Any, items: Any, worker_function: Any) -> Any:
        log.count("dstar.map_calls")
        if self.n_jobs > 1 and items and not sys.platform.startswith("win"):
            log.count("dstar.map_parallel_items", len(items))
        else:
            log.count("dstar.map_inprocess_items", len(items or []))
        return real_map(self, items, worker_function)

    sp.ParallelSlowPath.map = map_spy  # type: ignore[assignment]
    log.bindings["dstar"] = {"serial": FeaturePreprocessor._adf_pvalue_for_values is serial,
                             "parallel": sp._statsmodels_adf_pvalue is parallel}


# ---------------------------------------------------------------------------------------------- 層間 dtype 探針

def _install_layer_dtype(mode: str) -> None:
    """單週期 `_execute_layer1_6` 一律以 `preserve_dtype=True` 執行（同多週期 `_execute_layer1_6_preserve_dtype`）。
    自證：層函式返回後之層間轉型（`_ensure_float32` 於 `_execute_layer1_6` 收尾段之呼叫）為 0 次；被改為 preserve 之呼叫 ≥1；
    另記各層輸出 dtype（層函式內部之落盤轉型不計）。"""
    from momentum.FeatureEngineering import feature_factory as ff

    assert mode == "preserve", mode
    FF = ff.FeatureFactory
    log = _log()
    real_exec = FF._execute_layer1_6
    real_cast = FF.__dict__["_ensure_float32"].__func__
    tls = threading.local()

    def stack() -> List[str]:
        if not hasattr(tls, "stack"):
            tls.stack = []
        return tls.stack

    def exec_probe(self: Any, layer_name: str, func: Callable, *args: Any, preserve_dtype: bool = False) -> Any:
        def wrapped(*a: Any) -> Any:
            stack().append("func")
            try:
                return func(*a)
            finally:
                stack().pop()

        log.count("layer_dtype.calls")
        if not preserve_dtype:
            log.count("layer_dtype.forced")
        stack().append("post")
        try:
            result = real_exec(self, layer_name, wrapped, *args, preserve_dtype=True)
        finally:
            stack().pop()
        data = getattr(result, "data", None)
        if data is not None and not data.empty:
            log.extra.setdefault("layer_dtypes", {}).setdefault(str(layer_name), [])
            seen = log.extra["layer_dtypes"][str(layer_name)]
            for t in sorted({str(t) for t in data.dtypes}):
                if t not in seen:
                    seen.append(t)
        return result

    def cast_spy(df: Any) -> Any:
        if stack() and stack()[-1] == "post":
            log.violate("layer_dtype：_execute_layer1_6 收尾段仍呼叫 _ensure_float32")
        return real_cast(df)

    FF._execute_layer1_6 = exec_probe  # type: ignore[assignment]
    FF._ensure_float32 = staticmethod(cast_spy)  # type: ignore[assignment]
    log.bindings["layer_dtype"] = {"_execute_layer1_6": FF._execute_layer1_6 is exec_probe}


# ---------------------------------------------------------------------------------------------- 縮尾核心探針

def _install_winsor_core(mode: str) -> None:
    """`unify_numba`：校準域（`FeatureFactory._calibration_winsorizer` 所回之縮尾器；校準前置與公開域預熱探測兩呼叫點）之
    `_apply_winsorization` 改走快速核心（`_registry_fast_transform`，同公開主群組之核心；選欄依該縮尾器之 apply_to）。
    `unify_pandas`：公開主群組之快速核心（`FeaturePreprocessor._registry_fast_transform`）改走 pandas `_apply_winsorization`
    （同校準域之核心；以不與任何輸入欄同名之位置欄名呼叫，故不寫執行紀錄）。只換核心、不換選欄（ratio-unsafe 切片照舊）。
    `observe`（改前）：不換核心，只記錄。三模式皆記校準域縮尾之呼叫點（校準前置 `run_calibration_preflight` 內／公開域預熱
    探測）與 ratio-unsafe 欄之選欄差異（`record_unsafe`；SPEC v9 補①）。
    自證：校準前置確有執行且其內校準縮尾呼叫 ≥1；`unify_numba` 校準域快速核心呼叫 ≥1 且校準域 pandas 核心呼叫 0；
    `unify_pandas` 改道呼叫 ≥1 且 numba `transform_array_fast` 呼叫 0。"""
    import numpy as np
    import pandas as pd

    from momentum.FeatureEngineering import feature_factory as ff
    from momentum.FeatureEngineering.preprocessing import _numba_transforms as nt
    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

    log = _log()
    real_apply = FeaturePreprocessor._apply_winsorization
    real_taf = nt.transform_array_fast

    def apply_spy(self: Any, df: Any) -> Any:
        if getattr(self, "_ffprod_calibration", False):
            log.count("winsor_core.calibration_pandas_calls")
            if mode == "unify_numba":
                log.violate("winsor_core unify_numba：校準域仍走 pandas 核心")
        return real_apply(self, df)

    def taf_spy(*args: Any, **kwargs: Any) -> Any:
        log.count("winsor_core.transform_array_fast_calls")
        if mode == "unify_pandas":
            log.violate("winsor_core unify_pandas：公開仍呼叫 numba transform_array_fast")
        return real_taf(*args, **kwargs)

    from momentum.FeatureEngineering.feature_naming import is_ratio_unsafe_column

    if mode not in ("observe", "unify_numba", "unify_pandas"):
        raise ValueError(mode)
    FeaturePreprocessor._apply_winsorization = apply_spy  # type: ignore[assignment]
    nt.transform_array_fast = taf_spy
    real_calib = ff.FeatureFactory._calibration_winsorizer
    real_preflight = ff.FeatureFactory.run_calibration_preflight
    tls = threading.local()
    unsafe_seen: Dict[str, Dict[str, Any]] = {}

    def preflight_spy(self: Any, *args: Any, **kwargs: Any) -> Any:
        log.count("winsor_core.preflight_calls")
        tls.preflight = getattr(tls, "preflight", 0) + 1
        try:
            return real_preflight(self, *args, **kwargs)
        finally:
            tls.preflight -= 1

    def record_unsafe(site: str, before: Any, after: Any) -> None:
        """校準域縮尾對 ratio-unsafe 欄之作用（公開快速臂跳過此類欄，feature_preprocessor.py:1729-1740）：欄集合、值有變之欄、
        最大絕對差（兩側皆有限之格）、NaN 遮罩差之欄。"""
        cols = [c for c in before.columns if is_ratio_unsafe_column(str(c))]
        with log.timed():
            node = unsafe_seen.setdefault(site, {"columns": set(), "changed": set(), "nan_diff": set(), "max_abs": 0.0,
                                                 "calls": 0, "input_columns": 0})
            node["calls"] += 1  # 呼叫數含無 ratio-unsafe 欄者（記 0 欄而非缺紀錄）
            node["input_columns"] += int(before.shape[1])
            if not cols:
                log.extra["ratio_unsafe"] = _ratio_unsafe_view(unsafe_seen)
                return
            b = before.loc[:, cols].to_numpy(dtype=np.float64)
            a = after.loc[:, cols].to_numpy(dtype=np.float64)
            nan_diff = (np.isnan(a) != np.isnan(b)).any(axis=0)
            both = np.isfinite(a) & np.isfinite(b)
            delta = np.where(both, np.abs(a - b), 0.0)
            changed = nan_diff | (delta > 0).any(axis=0)
            node["columns"] |= {str(c) for c in cols}
            node["changed"] |= {str(c) for c, x in zip(cols, changed) if x}
            node["nan_diff"] |= {str(c) for c, x in zip(cols, nan_diff) if x}
            node["max_abs"] = max(node["max_abs"], float(delta.max()) if delta.size else 0.0)
            log.extra["ratio_unsafe"] = _ratio_unsafe_view(unsafe_seen)

    def calib_wrap(self: Any, config: Any, timeframe: str) -> Any:
        winsor = real_calib(self, config, timeframe)
        if winsor is None:
            return None
        winsor._ffprod_calibration = True
        log.count("winsor_core.calibration_winsorizers")

        def fast_core(frame: Any) -> Any:
            cols = winsor._select_columns(frame, winsor.winsor_config.get("apply_to", "all"))
            ctx = winsor._build_registry_transform_context()
            out = frame.copy()
            if cols:
                arr = np.ascontiguousarray(frame.loc[:, cols].to_numpy(dtype=np.float32))
                res = np.asarray(winsor._registry_fast_transform(arr, ctx), dtype=np.float32)
                out.loc[:, cols] = pd.DataFrame(res, index=frame.index, columns=cols)
            return out

        def wrapped(frame: Any) -> Any:
            site = "preflight" if getattr(tls, "preflight", 0) > 0 else "warmup_probe"
            if mode == "unify_numba":
                out = fast_core(frame)
                log.count("winsor_core.calibration_fast_calls")
            else:
                out = real_apply(winsor, frame)
                log.count("winsor_core.calibration_pandas_core_calls")
            log.count(f"winsor_core.calibration_calls.{site}")
            record_unsafe(site, frame, out)
            return out

        winsor._apply_winsorization = wrapped
        return winsor

    ff.FeatureFactory._calibration_winsorizer = calib_wrap  # type: ignore[assignment]
    ff.FeatureFactory.run_calibration_preflight = preflight_spy  # type: ignore[assignment]
    if mode == "unify_pandas":
        def fast_to_pandas(self: Any, group_array: Any, transform_context: Dict[str, object]) -> Any:
            enabled = [s for s in ("do_rank", "do_gaussian", "do_zscore") if bool(transform_context.get(s, False))]
            if enabled:
                raise ValueError(f"registry 快速路徑只做縮尾；設定開啟 {enabled}")
            values = np.ascontiguousarray(group_array, dtype=np.float32)
            log.count("winsor_core.public_routed_to_pandas")
            if not bool(transform_context.get("do_winsorize", True)):
                return values.copy()
            apply_to = self.winsor_config.get("apply_to", "all")
            if apply_to != "all":
                log.violate(f"winsor_core unify_pandas：apply_to＝{apply_to!r} ≠ all（位置欄名無法套選欄）")
            names = [f"\x00ffprod_pos{i}" for i in range(values.shape[1])]
            frame = pd.DataFrame(values, columns=names, copy=False)
            out = real_apply(self, frame)
            return np.ascontiguousarray(out.to_numpy(dtype=np.float32))

        FeaturePreprocessor._registry_fast_transform = fast_to_pandas  # type: ignore[assignment]
    log.bindings["winsor_core"] = {"mode": mode}


def _ratio_unsafe_view(seen: Mapping[str, Mapping[str, Any]]) -> Dict[str, Any]:
    return {s: {"columns_winsorized_in_calibration": len(n["columns"]), "changed_columns": len(n["changed"]),
                "nan_mask_diff_columns": len(n["nan_diff"]), "max_abs_diff": n["max_abs"], "calls": n["calls"],
                "input_columns_total": n["input_columns"], "columns": sorted(n["columns"]),
                "changed": sorted(n["changed"])}
            for s, n in seen.items()}


_INSTALLERS: Dict[str, Callable[[str], None]] = {
    "l2": _install_l2, "sigma": _install_sigma, "dstar": _install_dstar, "layer_dtype": _install_layer_dtype,
    "winsor_core": _install_winsor_core,
}


def install_probes(probes: Mapping[str, str], proof_dir: Path, role: str) -> _ProofLog:
    """於本行程安裝 `probes`（{探針名: 模式}）；重複呼叫為恆等。回傳本行程之自證紀錄。"""
    global _LOG
    if _LOG is not None:
        return _LOG
    import atexit

    _LOG = _ProofLog(proof_dir, role)
    atexit.register(_LOG.flush)
    for name, mode in probes.items():
        _INSTALLERS[name](str(mode))
        _LOG.installed[name] = str(mode)
    _LOG.flush()
    return _LOG


def install_from_env() -> None:
    """子行程（`sitecustomize`）入口：環境 `FFPROD_MEASURE_PROBES` 指向之規格檔安裝探針（role＝worker）。"""
    spec = json.loads(Path(os.environ[PROBES_ENV]).read_text(encoding="utf-8"))
    install_probes(spec["probes"], Path(spec["proof_dir"]), "worker")


SITECUSTOMIZE = '''"""FFPROD Task 2.1 量測探針之子行程安裝（`scripts/ffprod_measure.py` 產生；只在環境帶 FFPROD_MEASURE_PROBES 時作用）。"""
import os
import sys

if os.environ.get("FFPROD_MEASURE_PROBES") and os.environ.get("FFPROD_MEASURE_SCRIPT"):
    try:
        import importlib.util

        _spec = importlib.util.spec_from_file_location("ffprod_measure_site", os.environ["FFPROD_MEASURE_SCRIPT"])
        _mod = importlib.util.module_from_spec(_spec)
        sys.modules["ffprod_measure_site"] = _mod
        _spec.loader.exec_module(_mod)
        _mod.install_from_env()
    except BaseException as _exc:  # noqa: BLE001 — 安裝失敗寫入 proof 目錄，由主行程自證判失敗
        try:
            import json

            _d = json.loads(open(os.environ["FFPROD_MEASURE_PROBES"], encoding="utf-8").read())["proof_dir"]
            os.makedirs(_d, exist_ok=True)
            with open(os.path.join(_d, "install-error-%d.txt" % os.getpid()), "w", encoding="utf-8") as _f:
                _f.write("%s: %s" % (type(_exc).__name__, _exc))
        except BaseException:
            pass
'''


# ---------------------------------------------------------------------------------------------- 自證判定

def read_proofs(proof_dir: Path) -> Tuple[List[Dict[str, Any]], List[str]]:
    proofs = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(Path(proof_dir).glob("proof-*.json"))]
    errors = [p.read_text(encoding="utf-8") for p in sorted(Path(proof_dir).glob("install-error-*.txt"))]
    return proofs, errors


def _sum(proofs: Sequence[Mapping[str, Any]], key: str, role: Optional[str] = None) -> int:
    return sum(int((p.get("counters") or {}).get(key, 0)) for p in proofs if role is None or p.get("role") == role)


def verify_proof(probes: Mapping[str, str], proofs: Sequence[Mapping[str, Any]],
                 install_errors: Sequence[str] = ()) -> Dict[str, Any]:
    """依探針規格判定自證（純函式）。回 {passed, failures: [..], per_probe: {名: {...}}}；`observe` 只記錄不判。"""
    failures: List[str] = [f"子行程探針安裝失敗：{e}" for e in install_errors]
    per: Dict[str, Any] = {}
    violations = [v for p in proofs for v in p.get("violations") or []]
    vcount = sum(int(p.get("violation_count") or 0) for p in proofs)
    mains = [p for p in proofs if p.get("role") == "main"]
    if not mains:
        failures.append("無主行程自證紀錄")
    for name, mode in probes.items():
        info: Dict[str, Any] = {"mode": mode}
        if name == "l2":
            calls = _sum(proofs, "l2.observe_calls" if mode == "observe" else f"l2.{mode}_calls")
            uses = _sum(proofs, "l2.use.L5") + _sum(proofs, "l2.use.L6")
            info.update(calls=calls, uses=uses)
            if mode != "observe":
                if calls < 1:
                    failures.append(f"l2 {mode}：探針未被呼叫（格之 L2 臂非 Polars？）")
                if uses < 1:
                    failures.append(f"l2 {mode}：無 L5／L6 實收 L2 之比對")
                if mode == "pandas_category" and _sum(proofs, "l2.compute_all_polars") > 0:
                    failures.append("l2 pandas_category：仍呼叫 compute_all_polars")
        elif name == "sigma":
            calls = _sum(proofs, "sigma.calls")
            info.update(calls=calls, bindings=[p.get("bindings", {}).get("sigma") for p in proofs])
            if calls < 1:
                failures.append("sigma：_rolling_mean_std 探針未被呼叫（縮尾 method 非 sigma？）")
        elif name == "dstar":
            serial, parallel = _sum(proofs, "dstar.serial.calls"), _sum(proofs, "dstar.parallel.calls")
            effective = _sum(proofs, "dstar.serial.effective") + _sum(proofs, "dstar.parallel.effective")
            par_items = _sum(proofs, "dstar.map_parallel_items", "main")
            stats = [s for p in proofs for s in ((p.get("extra") or {}).get("dstar") or {}).values()]
            info.update(serial_calls=serial, parallel_calls=parallel, effective_calls=effective,
                        parallel_items_dispatched=par_items,
                        max_L=max([int(s.get("max_L") or 0) for s in stats] or [0]),
                        N_values=sorted({int(n) for s in stats for n in s.get("N_values") or []}),
                        samples=[s for p in proofs for k, v in (p.get("samples") or {}).items()
                                 if k.startswith("dstar.") for s in v][:SAMPLE_CAP])
            if serial + parallel < 1:
                failures.append("dstar：ADF 檢定未被呼叫（fracdiff／ADF 關？）")
            elif effective < 1:
                failures.append(DSTAR_NO_EFFECTIVE)
            if par_items > 0 and parallel < 1:
                failures.append(f"dstar：平行派工 {par_items} 項而 worker 無探針紀錄")
        elif name == "layer_dtype":
            calls, forced = _sum(proofs, "layer_dtype.calls"), _sum(proofs, "layer_dtype.forced")
            info.update(calls=calls, forced=forced,
                        layer_dtypes=next((p.get("extra", {}).get("layer_dtypes") for p in mains), None))
            if forced < 1:
                failures.append("layer_dtype：無層間轉型被改為保留（非單週期？）")
        elif name == "winsor_core":
            preflight = _sum(proofs, "winsor_core.preflight_calls")
            in_preflight = _sum(proofs, "winsor_core.calibration_calls.preflight")
            info.update(preflight_calls=preflight, calibration_winsor_calls_in_preflight=in_preflight,
                        calibration_winsor_calls_warmup_probe=_sum(proofs, "winsor_core.calibration_calls.warmup_probe"),
                        ratio_unsafe={s: {k: v for k, v in n.items() if k not in ("columns", "changed")}
                                      for s, n in (ratio_unsafe_selection(proofs) or {}).items()})
            if mode == "observe":
                pass
            elif preflight < 1 or in_preflight < 1:
                failures.append(f"winsor_core {mode}：校準前置未執行或其內無校準縮尾（前置 {preflight} 次、縮尾 {in_preflight} 次；"
                                "平穩化關？）")
            if mode == "observe":
                pass
            elif mode == "unify_numba":
                fast = _sum(proofs, "winsor_core.calibration_fast_calls")
                info.update(calibration_fast_calls=fast,
                            calibration_pandas_calls=_sum(proofs, "winsor_core.calibration_pandas_calls"))
                if fast < 1:
                    failures.append("winsor_core unify_numba：校準域快速核心未被呼叫")
            else:
                routed = _sum(proofs, "winsor_core.public_routed_to_pandas")
                info.update(public_routed_to_pandas=routed,
                            transform_array_fast_calls=_sum(proofs, "winsor_core.transform_array_fast_calls"))
                if routed < 1:
                    failures.append("winsor_core unify_pandas：公開快速核心未被改道（無快速臂群組？）")
        else:
            failures.append(f"未知探針 {name}")
        per[name] = info
    if vcount:
        failures.append(f"違規 {vcount} 次：{violations[:5]}")
    return {"passed": not failures, "failures": failures, "per_probe": per, "violation_count": vcount,
            "processes": len(proofs), "overhead_seconds": sum(float(p.get("overhead_seconds") or 0) for p in proofs)}


def ratio_unsafe_selection(proofs: Sequence[Mapping[str, Any]]) -> Optional[Dict[str, Any]]:
    """主行程之校準域 ratio-unsafe 欄縮尾紀錄（`_install_winsor_core.record_unsafe`；依呼叫點：preflight／warmup_probe）。"""
    for p in proofs:
        if p.get("role") == "main" and (p.get("extra") or {}).get("ratio_unsafe"):
            return p["extra"]["ratio_unsafe"]
    return None


def l2_observe_summary(proofs: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    """改前三取值點兩兩差（邊界③；主行程之 `extra.l2`）：逐 (實例, 週期, 域) 之比較與 NUMVIEW 原生值差合計。"""
    for p in proofs:
        if p.get("role") == "main" and "l2" in (p.get("extra") or {}):
            return p["extra"]["l2"]
    return {"checks": [], "native": {}, "note": "主行程無 L2 觀測紀錄（格之 L2 臂非 Polars 或未呼叫）"}


# ============================================================================================== 生成子行程

def _peak_sampler(stop: threading.Event, out: Dict[str, int], interval: float = 0.5) -> None:
    import psutil

    proc = psutil.Process()
    while not stop.is_set():
        try:
            rss = proc.memory_info().rss
            kids = 0
            for child in proc.children(recursive=True):
                try:
                    kids += child.memory_info().rss
                except psutil.Error:
                    pass
            out["self"] = max(out.get("self", 0), rss)
            out["tree"] = max(out.get("tree", 0), rss + kids)
        except psutil.Error:
            pass
        stop.wait(interval)


#: CPU 進度心跳（卡死監看之 log 靜默條件只認 log 增長）：每 HEARTBEAT_SECONDS 秒，行程樹 CPU 秒數之前進 ≥
#: HEARTBEAT_MIN_CPU_FRACTION × 經過秒數（平均至少四分之一核在算）才寫一行——長時間無 log 之計算（全特徵平穩化校準、
#: 全欄 IC）不被誤殺；真卡死（等鎖／等 I/O，只剩取樣執行緒約 1% 核）不寫、仍於 log 靜默門檻被終止
HEARTBEAT_SECONDS = 60.0
HEARTBEAT_MIN_CPU_FRACTION = 0.25


def tree_cpu_seconds() -> float:
    """本行程＋存活子孫＋已回收子行程之 CPU 秒數（user＋system）。子孫不可列舉（沙箱／權限，psutil 列 pid 失敗）⇒ 保守降級為
    本行程＋已回收子行程（標準庫 `resource`，不依 psutil）——平行 worker 之 CPU 不計入，不會多算。"""
    own = resource.getrusage(resource.RUSAGE_SELF)
    reaped = resource.getrusage(resource.RUSAGE_CHILDREN)
    total = own.ru_utime + own.ru_stime + reaped.ru_utime + reaped.ru_stime
    try:
        import psutil

        children = psutil.Process().children(recursive=True)
    except Exception:  # noqa: BLE001 — psutil.Error／PermissionError（macOS sysctl KERN_PROC_ALL）
        return total
    for child in children:
        try:
            ct = child.cpu_times()
            total += ct.user + ct.system
        except Exception:  # noqa: BLE001 — 子行程於列舉後結束或不可讀
            pass
    return total


def heartbeat_line(prev_cpu: float, cpu: float, elapsed: float) -> Optional[str]:
    """CPU 前進 ≥ HEARTBEAT_MIN_CPU_FRACTION × elapsed ⇒ 心跳行，否則 None（不寫）。"""
    delta = cpu - prev_cpu
    if elapsed <= 0 or delta < HEARTBEAT_MIN_CPU_FRACTION * elapsed:
        return None
    return f"[ffprod-heartbeat] 行程樹 CPU {cpu:.0f} 秒（近 {elapsed:.0f} 秒 +{delta:.0f} 秒）"


@contextlib.contextmanager
def cpu_heartbeat(interval: float = HEARTBEAT_SECONDS,
                  read_cpu: Callable[[], float] = tree_cpu_seconds) -> Iterator[None]:
    stop = threading.Event()

    def beat() -> None:
        prev: Optional[float] = None
        last = time.monotonic()
        while True:
            try:
                cpu: Optional[float] = read_cpu()
            except Exception:  # noqa: BLE001 — 讀不到 CPU ⇒ 本窗不寫心跳（保守：交由 log 靜默條件判），執行緒不退出
                cpu = None
            now = time.monotonic()
            if cpu is not None and prev is not None:
                line = heartbeat_line(prev, cpu, now - last)
                if line is not None:
                    print(line, file=sys.stderr, flush=True)
            prev, last = cpu, now  # 逐窗判定（不跨窗累積），閒置之微量 CPU 不會攢成心跳
            if stop.wait(interval):
                return

    thread = threading.Thread(target=beat, daemon=True)
    thread.start()
    try:
        yield
    finally:
        stop.set()


def _ru_maxrss_bytes(who: int) -> int:
    value = int(resource.getrusage(who).ru_maxrss)
    return value if sys.platform == "darwin" else value * 1024


def run_dir_of(work: Path, symbol: str, timeframe: str) -> Path:
    """隔離生成之 run 目錄（`<features 根>/<symbol>/<tf>/<config_hash>/feature_manifest.json` 恰一份）。"""
    hits = [p.parent for p in Path(work).rglob("feature_manifest.json")
            if p.parent.parent.name == timeframe and p.parent.parent.parent.name == symbol]
    if len(hits) != 1:
        raise RuntimeError(f"{work}：run 目錄須恰一份，實得 {[str(h) for h in hits]}")
    return hits[0]


def output_bytes(run_dir: Path) -> int:
    """run 目錄下全部一般檔之位元組合計。"""
    return sum(p.stat().st_size for p in Path(run_dir).rglob("*") if p.is_file())


def _gen_child(spec_path: Path) -> int:
    """生成子行程：安裝探針（本行程＋經 sitecustomize 之孫行程）、`_generate_in_process` 生成一格、取峰值記憶體與自證。"""
    spec = json.loads(Path(spec_path).read_text(encoding="utf-8"))
    proof_dir = Path(spec["proof_dir"])
    probes = dict(spec["probes"])
    result: Dict[str, Any]
    peak: Dict[str, int] = {}
    stop = threading.Event()
    sampler = threading.Thread(target=_peak_sampler, args=(stop, peak), daemon=True)
    try:
        if probes:
            install_probes(probes, proof_dir, "main")
            os.environ[PROBES_ENV] = str(spec_path)
            os.environ[SCRIPT_ENV] = str(Path(__file__).resolve())
        from momentum.FeatureEngineering.feature_factory import FeatureFactory

        gen_seconds: Dict[str, float] = {}
        real_generate = FeatureFactory.generate_features

        def timed_generate(self: Any, *args: Any, **kwargs: Any) -> Any:
            started = time.perf_counter()
            try:
                return real_generate(self, *args, **kwargs)
            finally:
                gen_seconds["generate_features"] = time.perf_counter() - started

        FeatureFactory.generate_features = timed_generate  # type: ignore[assignment]
        sampler.start()
        try:
            with cpu_heartbeat():
                gen = _fb()._generate_in_process(spec["cell"], Path(spec["work"]))
        finally:
            stop.set()
            FeatureFactory.generate_features = real_generate  # type: ignore[assignment]
        _shutdown_loky()
        result = {"status": "ok", **gen, "generation_seconds": gen_seconds.get("generate_features")}
    except BaseException as exc:  # noqa: BLE001 — 失敗型別決定 blocked（硬體）或 failed
        stop.set()
        result = {"status": "blocked" if _fb()._estimator()._is_memory_guard(exc) else "failed",
                  "error": f"{type(exc).__name__}: {exc}"[:2000]}
    result["peak_rss_bytes"] = peak.get("self") or _ru_maxrss_bytes(resource.RUSAGE_SELF)
    result["peak_rss_tree_bytes"] = peak.get("tree")
    result["ru_maxrss_self_bytes"] = _ru_maxrss_bytes(resource.RUSAGE_SELF)
    result["ru_maxrss_children_bytes"] = _ru_maxrss_bytes(resource.RUSAGE_CHILDREN)
    if probes and _LOG is not None:
        if "l2" in probes:
            _LOG.extra["l2"] = {"checks": _L2.checks,
                                "native": {k: _l2_native_merge(v) for k, v in _L2.native.items()},
                                "compute_all_polars_calls": _L2.compute_all_polars_calls,
                                "compute_category_calls": _L2.compute_category_calls}
        _LOG.flush()
    _fb()._write_atomic(Path(spec["result_path"]), result)
    return 0 if result["status"] in ("ok", "blocked") else 3


def _l2_native_merge(stats: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    out = {"categories": len(stats), "common_cols": 0, "nan_mask_diff": 0, "f64diff": 0, "f32diff": 0,
           "max_abs": 0.0, "max_rel": 0.0, "only_category": [], "row_mismatch": []}
    for s in stats:
        for k in ("common_cols", "nan_mask_diff", "f64diff", "f32diff"):
            out[k] += int(s.get(k) or 0)
        out["max_abs"] = max(out["max_abs"], float(s.get("max_abs") or 0.0))
        out["max_rel"] = max(out["max_rel"], float(s.get("max_rel") or 0.0))
        out["only_category"] = sorted(set(out["only_category"]) | set(s.get("only_category") or []))[:50]
        if s.get("row_mismatch"):
            out["row_mismatch"].append(s["row_mismatch"])
    return out


def _shutdown_loky() -> None:
    """結束可重用之 loky worker（使其 atexit 寫出最終自證紀錄）。"""
    try:
        from joblib.externals.loky import get_reusable_executor

        get_reusable_executor().shutdown(wait=True)
    except Exception:  # noqa: BLE001 — 無 loky 或已關：無事可做
        pass


def generate_watched(cell: Mapping[str, Any], probes: Mapping[str, str], item_dir: Path,
                     expected_seconds: Optional[float]) -> Dict[str, Any]:
    """主行程：以子行程（NUMVIEW 卡住監看）生成一格；回傳子行程結果＋`proof`（自證判定）與 run 目錄。卡住 ⇒ RuntimeError。"""
    fb = _fb()
    wd = fb._watchdog()
    item_dir = Path(item_dir)
    work = item_dir / "work"
    proof_dir = item_dir / "proof"
    site_dir = item_dir / "_probe_site"
    import shutil

    for path in (proof_dir, work):  # 續跑重生同項：舊自證紀錄與舊 run 不得混入
        if path.exists():
            shutil.rmtree(path)
    site_dir.mkdir(parents=True, exist_ok=True)
    (site_dir / "sitecustomize.py").write_text(SITECUSTOMIZE, encoding="utf-8")
    result_path = item_dir / "result.json"
    result_path.unlink(missing_ok=True)
    spec_path = item_dir / "spec.json"
    fb._write_atomic(spec_path, {"cell": dict(cell), "work": str(work), "result_path": str(result_path),
                                 "probes": dict(probes), "proof_dir": str(proof_dir)})
    env = dict(os.environ)
    env.pop(PROBES_ENV, None)
    env["PYTHONPATH"] = os.pathsep.join([str(site_dir), str(REPO)] + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else []))
    print(f"[ffprod-measure] {cell['id']} {dict(probes)}：子行程開始（預期 {expected_seconds} 秒）", flush=True)
    watched = wd.run_watched([sys.executable, str(Path(__file__).resolve()), "--gen-child", str(spec_path)],
                             log_path=item_dir / "child.log", config=wd.load_config(fb._criteria()),
                             expected_seconds=expected_seconds, cwd=str(REPO), env=env)
    if watched.status == wd.STALLED and watched.cause == wd.CAUSE_MEMORY:  # 記憶體證據 ⇒ 硬體受阻（照記、不重跑）
        _fb()._write_atomic(item_dir / "stall_diagnosis.json", watched.diagnosis)
        return {"status": "blocked", "error": f"卡死監看（記憶體）：{watched.reason}", "run_dir": None,
                "watch": {"status": watched.status, "cause": watched.cause, "reason": watched.reason,
                          "diagnosis": str(item_dir / "stall_diagnosis.json")}}
    if watched.status == wd.STALLED:  # 程式卡住 ⇒ 留現場、停止整跑（不自動重跑；依堆疊查因修好再跑）
        raise_hang(f"{cell['id']} 生成", watched, item_dir)
    if not result_path.is_file():
        raise RuntimeError(f"{cell['id']}：子行程 rc={watched.returncode} 未寫結果（見 {item_dir / 'child.log'}）")
    result = json.loads(result_path.read_text(encoding="utf-8"))
    result["watch"] = {"status": watched.status, "wall_seconds": watched.wall_seconds,
                       "swap_growth_max_mb": watched.swap_growth_max_mb, "log": str(item_dir / "child.log"),
                       "over_expected": bool(getattr(watched, "over_expected", False))}  # CODEX-R9-P1-03
    proofs, errors = read_proofs(proof_dir)
    result["proof"] = verify_proof(probes, proofs, errors) if probes else {"passed": True, "failures": [],
                                                                            "per_probe": {}, "overhead_seconds": 0.0}
    if probes.get("l2") == "observe":
        result["l2_three_points"] = l2_observe_summary(proofs)
    if "winsor_core" in probes:
        result["ratio_unsafe_selection"] = ratio_unsafe_selection(proofs)
    if result["status"] == "ok":
        result["run_dir"] = str(run_dir_of(work, str(cell["symbol"]), str(cell["timeframes"][0])))
        result["output_bytes"] = output_bytes(Path(result["run_dir"]))
    print(f"[ffprod-measure] {cell['id']}：{result['status']}（{result.get('generation_seconds')} 秒；自證 "
          f"{result['proof'].get('passed')}）", flush=True)
    return result


# ============================================================================================== 值差

def _group_index(run_dir: Path) -> Dict[str, Tuple[Path, str]]:
    """欄名 → (群組檔, 該欄 parquet 型別字面)；只讀 manifest 宣告之 raw 群組檔之 schema。"""
    import pyarrow.parquet as pq

    from tests.feature_engineering import preprov_helpers as ph

    out: Dict[str, Tuple[Path, str]] = {}
    for path in ph.declared_group_files(Path(run_dir), "raw"):
        schema = pq.read_schema(str(path))
        for name in schema.names:
            if name not in ph.NON_FEATURE_COLUMNS:
                out[str(name)] = (Path(path), str(schema.field(name).type))
    return out


def read_columns(run_dir: Path, names: Sequence[str], index: Optional[Mapping[str, Tuple[Path, str]]] = None
                 ) -> Dict[str, Tuple[Any, str]]:
    """讀 run 之 raw 指定欄（原生 dtype 陣列, parquet 型別字面）；依群組檔分批讀。"""
    import numpy as np
    import pyarrow.parquet as pq

    index = index if index is not None else _group_index(run_dir)
    by_file: Dict[Path, List[str]] = {}
    for name in names:
        if name in index:
            by_file.setdefault(index[name][0], []).append(name)
    out: Dict[str, Tuple[Any, str]] = {}
    for path, cols in by_file.items():
        table = pq.read_table(str(path), columns=cols)
        for name in cols:
            out[name] = (np.asarray(table.column(name).to_numpy(zero_copy_only=False)), index[name][1])
    return out


def column_fingerprint(native: Any, dtype_literal: str) -> Dict[str, str]:
    """單欄 §G 指紋（同 `numview_helpers.fingerprints` 逐欄定義：dtype＝parquet 型別字面、nan／values＝float32 遮罩與
    NaN→0 位元組、values_native＝原生位元組）。"""
    import numpy as np

    from tests.feature_engineering import numview_helpers as nh

    entry = {"dtype": dtype_literal}
    entry.update(nh._float32_entry(np.asarray(native)))
    entry["values_native"] = nh.values_native_sha256(np.asarray(native))
    return entry


def _differing_keys(before: Mapping[str, Any], after: Mapping[str, Any]) -> List[str]:
    from tests.feature_engineering import numview_helpers as nh

    keys = sorted(set(before) | set(after))
    return [k for k in keys if k not in before or k not in after
            or any(before[k].get(b) != after[k].get(b) for b in nh.BITWISE_COLUMN_KEYS)]


def value_diff(before_fp: Mapping[str, Any], after_fp: Mapping[str, Any],
               reader: Callable[[str, Sequence[str]], Dict[str, Tuple[Any, str]]],
               columns_of_groups: Callable[[str, Sequence[str]], List[str]]) -> Dict[str, Any]:
    """改前／改後值差（§G 值指紋導出）：差異鍵（逐欄格＝欄；群組粒度格＝群組，再由群組內欄逐欄導出指紋）→ 逐欄改前／改後
    指紋、改值欄集合（BITWISE 鍵任一不等或只在一側）、最大絕對差（兩側皆有限之格）、NaN 遮罩差欄數、欄集合／欄序是否改變。
    `reader(side, 欄)`→{欄: (原生陣列, 型別字面)}；`columns_of_groups(side, 群組鍵)`→該側群組內欄名。"""
    import numpy as np

    grouped = before_fp.get("granularity") == "group" or after_fp.get("granularity") == "group"
    diff_keys = _differing_keys(before_fp["columns"], after_fp["columns"])
    if grouped:
        names = sorted(set(columns_of_groups("before", diff_keys)) | set(columns_of_groups("after", diff_keys)))
    else:
        names = list(diff_keys)
    b_vals, a_vals = reader("before", names), reader("after", names)
    fps_before = {n: column_fingerprint(*b_vals[n]) for n in names if n in b_vals}
    fps_after = {n: column_fingerprint(*a_vals[n]) for n in names if n in a_vals}
    changed = sorted(_differing_keys(fps_before, fps_after))
    max_abs = 0.0
    nan_diff = 0
    for name in changed:
        if name not in b_vals or name not in a_vals:
            continue
        b = np.asarray(b_vals[name][0], dtype=np.float64)
        a = np.asarray(a_vals[name][0], dtype=np.float64)
        if b.shape != a.shape:
            continue
        if (np.isnan(b) != np.isnan(a)).any():
            nan_diff += 1
        both = np.isfinite(b) & np.isfinite(a)
        if both.any():
            max_abs = max(max_abs, float(np.max(np.abs(a[both] - b[both]))))
    return {"summary": {"changed_columns": len(changed), "max_abs_diff": max_abs, "nan_mask_diff_columns": nan_diff,
                        "only_before": sorted(set(fps_before) - set(fps_after))[:50],
                        "only_after": sorted(set(fps_after) - set(fps_before))[:50],
                        "column_set_changed": before_fp.get("column_set_sha256") != after_fp.get("column_set_sha256"),
                        "column_order_changed": before_fp.get("column_order_sha256") != after_fp.get("column_order_sha256"),
                        "differing_fingerprint_keys": len(diff_keys), "granularity": "group" if grouped else "column"},
            "changed": changed,
            "fingerprints": {"before": {n: fps_before[n] for n in changed if n in fps_before},
                             "after": {n: fps_after[n] for n in changed if n in fps_after}}}


def run_value_diff(before_run: Path, after_run: Path, before_fp: Mapping[str, Any],
                   after_fp: Mapping[str, Any]) -> Dict[str, Any]:
    """兩 run 目錄之值差（`value_diff` 之落盤讀取版）。"""
    idx = {"before": _group_index(before_run), "after": _group_index(after_run)}
    runs = {"before": Path(before_run), "after": Path(after_run)}

    def reader(side: str, names: Sequence[str]) -> Dict[str, Tuple[Any, str]]:
        return read_columns(runs[side], names, idx[side])

    def groups(side: str, keys: Sequence[str]) -> List[str]:
        wanted = {str((runs[side] / k).resolve()) for k in keys}
        return [n for n, (path, _t) in idx[side].items() if str(Path(path).resolve()) in wanted]

    return value_diff(before_fp, after_fp, reader, groups)


# ============================================================================================== IC

def _ic_child(spec_path: Path) -> int:
    """IC 子行程：以 IC 頁預設請求（`ICAnalyzeRequest` 欄預設＝前端 `icAnalysisStore.ts` defaultConfig 之門檻／週期／冗餘
    與後端 `ic_config_schema` 預設同值）經 `ICAnalysisService._build_config_override` 與 `create_ic_analyzer` 組 analyzer，
    `_materialize_features_for_ic` 物化（暫存 registry 登記該 run）後 `analyze`（同服務之縱向路徑）；寫逐欄摘要列。"""
    spec = json.loads(Path(spec_path).read_text(encoding="utf-8"))
    started = time.perf_counter()
    try:
        with cpu_heartbeat():
            out = ic_in_process(Path(spec["run_dir"]), spec["symbol"], spec["timeframe"], spec.get("include"),
                                bool(spec.get("winsor_off")), Path(spec["work"]))
        out["status"] = "ok"
    except BaseException as exc:  # noqa: BLE001 — 記憶體守護／MemoryError ⇒ blocked（硬體），其餘 failed
        out = {"status": "blocked" if _fb()._estimator()._is_memory_guard(exc) else "failed",
               "error": f"{type(exc).__name__}: {exc}"[:2000]}
    out["seconds"] = time.perf_counter() - started
    out["peak_rss_bytes"] = _ru_maxrss_bytes(resource.RUSAGE_SELF)
    _fb()._write_atomic(Path(spec["out"]), out)
    return 0 if out["status"] in ("ok", "blocked") else 3


def ic_request(symbol: str, timeframe: str, config_hash: str, include: Optional[Sequence[str]]) -> Any:
    from api.models.ic_models import FeatureFilterConfig, ICAnalyzeRequest

    return ICAnalyzeRequest(symbol=symbol, timeframe=timeframe, config_hash=config_hash,
                            feature_filter=FeatureFilterConfig(include_features=list(include)) if include else None)


def ic_override(request: Any, winsor_off: bool) -> Optional[Dict[str, Any]]:
    """IC 頁預設請求之 config_override（服務之 `_build_config_override`，不另寫參數）深合併 `IC_MEASURE_OVERRIDE`
    （衰減分析關）；`winsor_off` ⇒ 再深合併 `IC_WINSOR_OFF_OVERRIDE`。"""
    from api.services.ic_analysis_service import ICAnalysisService

    svc = ICAnalysisService.__new__(ICAnalysisService)
    override = svc._deep_merge(svc._build_config_override(request) or {}, IC_MEASURE_OVERRIDE)
    if winsor_off:
        override = svc._deep_merge(override or {}, IC_WINSOR_OFF_OVERRIDE)
    return override


def ic_in_process(run_dir: Path, symbol: str, timeframe: str, include: Optional[Sequence[str]], winsor_off: bool,
                  work: Path) -> Dict[str, Any]:
    from api.services.ic_analysis_service import FEATURE_KLINE_CACHE_DIR, ICAnalysisService
    from momentum.factories import create_ic_analyzer, create_kline_storage_manager
    from momentum.FeatureEngineering.feature_library import FeatureLibrary
    from momentum.FeatureEngineering.feature_reader import FeatureReader
    from momentum.FeatureEngineering.feature_registry import FeatureRegistry
    from momentum.FeatureEngineering.feature_storage import FeatureStorage
    from tests.feature_engineering.ffname_helpers import register_canonical_run

    work = Path(work)
    work.mkdir(parents=True, exist_ok=True)
    root = Path(run_dir).parents[2]
    registry = work / "registry.json"
    register_canonical_run(Path(run_dir) / "feature_manifest.json", registry)
    svc = ICAnalysisService.__new__(ICAnalysisService)
    svc._feature_library = FeatureLibrary(FeatureRegistry(registry), FeatureStorage(str(root)),
                                          feature_reader=FeatureReader(str(root)))
    request = ic_request(symbol, timeframe, Path(run_dir).name, include)
    override = ic_override(request, winsor_off)
    analyzer = create_ic_analyzer(override)
    features_path, meta_path = svc._materialize_features_for_ic(symbol, timeframe, Path(run_dir).name)
    def progress(payload: Dict[str, Any]) -> None:
        # 同服務之進度回呼（IC 頁以之推進度）；印出使卡住監看之 log 心跳反映實際進度
        keys = ("stage_name", "stage", "progress", "module_name", "current_step", "message")
        print("[ffprod-ic-progress] " + json.dumps({k: _jsonable(payload.get(k)) for k in keys if k in payload},
                                                   ensure_ascii=False), flush=True)

    report = analyzer.analyze(features_path=features_path, labels_path="", meta_path=meta_path,
                              config_override=override, progress_callback=progress,
                              kline_reader=create_kline_storage_manager(cache_dir=FEATURE_KLINE_CACHE_DIR))
    rows = {str(r.get("feature_name")): {k: _jsonable(v) for k, v in r.items()} for r in report.get("summary_table") or []}
    decay_rows = assert_decay_off(report, override)
    filter_log = report.get("filter_log") or {}
    stage1 = filter_log.get("stage1_preprocessing") or {}
    stage5 = filter_log.get("stage5_thresholds") or {}
    base_yaml = {p: (_sha256_file(Path(p)) if Path(p).is_file() else None)
                 for p in ("config/ic_config.yaml", "config/user_ic_config.yaml")}
    return {"rows": rows, "override": override, "config_sha256": _sha256_json(override), "ic_config_files": base_yaml,
            "stage1_winsorized_count": _count(stage1.get("winsorized_features")),
            "stage5": {k: _jsonable(v) for k, v in stage5.items() if not isinstance(v, (list, dict))},
            # 報告 stage5 只帶通過數（`output_features.count`，ic_filter_orchestrator.py:2056-2067），不帶欄名清單
            "passed_count_from_report": _count(stage5.get("output_features")),
            "ic_settings": IC_MEASURE_SETTINGS, "decay_rows": decay_rows, "report_keys": sorted(report)}


def assert_decay_off(report: Mapping[str, Any], override: Any) -> int:
    """自證 `IC_MEASURE_OVERRIDE` 確實關衰減，三條皆須成立否則 RuntimeError：送出之 override 之
    `report.include_decay_analysis` 為 False；報告帶 `ic_decay` 鍵（`ic_reporter.py` report 組裝固定輸出）且為 mapping；
    該 mapping 為空。回 0。摘要表 half_life 不作判據：衰減開時亦可為 None（IC 隨 horizon 無衰減形狀）。"""
    flag = ((override or {}).get("report") or {}).get("include_decay_analysis") if isinstance(override, Mapping) else None
    if flag is not False:
        raise RuntimeError(f"IC 衰減分析未關：override report.include_decay_analysis={flag!r}")
    if "ic_decay" not in report or not isinstance(report["ic_decay"], Mapping):
        raise RuntimeError(f"IC 報告缺 ic_decay mapping（{type(report.get('ic_decay')).__name__}），無從自證衰減已關")
    if report["ic_decay"]:
        raise RuntimeError(f"IC 衰減分析未關：報告 ic_decay 有 {len(report['ic_decay'])} 個特徵（override={override}）")
    return 0


def _count(value: Any) -> Optional[int]:
    if isinstance(value, (list, tuple, set)):
        return len(value)
    if isinstance(value, Mapping) and "count" in value:
        return int(value["count"])
    if isinstance(value, int):
        return value
    return None


def _jsonable(value: Any) -> Any:
    try:
        import numpy as np

        if isinstance(value, np.generic):
            value = value.item()
    except ImportError:
        pass
    if isinstance(value, (str, int, float, bool)) or value is None:  # NaN 原樣（json 之 NaN 字面可往返）
        return value
    return str(value)


def ic_watched(run_dir: Path, symbol: str, timeframe: str, include: Optional[Sequence[str]], winsor_off: bool,
               item_dir: Path) -> Dict[str, Any]:
    """主行程：IC 子行程（卡住監看）；cwd＝`item_dir`（服務之相對快取目錄落於此，K 線目錄以連結指向 repo 之資料）。"""
    fb = _fb()
    wd = fb._watchdog()
    item_dir = Path(item_dir)
    item_dir.mkdir(parents=True, exist_ok=True)
    link_root = item_dir / "data_cache"
    link_root.mkdir(exist_ok=True)
    for name in ("feature_klines", "feature_klines_longhist"):
        link = link_root / name
        if not link.exists() and (REPO / "data_cache" / name).exists():
            link.symlink_to((REPO / "data_cache" / name).resolve())
    if not (item_dir / "config").exists():  # IC 設定基底 `config/ic_config.yaml`（`load_ic_config` 以 cwd 相對路徑讀）
        (item_dir / "config").symlink_to((REPO / "config").resolve())
    out_path = item_dir / "ic_result.json"
    out_path.unlink(missing_ok=True)
    spec_path = item_dir / "ic_spec.json"
    fb._write_atomic(spec_path, {"run_dir": str(run_dir), "symbol": symbol, "timeframe": timeframe,
                                 "include": list(include) if include else None, "winsor_off": winsor_off,
                                 "work": str(item_dir / "ic_work"), "out": str(out_path)})
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join([str(REPO)] + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else []))
    watched = wd.run_watched([sys.executable, str(Path(__file__).resolve()), "--ic-child", str(spec_path)],
                             log_path=item_dir / "ic_child.log", config=wd.load_config(fb._criteria()),
                             cwd=str(item_dir), env=env)
    log = str(item_dir / "ic_child.log")
    if watched.status == wd.STALLED and watched.cause == wd.CAUSE_MEMORY:  # SPEC v12 補③：記憶體證據 ⇒ hardware
        _fb()._write_atomic(Path(item_dir) / "stall_diagnosis.json", watched.diagnosis)
        return {"status": "blocked", "blocked_by": BLOCKED_BY_HARDWARE, "reason": f"卡死監看（記憶體）：{watched.reason}",
                "wall_seconds": watched.wall_seconds, "swap_growth_max_mb": watched.swap_growth_max_mb,
                "swap_growth_threshold_mb": watched.swap_growth_threshold_mb, "log": log,
                "diagnosis": str(Path(item_dir) / "stall_diagnosis.json")}
    if watched.status == wd.STALLED:  # 程式卡住 ⇒ 留現場、停止整跑（不自動重跑）
        raise_hang(f"IC {run_dir}", watched, Path(item_dir))
    if not out_path.is_file():  # 子行程被訊號終止（例 OOM kill）而未寫結果
        if watched.returncode is not None and watched.returncode < 0:
            return {"status": "blocked", "blocked_by": BLOCKED_BY_HARDWARE,
                    "reason": f"子行程被訊號 {-watched.returncode} 終止（未寫結果）", "wall_seconds": watched.wall_seconds,
                    "swap_growth_max_mb": watched.swap_growth_max_mb, "log": log}
        raise RuntimeError(f"IC {run_dir}：子行程 rc={watched.returncode} 未寫結果（見 {log}）")
    result = json.loads(out_path.read_text(encoding="utf-8"))
    if result.get("status") == "blocked":
        return {**result, "blocked_by": BLOCKED_BY_HARDWARE, "reason": result.get("error"), "log": log}
    if result.get("status") != "ok":
        raise RuntimeError(f"IC {run_dir}：{result.get('error')}（見 {log}）")
    return result


def _selection_tools(override: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    from momentum.Analysis.statistical_validator import apply_fdr
    from momentum.factories import create_ic_analyzer

    analyzer = create_ic_analyzer(dict(override) if override else None)
    config = analyzer._apply_tier_config(analyzer._apply_config_override(dict(override) if override else None))
    alpha, _source, _mode = analyzer._resolve_alpha_policy(config, {})
    return {"analyzer": analyzer, "config": config, "alpha": float(alpha), "apply_fdr": apply_fdr,
            "fdr_enabled": analyzer._resolve_fdr_enabled(config), "fdr_method": analyzer._resolve_fdr_method(config)}


def select_features(rows: Mapping[str, Mapping[str, Any]], tools: Mapping[str, Any]) -> List[str]:
    """stage5 選欄之重排：全 universe 之 p 值重算 FDR q（`apply_fdr`）後以 `_apply_thresholds`（產品碼）判定。"""
    p_values = {f: (float(r["p_value"]) if r.get("p_value") is not None else float("nan")) for f, r in rows.items()}
    q_values, _n = tools["apply_fdr"](p_values, tools["alpha"], method=tools["fdr_method"])
    table = []
    for feature, row in rows.items():
        item = dict(row)
        item["p_value_adj"] = q_values.get(feature, float("nan"))
        table.append(item)
    passed, _log_ = tools["analyzer"]._apply_thresholds(table, tools["config"].thresholds, tools["alpha"],
                                                        fdr_enabled=tools["fdr_enabled"], icir_gate=True,
                                                        binary_mode=False)
    return sorted(str(f) for f in passed)


def _sign(value: Any) -> Optional[int]:
    if value is None:
        return None
    v = float(value)
    if v != v:
        return None
    return (v > 0) - (v < 0)


def ic_effect(base_rows: Mapping[str, Mapping[str, Any]], option_rows: Mapping[str, Mapping[str, Any]],
              changed: Sequence[str], tools: Mapping[str, Any]) -> Dict[str, Any]:
    """IC 正負號翻轉（`sign_flips`）＋選欄進出（`selection_effect`）。"""
    return {**sign_flips(base_rows, option_rows, changed), **selection_effect(base_rows, option_rows, changed, tools)}


def sign_flips(base_rows: Mapping[str, Mapping[str, Any]], option_rows: Mapping[str, Mapping[str, Any]],
               columns: Sequence[str]) -> Dict[str, Any]:
    """改值欄之 ic_mean 正負號翻轉（兩側皆有限且非零才計；有限↔NaN 另計）。"""
    flips = []
    nan_changes = 0
    for name in columns:
        sb = _sign((base_rows.get(name) or {}).get("ic_mean"))
        sa = _sign((option_rows.get(name) or {}).get("ic_mean"))
        if (sb is None) != (sa is None):
            nan_changes += 1
        elif sb is not None and sa is not None and sb != 0 and sa != 0 and sb != sa:
            flips.append(name)
    return {"sign_flips": len(flips), "sign_flip_examples": sorted(flips)[:20], "ic_nan_status_changes": nan_changes,
            "sign_flip_columns": len(columns)}


def selection_effect(base_rows: Mapping[str, Mapping[str, Any]], option_rows: Mapping[str, Mapping[str, Any]],
                     changed: Sequence[str], tools: Mapping[str, Any]) -> Dict[str, Any]:
    """第 5 階段選欄進出（SPEC v9 補③）：改前全欄列中替換改值欄之列後重算 FDR 與門檻（改值欄於選項 run 被 stage1 剔除者自
    universe 移除）。第 6 階段冗餘篩選須特徵間相關，非替換可得，不導出。"""
    merged = {f: r for f, r in base_rows.items() if f not in set(changed)}
    merged.update({f: r for f, r in option_rows.items() if f in set(changed)})
    before = set(select_features(base_rows, tools))
    after = set(select_features(merged, tools))
    return {"selection_in": len(after - before), "selection_out": len(before - after),
            "selection_in_examples": sorted(after - before)[:20], "selection_out_examples": sorted(before - after)[:20],
            "passed_before": len(before), "passed_after": len(after), "stage": "stage5_thresholds",
            "stage6_redundancy": STAGE6_NOTE}


STAGE6_NOTE = "不導出：第 6 階段冗餘篩選須特徵間相關，非替換可得（SPEC v9 補③）"


# ============================================================================================== 收據

def default_receipt_path() -> Path:
    """既有 `*-ffprod-candidates.json` 恰一份 ⇒ 續寫之；無 ⇒ 今日日期；多份 ⇒ RuntimeError。"""
    hits = sorted(RECEIPTS_DIR.glob(RECEIPT_GLOB))
    if len(hits) > 1:
        raise RuntimeError(f"候選收據多於一份：{[h.name for h in hits]}")
    return hits[0] if hits else RECEIPTS_DIR / f"{datetime.now().strftime('%Y%m%d')}-ffprod-candidates.json"


def spec_version(path: Path = SPEC_PATH) -> str:
    """SPEC 檔頭現行版本（`> 版本：v<N>`）；收據據此記錄，不寫死字面（版本前進時不漂）。"""
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("> 版本：v"):
                return "v" + line[len("> 版本：v"):].split("（", 1)[0].strip()
    raise RuntimeError(f"{path}：檔頭無「> 版本：v」行")


def new_receipt(cell_id: str, work_root: Path) -> Dict[str, Any]:
    assert_candidate_set()
    inv = _single(INVENTORY_GLOB)
    return {"schema_version": SCHEMA_VERSION, "ticket": "FFPROD", "task": "Task 2.1 改值候選量測",
            "spec": f"docs/FFPROD_SPEC.md {spec_version()} Task 2.1", "spec_sha256": _sha256_file(SPEC_PATH), "design": "handoffs/20261026-FFPROD-B3-MEASURE-PLAN.md",
            "script": "scripts/ffprod_measure.py", "script_sha256": _sha256_file(Path(__file__)),
            "inventory": {"path": str(inv.relative_to(REPO)), "sha256": _sha256_file(inv),
                          "measure_candidates": inventory_measure_ids(inv)},
            "primary_cell": cell_id, "work_root": str(work_root), "created_at": datetime.now(timezone.utc).isoformat(),
            "baselines": {}, "candidates": {cid: {"unique_path": spec["unique_path"], "baseline": spec["baseline"],
                                                  "options": {opt: {"cells": {}} for opt in spec["options"]}}
                                            for cid, spec in CANDIDATES.items()},
            "interactions": {k: {"members": v["members"], "baseline": v["baseline"], "cells": {}}
                             for k, v in INTERACTIONS.items()},
            "ic": {"baselines": {}}}


def check_receipt(receipt: Mapping[str, Any]) -> None:
    """收據結構檢查：候選集合＝盤點 measure 項集合；每個已寫之選項紀錄具 `OPTION_REQUIRED_KEYS`。"""
    assert sorted(receipt["candidates"]) == list(receipt["inventory"]["measure_candidates"]), \
        f"收據候選 {sorted(receipt['candidates'])} ≠ 盤點 {receipt['inventory']['measure_candidates']}"
    for cid, cand in receipt["candidates"].items():
        for opt, node in cand["options"].items():
            for cell_id, rec in node["cells"].items():
                missing = [k for k in OPTION_REQUIRED_KEYS if k not in rec]
                assert not missing, f"{cid}/{opt}/{cell_id} 缺 {missing}"


def write_receipt(path: Path, receipt: Dict[str, Any]) -> None:
    check_receipt(receipt)
    receipt["updated_at"] = datetime.now(timezone.utc).isoformat()
    _fb()._write_atomic(Path(path), receipt)


def load_receipt(path: Path, cell_id: str, work_root: Path) -> Dict[str, Any]:
    if Path(path).is_file():
        receipt = json.loads(Path(path).read_text(encoding="utf-8"))
        assert_candidate_set()
        check_receipt(receipt)
        return receipt
    return new_receipt(cell_id, work_root)


def _item_node(receipt: Mapping[str, Any], cell_id: str, item: Mapping[str, Any]) -> Optional[Mapping[str, Any]]:
    if item["kind"] == "unreachable":
        node = (receipt.get("candidates") or {}).get(item["candidate"]) or {}
        return node if node.get("status") == "unreachable_difference" else None
    if item["kind"] == "baseline":
        return (receipt.get("baselines") or {}).get(cell_id, {}).get(item["baseline"])
    if item["kind"] == "interaction":
        return (receipt.get("interactions") or {}).get(item["key"], {}).get("cells", {}).get(cell_id)
    return ((receipt.get("candidates") or {}).get(item["candidate"], {}).get("options", {}).get(item["option"], {})
            .get("cells", {}).get(cell_id))


def _generated(node: Optional[Mapping[str, Any]]) -> bool:
    """生成（或不可達判定）已完成且可沿用；自證失敗、probe_invalid 等皆非完成（續跑重做）。"""
    return bool(node) and node.get("status") in ("measured", "blocked", "frozen", "unreachable_difference")


def _has_blocked_by(obj: Any, value: str) -> bool:
    if isinstance(obj, Mapping):
        if value in str(obj.get("blocked_by") or ""):
            return True
        return any(_has_blocked_by(v, value) for v in obj.values())
    if isinstance(obj, (list, tuple)):
        return any(_has_blocked_by(v, value) for v in obj)
    return False


def ic_current(ic: Any, full_ic: bool = False) -> bool:
    """IC 結果已以現行量測設定（`IC_MEASURE_SETTINGS`）完成；無改值欄者不依設定（不跑 IC）。任一處受阻於
    watchdog_timeout ⇒ 非完成（監看終止之結果續跑重算，不沿用）。`full_ic`（--full-ic）時，先前延後
    （fullscale_deferred）之結果非完成 ⇒ 續跑以全欄 IC 重算（CODEX-R9-P1-01）。"""
    if full_ic and _has_blocked_by(ic, BLOCKED_BY_FULLSCALE):
        return False
    return isinstance(ic, dict) and not has_watchdog_timeout(ic) and \
        (ic.get("mode") == "no_changed_columns" or ic.get("ic_settings") == IC_MEASURE_SETTINGS)


def _needs_ic(node: Optional[Mapping[str, Any]], item: Mapping[str, Any], full_ic: bool = False) -> bool:
    """已生成而尚缺現行設定之 IC 結果（選項／交互之 measured 紀錄無 `ic`，或其 `ic` 非現行設定所算）。"""
    return item["kind"] in ("option", "interaction") and bool(node) and node.get("status") == "measured" \
        and not ic_current(node.get("ic"), full_ic)


def _item_done(receipt: Mapping[str, Any], cell_id: str, item: Mapping[str, Any], need_ic: bool = True,
               full_ic: bool = False) -> bool:
    """可略過＝生成已完成，且（要求 IC 時）IC 亦已完成。"""
    node = _item_node(receipt, cell_id, item)
    return _generated(node) and not (need_ic and _needs_ic(node, item, full_ic))


def _store(receipt: Dict[str, Any], cell_id: str, item: Mapping[str, Any], record: Dict[str, Any]) -> None:
    if item["kind"] == "baseline":
        receipt.setdefault("baselines", {}).setdefault(cell_id, {})[item["baseline"]] = record
    elif item["kind"] == "interaction":
        receipt["interactions"][item["key"]]["cells"][cell_id] = record
    else:
        receipt["candidates"][item["candidate"]]["options"][item["option"]]["cells"][cell_id] = record


def _probe_ref(item: Mapping[str, Any]) -> Dict[str, Any]:
    funcs = {name: f"scripts/ffprod_measure.py::_install_{name}" for name in item["probes"]}
    if item.get("ic_only"):
        funcs["ic"] = "scripts/ffprod_measure.py::IC_WINSOR_OFF_OVERRIDE"
    return {"probes": dict(item["probes"]), "paths": funcs, "ic_only": bool(item.get("ic_only"))}


def build_option_record(item: Mapping[str, Any], cell_id: str, gen: Mapping[str, Any], base: Mapping[str, Any],
                        diff: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    """選項收據紀錄（`OPTION_REQUIRED_KEYS` 全具）。`gen`＝生成結果（只 IC 之選項＝改前基準之生成結果）。"""
    blocked = gen.get("status") == "blocked"
    identity = dict(gen.get("identity") or {})
    if identity:
        identity["probe_sha256"] = _sha256_json(_probe_ref(item))
    perf_blocked = {"blocked_by": BLOCKED_BY_HARDWARE} if blocked else None
    return {"option": item["option"], "candidate": item.get("candidate"), "cell": cell_id, "baseline": item["baseline"],
            "probe": _probe_ref(item), "run_dir": gen.get("run_dir"), "identity": identity,
            "status": "blocked" if blocked else "measured",
            "self_proof": gen.get("proof"), "value_diff": (diff or {}).get("summary"),
            "value_diff_unavailable": None if diff is not None else (gen.get("error") or "無改後輸出"),
            "changed_columns": list((diff or {}).get("changed") or []),
            "fingerprints": (diff or {}).get("fingerprints"),
            "seconds": perf_blocked or {"generation": gen.get("generation_seconds"),
                                        "probe_overhead": (gen.get("proof") or {}).get("overhead_seconds"),
                                        "child_total": gen.get("seconds"),
                                        "baseline_generation": base.get("seconds", {}).get("generation")
                                        if isinstance(base.get("seconds"), Mapping) else None},
            "peak_rss_bytes": perf_blocked or {"generation_self": gen.get("peak_rss_bytes"),
                                               "generation_tree": gen.get("peak_rss_tree_bytes"),
                                               "ru_maxrss_children": gen.get("ru_maxrss_children_bytes")},
            "output_bytes": perf_blocked or gen.get("output_bytes"),
            "scale": cell_id, "error": gen.get("error")}


def _externalize_fingerprints(record: Dict[str, Any], receipt_path: Path, cell_id: str, key: str) -> None:
    """改值欄逾 `SIDECAR_MIN_COLUMNS` ⇒ 逐欄改前／改後指紋改寫至收據旁之 `<收據名>.d/<格>__<項>.fingerprints.json`，
    收據內記 {sidecar（相對收據目錄）, sha256, columns}（全特徵格之改值欄可達十萬級，內嵌使收據逾百 MB）。"""
    fps = record.get("fingerprints")
    if not isinstance(fps, Mapping) or len(fps.get("after") or {}) + len(fps.get("before") or {}) <= 2 * SIDECAR_MIN_COLUMNS:
        return
    side_dir = Path(receipt_path).parent / f"{Path(receipt_path).stem}.d"
    side_dir.mkdir(parents=True, exist_ok=True)
    path = side_dir / f"{cell_id}__{key}.fingerprints.json"
    _fb()._write_atomic(path, dict(fps))
    record["fingerprints"] = {"sidecar": str(path.relative_to(Path(receipt_path).parent)), "sha256": _sha256_file(path),
                              "columns": len(record.get("changed_columns") or [])}


def _record_unreachable(receipt: Dict[str, Any], item: Mapping[str, Any], work_root: Path,
                        generate: Callable[[Mapping[str, Any], Mapping[str, Any], Path], Dict[str, Any]]) -> int:
    """SPEC v9 補②：差異不可達之候選——於探針格（`UNREACHABLE[..]["probe_cell"]`）以探針生成一次（只取探針收據，不作量測），
    收據該候選記 {status: unreachable_difference, evidence, probe_receipt}。探針實得 L＞N ⇒ 差異可達：記
    `reachable_measure_required` 並回 3（須於該設定之格量）。"""
    cid = str(item["candidate"])
    spec = UNREACHABLE[cid]
    probe_cell = str(item["probe_cell"])
    gen = generate(item, measure_cell(probe_cell, item["baseline"]), Path(work_root) / probe_cell / item["key"])
    info = ((gen.get("proof") or {}).get("per_probe") or {}).get("dstar") or {}
    probe_receipt = {"cell": probe_cell, "probe": _probe_ref(item), "generation_status": gen.get("status"),
                     "identity": gen.get("identity"), "tests": int(info.get("serial_calls", 0)) + int(info.get("parallel_calls", 0)),
                     "serial_tests": info.get("serial_calls"), "parallel_tests": info.get("parallel_calls"),
                     "max_L": info.get("max_L"), "N_values": info.get("N_values"),
                     "L_gt_N_tests": info.get("effective_calls"),
                     "self_proof_failures": (gen.get("proof") or {}).get("failures"), "error": gen.get("error")}
    node = receipt["candidates"][cid]
    proof = gen.get("proof") or {}
    # 自證完整性：只豁免「無 L＞N 檢定」本身；探針安裝錯、worker 缺紀錄、取樣違規等一律不得記不可達
    unexpected = [f for f in (proof.get("failures") or []) if f != DSTAR_NO_EFFECTIVE]
    probe_receipt["violation_count"] = int(proof.get("violation_count") or 0)
    if gen.get("status") != "ok" or unexpected or probe_receipt["violation_count"] or not probe_receipt["tests"]:
        node.update(status="probe_invalid", evidence=list(spec["evidence"]), probe_receipt=probe_receipt,
                    unexpected_failures=unexpected)
        print(f"[ffprod-measure] {cid}：probe_invalid（{gen.get('status')}；{unexpected}；"
              f"違規 {probe_receipt['violation_count']} 次）", flush=True)
        return 3
    reachable = (probe_receipt["L_gt_N_tests"] or 0) > 0
    node.update(status="reachable_measure_required" if reachable else "unreachable_difference",
                evidence=list(spec["evidence"]), probe_receipt=probe_receipt)
    print(f"[ffprod-measure] {cid}：{node['status']}（檢定 {probe_receipt['tests']} 次、L 最大 {probe_receipt['max_L']}、"
          f"N {probe_receipt['N_values']}、L＞N {probe_receipt['L_gt_N_tests']} 次）", flush=True)
    return 3 if reachable else 0


# ============================================================================================== 編排

def execute(cell_id: str, items: Sequence[Mapping[str, Any]], receipt_path: Path, work_root: Path, *,
            generate: Callable[[Mapping[str, Any], Mapping[str, str], Path], Dict[str, Any]],
            diff: Callable[[Mapping[str, Any], Mapping[str, Any]], Dict[str, Any]],
            ic: Optional[Callable[[Dict[str, Any], str, Mapping[str, Any]], None]] = None) -> int:
    """逐項執行並原子寫入收據（可續跑：已完成項跳過）。`generate(item, cell, item_dir)` 回生成結果；`diff(base, gen)` 回值差；
    `ic(receipt, cell_id, item)` 就地補 IC。自證失敗之選項不寫入、記入回傳碼（3）；其餘續跑。"""
    receipt = load_receipt(receipt_path, cell_id, work_root)
    full_ic = bool(getattr(ic, "full_ic", False))  # --full-ic：先前延後之 IC 不算完成（CODEX-R9-P1-01）
    rc = 0

    def run_ic(item: Mapping[str, Any]) -> int:
        try:
            ic(receipt, cell_id, item)
            if has_watchdog_timeout(_item_node(receipt, cell_id, item)) or \
                    has_watchdog_timeout(receipt.get("ic", {}).get("baselines", {}).get(cell_id, {})):
                print(f"[ffprod-measure] {item['key']}：IC 遭監看終止（watchdog_timeout），不算完成、續跑重算", flush=True)
                return 3
            return 0
        except HangDetected:
            raise  # 程式卡住：整跑停止（不續跑其他項、不自動重跑）
        except Exception as exc:  # noqa: BLE001 — IC 失敗不毀生成紀錄；`ic` 未寫入 ⇒ 下次續跑只補 IC
            print(f"[ffprod-measure] {item['key']}：IC 失敗 {type(exc).__name__}: {exc}", flush=True)
            return 3
        finally:
            write_receipt(receipt_path, receipt)  # IC 步就地改之狀態（含 self_proof_failed）一律落盤

    for item in items:
        if _item_done(receipt, cell_id, item, need_ic=ic is not None, full_ic=full_ic):
            print(f"[ffprod-measure] {cell_id} {item['key']}：已完成，略過", flush=True)
            continue
        if ic is not None and _needs_ic(_item_node(receipt, cell_id, item), item, full_ic):
            print(f"[ffprod-measure] {cell_id} {item['key']}：已生成，只補 IC", flush=True)
            rc = max(rc, run_ic(item))
            continue
        if item["kind"] == "unreachable":
            rc = max(rc, _record_unreachable(receipt, item, work_root, generate))
            write_receipt(receipt_path, receipt)
            continue
        cell = measure_cell(cell_id, item["baseline"])
        item_dir = Path(work_root) / cell_id / item["key"]
        if item["kind"] == "baseline":
            gen = generate(item, cell, item_dir)
            if gen.get("status") == "failed":
                print(f"[ffprod-measure] 改前基準 {item['key']} 失敗：{gen.get('error')}", flush=True)
                return 3
            proof_failed = gen.get("status") == "ok" and not (gen.get("proof") or {}).get("passed")
            if proof_failed:  # 與選項同一閘：自證失敗之基準留診斷紀錄但非 frozen（不可沿用、續跑重做）
                print(f"[ffprod-measure] 改前基準 {item['key']} 自證失敗——{(gen.get('proof') or {}).get('failures')}",
                      flush=True)
                rc = 3
            record = {"status": "self_proof_failed" if proof_failed else
                      "blocked" if gen.get("status") == "blocked" else "frozen", "cell": cell_id,
                      "baseline": item["baseline"], "probe": _probe_ref(item), "run_dir": gen.get("run_dir"),
                      "identity": gen.get("identity"), "fingerprints": gen.get("fingerprints"),
                      "seconds": {"generation": gen.get("generation_seconds"), "child_total": gen.get("seconds"),
                                  "probe_overhead": (gen.get("proof") or {}).get("overhead_seconds")},
                      "peak_rss_bytes": {"generation_self": gen.get("peak_rss_bytes"),
                                         "generation_tree": gen.get("peak_rss_tree_bytes")},
                      "output_bytes": gen.get("output_bytes"), "observed_arm": gen.get("observed_arm"),
                      "self_proof": gen.get("proof"), "l2_three_points": gen.get("l2_three_points"),
                      "ratio_unsafe_selection": gen.get("ratio_unsafe_selection"),
                      "error": gen.get("error")}
            _store(receipt, cell_id, item, record)
            write_receipt(receipt_path, receipt)
            continue
        base = (receipt.get("baselines") or {}).get(cell_id, {}).get(item["baseline"])
        if not base or base.get("status") != "frozen":
            print(f"[ffprod-measure] {item['key']}：改前基準 {item['baseline']} 不可用（{(base or {}).get('status')}）",
                  flush=True)
            rc = 3
            continue
        if item.get("ic_only"):
            gen = {"status": "ok", "run_dir": base["run_dir"], "identity": base["identity"],
                   "fingerprints": base["fingerprints"], "proof": {"passed": None, "failures": [], "per_probe": {},
                                                                    "note": "只 IC：自證見 ic.self_proof"},
                   "generation_seconds": 0.0, "output_bytes": base.get("output_bytes")}
            d = {"summary": {"changed_columns": 0, "max_abs_diff": 0.0, "nan_mask_diff_columns": 0,
                             "note": "特徵值不變（只 IC 前處理改設定）"}, "changed": [], "fingerprints": {"before": {}, "after": {}}}
        else:
            gen = generate(item, cell, item_dir)
            if gen.get("status") == "failed":
                print(f"[ffprod-measure] {item['key']}：生成失敗 {gen.get('error')}", flush=True)
                rc = 3
                continue
            proof = gen.get("proof") or {}
            if gen.get("status") == "ok" and not proof.get("passed"):
                print(f"[ffprod-measure] {item['key']}：自證失敗，收據拒寫——{proof.get('failures')}", flush=True)
                rc = 3
                continue
            d = diff(base, gen) if gen.get("status") == "ok" else None
            if d is not None and "winsor_core" in item["probes"]:
                # SPEC v9 補①：盤點未列之選欄差異（校準域縮尾對 ratio-unsafe 欄亦作用、公開快速臂跳過）之欄集合與差值
                d["summary"]["ratio_unsafe_calibration_selection"] = {
                    "baseline": base.get("ratio_unsafe_selection"), "option": gen.get("ratio_unsafe_selection"),
                    "public_fast_arm": "跳過（momentum/FeatureEngineering/preprocessing/feature_preprocessor.py:1729-1740）"}
        record = build_option_record(item, cell_id, gen, base, d)
        if item["kind"] == "interaction":
            record["members"] = item.get("members")
        _externalize_fingerprints(record, receipt_path, cell_id, item["key"])
        _store(receipt, cell_id, item, record)
        write_receipt(receipt_path, receipt)
        if ic is not None and record["status"] == "measured":
            rc = max(rc, run_ic(item))
    return rc


#: 替換前提之逐欄比較鍵：翻轉與第 5 階段門檻（`ic_filter_orchestrator._apply_thresholds`）實際讀之逐特徵輸入；
#: `p_value_adj` 不比（全 universe FDR，由 `select_features` 於替換後重算）
PREMISE_KEYS = ("ic_mean", "icir", "p_value", "t_stat", "ic_hit_rate", "monotonicity_score", "coverage",
                "long_short_spread")


def _same_value(a: Any, b: Any) -> bool:
    """逐位元相等；兩側皆 NaN 視為相同（缺值一致）。"""
    if isinstance(a, float) and isinstance(b, float) and a != a and b != b:
        return True
    return a == b


def premise_mismatches(full_rows: Mapping[str, Mapping[str, Any]], subset_rows: Mapping[str, Mapping[str, Any]],
                       changed: Sequence[str]) -> List[str]:
    """改前全欄列與改前改值欄子集列於改值欄之不一致者：一側有列一側無（stage1 去留不同），或任一 PREMISE_KEYS 不同。"""
    out = []
    for f in changed:
        a, b = full_rows.get(f), subset_rows.get(f)
        if (a is None) != (b is None) or (a is not None and not all(_same_value(a.get(k), b.get(k)) for k in PREMISE_KEYS)):
            out.append(f)
    return out


def blocked_summary(sources: Mapping[str, Mapping[str, Any]]) -> Optional[Dict[str, Any]]:
    """多份 IC 來源中受阻者之摘要：`blocked_by`＝受阻原因類別（hardware／watchdog_timeout；多類以「+」依字母序連）、
    `reason`／`causes`＝逐來源之理由與類別；全部可得 ⇒ None。"""
    hit = {k: v for k, v in sources.items() if v.get("status") == "blocked"}
    if not hit:
        return None
    causes = {k: v.get("blocked_by") or BLOCKED_BY_HARDWARE for k, v in hit.items()}
    return {"blocked_by": "+".join(sorted(set(causes.values()))), "reason": {k: v.get("reason") for k, v in hit.items()},
            "causes": causes}


#: 改前全欄 IC 依使用者 2026-09-28 裁定（8 GB 跑不動之大規模驗證延後至完整規模驗證，docs/TICKET_ORDER.md 第 16 步
#: RM-FULLSCALE）及 NUMVIEW 2026-10-22 實測（全特徵格全欄 IC 於 8 GB 無法完成）延後：預設不跑，記此受阻類別（SPEC v13 補③）
BLOCKED_BY_FULLSCALE = "fullscale_deferred"
FULLSCALE_REASON = ("全特徵格之改前全欄 IC 依 2026-09-28 使用者裁定延後至完整規模驗證（docs/TICKET_ORDER.md 第 16 步 "
                    "RM-FULLSCALE；NUMVIEW 2026-10-22 實測 8 GB 無法完成）；以 --full-ic 於完整規模機器執行")


def make_ic_step(work_root: Path, force: bool = False,
                 full_ic: bool = False) -> Callable[[Dict[str, Any], str, Mapping[str, Any]], None]:
    """IC 步（SPEC v9 補③）：
    - 正負號翻轉：改前 run 與選項 run 各只算改值欄（產品 IC 縱向路徑、IC 頁預設請求），比 ic_mean 正負號。
    - 選欄進出：第 5 階段門檻由「改前全欄 IC（每個改前基準試跑一次，快取於收據 `ic.baselines`）中替換改值欄之列」重算 FDR
      與門檻導出；改前全欄 IC 逾 8 GB（記憶體守護、訊號終止）⇒ 記 `blocked_by: hardware`，卡死監看終止 ⇒
      `blocked_by: watchdog_timeout`（SPEC v10 補③；皆不以較小規模代替）。另以改前 run 只算
      改值欄之列對照全欄列（替換前提）。第 6 階段不導出（收據註明）。
    - `ic_winsor_off`：改前 run 全欄、IC 前處理縮尾關重算；全欄 IC 任一側受阻 ⇒ 翻轉與選欄皆記 blocked。"""

    def base_ic(receipt: Dict[str, Any], cell_id: str, bid: str) -> Dict[str, Any]:
        node = receipt["ic"]["baselines"].setdefault(cell_id, {})
        if not full_ic:  # 延後至完整規模驗證：不跑，記受阻（翻轉只用改值欄 IC，不受影響）
            node[bid] = {"status": "blocked", "blocked_by": BLOCKED_BY_FULLSCALE, "reason": FULLSCALE_REASON,
                         "scope": "改前全欄 IC", "ic_settings": IC_MEASURE_SETTINGS}
            return node[bid]
        cached = node.get(bid)
        if cached and not force and cached.get("ic_settings") == IC_MEASURE_SETTINGS and \
                not has_watchdog_timeout(cached) and cached.get("blocked_by") != BLOCKED_BY_FULLSCALE and \
                (cached.get("status") == "blocked" or Path(cached.get("rows_path", "")).is_file()):
            return cached  # 只沿用成功或硬體受阻者；監看終止者與先前延後者重算
        base = receipt["baselines"][cell_id][bid]
        cell = measure_cell(cell_id, bid)
        res = ic_watched(Path(base["run_dir"]), str(cell["symbol"]), str(cell["timeframes"][0]), None, False,
                         Path(work_root) / cell_id / f"ic__baseline__{bid}")
        if res.get("status") == "blocked":
            node[bid] = {"status": "blocked", "blocked_by": res.get("blocked_by"), "reason": res.get("reason"),
                         "swap_growth_max_mb": res.get("swap_growth_max_mb"), "ic_settings": IC_MEASURE_SETTINGS,
                         "scope": "改前全欄 IC", "log": res.get("log"), "wall_seconds": res.get("wall_seconds")}
            return node[bid]
        rows_path = Path(work_root) / cell_id / f"ic__baseline__{bid}" / "rows.json"
        rows_path.parent.mkdir(parents=True, exist_ok=True)
        rows_path.write_text(json.dumps(res["rows"], ensure_ascii=False), encoding="utf-8")
        tools = _selection_tools(res["override"])
        passed = select_features(res["rows"], tools)
        node[bid] = {"status": "ok", "ic_settings": IC_MEASURE_SETTINGS,
                     "rows_path": str(rows_path), "rows_sha256": _sha256_file(rows_path),
                     "features": len(res["rows"]),
                     "seconds": res["seconds"], "peak_rss_bytes": res["peak_rss_bytes"], "override": res["override"],
                     "config_sha256": res["config_sha256"], "ic_config_files": res.get("ic_config_files"),
                     "stage1_winsorized_count": res["stage1_winsorized_count"],
                     "passed_recomputed": len(passed), "passed_count_from_report": res["passed_count_from_report"],
                     "recompute_matches_report": len(passed) == res["passed_count_from_report"],
                     "stage5": res["stage5"]}
        if not node[bid]["recompute_matches_report"]:
            raise RuntimeError(f"{bid}：選欄重排（{len(passed)}）≠ 報告 stage5 通過數（{res['passed_count_from_report']}）"
                               "——替換重排之前提不成立，停止")
        return node[bid]

    def step(receipt: Dict[str, Any], cell_id: str, item: Mapping[str, Any]) -> None:
        rec = _item_node(receipt, cell_id, item)
        assert rec is not None
        if ic_current(rec.get("ic"), full_ic) and not force:
            return
        compute(receipt, cell_id, item, rec)
        rec["ic"]["ic_settings"] = IC_MEASURE_SETTINGS  # 正常完成才標記（自證失敗之 raise 不標 ⇒ 續跑重算）

    def compute(receipt: Dict[str, Any], cell_id: str, item: Mapping[str, Any], rec: Dict[str, Any]) -> None:
        cell = measure_cell(cell_id, item["baseline"])
        symbol, tf = str(cell["symbol"]), str(cell["timeframes"][0])
        idir = Path(work_root) / cell_id / f"ic__{item['key']}"
        base_run = Path(receipt["baselines"][cell_id][item["baseline"]]["run_dir"])
        if item.get("ic_only"):
            bnode = base_ic(receipt, cell_id, item["baseline"])
            res = ic_watched(Path(rec["run_dir"]), symbol, tf, None, True, idir)
            blocked = blocked_summary({"baseline_full": bnode, "winsor_off_full": res})
            if blocked:
                rec["ic"] = {"mode": "full_rerun_winsor_off", "sign_flips": blocked, "selection": blocked,
                             "stage6_redundancy": STAGE6_NOTE}
                return
            base_rows = json.loads(Path(bnode["rows_path"]).read_text(encoding="utf-8"))
            proof_ok = (res["stage1_winsorized_count"] == 0 and (bnode.get("stage1_winsorized_count") or 0) > 0
                        and ((res["override"] or {}).get("preprocessing") or {}).get("winsorization", {}).get("enabled")
                        is False)
            # IC 前處理縮尾作用於全部欄 ⇒ 翻轉於全欄計（特徵值不變，改值欄集合為空）
            flips = sign_flips(base_rows, res["rows"], sorted(set(base_rows) & set(res["rows"])))
            before = set(select_features(base_rows, _selection_tools(bnode["override"])))
            after = set(select_features(res["rows"], _selection_tools(res["override"])))
            rec["ic"] = {"mode": "full_rerun_winsor_off", "seconds": res["seconds"], "peak_rss_bytes": res["peak_rss_bytes"],
                         "features": len(res["rows"]), **flips,
                         "selection": {"selection_in": len(after - before), "selection_out": len(before - after),
                                       "passed_before": len(before), "passed_after": len(after),
                                       "stage": "stage5_thresholds（兩側皆全欄實算）"},
                         "stage6_redundancy": STAGE6_NOTE,
                         "self_proof": {"passed": proof_ok, "stage1_winsorized_count": res["stage1_winsorized_count"],
                                        "baseline_stage1_winsorized_count": bnode.get("stage1_winsorized_count"),
                                        "override": res["override"]}}
            rec["self_proof"] = rec["ic"]["self_proof"]
            if not proof_ok:
                rec["status"] = "self_proof_failed"
                raise SelfProofFailed(f"{item['key']}：IC 縮尾關自證失敗 {rec['ic']['self_proof']}")
            return
        changed = list(rec.get("changed_columns") or [])
        if not changed:
            rec["ic"] = {"mode": "no_changed_columns", "sign_flips": 0, "selection": {"selection_in": 0, "selection_out": 0},
                         "stage6_redundancy": STAGE6_NOTE, "seconds": 0.0}
            return
        res = ic_watched(Path(rec["run_dir"]), symbol, tf, changed, False, idir / "option")
        base_sub = ic_watched(base_run, symbol, tf, changed, False, idir / "baseline_changed")
        out: Dict[str, Any] = {"mode": "changed_columns", "seconds": res.get("seconds"),
                               "baseline_changed_seconds": base_sub.get("seconds"), "peak_rss_bytes": res.get("peak_rss_bytes"),
                               "stage6_redundancy": STAGE6_NOTE}
        flips_blocked = blocked_summary({"option_changed": res, "baseline_changed": base_sub})
        if flips_blocked:
            out["sign_flips"] = flips_blocked
        else:
            out.update(sign_flips(base_sub["rows"], res["rows"], changed))
        bnode = base_ic(receipt, cell_id, item["baseline"])
        # 選欄由替換推導，須三份皆可得：改前全欄、選項改值欄、改前改值欄（後者用以驗替換前提）
        blocked = blocked_summary({"baseline_full": bnode, "option_changed": res, "baseline_changed": base_sub})
        if blocked:
            out["selection"] = {**blocked, "scope": "改前全欄 IC 試跑一次（SPEC v10 補③）"}
        else:
            base_rows = json.loads(Path(bnode["rows_path"]).read_text(encoding="utf-8"))
            mismatch = premise_mismatches(base_rows, base_sub["rows"], changed)
            out["substitution_premise"] = {"checked_columns": len(changed), "mismatched": len(mismatch),
                                           "examples": mismatch[:10], "keys": list(PREMISE_KEYS), "holds": not mismatch}
            if mismatch:  # 前提不成立 ⇒ 替換不等價於全量重算，不輸出選欄數字
                out["selection"] = {"not_derived": "替換前提不成立（改前改值欄子集 IC ≠ 改前全欄 IC）",
                                    "mismatched": len(mismatch)}
            else:
                out["selection"] = selection_effect(base_rows, res["rows"], changed, _selection_tools(bnode["override"]))
        rec["ic"] = out

    step.full_ic = full_ic  # type: ignore[attr-defined]  # execute 之完成判定據此（CODEX-R9-P1-01）
    return step


def run(args: argparse.Namespace) -> int:
    cell_id = args.cell
    receipt_path = Path(args.receipt) if args.receipt else default_receipt_path()
    work_root = Path(args.work_root)
    items = plan_items(cell_id, args.candidates)

    def generate(item: Mapping[str, Any], cell: Mapping[str, Any], item_dir: Path) -> Dict[str, Any]:
        return generate_watched(cell, item["probes"], item_dir, expected_seconds(cell))

    def diff(base: Mapping[str, Any], gen: Mapping[str, Any]) -> Dict[str, Any]:
        return run_value_diff(Path(base["run_dir"]), Path(gen["run_dir"]), base["fingerprints"], gen["fingerprints"])

    step = None if args.skip_ic else make_ic_step(work_root, full_ic=args.full_ic)
    try:
        rc = execute(cell_id, items, receipt_path, work_root, generate=generate, diff=diff, ic=step)
    except HangDetected as exc:  # 不自動重跑：留現場後停止，依堆疊查因修好再跑
        print(f"[ffprod-measure] 停止：{exc}", flush=True)
        rc = 4
    print(f"[ffprod-measure] 收據 {receipt_path}（rc={rc}）", flush=True)
    return rc


def ic_only(args: argparse.Namespace) -> int:
    cell_id = args.cell
    receipt_path = Path(args.receipt) if args.receipt else default_receipt_path()
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    step = make_ic_step(Path(receipt.get("work_root") or args.work_root), force=args.force, full_ic=args.full_ic)
    rc = 0
    for item in plan_items(cell_id, args.candidates):
        if item["kind"] in ("baseline", "unreachable"):
            continue
        node = _item_node(receipt, cell_id, item)
        if not node or node.get("status") != "measured":
            continue
        try:
            step(receipt, cell_id, item)
        except HangDetected as exc:  # 程式卡住：留現場後整跑停止（不續跑其他項、不自動重跑；CODEX-R10-P1-01）
            write_receipt(receipt_path, receipt)
            print(f"[ffprod-measure] 停止：{exc}", flush=True)
            return 4
        except Exception as exc:  # noqa: BLE001
            print(f"[ffprod-measure] {item['key']}：IC 失敗 {type(exc).__name__}: {exc}", flush=True)
            rc = 3
        write_receipt(receipt_path, receipt)
    return rc


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="FFPROD Task 2.1 改值候選量測")
    parser.add_argument("--gen-child", default=None, help=argparse.SUPPRESS)
    parser.add_argument("--ic-child", default=None, help=argparse.SUPPRESS)
    sub = parser.add_subparsers(dest="cmd")
    for name in ("plan", "run", "ic"):
        p = sub.add_parser(name)
        p.add_argument("--cell", default=DEFAULT_CELL)
        p.add_argument("--candidates", nargs="*", default=None)
        p.add_argument("--receipt", default=None)
        p.add_argument("--work-root", default=str(DEFAULT_WORK_ROOT))
        if name == "run":
            p.add_argument("--skip-ic", action="store_true")
        if name == "ic":
            p.add_argument("--force", action="store_true")
        if name in ("run", "ic"):
            p.add_argument("--full-ic", action="store_true",
                           help="跑改前全欄 IC（只於完整規模驗證機器；預設延後，見 FULLSCALE_REASON）")
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.gen_child:
        return _gen_child(Path(args.gen_child))
    if args.ic_child:
        return _ic_child(Path(args.ic_child))
    assert_candidate_set()
    if args.cmd == "plan":
        receipt_path = Path(args.receipt) if args.receipt else default_receipt_path()
        receipt = json.loads(receipt_path.read_text(encoding="utf-8")) if receipt_path.is_file() else None
        print(json.dumps(plan(args.cell, args.candidates, receipt), ensure_ascii=False, indent=1))
        return 0
    if args.cmd == "run":
        return run(args)
    if args.cmd == "ic":
        return ic_only(args)
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
