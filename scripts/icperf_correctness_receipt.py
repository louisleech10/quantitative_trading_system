"""ICPERF Task 0.3：現行 IC 正確性之真實資料收據（docs/ICPERF_SPEC.md Task 0.3；§B ICPERF-BUDGET-7、-9、-10、-11）。

做法（逐請求、端到端）：每一請求於子行程（共用監看）以凍結腳本之同一產品路徑執行（`icperf_freeze_baseline` 之
`default_request`／`_ic_page_analyze`／`event_import_run`／深度分析步驟），並擷取產品實際所用之輸入——分析器快取
（`ICFilterOrchestrator._ic_cache`：第 1 段後之特徵、標籤、收盤、metadata、切分）、第 5 段實際輸入對
（`_stage5_input_spy`）與有效設定；母行程以獨立參考實作（`tests/momentum/Analysis/test_icperf_correctness.py` 與
`test_icperf_deep_*.py` 之 `_ref_*`／`compare_*`，皆不呼叫被測碼）自上列輸入重算回應之每一統計欄位逐值對照，另以真實
kline 獨立重建標籤、以切分參考實作重建訓練／測試段，驗產品輸入本身。

收據 `handoffs/run_receipts/<日期>-icperf-correctness.json`（形狀見 `build_receipt`）。逐請求封閉（SPEC v5.26 r40）：每一
請求之實際回應涵蓋鍵集合 == 該請求 coverage 鍵集合；每鍵狀態 verified／verified-na／unimplemented／metadata-missing／
insufficient-data，後三者存在 ⇒ 收據不 PASS。

用法（capture 為重型，列 `scripts/heavy_commands.json` 之 `icperf_correctness`：須背景、經共用監看、先寫估時收據；
`--n-features` 為小規模除錯之子集欄數上限，不改 `REQUESTS` 預設）：
  venv/bin/python scripts/icperf_correctness_receipt.py capture --out-dir <擷取目錄> [--requests <id>,...] [--n-features N]
  venv/bin/python scripts/icperf_correctness_receipt.py receipt --captures <擷取目錄> --out <收據 JSON>
receipt 只讀擷取檔（oracle 重算約 10 分鐘級，背景執行）。
"""

from __future__ import annotations

import argparse
import contextlib
import importlib.util
import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Iterator, List, Mapping, Optional, Sequence

REPO = Path(__file__).resolve().parents[1]
CHILD_CMD = "_child"
#: 特徵子集之 seed（同凍結腳本 `SEED`）
SEED = 20261027
#: 涵蓋小請求之欄數（＝`test_icperf_correctness.py` `COVERAGE_FEATURES`：§G (1)(4) 之 A 格小請求以排序後前 20 欄）
COVERAGE_FEATURES = 20
#: 逐請求之定義：凍結項（請求設定取 `default_request`）、特徵子集欄數（SPEC §B BUDGET-7：A 格小規模子集數十至數百欄；
#: L 格同）。`sorted`＝取排序後前 n 欄（同凍結腳本 `small_request`，供頂層 coverage 與 `test_correctness_coverage_closed_
#: over_response_keys` 之同一請求）；否則 seed 隨機巢狀子集。`method`＝覆寫 `global.default_method`（SPEC Task 0.3「Pearson、
#: Kendall 分支各至少一格」、BUDGET-7）。`kind="cross"`＝跨標的請求（SPEC Task 0.3 跨標的欄、BUDGET-11）。
#: 12h 長歷史格不列（SPEC v5.33 ⑪：IC 頁驗證之資料格須與產品 K 線同源，12h 長歷史格不作 IC 頁驗證格）。
REQUESTS: Dict[str, Dict[str, Any]] = {
    "A.ic_report": {"item": "ic_report", "n_features": 120},
    "A.ic_report.cov": {"item": "ic_report", "n_features": COVERAGE_FEATURES, "sorted": True},
    "A.ic_report.pearson": {"item": "ic_report", "n_features": 30, "method": "pearson"},
    "A.ic_report.kendall": {"item": "ic_report", "n_features": 30, "method": "kendall"},
    "A.event_report": {"item": "event_report", "n_features": 120},
    "A.event_report.cov": {"item": "event_report", "n_features": COVERAGE_FEATURES, "sorted": True},
    "A.deep_analysis": {"item": "deep_analysis", "n_features": 120},
    "L.ic_report": {"item": "ic_report_long", "n_features": 120},
    "L.deep_analysis": {"item": "deep_analysis_long", "n_features": 120},
    "L.event_import_report": {"item": "event_import_report", "n_features": 120},
    "X.cross_sectional": {"kind": "cross", "item": "ic_report", "cells": ["A_BTCUSDT_1h", "A_SOLUSDT_1h"],
                          "n_features": 20},
}
#: 頂層 coverage 之來源請求（§G (1)(4) 之 A 格小請求；同測試之涵蓋鍵規則）
TOP_COVERAGE_REQUESTS = ("A.ic_report.cov", "A.event_report.cov")
#: 子集欄數之覆寫（小規模除錯；不改 `REQUESTS` 預設值）
N_FEATURES_ENV = "ICPERF_T03_N_FEATURES"


def _load(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _fb() -> Any:
    return sys.modules.get("icperf_freeze_baseline_cr") or _load(
        "icperf_freeze_baseline_cr", REPO / "scripts" / "icperf_freeze_baseline.py")


def subset_names(names: Sequence[str], n: Optional[int], seed: int = SEED) -> List[str]:
    """特徵名之巢狀隨機子集：`default_rng(seed).permutation` 之前 n 個（依原順序排序）；n 為 None 或 ≥ 全數 ⇒ 全部。"""
    import numpy as np

    names = list(names)
    if n is None or n >= len(names):
        return names
    pick = np.sort(np.random.default_rng(seed).permutation(len(names))[:int(n)])
    return [names[int(i)] for i in pick]


def _n_features(spec: Mapping[str, Any]) -> Optional[int]:
    """請求之子集欄數：環境變數 `N_FEATURES_ENV` 有值 ⇒ 取 min(覆寫, 預設)（小規模除錯）；否則預設。"""
    n = spec.get("n_features")
    raw = os.environ.get(N_FEATURES_ENV)
    if raw:
        n = int(raw) if n is None else min(int(raw), int(n))
    return n


def request_for(req_id: str) -> Dict[str, Any]:
    """請求 id ⇒ 凍結腳本之預設請求加特徵子集（`feature_filter.include_features`）；`sorted` ⇒ 同凍結腳本 `small_request`；
    `method` ⇒ `config_override.global.default_method`；跨標的 ⇒ 各格之 run 與兩格共有特徵之子集。"""
    fb = _fb()
    spec = REQUESTS[req_id]
    n = _n_features(spec)
    if spec.get("kind") == "cross":
        cells = [fb.default_request(spec["item"], c) for c in spec["cells"]]
        common = sorted(set.intersection(*(set(fb._run_feature_names(r)) for r in cells)))
        names = subset_names(common, n)
        return {"kind": "cross", "item": spec["item"], "cells": cells, "timeframe": cells[0]["timeframe"],
                "config_override": cells[0]["config_override"], "feature_tiers": cells[0]["feature_tiers"],
                "feature_filter": {"include_features": names}, "receipt_request_id": req_id}
    request = fb.default_request(spec["item"], spec["cell"]) if spec.get("cell") else fb.default_request(spec["item"])
    if spec.get("sorted"):
        request = fb.small_request(spec["item"], request, int(n))
    else:
        request["feature_filter"] = {"include_features": subset_names(fb._run_feature_names(request), n)}
    if spec.get("method"):
        request["config_override"] = {**request["config_override"], "global": {"default_method": spec["method"]}}
    request["receipt_request_id"] = req_id
    return request


# ── 子行程：執行產品並擷取輸入 ───────────────────────────────────────────────────────────────────────────


def _effective_config(analyzer: Any, override: Optional[Mapping[str, Any]]) -> Any:
    """產品於該次執行之有效設定（`_apply_tier_config(_apply_config_override(override))`，同 analyze／run_deep_analysis
    之入口）之 model_dump（欄名鍵，非 alias）；設定回顯，不經任何統計計算。"""
    try:
        cfg = analyzer._apply_tier_config(analyzer._apply_config_override(dict(override) if override else None))
    except Exception:  # noqa: BLE001 — 回退記建構時設定
        cfg = getattr(analyzer, "_config", None)
    return cfg.model_dump() if hasattr(cfg, "model_dump") else None


def _peak_rss_bytes() -> int:
    """本行程之峰值常駐記憶體（`getrusage` ru_maxrss；macOS 單位 bytes、Linux 為 KiB ⇒ 乘 1024）。"""
    import resource

    v = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return v if sys.platform == "darwin" else v * 1024


def _child_cross(request: Mapping[str, Any]) -> Dict[str, Any]:
    """跨標的請求（SPEC Task 0.3 跨標的欄；服務 `_run_analysis` 之 `mode == "cross_sectional"` 分支同一步驟：逐標的讀特徵
    〔各格各自之特徵根，故逐格以該格 FeatureLibrary 之 `load_multi` 讀〕、加 `_symbol` 層、`_append_cross_sectional_labels`、
    `analyze_cross_sectional`）。特徵限縮於請求之子集（BUDGET-11 控時；產品跨標的路徑無 feature_filter）。預設設定之切分
    不成立（InvalidInputError）⇒ 記錄其訊息並以 `ic_train_test_split=False` 重跑（回應兩者皆記）。"""
    import pandas as pd

    from momentum.factories import create_ic_analyzer

    fb = _fb()
    names = list(request["feature_filter"]["include_features"])
    frames = []
    svc = None
    for i, cell in enumerate(request["cells"]):
        cs = fb._ic_service(cell, Path(request["_work"]) / f"registry_{i}.json")
        svc = svc or cs
        loaded = cs._feature_library.load_multi([cell["symbol"]], cell["timeframe"],
                                                config_hashes={cell["symbol"]: cell["config_hash"]})
        frame = loaded[cell["symbol"]][names].copy()
        frame["_symbol"] = cell["symbol"]
        frames.append(frame)
    cross_df = pd.concat(frames, axis=0).set_index("_symbol", append=True)
    cross_df = svc._append_cross_sectional_labels(cross_df, [c["symbol"] for c in request["cells"]], request["timeframe"])
    override = svc._build_config_override(fb._ic_analyze_request({**request["cells"][0], "feature_filter": None}))
    attempts = []
    report = None
    for extra in (None, {"ic_train_test_split": False}):
        ov = {**(override or {}), **(extra or {})}
        analyzer = create_ic_analyzer(ov)
        try:
            report = analyzer.analyze_cross_sectional(features=cross_df, labels_path=None, config_override=ov,
                                                      progress_callback=fb._progress, timeframe=request["timeframe"])
            attempts.append({"override_extra": extra, "ok": True})
            break
        except Exception as exc:  # noqa: BLE001 — 切分不成立之訊息入回應記錄
            attempts.append({"override_extra": extra, "ok": False, "error": f"{type(exc).__name__}: {exc}"})
    return {"response": report, "ic_report": report, "cross_df": cross_df, "attempts": attempts,
            "config": _effective_config(analyzer, ov), "analyzer": analyzer}


@contextlib.contextmanager
def _stage4_spy() -> Iterator[List[Dict[str, Any]]]:
    """暫時包住 `ICFilterOrchestrator._stage4_ic_calculation`，記錄其回傳之 `ic_values`（第 4 段 pooled 點 IC，
    `ic_filter_orchestrator.py` `_stage4_ic_calculation` 之 `compute_ic(features_for_ic, label_for_ic, method)`；summary
    `ic_mean` 之退回來源）；原樣回傳、不改值，離開時還原。"""
    import momentum.Analysis.ic_filter_orchestrator as orch

    cls = orch.ICFilterOrchestrator
    orig = cls.__dict__["_stage4_ic_calculation"]
    calls: List[Dict[str, Any]] = []

    def wrapped(self: Any, *args: Any, **kwargs: Any) -> Any:
        out = orig(self, *args, **kwargs)
        if isinstance(out, dict):
            calls.append({"ic_values": dict(out.get("ic_values") or {}), "keys": sorted(map(str, out))})
        return out

    cls._stage4_ic_calculation = wrapped
    try:
        yield calls
    finally:
        cls._stage4_ic_calculation = orig


def _child_capture(spec: Mapping[str, Any]) -> Dict[str, Any]:
    """依請求執行產品（IC 頁／深度分析／事件匯入批／跨標的），回 {"request", "response", "ic_report", "cache",
    "report_internal", "stage5_inputs", "config", "deep_config", "deep_raw", "fr_series", "selected", "survivors",
    "corr_cache", "engine", "elapsed_s", "peak_rss_bytes"}：`response`＝該凍結項之回應形狀（IC 頁＝報告；深度＝序列化
    深度報告；事件匯入批＝報告＋任務欄）、`ic_report`＝同一次 analyze 之報告、`cache`＝分析器 `_ic_cache` 全部鍵（第 1 段
    後之特徵、標籤、收盤、滾動 IC、icir 等產品實際輸入／中間結果）。"""
    import time

    from api.models.ic_models import DeepAnalysisRequest

    fb = _fb()
    t0 = time.perf_counter()
    request = spec["request"]
    registry = Path(spec["registry"])
    out: Dict[str, Any] = {"request": request, "deep_raw": None, "deep_config": None, "selected": None,
                           "fr_series": None}
    if request.get("kind") == "cross":
        res = _child_cross({**request, "_work": str(registry.parent)})
        analyzer = res.pop("analyzer")
        out.update(res)
        out.update({"cache": dict(getattr(analyzer, "_ic_cache", None) or {}), "stage5_inputs": [],
                    "report_internal": None, "survivors": None, "corr_cache": None, "engine": None})
        out.update({"elapsed_s": time.perf_counter() - t0, "peak_rss_bytes": _peak_rss_bytes()})
        return out
    with fb._stage5_input_spy(stop=False) as calls, _stage4_spy() as s4:
        if request.get("event_import_id"):
            info = fb.event_import_run(request, registry)
            analyzer = info["analyzer"]
            response = fb.event_import_response(info)
            report = info.get("result")
            svc = None
        else:
            svc, analyzer, report = fb._ic_page_analyze(request, registry)
            response = report
            if request.get("deep") is not None:
                deep_request = DeepAnalysisRequest(**request["deep"])
                deep_override = svc._build_deep_module_override(deep_request)
                selected = svc._resolve_selected_features(analyzer=analyzer,
                                                          selected_features=deep_request.selected_features,
                                                          top_n=deep_request.top_n)
                deep_report = analyzer.run_deep_analysis(selected, deep_override, fb._progress, None)
                response = svc._attach_cross_symbol_context(svc._serialize_deep_report(deep_report), analyzer)
                cfg = analyzer._apply_tier_config(analyzer._apply_config_override(deep_override))
                cfg, _ = analyzer._apply_explicit_module_requests(cfg, deep_override)
                out.update({"deep_raw": deep_report, "deep_config": cfg.model_dump(), "deep_config_obj": cfg,
                            "selected": list(selected),
                            "fr_series": dict(getattr(analyzer, "_factor_return_series", {}) or {})})
    override = None
    if svc is not None:
        override = svc._build_config_override(fb._ic_analyze_request(request))
    try:
        survivors = list(analyzer.get_filtered_features().columns)
    except Exception:  # noqa: BLE001 — 無倖存者或未產生
        survivors = None
    eng = getattr(analyzer, "_ic_engine", None)
    out.update({"response": response, "ic_report": report,
                "cache": dict(getattr(analyzer, "_ic_cache", None) or {}),
                "report_internal": getattr(analyzer, "_report", None),
                "stage5_inputs": list(calls), "stage4": list(s4), "config": _effective_config(analyzer, override),
                "survivors": survivors, "corr_cache": getattr(analyzer, "_corr_cache", None),
                "engine": None if eng is None else {"timeframe": getattr(eng, "_timeframe", None),
                                                    "reference_tf": getattr(eng, "_reference_tf", None),
                                                    "icir_window": getattr(eng, "_icir_window", None)},
                "elapsed_s": time.perf_counter() - t0, "peak_rss_bytes": _peak_rss_bytes()})
    return out


def _child_main(spec_path: Path) -> int:
    import pickle
    import traceback

    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))
    spec = json.loads(Path(spec_path).read_text(encoding="utf-8"))
    try:
        result = _child_capture(spec)
        with open(spec["out_pickle"], "wb") as fh:
            pickle.dump(result, fh, protocol=pickle.HIGHEST_PROTOCOL)
    except BaseException:  # noqa: BLE001 — 子行程任何失敗以 rc≠0 回報，堆疊進監看 log
        traceback.print_exc()
        sys.stdout.flush()
        return 3
    return 0


