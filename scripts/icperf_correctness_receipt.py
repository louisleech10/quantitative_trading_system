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

用法（重型，列 `scripts/heavy_commands.json` 之 `self_watched`：須背景、先寫估時收據）：
  venv/bin/python scripts/icperf_correctness_receipt.py capture --out-dir <擷取目錄> [--requests <id>,...]
  venv/bin/python scripts/icperf_correctness_receipt.py receipt --captures <擷取目錄> --out <收據 JSON>
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

REPO = Path(__file__).resolve().parents[1]
CHILD_CMD = "_child"
#: 特徵子集之 seed（同凍結腳本 `SEED`）
SEED = 20261027
#: 逐請求之定義：凍結項（請求設定取 `default_request`）、特徵子集欄數（SPEC §B BUDGET-7：A 格小規模子集數十至數百欄；
#: L 格同；None＝不限縮〔事件匯入批之事件列少，全欄〕）
REQUESTS: Dict[str, Dict[str, Any]] = {
    "A.ic_report": {"item": "ic_report", "n_features": 120},
    "A.event_report": {"item": "event_report", "n_features": 120},
    "A.deep_analysis": {"item": "deep_analysis", "n_features": 120},
    "L.ic_report": {"item": "ic_report_long", "n_features": 120},
    "L.deep_analysis": {"item": "deep_analysis_long", "n_features": 120},
    "L.event_import_report": {"item": "event_import_report", "n_features": 120},
    # r42 群集 D／F：IC-11 待驗——12h 格特徵來自長歷史檔而 IC 頁標籤讀主檔，記標籤有限列比例
    "A12.ic_report": {"item": "ic_report", "n_features": 20, "cell": "A_BTCUSDT_12h"},
}
#: 分析器快取中供 oracle 之鍵（`ic_filter_orchestrator.py` `self._ic_cache = {...}`）
CACHE_KEYS = ("features_df", "label_series", "close_series", "metadata", "split_context", "event_info",
              "feature_filter_info")


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


def request_for(req_id: str) -> Dict[str, Any]:
    """請求 id ⇒ 凍結腳本之預設請求加特徵子集（`feature_filter.include_features`）。"""
    fb = _fb()
    spec = REQUESTS[req_id]
    request = fb.default_request(spec["item"], spec["cell"]) if spec.get("cell") else fb.default_request(spec["item"])
    names = subset_names(fb._run_feature_names(request), spec["n_features"])
    request["feature_filter"] = {"include_features": names}
    request["receipt_request_id"] = req_id
    return request


# ── 子行程：執行產品並擷取輸入 ───────────────────────────────────────────────────────────────────────────


def _config_dump(analyzer: Any) -> Any:
    cfg = getattr(analyzer, "_config", None)
    return cfg.model_dump() if hasattr(cfg, "model_dump") else None


def _child_capture(spec: Mapping[str, Any]) -> Dict[str, Any]:
    """依請求執行產品（IC 頁／深度分析／事件匯入批），回 {"request", "response", "ic_report", "cache", "stage5_inputs",
    "config", "selected"}：`response`＝該凍結項之回應形狀（IC 頁＝報告；深度＝序列化深度報告；事件匯入批＝任務欄）、
    `ic_report`＝同一次 analyze 之報告（深度與事件匯入批亦存，供 IC 報告欄之 oracle）。"""
    from api.models.ic_models import DeepAnalysisRequest

    fb = _fb()
    request = spec["request"]
    registry = Path(spec["registry"])
    deep_payload = None
    selected = None
    with fb._stage5_input_spy(stop=False) as calls:
        if request.get("event_import_id"):
            info = fb.event_import_run(request, registry)
            analyzer = info["analyzer"]
            response = fb.event_import_response(info)
            report = info.get("result")
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
                deep_payload = svc._attach_cross_symbol_context(svc._serialize_deep_report(deep_report), analyzer)
                response = deep_payload
    cache = dict(getattr(analyzer, "_ic_cache", None) or {})
    return {"request": request, "response": response, "ic_report": report,
            "cache": {k: cache.get(k) for k in CACHE_KEYS},
            "stage5_inputs": list(calls), "config": _config_dump(analyzer), "selected": selected}


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
    for rid in req_ids:
        request = request_for(rid)
        work = Path(tempfile.mkdtemp(prefix=f"icperf-correct-{rid}-"))
        cap = work / "capture"
        cap.mkdir(parents=True)
        out = out_dir / f"{rid}.pkl"
        spec = {"request": request, "registry": str(cap / "registry.json"), "out_pickle": str(out)}
        spec_path = cap / "spec.json"
        spec_path.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
        cmd = [sys.executable, str(Path(__file__).resolve()), CHILD_CMD, str(spec_path)]
        try:
            res = fb.run_watched(cmd, log_path=cap / "run.log",
                                 env=fb.isolated_env(fb._child_env_base(), work / "iso"),
                                 cwd=fb._prepare_cwd(work / "cwd"))
            status[rid] = {"rc": res["rc"], "pickle": str(out) if out.is_file() else None, "log": res["log_path"]}
        except fb.FreezeError as exc:
            status[rid] = {"rc": None, "pickle": None, "log": str(cap / "run.log"), "error": str(exc)}
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


