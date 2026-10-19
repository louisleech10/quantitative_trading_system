"""FFDSTAR Task 1.2（docs/FFDSTAR_SPEC.md）：前處理器之逐欄執行狀態收集。

受測物：`FeaturePreprocessor` 之 run 層級執行紀錄容器（存取點經 `preprov_helpers.preprocessor_records`／
`preprocessor_groups` 單一假設點）、`_merge_decisions_from`、`FeatureFactory._capture_stationarity_decisions`。
真實 kline 短窗 run（同模組同格只生成一次）；單元案例之特徵值取自真實 run 之落盤欄（非合成）。
實作前應為紅；不得以 skip／xfail 暫避。
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple

import numpy as np
import pandas as pd
import pytest

from momentum.FeatureEngineering import run_provenance as rp
from tests.feature_engineering import ffstat_helpers as fsh
from tests.feature_engineering import preprov_helpers as ph

pytestmark = pytest.mark.requires_kline

Key = Tuple[str, str]


@pytest.fixture(scope="module")
def runs(tmp_path_factory: pytest.TempPathFactory) -> ph.RunCache:
    return ph.RunCache(tmp_path_factory.mktemp("preprov_collect"))


# ---------------------------------------------------------------------------------------------- oracle

def l65_input_keys(obs: ph.Observation) -> List[Key]:
    """觀測到之 L6.5 輸入欄（(原生週期, L6.5 所見欄名)；保留重複以驗無碰撞）。"""
    return [(tf, col) for cols, _arr, tf, _layer in obs.l65_inputs.values() for col in cols]


def record_violations(records: Mapping[Key, Mapping[str, Any]], inputs: Sequence[Key],
                      spec: Mapping[str, Any]) -> List[str]:
    """① 每個輸入欄恰一筆紀錄（無多無缺）、各步驟狀態皆非 null 且屬契約值集。"""
    out: List[str] = []
    if len(inputs) != len(set(inputs)):
        out.append("L6.5 輸入鍵有重複（鍵碰撞）")
    missing, extra = sorted(set(inputs) - set(records)), sorted(set(records) - set(inputs))
    if missing:
        out.append(f"缺紀錄 {len(missing)} 欄（例 {missing[:3]}）")
    if extra:
        out.append(f"多出紀錄 {len(extra)} 欄（例 {extra[:3]}）")
    for key, record in records.items():
        for step in spec["steps"]:
            value = record.get(step)
            if value is None or value not in ph.contract_values(f"step_status_values.{step}", spec):
                out.append(f"{key}.{step}={value!r} 不屬契約")
    return out


def _preprocessor_config(cell: str) -> Dict[str, Any]:
    from momentum.factories import create_feature_factory

    factory = create_feature_factory(cache_dir=ph.KLINE_DIR, validate_continuity=False)
    return factory._resolve_config(copy.deepcopy(ph.CELLS[cell]["payload"])).preprocessing.model_dump()


def _unit_preprocessor(runs: ph.RunCache, *, nan_history: bool) -> Tuple[Any, Any]:
    """真實 run（h1_stat_off）之 L1 特徵欄 ＋ 平穩化開啟之前處理器；`nan_history` ⇒ 校準前史全無有效值。"""
    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

    frame, layers = ph.real_feature_frame(runs.get("h1_stat_off"), 6, layer="L1")
    pre = FeaturePreprocessor(_preprocessor_config("h1_stat_on"), column_layer_map=layers)
    history = frame.copy()
    if nan_history:
        history.loc[:, :] = np.nan
    fsh.attach_unit_calibration(pre, history)
    return pre, frame


def conflict_raises(owner: Any, child: Any) -> bool:
    try:
        owner._merge_decisions_from(child)
    except rp.ProvenanceConflictError:
        return True
    return False


def _real_decision(runs: ph.RunCache) -> Tuple[Key, Dict[str, Any], Dict[str, Any]]:
    pre = ph.observation(runs.get("h1_stat_on")).l65_preprocessor
    key, record = next(iter(pre.stationarity_decisions().items()))
    return key, dict(record), dict(pre._config)


def _isolated_unit_preprocessor(runs: ph.RunCache, mp: pytest.MonkeyPatch, cache_dir: Path, *,
                                n_jobs: int) -> Tuple[Any, Any]:
    """`_unit_preprocessor`（真實 L1 欄、平穩化開）＋ d* 快取導向新目錄 `cache_dir`（必未命中；不寫專案 data_cache）＋
    固定 slow path worker 數（1＝純串行；>1＝parallel 臂）。"""
    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=False)
    mp.setattr(FeaturePreprocessor, "_d_star_cache_dir", staticmethod(lambda: cache_dir))
    mp.setattr(FeaturePreprocessor, "_resolve_slowpath_n_jobs", lambda self: n_jobs)
    return _unit_preprocessor(runs, nan_history=False)


def _unit_inputs(frame: Any) -> List[Key]:
    return [("1h", str(c)) for c in frame.columns]


# ---------------------------------------------------------------------------------------------- (a) d* 搜尋鏈內之紀錄錯誤

def dstar_search_provenance_error_outcome(runs: ph.RunCache, cache_dir: Path) -> Dict[str, Any]:
    """純串行 fracdiff；於 `_find_min_d` 呼叫鏈內之紀錄點（`_calibration_lookup`：記校準範圍與事件之決策紀錄點）注入
    `ProvenanceConflictError`。回傳 {"raised": 上拋之 ProvenanceError 或 None, "fired": 觸發欄, "failed": d* 搜尋失敗欄}。
    呼叫當下已安裝之 `_find_min_d`（含 mutation 換入者）為被包對象。"""
    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

    fired: List[str] = []
    state = {"inside": 0}
    raised: Optional[BaseException] = None
    with pytest.MonkeyPatch.context() as mp:
        pre, frame = _isolated_unit_preprocessor(runs, mp, cache_dir, n_jobs=1)
        orig_find = FeaturePreprocessor._find_min_d
        orig_lookup = FeaturePreprocessor._calibration_lookup

        def find(self: Any, series: Any, **kwargs: Any) -> Any:
            state["inside"] += 1
            try:
                return orig_find(self, series, **kwargs)
            finally:
                state["inside"] -= 1

        def lookup(self: Any, column: str, public_values: Any = None) -> Any:
            if state["inside"] and not fired:
                fired.append(str(column))
                raise rp.ProvenanceConflictError(f"injected：{column} 於 d* 搜尋鏈內之紀錄衝突")
            return orig_lookup(self, column, public_values)

        mp.setattr(FeaturePreprocessor, "_find_min_d", find)
        mp.setattr(FeaturePreprocessor, "_calibration_lookup", lookup)
        try:
            pre.transform(frame)
        except rp.ProvenanceError as exc:
            raised = exc
    return {"raised": raised, "fired": fired, "failed": {str(c) for c in pre._dstar_failed_columns}}


def dstar_error_violations(outcome: Mapping[str, Any]) -> List[str]:
    """oracle（SPEC Task 1.2 改法）：d* 搜尋鏈內之 `ProvenanceError` 屬 `NON_DEGRADABLE_ERRORS` ⇒ 原樣上拋，不得被包住
    `_find_min_d` 之 `except Exception` 轉為 d* 搜尋失敗而續跑。"""
    out: List[str] = []
    if not outcome["fired"]:
        out.append("注入未觸發（d* 搜尋鏈未經紀錄點）⇒ 空轉")
    if outcome["raised"] is None:
        out.append("ProvenanceError 被吞（轉為 d* 搜尋失敗續跑）")
    elif not isinstance(outcome["raised"], rp.ProvenanceConflictError):
        out.append(f"上拋型別被改：{type(outcome['raised']).__name__}")
    if set(outcome["fired"]) & set(outcome["failed"]):
        out.append(f"觸發欄被記為 d* 搜尋失敗：{sorted(set(outcome['fired']) & set(outcome['failed']))}")
    return out


# ---------------------------------------------------------------------------------------------- (b) parallel→serial 回退

def fracdiff_fallback_run(runs: ph.RunCache, cache_dir: Path, *, fail_parallel: bool) -> Dict[str, Any]:
    """`fail_parallel`：parallel 臂（2 worker）於第一欄之決策已記為 fracdiff 套用之後、下一欄註冊衍生校準時注入一般
    （可降級）例外 ⇒ 生產既有之 parallel→serial 回退；另記失敗當下已記錄之欄（touched）與串行嘗試中 d* 快取命中之欄。
    False ⇒ 純串行（1 worker）對照。皆用新 d* 快取目錄。回傳 {"pre", "output", "inputs", "touched", "serial_hits",
    "fired", "serial_after_failure"}。"""
    from momentum.FeatureEngineering.preprocessing._d_star_cache import DStarCache
    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

    state: Dict[str, Any] = {"in_parallel": False, "in_serial": False, "fired": False, "touched": set(),
                             "serial_hits": set(), "serial_after_failure": False}
    with pytest.MonkeyPatch.context() as mp:
        pre, frame = _isolated_unit_preprocessor(runs, mp, cache_dir, n_jobs=2 if fail_parallel else 1)
        if fail_parallel:
            orig_parallel = FeaturePreprocessor._apply_fractional_differencing_parallel
            orig_serial = FeaturePreprocessor._apply_fractional_differencing_serial
            orig_register = FeaturePreprocessor._register_derived_calibration
            orig_get = DStarCache.get

            def parallel(self: Any, *args: Any, **kwargs: Any) -> Any:
                state["in_parallel"] = True
                try:
                    return orig_parallel(self, *args, **kwargs)
                finally:
                    state["in_parallel"] = False

            def serial(self: Any, *args: Any, **kwargs: Any) -> Any:
                state["in_serial"] = True
                state["serial_after_failure"] = bool(state["fired"])
                try:
                    return orig_serial(self, *args, **kwargs)
                finally:
                    state["in_serial"] = False

            def register(self: Any, column: str, d_star: float, *, max_lag: int, weight_threshold: float) -> Any:
                if state["in_parallel"] and not state["fired"]:
                    done = {k for k, v in self.stationarity_decisions().items() if v.get("fracdiff") is True}
                    if done:
                        state["fired"], state["touched"] = True, set(done)
                        raise RuntimeError("injected parallel fracdiff failure after some columns recorded")
                return orig_register(self, column, d_star, max_lag=max_lag, weight_threshold=weight_threshold)

            def get(self: Any, column: str, col_values: Any = None) -> Any:
                value = orig_get(self, column, col_values)
                if state["in_serial"] and value is not None:
                    state["serial_hits"].add(str(column))
                return value

            mp.setattr(FeaturePreprocessor, "_apply_fractional_differencing_parallel", parallel)
            mp.setattr(FeaturePreprocessor, "_apply_fractional_differencing_serial", serial)
            mp.setattr(FeaturePreprocessor, "_register_derived_calibration", register)
            mp.setattr(DStarCache, "get", get)
        output = pre.transform(frame)
    return {"pre": pre, "output": output, "inputs": _unit_inputs(frame), "touched": set(state["touched"]),
            "serial_hits": set(state["serial_hits"]), "fired": bool(state["fired"]),
            "serial_after_failure": bool(state["serial_after_failure"])}


def fallback_record_violations(final: Mapping[Key, Mapping[str, Any]], reference: Mapping[Key, Mapping[str, Any]],
                               run: Mapping[str, Any], spec: Mapping[str, Any]) -> List[str]:
    """oracle（SPEC Task 1.2：紀錄以嘗試為單位，回退時失敗嘗試之紀錄整批撤回再由 serial 重記）：每欄恰一筆且屬契約；
    紀錄等於純串行對照，唯一例外＝失敗嘗試已記錄之欄（touched）之 `dstar_source`——其值須反映實際產出輸出之串行嘗試
    （串行嘗試快取命中者，不得仍等於「全新搜尋」之純串行值＝失敗嘗試殘留）。"""
    out = record_violations(final, run["inputs"], spec)
    if not run["fired"] or not run["touched"]:
        out.append("parallel 嘗試未於已記錄部分欄後失敗 ⇒ 空轉")
    if not run["serial_after_failure"]:
        out.append("未發生 parallel→serial 回退")
    if set(final) != set(reference):
        out.append(f"鍵集合與純串行不同：{sorted(set(final) ^ set(reference))[:5]}")
    for key in sorted(set(final) & set(reference)):
        got, want = dict(final[key]), dict(reference[key])
        if key in run["touched"]:
            diff = sorted(f for f in set(got) | set(want) if f != "dstar_source" and got.get(f) != want.get(f))
            if diff:
                out.append(f"{key}: 回退後紀錄與純串行不同之欄位 {diff}")
            if key[1] in run["serial_hits"] and got.get("dstar_source") == want.get("dstar_source"):
                out.append(f"{key}: dstar_source 為失敗嘗試之殘留（串行嘗試實為快取命中）")
        elif got != want:
            out.append(f"{key}: 回退後紀錄 ≠ 純串行")
    return out


# ---------------------------------------------------------------------------------------------- (c) ADF 檢定例外

def adf_exception_run(runs: ph.RunCache, cache_dir: Path, *, adf_raises: bool) -> Dict[str, Any]:
    """statsmodels ADF（關 fast ADF）之 `adfuller` 換為：`adf_raises` ⇒ 拋例外（生產以 p=1.0 續行之分支）；否則 ⇒ 回
    p=1.0（對照：例外分支應與之行為相同）。純串行、新 d* 快取目錄。回傳 {"pre", "output", "tested"(進入 ADF 檢定之
    (週期, 欄)), "adf_calls"}。"""
    from momentum.FeatureEngineering.preprocessing import feature_preprocessor as fpm

    tested: List[Key] = []
    calls = {"n": 0}

    def raising(*_args: Any, **_kwargs: Any) -> Any:
        calls["n"] += 1
        raise ValueError("injected statsmodels adfuller failure")

    def p_one(*_args: Any, **_kwargs: Any) -> Any:
        calls["n"] += 1
        return (0.0, 1.0)

    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("FFACT_USE_FAST_ADF", "0")
        pre, frame = _isolated_unit_preprocessor(runs, mp, cache_dir, n_jobs=1)
        mp.setattr(fpm, "adfuller", raising if adf_raises else p_one)
        orig_record_adf = fpm.FeaturePreprocessor._record_adf_test

        def record_adf(self: Any, column: str, sample: Any, pvalue: Any) -> Any:
            tested.append((str(self._decision_timeframe_for(str(column))), str(column)))
            return orig_record_adf(self, column, sample, pvalue)

        mp.setattr(fpm.FeaturePreprocessor, "_record_adf_test", record_adf)
        output = pre.transform(frame)
    return {"pre": pre, "output": output, "tested": sorted(set(tested)), "adf_calls": calls["n"]}


def adf_error_violations(err: Mapping[str, Any], ref: Mapping[str, Any], err_records: Mapping[Key, Mapping[str, Any]],
                         ref_records: Mapping[Key, Mapping[str, Any]], event: str) -> List[str]:
    """oracle（SPEC Task 1.2、§N FFDSTAR-R3）：ADF 例外 ⇒ 該欄紀錄 `events` 含契約之 ADF 例外事件值；未進入檢定之欄與
    p=1.0 對照之紀錄不含之；行為不變＝輸出值與平穩化決策（`events` 外）逐項等於 p=1.0 對照。"""
    out: List[str] = []
    if not err["tested"] or not err["adf_calls"]:
        out.append("無欄進入 statsmodels ADF 檢定 ⇒ 空轉")
    tested = set(err["tested"])
    for key, record in err_records.items():
        has = event in list(record.get("events") or [])
        if key in tested and not has:
            out.append(f"{key}: ADF 例外而紀錄無事件 {event!r}")
        if key not in tested and has:
            out.append(f"{key}: 未進入 ADF 檢定而紀錄有事件 {event!r}")
    out.extend(f"{key}: p=1.0 對照之紀錄出現 ADF 例外事件" for key, record in ref_records.items()
               if event in list(record.get("events") or []))
    if set(err_records) != set(ref_records):
        out.append(f"紀錄鍵集合與 p=1.0 對照不同：{sorted(set(err_records) ^ set(ref_records))[:5]}")
    try:
        pd.testing.assert_frame_equal(err["output"], ref["output"], check_exact=True)
    except AssertionError as exc:
        out.append(f"輸出值與 p=1.0 對照不同（行為被改）：{str(exc).splitlines()[0]}")
    strip = lambda d: {k: {f: v for f, v in r.items() if f != "events"} for k, r in d.items()}  # noqa: E731
    if strip(err["pre"].stationarity_decisions()) != strip(ref["pre"].stationarity_decisions()):
        out.append("平穩化決策（events 外）與 p=1.0 對照不同（行為被改）")
    return out


def adf_exception_parallel_run(runs: ph.RunCache, cache_dir: Path, *, adf_raises: bool) -> Dict[str, Any]:
    """`adf_exception_run` 之 parallel 版（審查 r7 CODEX-R7-P2-01；SPEC Task 1.2 之 `_slow_path_parallel.py:119` 附近）。

    機制（為何 monkeypatch 到得了 worker）：生產 `ParallelSlowPath.map` 以 joblib loky 起子行程，子行程內之
    monkeypatch 不生效；故將 `ParallelSlowPath.map`（既有假設點，同邊界③）換為同簽名之 joblib `threading` backend
    版——仍為 `n_jobs`（＝2）個並行 worker、仍呼叫生產傳入之 `process_fracdiff_column_values`、輸入同生產
    （`np.float64` 陣列＋metadata 副本），只是 worker 與主程序同一行程。worker 內 ADF 取 `adfuller` 之方式為呼叫當下
    `from statsmodels.tsa.stattools import adfuller`（`_slow_path_parallel.py:108`）⇒ 換 `statsmodels.tsa.stattools`
    模組屬性即可到達；另以 `raising=False` 同換 `_slow_path_parallel.adfuller`（實作若改為模組層 import 亦到達）。
    假 `adfuller` 只在 worker 執行緒內（thread-local 帶 metadata 之欄名）注入：`adf_raises` ⇒ 拋例外；否則 ⇒ 回
    p=1.0（對照）；主程序之 ADF（`feature_preprocessor` 模組層綁定之 `adfuller`）不受影響，故 owner 紀錄中之 ADF 例外
    事件只可能來自 worker 結果之併回。關 fast ADF、新 d* 快取目錄（worker 必實跑 d* 搜尋）。

    回傳 {"pre", "output", "tested"(worker 內進入 ADF 檢定之 (週期, 欄)), "adf_calls", "parallel_calls",
    "serial_calls", "map_jobs", "items", "eligible", "worker_threads", "main_thread"}。"""
    import threading

    from joblib import Parallel, delayed
    from statsmodels.tsa import stattools

    from momentum.FeatureEngineering.preprocessing import _slow_path_parallel as spp
    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

    local = threading.local()
    real_adfuller = stattools.adfuller
    state: Dict[str, Any] = {"tested": [], "worker_threads": set(), "map_jobs": [], "items": [], "eligible": [],
                             "parallel_calls": 0, "serial_calls": 0}

    def fake_adfuller(*args: Any, **kwargs: Any) -> Any:
        column = getattr(local, "column", None)
        if column is None:  # 非 worker 執行緒 ⇒ 原樣
            return real_adfuller(*args, **kwargs)
        state["tested"].append(column)
        if adf_raises:
            raise ValueError("injected worker statsmodels adfuller failure")
        return (0.0, 1.0)

    def threaded_map(self: Any, items: Any, worker_function: Any) -> Any:
        state["map_jobs"].append(int(self.n_jobs))
        state["items"].extend(str(metadata.get("column", "")) for _values, metadata in items)
        if not items:
            return []

        def run(values: Any, metadata: Dict[str, Any]) -> Any:
            local.column = str(metadata.get("column", ""))
            state["worker_threads"].add(threading.get_ident())
            try:
                return worker_function(values, metadata)
            finally:
                local.column = None

        return list(Parallel(n_jobs=self.n_jobs, backend="threading")(
            delayed(run)(np.asarray(values, dtype=np.float64), dict(metadata)) for values, metadata in items))

    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("FFACT_USE_FAST_ADF", "0")
        pre, frame = _isolated_unit_preprocessor(runs, mp, cache_dir, n_jobs=2)
        orig_parallel = FeaturePreprocessor._apply_fractional_differencing_parallel
        orig_serial = FeaturePreprocessor._apply_fractional_differencing_serial

        def parallel(self: Any, result: Any, eligible_columns: Any, *args: Any, **kwargs: Any) -> Any:
            state["parallel_calls"] += 1
            state["eligible"].extend(str(c) for c in eligible_columns)
            return orig_parallel(self, result, eligible_columns, *args, **kwargs)

        def serial(self: Any, *args: Any, **kwargs: Any) -> Any:
            state["serial_calls"] += 1
            return orig_serial(self, *args, **kwargs)

        mp.setattr(stattools, "adfuller", fake_adfuller)
        mp.setattr(spp, "adfuller", fake_adfuller, raising=False)
        mp.setattr(spp.ParallelSlowPath, "map", threaded_map)
        mp.setattr(FeaturePreprocessor, "_apply_fractional_differencing_parallel", parallel)
        mp.setattr(FeaturePreprocessor, "_apply_fractional_differencing_serial", serial)
        output = pre.transform(frame)
    tested = sorted({(str(pre._decision_timeframe_for(c)), c) for c in state["tested"]})
    return {"pre": pre, "output": output, "tested": tested, "adf_calls": len(state["tested"]),
            "parallel_calls": state["parallel_calls"], "serial_calls": state["serial_calls"],
            "map_jobs": list(state["map_jobs"]), "items": list(state["items"]), "eligible": list(state["eligible"]),
            "worker_threads": set(state["worker_threads"]), "main_thread": threading.get_ident()}


def parallel_path_violations(run: Mapping[str, Any]) -> List[str]:
    """前提（parallel 路徑確實被走到）：生產選 parallel 臂（`_apply_fractional_differencing_parallel` 被呼叫）且未回退
    串行；map 之 worker 數 ≥2、派出 ≥2 欄且派出欄＝可轉換欄（無去重代表欄 ⇒ 受檢鍵即事件應落之鍵）；至少一個 worker
    在非主執行緒；worker 內確有 ADF 檢定且受檢欄皆屬派出欄。"""
    out: List[str] = []
    if not run["parallel_calls"]:
        out.append("未選 parallel fracdiff 臂")
    if run["serial_calls"]:
        out.append("發生串行（回退或未走 parallel）⇒ 未驗 parallel worker 路徑")
    if not run["map_jobs"] or min(run["map_jobs"]) < 2:
        out.append(f"slow path worker 數 <2：{run['map_jobs']}")
    if len(run["items"]) < 2:
        out.append(f"派入 worker 之欄 <2：{run['items']}")
    if sorted(run["items"]) != sorted(run["eligible"]):
        out.append("派入 worker 之欄 ≠ 可轉換欄（有去重代表欄 ⇒ 事件落點不唯一）")
    if not (run["worker_threads"] - {run["main_thread"]}):
        out.append("worker 全在主執行緒 ⇒ 非並行")
    if not run["tested"]:
        out.append("worker 內無 ADF 檢定 ⇒ 空轉")
    if {c for _tf, c in run["tested"]} - set(run["items"]):
        out.append("受檢欄不屬派入 worker 之欄")
    return out


# ---------------------------------------------------------------------------------------------- (d) 前處理總開關關閉

def master_off_violations(table: pd.DataFrame, spec: Mapping[str, Any], value: str) -> List[str]:
    """oracle（SPEC v3 盤點輸入①）：總開關關閉（不建前處理器）⇒ 紀錄每列每個步驟狀態皆為契約之「總開關關閉」值。"""
    out: List[str] = []
    if len(table) == 0:
        out.append("紀錄零列 ⇒ 空轉")
    for step in spec["steps"]:
        if step not in table.columns:
            out.append(f"{step}: 紀錄缺該步驟欄")
            continue
        bad = table.loc[table[step].astype(str) != value, "output_column"].tolist()
        if bad:
            out.append(f"{step}: {len(bad)} 欄非總開關關閉值（例 {bad[:3]}）")
    return out


# ---------------------------------------------------------------------------------------------- (e) 群組 fallback 多重有序

def native_only_fallback(groups: Mapping[str, Mapping[str, Any]], shortened: Set[str]) -> Tuple[Optional[str], List[str]]:
    """參考格 `h12h1_native_fallback`（只有 native 回退、無注入之 parallel 失敗）：每個 native 回退群組之 `fallback`
    恰為一個元素之 list、全格同值 ⇒ 回 (native 回退值, 違規)；值不唯一 ⇒ (None, 違規)。"""
    out: List[str] = []
    seqs = {g: (groups.get(g) or {}).get("fallback") for g in sorted(shortened)}
    if not seqs:
        out.append("參考格無 native 回退群組 ⇒ 無法導出 native 回退值")
    bad = {g: s for g, s in seqs.items() if not (isinstance(s, list) and len(s) == 1)}
    if bad:
        out.append(f"只經 native 回退之群組 fallback 非恰一元素之清單：{bad}")
    values = {s[0] for s in seqs.values() if isinstance(s, list) and len(s) == 1}
    if len(values) != 1:
        out.append(f"native 回退值不唯一：{sorted(map(str, values))}")
    return (next(iter(values)) if len(values) == 1 else None), out


def ordered_fallback_violations(groups: Mapping[str, Mapping[str, Any]], obs: ph.Observation,
                                native_value: Optional[str], spec: Mapping[str, Any]) -> List[str]:
    """oracle（契約 `fallback_values._doc`「可多重，依發生序」；審查 r7 CODEX-R7-P2-02）：

    - 只經 parallel→serial 回退之群組（非 compact-aligned ⇒ 不可能有 native 回退）之 `fallback` ＝ [s]×(該群組實際注入
      失敗次數)，全格同一 s（導出 fracdiff 串行回退值；不在測試寫死字面）；
    - native 回退值 n（參考格導出）≠ s，兩者皆屬契約 `fallback_values`；
    - 每個 native 回退群組之 `fallback` 逐項等於依發生序之 [n] ＋ [s]×(該群組實際 parallel 失敗次數)——native 回退於
      `_maybe_run_native_l65_to_sink`（列數不符即 return None）先發生，其後同群組於 owner 之轉換才進 fracdiff；
      長度＝實際發生次數（不多不少、不去重）。"""
    out: List[str] = []
    fallbacks = set(ph.contract_values("fallback_values", spec))
    shortened, failures, aligned = set(obs.native_shortened), dict(obs.parallel_failures), set(obs.native_groups)
    serial_only = sorted(g for g in failures if g not in aligned)
    if not serial_only:
        out.append("無只經 parallel→serial 回退之群組 ⇒ 無法導出其回退值")
    values = {v for g in serial_only for v in list((groups.get(g) or {}).get("fallback") or [])}
    if len(values) != 1:
        out.append(f"只經 parallel→serial 回退之群組之回退值不唯一：{sorted(map(str, values))}")
    serial_value = next(iter(values)) if len(values) == 1 else None
    for gid in serial_only:
        got = (groups.get(gid) or {}).get("fallback")
        if serial_value is not None and got != [serial_value] * failures[gid]:
            out.append(f"{gid}: 只經 {failures[gid]} 次 parallel→serial 回退而 fallback={got!r}")
    if native_value is None or serial_value is None:
        return out
    if native_value == serial_value:
        out.append(f"native 回退值與 fracdiff 串行回退值相同（{native_value!r}）⇒ 無從區分發生序")
    out.extend(f"回退值 {v!r} 不屬契約 fallback_values" for v in (native_value, serial_value) if v not in fallbacks)
    if not shortened & set(failures):
        out.append("無群組同時經 native 回退與 parallel→serial 回退 ⇒ 空轉")
    for gid in sorted(shortened):
        want = [native_value] + [serial_value] * failures.get(gid, 0)
        got = (groups.get(gid) or {}).get("fallback")
        if got != want:
            out.append(f"{gid}: fallback={got!r} ≠ 依發生序 {want!r}")
    return out


def _mutant_group_accessor(target: Any, transform: Any) -> Any:
    """只對 `target` 實例以改壞之群組表包住生產之 `execution_groups`（參考格之實例不受影響）。"""
    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

    original = FeaturePreprocessor.execution_groups

    def accessor(self: Any) -> Any:
        groups = dict(original(self))
        return transform(groups) if self is target else groups

    return accessor


# ---------------------------------------------------------------------------------------------- 驗證

def test_verification_01_each_input_column_exactly_one_record(runs: ph.RunCache) -> None:
    """① 真實短窗群組：每個 L6.5 輸入欄恰一筆、各步驟狀態皆屬契約（平穩化開與關兩格）。"""
    spec = ph.contract()
    for cell in ("h1_stat_on", "h1_stat_off"):
        obs = ph.observation(runs.get(cell))
        inputs = l65_input_keys(obs)
        assert inputs, f"{cell}：無 L6.5 輸入 ⇒ ① 空轉"
        assert record_violations(ph.preprocessor_records(obs.l65_preprocessor), inputs, spec) == [], cell


def test_verification_02_native_success_and_fallback(runs: ph.RunCache) -> None:
    """② native 成功與回退各一案：成功群組之臂屬契約且回退清單為空；回退案（native 載入列數不符）之同群組回退清單
    非空且元素屬契約回退值集（SPEC v3 盤點輸入③），且（臂, 回退）不同於成功案；回退群組之欄仍各恰一筆紀錄。"""
    spec = ph.contract()
    arms = set(ph.contract_values("group_arm_values", spec))
    fallbacks = set(ph.contract_values("fallback_values", spec))
    ok_obs = ph.observation(runs.get("h12h1_multi"))
    native = sorted(g for g, ok in ok_obs.native_groups.items() if ok)
    assert native
    ok_groups = ph.preprocessor_groups(ok_obs.l65_preprocessor)
    for gid in native:
        assert ok_groups[gid]["arm"] in arms and ok_groups[gid]["fallback"] == [], gid
    fb_obs = ph.observation(runs.get("h12h1_native_fallback"))
    fb_groups = ph.preprocessor_groups(fb_obs.l65_preprocessor)
    fell_back = sorted(fb_obs.native_shortened)
    assert fell_back and not any(fb_obs.native_groups.get(g) for g in fell_back)
    for gid in fell_back:
        assert fb_groups[gid]["fallback"] and set(fb_groups[gid]["fallback"]) <= fallbacks, gid
        if gid in ok_groups:
            assert (fb_groups[gid]["arm"], fb_groups[gid]["fallback"]) != (ok_groups[gid]["arm"], []), gid
    assert record_violations(ph.preprocessor_records(fb_obs.l65_preprocessor), l65_input_keys(fb_obs), spec) == []


def test_verification_03_conflicting_merge_raises(runs: ph.RunCache) -> None:
    """③ 同鍵而值不逐項相同 ⇒ `_merge_decisions_from` 與 `_capture_stationarity_decisions` 皆拋
    `ProvenanceConflictError`；逐項相同則冪等（不拋、值不變）。"""
    from momentum.factories import create_feature_factory
    from momentum.FeatureEngineering.feature_naming import tag_timeframe
    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

    key, record, config = _real_decision(runs)
    changed = dict(record, d=(record.get("d") or 0.0) + 0.25)
    owner, child = FeaturePreprocessor(config), FeaturePreprocessor(config)
    owner._decisions[key], child._decisions[key] = dict(record), changed
    assert conflict_raises(owner, child)
    same_owner, same_child = FeaturePreprocessor(config), FeaturePreprocessor(config)
    same_owner._decisions[key], same_child._decisions[key] = dict(record), dict(record)
    assert not conflict_raises(same_owner, same_child)
    assert same_owner.stationarity_decisions()[key] == FeaturePreprocessor.stationarity_decisions(same_child)[key]
    factory = create_feature_factory(cache_dir=ph.KLINE_DIR, validate_continuity=False)
    factory.last_stationarity_decisions = {tag_timeframe(key[1], key[0]): changed}
    with pytest.raises(rp.ProvenanceConflictError):
        factory._capture_stationarity_decisions(same_owner, None)


def test_verification_02b_native_fallback_recorded_as_fallback_list(runs: ph.RunCache) -> None:
    """② 之 SPEC v3 形（盤點輸入③：回退另設值集、群組 `fallback` 為清單）：native 成功群組之 `fallback` 為空清單、臂屬
    群組臂值集；回退案之同群組 `fallback` 為非空清單、元素皆屬 `fallback_values`；回退群組之欄仍各恰一筆紀錄。"""
    spec = ph.contract()
    arms, fallbacks = set(ph.contract_values("group_arm_values", spec)), set(ph.contract_values("fallback_values", spec))
    ok_obs = ph.observation(runs.get("h12h1_multi"))
    native = sorted(g for g, ok in ok_obs.native_groups.items() if ok)
    assert native
    ok_groups = ph.preprocessor_groups(ok_obs.l65_preprocessor)
    for gid in native:
        assert ok_groups[gid]["arm"] in arms and ok_groups[gid]["fallback"] == [], gid
    fb_obs = ph.observation(runs.get("h12h1_native_fallback"))
    fb_groups = ph.preprocessor_groups(fb_obs.l65_preprocessor)
    fell_back = sorted(fb_obs.native_shortened)
    assert fell_back and not any(fb_obs.native_groups.get(g) for g in fell_back)
    for gid in fell_back:
        fallback = fb_groups[gid]["fallback"]
        assert isinstance(fallback, list) and fallback and set(fallback) <= fallbacks, (gid, fallback)
        assert fb_groups[gid]["arm"] in arms, gid
    assert record_violations(ph.preprocessor_records(fb_obs.l65_preprocessor), l65_input_keys(fb_obs), spec) == []


def _ordered_fallback_inputs(runs: ph.RunCache) -> Tuple[Optional[str], ph.Observation, List[str]]:
    """(參考格導出之 native 回退值, 雙回退變體之觀測, 同時經兩種回退之群組)；參考格違規即 AssertionError。"""
    ref = ph.observation(runs.get("h12h1_native_fallback"))
    native_value, ref_violations = native_only_fallback(ph.preprocessor_groups(ref.l65_preprocessor),
                                                        set(ref.native_shortened))
    assert ref_violations == [], ref_violations
    obs = ph.observation(runs.get("h12h1_native_fallback_parallel_fail"))
    both = sorted(set(obs.native_shortened) & set(obs.parallel_failures))
    assert both, ("前提不成立：無 12h 群組於 native 回退後 ≥2 欄進入 fracdiff 而選入 parallel 臂（注入對象）："
                  f"native 回退 {sorted(obs.native_shortened)}、parallel 失敗 {obs.parallel_failures}")
    return native_value, obs, both


def test_verification_02c_group_fallback_list_ordered_by_occurrence(runs: ph.RunCache) -> None:
    """契約 `fallback_values._doc`「可多重，依發生序」（審查 r7 CODEX-R7-P2-02）：同一群組依序經歷 native 回退與
    fracdiff parallel→serial 回退 ⇒ 群組 `fallback` 逐項等於 [native 回退值] ＋ [串行回退值]×實際 parallel 失敗次數
    （順序、長度、重複皆依實際發生）。

    構造（同一真實群組，非兩個獨立實例）：變體 `h12h1_native_fallback_parallel_fail`＝`h12h1_native_fallback`（native
    載入少一列 ⇒ `_maybe_run_native_l65_to_sink` 於 `feature_preprocessor.py:1219` 附近 return None）＋ slow path worker 數
    固定 2、owner 每次 parallel fracdiff 嘗試於入口注入一般例外（⇒ 生產既有之 parallel→serial 回退，`:3780` 附近）。
    回退之 12h 群組隨即於 owner 之 aligned 路徑轉換、進 fracdiff ⇒ 兩事件於同群組依序發生。可行性前提（該群組於真實
    短窗有 ≥2 欄可轉換，生產方選 parallel 臂）以前提斷言驗證；兩回退值皆自實際紀錄導出（native 值取只回退 native 之
    參考格、串行值取只經 parallel 失敗之 1h 群組），不在測試寫死字面。各欄仍恰一筆紀錄。"""
    spec = ph.contract()
    native_value, obs, _both = _ordered_fallback_inputs(runs)
    groups = ph.preprocessor_groups(obs.l65_preprocessor)
    assert ordered_fallback_violations(groups, obs, native_value, spec) == []
    assert record_violations(ph.preprocessor_records(obs.l65_preprocessor), l65_input_keys(obs), spec) == []


def test_verification_04_dstar_search_provenance_error_propagates(runs: ph.RunCache, tmp_path: Path) -> None:
    """SPEC Task 1.2 改法：d* 搜尋鏈內（`_find_min_d` → 校準查找之紀錄點）拋出之 `ProvenanceConflictError` 原樣上拋，不被
    包住 `_find_min_d` 之 `except Exception`（`feature_preprocessor.py:3543` 附近）轉為 d* 搜尋失敗紀錄而續跑。"""
    assert dstar_error_violations(dstar_search_provenance_error_outcome(runs, tmp_path / "dstar")) == []


def test_verification_05_parallel_fallback_serial_records_equal_pure_serial(runs: ph.RunCache, tmp_path: Path) -> None:
    """SPEC Task 1.2 改法：parallel fracdiff 於已記錄部分欄後失敗 ⇒ 回退串行：不拋 `ProvenanceConflictError`、每欄恰一筆、
    紀錄等於純串行對照（失敗嘗試之紀錄已整批撤回；touched 欄之 `dstar_source` 反映串行嘗試之實際來源）；輸出值等於
    純串行（回退不改值）。"""
    spec = ph.contract()
    fallback = fracdiff_fallback_run(runs, tmp_path / "fallback", fail_parallel=True)
    reference = fracdiff_fallback_run(runs, tmp_path / "serial", fail_parallel=False)
    assert fallback["touched"] and {k[1] for k in fallback["touched"]} <= fallback["serial_hits"], fallback["serial_hits"]
    pd.testing.assert_frame_equal(fallback["output"], reference["output"], check_exact=True)
    assert fallback_record_violations(ph.preprocessor_records(fallback["pre"]),
                                      ph.preprocessor_records(reference["pre"]), fallback, spec) == []


def test_verification_06_adf_exception_event_without_behavior_change(runs: ph.RunCache, tmp_path: Path) -> None:
    """SPEC Task 1.2、§N FFDSTAR-R3：statsmodels ADF 拋例外（現行以 p=1.0 續行）⇒ 進入檢定之欄之紀錄 `events` 含契約
    `named_values.adf_test_error_event`；輸出值與平穩化決策等於 `adfuller` 回 p=1.0 之對照（只記、不改行為）；各步驟狀態
    屬契約。"""
    spec = ph.contract()
    event = ph.contract_named("adf_test_error_event", spec)
    err = adf_exception_run(runs, tmp_path / "adf_err", adf_raises=True)
    ref = adf_exception_run(runs, tmp_path / "adf_ref", adf_raises=False)
    err_records, ref_records = ph.preprocessor_records(err["pre"]), ph.preprocessor_records(ref["pre"])
    assert err["tested"] and err["tested"] == ref["tested"]
    assert adf_error_violations(err, ref, err_records, ref_records, event) == []
    assert record_violations(err_records, list(err_records), spec) == []


def test_verification_06b_parallel_adf_exception_event_merged_to_owner(runs: ph.RunCache, tmp_path: Path) -> None:
    """SPEC Task 1.2（`_slow_path_parallel.py:119` 附近）、§N FFDSTAR-R3（審查 r7 CODEX-R7-P2-01）：parallel fracdiff
    worker 內 statsmodels ADF 拋例外（現行以 p=1.0 續行）⇒ worker 內受檢欄之 owner 紀錄 `events` 含契約
    `named_values.adf_test_error_event`（worker 事件併回 owner），未受檢欄與 p=1.0 對照不含；輸出值與平穩化決策
    （events 外）逐項等於 worker 內 `adfuller` 回 p=1.0 之對照。機制（worker 同行程之 threading backend、只於 worker
    執行緒注入）見 `adf_exception_parallel_run`；前提斷言證 parallel 路徑確實被走到（未回退串行、≥2 worker、非主執行緒）。"""
    spec = ph.contract()
    event = ph.contract_named("adf_test_error_event", spec)
    err = adf_exception_parallel_run(runs, tmp_path / "padf_err", adf_raises=True)
    ref = adf_exception_parallel_run(runs, tmp_path / "padf_ref", adf_raises=False)
    assert parallel_path_violations(err) == [] and parallel_path_violations(ref) == []
    assert err["tested"] == ref["tested"]
    err_records, ref_records = ph.preprocessor_records(err["pre"]), ph.preprocessor_records(ref["pre"])
    assert adf_error_violations(err, ref, err_records, ref_records, event) == []
    assert record_violations(err_records, list(err_records), spec) == []


def test_verification_07_master_switch_off_every_step_master_off_value(runs: ph.RunCache) -> None:
    """SPEC v3 盤點輸入①：前處理總開關關閉（不建前處理器）⇒ raw 紀錄每列之每個步驟狀態皆為契約
    `named_values.preprocessing_master_off`（值屬每個步驟之狀態值集；不得為 null 或「步驟關閉」之值）。"""
    spec = ph.contract()
    value = ph.contract_named("preprocessing_master_off", spec)
    handle = runs.get("h1_pp_off")
    assert ph.observation(handle).l65_preprocessor is None, "總開關關閉格仍建前處理器 ⇒ 前提不成立"
    table = ph.provenance_table(handle.run_dir, "raw")
    assert master_off_violations(table, spec, value) == []
    off = ph.provenance_table(runs.get("h1_stat_off").run_dir, "raw")
    assert not (set(off["fractional_differencing"].astype(str)) & {value}), "平穩化關（總開關開）亦記總開關關閉值"


# ---------------------------------------------------------------------------------------------- 邊界

def test_boundary_01_group_all_ratio_unsafe(runs: ph.RunCache) -> None:
    """邊界①：群組全為 ratio-unsafe ⇒ 其每欄恰一筆、終態＝SPEC 點名之 `ratio_unsafe`、縮尾非 `applied`。"""
    from momentum.FeatureEngineering.feature_naming import is_ratio_unsafe_column

    spec = ph.contract()
    obs = ph.observation(runs.get("ratio_unsafe"))
    records = ph.preprocessor_records(obs.l65_preprocessor)
    keys = [(tf, c) for cols, _a, tf, _l in obs.l65_inputs.values()
            if cols and all(is_ratio_unsafe_column(x) for x in cols) for c in cols]
    assert keys
    terminal, applied = ph.spec_named("terminal_ratio_unsafe", spec), ph.spec_named("winsor_applied", spec)
    assert all(records[k]["terminal"] == terminal for k in keys)
    assert all(records[k]["winsorization"] != applied for k in keys)


def test_boundary_02_eligible_columns_empty(runs: ph.RunCache) -> None:
    """邊界②：`eligible_columns` 為空（校準前史全無有效值）⇒ 每欄仍恰一筆、fracdiff 未套用（d null）、其 fracdiff 狀態屬
    契約且不同於實際套用 fracdiff 之欄之狀態。"""
    spec = ph.contract()
    pre, frame = _unit_preprocessor(runs, nan_history=True)
    pre.transform(frame)
    records = ph.preprocessor_records(pre)
    inputs = [("1h", str(c)) for c in frame.columns]
    assert record_violations(records, inputs, spec) == []
    assert all(r.get("d") is None and r.get("fracdiff") is not True for r in records.values())
    on = ph.provenance_table(runs.get("h1_stat_on").run_dir, "raw")
    applied = set(on.loc[on["fracdiff"].fillna(False).astype(bool), "fractional_differencing"].astype(str))
    assert applied and not {str(r["fractional_differencing"]) for r in records.values()} & applied


def test_boundary_03_parallel_fracdiff_merge_rejects_duplicate_key(runs: ph.RunCache, monkeypatch: pytest.MonkeyPatch) -> None:
    """邊界③：parallel fracdiff 多 worker 結果合併——正常時每欄恰一筆且鍵集合同串行；同一欄出現兩份不同結果 ⇒ 拒收
    （`ProvenanceError` 上拋，不得被 parallel→serial 回退吞下）。"""
    from momentum.FeatureEngineering.preprocessing import _slow_path_parallel as spp
    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

    spec = ph.contract()
    serial, frame = _unit_preprocessor(runs, nan_history=False)
    serial.transform(frame)
    monkeypatch.setattr(FeaturePreprocessor, "_resolve_slowpath_n_jobs", lambda self: 2)
    parallel, _ = _unit_preprocessor(runs, nan_history=False)
    parallel.transform(frame)
    inputs = [("1h", str(c)) for c in frame.columns]
    assert record_violations(ph.preprocessor_records(parallel), inputs, spec) == []
    assert set(ph.preprocessor_records(parallel)) == set(ph.preprocessor_records(serial))

    real_map = spp.ParallelSlowPath.map

    def duplicating_map(self: Any, items: Any, fn: Any) -> Any:
        outputs = list(real_map(self, items, fn))
        first = next(o for o in outputs if o.get("status") == "ok")
        return outputs + [dict(first, d_star=float(first["d_star"]) + 0.1)]

    monkeypatch.setattr(spp.ParallelSlowPath, "map", duplicating_map)
    dup, _ = _unit_preprocessor(runs, nan_history=False)
    with pytest.raises(rp.ProvenanceError):
        dup.transform(frame)


def test_boundary_04_append_mode_derived_columns_link_parent(runs: ph.RunCache) -> None:
    """邊界④：append 模式衍生欄（`_fracdiff`／`_diff1`／`_diff2`）——其紀錄列之 `parent_column`＝父欄落盤名（最長之
    「輸入欄名＋底線」前綴）、終態屬契約；輸入欄本身 `parent_column` 為 null。"""
    spec = ph.contract()
    handle = runs.get("h1_stat_on")
    obs = ph.observation(handle)
    table = ph.provenance_table(handle.run_dir, "raw").set_index("output_column")
    inputs = {ph.output_name(c, tf) for tf, c in l65_input_keys(obs)}
    derived = sorted(set(table.index) - inputs - set(obs.l7_dropped))
    assert derived, "無衍生欄 ⇒ 邊界空轉"
    terminals = set(ph.contract_values("terminal_values", spec))
    for name in derived:
        parents = [p for p in inputs if name.startswith(p + "_")]
        assert parents, name
        assert table.loc[name, "parent_column"] == max(parents, key=len), name
        assert table.loc[name, "terminal"] in terminals, name
    assert table.loc[sorted(inputs & set(table.index)), "parent_column"].isna().all()


# ---------------------------------------------------------------------------------------------- mutation

def _mutant_accessor(transform: Any) -> Any:
    """以改壞之紀錄存取點包住生產之 `execution_records`（呼叫端以 monkeypatch.setattr 換入）。"""
    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

    original = FeaturePreprocessor.execution_records
    return lambda self: transform(dict(original(self)))


def test_mutation_winsor_success_not_recorded(runs: ph.RunCache, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation：縮尾成功不記（該步狀態缺）⇒ ① 轉紅。"""
    spec = ph.contract()
    obs = ph.observation(runs.get("h1_stat_off"))
    assert record_violations(ph.preprocessor_records(obs.l65_preprocessor), l65_input_keys(obs), spec) == []

    def drop_winsor(records: Dict[Key, Dict[str, Any]]) -> Dict[Key, Dict[str, Any]]:
        key = next(iter(records))
        records[key] = {k: v for k, v in records[key].items() if k != "winsorization"}
        return records

    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

    monkeypatch.setattr(FeaturePreprocessor, "execution_records", _mutant_accessor(drop_winsor))
    assert record_violations(ph.preprocessor_records(obs.l65_preprocessor), l65_input_keys(obs), spec) != []


