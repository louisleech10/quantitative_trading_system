"""ICPERF SPEC v5.86 Task 0.6 (h) L1a：IC 設定參數上界（② 無數學依據之上界）——後端。

施工輸入＝L0 機讀表（git 物件 1eeef821:tests/_golden/icperf/limit_inventory.json）之 L1 needs_fix 列；每個測試以
`@pytest.mark.limit_rows((file, L0 line, code_sha256), ...)` 具名對應其覆蓋之落點。

f1／f2 判定（靜態，SPEC (h)）：本子批全部單元之舊預設值皆在舊界內、舊預設請求不觸發舊界 ⇒ 全為 f1。
驗收走產品路徑（審查 r159 CODEX-R159-P1-01）：`momentum.factories.create_ic_analyzer(config)`（＝`load_ic_config(api_override=…)`
＋`ICFilterOrchestrator`，同 `api/routes/ic_analysis.py:580`）建編排器，呼叫其實際階段方法（`_run_factor_return`、
`_run_factor_centrality`、`_run_trend_analysis`、`_run_parameter_sensitivity`、`_run_rolling_oos`、`_run_factor_exposure`、
`_run_long_short`、`_run_feature_quality_diagnostics`、`_run_net_ic`、`_stage6b_marginal_ic`）；於分析器建構處掛監看，
斷言計算端實際收到之設定與其持有之參數。編排器若漏傳、寫死或夾值即紅。
舊預設請求之計算結果不變（審查 r159 CODEX-R159-P1-02）：以真實 kline（BTCUSDT 1h 末 600 根）建最小快取，以預設設定跑
上列各階段，輸出（含例外）之 sha256 須等於施工前擷取之值（`DEFAULT_DIGESTS`）。
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import pytest
from pydantic import ValidationError

from momentum.Analysis.ic_config_schema import load_ic_config

REPO = Path(__file__).resolve().parents[3]
KLINE_CACHE = REPO / "data_cache" / "feature_klines" / "kline_cache.h5"
Row = Tuple[str, int, str]
SCHEMA = "momentum/Analysis/ic_config_schema.py"
INF = float("inf")
NAN = float("nan")


def _row(line: int, sha: str) -> Row:
    return (SCHEMA, line, sha)


def _override(path: str, field: str, value: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {field: value}
    for part in reversed(path.split(".")):
        out = {part: out}
    return out


def _section(cfg: Any, path: str) -> Any:
    obj = cfg
    for part in path.split("."):
        obj = getattr(obj, part)
    return obj


# ── 真實 kline 之最小快取 ────────────────────────────────────────────────────────────────────────────

LONGHIST_CACHE = REPO / "data_cache" / "feature_klines_longhist" / "kline_cache.h5"


def _real_kline(rows: int = 600, symbol: str = "BTCUSDT", tf: str = "1h") -> pd.DataFrame:
    import h5py

    src = LONGHIST_CACHE if tf == "5m" else KLINE_CACHE
    assert src.is_file(), f"真實 kline 不存在：{src}"
    with h5py.File(src, "r") as f:
        data = f[f"{symbol}/{tf}/data"][-rows:]
    assert len(data) == rows, f"{symbol}/{tf} 只有 {len(data)} 根 < {rows}"
    idx = pd.to_datetime(data["timestamp"].astype("int64"), unit="s", utc=True)
    return pd.DataFrame({k: data[k].astype("float64") for k in ("close", "volume", "quote_volume")}, index=idx)


def _cache(rows: int = 600, symbol: str = "BTCUSDT", tf: str = "1h", family: Tuple[int, ...] = (6, 12, 24),
           n_lag: int = 0, close_level: bool = False, ic_window: int = 63,
           cols: Optional[Tuple[str, ...]] = None) -> Dict[str, Any]:
    """因果特徵（只用 0..t）＋前瞻一根報酬標籤＋各特徵 `ic_window` 根滾動相關序列。
    `madev_<w>`（w∈family）為同一參數族（`parameter_sensitivity_analyzer.py:67` 族名規則 `<名>_<數字>`），預設三變體達
    min_family_size 3，使參數敏感度階段實際算出族結果（審查 r160 CODEX-R160-P1-01）。預設參數之輸出與施工前相同（指紋所用）；
    越舊界驗收依產品之樣本／維度門檻放大列數、族大小、特徵數（審查 r163 CODEX-R163-P1-02）。"""
    k = _real_kline(rows, symbol, tf)
    c = k["close"]
    data: Dict[str, pd.Series] = {
        "ret1": c.pct_change(),
        "vol24_ratio": k["volume"] / k["volume"].rolling(24).mean() - 1.0,
        **{f"madev_{w}": c / c.rolling(w).mean() - 1.0 for w in family},
        **{f"retlag_{j}": c.pct_change().shift(j) for j in range(1, n_lag + 1)},
    }
    if close_level:
        data["close_level"] = c
    feats = pd.DataFrame(data, index=k.index)
    if cols is not None:
        feats = feats[list(cols)]
    labels = c.shift(-1) / c - 1.0
    rolling_ic = {name: {f"window_{ic_window}": feats[name].rolling(ic_window).corr(labels).tolist()}
                  for name in feats.columns}
    return {"features_df": feats, "label_series": labels, "rolling_ic": rolling_ic, "metadata": {"quote_currency": "USDT"},
            "close_series": c, "quote_value_series": k["quote_volume"]}


FEATS = ["ret1", "vol24_ratio", "madev_6", "madev_12", "madev_24"]


def _prepare_net_ic(orch: Any) -> None:
    """Net IC 之上游輸入：先跑產品 factor_return 階段（建 series owner），再以同一真實快取算各特徵 IC 均值（Spearman）
    與分位換手率（五分位標籤逐根變動比例之平均）填入報告（同 `_run_net_ic` 所讀之 summary_table／turnover_analysis）。"""
    orch._run_factor_return(FEATS, orch._config)
    cache = orch._ic_cache
    feats, labels = cache["features_df"], cache["label_series"]
    summary, turnover = [], {}
    for name in FEATS:
        pair = pd.concat([feats[name], labels], axis=1).dropna()
        summary.append({"feature_name": name, "ic_mean": float(pair.iloc[:, 0].rank().corr(pair.iloc[:, 1].rank()))})
        q = pd.qcut(feats[name].dropna(), 5, labels=False)
        turnover[name] = {"quantile_turnover": float((q.diff().fillna(0) != 0).mean())}
    orch._report = {"summary_table": summary, "turnover_analysis": turnover}


def _orchestrator(config: Optional[Dict[str, Any]] = None, cache: Optional[Dict[str, Any]] = None) -> Any:
    from momentum.factories import create_ic_analyzer

    orch = create_ic_analyzer(config)
    orch._ic_cache = cache if cache is not None else _cache()
    orch._report = {}
    return orch


def _run_stage(orch: Any, stage: str) -> Any:
    cfg = orch._config
    cache = orch._ic_cache
    feats = list(cache["features_df"].columns)
    if stage == "marginal_ic":
        return orch._stage6b_marginal_ic(cache["features_df"], cache["label_series"], {"passed_features": feats},
                                         {"filtered_df": cache["features_df"]}, None, cfg, fit_scope="full_sample")
    if stage == "net_ic":
        _prepare_net_ic(orch)
    return getattr(orch, f"_run_{stage}")(feats, cfg)


# 區段 → (階段, 建構點之模組與名稱, 欄位 → 計算端屬性)
STAGES: Dict[str, Tuple[str, str, str, Dict[str, str]]] = {
    "marginal_ic": ("marginal_ic", "momentum.Analysis.ic_filter_orchestrator", "MarginalICParams", {"n_bootstrap": "n_bootstrap"}),
    "factor_return": ("factor_return", "momentum.factories", "create_factor_return_analyzer", {"num_quantiles": "_num_quantiles"}),
    "factor_centrality": ("factor_centrality", "momentum.Analysis.factor_centrality_analyzer", "FactorCentralityAnalyzer",
                          {"n_components": "_n_components", "rolling_window": "_rolling_window",
                           "crowding_threshold_relative": "_tau", "min_samples_for_pca": "_min_samples"}),
    "trend_analysis": ("trend_analysis", "momentum.Analysis.trend_analyzer", "TrendAnalyzer",
                       {"min_samples": "_min_samples", "significance_level": "_significance"}),
    "parameter_sensitivity": ("parameter_sensitivity", "momentum.Analysis.parameter_sensitivity_analyzer",
                              "ParameterSensitivityAnalyzer", {"min_family_size": "_min_family_size"}),
    "rolling_oos": ("rolling_oos", "momentum.Analysis.rolling_oos_validator", "RollingOOSValidator",
                    {"train_window": "_train_window", "test_window": "_test_window", "step": "_step",
                     "min_splits": "_min_splits", "robust_max_degradation": "_robust_max_degradation",
                     "moderate_max_degradation": "_moderate_max_degradation"}),
    "factor_exposure": ("factor_exposure", "momentum.Analysis.factor_exposure_analyzer", "FactorExposureAnalyzer",
                        {"neutralization_lookback": "_neutralization_lookback"}),
    "long_short_analysis": ("long_short", "momentum.Analysis.long_short_analyzer", "LongShortAnalyzer",
                            {"num_quantiles": "_num_quantiles"}),
    "feature_quality_diagnostics": ("feature_quality_diagnostics", "momentum.Analysis.feature_quality_diagnostics",
                                    "FeatureQualityDiagnostics",
                                    {f: f"_{f}" for f in ("adf_significance", "ljungbox_lags", "ljungbox_significance",
                                                          "adf_min_samples", "drift_window", "drift_threshold")}),
    "net_ic_analysis": ("net_ic", "momentum.Analysis.net_ic_analyzer", "NetICAnalyzer", {"cost_bps": "_cost_bps"}),
}


def _spy(monkeypatch: pytest.MonkeyPatch, module_name: str, attr: str) -> List[Tuple[Any, Any]]:
    """於建構點掛監看：記錄 (傳入設定, 建出之物件)，行為照舊。類別只包 `__init__`（模組內之類別名仍指向原類別，
    類別自身之靜態方法呼叫不受影響）；工廠函式則包函式。"""
    import importlib

    mod = importlib.import_module(module_name)
    real = getattr(mod, attr)
    calls: List[Tuple[Any, Any]] = []

    if isinstance(real, type):
        init = real.__init__

        def wrapped_init(self: Any, *args: Any, **kwargs: Any) -> None:
            init(self, *args, **kwargs)
            if type(self) is real:
                calls.append((args[0] if args else kwargs, self))

        monkeypatch.setattr(real, "__init__", wrapped_init)
        return calls

    def wrapper(*args: Any, **kwargs: Any) -> Any:
        obj = real(*args, **kwargs)
        calls.append((args[0] if args else kwargs, obj))
        return obj

    monkeypatch.setattr(mod, attr, wrapper)
    return calls


def _stage_through_product(monkeypatch: pytest.MonkeyPatch, section: str, config: Optional[Dict[str, Any]],
                           cache: Optional[Dict[str, Any]] = None) -> Tuple[List[Tuple[Any, Any]], Any]:
    """經產品編排器之實際階段方法跑一次：回傳 (建構點監看紀錄, 階段輸出)。例外不吞（審查 r163 CODEX-R163-P1-02）。"""
    stage, module_name, attr, _ = STAGES[section]
    calls = _spy(monkeypatch, module_name, attr)
    out = _run_stage(_orchestrator(config, cache), stage)
    assert calls, f"{section}：編排器階段未建構計算端（{module_name}.{attr}）"
    return calls, out


def _stage_output(section: str, config: Optional[Dict[str, Any]], cache: Dict[str, Any]) -> Any:
    return _run_stage(_orchestrator(config, cache), STAGES[section][0])


def _merge(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(a)
    for k, v in b.items():
        out[k] = _merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


# (L0 列, 區段路徑, 欄位, 越舊界之合法值〔舊界之上最小值〕, 修前預設值, 依數學定義域須仍拒之值)
UNITS: List[Tuple[Row, str, str, Any, Any, List[Any]]] = [
    (_row(207, "87e0bbffa42448c2208b2bcd8c91cb670f389fcea9a484ca0ad6a34a7f10a97e"), "marginal_ic", "n_bootstrap", 20001, 1000, [0, 1.5]),
    (_row(246, "c43c91f4caf60658796b06da6f5cef6335abaa1ca6465734e06011571b72189f"), "factor_return", "num_quantiles", 21, 5, [1, 2.5]),
    (_row(257, "bf96d2e8114ae8d609451b790f61620235ea6074ca91391253ecd5134eab3c84"), "factor_centrality", "n_components", 51, 5, [0, 1.5]),
    (_row(258, "e9a6c3b00eb3542ab16a939c11b4124ad24599ed52c7535bc35a3d4eef1a12ea"), "factor_centrality", "rolling_window", 501, 60, [4, 1.5]),
    (_row(263, "426a7aa8653cb48c515fae6c3519ed08ba9fc7084faadc4388f1bad3e5fc58bd"), "factor_centrality", "crowding_threshold_relative", 2000.0, 1.5, [0.0, INF, NAN]),
    (_row(264, "407c9cd97df4389beb7807f7a5b259fef292d3bb4b5d9a14fed39e2583b27f5e"), "factor_centrality", "min_samples_for_pca", 10001, 30, [9, 1.5]),
    (_row(269, "5d60515d80695072b587350096ae82e83696926de4c96b7e95bd21862ef38e5a"), "trend_analysis", "min_samples", 10001, 20, [4, 1.5]),
    (_row(270, "8377856e7ad112f1a7f4fd24098c2baf6e5162bd265e61680592260a171765cc"), "trend_analysis", "significance_level", 0.5, 0.05, [0.0, 1.0, INF, NAN]),
    (_row(279, "0d580fb7760218cc0fbcec40eede5f91d5f1dade2e551d833d5a69f5fd53a053"), "parameter_sensitivity", "min_family_size", 101, 3, [1, 1.5]),
    (_row(287, "02530a39505cce6b2151c9e5d80edbd1619e70eb23c3bc35d5ba1704347d1c24"), "rolling_oos.assessment_thresholds", "robust_max_degradation", 6.0, 0.3, [-0.1, INF, NAN]),
    (_row(289, "ab91605ab102c139c652f3f2af2f4fa126a5ea60910e5f39cead937d5ec024a5"), "rolling_oos.assessment_thresholds", "moderate_max_degradation", 6.0, 0.5, [-0.1, INF, NAN]),
    (_row(294, "f8a93ebc6ab7ffb14f1307b8f486a34f63b1b2dc6f2b01b09e332fab892bc48c"), "rolling_oos", "train_window", 20001, 252, [9, 1.5]),
    (_row(295, "8668bf825743dff720660cffddf9bb15c019577bed1a93dfd41bd2c83ccaf409"), "rolling_oos", "test_window", 5001, 63, [4, 1.5]),
    (_row(296, "4887e455c2e35c23c3d4af084078e26450313630d4d736cfd147b78f8da3e301"), "rolling_oos", "step", 5001, 21, [0, 1.5]),
    (_row(297, "b0f042192946bfc55a97cae6408936124f147669fd85eafa54858e931467d03f"), "rolling_oos", "min_splits", 201, 5, [0, 1.5]),
    (_row(312, "93a81a9795550c4b9c514d2fec0a79a1504012f623ff6ccb901ecf6f380ffa9f"), "factor_exposure", "neutralization_lookback", 5001, 63, [4, 1.5]),
    (_row(319, "c43c91f4caf60658796b06da6f5cef6335abaa1ca6465734e06011571b72189f"), "long_short_analysis", "num_quantiles", 21, 5, [1, 2.5]),
    (_row(340, "2b7b71d0777b9d694d3b5b075ea3f5621d3dc1221a364c6718e58f3da62a326c"), "feature_quality_diagnostics", "adf_significance", 0.5, 0.05, [0.0, 1.0, INF, NAN]),
    (_row(341, "017cdbdbace23ef48225dfd9b1890ebd309f343f601302d4aec6a4cecf41f69a"), "feature_quality_diagnostics", "ljungbox_lags", 501, 10, [0, 1.5]),
    (_row(342, "ed817f22ae02c0324a52ef1adbd9926332c55acb8ec8c6aee63e3cb14aca2a95"), "feature_quality_diagnostics", "ljungbox_significance", 0.5, 0.05, [0.0, 1.0, INF, NAN]),
    (_row(345, "f69ec439f41cc17d1aacedbeaeceddb92d1365caecdfcb15cee14f81fdc55e9d"), "feature_quality_diagnostics", "adf_min_samples", 100001, 20, [9, 1.5]),
    (_row(347, "52915552732766b1239015fcd917dddb9ae952718e1b775961c8045de3fbbce0"), "feature_quality_diagnostics", "drift_window", 5001, 60, [9, 1.5]),
    (_row(348, "2c447d26f07f88b2c9bc7b0f11bda872c6372393e5fd263a6903294c0f28aca4"), "feature_quality_diagnostics", "drift_threshold", 20.0, 0.25, [-0.1, INF, NAN]),
]


def _unit_params() -> List[Any]:
    return [pytest.param(path, field, over, default, illegal,
                         marks=pytest.mark.limit_rows(row), id=f"{path}.{field}")
            for row, path, field, over, default, illegal in UNITS]


def _received(section_path: str, field: str, calls: List[Tuple[Any, Any]]) -> Tuple[Any, Any]:
    """(建構點收到之設定值, 計算端物件持有之值)；取第一次建構。"""
    top = section_path.split(".")[0]
    cfg_arg, obj = calls[0]
    attr = STAGES[top][3][field]
    if top == "marginal_ic":
        return cfg_arg.get(field) if isinstance(cfg_arg, dict) else getattr(obj, field), getattr(obj, attr)
    sub = cfg_arg
    for part in section_path.split(".")[1:]:
        sub = sub[part]
    return sub[field], getattr(obj, attr)


# ── 越舊界之合法請求「可算」（SPEC (h) f1；審查 r163 CODEX-R163-P1-02）──────────────────────────────────────────
# 每單元依產品之樣本／維度門檻配最小足量之真實 kline（1h 單標的 20,352 根；5m 長歷史 105,260 根），斷言該分支實際算出
# 有限結果並帶有越界值之痕跡（實際成分數、窗長、分箱數、切分設定等）；樣本門檻類另以門檻下一列之同請求反證門檻值生效；
# 顯著水準與門檻類於真實資料段（探針 runs/limit_audit/l1a/decisive_probe*.py 所選）使判定與舊預設不同，並逐特徵以輸出值
# 重驗判定規則（漂移之 CUSUM 以 statsmodels `breaks_cusumolsresid` 獨立重算）。

def _fin(x: Any) -> bool:
    return isinstance(x, (int, float, np.floating, np.integer)) and not isinstance(x, bool) and math.isfinite(float(x))


DECISIVE = dict(rows=600, symbol="ETHUSDT")                       # 趨勢／Ljung-Box／OOS 判定隨門檻改變之真實段
DECISIVE_ADF_DRIFT = dict(rows=600, symbol="ETHUSDT", close_level=True, ic_window=10)   # ADF／漂移判定隨門檻改變


def _chk_marginal(out: Any, cache: Dict[str, Any], cfg: Dict[str, Any]) -> None:
    assert out["status"] == "ok", out.get("reason")
    for name, r in out["per_feature"].items():
        assert r["status"] == "ok" and len(r["ci95"]) == 2 and all(_fin(v) for v in r["ci95"]), (name, r)


def _chk_factor_return(out: Any, cache: Dict[str, Any], cfg: Dict[str, Any]) -> None:
    assert out["status"] == "ok", out.get("reason")
    for name, r in out["value"]["features"].items():
        assert r["num_quantiles_used"] == 21, name
        assert {f"Q{i}" for i in range(1, 22)} <= set(r["quantile_summary"]), name
        assert _fin(r["risk_metrics"]["sharpe_ratio"]) and _fin(r["turnover"]), name


def _chk_n_components(out: Any, cache: Dict[str, Any], cfg: Dict[str, Any]) -> None:
    ps = out["pca_summary"]
    assert ps["n_components_used"] == 51 and len(ps["explained_variance_ratio"]) == 51
    assert all(_fin(v) for v in ps["explained_variance_ratio"]) and _fin(ps["total_variance_explained"])


def _chk_rolling_window(out: Any, cache: Dict[str, Any], cfg: Dict[str, Any]) -> None:
    n = len(cache["features_df"])
    assert set(out["rolling_centrality"]) == set(cache["features_df"].columns)
    for name, s in out["rolling_centrality"].items():
        assert len(s) == n - 501 + 1 and all(_fin(v) for v in s), name


def _chk_tau(out: Any, cache: Dict[str, Any], cfg: Dict[str, Any]) -> None:
    cent = {k: v["centrality"] for k, v in out["features"].items()}
    cut = 2000.0 * float(np.mean(list(cent.values())))
    assert math.isclose(out["pca_summary"]["crowded_threshold"], cut, rel_tol=1e-12)
    assert all(out["features"][k]["crowded"] == (v > cut) for k, v in cent.items())


def _chk_pca_min_samples(out: Any, cache: Dict[str, Any], cfg: Dict[str, Any]) -> None:
    ps = out["pca_summary"]
    assert ps["n_components_used"] >= 1 and _fin(ps["total_variance_explained"])
    from momentum.core.exceptions import InsufficientDataError

    with pytest.raises(InsufficientDataError, match=r"n_samples\(10000\) < min_required\(10001\)"):
        _stage_output("factor_centrality", cfg, _cache(rows=10000))


def _chk_trend_min_samples(out: Any, cache: Dict[str, Any], cfg: Dict[str, Any]) -> None:
    for name, r in out.items():
        assert r["ic_trend"]["inference_status"] == "ok" and _fin(r["ic_trend"]["p_value"]), name
    below = _stage_output("trend_analysis", cfg, _cache(rows=10000))
    assert all("ic_trend" not in r and r["dimension_status"]["ic"] == "insufficient_data" for r in below.values()), \
        "有效點低於 min_samples 仍推論（門檻未生效）"


def _trend_label_rule(it: Dict[str, Any], alpha: float) -> str:
    """`trend_analyzer.py` 之標籤規則（顯著＝p＋誤差界 ≤ α，且 R² ≥ 0.1 ⇒ 依推論斜率號）。"""
    sig = it["p_value"] + it["p_abs_error"] <= alpha
    if sig and it["r_squared"] >= 0.1:
        return "up" if it["inference_slope"] > 0 else "down" if it["inference_slope"] < 0 else "flat"
    return "flat"


def _chk_trend_significance(out: Any, cache: Dict[str, Any], cfg: Dict[str, Any]) -> None:
    base = _stage_output("trend_analysis", None, cache)
    for name, r in out.items():
        assert r["ic_trend"]["inference_status"] == "ok", name
        assert r["ic_trend"]["trend"] == _trend_label_rule(r["ic_trend"], 0.5), name
    assert any(out[n]["ic_trend"]["trend"] != base[n]["ic_trend"]["trend"] for n in out), "α＝0.5 未改變任何判定"


def _chk_family(out: Any, cache: Dict[str, Any], cfg: Dict[str, Any]) -> None:
    assert out["summary"]["total_families"] == 1 and len(out["families"]["madev"]["variants"]) == 101
    below = _stage_output("parameter_sensitivity", cfg, _cache(family=tuple(range(2, 102))))
    assert below["summary"]["total_families"] == 0, "族成員 100 < min_family_size 101 仍成族（門檻未生效）"


def _chk_oos(field: str, value: int) -> Callable[[Any, Dict[str, Any], Dict[str, Any]], None]:
    def chk(out: Any, cache: Dict[str, Any], cfg: Dict[str, Any]) -> None:
        conf = out["config"]
        n = conf["n_splits"]
        assert (n >= value) if field == "min_splits" else (conf[field] == value), conf
        assert n >= 1 and out["summary"]["total_validated"] == len(cache["features_df"].columns)
        for name, r in out["features"].items():
            assert r["n_valid_splits"] == n and r["assessment"] in {"robust", "moderate", "overfitting"}, name
            assert all(_fin(r["oos_stability"][k]) for k in ("mean_oos_ic", "oos_hit_rate", "degradation_ratio")), name
    return chk


def _chk_oos_degradation(out: Any, cache: Dict[str, Any], cfg: Dict[str, Any]) -> None:
    base = _stage_output("rolling_oos", None, cache)
    for name, r in out["features"].items():
        h, d = r["oos_stability"]["oos_hit_rate"], r["oos_stability"]["degradation_ratio"]
        expect = "robust" if h >= 0.7 and d < 6.0 else "moderate" if h >= 0.5 and d < 6.0 else "overfitting"
        assert r["assessment"] == expect, name
    assert any(out["features"][n]["assessment"] != base["features"][n]["assessment"] for n in out["features"]), \
        "退化門檻 6.0 未改變任何評等"


def _chk_exposure(out: Any, cache: Dict[str, Any], cfg: Dict[str, Any]) -> None:
    assert out["neutralization_mode"] == "vol_neutral" and out["neutralization_lookback"] == 5001
    exp = out["neutralized_portfolio_exposure"]   # 回看只作用於中和後曝險（`ic_filter_orchestrator.py` _run_factor_exposure）
    assert set(exp) == set(cache["features_df"].columns) and all(_fin(v) for v in exp.values())
    short = _stage_output("factor_exposure", {"factor_exposure": {"neutralization_mode": "vol_neutral"}}, cache)
    assert exp != short["neutralized_portfolio_exposure"], "回看 5001 與預設 63 之中和後曝險相同（回看未生效）"


def _chk_long_short(out: Any, cache: Dict[str, Any], cfg: Dict[str, Any]) -> None:
    for name, r in out.items():
        assert r["num_quantiles_used"] == 21, name
        for side in ("long_analysis", "short_analysis"):
            assert r[side]["samples"] > 0 and _fin(r[side]["mean_return"]), (name, side)


def _chk_lb_lags(out: Any, cache: Dict[str, Any], cfg: Dict[str, Any]) -> None:
    for name, r in out["autocorrelation_results"].items():
        assert r["skipped"] is False and _fin(r["ljungbox_stat"]) and _fin(r["p_value"]), name


def _chk_rule(kind: str) -> Callable[[Any, Dict[str, Any], Dict[str, Any]], None]:
    key, flag = {"adf": ("adf_results", "is_stationary"), "lb": ("autocorrelation_results", "significant_autocorrelation")}[kind]

    def chk(out: Any, cache: Dict[str, Any], cfg: Dict[str, Any]) -> None:
        base = _stage_output("feature_quality_diagnostics", None, cache)
        for name, r in out[key].items():
            assert r["skipped"] is False and r[flag] == (r["p_value"] < 0.5), name
        assert any(out[key][n][flag] != base[key][n][flag] for n in out[key]), f"{kind} α＝0.5 未改變任何判定"
    return chk


def _chk_adf_min_samples(out: Any, cache: Dict[str, Any], cfg: Dict[str, Any]) -> None:
    for name, r in out["adf_results"].items():
        assert r["skipped"] is False and _fin(r["adf_statistic"]) and _fin(r["p_value"]), name
    # ret1 首根為 NaN ⇒ 100,001 根之有效樣本為 100,000，恰少門檻一個
    below = _stage_output("feature_quality_diagnostics", cfg, _cache(rows=100001, tf="5m", cols=("ret1",)))
    assert all(r["skipped"] is True for r in below["adf_results"].values()), "樣本 < adf_min_samples 仍跑 ADF（門檻未生效）"


def _chk_drift_window(out: Any, cache: Dict[str, Any], cfg: Dict[str, Any]) -> None:
    base = _stage_output("feature_quality_diagnostics", None, cache)
    for name, r in out["drift_results"].items():
        assert r["skipped"] is False and r["psi_reason"] is None and _fin(r["psi_score"]), name
    assert any(out["drift_results"][n]["psi_score"] != base["drift_results"][n]["psi_score"] for n in out["drift_results"])


def _chk_drift_threshold(out: Any, cache: Dict[str, Any], cfg: Dict[str, Any]) -> None:
    from statsmodels.stats.diagnostic import breaks_cusumolsresid

    base = _stage_output("feature_quality_diagnostics", None, cache)
    for name, r in out["drift_results"].items():
        s = pd.Series(next(iter(cache["rolling_ic"][name].values())), dtype=float).dropna()
        cusum_p = breaks_cusumolsresid((s - s.mean()).to_numpy(dtype=float), ddof=0)[1]
        expect = bool((math.isfinite(cusum_p) and cusum_p < 0.05) or (_fin(r["psi_score"]) and r["psi_score"] > 20.0))
        assert r["drifted"] is expect, name
    assert any(out["drift_results"][n]["drifted"] != base["drift_results"][n]["drifted"] for n in out["drift_results"]), \
        "漂移門檻 20 未改變任何判定"


FULL_1H = dict(rows=20352)
# 單元 → (同請求之其他合法設定, 真實資料規模, 算出判定)
OVER_WORKLOAD: Dict[str, Tuple[Dict[str, Any], Dict[str, Any], Callable[[Any, Dict[str, Any], Dict[str, Any]], None]]] = {
    "marginal_ic.n_bootstrap": ({}, dict(cols=("ret1", "madev_6")), _chk_marginal),
    "factor_return.num_quantiles": ({}, dict(rows=2000), _chk_factor_return),
    "factor_centrality.n_components": ({}, dict(n_lag=60), _chk_n_components),
    "factor_centrality.rolling_window": ({}, dict(rows=2000), _chk_rolling_window),
    "factor_centrality.crowding_threshold_relative": ({}, dict(rows=2000), _chk_tau),
    "factor_centrality.min_samples_for_pca": ({}, FULL_1H, _chk_pca_min_samples),
    "trend_analysis.min_samples": ({}, FULL_1H, _chk_trend_min_samples),
    "trend_analysis.significance_level": ({}, DECISIVE, _chk_trend_significance),
    "parameter_sensitivity.min_family_size": ({}, dict(family=tuple(range(2, 103))), _chk_family),
    "rolling_oos.assessment_thresholds.robust_max_degradation":
        ({"rolling_oos": {"assessment_thresholds": {"moderate_max_degradation": 6.0}}}, DECISIVE, _chk_oos_degradation),
    "rolling_oos.assessment_thresholds.moderate_max_degradation":
        ({"rolling_oos": {"assessment_thresholds": {"robust_max_degradation": 6.0}}}, DECISIVE, _chk_oos_degradation),
    "rolling_oos.train_window": ({"rolling_oos": {"min_splits": 1}}, FULL_1H, _chk_oos("train_window", 20001)),
    "rolling_oos.test_window": ({"rolling_oos": {"min_splits": 1}}, FULL_1H, _chk_oos("test_window", 5001)),
    "rolling_oos.step": ({"rolling_oos": {"min_splits": 1}}, FULL_1H, _chk_oos("step", 5001)),
    "rolling_oos.min_splits": ({}, FULL_1H, _chk_oos("min_splits", 201)),
    "factor_exposure.neutralization_lookback": ({"factor_exposure": {"neutralization_mode": "vol_neutral"}}, FULL_1H, _chk_exposure),
    "long_short_analysis.num_quantiles":
        ({"long_short_analysis": {"long_quantiles": [21], "short_quantiles": [1]}}, dict(rows=2000), _chk_long_short),
    "feature_quality_diagnostics.adf_significance": ({}, DECISIVE_ADF_DRIFT, _chk_rule("adf")),
    "feature_quality_diagnostics.ljungbox_lags": ({}, dict(rows=2000), _chk_lb_lags),
    "feature_quality_diagnostics.ljungbox_significance": ({}, DECISIVE, _chk_rule("lb")),
    "feature_quality_diagnostics.adf_min_samples": ({}, dict(rows=105260, tf="5m", cols=("ret1",)), _chk_adf_min_samples),
    "feature_quality_diagnostics.drift_window": ({}, FULL_1H, _chk_drift_window),
    "feature_quality_diagnostics.drift_threshold": ({}, DECISIVE_ADF_DRIFT, _chk_drift_threshold),
}


def test_over_workload_covers_every_unit() -> None:
    assert set(OVER_WORKLOAD) == {f"{path}.{field}" for _, path, field, *_ in UNITS}


@pytest.mark.slow
@pytest.mark.requires_kline
@pytest.mark.parametrize("path,field,over,default,illegal", _unit_params())
def test_over_old_bound_reaches_consumer_and_computes(monkeypatch: pytest.MonkeyPatch, path: str, field: str, over: Any,
                                                      default: Any, illegal: List[Any]) -> None:
    """f1：越舊界之合法值經產品編排器之實際階段方法抵達計算端（建構點收到之設定與計算端持有之參數），且於足量真實資料
    上實際算出（非資料不足分支；審查 r163 CODEX-R163-P1-02）。"""
    extra, workload, check = OVER_WORKLOAD[f"{path}.{field}"]
    cfg = _merge(extra, _override(path, field, over))
    cache = _cache(**workload)
    calls, out = _stage_through_product(monkeypatch, path.split(".")[0], cfg, cache)
    got_cfg, got_attr = _received(path, field, calls)
    assert got_cfg == over and got_attr == over
    check(out, cache, cfg)


@pytest.mark.parametrize("path,field,over,default,illegal", _unit_params())
def test_illegal_values_still_rejected(path: str, field: str, over: Any, default: Any, illegal: List[Any]) -> None:
    """f1：依各欄自身數學定義域之非法值仍拒（非整數、低於下界、inf／nan、α∉(0,1)）。"""
    for bad in illegal:
        with pytest.raises(ValidationError):
            load_ic_config(api_override=_override(path, field, bad))


@pytest.mark.requires_kline
@pytest.mark.parametrize("path,field,over,default,illegal", _unit_params())
def test_old_default_reaches_consumer_unchanged(monkeypatch: pytest.MonkeyPatch, path: str, field: str, over: Any,
                                                default: Any, illegal: List[Any]) -> None:
    """f1：舊預設請求之設定值與修前相同，且經產品編排器抵達計算端之值不變。"""
    assert getattr(_section(load_ic_config(), path), field) == default
    calls, _ = _stage_through_product(monkeypatch, path.split(".")[0], None)
    assert _received(path, field, calls) == (default, default)


def _digest(obj: Any) -> str:
    def norm(x: Any) -> Any:
        if isinstance(x, pd.DataFrame):
            return {"__df__": x.to_dict(orient="split")}
        if isinstance(x, pd.Series):
            return {"__s__": x.to_dict()}
        if isinstance(x, np.ndarray):
            return x.tolist()
        if isinstance(x, (np.floating, np.integer)):
            return x.item()
        return repr(x)
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=norm).encode("utf-8")).hexdigest()


def _default_stage_digest(section: str) -> str:
    orch = _orchestrator(None)
    try:
        out: Any = _run_stage(orch, STAGES[section][0])
    except Exception as exc:  # noqa: BLE001 —— 例外亦屬輸出之一部分
        out = {"__exception__": type(exc).__name__, "message": str(exc)}
    return _digest(out)


# 施工前（產品碼未改，HEAD 7b56d1c3）以本檔 `_default_stage_digest` 實跑擷取、連跑兩次相同；施工後須逐位元相同（SPEC (h) f1）。
# 十階段皆回傳 dict（無例外）；參數敏感度算出 madev 族（total_families 1）、Net IC 算出 5 特徵（evaluable_count 5）
# （審查 r160 CODEX-R160-P1-01）。
DEFAULT_DIGESTS: Dict[str, str] = {
    "factor_centrality": "0298cb8d9c8debabc95a39d1c4221d835122b224cf91e28218e13318c2037546",
    "factor_exposure": "02492799d3753d987ce15f4e4ae5c45dedb10fd4eade444848e0bd265709d4a2",
    "factor_return": "d6621409aba735af4629224ad09b39667ed369b8a97ca4fd6fb28bbfee29544d",
    "feature_quality_diagnostics": "1009f58075f4718808f9b0fb6b2bf12ad65e47f7fd3278fd4cc5ef24ef56a14b",
    "long_short_analysis": "9b5df20eb373d7f554a7c90bba7fcb1baee0da92ef6d97b15990c4738daacbfe",
    "marginal_ic": "40d19ac6bda524ba9aaa5676abe6cfaf83cf6555c333c849e59df8fed4588370",
    "net_ic_analysis": "e0195313a5f18ddba31a325f0922fed538097741f0317711a28c12cd383b041b",
    "parameter_sensitivity": "99222fee2867acf5c9da82e9c7455916efe1d7e5e7f02f14c106a083f8649491",
    "rolling_oos": "e91f4e1f8165d1eb18d507aff9194506aa5ce691ce28beded383cf87707c01e8",
    "trend_analysis": "6e0bc29baa28da9d914f0fec543c6dd57e36c8f506f6f5242a9c2f2d8e151f4f",
}


@pytest.mark.requires_kline
@pytest.mark.limit_rows(*[row for row, *_ in UNITS])
@pytest.mark.parametrize("section", sorted(STAGES))
def test_old_default_request_computation_unchanged(section: str) -> None:
    """f1：舊預設請求於真實 kline 最小快取上，各階段輸出（含例外）之 sha256 與施工前相同。"""
    assert section in DEFAULT_DIGESTS, f"{section} 未擷取施工前指紋"
    assert _default_stage_digest(section) == DEFAULT_DIGESTS[section]


COST_ROWS = {
    "request": ("api/models/ic_models.py", 58, "639ddc5639ce75bee79abab9ace28c3d0a663fe6ba219f0347774689a0e03b18"),
    "schema": (SCHEMA, 372, "639ddc5639ce75bee79abab9ace28c3d0a663fe6ba219f0347774689a0e03b18"),
    "analyzer": ("momentum/Analysis/net_ic_analyzer.py", 197, "639ddc5639ce75bee79abab9ace28c3d0a663fe6ba219f0347774689a0e03b18"),
    "ladder": ("momentum/Analysis/net_ic_analyzer.py", 274, "2b93ce266a915f8132ee65a56f1f1d49418c1ff9b663e2465f6cc49b83e6adeb"),
    "turnover": ("momentum/Analysis/turnover_analyzer.py", 215, "c40dc5a3cc24ea66f5ef9be2169f0a80a0d16c48f3932c5cf2d661e88a36779e"),
}


@pytest.mark.requires_kline
@pytest.mark.limit_rows(COST_ROWS["request"], COST_ROWS["schema"], COST_ROWS["analyzer"], COST_ROWS["turnover"])
def test_cost_bps_over_1000_reaches_consumers(monkeypatch: pytest.MonkeyPatch) -> None:
    """f1：cost_bps 逾舊界 1000 經 API 請求模型、IC 設定、產品編排器之 Net IC 階段與換手率成本拖累皆可算（保留有限且 >0）。"""
    from api.models.ic_models import NetICAnalysisRequest
    from momentum.Analysis.turnover_analyzer import TurnoverAnalyzer
    assert NetICAnalysisRequest(cost_bps=2000.0).cost_bps == 2000.0
    calls, _ = _stage_through_product(monkeypatch, "net_ic_analysis",
                                   {"net_ic_analysis": {"cost_enabled": True, "cost_bps": 2000.0}})
    assert _received("net_ic_analysis", "cost_bps", calls) == (2000.0, 2000.0)
    assert math.isclose(TurnoverAnalyzer({}).compute_cost_drag_proxy(0.5, 2000.0), 0.1, rel_tol=0, abs_tol=1e-15)


@pytest.mark.limit_rows(COST_ROWS["request"], COST_ROWS["schema"], COST_ROWS["analyzer"], COST_ROWS["turnover"])
@pytest.mark.parametrize("bad", [0.0, -1.0, INF, NAN])
def test_cost_bps_illegal_still_rejected(bad: float) -> None:
    """f1：cost_bps 之定義域（有限且 >0）仍拒。"""
    from api.models.ic_models import NetICAnalysisRequest
    from momentum.Analysis.net_ic_analyzer import NetICAnalyzer
    from momentum.Analysis.turnover_analyzer import TurnoverAnalyzer
    with pytest.raises(ValidationError):
        NetICAnalysisRequest(cost_bps=bad)
    with pytest.raises(ValidationError):
        load_ic_config(api_override={"net_ic_analysis": {"cost_enabled": True, "cost_bps": bad}})
    with pytest.raises(ValueError):
        NetICAnalyzer({"cost_enabled": True, "cost_bps": bad})
    with pytest.raises(ValueError):
        TurnoverAnalyzer({}).compute_cost_drag_proxy(0.5, bad)


@pytest.mark.limit_rows(COST_ROWS["ladder"])
def test_cost_ladder_not_clamped_and_old_range_unchanged() -> None:
    """f1：成本敏感度階梯 {c/2, c, 2c, 5c} 不再夾 1000，各檔成本拖累＝bps/10000×turnover；舊界內之 c（10、200）與修前相同。"""
    from momentum.Analysis.net_ic_analyzer import NetICAnalyzer
    a = NetICAnalyzer({"cost_enabled": True, "cost_bps": 2000.0})
    for c, expected in ((2000.0, [1000.0, 2000.0, 4000.0, 10000.0]), (10.0, [5.0, 10.0, 20.0, 50.0]),
                        (200.0, [100.0, 200.0, 400.0, 1000.0])):
        ladder = a.cost_sensitivity_analysis(c, 0.5)
        assert [s["cost_bps"] for s in ladder] == expected
        assert [s["cost_drag_return"] for s in ladder] == [b / 10000.0 * 0.5 for b in expected]


@pytest.mark.limit_rows(COST_ROWS["ladder"])
def test_cost_ladder_overflow_is_explicit_error_not_clamped() -> None:
    """審查 r163 CODEX-R163-P2-03：有限 cost_bps 倍乘後超出 float64（5c＝inf）⇒ 明示 ValueError，不輸出 inf、不夾回任何上界；
    倍乘仍可表示者（1e307 ⇒ 5e307）照算。"""
    from momentum.Analysis.net_ic_analyzer import NetICAnalyzer
    a = NetICAnalyzer({"cost_enabled": True, "cost_bps": 10.0})
    ladder = a.cost_sensitivity_analysis(1e307, 1.0)
    assert [s["cost_bps"] for s in ladder] == [5e306, 1e307, 2e307, 5e307]
    assert all(math.isfinite(s["cost_drag_return"]) for s in ladder)
    with pytest.raises(ValueError, match="overflows float64"):
        a.cost_sensitivity_analysis(1e308, 1.0)


def _net_ic_features(config: Dict[str, Any]) -> Dict[str, Any]:
    orch = _orchestrator(config)
    out = _run_stage(orch, "net_ic")
    feats = out.get("features") or {}
    assert set(feats) == set(FEATS), out.get("summary")
    return feats


@pytest.mark.requires_kline
@pytest.mark.limit_rows(COST_ROWS["schema"], COST_ROWS["analyzer"], COST_ROWS["ladder"])
def test_cost_bps_over_1000_net_ic_stage_computes_drag() -> None:
    """f1：cost_bps＝2000 經產品編排器 Net IC 階段實際算出：逐特徵成本拖累＝2000/10000×turnover，敏感度階梯未夾 1000
    （獨立 oracle＝公式逐項重算）。"""
    for name, feat in _net_ic_features({"net_ic_analysis": {"cost_enabled": True, "cost_bps": 2000.0}}).items():
        t = feat["turnover"]
        assert feat["cost_bps"] == 2000.0, name
        assert feat["cost_drag_return"] == 2000.0 / 10000.0 * t, name
        assert [s["cost_bps"] for s in feat["cost_sensitivity"]] == [1000.0, 2000.0, 4000.0, 10000.0], name
        assert [s["cost_drag_return"] for s in feat["cost_sensitivity"]] == [b / 10000.0 * t for b in (1000.0, 2000.0, 4000.0, 10000.0)], name


# cost_bps＝10（舊界內）之產品 Net IC 階段完整輸出；施工前於 HEAD 7b56d1c3 擷取。
COST10_DIGEST = "a1b47abb795d1c5ba1e3082e9baf668c255d0059880862a7c1d27a3a817b9cdd"


@pytest.mark.requires_kline
@pytest.mark.limit_rows(COST_ROWS["schema"], COST_ROWS["analyzer"], COST_ROWS["ladder"])
def test_cost_within_old_range_net_ic_unchanged() -> None:
    """f1：未觸發舊界之成本請求（cost_bps＝10）經產品 Net IC 階段之完整輸出與施工前相同；逐特徵拖累＝10/10000×turnover。"""
    orch = _orchestrator({"net_ic_analysis": {"cost_enabled": True, "cost_bps": 10.0}})
    out = _run_stage(orch, "net_ic")
    for name, feat in out["features"].items():
        assert feat["cost_drag_return"] == 10.0 / 10000.0 * feat["turnover"], name
    assert _digest(out) == COST10_DIGEST