class Tally:
    """一個 oracle 項之逐值對照累計：比較數、有限值數、最大相對誤差、不一致之前若干例。"""

    def __init__(self, oracle: str) -> None:
        self.oracle, self.n, self.n_finite, self.max_rel = oracle, 0, 0, 0.0
        self.mismatch: List[Dict[str, Any]] = []
        self.n_mismatch = 0
        self.notes: List[str] = []

    def num(self, where: str, prod: Any, orc: Any, tol: float = REL_TOL) -> None:
        import math

        self.n += 1
        p, o = _f(prod), _f(orc)
        if p is None or o is None:
            ok = (prod is None and orc is None) or (p is None and o is None and prod == orc)
            d = 0.0 if ok else math.inf
        elif math.isnan(p) and math.isnan(o):
            d = 0.0
        elif math.isnan(p) or math.isnan(o):
            d = math.inf
        else:
            d = abs(p - o) / abs(o) if o != 0 else abs(p - o)
        if p is not None and o is not None and math.isfinite(p) and math.isfinite(o):
            self.n_finite += 1
        self.max_rel = max(self.max_rel, d) if math.isfinite(d) else math.inf
        if d > tol:
            self._miss(where, prod, orc)

    def eq(self, where: str, prod: Any, orc: Any) -> None:
        self.n += 1
        if prod is not None:
            self.n_finite += 1
        if _canon(prod) != _canon(orc):
            self._miss(where, prod, orc)

    def _miss(self, where: str, prod: Any, orc: Any) -> None:
        self.n_mismatch += 1
        if len(self.mismatch) < 12:
            self.mismatch.append({"where": where, "product": _short(prod), "oracle": _short(orc)})

    def record(self) -> Dict[str, Any]:
        import math

        verdict = "未驗" if self.n == 0 else ("一致" if self.n_mismatch == 0 else "不一致")
        return {"verdict": verdict, "oracle": self.oracle, "n_compared": self.n, "n_finite": self.n_finite,
                "n_mismatch": self.n_mismatch, "max_rel_diff": None if not math.isfinite(self.max_rel) else self.max_rel,
                "examples": self.mismatch, "notes": self.notes}


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


def _tree(t: Tally, where: str, got: Any, exp: Any) -> None:
    """巢狀逐葉對照（鍵集合須同；浮點以相對誤差；其餘 ==）。"""
    import numpy as np

    if isinstance(exp, Mapping):
        if not isinstance(got, Mapping):
            t._miss(where, got, "dict")
            return
        gk, ek = set(map(str, got)), set(map(str, exp))
        if gk != ek:
            t._miss(where + "#keys", sorted(gk), sorted(ek))
        gm = {str(k): v for k, v in got.items()}
        for k, v in exp.items():
            if str(k) in gm:
                _tree(t, f"{where}/{k}", gm[str(k)], v)
    elif isinstance(exp, (list, tuple)):
        if not isinstance(got, (list, tuple)) or len(got) != len(exp):
            t._miss(where + "#len", len(got) if isinstance(got, (list, tuple)) else got, len(exp))
            return
        for i, (g, e) in enumerate(zip(got, exp)):
            _tree(t, f"{where}/{i}", g, e)
    elif isinstance(exp, (float, np.floating)) and not isinstance(exp, bool):
        t.num(where, got, exp)
    else:
        t.eq(where, got, exp)


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


