"""ICPERF Task 0.2 v5.59 產品施工（code review r70 群集 B、C、E、G、I、L）——秒級測試。

使用者 2026-11-02：「現在是自己寫計算方程式? 突然想起為何不直接套用業界標準函式庫就好？」；2026-09-10：「前後端務必同步，
不能再有幽靈狀態」。

- (ab) 顯著性 metadata `significance.tested_estimator` 依實際被檢定之估計量：
  - 跨標的：HAC 檢定之對象＝逐時點截面 IC 序列（估計量＝`global.default_method`）⇒ `cross_sectional_period_ic_<method>`。
  - 縱向：HAC 檢定之對象＝逐根 Spearman 貢獻序列（`statistical_validator.compute_hac_ic_statistics` 不收方法參數）⇒
    不論 `default_method`，被檢定之估計量恆為 Spearman，字面 `bar_level_spearman` 方為真；本檔以 statsmodels OLS HAC 於
    Spearman 貢獻序列之 t 值逐值對照證之（若日後 HAC 改依方法，本條紅，字面須同步改）。
- (ac) 事件負對照固定跑 `negative_control_n` 次（刪牆鐘預算縮減）；`degraded_by_budget`／`budget_seconds` 不再出現在收據；
  耗時以 `_report_progress` 之子步驟進度揭露。
- (ae) 跨標的主 IC 標籤依 `labels.return_type`（與 IC 衰減同一定義）：以 `data_cache/feature_klines/kline_cache.h5` 直讀收盤
  重算為 oracle；Pearson 下主 IC＝衰減 h=1 之截面 IC 均值；Spearman 下 log 與 simple 之主 IC 逐值相同。
- (ag) 舊方法 `ICEngine.compute_ic_autocorrelation` 已刪。
- (ah) `StatisticalValidator._fdr_bh` 委派 `statsmodels.stats.multitest.multipletests(method="fdr_bh")`：逐值 `==`（含並列 p 與
  NaN 保位）。
"""

from __future__ import annotations

import asyncio
import math
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List

import numpy as np
import pandas as pd
import pytest
import statsmodels.api as sm
from scipy import stats
from statsmodels.stats.multitest import multipletests

from momentum.Analysis import ic_filter_orchestrator as orch_mod
from momentum.Analysis.ic_config_schema import EventFilterConfig, ICConfig
from momentum.Analysis.ic_engine import ICEngine
from momentum.Analysis.ic_filter_orchestrator import ICFilterOrchestrator
from momentum.Analysis.statistical_validator import StatisticalValidator, apply_fdr
from momentum.core.contracts import ValidatedBinaryLabel, binary_label_digest
from momentum.factories import create_ic_analyzer

REPO = Path(__file__).resolve().parents[3]
KLINE_H5 = REPO / "data_cache" / "feature_klines" / "kline_cache.h5"
METHODS = ("spearman", "pearson", "kendall")
LABEL = "return_1"
NO_SPLIT = {"ic_train_test_split": False}
HOUR_MS = 3_600_000
BASE_MS = 1_700_000_000_000


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# (ab) significance.tested_estimator
# ══════════════════════════════════════════════════════════════════════════════════════════════════


def _xsec_panel() -> pd.DataFrame:
    """明列輸入：6 標的 × 60 時點；f1 與標籤非線性相關（Pearson ≠ Spearman），f2 為雜訊；標籤 `return_1`。"""
    rng = np.random.default_rng(20261102)
    ts = pd.date_range("2024-01-01", periods=60, freq="h")
    rows = []
    for stamp in ts:
        latent = rng.standard_normal(6)
        for j, sym in enumerate(("AAA", "BBB", "CCC", "DDD", "EEE", "FFF")):
            y = 0.01 * latent[j]
            rows.append((stamp, sym, float(np.exp(3.0 * latent[j]) + 0.3 * rng.standard_normal()),
                         float(rng.standard_normal()), y))
    return pd.DataFrame(rows, columns=["timestamp", "symbol", "f1", "f2", LABEL]).set_index(["timestamp", "symbol"])


@pytest.mark.parametrize("method", METHODS)
def test_xsec_tested_estimator_names_method(method: str) -> None:
    """跨標的：HAC 檢定之 IC 序列以 `default_method` 計 ⇒ 字面帶方法（改前三法皆 `cross_sectional_period_ic`）。"""
    report = create_ic_analyzer().analyze_cross_sectional(
        _xsec_panel(), config_override={**NO_SPLIT, "global": {"default_method": method}})
    assert report["metadata"]["significance"]["tested_estimator"] == f"cross_sectional_period_ic_{method}"