def capture(req_ids: Sequence[str], out_dir: Path) -> Dict[str, Any]:
    """逐請求於子行程（共用監看；隔離 cwd 與 TMPDIR）執行並擷取，寫 `out_dir/<id>.pkl`；回 {id: {"rc", "pickle", "log"}}。
    任一請求失敗 ⇒ 記錄並續跑其餘（收據將該請求記為失敗，不 PASS）。"""
    fb = _fb()
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    status: Dict[str, Any] = {}
    work_root = out_dir / "_work"
    work_root.mkdir(parents=True, exist_ok=True)
    for rid in req_ids:
        request = request_for(rid)
        work = Path(tempfile.mkdtemp(prefix=f"{rid}-", dir=str(work_root)))
        cap = work / "capture"
        cap.mkdir(parents=True)
        out = out_dir / f"{rid}.pkl"
        out.unlink(missing_ok=True)
        spec = {"request": request, "registry": str(cap / "registry.json"), "out_pickle": str(out)}
        spec_path = cap / "spec.json"
        spec_path.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
        cmd = [sys.executable, str(Path(__file__).resolve()), CHILD_CMD, str(spec_path)]
        t0 = time.perf_counter()
        try:
            res = fb.run_watched(cmd, log_path=cap / "run.log",
                                 env=fb.isolated_env(fb._child_env_base(), work / "iso"),
                                 cwd=fb._prepare_cwd(work / "cwd"))
            status[rid] = {"rc": res["rc"], "pickle": str(out) if out.is_file() else None, "log": res["log_path"]}
        except fb.FreezeError as exc:
            status[rid] = {"rc": None, "pickle": None, "log": str(cap / "run.log"), "error": str(exc)}
        status[rid]["wall_s"] = time.perf_counter() - t0
        status[rid]["pickle_bytes"] = out.stat().st_size if out.is_file() else None
        print(json.dumps({"request": rid, **status[rid]}, ensure_ascii=False), flush=True)
    (out_dir / "capture_status.json").write_text(json.dumps(status, ensure_ascii=False, indent=1), encoding="utf-8")
    return status


# ── oracle 對照（母行程；oracle 取自測試檔之參考實作，皆不呼叫被測碼） ───────────────────────────────────────

ORACLE_TEST = REPO / "tests" / "momentum" / "Analysis" / "test_icperf_correctness.py"
KLINE_H5 = REPO / "data_cache" / "feature_klines" / "kline_cache.h5"
REL_TOL = 1e-12


def _oracles() -> Any:
    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))
    return sys.modules.get("icperf_oracles_cr") or _load("icperf_oracles_cr", ORACLE_TEST)


def _is_informative(v: Any) -> bool:
    """值是否「有內容」（資料充足判準）：有限數、非空字串／容器、bool；None、NaN、空容器 ⇒ False。"""
    import math

    import numpy as np

    if v is None:
        return False
    if isinstance(v, (bool, np.bool_)):
        return True
    if isinstance(v, (int, float, np.integer, np.floating)):
        return math.isfinite(float(v))
    if isinstance(v, (str, list, tuple, dict)):
        return len(v) > 0
    return True


#: 目前對照之回應是否經服務 JSON 化（NaN ⇒ null；事件匯入批之任務結果）
NULL_IS_NAN: Dict[str, bool] = {"on": False}


class Tally:
    """一個 oracle 項之逐值對照累計：比較數、有限值數、最大相對誤差、不一致之前若干例；另逐涵蓋鍵記
    [比較數, 有內容之比較數, 不一致數]（收據 coverage 之 verified／verified-na／insufficient-data 依此判）。"""

    def __init__(self, oracle: str) -> None:
        self.oracle, self.n, self.n_finite, self.max_rel = oracle, 0, 0, 0.0
        self.mismatch: List[Dict[str, Any]] = []
        self.n_mismatch = 0
        self.notes: List[str] = []
        self.keys: Dict[str, List[int]] = {}
        self.features: set = set()
        self.na_proofs: Dict[str, str] = {}

    def _key(self, key: str, informative: bool, miss: bool) -> None:
        rec = self.keys.setdefault(key, [0, 0, 0])
        rec[0] += 1
        rec[1] += int(informative)
        rec[2] += int(miss)

    def num(self, key: str, where: str, prod: Any, orc: Any, tol: float = REL_TOL,
            feature: Optional[str] = None) -> None:
        """浮點對照：相對誤差（oracle 為 0 ⇒ 絕對誤差）≤ tol 為一致；NaN＝NaN、None＝None。"""
        import math

        self.n += 1
        p, o = _f(prod), _f(orc)
        if p is None or o is None:
            ok = (prod is None and orc is None) or (p is None and o is None and _canon(prod) == _canon(orc))
            if not ok and NULL_IS_NAN["on"]:
                # 經服務 JSON 化之回應（事件匯入批任務結果）以 null 表 NaN：null 與 NaN 視為同值
                ok = (prod is None and o is not None and math.isnan(o)) or (orc is None and p is not None and math.isnan(p))
            d = 0.0 if ok else math.inf
        elif math.isnan(p) and math.isnan(o):
            d = 0.0
        elif math.isnan(p) or math.isnan(o):
            d = math.inf
        elif math.isinf(p) or math.isinf(o):
            d = 0.0 if p == o else math.inf
        else:
            d = abs(p - o) / abs(o) if o != 0 else abs(p - o)
        info = p is not None and o is not None and math.isfinite(p) and math.isfinite(o)
        self.n_finite += int(info)
        self.max_rel = max(self.max_rel, d) if math.isfinite(d) else math.inf
        miss = d > tol
        self._key(key, info, miss)
        if miss:
            self._miss(where, prod, orc, feature)

    def eq(self, key: str, where: str, prod: Any, orc: Any, feature: Optional[str] = None) -> None:
        """精確對照（正準 JSON 相等；整數、字串、bool、None、名單）。"""
        self.n += 1
        info = _is_informative(prod)
        self.n_finite += int(info)
        miss = _canon(prod) != _canon(orc)
        self._key(key, info, miss)
        if miss:
            self._miss(where, prod, orc, feature)

    def na(self, key: str, proof: str) -> None:
        """該鍵於此輸入依定義為 NaN／空／None，並以明列邊界輸入另證（`proof`＝本檔綁定之測試名）⇒ verified-na。"""
        self.na_proofs[key] = proof

    def _miss(self, where: str, prod: Any, orc: Any, feature: Optional[str]) -> None:
        self.n_mismatch += 1
        if feature is not None:
            self.features.add(str(feature))
        if len(self.mismatch) < 12:
            self.mismatch.append({"where": where, "product": _short(prod), "oracle": _short(orc)})

    def record(self) -> Dict[str, Any]:
        import math

        verdict = "未驗" if self.n == 0 else ("一致" if self.n_mismatch == 0 else "不一致")
        return {"verdict": verdict, "oracle": self.oracle, "n_compared": self.n, "n_finite": self.n_finite,
                "n_mismatch": self.n_mismatch, "max_rel_diff": None if not math.isfinite(self.max_rel) else self.max_rel,
                "examples": self.mismatch, "mismatch_features": sorted(self.features)[:50],
                "n_mismatch_features": len(self.features), "notes": self.notes[:20],
                "keys": {k: {"n": v[0], "n_informative": v[1], "n_mismatch": v[2]} for k, v in sorted(self.keys.items())},
                "na_proofs": dict(self.na_proofs)}


def _f(v: Any) -> Optional[float]:
    import numpy as np

    if isinstance(v, bool) or v is None:
        return None
    if isinstance(v, (int, float, np.integer, np.floating)):
        return float(v)
    return None


def _canon(v: Any) -> str:
    return json.dumps(v, sort_keys=True, default=str, allow_nan=True)


def _short(v: Any) -> Any:
    s = _canon(v)
    return v if len(s) <= 200 else s[:200] + "…"


class KeyOf:
    """回應路徑 → 涵蓋鍵（同 `coverage_keys`：段為特徵名者 → `*`、純數字段 → `#`）。"""

    def __init__(self, feature_names: Sequence[str]) -> None:
        self.feats = {_ptr(f) for f in feature_names}

    def __call__(self, path: str) -> str:
        segs = path.split("/")[1:]
        return "/" + "/".join("*" if s in self.feats else "#" if s.isdigit() else s for s in segs)


def _ptr(seg: Any) -> str:
    return str(seg).replace("~", "~0").replace("/", "~1")


def _is_scalar(v: Any) -> bool:
    import numpy as np

    return v is None or isinstance(v, (bool, int, float, str, np.generic))


def _tree(t: Tally, key_of: KeyOf, path: str, got: Any, exp: Any, feature: Optional[str] = None) -> None:
    """巢狀逐葉對照（鍵集合須同；浮點以相對誤差；其餘 ==）。葉之涵蓋鍵＝`key_of(路徑)`；純量 list 以 list 本身之路徑為鍵
    （同 `flatten_fields` 整段一值）。"""
    if isinstance(exp, (Mapping, list, tuple)) and len(exp) == 0:
        # 空容器為一葉（同 `flatten_fields`）：精確比對，無內容（資料充足判準另計）
        t.eq(key_of(path), path, _canon(got) if not isinstance(got, (Mapping, list, tuple)) else got, exp, feature)
        return
    if isinstance(exp, Mapping):
        if not isinstance(got, Mapping):
            t.eq(key_of(path), path + "#type", type(got).__name__, "dict", feature)
            return
        gk, ek = set(map(str, got)), set(map(str, exp))
        if gk != ek:
            t.eq(key_of(path), path + "#keys", sorted(gk), sorted(ek), feature)
        gm = {str(k): v for k, v in got.items()}
        for k, v in exp.items():
            if str(k) in gm:
                _tree(t, key_of, f"{path}/{_ptr(k)}", gm[str(k)], v, feature)
    elif isinstance(exp, (list, tuple)):
        scalar = bool(exp) and all(_is_scalar(v) for v in exp)
        if not isinstance(got, (list, tuple)) or len(got) != len(exp):
            t.eq(key_of(path), path + "#len", len(got) if isinstance(got, (list, tuple)) else _short(got), len(exp),
                 feature)
            return
        for i, (g, e) in enumerate(zip(got, exp)):
            if scalar:
                _leaf(t, key_of(path), f"{path}/{i}", g, e, feature)
            else:
                _tree(t, key_of, f"{path}/{i}", g, e, feature)
    else:
        _leaf(t, key_of(path), path, got, exp, feature)


def _leaf(t: Tally, key: str, where: str, got: Any, exp: Any, feature: Optional[str]) -> None:
    import numpy as np

    if isinstance(exp, (float, np.floating)) and not isinstance(exp, bool):
        t.num(key, where, got, exp, feature=feature)
    elif isinstance(exp, (int, np.integer)) and not isinstance(exp, (bool, np.bool_)) and isinstance(got, (float, np.floating)):
        t.num(key, where, got, float(exp), feature=feature)
    else:
        t.eq(key, where, got, exp, feature)


def read_kline_close(symbol: str, timeframe: str) -> Any:
    """真實 kline 之收盤序列（UTC 時間索引；獨立於產品之 kline reader 直接讀 h5）。"""
    import h5py
    import pandas as pd

    with h5py.File(KLINE_H5, "r") as f:
        data = f[f"{symbol}/{timeframe}/data"][:]
    ts = data["timestamp"].astype("int64")
    unit = "ms" if int(ts[-1]) > 10 ** 12 else "s"
    return pd.Series(data["close"].astype("float64"), index=pd.to_datetime(ts, unit=unit, utc=True), name="close")


def _utc(index: Any) -> Any:
    import pandas as pd

    idx = pd.DatetimeIndex(index)
    return idx.tz_localize("UTC") if idx.tz is None else idx.tz_convert("UTC")


def oracle_label(close: Any, index: Any, horizon: int, return_type: str) -> Any:
    """主線標籤之 oracle：收盤截至特徵末根（同資料窗），simple＝close[t+h]／close[t]−1、log＝ln 比值；對齊特徵索引。"""
    import numpy as np

    idx = _utc(index)
    c = close.loc[: idx.max()]
    fwd = c.shift(-int(horizon))
    lab = fwd / c - 1.0 if return_type == "simple" else np.log(fwd / c)
    return lab.reindex(idx)


def oracle_split(n_rows: int, cfg: Mapping[str, Any], purge: int) -> Dict[str, Any]:
    """切分之 oracle（`holdout_boundary` 之定義，獨立重寫）：train＝前 floor((1−oos)·N) 列；test＝其後跳過 purge＋embargo
    列之其餘；任一段 < min_test_rows ⇒ 不成立（退回全樣本）。"""
    import math

    n_train = int(math.floor((1.0 - float(cfg["oos_test_size"])) * n_rows))
    start = n_train + int(purge) + int(cfg.get("embargo") or 0)
    n_test = max(0, n_rows - start)
    ok = n_train >= int(cfg["min_test_rows"]) and n_test >= int(cfg["min_test_rows"])
    return {"n_train": n_train, "test_start": start, "n_test": n_test, "applied": ok}