def oracle_rolling_ic(F: Any, y: Any, window: int, allowed: Any, test: Any) -> Dict[str, List[float]]:
    """滾動 Spearman IC 之 oracle（SPEC Task 0.4 ④ 鎖定之定義）：時間軸＝`allowed` 列中標籤有限者；固定窗依軸之列位置
    滑動（步長 1）；每窗每特徵獨立——窗內該特徵或標籤有任一非有限值 ⇒ NaN，否則以 scipy 平均秩之 Pearson（＝Spearman）；
    `test` 非 None ⇒ 只留窗終點落在 test 之窗。回 {特徵: [IC, …]}。"""
    import numpy as np
    from scipy import stats

    X = F.to_numpy(dtype=float)
    yv = y.to_numpy(dtype=float)
    keep = np.asarray(allowed, dtype=bool) & np.isfinite(yv)
    rows = np.flatnonzero(keep)
    out = {c: [] for c in F.columns}
    if rows.size < window or window <= 1:
        return out
    tmask = None if test is None else np.asarray(test, dtype=bool)
    for end in range(window - 1, rows.size):
        if tmask is not None and not tmask[rows[end]]:
            continue
        sel = rows[end - window + 1:end + 1]
        xw, yw = X[sel], yv[sel]
        ry = stats.rankdata(yw)
        for j, c in enumerate(F.columns):
            col = xw[:, j]
            if not np.all(np.isfinite(col)) or np.ptp(col) == 0 or np.ptp(yw) == 0:
                out[c].append(float("nan"))
                continue
            out[c].append(float(np.corrcoef(stats.rankdata(col), ry)[0, 1]))
    return out