def test_xsec_tested_estimator_closed_mapping() -> None:
    """封閉對映：鍵集合＝跨標的可用之 IC 方法（schema Literal），值兩兩不同。"""
    mapping = orch_mod.TESTED_ESTIMATOR_XSEC_BY_METHOD
    assert set(mapping) == set(orch_mod.XSEC_IC_METHODS) == set(METHODS)
    assert len(set(mapping.values())) == len(mapping)


def _longitudinal_inputs(n: int = 240) -> tuple[pd.DataFrame, pd.Series]:
    """明列輸入：240 根、三欄（f0 帶非線性訊號）、標籤；int64 epoch 秒索引（同 `test_ic_1eb_b2_wiring` 之 stage5 輸入形狀）。"""
    rng = np.random.default_rng(7)
    index = pd.Index(np.arange(n, dtype=np.int64) * 3600 + 1_600_000_000, name="timestamp")
    latent = rng.standard_normal(n)
    features = pd.DataFrame({
        "f0": np.exp(2.0 * latent) + 0.5 * rng.standard_normal(n),
        "f1": rng.standard_normal(n),
        "f2": 0.3 * latent + rng.standard_normal(n),
    }, index=index)
    label = pd.Series(latent + 0.1 * rng.standard_normal(n), index=index, name="label")
    return features, label


def _spearman_hac_t_oracle(x: np.ndarray, y: np.ndarray, horizon: int) -> float:
    """逐根 Spearman 貢獻 z＝zscore(rank x)·zscore(rank y)（ddof=1）之均值 t：statsmodels OLS(z, 1) HAC（Bartlett、無小樣本
    修正）；L＝max(int(4·(n/100)^(2/9)), horizon−1)（同 SPEC Task 0.3 HAC 項之定義）。"""
    rx, ry = stats.rankdata(x), stats.rankdata(y)
    z = ((rx - rx.mean()) / rx.std(ddof=1)) * ((ry - ry.mean()) / ry.std(ddof=1))
    n = z.size
    lags = max(int(4 * (n / 100.0) ** (2.0 / 9.0)), horizon - 1)
    fit = sm.OLS(z, np.ones(n)).fit(cov_type="HAC", cov_kwds={"maxlags": lags, "kernel": "bartlett",
                                                               "use_correction": False})
    return float(fit.tvalues[0])


@pytest.mark.parametrize("method", METHODS)
def test_longitudinal_tested_estimator_is_the_spearman_hac_actually_run(method: str) -> None:
    """縱向：不論 `default_method`，第 5 段 HAC t 值 == Spearman 貢獻序列之 statsmodels HAC t（相對誤差 ≤ 1e-12）⇒ 被檢定之
    估計量恆為 Spearman，字面 `bar_level_spearman` 為真；寫成 `bar_level_<method>` 即與實際檢定不符（本條紅）。"""
    features, label = _longitudinal_inputs()
    config = ICConfig.model_validate({**NO_SPLIT, "global": {"default_method": method, "default_horizon": 1},
                                      "labels": {"horizons": [1]}})
    orch = ICFilterOrchestrator(config)
    icir = {c: {"ic_mean": 0.05, "ic_std": 0.1, "icir": 0.5, "ic_hit_rate": 0.6} for c in features.columns}
    stage5 = orch._stage5_statistical_validation(
        features, label, {"rolling_ic": {c: {"window_5": [0.1, 0.2]} for c in features.columns}, "icir": icir,
                          "ic_decay": {}},
        config, {"tier": "sufficient"}, metadata={"symbol": "BTCUSDT"},
    )
    assert stage5["significance"]["tested_estimator"] == "bar_level_spearman"
    for col in features.columns:
        got = float(stage5["ic_stats"][col]["t_stat"])
        exp = _spearman_hac_t_oracle(features[col].to_numpy(), label.to_numpy(), 1)
        assert math.isclose(got, exp, rel_tol=1e-12), f"{method}/{col}：產品 HAC t {got!r} != Spearman HAC {exp!r}"
    # 前提（辨識力）：f0 之 Pearson 與 Spearman 確實不同，故「HAC 等於 Spearman 版」可分辨兩估計量
    assert abs(stats.pearsonr(features["f0"], label)[0] - stats.spearmanr(features["f0"], label)[0]) > 0.05


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# (ac) 事件負對照固定次數
# ══════════════════════════════════════════════════════════════════════════════════════════════════


