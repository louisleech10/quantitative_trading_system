"""NUMVIEW L2 兩臂矩陣（docs/NUMVIEW_SPEC.md Task 1.3，C7）。

承 `handoffs/run_receipts/icfirstalign_probes/l2_arm_pipeline_probe.py`，參數化至格 A＋格 B 全部格：每格記 L1 輸入
dtype、兩臂（L5／L6 所吃之 `compute_all_polars` 表 vs 公開落盤之 `compute_category`）之欄集合、NaN 遮罩、float32
有限值差格數（`f32diff`）、max_abs、max_rel，及 `FFACT_USE_POLARS=0` 時 pandas 臂之同表。某類別 `compute_category`
拋錯 ⇒ 記錯誤，不以缺欄計 0 差（邊界②）。啟動前呼叫 `_estimate_gate.require("l2_arm_matrix", cells)`。
格與生成依判準檔 `run_coverage.l2_arm_matrix`（路徑覆蓋）：凍結已生成之 (格, 環境) 一律讀凍結生成所掛 L2 spy 之紀錄、
不重生；只有凍結無該環境之生成（格 B、格 C 之 `FFACT_USE_POLARS=0`）才生成。
BTCUSDT 12h 格須重現 freeze-baselines 收據之 f32diff=0（不符 ⇒ rc≠0，停下歸因）。
收據 `handoffs/run_receipts/<date>-numview-l2-arm-matrix.json`，含 `criteria_sha256`。

`compare_l2_arms` 與擷取 spy `L2Capture` 於 Task 0.5 建立（凍結生成時掛之）；`main` 為 Task 1.3 實作。
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple

import numpy as np
import pandas as pd

#: 擷取紀錄之 schema 版本（Task 1.3 讀之）；2 起公開類別表於 cascade blacklist 後計算（`blacklist_applied`）
L2_CAPTURE_SCHEMA = 2


def compare_l2_arms(returned: pd.DataFrame, category: pd.DataFrame) -> Dict[str, Any]:
    """兩臂比較：`common_cols`、`only_returned`、`only_category`、`nan_mask_diff`、`f64diff`、`f32diff`、`max_abs`、
    `max_rel`；只比兩者皆有限之格之值差，NaN 遮罩差另列。`only_returned`／`only_category` 為欄名清單（排序；Task 1.3 驗收
    契約），`common_cols` 為共同欄數。列數不同 ⇒ `row_mismatch`（不比值）。"""
    ret_cols = [str(c) for c in returned.columns]
    cat_cols = [str(c) for c in category.columns]
    ret_set, cat_set = set(ret_cols), set(cat_cols)
    common = [c for c in cat_cols if c in ret_set]
    out: Dict[str, Any] = {"common_cols": len(common), "only_returned": sorted(ret_set - cat_set),
                           "only_category": sorted(cat_set - ret_set), "nan_mask_diff": 0, "f64diff": 0, "f32diff": 0,
                           "max_abs": 0.0, "max_rel": 0.0, "row_mismatch": None}
    if returned.shape[0] != category.shape[0]:
        out["row_mismatch"] = [int(returned.shape[0]), int(category.shape[0])]
        return out
    if not common:
        return out
    a = returned.loc[:, common].to_numpy(dtype=np.float64)
    b = category.loc[:, common].to_numpy(dtype=np.float64)
    nan_a, nan_b = np.isnan(a), np.isnan(b)
    both = np.isfinite(a) & np.isfinite(b)
    diff = np.abs(np.where(both, a - b, 0.0))
    scale = np.where(both, np.maximum(np.abs(a), np.abs(b)), 0.0)
    rel = np.divide(diff, scale, out=np.zeros_like(diff), where=scale > 0)
    out.update(nan_mask_diff=int((nan_a != nan_b).sum()), f64diff=int((both & (a != b)).sum()),
               f32diff=int((both & (a.astype(np.float32) != b.astype(np.float32))).sum()),
               max_abs=float(diff.max()) if diff.size else 0.0, max_rel=float(rel.max()) if rel.size else 0.0)
    return out


def _merge(stats: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """逐類別比較之合計（計數相加、max 取最大；任一類別列數不符 ⇒ 列出）。"""
    out: Dict[str, Any] = {"common_cols": 0, "only_category": [], "nan_mask_diff": 0, "f64diff": 0, "f32diff": 0,
                           "max_abs": 0.0, "max_rel": 0.0, "row_mismatch": []}
    only_category: Set[str] = set()
    for s in stats:
        for key in ("common_cols", "nan_mask_diff", "f64diff", "f32diff"):
            out[key] += int(s[key])
        only_category |= set(s.get("only_category") or [])
        out["max_abs"] = max(out["max_abs"], float(s["max_abs"]))
        out["max_rel"] = max(out["max_rel"], float(s["max_rel"]))
        if s.get("row_mismatch"):
            out["row_mismatch"].append(s["row_mismatch"])
    out["only_category"] = sorted(only_category)
    return out


class L2Capture:
    """凍結生成所掛之 L2 兩臂擷取 spy（SPEC Task 0.5、Task 1.3）：包 `FeatureFactory._layer2_derived_features`，對其回傳表
    （L5／L6 所吃者：Polars 臂為 `compute_all_polars`、pandas 臂為 pandas 實作）與同一輸入之逐類別 `compute_category`
    （公開落盤路徑）逐類別比較、只累積統計量（全特徵格不同時持有兩份全表）。每個 (domain, 列數) 只記第一次呼叫
    （domain＝calibration／main；多週期格之各週期列數不同而各記一次）。比較本身之例外記入紀錄、不影響生成。"""

    def __init__(self) -> None:
        self.records: List[Dict[str, Any]] = []
        self._seen: Set[Tuple[str, int]] = set()

    def __enter__(self) -> "L2Capture":
        from momentum.FeatureEngineering import feature_factory as ff

        self._ff = ff
        self._real = ff.FeatureFactory._layer2_derived_features
        capture = self

        def spy(this: Any, layer1: pd.DataFrame, data: pd.DataFrame, config: Any) -> Any:
            result = capture._real(this, layer1, data, config)
            domain = "calibration" if getattr(this, "_calibration_domain", False) else "main"
            key = (domain, int(layer1.shape[0]))
            if key not in capture._seen:
                capture._seen.add(key)
                capture.records.append(capture._record(this, layer1, data, config, result, domain))
            return result

        ff.FeatureFactory._layer2_derived_features = spy  # type: ignore[assignment]
        return self

    def __exit__(self, *exc: Any) -> None:
        self._ff.FeatureFactory._layer2_derived_features = self._real  # type: ignore[assignment]

    def _record(self, this: Any, layer1: pd.DataFrame, data: pd.DataFrame, config: Any, result: Any,
                domain: str) -> Dict[str, Any]:
        started = time.perf_counter()
        returned = getattr(result, "data", None)
        base: Dict[str, Any] = {"schema": L2_CAPTURE_SCHEMA, "domain": domain, "rows": int(layer1.shape[0]),
                                "l1_cols": int(layer1.shape[1]), "l1_dtypes": sorted({str(t) for t in layer1.dtypes})}
        try:
            from momentum.FeatureEngineering.polars_adapter import polars_enabled

            base["returned_arm"] = "polars" if polars_enabled() else "pandas"
            base["returned_cols"] = int(returned.shape[1]) if returned is not None else None
            base["returned_dtypes"] = sorted({str(t) for t in returned.dtypes}) if returned is not None else []
            eng_cls = self._ff._derived_operator_engine_cls()
            engine = eng_cls(this._filter_operators_config(config.operators))
            # 審碼 r29：同生產 L2（feature_factory.py:1771）先套 cascade blacklist 再算公開類別表；未套則黑名單 L1 欄之
            # 衍生欄假現於 `only_category`（凍結 C 之 78 欄即此；schema 1 之紀錄未套）
            layer1 = this._apply_cascade_blacklist(layer1, "L2_input", config)
            base["blacklist_applied"] = True
            specs = this._build_indicator_specs(layer1, config)
            stats: List[Dict[str, Any]] = []
            covered: Set[str] = set()
            errors: Dict[str, str] = {}
            per_category: Dict[str, Dict[str, Any]] = {}
            for category in eng_cls.OPERATOR_CATEGORIES:
                try:
                    frame = engine.compute_category(layer1, data, specs, category)
                except Exception as exc:  # noqa: BLE001 — 邊界②：記錯誤，不以缺欄計 0 差
                    errors[str(category)] = f"{type(exc).__name__}: {exc}"[:500]
                    continue
                if frame is None or frame.empty:
                    continue
                one = compare_l2_arms(returned, frame)
                stats.append(one)
                # 逐類別之「只在回傳表」為其他類別之欄，不存（全特徵格過大）；合計後另算
                per_category[str(category)] = {k: v for k, v in one.items() if k != "only_returned"}
                covered |= {str(c) for c in frame.columns}
                del frame
            merged = _merge(stats)
            merged["only_returned"] = sorted({str(c) for c in returned.columns} - covered) if returned is not None else None
            base.update(merged, per_category=per_category, category_errors=errors)
        except Exception as exc:  # noqa: BLE001 — 比較失敗記錄、不影響生成
            base["capture_error"] = f"{type(exc).__name__}: {exc}"[:1000]
        base["compare_seconds"] = time.perf_counter() - started
        return base


# ============================================================================================== Task 1.3 主入口

REPO = Path(__file__).resolve().parents[3]
PROBES_DIR = Path(__file__).resolve().parent
RECEIPTS_DIR = REPO / "handoffs" / "run_receipts"
FREEZE_SCRIPT = REPO / "scripts" / "numview_freeze_baseline.py"
DEFAULT_WORK_ROOT = REPO / "data_cache" / "numview_l2_runs"
RUN_KIND = "l2_arm_matrix"
#: freeze-baselines 已知零差之重現格（SPEC Task 1.3 驗證；收據 `20261004-icfirstalign-freeze-baselines.json`）
REPRO_CELL = "A_BTCUSDT_12h"
_MODULES: Dict[str, Any] = {}


def _log(message: str) -> None:
    print(f"[l2-matrix] {datetime.now().strftime('%H:%M:%S')} {message}", flush=True)


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


def _gate() -> Any:
    return _load("numview_estimate_gate", PROBES_DIR / "_estimate_gate.py")


def _watchdog() -> Any:
    return _load("numview_watchdog", PROBES_DIR / "_watchdog.py")


def _freeze() -> Any:
    return _load("numview_freeze_baseline_l2", FREEZE_SCRIPT)


def _criteria_path() -> Path:
    from tests.feature_engineering import numview_helpers as nh

    return nh.current_criteria_path()


def _criteria() -> Dict[str, Any]:
    return json.loads(_criteria_path().read_text(encoding="utf-8"))


def _cell(cell_id: str) -> Dict[str, Any]:
    for c in _criteria()["cell_rules"]["cell_list"]["cells"]:
        if str(c["id"]) == cell_id:
            return {"id": str(c["id"]), "kind": str(c["kind"]), "symbol": str(c["symbol"]),
                    "timeframes": [str(t) for t in c["timeframes"]]}
    raise KeyError(cell_id)


def env_key(env: Mapping[str, str]) -> str:
    """凍結收據 `l2_capture.<格>` 之環境鍵（同 `numview_freeze_baseline.freeze_cell`：空＝default，否則 `K=V` 以 `_` 連接）。"""
    return "_".join(f"{k}={v}" for k, v in sorted(env.items())) or "default"


def planned_runs(criteria: Mapping[str, Any]) -> List[Dict[str, Any]]:
    """判準 `run_coverage.l2_arm_matrix.runs`（格、環境、generations、來源）。"""
    runs = (criteria.get("run_coverage") or {}).get(RUN_KIND, {}).get("runs") or []
    return [{"cell": str(r["cell"]), "env": {str(k): str(v) for k, v in (r.get("env") or {}).items()},
             "generations": int(r.get("generations") or 0), "covers": r.get("covers")} for r in runs]


def _freeze_capture() -> Tuple[Dict[str, Any], str]:
    hits = sorted(RECEIPTS_DIR.glob("*-numview-freeze-baseline.json"))
    if len(hits) != 1:
        raise RuntimeError(f"凍結收據須恰一份，實得 {[p.name for p in hits]}")
    return json.loads(hits[0].read_text(encoding="utf-8")).get("l2_capture") or {}, hits[0].name


def summarize_arm(records: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    """一個 (格, 環境) 之擷取紀錄彙總：主生成域（domain＝main）之各次呼叫合計為該臂之格層數字（計數相加、max 取最大、
    欄名清單取聯集、L1 dtype 取聯集），校準域另列；任一類別錯誤或擷取錯誤 ⇒ `errors` 非空且 `f32diff` 為 None（邊界②）。"""
    main = [r for r in records if r.get("domain") == "main"]
    out: Dict[str, Any] = {"main_calls": len(main), "main_rows": [int(r.get("rows") or 0) for r in main],
                           "calibration_calls": sum(1 for r in records if r.get("domain") == "calibration"),
                           "returned_arm": sorted({str(r.get("returned_arm")) for r in main if r.get("returned_arm")}),
                           "l1_dtypes": sorted({str(t) for r in main for t in r.get("l1_dtypes") or []}),
                           "returned_dtypes": sorted({str(t) for r in main for t in r.get("returned_dtypes") or []}),
                           "common_cols": sum(int(r.get("common_cols") or 0) for r in main),
                           "only_returned": sorted({str(c) for r in main for c in r.get("only_returned") or []}),
                           "only_category": sorted({str(c) for r in main for c in r.get("only_category") or []}),
                           "nan_mask_diff": sum(int(r.get("nan_mask_diff") or 0) for r in main),
                           "f64diff": sum(int(r.get("f64diff") or 0) for r in main),
                           "f32diff": sum(int(r.get("f32diff") or 0) for r in main),
                           "max_abs": max([float(r.get("max_abs") or 0.0) for r in main] or [0.0]),
                           "max_rel": max([float(r.get("max_rel") or 0.0) for r in main] or [0.0]),
                           "row_mismatch": [m for r in main for m in r.get("row_mismatch") or []]}
    # 審碼 r29：錯誤含主域與校準域之類別錯誤、擷取錯誤及列數不符（任一 ⇒ 不以 0 差計）
    errors = []
    for r in records:
        prefix = "" if r.get("domain") == "main" else f"{r.get('domain')}:"
        errors += [{"category": f"{prefix}{cat}", "error": str(err)} for cat, err in (r.get("category_errors") or {}).items()]
        if r.get("capture_error"):
            errors.append({"category": f"{prefix}*capture*", "error": str(r["capture_error"])})
        if r.get("row_mismatch"):
            errors.append({"category": f"{prefix}*row_mismatch*", "error": f"列數不符 {r.get('row_mismatch')}"})
    if not main:
        errors.append({"category": "*capture*", "error": "無主生成域之 L2 擷取紀錄"})
    out["errors"] = errors
    if errors:
        out["f32diff"] = None
    # 審碼 r29：schema 1 之紀錄未套 cascade blacklist ⇒ 其 `only_category` 含黑名單 L1 欄之衍生欄（spy 假象，非兩臂差）
    out["blacklist_applied"] = bool(main) and all(r.get("blacklist_applied") is True for r in main)
    out["calibration"] = [{k: r.get(k) for k in ("rows", "l1_dtypes", "returned_arm", "common_cols", "nan_mask_diff",
                                                 "f32diff", "max_abs", "max_rel")} for r in records
                          if r.get("domain") == "calibration"]
    return out


def build_cell(cell: Mapping[str, Any], arms: Mapping[str, Mapping[str, Any]]) -> Dict[str, Any]:
    """格層紀錄：格層數字＝預設環境（Polars 臂；判準 run_coverage 之 `env` 空）之主生成域彙總；各環境之彙總於 `arms`。"""
    default = arms.get("default") or summarize_arm([])
    keys = ("l1_dtypes", "common_cols", "only_returned", "only_category", "nan_mask_diff", "f64diff", "f32diff", "max_abs",
            "max_rel", "errors", "blacklist_applied")
    return {"cell_id": str(cell["id"]), "kind": str(cell["kind"]), "symbol": str(cell["symbol"]),
            "timeframes": list(cell["timeframes"]), **{k: default.get(k) for k in keys}, "arms": dict(arms)}


def _child(spec_path: Path) -> int:
    spec = json.loads(Path(spec_path).read_text(encoding="utf-8"))
    fz = _freeze()
    with fz._clean_env({}):
        handle = fz.generate_cell(Path(spec["work_root"]), _cell(spec["cell"]), run_kind=RUN_KIND, env=spec["env"],
                                  observe_l2=True)
    side = fz._sidecar(handle.work)  # 該格生成之 sidecar（含 `l2_capture`；`generate_cell_run` 最後原子寫入）
    Path(spec["result_path"]).write_text(json.dumps({"status": side.get("status"), "seconds": side.get("seconds"),
                                                     "l2_capture": side.get("l2_capture"), "env": side.get("env")},
                                                    ensure_ascii=False, default=str), encoding="utf-8")
    return 0


def _generate(cell_id: str, env: Mapping[str, str], work_root: Path) -> Dict[str, Any]:
    """另行生成（判準 generations＝1 之 (格, 環境)）：子行程經卡死監看執行 `generate_cell(observe_l2=True)`。"""
    results = work_root / "_results"
    results.mkdir(parents=True, exist_ok=True)
    result_path = results / f"{cell_id}__{env_key(env)}.json"
    result_path.unlink(missing_ok=True)
    spec_path = result_path.with_suffix(".spec.json")
    spec_path.write_text(json.dumps({"cell": cell_id, "env": dict(env), "work_root": str(work_root),
                                     "result_path": str(result_path)}, ensure_ascii=False), encoding="utf-8")
    wd = _watchdog()
    watched = wd.run_watched([sys.executable, str(Path(__file__).resolve()), "--child", str(spec_path)],
                             log_path=result_path.with_suffix(".log"), config=wd.load_config(_criteria()), cwd=str(REPO))
    if watched.status == wd.STALLED or watched.returncode != 0 or not result_path.is_file():
        return {"status": "failed", "watch_status": watched.status, "swap_growth_max_mb": watched.swap_growth_max_mb,
                "reason": f"{watched.status}（{watched.reason}；rc={watched.returncode}；{watched.wall_seconds:.0f} 秒；"
                          f"見 {result_path.with_suffix('.log')}）"}
    out = json.loads(result_path.read_text(encoding="utf-8"))
    out["swap_growth_max_mb"] = watched.swap_growth_max_mb
    return out


def assemble(plan: Sequence[Mapping[str, Any]], frozen: Mapping[str, Any],
             generated: Mapping[Tuple[str, str], Mapping[str, Any]]) -> Dict[str, Any]:
    """依判準之 (格, 環境) 計畫組收據之 `cells`／`runs`／`checks`（純函式）：generations＝0 ⇒ 紀錄取自凍結 `l2_capture`
    （缺 ⇒ 該臂錯誤）；generations＝1 ⇒ 取自 `generated`，且凍結已有同 (格, 環境) 之紀錄 ⇒ 違規（不得重生已凍結者）。"""
    arms_by_cell: Dict[str, Dict[str, Dict[str, Any]]] = {}
    runs: List[Dict[str, Any]] = []
    checks: Dict[str, bool] = {}
    for item in plan:
        cid, env = str(item["cell"]), dict(item["env"])
        key = env_key(env)
        frozen_records = (frozen.get(cid) or {}).get(key)
        if item["generations"] == 0:
            records, source, status = list(frozen_records or []), "freeze_baseline", "frozen" if frozen_records else "missing"
            seconds = 0.0
        else:
            checks[f"{cid}.{key}.not_regenerating_frozen"] = frozen_records is None
            got = generated.get((cid, key)) or {"status": "not_run"}
            records, source, status = list(got.get("l2_capture") or []), "generated", str(got.get("status"))
            seconds = float(got.get("seconds") or 0.0)
        arm = summarize_arm(records)
        arm.update(source=source, run_status=status, env=env)
        if item["generations"] and status != "complete":
            arm["errors"].append({"category": "*generation*", "error": f"另行生成未完成：{status}"})
            arm["f32diff"] = None
        arms_by_cell.setdefault(cid, {})[key] = arm
        checks[f"{cid}.{key}.no_errors"] = not arm["errors"]  # 審碼 r29：任一臂有錯誤 ⇒ 收據 rc≠0（fail-closed）
        runs.append({"cell": cid, "env": env, "generations": item["generations"], "source": source, "status": status,
                     "seconds": seconds, "covers": item.get("covers")})
    cells = [build_cell(_cell(cid), arms) for cid, arms in arms_by_cell.items()]
    for cell in cells:
        if cell["only_category"] and not cell["blacklist_applied"]:  # 審碼 r29：schema 1 spy 未套 cascade blacklist
            cell["only_category_note"] = ("凍結時之 spy 未套 cascade blacklist（feature_factory.py:1771）重算公開類別表，"
                                          "`only_category` 為黑名單 L1 欄之衍生欄（spy 假象，非兩臂差）；共同欄之差不受影響")
        if cell["kind"] == "B":  # 審碼 r29：多週期之非主週期 L2 於並行子行程計算、主行程 spy 不擷取（量測限制，具名）
            cell["coverage_note"] = ("主行程只擷取主週期之 L2（各臂 main_rows）；非主週期於並行 spawn 子行程計算未擷取——"
                                     "子行程與主行程同呼叫 `_execute_layer1_6_preserve_dtype('Layer 2', _layer2_derived_features, …)`"
                                     "（multi_tf_generator.py:1474-1481 對 :1833-1840），同一程式路徑，依路徑覆蓋不另生成")
    repro = next((c for c in cells if c["cell_id"] == REPRO_CELL), None)
    checks["repro_btc_12h_f32diff_zero"] = bool(repro) and not repro["errors"] and repro["f32diff"] == 0
    checks["all_runs_available"] = all(r["status"] in ("frozen", "complete") for r in runs)
    return {"cells": cells, "runs": runs, "checks": checks}


def _parse(argv: Optional[Sequence[str]]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="NUMVIEW Task 1.3 L2 兩臂矩陣")
    parser.add_argument("--out", default=None, help="收據輸出路徑（未給 ⇒ 正式收據 handoffs/run_receipts/<date>-numview-l2-arm-matrix.json）")
    parser.add_argument("--work-root", default=str(DEFAULT_WORK_ROOT))
    parser.add_argument("--child", default=None, help=argparse.SUPPRESS)
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """量測主入口；rc 0＝收據寫出且檢查全過（BTCUSDT 12h 重現 f32diff=0、各 (格, 環境) 紀錄可得、未重生已凍結者）。"""
    args = _parse(argv)
    if args.child:
        return _child(Path(args.child))
    criteria = _criteria()
    plan = planned_runs(criteria)
    cells = sorted({p["cell"] for p in plan})
    _gate().require(RUN_KIND, cells, receipts_dir=RECEIPTS_DIR)  # 一切生成之前（Task 0.4）
    frozen, freeze_name = _freeze_capture()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    work_root = Path(args.work_root) / stamp
    generated: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for item in plan:
        if item["generations"]:
            if (frozen.get(item["cell"]) or {}).get(env_key(item["env"])) is not None:
                _log(f"{item['cell']} {env_key(item['env'])}：凍結已有紀錄，不重生")
                continue
            _log(f"生成 {item['cell']} {env_key(item['env'])}")
            generated[(item["cell"], env_key(item["env"]))] = _generate(item["cell"], item["env"], work_root)
            got = generated[(item["cell"], env_key(item["env"]))]
            _log(f"{item['cell']} {env_key(item['env'])}：{got.get('status')}，{float(got.get('seconds') or 0):.1f} 秒")
    body = assemble(plan, frozen, generated)
    receipt = {"schema_version": 1, "generated_at": datetime.now(timezone.utc).isoformat(),
               "head": subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(REPO), capture_output=True, text=True).stdout.strip(),
               "command": " ".join(["venv/bin/python", "handoffs/run_receipts/numview_probes/l2_arm_matrix.py",
                                    *(list(argv) if argv is not None else sys.argv[1:])]),
               "criteria_sha256": hashlib.sha256(_criteria_path().read_bytes()).hexdigest(),
               "freeze_receipt": freeze_name, "work_root": str(work_root),
               "memory": {f"{c}__{k}": {"swap_growth_max_mb": g.get("swap_growth_max_mb")} for (c, k), g in generated.items()},
               **body}
    receipt["exit_code"] = 0 if all(receipt["checks"].values()) else 3
    dest = Path(args.out) if args.out else RECEIPTS_DIR / f"{datetime.now().strftime('%Y%m%d')}-numview-l2-arm-matrix.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(receipt, ensure_ascii=False, indent=1, default=str) + "\n", encoding="utf-8")
    _log(f"收據 {dest}；檢查 {receipt['checks']}")
    return int(receipt["exit_code"])


if __name__ == "__main__":
    import sys

    sys.exit(main(sys.argv[1:]))