def evaluate_ic_report(cap: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    """IC 報告欄之 oracle 對照（逐項 Tally 記錄）。報告取 `cap["ic_report"]`；輸入取擷取之分析器快取與第 5 段輸入對。"""
    import math

    import numpy as np
    import pandas as pd

    O = _oracles()
    rep = cap["ic_report"]
    rep = rep if isinstance(rep, dict) else getattr(rep, "__dict__", {})
    cfg = cap["config"] or {}
    cache = cap["cache"]
    F, y = cache["features_df"], cache["label_series"]
    sc = cache.get("split_context")
    meta = cache.get("metadata") or {}
    method = str(cfg["global_settings"]["default_method"])
    horizon = int(cfg["global_settings"]["default_horizon"])
    items: Dict[str, Tally] = {}

    def T(iid: str, oracle: str) -> Tally:
        return items.setdefault(iid, Tally(oracle))

    rows = {r["feature_name"]: r for r in rep.get("summary_table") or []}
    close_full = read_kline_close(str(meta.get("symbol")), str(meta.get("timeframe")))
    # 標籤
    t = T("label", "close[t+h]/close[t]−1（kline_cache.h5 直接讀、截至特徵末根）")
    lab = oracle_label(close_full, F.index, horizon, str(cfg["labels"]["return_type"]))
    for ts, pv, ov in zip(F.index, y.to_numpy(dtype=float), lab.to_numpy(dtype=float)):
        t.num(f"label@{ts}", pv, ov)
    # 切分
    t = T("split", "holdout 參考實作：train＝前 floor(0.8N)、purge＝label horizon、test＝其餘；任一段 < min_test_rows ⇒ 退回")
    osp = oracle_split(len(F), cfg, horizon)
    t.eq("applied", sc is not None, osp["applied"])
    if sc is not None:
        trm, tem = np.asarray(sc["train_mask"], bool), np.asarray(sc["test_mask"], bool)
        exp_tr = np.zeros(len(F), bool)
        exp_tr[:osp["n_train"]] = True
        exp_te = np.zeros(len(F), bool)
        exp_te[osp["test_start"]:] = True
        t.eq("train_mask", np.flatnonzero(trm != exp_tr).tolist(), [])
        t.eq("test_mask", np.flatnonzero(tem != exp_te).tolist(), [])
    test_mask = None if sc is None else np.asarray(sc["test_mask"], bool)
    F_ic = F if test_mask is None else F.loc[test_mask]
    y_ic = y if test_mask is None else y.loc[test_mask]
    # 點 IC（ic_mean 之 pooled 來源）
    point = {c: O._ic_oracle(F_ic[c].to_numpy(float), y_ic.to_numpy(float), method) for c in F.columns}
    # 滾動 IC／ICIR／勝率／抽樣序列
    windows = [int(k.split("_", 1)[1]) for k in next(iter((rep.get("rolling_ic_series") or {}).values()), {})]
    if not windows:
        tf = str(meta.get("timeframe"))
        windows = [int(w) * {"1h": 12, "4h": 3, "12h": 1}.get(tf, 1) for w in cfg["ic_calculation"]["rolling_windows"]]
    allowed = np.ones(len(F), bool) if sc is None else (np.asarray(sc["train_mask"], bool) | test_mask)
    roll = {w: oracle_rolling_ic(F.loc[allowed], y.loc[allowed], w, np.ones(int(allowed.sum()), bool),
                                 None if test_mask is None else test_mask[allowed]) for w in windows}
    icir_w = int(cfg["ic_calculation"]["icir"]["window"]) * (max(windows) // max(1, max(cfg["ic_calculation"]["rolling_windows"])))
    t_r = T("rolling_ic_icir", "滾動 Spearman（逐特徵獨立、標籤有限之時間軸、scipy 平均秩）＋ nanmean／nanstd／比值／有限值 >0 比例")
    t_s = T("rolling_ic_series_sampling", "oracle 滾動序列經測試自寫抽樣參考實作（ic_reporter 之上限規則）")
    t_m = T("ic_mean_source", "滾動均值有限 ⇒ 用之，否則 pooled 點 IC（scipy）")
    max_points = int(((cfg.get("report") or {}).get("max_series_points")) or 1000)
    srs = rep.get("rolling_ic_series") or {}
    for c in F.columns:
        row = rows.get(c)
        series = O._ref_sample({c: {f"window_{w}": roll[w][c] for w in windows}}, max_points)[c]
        for w in windows:
            got = (srs.get(c) or {}).get(f"window_{w}")
            if got is not None or c in srs:
                _tree(t_s, f"{c}/window_{w}", got, series[f"window_{w}"])
        vals = roll.get(icir_w, roll[windows[0]] if windows else [])[c] if windows else []
        o = O._icir_oracle(vals)
        hit = O._finite_hit_rate(vals) if vals else math.nan
        if row is not None:
            t_r.num(f"{c}/ic_std", row.get("ic_std"), o["ic_std"])
            t_r.num(f"{c}/icir", row.get("icir"), o["icir"])
            t_r.num(f"{c}/ic_hit_rate", row.get("ic_hit_rate"), hit)
            exp_mean = o["ic_mean"] if math.isfinite(o["ic_mean"]) else point[c]
            t_m.num(f"{c}/ic_mean", row.get("ic_mean"), exp_mean)
    # 衰減
    t_d = T("ic_decay_values", "逐 horizon：收盤截至特徵段之 h 根前瞻報酬 vs 特徵，scipy 對應方法")
    t_f = T("ic_decay_fit", "curve_fit 固定起點集合之最小殘差（最佳性）＋衍生欄依產品參數重算")
    close_ic = close_full.reindex(_utc(F_ic.index))
    decay = rep.get("ic_decay") or {}
    for c in F.columns:
        d = decay.get(c)
        if d is None:
            continue
        hs = list(d.get("horizons") or cfg["ic_calculation"]["ic_decay_horizons"])
        exp_vals = []
        for h in hs:
            r_h = (close_ic.shift(-int(h)) / close_ic - 1.0).to_numpy(float)
            exp_vals.append(O._ic_oracle(F_ic[c].to_numpy(float), r_h, method))
        _tree(t_d, f"{c}/ic_values", d.get("ic_values"), exp_vals)
        fin = [v for v in exp_vals if math.isfinite(v)]
        if len(fin) < 3:
            t_f.eq(f"{c}/decay_type", d.get("decay_type"), "fit_failed")
        else:
            best = O._oracle_min_ssr(hs, exp_vals)
            if d.get("decay_type") == "fit_failed":
                t_f.eq(f"{c}/fit_failed", "fit_failed", "oracle 擬合成功" if math.isfinite(best) else "fit_failed")
            else:
                pss = O._product_ssr(d.get("ic_values"), {"r2": d.get("fit_r2")})
                t_f.eq(f"{c}/ssr_optimal", bool(pss <= best * (1 + 1e-9) + 1e-300), True)
                lam = _f(d.get("decay_rate"))
                t_f.num(f"{c}/half_life", d.get("half_life"), math.log(2) / lam if lam and lam > 0 else math.nan)
                t_f.eq(f"{c}/decay_type", d.get("decay_type"),
                       "exponential" if float(d.get("fit_r2")) >= 0.5 else "non_exponential")
        t_f.eq(f"{c}/peak_horizon", d.get("peak_horizon"), O._ref_peak(hs, exp_vals))
        if row := rows.get(c):
            t_f.num(f"{c}/summary_half_life", row.get("ic_half_life"), d.get("half_life"))
    # 分組 IC
    t_g = T("grouped_ic", "年度／regime 規則／metadata 分組，逐組 scipy（測試自寫 _ref_grouped_ic）")
    gcfg = cfg["ic_calculation"]["grouped_analysis"]
    fmeta = {c: (meta.get(c) or {}) for c in F.columns}
    exp_g = O._ref_grouped_ic(F_ic, y_ic, close_ic.set_axis(F_ic.index), fmeta, method)
    got_g = rep.get("grouped_ic") or {}
    for key in ("by_year", "by_quarter", "by_regime", "by_category", "by_data_source", "by_layer"):
        if key in got_g or gcfg.get(key):
            _tree(t_g, key, got_g.get(key, {}), exp_g.get(key, {}) if gcfg.get(key) else {})
    # 第 5 段：HAC、FDR、逐根 PIT 統計
    t_h = T("hac", "statsmodels OLS HAC（Bartlett、無小樣本修正）＋ scipy t 分布；測試自寫 _hac_oracle")
    t_q = T("fdr", "statsmodels multipletests fdr_bh（同檢定集合）")
    t_p = T("stage5_pit_stats", "逐根 PIT 參考實作（_ref_monotonicity／_ref_turnover／_ref_coverage）")
    pairs = cap.get("stage5_inputs") or []
    if pairs:
        Fs, ys = pairs[0]
        pv: Dict[str, float] = {}
        for c in Fs.columns:
            x, yy = Fs[c].to_numpy(float), ys.to_numpy(float)
            ok = np.isfinite(x) & np.isfinite(yy)
            try:
                o = O._hac_oracle(x[ok], yy[ok], horizon) if ok.sum() >= 3 else {"t_stat": math.nan, "p_value": math.nan}
            except Exception as exc:  # noqa: BLE001 — oracle 於邊界輸入失敗 ⇒ 記錄，不中斷
                o = {"t_stat": math.nan, "p_value": math.nan}
                t_h.notes.append(f"{c}: oracle {exc!r}")
            if (row := rows.get(c)) is not None:
                t_h.num(f"{c}/t_stat", row.get("t_stat"), o["t_stat"])
                t_h.num(f"{c}/p_value", row.get("p_value"), o["p_value"])
                pv[c] = _f(row.get("p_value")) if _f(row.get("p_value")) is not None else math.nan
        fin = {c: p for c, p in pv.items() if math.isfinite(p)}
        if fin:
            from statsmodels.stats.multitest import multipletests

            adj_p = multipletests(list(fin.values()), method="fdr_bh")[1]
            for (c, _), a in zip(fin.items(), adj_p):
                t_q.num(f"{c}/p_value_adj", rows[c].get("p_value_adj"), float(a))
        qr, cov, tov = rep.get("quantile_returns") or {}, rep.get("coverage_analysis") or {}, rep.get("turnover_analysis") or {}
        for c in Fs.columns:
            if c in qr:
                ref = O._ref_monotonicity(Fs[c], ys)
                _tree(t_p, f"quantile_returns/{c}", qr[c], {**ref["quantile_returns"],
                                                            "monotonicity_score": ref["monotonicity_score"]})
            if c in cov:
                _tree(t_p, f"coverage_analysis/{c}", cov[c], O._ref_coverage(Fs[c]))
            if c in tov:
                _tree(t_p, f"turnover_analysis/{c}", tov[c], O._ref_turnover(Fs[c]))
    # summary 透傳與門檻
    t_x = T("summary_passthrough", "summary 列各欄 == 同請求之第 5 段／衰減輸出")
    for c, row in rows.items():
        q = (rep.get("quantile_returns") or {}).get(c) or {}
        t_x.num(f"{c}/monotonicity_score", row.get("monotonicity_score"), q.get("monotonicity_score"))
        t_x.num(f"{c}/long_short_spread", row.get("long_short_spread"), q.get("long_short_spread"))
        t_x.num(f"{c}/coverage", row.get("coverage"), ((rep.get("coverage_analysis") or {}).get(c) or {}).get("coverage"))
        t_x.num(f"{c}/turnover_rate", row.get("turnover_rate"),
                ((rep.get("turnover_analysis") or {}).get(c) or {}).get("quantile_turnover"))
    return {k: v.record() for k, v in items.items()}


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


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="icperf_correctness_receipt.py", description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd")
    p = sub.add_parser("capture", help="逐請求執行產品並擷取輸入與回應")
    p.add_argument("--out-dir", type=Path, required=True)
    p.add_argument("--requests", default=",".join(REQUESTS), help="請求 id（逗號分隔）")
    p = sub.add_parser(CHILD_CMD)
    p.add_argument("spec", type=Path)
    args = parser.parse_args(argv)
    if args.cmd == CHILD_CMD:
        return _child_main(args.spec)
    if args.cmd == "capture":
        ids = [s for s in str(args.requests).split(",") if s]
        unknown = [s for s in ids if s not in REQUESTS]
        if unknown:
            print(f"未知請求：{unknown}", file=sys.stderr)
            return 2
        status = capture(ids, args.out_dir)
        return 0 if all(s.get("rc") == 0 for s in status.values()) else 1
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