def oracle_rolling_ic(F: Any, y: Any, window: int, method: str, stride: int = 1) -> Dict[str, List[float]]:
    """滾動 IC 之 oracle（SPEC Task 0.4 ④⑨ 鎖定之定義，獨立重寫）：時間軸＝標籤有限之列；固定窗依軸之列位置以 stride 滑動；
    每窗每特徵獨立——窗內該特徵或標籤有任一非有限值、或任一為常數 ⇒ NaN；否則請求 IC 方法之 scipy 函式（spearmanr／
    pearsonr／kendalltau）。呼叫端傳入之 F、y 已為該段（樣本外＝測試段：整窗落於測試段，⑨）。回 {特徵: [IC, …]}。"""
    import math

    import numpy as np
    from scipy import stats

    fn = {"spearman": stats.spearmanr, "pearson": stats.pearsonr, "kendall": stats.kendalltau}[method]
    yv = y.reindex(F.index).to_numpy(dtype=float)
    rows = np.flatnonzero(np.isfinite(yv))
    X = F.to_numpy(dtype=float)
    out: Dict[str, List[float]] = {c: [] for c in F.columns}
    if window <= 1 or rows.size < window:
        return out
    for end in range(window - 1, rows.size, max(1, int(stride))):
        sel = rows[end - window + 1:end + 1]
        yw = yv[sel]
        ycon = np.ptp(yw) == 0
        for j, c in enumerate(F.columns):
            xw = X[sel, j]
            if ycon or not np.all(np.isfinite(xw)) or np.ptp(xw) == 0:
                out[c].append(math.nan)
            else:
                out[c].append(float(fn(xw, yw)[0]))
    return out


def bar_hours(index: Any) -> Optional[float]:
    """資料之 K 線間距（小時；時間索引相鄰差之中位數，由資料本身導出，不假設 24 小時交易或特定週期）。"""
    import numpy as np

    idx = _utc(index)
    if len(idx) < 2:
        return None
    d = np.diff(idx.asi8) / 3.6e12
    return float(np.median(d[d > 0])) if (d > 0).any() else None


def tf_hours(tf: Any) -> Optional[float]:
    """週期字串（<數字><h|d|w>）之小時數；不可解析 ⇒ None。"""
    s = str(tf or "")
    try:
        v = float(s[:-1])
    except ValueError:
        return None
    return {"h": v, "d": v * 24.0, "w": v * 168.0}.get(s[-1:].lower())


def oracle_windows(windows: Sequence[int], reference_tf: Any, bar_h: Optional[float]) -> List[int]:
    """滾動窗之週期換算 oracle（TFWINDOW：窗以 reference_tf 為單位，換算為本資料之根數＝max(round(w·ref／bar), 1)）；
    bar 取資料實際間距（`bar_hours`）；無法換算 ⇒ 原樣。"""
    ref = tf_hours(reference_tf)
    if not ref or not bar_h:
        return [int(w) for w in windows]
    return [max(int(round(int(w) * ref / bar_h)), 1) for w in windows]


# ── 涵蓋鍵（逐請求封閉） ───────────────────────────────────────────────────────────────────────────────


def coverage_keys(response: Any, feature_names: Sequence[str]) -> Dict[str, List[str]]:
    """回應之涵蓋鍵 ⇒ 該鍵之實際欄位路徑（凍結腳本 `flatten_fields` 之鍵，去 `#values`／`#index` 等尾綴後，段為特徵名者
    →`*`、純數字段（list 索引）→`#`）。特徵名＝請求所指 run 之特徵名全集（含被剔除者）。"""
    import re

    fb = _fb()
    feats = {fb._ptr_seg(f) for f in feature_names}
    out: Dict[str, List[str]] = {}
    for path in fb.flatten_fields(response):
        base = re.sub(r"#[A-Za-z_]+$", "", path)
        segs = base.split("/")[1:]
        key = "/" + "/".join("*" if s in feats else "#" if s.isdigit() else s for s in segs)
        out.setdefault(key, []).append(path)
    return out


# ── 收據：逐請求 oracle 對照（母行程；oracle 取自測試檔之參考實作與業界標準函式庫，皆不呼叫被測碼計算） ──────────

NON_STAT = "非統計欄"
SSR_SLACK = 1e-9
REGIME_TEST = REPO / "tests" / "momentum" / "Analysis" / "test_icperf_regime_robust.py"
DEEP_TESTS = {name: REPO / "tests" / "momentum" / "Analysis" / f"test_icperf_deep_{name}.py"
              for name in ("factor_return", "centrality_trend", "orth_exposure", "quality_netic", "sensitivity_oos")}
#: 組合因子之非統計欄（COVERAGE_RULES 記非統計欄者）
COMPOSITE_NON_STAT = ("status", "reason", "method", "fit_scope", "oos_guarantees", "excluded")
#: 依滾動 IC 序列（含其方法）導出之項：請求 IC 方法非 spearman 時以 `<項>.<方法>` 分立
ROLLING_DERIVED_ITEMS = ("rolling_ic_icir", "rolling_ic_series_sampling", "ic_hit_rate", "ic_mean_source", "direction",
                         "regime_robust")


def _sib(name: str, path: Path) -> Any:
    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))
    return sys.modules.get(name) or _load(name, path)


def _seg(F: Any, y: Any, mask: Any) -> Any:
    """以布林遮罩切出該段（None ⇒ 全段）。"""
    import numpy as np

    if mask is None:
        return F, y
    m = np.asarray(mask, dtype=bool)
    return F.loc[F.index[m]], (y.loc[y.index[m]] if len(y) == len(F) else y.reindex(F.index[m]))


def _hac_fail_closed(x: Any, y: Any, horizon: int, maxlags: Any) -> Dict[str, Any]:
    """HAC t／p 之 oracle（SPEC Task 0.3 鎖定定義；測試檔 `_hac_oracle` 之 statsmodels OLS HAC SE）＋現行 fail-closed 邊界：
    L＝指定 maxlags 或 max(int(4·(n/100)^(2/9)), h−1)；L ≥ n−1 或 n < max(8, 2L) ⇒ NaN；SE 非有限或 0 ⇒ NaN。"""
    import math

    import numpy as np

    O = _oracles()
    n = int(np.asarray(x).size)
    lag = int(maxlags) if maxlags is not None else max(int(4 * (n / 100.0) ** (2.0 / 9.0)), int(horizon) - 1)
    nan = {"t_stat": math.nan, "p_value": math.nan, "se": math.nan, "n_obs": n, "maxlags": lag}
    if n < 3 or lag >= n - 1 or n < max(8, 2 * lag):
        return nan
    z = O._ref_spearman_z(np.asarray(x, dtype=float), np.asarray(y, dtype=float))
    if not np.all(np.isfinite(z)):
        return nan
    se = O._sm_hac_se(z, lag)
    if not math.isfinite(se) or se == 0:
        return nan
    return O._hac_oracle(np.asarray(x, dtype=float), np.asarray(y, dtype=float), horizon, lag)


def _hac_on_series(z: Any, horizon: int, maxlags: Any) -> Dict[str, Any]:
    """截面 IC 序列之 HAC oracle（z＝IC 序列本身；L＝指定或 max(int(4·(n/100)^(2/9)), h−1)；fail-closed 同第 5 段；SE＝
    statsmodels OLS HAC Bartlett 無小樣本修正；t＝mean／SE、p＝2·t.sf(|t|, n−1)）。"""
    import math

    import numpy as np
    from scipy import stats

    O = _oracles()
    z = np.asarray(z, dtype=float)
    n = int(z.size)
    lag = int(maxlags) if maxlags is not None else max(int(4 * (n / 100.0) ** (2.0 / 9.0)), int(horizon) - 1)
    nan = {"t_stat": math.nan, "p_value": math.nan}
    if n < 2 or lag >= n - 1 or n < max(8, 2 * lag):
        return nan
    se = O._sm_hac_se(z, lag)
    if not math.isfinite(se) or se == 0:
        return nan
    tval = float(np.mean(z)) / se
    return {"t_stat": tval, "p_value": float(2.0 * stats.t.sf(abs(tval), df=n - 1))}


def _fdr(pvals: Mapping[str, Optional[float]]) -> Dict[str, float]:
    """FDR（statsmodels multipletests fdr_bh）於有限 p 值之同一檢定集合；非有限 ⇒ 不入。"""
    import math

    from statsmodels.stats.multitest import multipletests

    fin = {c: p for c, p in pvals.items() if p is not None and math.isfinite(p)}
    if not fin:
        return {}
    adj = multipletests(list(fin.values()), method="fdr_bh")[1]
    return {c: float(a) for c, a in zip(fin, adj)}


def _aligned_mono(qmeans: Mapping[str, Any], d: int) -> float:
    """方向對齊單調性 oracle（SPEC ⑧：分位依數值序；d＝+1 相鄰差 > 0 之比例、−1 相鄰差 < 0 之比例；無可比 ⇒ 0；d＝0 ⇒ NaN）。"""
    import math

    import numpy as np

    if d == 0:
        return math.nan

    def order(k: Any) -> Any:
        m = re.fullmatch(r"Q(\d+)", str(k))
        return (0, int(m.group(1)), str(k)) if m else (1, 0, str(k))

    keys = sorted(qmeans or {}, key=order)
    v = np.asarray([qmeans[k] for k in keys], dtype=float)
    if v.size < 2:
        return 0.0
    pair = np.isfinite(v[:-1]) & np.isfinite(v[1:])
    if not pair.any():
        return 0.0
    diff = (v[1:] - v[:-1])[pair]
    return float(np.mean(diff > 0)) if d > 0 else float(np.mean(diff < 0))


def _run_time_grid(cap: Mapping[str, Any], close_full: Any) -> Any:
    """請求所指 run 之完整時間網格（kline 時間軸於 manifest `time_range` 內之各根；UTC）；取不到 ⇒ None。"""
    import pandas as pd

    run_dir = (cap.get("request") or {}).get("run_dir")
    if not run_dir:
        return None
    man = json.loads((REPO / run_dir / "feature_manifest.json").read_text(encoding="utf-8"))
    tr = man.get("time_range") or {}
    lo, hi = (tr.get("start"), tr.get("end")) if isinstance(tr, dict) else (tr[0], tr[1]) if tr else (None, None)
    if lo is None or hi is None:
        return None

    def ts(v: Any) -> Any:
        if isinstance(v, str) and v.strip().isdigit():
            v = int(v.strip())
        t = pd.Timestamp(int(v), unit="ms" if int(v) > 10 ** 12 else "s") if isinstance(v, (int, float)) else pd.Timestamp(v)
        return t.tz_localize("UTC") if t.tzinfo is None else t.tz_convert("UTC")

    idx = close_full.index
    return idx[(idx >= ts(lo)) & (idx <= ts(hi))]


