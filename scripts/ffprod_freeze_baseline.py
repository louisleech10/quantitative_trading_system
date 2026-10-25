#!/usr/bin/env python3
"""FFPROD Task 0.2：改前基準凍結（SPEC `docs/FFPROD_SPEC.md` §G、Task 0.2）。

格＝覆蓋獨有分支之最少集合（A 單週期 1h〔宿主格，兼 fracdiff／ADF 開與 L2.polars〕、A 12h、B 多週期 1h＋4h、C 全特徵 1h、
A 1h sigma 縮尾、A 1h 之 L2 pandas 串列／平行兩臂）；格類 A／B／C 之設定覆寫、輸出段、K 線來源與連續性沿 NUMVIEW 判準檔
（`tests/_golden/numview/preregistered_criteria_v9.json`，經 `numview_helpers.current_criteria_path`）與其估時器函式。
生成一律 `FeatureFactory.generate_features`（只凍特徵生產層之 raw 成品；不跑 IC-first），每格於子行程經 NUMVIEW 卡住監看
（`handoffs/run_receipts/numview_probes/_watchdog.py`）執行、生成環境清除影響值環境變數後只套該格 `env`
（`scripts/numview_freeze_baseline.py` 之 `_isolated`）。值指紋＝`tests/feature_engineering/numview_helpers.py` 之
`fingerprints(run_dir, "raw")`；L2 格以 spy 記 `FeatureFactory._budget_check_l2` 之回傳臂，不等於宣告臂 ⇒ 拒寫該格。

用法：`venv/bin/python scripts/ffprod_freeze_baseline.py --estimate`（只估時）；無旗標 ⇒ 凍結全部格至 `GOLDEN_PATH`。
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
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Set

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

GOLDEN_PATH = REPO / "tests" / "_golden" / "ffprod" / "pre_change_fingerprints.json"
DECISIONS_PATH = REPO / "tests" / "_golden" / "ffprod" / "decisions.json"
RECEIPTS_DIR = REPO / "handoffs" / "run_receipts"
INVENTORY_GLOB = "*-ffprod-inventory.json"
PROBES_DIR = RECEIPTS_DIR / "numview_probes"
NUMVIEW_ESTIMATE_RECEIPT = RECEIPTS_DIR / "20261023-numview-estimate.json"
DEFAULT_WORK_ROOT = Path(os.environ.get("TMPDIR", "/tmp")) / "ffprod-freeze"

#: L2 三條生產臂（`FeatureFactory._budget_check_l2` 之回傳值）與各格之環境覆寫（SPEC Task 0.2）。
L2_ARM_ENV: Dict[str, Dict[str, str]] = {
    "L2.polars": {},
    "L2.pandas_serial": {"FFACT_USE_POLARS": "0", "FFACT_L2_CATEGORY_WORKERS": "1"},
    "L2.pandas_parallel": {"FFACT_USE_POLARS": "0", "FFACT_L2_CATEGORY_WORKERS": "2"},
}

#: §G 逐位元比對鍵（同 `numview_helpers.BITWISE_COLUMN_KEYS`）。
BITWISE_KEYS = ("dtype", "nan", "values_native")

#: 生成身分必備鍵（SPEC Task 0.2：HEAD、設定、資料集 sha256）。
IDENTITY_KEYS = ("head", "config_sha256", "dataset_sha256")

BLOCKED_BY_HARDWARE = "hardware"

#: 格描述子（id、格類、標的、週期〔首為主週期〕、環境、設定變體〔深合併於格類設定覆寫之上〕、覆蓋標記、宣告臂）。
_CELL_SPECS: List[Dict[str, Any]] = [
    {"id": "A_BTCUSDT_1h", "kind": "A", "symbol": "BTCUSDT", "timeframes": ["1h"], "env": {}, "variant": {},
     "covers": ["A_1h", "fracdiff_adf", "L2.polars"], "declared_arm": "L2.polars"},
    {"id": "A_BTCUSDT_12h", "kind": "A", "symbol": "BTCUSDT", "timeframes": ["12h"], "env": {}, "variant": {},
     "covers": ["A_12h"]},
    {"id": "B_BTCUSDT_1h_4h", "kind": "B", "symbol": "BTCUSDT", "timeframes": ["1h", "4h"], "env": {}, "variant": {},
     "covers": ["B_1h_4h"]},
    {"id": "C_BTCUSDT_1h", "kind": "C", "symbol": "BTCUSDT", "timeframes": ["1h"], "env": {}, "variant": {},
     "covers": ["C_1h"]},
    {"id": "A_BTCUSDT_1h__winsor_sigma", "kind": "A", "symbol": "BTCUSDT", "timeframes": ["1h"], "env": {},
     "variant": {"preprocessing": {"winsorization": {"method": "sigma"}}}, "covers": ["A_1h", "winsor_sigma"]},
    {"id": "A_BTCUSDT_1h__l2_pandas_serial", "kind": "A", "symbol": "BTCUSDT", "timeframes": ["1h"],
     "env": dict(L2_ARM_ENV["L2.pandas_serial"]), "variant": {}, "covers": ["A_1h", "L2.pandas_serial"],
     "declared_arm": "L2.pandas_serial"},
    {"id": "A_BTCUSDT_1h__l2_pandas_parallel", "kind": "A", "symbol": "BTCUSDT", "timeframes": ["1h"],
     "env": dict(L2_ARM_ENV["L2.pandas_parallel"]), "variant": {}, "covers": ["A_1h", "L2.pandas_parallel"],
     "declared_arm": "L2.pandas_parallel"},
]


class ArmMismatch(RuntimeError):
    """L2 格以 spy 觀測之 `_budget_check_l2` 回傳臂不等於該格宣告之臂 ⇒ 凍結拒寫該格（SPEC Task 0.2）。"""


# ---------------------------------------------------------------------------------------------- 載入（NUMVIEW 判準與工具）

def _load(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    if name in sys.modules:
        return sys.modules[name]
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # dataclass 定義於載入期需自模組表取得命名空間
    spec.loader.exec_module(module)
    return module


def _estimator() -> Any:
    return _load("ffprod_numview_estimate", PROBES_DIR / "estimate.py")


def _watchdog() -> Any:
    return _load("ffprod_numview_watchdog", PROBES_DIR / "_watchdog.py")


def _numview_freeze() -> Any:
    return _load("ffprod_numview_freeze", REPO / "scripts" / "numview_freeze_baseline.py")


def _criteria() -> Dict[str, Any]:
    from tests.feature_engineering import numview_helpers as nh

    return json.loads(nh.current_criteria_path().read_text(encoding="utf-8"))


def _deep_merge(base: Mapping[str, Any], extra: Mapping[str, Any]) -> Dict[str, Any]:
    out = copy.deepcopy(dict(base))
    for key, value in extra.items():
        if isinstance(value, Mapping) and isinstance(out.get(key), Mapping):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = copy.deepcopy(value)
    return out


def cell_payload(cell: Mapping[str, Any]) -> Dict[str, Any]:
    """格之設定覆寫＝NUMVIEW 判準之格類 `config_override`（主週期與訓練週期依格描述子）深合併本格變體。"""
    est, criteria = _estimator(), _criteria()
    base = est.cell_payload(cell, criteria, [str(t) for t in cell["timeframes"]])
    return _deep_merge(base, cell.get("variant") or {})


def _effective_preprocessing(payload: Mapping[str, Any]) -> Dict[str, Any]:
    """設定覆寫經 `FactoryConfig` 解析後之前處理有效值（縮尾 method、fracdiff／ADF 開關），供覆蓋判準。"""
    from momentum.factories import create_feature_factory

    config = create_feature_factory(validate_continuity=False)._resolve_config(dict(payload))
    pre = config.preprocessing.model_dump()
    return {"winsorization": {"method": str(pre["winsorization"]["method"]),
                              "enabled": bool(pre["winsorization"]["enabled"])},
            "fractional_differencing": bool(pre["fractional_differencing"]["enabled"]),
            "adf_differencing": bool(pre["adf_differencing"]["enabled"])}


def cells() -> List[Dict[str, Any]]:
    """回傳凍結格清單（每格含 `id`、`kind`、`symbol`、`timeframes`、`env`、`preprocessing`〔`winsorization.method`、
    `fractional_differencing`、`adf_differencing` 之有效值〕、`covers`〔該格獨有覆蓋之路徑標記；每個標記須滿足
    `test_ffprod_gate.COVERAGE_PREDICATES` 之結構判準，全部格須涵蓋 `REQUIRED_COVERAGE`〕；L2 格另含 `declared_arm`
    〔亦列入 `covers`，`env` 含 `L2_ARM_ENV` 該臂〕）。凍結 CLI 與重生對照皆用本清單。"""
    out = []
    for spec in _CELL_SPECS:
        cell = copy.deepcopy(spec)
        cell["preprocessing"] = _effective_preprocessing(cell_payload(cell))
        out.append(cell)
    return out


# ---------------------------------------------------------------------------------------------- 凍結與對照

def _write_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    staging = path.with_suffix(path.suffix + ".tmp")
    staging.write_text(json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=True, default=str) + "\n",
                       encoding="utf-8")
    os.replace(staging, path)


def freeze_cells(cell_list: Sequence[Mapping[str, Any]], out_path: Path, *,
                 generate: Callable[[Mapping[str, Any]], Dict[str, Any]]) -> Dict[str, Any]:
    """逐格呼叫 `generate(cell)`（回傳 {"fingerprints": ..., "identity": ..., "observed_arm": 可缺}），每完成一格即原子寫入
    `out_path`。邊界①：中途例外 ⇒ 已完成格保留、未完成格不寫入、例外上拋。邊界②：
    `GenerationMemoryBudgetExceeded` ⇒ 該格記 {"status": "blocked", "blocked_by": "hardware"} 並續下一格。
    L2 格之 `observed_arm` ≠ `declared_arm` ⇒ 拋 `ArmMismatch`、該格不寫入。生成身分缺 `IDENTITY_KEYS` 任一 ⇒
    `ValueError`、該格不寫入。回傳寫入之全部格。"""
    from momentum.FeatureEngineering.memory_budget import GenerationMemoryBudgetExceeded

    written: Dict[str, Any] = {}
    listed: List[Dict[str, Any]] = []
    for cell in cell_list:
        cell_id = str(cell["id"])
        try:
            result = generate(cell)
        except GenerationMemoryBudgetExceeded:
            written[cell_id] = {"status": "blocked", "blocked_by": BLOCKED_BY_HARDWARE}
            listed.append(dict(cell))
            _write_atomic(out_path, {"cell_list": listed, "cells": written})
            continue
        identity = dict(result.get("identity") or {})
        missing = [key for key in IDENTITY_KEYS if not identity.get(key)]
        if missing:
            raise ValueError(f"{cell_id}：生成身分缺 {missing}")
        declared = cell.get("declared_arm")
        if declared is not None and result.get("observed_arm") != declared:
            raise ArmMismatch(f"{cell_id}：宣告 {declared}，實際 {result.get('observed_arm')!r}")
        entry: Dict[str, Any] = {"status": "frozen", "fingerprints": result["fingerprints"], "identity": identity}
        if "observed_arm" in result:
            entry["observed_arm"] = result["observed_arm"]
        written[cell_id] = entry
        listed.append(dict(cell))
        _write_atomic(out_path, {"cell_list": listed, "cells": written})
    return written


def compare(frozen: Mapping[str, Any], actual: Mapping[str, Any], changed_targets: Set[str]) -> List[str]:
    """§G 對照：回傳不符描述清單（空＝通過）。欄集合或欄序不同、非 `changed_targets` 之欄任一 `BITWISE_KEYS` 不等、
    `changed_targets` 之欄實際未改（少一欄）皆為不符。`frozen`／`actual` 為 `fingerprints` 之輸出。"""
    out: List[str] = []
    if changed_targets and frozen.get("granularity") == "group":
        # 群組粒度（全特徵格 C）之 columns 鍵為群組檔、非欄名：逐欄核可之對照須群組→欄映射，依 Task 2.2 裁定於 Phase 3
        # 重凍時具體化（SPEC Task 3.x）；在此之前一律拒判，不以群組鍵比對欄名
        return [f"群組粒度格不支援逐欄 changed_targets 對照（{len(changed_targets)} 欄待 Phase 3 具體化）"]
    unknown = sorted(set(changed_targets) - set(frozen.get("columns", {})))
    if unknown:
        out.append(f"changed_targets 含凍結值中不存在之欄：{unknown[:5]}")
    for key in ("column_set_sha256", "column_order_sha256"):
        if frozen.get(key) != actual.get(key):
            out.append(f"{key} 不同")
    if out:
        return out
    frozen_cols, actual_cols = frozen["columns"], actual["columns"]
    for name in sorted(frozen_cols):
        diff = [k for k in BITWISE_KEYS if frozen_cols[name].get(k) != actual_cols.get(name, {}).get(k)]
        if name in changed_targets:
            if not diff and BITWISE_KEYS:
                out.append(f"{name}：核可改值而實際未改")
        elif diff:
            out.append(f"{name}：{diff} 不同")
    return out


# ---------------------------------------------------------------------------------------------- 生成（子行程）

def _git_head() -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(REPO), capture_output=True, text=True,
                          check=True).stdout.strip()


def _identity(cell: Mapping[str, Any], payload: Mapping[str, Any]) -> Dict[str, Any]:
    from tests.feature_engineering import numview_helpers as nh

    datasets = nh.cell_dataset_records(cell)
    config_doc = {"payload": payload, "env": dict(cell.get("env") or {})}
    return {"head": _git_head(),
            "config_sha256": hashlib.sha256(json.dumps(config_doc, sort_keys=True, ensure_ascii=False,
                                                       default=str).encode("utf-8")).hexdigest(),
            "dataset_sha256": hashlib.sha256(json.dumps(datasets, sort_keys=True).encode("utf-8")).hexdigest(),
            "datasets": datasets}


def cell_fingerprints(cell: Mapping[str, Any], run_dir: Path) -> Dict[str, Any]:
    """§G 值指紋：格類屬 `numview_helpers.GROUP_GRANULARITY_KINDS`（全特徵格 C，約 20.9 萬欄；逐欄指紋使基準檔約 100 MB、
    逾版控單檔上限）⇒ 群組粒度 `group_fingerprints`（任一欄之值、NaN、dtype、欄名或欄序改變 ⇒ 所屬群組或表層雜湊改變），
    否則逐欄 `fingerprints`。"""
    from tests.feature_engineering import numview_helpers as nh

    if str(cell["kind"]) in nh.GROUP_GRANULARITY_KINDS:
        return nh.group_fingerprints(Path(run_dir), "raw")
    return nh.fingerprints(Path(run_dir), "raw")


def _generate_in_process(cell: Mapping[str, Any], work: Path) -> Dict[str, Any]:
    """子行程內：隔離環境生成一格（`generate_features`、輸出段與連續性依 NUMVIEW 判準），回傳結果 dict。"""
    from momentum.factories import create_feature_factory
    from momentum.FeatureEngineering.feature_factory import FeatureFactory
    from momentum.FeatureEngineering.feature_storage import FeatureStorage
    from tests.feature_engineering import numview_helpers as nh

    est, criteria, nf = _estimator(), _criteria(), _numview_freeze()
    payload = cell_payload(cell)
    training = [str(t) for t in cell["timeframes"]]
    symbol, primary = str(cell["symbol"]), training[0]
    source = est.cell_source(cell, criteria)
    start, end = est.cell_window(cell, criteria)
    continuity = est.continuity_plan(cell, criteria, training)
    gaps = est.window_gap_violations(continuity, start)
    if gaps:
        raise RuntimeError(f"{cell['id']}：輸出段內有 K 線缺口：{gaps}")
    arms: List[str] = []
    real_check = FeatureFactory._budget_check_l2

    def spy(self: Any, *args: Any, **kwargs: Any) -> str:
        arm = real_check(self, *args, **kwargs)
        arms.append(str(arm))
        return arm

    started = time.perf_counter()
    with nf._isolated(work, dict(cell.get("env") or {})) as features_root:
        factory = create_feature_factory(cache_dir=str(source.parent),
                                         validate_continuity=continuity["validate_continuity"])
        factory._storage = FeatureStorage(str(features_root))
        FeatureFactory._budget_check_l2 = spy  # type: ignore[assignment]
        try:
            factory.generate_features(symbol, primary, config_override=payload, force_regenerate=True,
                                      persist=True, start_date=start, end_date=end)
        finally:
            FeatureFactory._budget_check_l2 = real_check  # type: ignore[assignment]
        verdict = est.classify_generated_run(features_root, symbol, primary, criteria)
        manifests = sorted((Path(features_root) / symbol / primary).glob("*/feature_manifest.json"))
        if verdict.get("status") != "complete" or len(manifests) != 1:
            raise RuntimeError(f"{cell['id']}：run 非 complete 或 manifest 數 ≠ 1：{verdict}")
        fingerprints = cell_fingerprints(cell, manifests[0].parent)
    result: Dict[str, Any] = {"fingerprints": fingerprints, "identity": _identity(cell, payload),
                              "seconds": time.perf_counter() - started, "output_window": [start, end],
                              "observed_arms": arms}
    distinct = sorted(set(arms))
    if distinct:
        result["observed_arm"] = distinct[0] if len(distinct) == 1 else distinct
    return result


def _child(spec_path: Path) -> int:
    """子行程入口：生成一格、寫結果檔；記憶體守護具名終止 ⇒ status＝blocked（hardware）。"""
    spec = json.loads(Path(spec_path).read_text(encoding="utf-8"))
    try:
        result = _generate_in_process(spec["cell"], Path(spec["work"]))
        result["status"] = "ok"
    except BaseException as exc:  # noqa: BLE001 — 失敗型別決定 blocked（硬體）或 failed，皆寫結果
        result = {"status": "blocked" if _estimator()._is_memory_guard(exc) else "failed",
                  "error": f"{type(exc).__name__}: {exc}"[:2000]}
    _write_atomic(Path(spec["result_path"]), result)
    return 0 if result["status"] in ("ok", "blocked") else 3


def _run_watched(cell: Mapping[str, Any], work_root: Path) -> Dict[str, Any]:
    """主行程：以子行程經 NUMVIEW 卡住監看生成一格；blocked ⇒ 拋 `GenerationMemoryBudgetExceeded`（供 `freeze_cells` 標
    blocked）；卡住或失敗 ⇒ RuntimeError。"""
    from momentum.FeatureEngineering.memory_budget import GenerationMemoryBudgetExceeded

    wd = _watchdog()
    cell_dir = Path(work_root) / str(cell["id"])
    cell_dir.mkdir(parents=True, exist_ok=True)
    result_path = cell_dir / "result.json"
    result_path.unlink(missing_ok=True)
    spec_path = cell_dir / "spec.json"
    _write_atomic(spec_path, {"cell": dict(cell), "work": str(cell_dir / "work"), "result_path": str(result_path)})
    expected = estimate([cell])["cells"].get(str(cell["id"]))
    print(f"[ffprod-freeze] {cell['id']}：子行程開始（預期 {expected} 秒）", flush=True)
    watched = wd.run_watched([sys.executable, str(Path(__file__).resolve()), "--child", str(spec_path)],
                             log_path=cell_dir / "child.log", config=wd.load_config(_criteria()),
                             expected_seconds=expected, cwd=str(REPO))
    if watched.status == wd.STALLED or not result_path.is_file():
        raise RuntimeError(f"{cell['id']}：{watched.status}（{watched.reason}；rc={watched.returncode}；"
                           f"見 {cell_dir / 'child.log'}）")
    result = json.loads(result_path.read_text(encoding="utf-8"))
    if result["status"] == "blocked":
        raise GenerationMemoryBudgetExceeded(str(cell["id"]), 0, 0, 0, result.get("error", "記憶體守護終止"))
    if result["status"] != "ok":
        raise RuntimeError(f"{cell['id']}：生成失敗 {result.get('error')}")
    print(f"[ffprod-freeze] {cell['id']}：完成（{result.get('seconds', 0):.0f} 秒；臂 {result.get('observed_arm')}）",
          flush=True)
    return result


def regenerate(cell: Mapping[str, Any]) -> Dict[str, Any]:
    """以現行 HEAD 重生成一格並回傳其值指紋（同 `freeze_cells` 之 `generate` 回傳格式）。"""
    return _run_watched(cell, DEFAULT_WORK_ROOT / "regen")


def estimate(cell_list: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    """逐格估計生成秒數（依既有實測收據或單格試跑），回傳 {"cells": {格 id: 秒數}, "total_seconds": 合計}；不生成特徵、
    不寫 `GOLDEN_PATH`。估值取 NUMVIEW 估時收據（`20261023-numview-estimate.json`）同格類同標的同週期之實測生成秒數
    （該收據之 A／B 含 IC-first，故為上界）；變體格取其宿主格之值。"""
    receipt = json.loads(NUMVIEW_ESTIMATE_RECEIPT.read_text(encoding="utf-8"))
    measured: Dict[str, float] = {}

    def walk(node: Any) -> None:
        if isinstance(node, Mapping):
            if "cell_id" in node and isinstance(node.get("seconds"), (int, float)):
                measured.setdefault(str(node["cell_id"]), float(node["seconds"]))
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(receipt)
    out: Dict[str, float] = {}
    for cell in cell_list:
        base = f"{cell['kind']}_{cell['symbol']}_{'_'.join(str(t) for t in cell['timeframes'])}"
        out[str(cell["id"])] = measured.get(base, measured.get(str(cell["id"]), float("nan")))
    return {"cells": out, "total_seconds": float(sum(v for v in out.values() if v == v)), "source": str(NUMVIEW_ESTIMATE_RECEIPT)}


def main(argv: Optional[Sequence[str]] = None) -> int:
    """CLI：`--estimate` 只呼叫 `estimate(cells())` 並印出結果（>30 分先白話告知使用者），不呼叫 `freeze_cells`、
    不寫 `GOLDEN_PATH`；無旗標 ⇒ `freeze_cells(cells(), GOLDEN_PATH, generate=...)`。"""
    parser = argparse.ArgumentParser(description="FFPROD 改前基準凍結（SPEC Task 0.2）")
    parser.add_argument("--estimate", action="store_true", help="只估時，不生成、不寫基準")
    parser.add_argument("--work-root", default=str(DEFAULT_WORK_ROOT / "freeze"))
    parser.add_argument("--child", default=None, help=argparse.SUPPRESS)
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.child:
        return _child(Path(args.child))
    cell_list = cells()
    if args.estimate:
        print(json.dumps(estimate(cell_list), ensure_ascii=False, indent=1))
        return 0
    work_root = Path(args.work_root)
    freeze_cells(cell_list, GOLDEN_PATH, generate=lambda cell: _run_watched(cell, work_root))
    print(f"[ffprod-freeze] 寫入 {GOLDEN_PATH}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