def test_mutation_exit_point_record_deleted(runs: ph.RunCache, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation：刪任一離開點之紀錄呼叫（該欄整筆缺）⇒ ① 轉紅。"""
    spec = ph.contract()
    obs = ph.observation(runs.get("h1_stat_on"))

    def drop_one(records: Dict[Key, Dict[str, Any]]) -> Dict[Key, Dict[str, Any]]:
        records.pop(next(iter(records)))
        return records

    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

    monkeypatch.setattr(FeaturePreprocessor, "execution_records", _mutant_accessor(drop_one))
    assert any("缺紀錄" in v for v in record_violations(ph.preprocessor_records(obs.l65_preprocessor),
                                                       l65_input_keys(obs), spec))


def test_mutation_merge_reverts_to_overwrite(runs: ph.RunCache, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation：`_merge_decisions_from` 改回覆寫（後寫勝）⇒ ③ 轉紅（衝突不再拋錯）。"""
    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

    key, record, config = _real_decision(runs)

    def overwrite(self: Any, other: Any, idx_map: Any = None) -> None:
        for k, v in other.stationarity_decisions().items():
            self._decisions[k] = dict(v)

    owner, child = FeaturePreprocessor(config), FeaturePreprocessor(config)
    owner._decisions[key], child._decisions[key] = dict(record), dict(record, d=(record.get("d") or 0.0) + 0.25)
    assert conflict_raises(owner, child)
    monkeypatch.setattr(FeaturePreprocessor, "_merge_decisions_from", overwrite)
    owner2, child2 = FeaturePreprocessor(config), FeaturePreprocessor(config)
    owner2._decisions[key], child2._decisions[key] = dict(record), dict(record, d=(record.get("d") or 0.0) + 0.25)
    assert not conflict_raises(owner2, child2)


def test_mutation_dstar_search_swallows_provenance_error(runs: ph.RunCache, monkeypatch: pytest.MonkeyPatch,
                                                         tmp_path: Path) -> None:
    """mutation（SPEC Task 1.2）：d* 搜尋把 `ProvenanceError` 轉成一般例外（＝包住 `_find_min_d` 之 `except Exception`
    未補 NON_DEGRADABLE 重拋時之效果：轉為 d* 搜尋失敗續跑）⇒ 驗證 04 之 oracle 轉紅。正對照：未改壞時無違規。"""
    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

    assert dstar_error_violations(dstar_search_provenance_error_outcome(runs, tmp_path / "good")) == []
    real_find = FeaturePreprocessor._find_min_d

    def degrading_find(self: Any, series: Any, **kwargs: Any) -> Any:
        try:
            return real_find(self, series, **kwargs)
        except rp.ProvenanceError as exc:
            raise ValueError(f"degraded: {exc}") from None

    monkeypatch.setattr(FeaturePreprocessor, "_find_min_d", degrading_find)
    violations = dstar_error_violations(dstar_search_provenance_error_outcome(runs, tmp_path / "mutant"))
    assert any("被吞" in v for v in violations), violations


def test_mutation_fallback_keeps_failed_attempt_record(runs: ph.RunCache, monkeypatch: pytest.MonkeyPatch,
                                                       tmp_path: Path) -> None:
    """mutation（SPEC Task 1.2「紀錄以嘗試為單位」）：回退後保留失敗 parallel 嘗試之紀錄（touched 欄之 `dstar_source` 停在
    純串行全新搜尋之值，而非串行嘗試實際之快取命中）、或回退後某欄重複／缺漏 ⇒ 驗證 05 之 oracle 轉紅。"""
    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

    spec = ph.contract()
    fallback = fracdiff_fallback_run(runs, tmp_path / "fallback", fail_parallel=True)
    reference = fracdiff_fallback_run(runs, tmp_path / "serial", fail_parallel=False)
    ref_records = ph.preprocessor_records(reference["pre"])
    assert fallback_record_violations(ph.preprocessor_records(fallback["pre"]), ref_records, fallback, spec) == []
    stale_key = sorted(k for k in fallback["touched"] if k[1] in fallback["serial_hits"])[0]

    def keep_stale(records: Dict[Key, Dict[str, Any]]) -> Dict[Key, Dict[str, Any]]:
        records[stale_key] = dict(records[stale_key], dstar_source=ref_records[stale_key].get("dstar_source"))
        return records

    monkeypatch.setattr(FeaturePreprocessor, "execution_records", _mutant_accessor(keep_stale))
    violations = fallback_record_violations(ph.preprocessor_records(fallback["pre"]), ref_records, fallback, spec)
    assert any("殘留" in v for v in violations), violations


def test_mutation_adf_exception_event_not_recorded(runs: ph.RunCache, monkeypatch: pytest.MonkeyPatch,
                                                   tmp_path: Path) -> None:
    """mutation（SPEC Task 1.2、§N FFDSTAR-R3）：ADF 例外不記事件（紀錄 `events` 去掉該事件值）⇒ 驗證 06 之 oracle 轉紅。"""
    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

    spec = ph.contract()
    event = ph.contract_named("adf_test_error_event", spec)
    err = adf_exception_run(runs, tmp_path / "adf_err", adf_raises=True)
    ref = adf_exception_run(runs, tmp_path / "adf_ref", adf_raises=False)
    ref_records = ph.preprocessor_records(ref["pre"])
    assert adf_error_violations(err, ref, ph.preprocessor_records(err["pre"]), ref_records, event) == []

    def drop_event(records: Dict[Key, Dict[str, Any]]) -> Dict[Key, Dict[str, Any]]:
        return {k: dict(r, events=[e for e in (r.get("events") or []) if e != event]) for k, r in records.items()}

    monkeypatch.setattr(FeaturePreprocessor, "execution_records", _mutant_accessor(drop_event))
    violations = adf_error_violations(err, ref, ph.preprocessor_records(err["pre"]), ref_records, event)
    assert any("ADF 例外而紀錄無事件" in v for v in violations), violations


def test_mutation_parallel_adf_worker_event_dropped(runs: ph.RunCache, monkeypatch: pytest.MonkeyPatch,
                                                    tmp_path: Path) -> None:
    """mutation（審查 r7 CODEX-R7-P2-01）：parallel worker 之 ADF 例外事件未併回 owner（worker 受檢欄之紀錄 `events`
    去掉該事件值＝現行 worker 只回 p=1.0 之效果）⇒ 驗證 06b 之 oracle 轉紅。正對照：未改壞時無違規。"""
    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

    spec = ph.contract()
    event = ph.contract_named("adf_test_error_event", spec)
    err = adf_exception_parallel_run(runs, tmp_path / "padf_err", adf_raises=True)
    ref = adf_exception_parallel_run(runs, tmp_path / "padf_ref", adf_raises=False)
    assert parallel_path_violations(err) == []
    ref_records = ph.preprocessor_records(ref["pre"])
    assert adf_error_violations(err, ref, ph.preprocessor_records(err["pre"]), ref_records, event) == []
    worker_tested = set(err["tested"])

    def drop_worker_event(records: Dict[Key, Dict[str, Any]]) -> Dict[Key, Dict[str, Any]]:
        return {k: (dict(r, events=[e for e in (r.get("events") or []) if e != event]) if k in worker_tested else r)
                for k, r in records.items()}

    monkeypatch.setattr(FeaturePreprocessor, "execution_records", _mutant_accessor(drop_worker_event))
    violations = adf_error_violations(err, ref, ph.preprocessor_records(err["pre"]), ref_records, event)
    assert any("ADF 例外而紀錄無事件" in v for v in violations), violations


def test_mutation_group_fallback_second_event_dropped(runs: ph.RunCache, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation（審查 r7 CODEX-R7-P2-02）：同時經兩種回退之群組之 `fallback` 刪去第二個事件（fracdiff 串行回退）⇒
    驗證 02c 之 oracle 轉紅。正對照：未改壞時無違規。"""
    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

    spec = ph.contract()
    native_value, obs, both = _ordered_fallback_inputs(runs)
    pre = obs.l65_preprocessor
    assert ordered_fallback_violations(ph.preprocessor_groups(pre), obs, native_value, spec) == []

    def drop_second(groups: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        return {g: (dict(v, fallback=list(v["fallback"])[:1] + list(v["fallback"])[2:]) if g in both else v)
                for g, v in groups.items()}

    monkeypatch.setattr(FeaturePreprocessor, "execution_groups", _mutant_group_accessor(pre, drop_second))
    violations = ordered_fallback_violations(ph.preprocessor_groups(pre), obs, native_value, spec)
    assert any(v.startswith(f"{both[0]}: fallback=") and "依發生序" in v for v in violations), violations


def test_mutation_group_fallback_order_swapped(runs: ph.RunCache, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation（審查 r7 CODEX-R7-P2-02）：同時經兩種回退之群組之 `fallback` 順序顛倒（串行回退在前、native 在後）⇒
    驗證 02c 之 oracle 轉紅。正對照：未改壞時無違規。"""
    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

    spec = ph.contract()
    native_value, obs, both = _ordered_fallback_inputs(runs)
    pre = obs.l65_preprocessor
    assert ordered_fallback_violations(ph.preprocessor_groups(pre), obs, native_value, spec) == []

    def swap(groups: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        return {g: (dict(v, fallback=list(reversed(list(v["fallback"])))) if g in both else v)
                for g, v in groups.items()}

    monkeypatch.setattr(FeaturePreprocessor, "execution_groups", _mutant_group_accessor(pre, swap))
    violations = ordered_fallback_violations(ph.preprocessor_groups(pre), obs, native_value, spec)
    assert any(v.startswith(f"{both[0]}: fallback=") and "依發生序" in v for v in violations), violations


def test_mutation_master_off_step_recorded_as_other_value(runs: ph.RunCache, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation（SPEC v3 盤點輸入①）：總開關關閉格之紀錄某欄某步驟改記為該步驟之其他契約值（如「步驟關閉」）⇒
    驗證 07 之 oracle 轉紅。"""
    spec = ph.contract()
    value = ph.contract_named("preprocessing_master_off", spec)
    run_dir = runs.get("h1_pp_off").run_dir
    table = ph.provenance_table(run_dir, "raw")
    assert master_off_violations(table, spec, value) == []
    step = spec["steps"][0]
    other = sorted(set(ph.contract_values(f"step_status_values.{step}", spec)) - {value})
    assert other, f"{step} 值集只有總開關關閉值 ⇒ mutant 無對象"
    mutated = table.copy()
    mutated.loc[mutated.index[0], step] = other[0]
    monkeypatch.setattr(ph, "provenance_table", lambda _run_dir, _kind: mutated.copy())
    violations = master_off_violations(ph.provenance_table(run_dir, "raw"), spec, value)
    assert any(v.startswith(f"{step}: 1 欄") for v in violations), violations