def evaluate_ic_report(cap: Mapping[str, Any], key_of: "KeyOf", items: Dict[str, Tally]) -> Dict[str, Any]:
    """IC 報告欄之 oracle 對照（SPEC Task 0.3 各項；Task 0.4 ①–㉖ 修正後之定義）。報告取 `cap["ic_report"]`；輸入取擷取之
    分析器快取、第 4 段點 IC、第 5 段輸入對與有效設定。滾動窗由設定 reference_tf 與資料實際 K 線間距導出（不寫死週期）。
    回本請求之資料事實（FACT）。"""
    import math

    import numpy as np
    import pandas as pd

    O = _oracles()
    R = _sib("icperf_cr_regime", REGIME_TEST)
    rep = cap["ic_report"] if isinstance(cap["ic_report"], dict) else {}
    cfg = cap["config"] or {}
    cache = cap["cache"]
    F, y = cache["features_df"], cache["label_series"]
    sc = cache.get("split_context")
    meta = cache.get("metadata") or {}
    method = str(cfg["global_settings"]["default_method"])
    horizon = int((sc or {}).get("effective_horizon") or cfg["global_settings"]["default_horizon"])
    icc = cfg["ic_calculation"]
    stride = int(icc.get("rolling_stride") or 1)

    def T(iid: str, oracle: str) -> Tally:
        # 滾動 IC 依賴之項依請求 IC 方法分立（Pearson／Kendall 分支各自之 oracle 項；Spearman 為基本項）
        if method != "spearman" and iid in ROLLING_DERIVED_ITEMS:
            iid = f"{iid}.{method}"
        return items.setdefault(iid, Tally(oracle))

    rows = {r["feature_name"]: r for r in rep.get("summary_table") or [] if isinstance(r, dict)}
    symbol, tf = str(meta.get("symbol")), str(meta.get("timeframe"))
    close_full = read_kline_close(symbol, tf)
    facts: Dict[str, Any] = {"symbol": symbol, "timeframe": tf, "n_rows": int(len(F)), "n_features": int(F.shape[1]),
                             "kline": str(KLINE_H5.relative_to(REPO)), "method": method, "horizon": horizon,
                             "index_first": str(F.index[0]) if len(F) else None,
                             "index_last": str(F.index[-1]) if len(F) else None}
    # 標籤（獨立讀 kline，float64；SPEC ⑥）
    ev = cache.get("event_info") or {}
    if str(ev.get("label_source")) == "event_label_value":
        # 事件匯入批：標籤＝事件管線（`label_value_from_case`）依各事件之 label_definition 所算之值，非主線 h 根報酬
        facts["event_label"] = {"label_source": ev.get("label_source"), "label_kind": ev.get("label_kind"),
                                "n_events": ev.get("n_events"), "oracle": "未建（事件管線標籤定義另驗）"}
    else:
        t = T("label", "close[t+h]/close[t]−1（kline_cache.h5 直接讀、float64、截至特徵末根；log 報酬取 ln 比值）")
        lab = oracle_label(close_full, y.index, horizon, str(cfg["labels"]["return_type"]))
        for ts, pv, ov in zip(y.index, y.to_numpy(dtype=float), lab.to_numpy(dtype=float)):
            t.num("@input/label_series", f"label@{ts}", pv, ov)
    # 切分（事件路徑之 purge／embargo 列數取切分計畫所記〔事件管線之隔離區換算〕，切分公式本身獨立重算）
    t = T("split", "holdout 參考實作：train＝前 floor((1−oos)·N)、purge＝label horizon（事件路徑取切分計畫之 purge／embargo"
          " 列數、於 run 完整時間網格切分）、test＝其餘；任一段 < min_test_rows ⇒ 退回")
    plan = (sc or {}).get("train_plan")
    purge = int(getattr(plan, "purge_gap", horizon)) if plan is not None else horizon
    emb = int(getattr(plan, "embargo", 0) or 0) if plan is not None else None
    cfg_s = {**cfg, **({"embargo": emb} if emb is not None else {})}
    osp = oracle_split(len(F), cfg_s, purge)
    split_meta = (rep.get("metadata") or {}).get("ic_train_test_split") or {}
    facts["split"] = {"product_applied": sc is not None, "metadata": split_meta, "oracle": osp}
    grid_rows = _run_time_grid(cap, close_full)
    if sc is not None:
        trm, tem = np.asarray(sc["train_mask"], bool), np.asarray(sc["test_mask"], bool)
        if grid_rows is not None and len(grid_rows) != len(F):
            n = len(grid_rows)
            g = oracle_split(n, cfg_s, purge)
            tr_end = grid_rows[g["n_train"] - 1]
            te_start = grid_rows[g["test_start"]] if g["test_start"] < n else None
            idx = _utc(F.index)
            exp_tr = np.asarray(idx <= tr_end, bool)
            exp_te = np.zeros(len(F), bool) if te_start is None else np.asarray(idx >= te_start, bool)
            facts["split"]["grid"] = {"n_grid": n, "n_train": g["n_train"], "test_start": g["test_start"]}
        else:
            exp_tr = np.zeros(len(F), bool)
            exp_tr[:osp["n_train"]] = True
            exp_te = np.zeros(len(F), bool)
            exp_te[osp["test_start"]:] = True
        t.eq("@input/split", "train_mask", np.flatnonzero(trm != exp_tr).tolist(), [])
        t.eq("@input/split", "test_mask", np.flatnonzero(tem != exp_te).tolist(), [])
    else:
        t.eq("@input/split", "fallback", bool(split_meta.get("applied")), False)
    test_mask = None if sc is None else np.asarray(sc["test_mask"], bool)
    F_seg, y_seg = _seg(F, y, test_mask)
    facts["segment_rows"] = int(len(F_seg))
    # 點 IC（第 4 段 pooled；summary ic_mean 之退回來源）
    fn = {"spearman": "spearmanr", "pearson": "pearsonr", "kendall": "kendalltau"}[method]
    t = T(f"point_ic.{method}", f"scipy.stats.{fn}（兩欄共同非 NaN 列；列數 < 2 或任一常數 ⇒ NaN）")
    point = {c: O._ic_oracle(F_seg[c].to_numpy(float), y_seg.to_numpy(float), method) for c in F.columns}
    s4 = (cap.get("stage4") or [{}])[0].get("ic_values") or {}
    for c in F.columns:
        if c in s4:
            t.num("@stage4/ic_values", c, s4[c], point[c], feature=c)
    # 滾動窗之週期換算（K 線間距由 kline 時間軸導出；事件路徑之特徵列只含事件根，間距不規則）
    bh = bar_hours(close_full.index)
    owins = oracle_windows(icc["rolling_windows"], icc["icir"]["reference_tf"], bh)
    icir_w = oracle_windows([icc["icir"]["window"]], icc["icir"]["reference_tf"], bh)[0]
    ri = cache.get("rolling_ic") or {}
    pw = sorted({int(k.split("_", 1)[1]) for v in ri.values() if isinstance(v, dict) for k in v})
    t_r = T("rolling_ic_icir", "滾動 IC 參考實作（時間軸＝標籤有限列、逐特徵獨立、樣本外整窗、scipy 對應方法）＋ nanmean／"
            "nanstd(ddof0)／比值")
    t_r.eq("@windows", "rolling_windows", pw, sorted(owins))
    facts["windows"] = {"bar_hours": bh, "oracle": owins, "product": pw, "icir_window_adjusted": icir_w}
    roll = {w: oracle_rolling_ic(F_seg, y_seg, w, method, stride) for w in owins}
    for c in F.columns:
        for w in owins:
            got = (ri.get(c) or {}).get(f"window_{w}")
            exp = roll[w][c]
            if got is None or len(got) != len(exp):
                t_r.eq("@rolling_ic_full", f"{c}/window_{w}#len", None if got is None else len(got), len(exp), feature=c)
                continue
            for i, (g, e) in enumerate(zip(got, exp)):
                t_r.num("@rolling_ic_full", f"{c}/window_{w}/{i}", g, e, feature=c)
            if not exp:
                t_r.na(f"/rolling_ic_series/*/window_{w}", "test_rolling_ic_window_longer_than_axis_is_empty")
    # 報告端抽樣
    t_s = T("rolling_ic_series_sampling", "oracle 滾動序列經測試自寫抽樣參考實作（ic_reporter 之上限規則）")
    srs = rep.get("rolling_ic_series") or {}
    for c in F.columns:
        if c in srs:
            sampled = O._ref_sample({c: {f"window_{w}": roll[w][c] for w in owins}}, 1000)[c]
            _tree(t_s, key_of, f"/rolling_ic_series/{_ptr(c)}", srs.get(c), sampled, c)
    for w in owins:
        if all(not roll[w][c] for c in F.columns):
            t_s.na(f"/rolling_ic_series/*/window_{w}", "test_rolling_ic_window_longer_than_axis_is_empty")
    # ICIR／勝率／ic_mean 來源／方向欄
    t_m = T("ic_mean_source", "滾動均值有限 ⇒ 用之，否則 pooled 點 IC（scipy）；來源計數")
    t_d = T("direction", "direction＝sign(ic_mean)、icir_aligned＝d·icir、方向對齊勝率與單調性（SPEC Task 0.4 ⑧）")
    t_hr = T("ic_hit_rate", "滾動 IC（oracle）有限值中 > 0 之比例；無有限值 ⇒ NaN（SPEC Task 0.4 ②）")
    src_counts = {"rolling_mean": 0, "pooled_point_ic": 0, "unavailable": 0}
    oracle_rows: Dict[str, Dict[str, Any]] = {}
    icir_cache = cache.get("icir") or {}
    # ICIR 所用序列＝`_select_icir_series` 之選擇（SPEC Task 0.3：鍵 `window_<icir.window>`〔設定值，未經週期換算〕存在
    # 則用之，否則窗字典之首窗〔設定順序〕）
    sel_w = int(icc["icir"]["window"]) if int(icc["icir"]["window"]) in roll else (owins[0] if owins else None)
    facts["windows"]["icir_series_window"] = sel_w
    for c in F.columns:
        vals = roll[sel_w][c] if sel_w is not None else []
        o = O._icir_oracle(vals)
        fin = np.asarray(vals, dtype=float)
        fin = fin[np.isfinite(fin)]
        hit = float(np.mean(fin > 0)) if fin.size else math.nan
        neg = float(np.mean(fin < 0)) if fin.size else math.nan
        if math.isfinite(o["ic_mean"]):
            mean, src = o["ic_mean"], "rolling_mean"
        elif math.isfinite(point[c]):
            mean, src = point[c], "pooled_point_ic"
        else:
            mean, src = math.nan, "unavailable"
        src_counts[src] += 1
        d = 0 if not math.isfinite(mean) or mean == 0 else (1 if mean > 0 else -1)
        oracle_rows[c] = {"direction": d}
        if c in icir_cache:
            exp_icir = {"ic_mean": o["ic_mean"], "ic_std": o["ic_std"], "icir": o["icir"], "ic_hit_rate": hit,
                        "ic_neg_rate": neg}
            for k, v in exp_icir.items():
                t_r.num("@icir", f"{c}/{k}", icir_cache[c].get(k), v, feature=c)
        row = rows.get(c)
        if row is None:
            continue
        t_r.num("/summary_table/#/ic_std", f"{c}/ic_std", row.get("ic_std"), o["ic_std"], feature=c)
        t_r.num("/summary_table/#/icir", f"{c}/icir", row.get("icir"), o["icir"], feature=c)
        t_hr.num("/summary_table/#/ic_hit_rate", f"{c}/ic_hit_rate", row.get("ic_hit_rate"), hit, feature=c)
        t_m.num("/summary_table/#/ic_mean", f"{c}/ic_mean", row.get("ic_mean"), mean, feature=c)
        t_d.eq("/summary_table/#/direction", f"{c}/direction", row.get("direction"), d, feature=c)
        t_d.num("/summary_table/#/icir_aligned", f"{c}/icir_aligned", row.get("icir_aligned"),
                d * o["icir"] if d != 0 and math.isfinite(o["icir"]) else math.nan, feature=c)
        t_d.num("/summary_table/#/ic_hit_rate_aligned", f"{c}/ic_hit_rate_aligned", row.get("ic_hit_rate_aligned"),
                hit if d > 0 else (neg if d < 0 else math.nan), feature=c)
    disc = ((rep.get("metadata") or {}).get("ic_window_disclosure") or {}).get("ic_mean_source")
    if isinstance(disc, dict):
        for k, v in src_counts.items():
            t_m.eq(f"/metadata/ic_window_disclosure/ic_mean_source/{k}", k, disc.get(k), v)
    facts["ic_mean_source"] = src_counts
    # 衰減（逐 horizon IC 與擬合）
    t_dv = T("ic_decay_values", "逐 horizon：收盤（kline 直接讀、float64）截至該段之 h 根前瞻報酬 vs 特徵，scipy 對應方法")
    t_f = T("ic_decay_fit", "curve_fit 固定起點集合之最小殘差（最佳性，雙向）＋衍生欄依產品參數重算（half_life、decay_type、"
            "fit_warning、fit_warning_reason、peak_horizon）")
    close_seg = close_full.reindex(_utc(F_seg.index))
    decay = rep.get("ic_decay") or {}
    for c in F.columns:
        dd = decay.get(c)
        if not isinstance(dd, dict):
            continue
        hs = list(dd.get("horizons") or icc["ic_decay_horizons"])
        t_dv.eq("/ic_decay/*/horizons", f"{c}/horizons", [int(h) for h in hs], [int(h) for h in icc["ic_decay_horizons"]], c)
        exp_vals = []
        for h in hs:
            r_h = (close_seg.shift(-int(h)) / close_seg - 1.0).to_numpy(float)
            exp_vals.append(O._ic_oracle(F_seg[c].to_numpy(float), r_h, method))
        _tree(t_dv, key_of, f"/ic_decay/{_ptr(c)}/ic_values", dd.get("ic_values"), exp_vals, c)
        yv = np.asarray(exp_vals, dtype=float)
        fin = yv[np.isfinite(yv)]
        exp_reason = "insufficient_points" if fin.size < 3 else ("low_variance" if np.nanstd(fin) < 1e-8 else None)
        kp = f"/ic_decay/{_ptr(c)}"
        if exp_reason is not None:
            t_f.eq(key_of(kp + "/decay_type"), f"{c}/decay_type", dd.get("decay_type"), "fit_failed", c)
            t_f.eq(key_of(kp + "/fit_warning_reason"), f"{c}/fit_warning_reason", dd.get("fit_warning_reason"), exp_reason, c)
            t_f.eq(key_of(kp + "/fit_warning"), f"{c}/fit_warning", dd.get("fit_warning"), True, c)
            for k in ("decay_rate", "half_life", "fit_r2"):
                t_f.num(key_of(kp + "/" + k), f"{c}/{k}", dd.get(k), math.nan, feature=c)
        else:
            best = O._oracle_min_ssr(hs, exp_vals)
            if dd.get("decay_type") == "fit_failed":
                t_f.eq(key_of(kp + "/decay_type"), f"{c}/fit_failed_vs_oracle", "fit_failed",
                       "oracle 擬合成功" if math.isfinite(best) else "fit_failed", c)
            else:
                pss = O._product_ssr(dd.get("ic_values"), {"r2": dd.get("fit_r2")})
                ok = bool(math.isfinite(best) and pss <= best * (1 + SSR_SLACK) + 1e-300)
                t_f.eq(key_of(kp + "/fit_r2"), f"{c}/ssr_optimal", ok, True, c)
                t_f.eq(key_of(kp + "/decay_rate"), f"{c}/ssr_optimal", ok, True, c)
                lam = _f(dd.get("decay_rate"))
                t_f.num(key_of(kp + "/half_life"), f"{c}/half_life", dd.get("half_life"),
                        math.log(2) / lam if lam is not None and lam > 0 else math.nan, feature=c)
                r2 = _f(dd.get("fit_r2"))
                etype = "exponential" if r2 is not None and r2 >= 0.5 else "non_exponential"
                t_f.eq(key_of(kp + "/decay_type"), f"{c}/decay_type", dd.get("decay_type"), etype, c)
                t_f.eq(key_of(kp + "/fit_warning"), f"{c}/fit_warning", dd.get("fit_warning"), etype != "exponential", c)
                t_f.eq(key_of(kp + "/fit_warning_reason"), f"{c}/fit_warning_reason", dd.get("fit_warning_reason"),
                       "low_r2" if etype != "exponential" else None, c)
        t_f.eq(key_of(kp + "/peak_horizon"), f"{c}/peak_horizon", dd.get("peak_horizon"), O._ref_peak(hs, exp_vals), c)
        if (row := rows.get(c)) is not None:
            t_f.num("/summary_table/#/ic_half_life", f"{c}/summary_half_life", row.get("ic_half_life"), dd.get("half_life"),
                    feature=c)
    # 分組 IC（年度／季度／regime 規則／metadata；與主 IC 同估計量＝default_method，SPEC ㉓）
    t_g = T("grouped_ic", "年度／季度／regime 規則（只用 0..t）／metadata 分組，逐組 scipy 對應方法（測試自寫 _ref_grouped_ic）")
    gcfg = icc["grouped_analysis"]
    fmeta = {c: (meta.get(c) or {}) if isinstance(meta.get(c), dict) else {} for c in F.columns}
    close_g = close_seg.set_axis(F_seg.index)
    exp_g = O._ref_grouped_ic(F_seg, y_seg, close_g, fmeta, method) if len(F_seg) else {}
    # 規則型 regime 之空波動守衛（ic_engine.py `_build_regime_rule_masks`：該段 55 根滾動波動無任一有限值 ⇒ by_regime＝{}）
    vol_seg = close_g.pct_change(fill_method=None).rolling(55).std() if len(F_seg) else close_g
    if "by_regime" in exp_g and not np.isfinite(vol_seg.to_numpy(dtype=float)).any():
        exp_g["by_regime"] = {}
    got_g = rep.get("grouped_ic") or {}
    if str(gcfg.get("regime_method", "rule")) != "rule":
        t_g.notes.append(f"regime_method={gcfg.get('regime_method')}：by_regime 不以規則型 oracle 對照")
    for key in ("by_year", "by_quarter", "by_regime", "by_category", "by_data_source", "by_layer"):
        if key in got_g or gcfg.get(key):
            _tree(t_g, key_of, f"/grouped_ic/{key}", got_g.get(key, {}), exp_g.get(key, {}) if gcfg.get(key) else {})
    # regime_robust（SPEC ㉓：由 by_regime 導出、合格＝IC 有限且有限配對數 ≥ min_samples）
    t_rr = T("regime_robust", "由 oracle by_regime（scipy）與逐 regime 有限配對數依 ㉓ 判 True／False／None 與 reason"
             "（test_icperf_regime_robust.py oracle_regime_robust）")
    min_s = int(gcfg.get("regime_robust_min_samples") or 30)
    masks = O._ref_regime_masks(close_g) if len(F_seg) and exp_g.get("by_regime") != {} else {}
    yv = y_seg.to_numpy(dtype=float)
    regime_on = bool(gcfg.get("by_regime")) and bool((cfg.get("report") or {}).get("include_regime_analysis", True))
    pc_cache = cache.get("regime_pair_counts") or {}
    for c in F.columns:
        xv = F_seg[c].to_numpy(dtype=float)
        per = {}
        for reg, m in masks.items():
            m = np.asarray(m, dtype=bool)
            n_pair = int((np.isfinite(xv[m]) & np.isfinite(yv[m])).sum())
            per[reg] = (O._ic_oracle(xv[m], yv[m], method) if m.any() else math.nan, n_pair)
            if reg in pc_cache:
                t_rr.eq("@regime_pair_counts", f"{reg}/{c}", (pc_cache.get(reg) or {}).get(c), n_pair, c)
        exp_rr, exp_reason = R.oracle_regime_robust(oracle_rows.get(c, {}).get("direction", 0),
                                                    per if regime_on else None, min_s)
        if (row := rows.get(c)) is not None:
            t_rr.eq("/summary_table/#/regime_robust", f"{c}/regime_robust", row.get("regime_robust"), exp_rr, c)
            t_rr.eq("/summary_table/#/regime_robust_reason", f"{c}/regime_robust_reason", row.get("regime_robust_reason"),
                    exp_reason, c)
    # 第 5 段：HAC、FDR、逐根 PIT 統計（輸入＝產品第 5 段實際輸入對）
    t_h = T("hac", "statsmodels OLS HAC（Bartlett、無小樣本修正）＋ scipy t 分布＋現行 fail-closed 邊界；測試自寫 _hac_oracle")
    t_q = T("fdr", "statsmodels multipletests fdr_bh（同檢定集合：summary 有限 p 值）")
    t_p = T("stage5_pit_stats", "逐根 PIT 參考實作（_ref_monotonicity／_ref_turnover／_ref_coverage；只用 0..t）")
    t_ls = T("long_short_tstat", "測試自寫 PIT 分組重得頂底兩組報酬後 scipy.stats.ttest_ind(nan_policy='omit')")
    t_x = T("summary_passthrough", "summary 列各欄 == 同請求之第 5 段／衰減 oracle 輸出")
    pairs = cap.get("stage5_inputs") or []
    maxlags = (cfg.get("significance") or {}).get("maxlags")
    mono_ref: Dict[str, Any] = {}
    if pairs:
        Fs, ys = pairs[0]
        ysr = ys.reindex(Fs.index)
        facts["stage5_rows"] = int(len(Fs))
        for c in Fs.columns:
            x, yy = Fs[c].to_numpy(float), ysr.to_numpy(float)
            ok = np.isfinite(x) & np.isfinite(yy)
            try:
                o = _hac_fail_closed(x[ok], yy[ok], horizon, maxlags)
            except Exception as exc:  # noqa: BLE001 — oracle 於邊界輸入失敗 ⇒ 記錄，不中斷
                o = {"t_stat": math.nan, "p_value": math.nan}
                t_h.notes.append(f"{c}: oracle {exc!r}")
            if (row := rows.get(c)) is not None:
                t_h.num("/summary_table/#/t_stat", f"{c}/t_stat", row.get("t_stat"), o["t_stat"], feature=c)
                t_h.num("/summary_table/#/p_value", f"{c}/p_value", row.get("p_value"), o["p_value"], feature=c)
        adj = _fdr({c: _f(r.get("p_value")) for c, r in rows.items()})
        for c, r in rows.items():
            t_q.num("/summary_table/#/p_value_adj", f"{c}/p_value_adj", r.get("p_value_adj"), adj.get(c, math.nan),
                    feature=c)
        qr, cov, tov = rep.get("quantile_returns") or {}, rep.get("coverage_analysis") or {}, rep.get("turnover_analysis") or {}
        for c in Fs.columns:
            if c in qr:
                ref = O._ref_monotonicity(Fs[c], ysr)
                mono_ref[c] = ref
                exp_qr = {**ref["quantile_returns"], "monotonicity_score": ref["monotonicity_score"]}
                got = dict(qr[c]) if isinstance(qr[c], dict) else qr[c]
                if isinstance(got, dict) and "long_short_tstat" in got:
                    t_ls.num("/quantile_returns/*/long_short_tstat", f"{c}/long_short_tstat", got.pop("long_short_tstat"),
                             exp_qr.pop("long_short_tstat"), feature=c)
                _tree(t_p, key_of, f"/quantile_returns/{_ptr(c)}", got, exp_qr, c)
            if c in cov:
                _tree(t_p, key_of, f"/coverage_analysis/{_ptr(c)}", cov[c], O._ref_coverage(Fs[c]), c)
            if c in tov:
                _tree(t_p, key_of, f"/turnover_analysis/{_ptr(c)}", tov[c], O._ref_turnover(Fs[c]), c)
        for c, row in rows.items():
            ref = mono_ref.get(c)
            if ref is None:
                continue
            q = ref["quantile_returns"]
            t_x.num("/summary_table/#/monotonicity_score", f"{c}/monotonicity_score", row.get("monotonicity_score"),
                    ref["monotonicity_score"], feature=c)
            t_x.num("/summary_table/#/long_short_spread", f"{c}/long_short_spread", row.get("long_short_spread"),
                    q.get("long_short_spread"), feature=c)
            t_x.num("/summary_table/#/coverage", f"{c}/coverage", row.get("coverage"), O._ref_coverage(Fs[c])["coverage"],
                    feature=c)
            if "turnover_rate" in row:
                t_x.num("/summary_table/#/turnover_rate", f"{c}/turnover_rate", row.get("turnover_rate"),
                        O._ref_turnover(Fs[c])["quantile_turnover"], feature=c)
            t_d.num("/summary_table/#/monotonicity_score_aligned", f"{c}/monotonicity_score_aligned",
                    row.get("monotonicity_score_aligned"),
                    _aligned_mono(q.get("quantile_mean_returns") or {}, oracle_rows.get(c, {}).get("direction", 0)),
                    feature=c)
    # 第 6 段：相關矩陣與多元化指標（輸入＝該段之倖存者欄；含 NaN ⇒ 逐對 pearsonr，否則 numpy.corrcoef）
    t_c = T("redundancy_correlation", "無 NaN＝numpy.corrcoef、含 NaN＝逐對 scipy.stats.pearsonr（測試自寫 _ref_corr）")
    t_v = T("diversification_metrics", "倖存者之 oracle 相關子矩陣與 metadata 依公式重算（測試自寫 _ref_diversification）")
    cm = rep.get("correlation_matrix") or {}
    feats_c = list(cm.get("features") or []) if isinstance(cm, dict) else []
    if feats_c:
        exp_m = np.atleast_2d(O._ref_corr(F_seg[feats_c]))
        _tree(t_c, key_of, "/correlation_matrix/matrix", cm.get("matrix"), [[float(v) for v in r] for r in exp_m])
        t_c.eq("/correlation_matrix/features", "features", feats_c, list(cap.get("survivors") or feats_c))
        corr_df = pd.DataFrame(exp_m, index=feats_c, columns=feats_c)
        fm = {k: v for k, v in meta.items() if isinstance(v, dict)}
        _tree(t_v, key_of, "/diversification_metrics", rep.get("diversification_metrics"),
              O._ref_diversification(feats_c, corr_df, fm))
    elif isinstance(cm, dict):
        # 無倖存者 ⇒ 第 6 段空矩陣、多元化指標空（依定義）
        n_surv = len(cap.get("survivors") or [])
        t_c.eq("/correlation_matrix/features", "features(empty)", cm.get("features"), [] if n_surv == 0 else ["…"])
        t_c.eq("/correlation_matrix/matrix", "matrix(empty)", cm.get("matrix"), [] if n_surv == 0 else ["…"])
        t_v.eq("/diversification_metrics", "diversification(empty)", rep.get("diversification_metrics"),
               {} if n_surv == 0 else {"…": "…"})
        for k in ("/correlation_matrix/features", "/correlation_matrix/matrix"):
            t_c.na(k, "test_redundancy_correlation_matches_oracle")
        t_v.na("/diversification_metrics", "test_diversification_metrics_match_reference")
    # 第 6b 段：邊際 IC 與組合（status ok 時；輸入同 `_stage6b_marginal_ic`）
    mi = rep.get("marginal_ic") or {}
    if isinstance(mi, dict) and mi.get("status") == "ok":
        _evaluate_marginal(cap, rep, cfg, key_of, items, horizon)
    facts["survivors"] = list(cap.get("survivors") or [])
    facts["marginal_status"] = mi.get("status") if isinstance(mi, dict) else None
    return facts