def _event_orch(n_control: int) -> ICFilterOrchestrator:
    return ICFilterOrchestrator(ICConfig.model_validate({
        "event_filter": {"min_events_per_class": 5, "negative_control_n": n_control, "oracle_seed": 7},
        "thresholds": {"rank_biserial_min": 0.10},
    }))


def _event_inputs() -> tuple[pd.DataFrame, np.ndarray]:
    """明列輸入：120 事件（每 20 個一區塊交替 10 正 10 反）、8 欄雜訊（同 `test_evtlabel_oracle` 之負對照輸入形狀）。"""
    n = 120
    y = np.array(([1] * 10 + [0] * 10) * 6, dtype=int)
    rng = np.random.default_rng(5)
    idx = pd.to_datetime([BASE_MS + i * HOUR_MS for i in range(n)], unit="ms")
    return pd.DataFrame({f"f{i}": rng.standard_normal(n) for i in range(8)}, index=idx), y


def _bind(orch: ICFilterOrchestrator, feats: pd.DataFrame, y: np.ndarray) -> None:
    ms = (feats.index.asi8 // 10**6).astype("int64")
    rows = frozenset((f"e{i}", int(t), int(v)) for i, (t, v) in enumerate(zip(ms, y)))
    orch._ic_cache = {"event_binary_label": ValidatedBinaryLabel(
        series=pd.Series(y.astype(float), index=feats.index), digest=binary_label_digest(rows), rows_frozenset=rows,
        n_pos=int((y == 1).sum()), n_neg=int((y == 0).sum()),
    )}
    orch._binary_label_window_bars = 2
    orch._binary_feature_bar_ms = HOUR_MS


def _run_negative_control(orch: ICFilterOrchestrator, feats: pd.DataFrame) -> Dict[str, Any]:
    _, receipt = orch._run_binary_permutation_and_negative_control(
        ["f0"], {}, feats, orch._config, alpha_effective=0.05, fdr_method="fdr_bh",
    )
    return receipt["negative_control"]


def test_negative_control_runs_planned_count_even_when_first_call_takes_20s(monkeypatch: pytest.MonkeyPatch) -> None:
    """同 seed、第一次全表 Mann-Whitney 耗時注入 20 秒（假時鐘，不真睡）⇒ 實跑次數 == `negative_control_n`，且置亂計數與
    未注入時逐值相同（改前：預算 60 秒 ÷ 20 秒 ⇒ 縮為 5 次並標 degraded_by_budget）。"""
    n_planned = 8
    feats, y = _event_inputs()
    base = _event_orch(n_planned)
    _bind(base, feats, y)
    baseline = _run_negative_control(base, feats)

    clock = SimpleNamespace(t=0.0)
    real_mw = orch_mod.mann_whitney_table
    calls: List[int] = []

    def slow_mw(*args: Any, **kwargs: Any) -> Any:
        calls.append(1)
        if len(calls) == 1:
            clock.t += 20.0
        return real_mw(*args, **kwargs)

    monkeypatch.setattr(orch_mod, "mann_whitney_table", slow_mw)
    monkeypatch.setattr(orch_mod, "_time", SimpleNamespace(perf_counter=lambda: clock.t))
    orch = _event_orch(n_planned)
    _bind(orch, feats, y)
    progress: List[Dict[str, Any]] = []
    orch._progress_callback = progress.append
    nc = _run_negative_control(orch, feats)

    assert len(calls) == n_planned
    assert nc["n_planned"] == n_planned and nc["n_effective"] == n_planned
    assert len(nc["shuffled_counts"]) == n_planned
    assert nc["shuffled_counts"] == baseline["shuffled_counts"], "同 seed 之置亂計數不得因耗時而變"
    assert "degraded_by_budget" not in nc and "budget_seconds" not in nc
    # 耗時以進度揭露（子步驟 done/total＋ETA；第一次 20 秒 ⇒ 剩 7 次之 ETA 為正）
    steps = [p for p in progress if p.get("sub_step") == "negative_control"]
    assert [p["sub_done"] for p in steps] == list(range(1, n_planned + 1))
    assert {p["sub_total"] for p in steps} == {n_planned}
    assert steps[0]["eta_state"] == "ok" and steps[0]["eta_seconds"] > 0
    assert steps[-1]["eta_state"] == "done"


def test_negative_control_budget_key_removed_from_schema() -> None:
    """`negative_control_budget_seconds` 自 schema 刪除；舊請求帶此鍵 ⇒ 依 pydantic 預設（extra＝ignore，同本檔其他未列鍵）
    忽略，不影響次數。"""
    assert "negative_control_budget_seconds" not in EventFilterConfig.model_fields
    cfg = ICConfig.model_validate({"event_filter": {"negative_control_budget_seconds": 0.0, "negative_control_n": 7}})
    assert not hasattr(cfg.event_filter, "negative_control_budget_seconds")
    assert cfg.event_filter.negative_control_n == 7


def test_negative_control_budget_key_warns_as_removed_key(caplog: pytest.LogCaptureFixture) -> None:
    """依本專案移除鍵慣例（契約 `removed_config_keys`＋`_warn_removed_keys`）：舊設定帶 `event_filter.negative_control_budget_seconds`
    ⇒ 發 ICHC-REMOVED-KEY 警告一則（不靜默吞鍵）；不帶 ⇒ 無此警告。"""
    import logging

    from momentum.Analysis.ic_config_schema import load_ic_config

    with caplog.at_level(logging.WARNING):
        load_ic_config(api_override={"event_filter": {"negative_control_budget_seconds": 60.0}})
    hits = [r.getMessage() for r in caplog.records if "ICHC-REMOVED-KEY" in r.getMessage()]
    assert len(hits) == 1 and "event_filter.negative_control_budget_seconds" in hits[0], hits
    caplog.clear()
    with caplog.at_level(logging.WARNING):
        load_ic_config(api_override={"event_filter": {"negative_control_n": 7}})
    assert not [r for r in caplog.records if "ICHC-REMOVED-KEY" in r.getMessage()]


#: 刪欄前（HEAD 6d6fa6c0）實測之 config_hash（`runs/icperf/task04/probes/v559_config_hash.py` 於 HEAD worktree 之輸出）
HEAD_HASH_SCHEMA_DEFAULT = "64027ea64515424f39a9b3a04372a97c"
HEAD_HASH_EVENT_N30 = "44126696ab1d6f77770fbff6650e659a"


def test_config_hash_unchanged_by_removed_budget_key() -> None:
    """刪欄後 config_hash 與刪欄前逐字相同（`_HASH_REMOVED_FIELD_LEGACY_DEFAULTS` 補回刪除前之預設值）；舊請求帶任意
    budget 值 ⇒ 該鍵已無作用 ⇒ 雜湊同預設。mutation：拿掉補回 ⇒ 兩個 HEAD 字面皆紅。"""
    orch = ICFilterOrchestrator(ICConfig())
    assert orch._hash_config(ICConfig()) == HEAD_HASH_SCHEMA_DEFAULT
    assert orch._hash_config(ICConfig.model_validate({"event_filter": {"negative_control_n": 30}})) == HEAD_HASH_EVENT_N30
    legacy = ICConfig.model_validate({"event_filter": {"negative_control_budget_seconds": 5.0}})
    assert orch._hash_config(legacy) == HEAD_HASH_SCHEMA_DEFAULT


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# (ae) 跨標的主 IC 標籤依 labels.return_type（真實 kline）
# ══════════════════════════════════════════════════════════════════════════════════════════════════

XSEC_TF = "12h"
RETURN_TYPES = ("simple", "log", "risk_adjusted")


def _kline_closes(tf: str = XSEC_TF) -> Dict[str, pd.Series]:
    """`kline_cache.h5` 該週期全部標的之完整收盤（float64；索引＝epoch 秒轉 naive DatetimeIndex，同服務之 kline 讀取）。"""
    import h5py

    if not KLINE_H5.is_file():
        pytest.fail(f"requires_kline: missing {KLINE_H5}")
    out: Dict[str, pd.Series] = {}
    with h5py.File(KLINE_H5, "r") as fh:
        for sym in sorted(k for k in fh.keys() if not k.startswith("_") and tf in fh[k]):
            data = fh[f"{sym}/{tf}/data"][:]
            idx = pd.DatetimeIndex(pd.to_datetime(data["timestamp"].astype("int64"), unit="s"))
            out[sym] = pd.Series(data["close"].astype(np.float64), index=idx)
    assert len(out) >= 5, f"前提失效：{tf} 標的數 {len(out)} < 5"
    return out


def _oracle_label(close: pd.Series, return_type: str) -> np.ndarray:
    """獨立 oracle（numpy 直算，不經 LabelGenerator）：simple＝c[t+1]/c[t]−1；log＝ln(c[t+1]/c[t])；risk_adjusted＝simple／
    （含 t 之前 21 根簡單報酬之樣本標準差，ddof=1；不足 21 根 ⇒ NaN）。"""
    c = close.to_numpy(dtype=np.float64)
    nxt = np.append(c[1:], np.nan)
    simple = nxt / c - 1.0
    if return_type == "simple":
        return simple
    if return_type == "log":
        return np.log(nxt / c)
    pct = np.append(np.nan, c[1:] / c[:-1] - 1.0)
    vol = np.full(c.size, np.nan)
    win = np.lib.stride_tricks.sliding_window_view(pct, 21)
    vol[20:] = np.std(win, axis=1, ddof=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        return simple / np.where(vol == 0.0, np.nan, vol)


def _causal_features(close: pd.Series) -> pd.DataFrame:
    """真實收盤之因果特徵（只用 0..t）：一根報酬、20 根乖離、10 根動能。"""
    ret = close.pct_change()
    frame = pd.DataFrame({"ret1": ret, "dev20": close / close.rolling(20).mean() - 1.0,
                          "mom10": close / close.shift(10) - 1.0}, index=close.index)
    frame.index.name = "timestamp"
    return frame


def _cross_df(closes: Dict[str, pd.Series]) -> pd.DataFrame:
    frames = []
    for sym, close in closes.items():
        frame = _causal_features(close)
        frame["_symbol"] = sym
        frames.append(frame)
    return pd.concat(frames, axis=0).set_index("_symbol", append=True)


def _assert_same(got: np.ndarray, exp: np.ndarray, where: str) -> None:
    got_nan, exp_nan = ~np.isfinite(got), ~np.isfinite(exp)
    assert np.array_equal(got_nan, exp_nan), f"{where}：缺值位置不同（{int(got_nan.sum())} vs {int(exp_nan.sum())}）"
    np.testing.assert_allclose(got[~got_nan], exp[~exp_nan], rtol=1e-12, atol=0.0, err_msg=where)


@pytest.mark.requires_kline
@pytest.mark.filterwarnings("ignore::RuntimeWarning")
@pytest.mark.parametrize("return_type", RETURN_TYPES)
def test_xsec_main_label_follows_return_type_on_real_kline(return_type: str) -> None:
    """服務 `_append_cross_sectional_labels(..., return_type=…)` 之 `return_1` == kline 直讀收盤之 oracle（全部 12h 標的、
    完整歷史；逐列、缺值位置相同）；且 == IC 衰減 h=1 所用之前瞻報酬（`ICEngine._compute_returns(close, 1, return_type)`）。"""
    from api.services.ic_analysis_service import ICAnalysisService

    closes = _kline_closes()
    labeled = ICAnalysisService()._append_cross_sectional_labels(
        _cross_df(closes), list(closes), XSEC_TF, return_type=return_type)
    engine = ICEngine({})
    for sym, close in closes.items():
        got = labeled.xs(sym, level="_symbol")[LABEL].to_numpy(dtype=np.float64)
        _assert_same(got, _oracle_label(close, return_type), f"{return_type}/{sym} 主標籤 vs oracle")
        decay_h1 = engine._compute_returns(close.reset_index(drop=True), 1, return_type).to_numpy(dtype=np.float64)
        _assert_same(got, decay_h1, f"{return_type}/{sym} 主標籤 vs 衰減 h=1")


def _run_service_xsec(closes: Dict[str, pd.Series], override: Dict[str, Any], tf: str) -> Dict[str, Any]:
    """經服務 `_run_analysis`（跨標的分支：特徵載入 → `_append_cross_sectional_labels` → `analyze_cross_sectional`）跑一次；
    特徵庫以真實收盤之因果特徵替身（`load_multi` 之形狀），標籤由服務自 kline 導出（不給 labels_path）。"""
    from api.models.ic_models import ICAnalyzeRequest
    from api.services.ic_analysis_service import ICAnalysisService

    service = ICAnalysisService()
    frames = {sym: _causal_features(close) for sym, close in closes.items()}
    service._feature_library = SimpleNamespace(load_multi=lambda *_a, **_k: frames)
    request = ICAnalyzeRequest(mode="cross_sectional", symbols=list(closes), timeframe=tf,
                               config_override=override)
    config_override = service._build_config_override(request)
    task_id = "v559-ae"
    service._tasks[task_id] = {"task_id": task_id, "status": "running", "progress": 0.0, "error": None,
                               "result": None}
    asyncio.run(service._run_analysis(task_id, create_ic_analyzer(config_override), request, config_override))
    info = service._tasks[task_id]
    assert info["status"] == "completed", info.get("error")
    return info["result"]


@pytest.mark.requires_kline
@pytest.mark.filterwarnings("ignore::RuntimeWarning")
@pytest.mark.parametrize("return_type", RETURN_TYPES)
def test_xsec_pearson_main_ic_equals_decay_h1_via_service(return_type: str) -> None:
    """服務端到端（Pearson、不切分）：summary `ic_mean`（主標籤之截面 IC 均值）== `ic_decay.<特徵>.ic_values[h=1]`（衰減 h=1
    之截面 IC 均值）——兩處同一報酬定義（改前主標籤固定一根對數報酬 ⇒ simple／risk_adjusted 不等）。

    資料格＝4h 全部標的完整歷史（5,088 根）：特徵框始於 kline 首根，故衰減（於分析段內逐標的計）與主標籤（kline 全序列計）之
    缺值位置相同；12h risk_adjusted（波動暖機）見 `test_xsec_risk_adjusted_12h_passes_coverage_and_main_ic_equals_decay_h1_via_service`。"""
    closes = _kline_closes("4h")
    report = _run_service_xsec(closes, {**NO_SPLIT, "global": {"default_method": "pearson"},
                                        "labels": {"return_type": return_type},
                                        "ic_calculation": {"ic_decay_horizons": [1, 2, 3]}}, "4h")
    rows = {r["feature_name"]: r for r in report["summary_table"]}
    assert set(rows) == {"ret1", "dev20", "mom10"}
    for name, row in rows.items():
        decay = report["ic_decay"][name]
        assert decay["horizons"][0] == 1
        assert math.isclose(float(row["ic_mean"]), float(decay["ic_values"][0]), rel_tol=1e-12, abs_tol=1e-15), (
            f"{return_type}/{name}：主 IC {row['ic_mean']!r} != 衰減 h=1 {decay['ic_values'][0]!r}")


@pytest.mark.requires_kline
@pytest.mark.filterwarnings("ignore::RuntimeWarning")
@pytest.mark.parametrize("return_type", RETURN_TYPES)
def test_label_backward_warmup_bars_equals_leading_nan_on_real_kline(return_type: str) -> None:
    """`LabelGenerator.backward_warmup_bars(return_type)`（跨標的覆蓋率守衛之結構暖機）== 真實收盤上該定義標籤之開頭連續
    缺值數（oracle＝`_oracle_label` 直算，不經 LabelGenerator；每個 12h 標的皆同）。"""
    from momentum.factories import create_label_generator

    got = create_label_generator().backward_warmup_bars(return_type)
    for sym, close in _kline_closes().items():
        lab = _oracle_label(close, return_type)
        lead = int(np.argmax(np.isfinite(lab)))
        assert got == lead, f"{return_type}/{sym}：暖機 {got} != 開頭缺值 {lead}"


def test_xsec_coverage_guard_floor_subtracts_warmup_and_still_rejects_extra_nan() -> None:
    """守衛結構下限＝(列數 − 前瞻 − 暖機)／列數，容忍度不變：恰為結構缺值 ⇒ 過；再多缺 >1%（相對下限）⇒ 拒收；
    暖機=0 時同一列（含 21 根開頭缺值、1,696 列）⇒ 拒收（改前行為，即 12h risk_adjusted 誤擋之形）。"""
    n, warm, h = 1696, 21, 1
    idx = pd.MultiIndex.from_product([pd.RangeIndex(n), ["S"]], names=["timestamp", "_symbol"])
    lab = np.arange(n, dtype=np.float64)
    lab[:warm] = np.nan
    lab[-h:] = np.nan
    df = pd.DataFrame({LABEL: lab}, index=idx)
    got = orch_mod._enforce_cross_sectional_label_coverage(df, LABEL, 1, h, 0.01, backward_warmup=warm)
    assert got["S"] == (n - h - warm) / n
    with pytest.raises(orch_mod.InvalidInputError, match="label coverage too low"):
        orch_mod._enforce_cross_sectional_label_coverage(df, LABEL, 1, h, 0.01, backward_warmup=0)
    extra = lab.copy()
    extra[warm:warm + 17] = np.nan  # 17 / 1674 ≈ 1.02% > 1%
    with pytest.raises(orch_mod.InvalidInputError, match="label coverage too low"):
        orch_mod._enforce_cross_sectional_label_coverage(
            pd.DataFrame({LABEL: extra}, index=idx), LABEL, 1, h, 0.01, backward_warmup=warm)


def _xsec_panel_leading_nan(n: int = 200, lead: int = 21) -> pd.DataFrame:
    """明列輸入：6 標的 × n 時點、in-frame `return_1` 每標的開頭 lead 根與末根缺值（＝risk_adjusted 暖機之形）。"""
    rng = np.random.default_rng(20261103)
    ts = pd.date_range("2024-01-01", periods=n, freq="h")
    syms = ("AAA", "BBB", "CCC", "DDD", "EEE", "FFF")
    idx = pd.MultiIndex.from_product([ts, syms], names=["timestamp", "symbol"])
    lab = rng.standard_normal((n, len(syms)))
    lab[:lead, :] = np.nan
    lab[-1, :] = np.nan
    return pd.DataFrame({"f1": rng.standard_normal(n * len(syms)), LABEL: lab.reshape(-1)}, index=idx)


def test_xsec_coverage_warmup_only_for_caller_declared_generated_label() -> None:
    """r71：暖機扣除只認呼叫端明示之生成標籤欄——同一 in-frame `return_1`（開頭 21 根缺值）× risk_adjusted：
    未宣告（外部提供之同名標籤）⇒ 依原守衛拒收；宣告 `generated_label_column="return_1"` ⇒ 扣暖機後通過；
    宣告他欄名 ⇒ 不扣、拒收（改前憑欄名即扣 ⇒ 第一、三條皆通過）。"""
    cfg = {**NO_SPLIT, "labels": {"return_type": "risk_adjusted"}}
    with pytest.raises(orch_mod.InvalidInputError, match="label coverage too low"):
        create_ic_analyzer().analyze_cross_sectional(_xsec_panel_leading_nan(), config_override=dict(cfg))
    with pytest.raises(orch_mod.InvalidInputError, match="label coverage too low"):
        create_ic_analyzer().analyze_cross_sectional(_xsec_panel_leading_nan(), config_override=dict(cfg),
                                                     generated_label_column="return_5")
    report = create_ic_analyzer().analyze_cross_sectional(_xsec_panel_leading_nan(), config_override=dict(cfg),
                                                          generated_label_column=LABEL)
    assert {r["feature_name"] for r in report["summary_table"]} == {"f1"}


def test_service_declares_generated_label_column_only_when_it_generates_labels() -> None:
    """服務跨標的分支：自 kline 導出標籤（無 labels_path）時傳 `generated_label_column`＝其寫入之欄名；給 labels_path 時傳 None。"""
    import inspect

    from api.services import ic_analysis_service as svc_mod

    src = inspect.getsource(svc_mod.ICAnalysisService)
    assert "generated_label_column=None if labels_path else XSEC_GENERATED_LABEL_COLUMN" in src
    assert "working_df.loc[symbol_mask, XSEC_GENERATED_LABEL_COLUMN] = aligned.to_numpy()" in src
    assert svc_mod.XSEC_GENERATED_LABEL_COLUMN == LABEL


@pytest.mark.requires_kline
@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_xsec_risk_adjusted_12h_passes_coverage_and_main_ic_equals_decay_h1_via_service() -> None:
    """12h（1,696 根）跨標的 × risk_adjusted 經服務：首 21 根波動暖機為定義上必然之缺值，不得被覆蓋率守衛誤擋；
    且主 IC == 衰減 h=1（同上條之報酬定義一致性）。"""
    closes = _kline_closes("12h")
    report = _run_service_xsec(closes, {**NO_SPLIT, "global": {"default_method": "pearson"},
                                        "labels": {"return_type": "risk_adjusted"},
                                        "ic_calculation": {"ic_decay_horizons": [1, 2, 3]}}, "12h")
    rows = {r["feature_name"]: r for r in report["summary_table"]}
    assert set(rows) == {"ret1", "dev20", "mom10"}
    for name, row in rows.items():
        assert math.isclose(float(row["ic_mean"]), float(report["ic_decay"][name]["ic_values"][0]),
                            rel_tol=1e-12, abs_tol=1e-15), name


@pytest.mark.requires_kline
@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_xsec_spearman_main_ic_identical_for_log_and_simple_on_real_kline() -> None:
    """Spearman（預設）下主標籤由 log 改 simple（預設 return_type）⇒ 每截面秩相同 ⇒ 主 IC 序列與 summary 之 IC 欄逐值相同；
    前提：兩標籤之值確實不同（否則本條無辨識力）。"""
    from api.services.ic_analysis_service import ICAnalysisService

    closes = _kline_closes()
    svc = ICAnalysisService()
    reports = {}
    for rt in ("log", "simple"):
        labeled = svc._append_cross_sectional_labels(_cross_df(closes), list(closes), XSEC_TF, return_type=rt)
        reports[rt] = create_ic_analyzer().analyze_cross_sectional(labeled, config_override=dict(NO_SPLIT))
        if rt == "simple":
            log_lab = svc._append_cross_sectional_labels(_cross_df(closes), list(closes), XSEC_TF, return_type="log")
            assert not np.allclose(labeled[LABEL].to_numpy(), log_lab[LABEL].to_numpy(), equal_nan=True)
    a, b = reports["log"], reports["simple"]
    assert a["rolling_ic_series"] == b["rolling_ic_series"]
    rows_a = {r["feature_name"]: r for r in a["summary_table"]}
    rows_b = {r["feature_name"]: r for r in b["summary_table"]}
    for name in rows_a:
        for key in ("ic_mean", "ic_std", "icir", "ic_hit_rate", "t_stat", "p_value", "p_value_adj"):
            assert rows_a[name][key] == rows_b[name][key], f"{name}.{key}"


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# (ag) 舊 IC 自相關方法已刪
# ══════════════════════════════════════════════════════════════════════════════════════════════════


def test_old_ic_autocorrelation_method_removed() -> None:
    """`ICEngine.compute_ic_autocorrelation`（兩段 Pearson、無呼叫者）已刪；產品之 IC 自相關唯一實作＝`ic_lag1_autocorrelation`。"""
    assert not hasattr(ICEngine, "compute_ic_autocorrelation")
    assert callable(orch_mod.ic_lag1_autocorrelation)


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# (ah) FDR 委派 statsmodels
# ══════════════════════════════════════════════════════════════════════════════════════════════════

FDR_CASES: Dict[str, Dict[str, float]] = {
    "plain": {"a": 0.01, "b": 0.02, "c": 0.5},
    "ties": {"a": 0.04, "b": 0.04, "c": 0.04, "d": 0.001},
    "single": {"only": 0.03},
    "edges": {"x": 0.0, "y": 1.0, "z": 0.012, "w": 0.3, "v": 0.012, "u": 0.7},
    "many": {f"k{i}": p for i, p in enumerate(np.random.default_rng(3).uniform(0, 0.2, 57).tolist())},
}


def _sm_bh(p: Dict[str, float]) -> Dict[str, float]:
    finite = [k for k, v in p.items() if math.isfinite(v)]
    out = {k: math.nan for k in p}
    if finite:
        adj = multipletests([p[k] for k in finite], method="fdr_bh")[1]
        out.update({k: float(a) for k, a in zip(finite, adj)})
    return out


def _same(got: Dict[str, float], exp: Dict[str, float]) -> bool:
    return set(got) == set(exp) and all(
        (math.isnan(exp[k]) and math.isnan(got[k])) or got[k] == exp[k] for k in exp)


@pytest.mark.parametrize("case", sorted(FDR_CASES))
def test_fdr_bh_equals_statsmodels_exactly(case: str) -> None:
    """`_fdr_bh` 逐值 `==` statsmodels（非近似）；含並列 p、0 與 1、單元素。"""
    p = FDR_CASES[case]
    assert _same(StatisticalValidator._fdr_bh(dict(p)), _sm_bh(p))


def test_fdr_bh_keeps_nan_positions() -> None:
    """NaN／±inf 保位為 NaN、不入檢定集合（其餘之 q == statsmodels 對有限 p 之校正）。"""
    p = {"a": 0.01, "b": math.nan, "c": 0.04, "d": 0.04, "e": math.inf, "f": 0.2}
    assert _same(StatisticalValidator._fdr_bh(dict(p)), _sm_bh(p))


def test_apply_fdr_still_exact_whitelist_and_matches_statsmodels() -> None:
    """應用層 `apply_fdr` 白名單照舊（非精確 "fdr_bh" ⇒ ValueError），其 q 逐值 == statsmodels。"""
    p = dict(FDR_CASES["edges"], bad=math.nan)
    q, n_tests = apply_fdr(p, 0.05)
    assert n_tests == 6 and _same(q, _sm_bh(p))
    for bad in ("FDR_BH", " fdr_bh", "fdr", None):
        with pytest.raises(ValueError):
            apply_fdr({"a": 0.1}, 0.05, method=bad)  # type: ignore[arg-type]