def _evaluate_marginal(cap: Mapping[str, Any], rep: Mapping[str, Any], cfg: Mapping[str, Any], key_of: "KeyOf",
                       items: Dict[str, Tally], horizon: int) -> None:
    """邊際 IC 三視角、train_ic 與組合因子之 oracle（測試檔 `_ref_marginal`／`_ref_train_ic`／`_ref_composite`：statsmodels
    OLS 投影、scipy Spearman、固定 seed 成對 moving-block bootstrap）；masks／參數同 `_stage6b_marginal_ic`。"""
    import math

    import numpy as np

    from momentum.Analysis.marginal_ic import MarginalICParams

    O = _oracles()
    cache = cap["cache"]
    F = cache["features_df"]
    y = cache["label_series"].reindex(F.index)
    sc = cache.get("split_context")
    mi = rep["marginal_ic"]
    n = len(F)
    if mi.get("fit_scope") == "train" and sc is not None:
        tr, te = np.asarray(sc["train_mask"], bool), np.asarray(sc["test_mask"], bool)
    else:
        tr, te = np.ones(n, bool), np.ones(n, bool)
    survivors = list(cap.get("survivors") or [])
    removed = ((rep.get("filter_log") or {}).get("stage6_redundancy") or {}).get("removed_features") or []
    m = cfg["marginal_ic"]
    extra = [f for f in removed if isinstance(f, str)] if m.get("include_removed_candidates") else []
    n_test = int(te.sum())
    block = max(int(horizon), int(math.ceil(n_test ** (1.0 / 3.0))) if n_test > 0 else 1, 1)
    p = MarginalICParams(min_test_rows=int(m["min_test_rows"]), min_rows_per_regressor=int(m["min_rows_per_regressor"]),
                         degenerate_threshold=float(m["degenerate_threshold"]), n_bootstrap=int(m["n_bootstrap"]),
                         block_len=int(block), seed=int(m["bootstrap_seed"]), weights_method=str(m["weights_method"]),
                         max_survivors_for_loo=int(m["max_survivors_for_loo"]),
                         max_removed_candidates=int(m["max_removed_candidates"]))
    yv = y.to_numpy(dtype=float)
    t_m = items.setdefault("marginal_ic", Tally("statsmodels OLS 投影（秩常態分數）、R²、numpy.linalg.cond、scipy Spearman、"
                                                "固定 seed 成對 moving-block bootstrap（測試自寫 _ref_marginal）"))
    t_t = items.setdefault("marginal_ic.train_ic", Tally("train 段有限列 scipy.stats.spearmanr（測試自寫 _ref_train_ic）"))
    t_c = items.setdefault("marginal_ic.composite", Tally("train 段定權與符號、test 段計 composite IC、固定 seed delta_ci95"
                                                          "（測試自寫 _ref_composite）"))
    exp = O._ref_marginal(F, yv, tr, te, survivors, extra, p)
    _tree(t_t, key_of, "/marginal_ic/train_ic", mi.get("train_ic"), exp["train_ic"])
    for view in ("per_feature", "sequential", "removed_candidates"):
        _tree(t_m, key_of, f"/marginal_ic/{view}", mi.get(view), exp[view])
    if survivors:
        comp = O._ref_composite(F, yv, tr, te, survivors, p)
        got = dict(mi.get("composite") or {})
        # 非統計欄（狀態、方法回顯、fit_scope／oos_guarantees 由 stage 7 依 root 注入）不入對照
        comp = {k: v for k, v in comp.items() if k in got and k not in COMPOSITE_NON_STAT}
        _tree(t_c, key_of, "/marginal_ic/composite", {k: got[k] for k in comp}, comp)


#: 深度模組 → 其 oracle 所在深度測試檔簡稱
DEEP_MODULES = {
    "factor_returns": "factor_return", "long_short_analysis": "factor_return", "factor_centrality": "centrality_trend",
    "trend_analysis": "centrality_trend", "parameter_sensitivity": "sensitivity_oos", "rolling_oos": "sensitivity_oos",
    "factor_orthogonalization": "orth_exposure", "factor_exposure": "orth_exposure",
    "feature_quality_diagnostics": "quality_netic", "net_ic_analysis": "quality_netic",
}
#: 深度欄中非數值之判定欄（字串／bool）：一致即視為有內容
_DEEP_NONNUMERIC = {"trend", "regime", "assessment", "crowded", "risk_level", "recommendation", "type", "side", "action",
                    "reason", "interpretation", "degenerate", "drifted", "is_stationary", "significant_autocorrelation",
                    "concentrated", "max_exposure_factor", "capacity_tier", "status", "trend_reason", "feature",
                    "direction", "skipped", "calibration", "quote_currency", "turnover_semantics", "psi_reason"}


def _deep(name: str) -> Any:
    return _sib(f"icperf_cr_deep_{name}", DEEP_TESTS[name])


def _deep_cov_key(path: str) -> str:
    """深度測試檔之正規化路徑 → 涵蓋鍵：前綴 `/results/`、純量 list 之尾段 `/#` 去除（同 `flatten_fields` 整段一值）。"""
    p = "/results/" + str(path).strip("/")
    return p[:-2] if p.endswith("/#") else p


def _norm_deep_key(key: str) -> str:
    """回應涵蓋鍵 → 與深度測試檔 MODULE_FIELDS 比對之形（`PC<n>` → `PC#`）。"""
    return re.sub(r"/PC\d+(?=/|$)", "/PC#", key)


def _tally_from_compare(t: Tally, res: Mapping[str, Mapping[str, Any]]) -> None:
    """深度測試檔 `compare_*` 之逐欄結果（{正規化路徑: {verdict, max_rel_diff, n_finite, detail}}）併入 Tally（鍵＝`_deep_cov_key`）。"""
    import math

    for path, r in res.items():
        key = _deep_cov_key(path)
        miss = r.get("verdict") != "一致"
        if miss and str(path).endswith("correlation_after"):
            # 正交化後之相關（理論值 0、有界 [0, 1]）：產品與 oracle 皆 ≤ 1e-9 ⇒ 皆為數值零，差異屬 oracle 之 statsmodels OLS
            # 逐欄投影累積捨入（實測 oracle 1e-11、產品 1e-17），不判產品不一致；逐值記 notes
            nums = [abs(float(v)) for v in re.findall(r"(?:產品|oracle)\s*([-+0-9.eE]+)", str(r.get("detail") or ""))]
            if nums and max(nums) <= 1e-9:
                t.notes.append(f"{path}：產品與 oracle 皆為數值零（max |值| {max(nums):.3g}），不判不一致；{r.get('detail')}")
                r = {**r, "verdict": "一致", "max_rel_diff": None}
                miss = False
        t.n += 1
        t.n_finite += int(r.get("n_finite") or 0)
        rel = r.get("max_rel_diff")
        if rel is not None:
            t.max_rel = max(t.max_rel, float(rel)) if math.isfinite(float(rel)) else math.inf
        elif miss:
            t.max_rel = math.inf
        last = str(path).rstrip("/#").rsplit("/", 1)[-1].split("@", 1)[0]
        t._key(key, bool(r.get("n_finite")) or (not miss and last in _DEEP_NONNUMERIC), miss)
        if miss:
            t._miss(path, r.get("detail"), "oracle", None)
            for f in re.findall(r"\[([^\]]+)\]|/([^/：]+)/[a-z_]+：", str(r.get("detail") or "")):
                t.features.add(next(x for x in f if x))


def deep_fields() -> Dict[str, Dict[str, str]]:
    """深度十模組之欄位清冊（各深度測試檔 `MODULE_FIELDS`／`MODULE_FIELDS_FALLBACK`）→ {涵蓋鍵: {oracle, producer}}。"""
    out: Dict[str, Dict[str, str]] = {}
    for name in DEEP_TESTS:
        m = _deep(name)
        for attr in ("MODULE_FIELDS", "MODULE_FIELDS_FALLBACK"):
            for path, meta in (getattr(m, attr, None) or {}).items():
                out.setdefault(_deep_cov_key(path), dict(meta))
    return out


def evaluate_deep(cap: Mapping[str, Any], items: Dict[str, Tally]) -> Dict[str, Any]:
    """深度十模組（全部模組開，含預設關閉者）之 oracle 對照：各模組以其深度測試檔之 `compare_*`（oracle＝scipy／statsmodels／
    numpy.linalg 或測試自寫逐根 PIT 參考實作，不呼叫被測碼）於產品同一組輸入（`_ic_cache`、selected、有效設定、同請求來源
    模組）重算。回 {模組: 產品狀態}。"""
    import pandas as pd

    raw = cap.get("deep_raw")
    if raw is None:
        return {}
    results = raw.results
    cache = cap["cache"]
    sel = list(cap.get("selected") or [])
    dc = cap["deep_config"] or {}
    cfg = cap["config"] or {}
    sc = cache.get("split_context") or {}
    h = int(sc.get("effective_horizon") or cfg["global_settings"]["default_horizon"])
    rows = {r["feature_name"]: r for r in (cap["ic_report"] or {}).get("summary_table") or [] if isinstance(r, dict)}
    dirs = {n: int(r["direction"]) for n, r in rows.items() if isinstance(r.get("direction"), (int, float))}
    F = cache["features_df"][[c for c in sel if c in cache["features_df"].columns]]
    y = cache["label_series"]
    ric = cache.get("rolling_ic") or {}
    method = str(cfg["global_settings"]["default_method"])
    meta = cache.get("metadata") or {}
    FR, CT, SO, OE, QN = (_deep(n) for n in ("factor_return", "centrality_trend", "sensitivity_oos", "orth_exposure",
                                              "quality_netic"))
    icc = dc.get("ic_calculation") or cfg["ic_calculation"]
    stride = int(icc.get("rolling_stride") or 1)
    bh = bar_hours(read_kline_close(str(meta.get("symbol")), str(meta.get("timeframe"))).index)
    icir_w = oracle_windows([icc["icir"]["window"]], icc["icir"]["reference_tf"], bh)[0]
    rep = cap["ic_report"] or {}
    status = dict(raw.module_summary)

    def run(module: str, fn: Any) -> None:
        t = items.setdefault(f"deep.{module}", Tally(f"深度模組 {module}：{DEEP_TESTS[DEEP_MODULES[module]].name} 之 compare_*"))
        if status.get(module) not in ("completed", "completed_partial"):
            t.notes.append(f"產品 {status.get(module)}：{_short(results.get(module))}")
        try:
            res = fn(results.get(module))
        except Exception as exc:  # noqa: BLE001 — oracle 失敗入記錄（不中斷其餘模組）
            t.eq(f"/results/{module}", f"{module}#oracle_error", f"{type(exc).__name__}: {exc}", "oracle 可執行")
            return
        _tally_from_compare(t, res)

    run("factor_returns", lambda p: FR.compare_factor_return(p, F, y, horizon=h, top_n=len(sel), config=dc["factor_return"]))
    run("long_short_analysis", lambda p: FR.compare_long_short(p, F, y, top_n=len(sel), config=dc["long_short_analysis"]))
    run("factor_centrality", lambda p: CT.compare_factor_centrality(p, ric, sel, dc["factor_centrality"],
                                                                    trend_config=dc["trend_analysis"]))
    run("trend_analysis", lambda p: CT.compare_trend_analysis(
        p, ric, sel, dc["trend_analysis"], rolling_stride=stride, overlap_window="from_key",
        sources=CT._ref_trend_sources(raw, ric, sel, cap["deep_config_obj"], h),
        dimensions=list(dc["trend_analysis"]["dimensions"])))
    run("parameter_sensitivity", lambda p: SO.compare_parameter_sensitivity(
        p, F, y, metadata=meta, config={**dc["parameter_sensitivity"], "icir_window": int(icir_w)}, method=method,
        direction=dirs))
    run("rolling_oos", lambda p: SO.compare_rolling_oos(p, F, y, config=dc["rolling_oos"], horizon=h, method=method,
                                                        direction=dirs, top_n=len(sel)))
    run("factor_orthogonalization", lambda p: OE.compare_factor_orthogonalizer(
        p, F, cache.get("icir") or {}, method=str(dc["factor_orthogonalization"]["method"])))
    fe = dc["factor_exposure"]
    run("factor_exposure", lambda p: OE.compare_factor_exposure_analyzer(
        p, F, cache.get("close_series"), str(fe["neutralization_mode"]), int(fe["neutralization_lookback"]),
        float(fe["max_single_exposure"])))
    rid = {n: pd.Series(CT.ref_extract_rolling_ic_series(v)[1]) for n, v in ric.items() if n in sel and isinstance(v, dict)}
    run("feature_quality_diagnostics", lambda p: QN.compare_feature_quality_diagnostics(
        p, F, rolling_ic_dict=rid, config=dc["feature_quality_diagnostics"]))
    qv = cache.get("quote_value_series")
    avg = QN._ref_daily_quote_volume(qv) if isinstance(qv, pd.Series) else None
    summary = {n: {"ic_mean": rows[n].get("ic_mean"), "avg_daily_quote_volume": avg} for n in sel if n in rows}
    tov = {n: float(d.get("quantile_turnover", 0.0)) for n, d in (rep.get("turnover_analysis") or {}).items()
           if n in sel and isinstance(d, dict)}
    frs = {n: s for n, s in (cap.get("fr_series") or {}).items() if n in sel}
    qc = meta.get("quote_currency") if isinstance(meta.get("quote_currency"), str) and meta.get("quote_currency") else None
    run("net_ic_analysis", lambda p: QN.compare_net_ic_analysis(p, summary, tov, factor_return_series=frs,
                                                                config=dc["net_ic_analysis"], quote_currency=qc))
    return status


#: 跨標的路徑結構上不算之 summary 欄（`ic_filter_orchestrator.py` analyze_cross_sectional 之 None 佔位）
XSEC_PLACEHOLDERS = ("monotonicity_score", "long_short_spread", "coverage", "turnover_rate", "ic_half_life")
#: 跨標的路徑之第 6 段區段（不跑冗餘篩選 ⇒ 空）
XSEC_EMPTY = {"correlation_matrix": {"features": [], "matrix": []}, "diversification_metrics": {}}


def evaluate_cross(cap: Mapping[str, Any], key_of: "KeyOf", items: Dict[str, Tally]) -> Dict[str, Any]:
    """跨標的請求之 oracle（測試檔 `_ref_cross_sectional`：每時點逐特徵 scipy.stats.spearmanr 截面 IC、逐標的逐特徵
    spearmanr、`cross_symbol_validation` 參考實作；截面 IC 序列之 HAC 以 statsmodels）；預設設定之切分不成立而以
    `ic_train_test_split=False` 執行者照該設定對照（擷取之 attempts 記兩次嘗試）。"""
    import math

    import numpy as np

    O = _oracles()
    t = items.setdefault("cross_sectional", Tally("每時點截面 scipy.stats.spearmanr、逐標的 spearmanr、cross_symbol_validation "
                                                  "測試自寫參考實作（_ref_cross_sectional）"))
    rep = cap["ic_report"] or {}
    df = cap["cross_df"]
    label_col = [c for c in df.columns if str(c).startswith("return_")]
    facts = {"attempts": cap.get("attempts"), "shape": list(df.shape), "label_col": label_col,
             "symbols": sorted(map(str, df.index.get_level_values(-1).unique()))}
    if not rep or not label_col:
        t.eq("/cross_sectional_symbol_ic", "report", None, "跨標的報告")
        return facts
    facts["split_applied"] = ((rep.get("metadata") or {}).get("ic_train_test_split") or {}).get("applied")
    exp = O._ref_cross_sectional(df, label_col[0])
    srs = rep.get("rolling_ic_series") or {}
    for f, values in exp["series"].items():
        _tree(t, key_of, f"/rolling_ic_series/{_ptr(f)}/window_cross_sectional",
              (srs.get(f) or {}).get("window_cross_sectional"), values, f)
    rows = {r["feature_name"]: r for r in rep.get("summary_table") or [] if isinstance(r, dict)}
    for f, fields in exp["summary"].items():
        for k, v in fields.items():
            t.num(f"/summary_table/#/{k}", f"{f}/{k}", (rows.get(f) or {}).get(k), v, feature=f)
    _tree(t, key_of, "/cross_sectional_symbol_ic", rep.get("cross_sectional_symbol_ic"), exp["symbol_ic"])
    _tree(t, key_of, "/cross_symbol_validation", rep.get("cross_symbol_validation"), exp["validation"])
    cfg = cap["config"] or {}
    mh = re.match(r"return_(\d+)$", str(label_col[0]))
    h = int(mh.group(1)) if mh else 1
    maxlags = (cfg.get("significance") or {}).get("maxlags")
    t_h = items.setdefault("hac", Tally("statsmodels OLS HAC（Bartlett、無小樣本修正）＋ scipy t 分布＋現行 fail-closed 邊界"))
    t_q = items.setdefault("fdr", Tally("statsmodels multipletests fdr_bh（同檢定集合）"))
    t_d = items.setdefault("direction", Tally("direction＝sign(ic_mean)、icir_aligned＝d·icir、方向對齊勝率與單調性"))
    pv: Dict[str, float] = {}
    for f, values in exp["series"].items():
        z = np.asarray(values, dtype=float)
        z = z[np.isfinite(z)]
        o = _hac_on_series(z, h, maxlags)
        row = rows.get(f) or {}
        t_h.num("/summary_table/#/t_stat", f"xsec/{f}/t_stat", row.get("t_stat"), o["t_stat"], feature=f)
        t_h.num("/summary_table/#/p_value", f"xsec/{f}/p_value", row.get("p_value"), o["p_value"], feature=f)
        pv[f] = o["p_value"]
        s = exp["summary"][f]
        d = 0 if not math.isfinite(s["ic_mean"]) or s["ic_mean"] == 0 else (1 if s["ic_mean"] > 0 else -1)
        neg = float(np.mean(z < 0)) if z.size else math.nan
        t_d.eq("/summary_table/#/direction", f"xsec/{f}/direction", row.get("direction"), d, f)
        t_d.num("/summary_table/#/icir_aligned", f"xsec/{f}/icir_aligned", row.get("icir_aligned"),
                d * s["icir"] if d != 0 and math.isfinite(s["icir"]) else math.nan, feature=f)
        t_d.num("/summary_table/#/ic_hit_rate_aligned", f"xsec/{f}/ic_hit_rate_aligned", row.get("ic_hit_rate_aligned"),
                s["ic_hit_rate"] if d > 0 else (neg if d < 0 else math.nan), feature=f)
        t_d.num("/summary_table/#/monotonicity_score_aligned", f"xsec/{f}/monotonicity_score_aligned",
                row.get("monotonicity_score_aligned"), _aligned_mono({}, d), feature=f)
        for k in XSEC_PLACEHOLDERS:
            t.eq(f"/summary_table/#/{k}", f"xsec/{f}/{k}", row.get(k), None, f)
            t.na(f"/summary_table/#/{k}", "test_cross_sectional_matches_oracle")
        t.eq("/summary_table/#/regime_robust", f"xsec/{f}/regime_robust", row.get("regime_robust"), None, f)
        t.eq("/summary_table/#/regime_robust_reason", f"xsec/{f}/regime_robust_reason", row.get("regime_robust_reason"),
             "regime_analysis_off", f)
    adj = _fdr(pv)
    for f in exp["series"]:
        t_q.num("/summary_table/#/p_value_adj", f"xsec/{f}/p_value_adj", (rows.get(f) or {}).get("p_value_adj"),
                adj.get(f, math.nan), feature=f)
    for key in ("correlation_matrix", "diversification_metrics"):
        if key in rep:
            _tree(t, key_of, f"/{key}", rep.get(key), XSEC_EMPTY.get(key))
    for k in ("/correlation_matrix/features", "/correlation_matrix/matrix", "/diversification_metrics"):
        t.na(k, "test_cross_sectional_matches_oracle")
    return facts


def prefix_invariance(cap: Mapping[str, Any], items: Dict[str, Tally], ks: Sequence[int] = (1, 37),
                      max_features: int = 12) -> None:
    """防偷看未來（SPEC Task 0.3）：以產品第 5 段之真實輸入對與該段收盤，截去末 k 根後前段之 PIT 分位標籤、PIT 排名、逐根換手
    時序、滾動 IC（spearman 與 pearson）與 regime 遮罩皆 `==`（測試檔 `_check_prefix_invariance`，產品函式對自身截斷輸入）；
    特徵取第 5 段輸入中有限值 ≥ 150 之前 max_features 欄（控時：每欄 PIT 為 O(T²)）。"""
    import numpy as np

    O = _oracles()
    t = items.setdefault("prefix_invariance", Tally("截去末 k 根後前段一切逐根序列不變（test_icperf_correctness.py "
                                                    "_check_prefix_invariance；k＝1、37）"))
    pairs = cap.get("stage5_inputs") or []
    if not pairs:
        return
    Fs, ys = pairs[0]
    meta = cap["cache"].get("metadata") or {}
    close = read_kline_close(str(meta.get("symbol")), str(meta.get("timeframe"))).reindex(_utc(Fs.index))
    cols = [c for c in Fs.columns if np.isfinite(Fs[c].to_numpy(dtype=float)).sum() >= 150][:max_features]
    try:
        O._check_prefix_invariance(Fs[cols], ys.reindex(Fs.index), close.set_axis(Fs.index), tuple(ks))
        t.eq("@prefix", f"k={list(ks)}/{len(cols)} 欄", True, True)
    except AssertionError as exc:
        t.eq("@prefix", f"k={list(ks)}", f"AssertionError: {exc}", True)


# ── 涵蓋對映（封閉規則表；未命中 ⇒ unmapped ⇒ FAIL） ───────────────────────────────────────────────────

_ORC = "momentum/Analysis/ic_filter_orchestrator.py"
_REPT = "momentum/Analysis/ic_reporter.py"
_ENG = "momentum/Analysis/ic_engine.py"
#: (正則, oracle 項或 NON_STAT, 產生之檔:行)。依序比對，首個命中者生效；深度分析之 `/results/` 另由 `deep_fields()`。
COVERAGE_RULES: List[tuple] = [
    (r"^/(analysis_status|version|generated_at|oos_guarantees)$", NON_STAT, f"{_REPT}:343"),
    # 區段之狀態物件（未算／停用／不適用之 {status, reason}，如跨標的路徑之 ic_decay、grouped_ic）
    (r"^/[a-z_]+/(status|reason)$", NON_STAT, f"{_REPT}:343"),
    (r"^/(cross_sectional_symbol_ic|cross_symbol_validation)$", NON_STAT, f"{_REPT}:360"),
    (r"^/metadata/ic_window_disclosure/ic_mean_source/", "ic_mean_source", f"{_ORC}:1868"),
    (r"^/metadata/", NON_STAT, f"{_REPT}:345"),
    (r"^/filter_log/", NON_STAT, f"{_ORC}:5067"),
    (r"^/summary_table/#/feature_name$", NON_STAT, f"{_ORC}:5326"),
    (r"^/summary_table/#/(ic_std|icir)$", "rolling_ic_icir", f"{_ENG}:468"),
    (r"^/summary_table/#/ic_hit_rate$", "ic_hit_rate", f"{_ENG}:487"),
    (r"^/summary_table/#/ic_mean$", "ic_mean_source", f"{_ORC}:5303"),
    (r"^/summary_table/#/(direction|icir_aligned|ic_hit_rate_aligned|monotonicity_score_aligned)$", "direction",
     f"{_ORC}:1177"),
    (r"^/summary_table/#/(t_stat|p_value)$", "hac", "momentum/Analysis/statistical_validator.py:74"),
    (r"^/summary_table/#/p_value_adj$", "fdr", "momentum/Analysis/statistical_validator.py:161"),
    (r"^/summary_table/#/ic_half_life$", "ic_decay_fit", f"{_ORC}:5342"),
    (r"^/summary_table/#/(monotonicity_score|long_short_spread|coverage|turnover_rate)$", "summary_passthrough",
     f"{_ORC}:5326"),
    (r"^/summary_table/#/(regime_robust|regime_robust_reason)$", "regime_robust", f"{_ORC}:1199"),
    (r"^/summary_table/#/pass_class$", NON_STAT, f"{_ORC}:2199"),
    (r"^/rolling_ic_series/\*/window_cross_sectional$", "cross_sectional", f"{_ORC}:2219"),
    (r"^/rolling_ic_series/", "rolling_ic_series_sampling", f"{_REPT}:987"),
    (r"^/ic_decay/\*/(ic_values|horizons)$", "ic_decay_values", f"{_ENG}:501"),
    (r"^/ic_decay/\*/", "ic_decay_fit", f"{_ENG}:1150"),
    (r"^/grouped_ic/", "grouped_ic", f"{_ENG}:550"),
    (r"^/quantile_returns/\*/long_short_tstat$", "long_short_tstat", "momentum/Analysis/monotonicity_tester.py:112"),
    (r"^/quantile_returns/", "stage5_pit_stats", "momentum/Analysis/monotonicity_tester.py:181"),
    (r"^/coverage_analysis/", "stage5_pit_stats", "momentum/Analysis/coverage_analyzer.py:46"),
    (r"^/turnover_analysis/", "stage5_pit_stats", "momentum/Analysis/turnover_analyzer.py:211"),
    (r"^/correlation_matrix/", "redundancy_correlation", "momentum/Analysis/redundancy_filter.py:153"),
    (r"^/diversification_metrics", "diversification_metrics", "momentum/Analysis/redundancy_filter.py:287"),
    (r"^/marginal_ic/train_ic", "marginal_ic.train_ic", "momentum/Analysis/marginal_ic.py:302"),
    (r"^/marginal_ic/composite/(status|reason|method|fit_scope|oos_guarantees|excluded)$", NON_STAT,
     "momentum/Analysis/factor_combiner.py:118"),
    (r"^/marginal_ic/composite", "marginal_ic.composite", "momentum/Analysis/factor_combiner.py:162"),
    (r"^/marginal_ic/(per_feature|sequential|removed_candidates)(/|$)", "marginal_ic", "momentum/Analysis/marginal_ic.py:302"),
    (r"^/marginal_ic/", NON_STAT, "momentum/Analysis/marginal_ic.py:170"),
    (r"^/event_task/", NON_STAT, "scripts/icperf_freeze_baseline.py:1897"),
    (r"^/(completed_count|skipped_count|failed_count|total_modules|total_execution_time_s|tier_module_overrides|"
     r"deep_analysis_errors)(/|$)", NON_STAT, f"{_ORC}:2988"),
    (r"^/module_summary/", NON_STAT, f"{_ORC}:2937"),
]
#: 依 metadata 分組且全落 `unknown` 或無任一特徵帶該 metadata ⇒ metadata-missing（特徵 metadata 未帶入）
METADATA_MISSING = [r"^/grouped_ic/by_category/unknown(/|$)", r"^/grouped_ic/by_data_source$"]


def _producer_norm(prod: str) -> str:
    """深度測試檔 producer 字串 → `<repo 相對檔>:<行>`（取首個 `<檔>.py:<數字>`；檔名補 `momentum/Analysis/`；行為函式名者
    以該函式定義行）。"""
    m = re.search(r"([\w./-]+\.py):(\d+)", prod or "")
    if m:
        f = m.group(1) if (REPO / m.group(1)).is_file() else f"momentum/Analysis/{Path(m.group(1)).name}"
        if (REPO / f).is_file():
            return f"{f}:{m.group(2)}"
    m = re.search(r"([\w./-]+\.py):([A-Za-z_]\w*)", prod or "")
    if m:
        f = m.group(1) if (REPO / m.group(1)).is_file() else f"momentum/Analysis/{Path(m.group(1)).name}"
        if (REPO / f).is_file():
            for i, ln in enumerate((REPO / f).read_text(encoding="utf-8").splitlines(), 1):
                if re.match(rf"\s*def {re.escape(m.group(2))}\b", ln):
                    return f"{f}:{i}"
            return f"{f}:1"
    return f"{_ORC}:2835"


def map_key(key: str, deep: Mapping[str, Mapping[str, str]], is_deep: bool, is_cross: bool) -> Optional[tuple]:
    """涵蓋鍵 → (oracle 項, producer, 對照鍵)；未命中 ⇒ None（unmapped）。"""
    if is_cross and re.match(r"^/(cross_sectional_symbol_ic|cross_symbol_validation)(/|$)", key):
        return "cross_sectional", f"{_ORC}:2391", key
    if is_cross and re.match(r"^/summary_table/#/(ic_mean|ic_std|icir|ic_hit_rate)$", key):
        return "cross_sectional", f"{_ORC}:2386", key
    if is_deep and key.startswith("/results/"):
        nk = _norm_deep_key(key)
        match = nk if nk in deep else None
        if match is None:
            # 清冊鍵為本鍵之前綴（如 dimension_status 之值為 dict）⇒ 取最長前綴
            pre = [k for k in deep if nk.startswith(k + "/")]
            match = max(pre, key=len) if pre else None
        if match is None:
            # 本鍵為清冊鍵之前綴（空容器葉，如無參數族之 families）⇒ 該模組之統計項（無內容 ⇒ insufficient-data）
            sub = sorted(k for k in deep if k.startswith(nk + "/"))
            if not sub:
                return None
            stat = [k for k in sub if deep[k].get("oracle") != NON_STAT]
            meta = deep[(stat or sub)[0]]
            return (f"deep.{nk.split('/')[2]}" if stat else NON_STAT), _producer_norm(str(meta.get("producer") or "")), nk
        meta = deep[match]
        oracle = NON_STAT if meta.get("oracle") == NON_STAT else f"deep.{match.split('/')[2]}"
        return oracle, _producer_norm(str(meta.get("producer") or "")), match
    for rx, oracle, prod in COVERAGE_RULES:
        if re.match(rx, key):
            return oracle, prod, key
    return None


def key_status(key: str, oracle: str, items: Mapping[str, Tally]) -> str:
    """單鍵狀態（SPEC Task 0.3 r39 群集 E）：非統計欄 ⇒ non-stat；metadata 分組全落 unknown ⇒ metadata-missing；該項於此鍵有
    內容之比較 ⇒ verified；有比較而皆為 NaN／空且有明列邊界證明 ⇒ verified-na；無內容之比較 ⇒ insufficient-data；未比較
    ⇒ not-compared（收據工具未對照，FAIL）。"""
    if oracle == NON_STAT:
        return "non-stat"
    if any(re.match(rx, key) for rx in METADATA_MISSING):
        return "metadata-missing"
    t = items.get(oracle)
    rec = None if t is None else t.keys.get(key)
    if rec is None:
        return "verified-na" if t is not None and key in t.na_proofs else "not-compared"
    if rec[1] > 0:
        return "verified"
    if key in t.na_proofs:
        return "verified-na"
    return "insufficient-data"


# ── 收據組裝 ──────────────────────────────────────────────────────────────────────────────────────────

#: 收據項之綁定測試（`test_icperf_correctness.py` 內實存之測試函式名）：SPEC 最少項取該檔 `ITEM_TESTS`；其餘項於此列
#: （`<項>.<方法>` 取 `<項>` 之綁定）。
EXTRA_ITEM_TESTS: Dict[str, tuple] = {
    "label": ("test_label_matches_float64_kline_oracle_on_real_kline",),
    "split": ("test_full_sample_fallback_aligns_raw_kline_to_features",
              "test_rolling_ic_test_slice_keeps_whole_test_windows_only"),
    "direction": ("test_direction_neutral_thresholds_pass_strong_reverse_factor",
                  "test_top_features_default_sort_is_direction_aligned"),
    "summary_passthrough": ("test_stage5_pit_stats_match_reference", "test_stage5_pit_stats_match_reference_on_real_kline"),
    "regime_robust": ("test_regime_robust_oracle_suite",),
    **{f"deep.{m}": (f"test_deep_{m}_oracle_suite",) for m in DEEP_MODULES},
}
_KENDALL = {"xfail": "test_rolling_ic_kendall_matches_kendalltau_xfail",
            "reason": "請求 IC 方法為 Kendall 時，滾動 IC 實以 Pearson 計（ic_engine.py compute_rolling_ic 之非 spearman 分支），"
                      "其 ic_mean／ic_std／ICIR／勝率／方向與 regime_robust 隨之非 Kendall 定義",
            "affected": "default_method＝kendall 之請求：summary ic_mean（滾動均值來源）、ic_std、icir、ic_hit_rate、direction、"
                        "icir_aligned、ic_hit_rate_aligned、regime_robust 與 rolling_ic_series；第 5 段 ic_mean／icir／勝率門檻"
                        "之通過集合與 Top-N 排序隨之改變（本收據 A 格 30 欄請求為全樣本研究模式，倖存者 0）"}
_PEARSON = {"xfail": "test_rolling_ic_pearson_price_level_matches_scipy_xfail",
            "reason": "Pearson 滾動 IC 以原值累積和計，價格水準欄相消誤差使逐窗相對誤差超過 1e-12（A 格請求實測至 1e-11 量級、"
                      "明列真實收盤欄輸入至 1e-7 量級）",
            "affected": "default_method＝pearson 之請求：滾動 IC 序列與其 ic_mean／ic_std／icir／勝率／方向欄之低位數；本收據"
                        "資料之門檻判定未因此改變，但不滿足 1e-12"}
_AUTOCORR = {"xfail": "test_turnover_autocorrelation_constant_series_is_nan_xfail",
             "reason": "常數序列之 lag-1 自相關產品回 0.9999999999999998（pandas 浮點殘差），定義上未定義應為 NaN",
             "affected": "turnover_analysis.<特徵>.autocorrelation（L 格測試段與事件匯入批測試段之常數特徵）；此欄不入第 5 段"
                         "門檻與 summary，無通過集合變動"}
_ROLL_IDS = ("rolling_ic_icir", "rolling_ic_series_sampling", "ic_hit_rate", "ic_mean_source", "direction", "regime_robust")
#: 收據之「不一致」項 → 本檔照正確答案寫之 xfail(strict=True) 測試
XFAIL_TESTS: Dict[str, str] = {
    **{f"{i}.kendall": _KENDALL["xfail"] for i in _ROLL_IDS},
    **{f"{i}.pearson": _PEARSON["xfail"] for i in _ROLL_IDS},
    "stage5_pit_stats": _AUTOCORR["xfail"],
    "deep.feature_quality_diagnostics": "test_fq_effective_sample_ratio_price_level_matches_oracle_xfail",
    "deep.trend_analysis": "test_trend_four_dimensions_wide_real_kline_matches_oracle_xfail",
}
#: 「不一致」項之原因、受影響之通過集合與下游判定
FINDINGS: Dict[str, Dict[str, str]] = {
    **{f"{i}.kendall": _KENDALL for i in _ROLL_IDS},
    **{f"{i}.pearson": _PEARSON for i in _ROLL_IDS},
    "stage5_pit_stats": _AUTOCORR,
    "deep.feature_quality_diagnostics": {
        "reason": "價格水準、近單位自相關之特徵，effective_sample_ratio 與 oracle 相對差 1e-12–5e-11（捨入級，非演算法差異）",
        "affected": "feature_quality_diagnostics.autocorrelation_results.<特徵>.effective_sample_ratio；不入篩選門檻與旗標判定"
                    "（旗標以 Ljung–Box p 值判），無通過集合變動"},
    "deep.trend_analysis": {
        "reason": "趨勢之斜率／p 值／尾端估計與 statsmodels OLS＋HAC oracle 相對差 1e-12–1e-11（捨入級，非演算法差異）",
        "affected": "trend_analysis.<特徵>.<維>_trend 之 slope／p_value／tail_estimate 低位數；本收據資料之 trend 判定無變動"},
}
#: 收據項以外之發現（小規模除錯擷取所見之崩潰；收據項不涵蓋者）
EXTRA_FINDINGS: List[Dict[str, Any]] = [
    {"id": "point_ic.spearman.constant_label_crash",
     "evidence": "L.event_import_report 以 10 欄小規模擷取（capture --n-features 10）於第 4 段崩潰：ic_engine.py:1601-1602 "
                 "stats.spearmanr(values, axis=0) 於標籤為常數時回純量、`corr[0, 1:]` 拋 TypeError（120 欄時因含缺值走逐對"
                 "路徑而未觸發）",
     "xfail_test": "test_point_ic_spearman_constant_label_returns_nan_xfail", "ruling": None},
]


def _git_head() -> Optional[str]:
    import subprocess

    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(REPO), capture_output=True, text=True, check=True)
        return out.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _feature_names_of(cap: Mapping[str, Any]) -> List[str]:
    fb = _fb()
    req = cap["request"]
    if req.get("kind") == "cross":
        return sorted(set().union(*(fb._run_feature_names(c) for c in req["cells"])))
    return fb._run_feature_names(req)


def evaluate_request(rid: str, cap: Mapping[str, Any], deep: Mapping[str, Mapping[str, str]]) -> Dict[str, Any]:
    """單一請求：oracle 對照（items）＋逐鍵涵蓋對映與狀態（逐請求封閉：涵蓋鍵＝該請求實際回應之 `flatten_fields` 鍵）。"""
    import collections

    names = _feature_names_of(cap)
    key_of = KeyOf(names)
    items: Dict[str, Tally] = {}
    is_cross = cap["request"].get("kind") == "cross"
    is_deep = cap.get("deep_raw") is not None
    # 報告之 JSON 契約以 null 表未定義之浮點（NaN）：null 與 NaN 視為同值（null 對有限值仍判不一致）
    NULL_IS_NAN["on"] = True
    if is_cross:
        facts = evaluate_cross(cap, key_of, items)
    else:
        facts = evaluate_ic_report(cap, key_of, items)
        if rid in ("A.ic_report", "L.ic_report"):
            prefix_invariance(cap, items)
        if is_deep:
            facts["deep_status"] = evaluate_deep(cap, items)
    cov_paths = coverage_keys(cap["response"], names)
    coverage: Dict[str, Dict[str, Any]] = {}
    unmapped: List[str] = []
    method = str(((cap.get("config") or {}).get("global_settings") or {}).get("default_method") or "spearman")
    for key in sorted(cov_paths):
        m = map_key(key, deep, is_deep, is_cross)
        if m is None:
            unmapped.append(key)
            coverage[key] = {"oracle": None, "producer": None, "status": "unmapped"}
            continue
        oracle = m[0]
        if not is_cross and method != "spearman" and oracle in ROLLING_DERIVED_ITEMS:
            oracle = f"{oracle}.{method}"
        coverage[key] = {"oracle": oracle, "producer": m[1], "status": key_status(m[2], oracle, items),
                         "n_paths": len(cov_paths[key])}
    counts = collections.Counter(v["status"] for v in coverage.values())
    return {"items": items, "coverage": coverage, "unmapped": unmapped, "status_counts": dict(counts), "facts": facts,
            "closed": set(coverage) == set(cov_paths)}


def _merge_items(per_req: Mapping[str, Mapping[str, Tally]]) -> Dict[str, Dict[str, Any]]:
    """逐請求之同一 oracle 項合併：任一請求不一致 ⇒ 不一致；皆一致且至少一請求有比較 ⇒ 一致（最大相對誤差 > 1e-12 ⇒
    不一致）；否則未驗。"""
    out: Dict[str, Dict[str, Any]] = {}
    for iid in sorted({i for items in per_req.values() for i in items}):
        recs = {rid: items[iid].record() for rid, items in per_req.items() if iid in items}
        compared = {r: v for r, v in recs.items() if v["n_compared"]}
        bad = {r: v for r, v in compared.items() if v["verdict"] == "不一致"}
        verdict = "不一致" if bad else ("一致" if compared else "未驗")
        rels = [v["max_rel_diff"] for v in compared.values()]
        max_rel = None if any(v["max_rel_diff"] is None and v["n_mismatch"] for v in compared.values()) else \
            max([r for r in rels if r is not None], default=0.0)
        if verdict == "一致" and max_rel is not None and max_rel > REL_TOL:
            verdict = "不一致"
        first = next(iter(recs.values()))
        out[iid] = {"verdict": verdict, "oracle": first["oracle"], "max_rel_diff": max_rel,
                    "n_compared": sum(v["n_compared"] for v in recs.values()),
                    "n_finite": sum(v["n_finite"] for v in recs.values()),
                    "n_mismatch": sum(v["n_mismatch"] for v in recs.values()),
                    "requests": {r: {k: v[k] for k in ("verdict", "n_compared", "n_finite", "n_mismatch", "max_rel_diff",
                                                         "examples", "n_mismatch_features", "notes")}
                                 for r, v in recs.items()},
                    "mismatch_features": sorted({f for v in bad.values() for f in v["mismatch_features"]})[:50],
                    "n_mismatch_features": sum(v["n_mismatch_features"] for v in bad.values())}
    return out


def build_receipt(captures: Path) -> Dict[str, Any]:
    """收據（SPEC Task 0.3）：{"head", "spec", "generated_at", "tolerance", "data", "items", "coverage", "requests",
    "cross_request", "four_way", "extra_findings", "pass", "fail_reasons"}。頂層 `items`＝各請求同一 oracle 項之合併；頂層
    `coverage`＝§G (1)(4) 之 A 格小請求（`TOP_COVERAGE_REQUESTS`）回應之涵蓋鍵（同 `test_icperf_correctness.py`
    `_coverage_keys` 規則）；`requests`＝逐請求封閉之 coverage（鍵集合 == 該請求實際回應鍵集合）、items 與狀態計數。
    PASS ⇔ 全部請求 rc 0、無 unmapped、每一統計鍵於至少一請求 verified／verified-na、全部項一致。"""
    import datetime as _dt
    import pickle

    O = _oracles()
    captures = Path(captures)
    status = json.loads((captures / "capture_status.json").read_text(encoding="utf-8"))
    deep = deep_fields()
    per_req: Dict[str, Dict[str, Any]] = {}
    caps_meta: Dict[str, Any] = {}
    top_keys: Dict[str, set] = {}
    fail: List[str] = []
    for rid in REQUESTS:
        st = status.get(rid)
        if st is None:
            fail.append(f"{rid}：未擷取")
            continue
        caps_meta[rid] = {"rc": st.get("rc"), "wall_s": st.get("wall_s"), "pickle_bytes": st.get("pickle_bytes"),
                          "error": st.get("error")}
        if st.get("rc") != 0 or not st.get("pickle"):
            fail.append(f"{rid}：擷取 rc={st.get('rc')}（{st.get('log')}）")
            continue
        t0 = time.perf_counter()
        with open(st["pickle"], "rb") as fh:
            cap = pickle.load(fh)
        per_req[rid] = evaluate_request(rid, cap, deep)
        caps_meta[rid].update({"elapsed_s": cap.get("elapsed_s"), "peak_rss_bytes": cap.get("peak_rss_bytes"),
                               "oracle_s": time.perf_counter() - t0, "request": cap["request"]})
        if rid in TOP_COVERAGE_REQUESTS:
            top_keys[rid] = O._coverage_keys(cap["response"])
    merged = _merge_items({r: v["items"] for r, v in per_req.items()})
    item_tests = {**{k: tuple(v) for k, v in O.ITEM_TESTS.items()}, **EXTRA_ITEM_TESTS}
    for iid in sorted(O.REQUIRED_ITEMS - set(merged)):
        merged[iid] = {"verdict": "未驗", "oracle": "（無請求產生此項之可對照輸出）", "max_rel_diff": None, "requests": {}}
    for iid, it in merged.items():
        it["tests"] = list(item_tests.get(iid) or item_tests.get(iid.rsplit(".", 1)[0]) or ())
        if it["verdict"] == "不一致":
            f = FINDINGS.get(iid) or {}
            it.update({"reason": f.get("reason") or "（未定因：見 requests 之 examples）",
                       "features": it.get("mismatch_features") or ["（見 requests 之 examples）"],
                       "affected": f.get("affected") or "（未定）", "ruling": None, "xfail_test": XFAIL_TESTS.get(iid)})
            if it["xfail_test"] and it["xfail_test"] not in it["tests"]:
                it["tests"].append(it["xfail_test"])
        elif it["verdict"] == "未驗":
            it["blocked_reason"] = "無任何請求得此項之可對照輸出（資料不足或請求失敗，見 fail_reasons）"
    # 頂層 coverage：§G (1)(4) 小請求之涵蓋鍵（測試規則），oracle／producer 取該請求之逐鍵對映
    coverage: Dict[str, Dict[str, Any]] = {}
    for rid, keys in top_keys.items():
        rc = per_req[rid]["coverage"]
        for key in sorted(keys):
            m = rc.get(key)
            if m is None:
                mm = map_key(key, deep, False, False)
                m = {"oracle": mm[0] if mm else None, "producer": mm[1] if mm else None,
                     "status": key_status(mm[2], mm[0], per_req[rid]["items"]) if mm else "unmapped"}
            ent = coverage.setdefault(key, {"oracle": m.get("oracle"), "producer": m.get("producer"), "status": {}})
            ent["status"][rid] = m.get("status")
    # 跨請求資料充足：每一統計鍵於至少一請求 verified／verified-na
    stat_keys: Dict[str, Dict[str, str]] = {}
    for rid, rr in per_req.items():
        for key, ent in rr["coverage"].items():
            if ent["status"] != "non-stat":
                stat_keys.setdefault(key, {})[rid] = ent["status"]
    unsatisfied = {k: v for k, v in stat_keys.items() if not any(s in ("verified", "verified-na") for s in v.values())}
    for rid, rr in per_req.items():
        if rr["unmapped"]:
            fail.append(f"{rid}：unmapped 鍵 {len(rr['unmapped'])}（例 {rr['unmapped'][:3]}）")
    if unsatisfied:
        fail.append(f"統計鍵無任一請求 verified／verified-na：{len(unsatisfied)}（例 {sorted(unsatisfied)[:5]}）")
    bad_items = sorted(i for i, v in merged.items() if v["verdict"] != "一致")
    if bad_items:
        fail.append(f"非一致項：{bad_items}")
    requests_out = {rid: {**caps_meta.get(rid, {}), "coverage": rr["coverage"], "unmapped": rr["unmapped"],
                          "closed": rr["closed"], "status_counts": rr["status_counts"], "facts": rr["facts"],
                          "items": {i: {k: t.record()[k] for k in ("verdict", "n_compared", "n_finite", "n_mismatch",
                                                                     "max_rel_diff")} for i, t in rr["items"].items()}}
                    for rid, rr in per_req.items()}
    for rid, meta in caps_meta.items():
        requests_out.setdefault(rid, dict(meta))
    return {
        "head": _git_head(), "spec": "docs/ICPERF_SPEC.md v5.37 Task 0.3（§B ICPERF-BUDGET-7、-9、-10、-11）",
        "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "tolerance": {"relative": REL_TOL, "ssr_slack": SSR_SLACK},
        "data": {"cell": "A_BTCUSDT_1h", "fact_receipt": {rid: rr["facts"] for rid, rr in per_req.items()},
                 "long_cell": "L_BTCUSDT_4h_longhist（handoffs/run_receipts/20261029-icperf-long-cell-4h-longhist.json）",
                 "kline": str(KLINE_H5.relative_to(REPO)), "captures": str(captures)},
        "items": merged, "coverage": coverage, "requests": requests_out,
        "cross_request": {"stat_keys": len(stat_keys), "unsatisfied": {k: unsatisfied[k] for k in sorted(unsatisfied)}},
        "four_way": {rid: {k: m.get(k) for k in ("wall_s", "elapsed_s", "peak_rss_bytes", "pickle_bytes", "oracle_s")}
                     for rid, m in caps_meta.items()},
        "extra_findings": EXTRA_FINDINGS,
        "pass": not fail, "fail_reasons": fail,
    }


def write_receipt(captures: Path, out: Path) -> Dict[str, Any]:
    """組裝收據並寫出 JSON（NaN 以 JSON 擴充字面 NaN 記；收據大小回寫 `four_way._receipt_bytes`）。"""
    receipt = build_receipt(captures)
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, ensure_ascii=False, indent=1, default=str, allow_nan=True) + "\n", encoding="utf-8")
    receipt["four_way"]["_receipt_bytes"] = out.stat().st_size
    out.write_text(json.dumps(receipt, ensure_ascii=False, indent=1, default=str, allow_nan=True) + "\n", encoding="utf-8")
    return receipt


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="icperf_correctness_receipt.py", description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd")
    p = sub.add_parser("capture", help="逐請求執行產品並擷取輸入與回應")
    p.add_argument("--out-dir", type=Path, required=True)
    p.add_argument("--requests", default=",".join(REQUESTS), help="請求 id（逗號分隔）")
    p.add_argument("--n-features", type=int, default=None, help="子集欄數上限覆寫（小規模除錯；不改 REQUESTS 預設）")
    p = sub.add_parser("receipt", help="由擷取檔組裝收據（只讀擷取檔，非重型）")
    p.add_argument("--captures", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p = sub.add_parser(CHILD_CMD)
    p.add_argument("spec", type=Path)
    args = parser.parse_args(argv)
    if args.cmd == CHILD_CMD:
        return _child_main(args.spec)
    if args.cmd == "receipt":
        rec = write_receipt(args.captures, args.out)
        print(json.dumps({"out": str(args.out), "pass": rec["pass"], "fail_reasons": rec["fail_reasons"],
                          "verdicts": {k: v["verdict"] for k, v in rec["items"].items()}}, ensure_ascii=False, indent=1))
        return 0
    if args.cmd == "capture":
        ids = [s for s in str(args.requests).split(",") if s]
        unknown = [s for s in ids if s not in REQUESTS]
        if unknown:
            print(f"未知請求：{unknown}", file=sys.stderr)
            return 2
        if args.n_features:
            os.environ[N_FEATURES_ENV] = str(int(args.n_features))
        status = capture(ids, args.out_dir)
        return 0 if all(s.get("rc") == 0 for s in status.values()) else 1
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
