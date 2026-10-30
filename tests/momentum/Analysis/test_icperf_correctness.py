"""ICPERF Task 0.3 現行 IC 正確性獨立驗證（docs/ICPERF_SPEC.md §P Task 0.3、§B ICPERF-BUDGET-7；manifest
docs/manifests/ICPERF.json）。

本 Task 為**稽核**：以業界標準函式庫（scipy／statsmodels／numpy）與測試自寫之參考實作為獨立 oracle，對照現行碼；不一致
是要找的結果，記入收據、白話報使用者，裁定前不修產品碼。不一致項於本檔標 `xfail(strict=True)`，reason 引收據路徑。

- 收據測試（施工前為紅：收據尚未產出）：`handoffs/run_receipts/<日期>-icperf-correctness.json` 恰一份。形狀：
    {"head": <40 位提交雜湊>, "data": {"cell": "A_BTCUSDT_1h", "fact_receipt": <所用資料之 FACT-RECEIPT>, ...},
     "tolerance": {"relative": 1e-12},
     "coverage": {<涵蓋鍵>: {"oracle": <items 之 id>|"非統計欄", "producer": "<檔>:<行>"}},
     "items": {<oracle 項 id>: {"verdict": "一致"|"不一致"|"未驗", "oracle": <oracle 說明>, "max_rel_diff": <float>|None,
               "reason", "features", "affected"（不一致者必填：原因、差異大小與特徵、受影響之通過集合與下游判定）,
               "ruling": <使用者裁定紀錄>|None, "xfail_test": <本檔標 xfail(strict=True) 之測試名>（不一致者必填，且須在
               "tests" 內）, "blocked_reason"（未驗者必填；只准 cross_sectional：本機無可用多標的資料）,
               "tests": [<本檔實存之測試 nodeid 或函式名>, ...]（每項必填、非空；「一致」須至少一支綁定測試；SPEC 最少項之綁定須
               含 `ITEM_TESTS[<id>]` 至少一支——r30 CODEX-R30-P1-02：收據項須綁定本檔可執行之 oracle）}}}
  涵蓋鍵＝§G 第 (1)(4) 項小請求之回應欄位路徑（`_coverage_keys`：特徵名段→`*`、list 索引段→`#`、去 `#values` 等尾綴；
  逐特徵來源之每一欄名即其下之鍵），封閉集合——以實際回應鍵集合對照（slow＋requires_kline），不以 REQUIRED_ITEMS 為準。
- 秒級 oracle 定義測試（明列邊界輸入，SPEC §V「單元邊界案除外，需明列為邊界輸入」）：HAC SE 對 statsmodels、HAC
  fail-closed 邊界、ic_mean／ic_std／ICIR／勝率定義（只計有限值，含 NaN／±inf 邊界與跨標的分母）、報告端 rolling_ic_series
  抽樣、衰減擬合之有限值遮罩、最佳性與衍生欄、peak_horizon、點 IC 三方法分支；分組 IC（逐群組逐方法對 scipy）、多空 t 值
  （scipy.stats.ttest_ind nan_policy="omit"）、第 5 段逐根 PIT 參考實作（分位報酬、多空價差、單調性、換手率——頂分位依逐根
  箱數 k_t，SPEC Task 0.4 ①——、排名變化率、自相關、覆蓋率）、FDR（statsmodels
  multipletests fdr_bh）、第 6 段相關矩陣（無 NaN＝numpy.corrcoef、含 NaN＝逐對 scipy.stats.pearsonr）、多元化指標、
  邊際 IC（statsmodels OLS 投影、train_ic、組合因子、test 段不影響 train 段欄）、ic_mean 來源切換、前綴不變性、跨標的路徑；
  另以真實 kline（requires_kline，秒級）對照 HAC、衰減逐 horizon IC、分組 IC、第 5 段、相關矩陣、邊際 IC、前綴不變性與跨標的
  （本機 kline_cache.h5 含 10 標的）。各 SPEC 最少項之 oracle 測試見 `ITEM_TESTS`（收據項依此綁定）。
- 本檔之 pytest 列 `scripts/heavy_commands.json` 之 wrapped（`pytest_icperf_correctness`）：只有
  `-m "not slow and not requires_kline"` 之選取不列重型；標 slow／requires_kline 之測試須經共用監看（autouse 自證）。
"""

from __future__ import annotations

import importlib.util
import json
import math
import os
import pickle
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set

import numpy as np
import pandas as pd
import pytest
import statsmodels.api as sm
from scipy import optimize, stats
from statsmodels.stats.multitest import multipletests

from momentum.Analysis.coverage_analyzer import CoverageAnalyzer
from momentum.Analysis.factor_combiner import combine_factors
from momentum.Analysis.ic_engine import ICEngine
from momentum.Analysis.ic_reporter import ICReporter
from momentum.Analysis.marginal_ic import MarginalICParams, compute_marginal_ic
from momentum.Analysis.monotonicity_tester import MonotonicityTester
from momentum.Analysis.pit_stats import pit_expanding_qcut_label, pit_expanding_rank
from momentum.Analysis.redundancy_filter import RedundancyFilter
from momentum.Analysis.statistical_validator import _newey_west_bartlett_se, apply_fdr, compute_hac_ic_statistics
from momentum.Analysis.turnover_analyzer import TurnoverAnalyzer
from momentum.factories import create_ic_analyzer

REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / "scripts" / "icperf_freeze_baseline.py"
CORRECTNESS_PATTERN = "handoffs/run_receipts/*-icperf-correctness.json"
KLINE_CACHE = REPO / "data_cache" / "feature_klines" / "kline_cache.h5"
CELL = "A_BTCUSDT_1h"
#: SPEC Task 0.3「驗證」：浮點對照之相對誤差門檻
REL_TOL = 1e-12
#: SPEC Task 0.3 衰減擬合 ②：產品殘差平方和之容許倍數
SSR_SLACK = 1e-9
#: SPEC Task 0.3 衰減擬合 ②：oracle 之 curve_fit 設定（固定起點集合、maxfev；不含產品參數）
ORACLE_MAXFEV = 20000
DECAY_HORIZONS = [1, 2, 3, 5, 8, 13, 21]
#: SPEC Task 0.3 所列最少項（收據 items 須含；涵蓋以實際回應鍵為準，本清單不得作涵蓋之上限）
REQUIRED_ITEMS = {
    "ic_hit_rate", "ic_decay_fit", "long_short_tstat", "diversification_metrics", "marginal_ic", "marginal_ic.train_ic",
    "marginal_ic.composite", "cross_sectional", "point_ic.spearman", "point_ic.pearson", "point_ic.kendall",
    "rolling_ic_icir", "rolling_ic_series_sampling", "ic_decay_values", "grouped_ic", "hac", "fdr", "stage5_pit_stats",
    "redundancy_correlation", "ic_mean_source", "prefix_invariance",
}
#: SPEC 最少項 → 本檔之可執行 oracle 測試（函式名；收據項之 "tests" 須含其一，`test_required_items_bound_to_oracle_tests`
#: 斷言每項非空且逐一實存）
ITEM_TESTS: Dict[str, tuple] = {
    "ic_hit_rate": ("test_ic_hit_rate_definition_without_nan", "test_ic_hit_rate_ignores_nan_like_ic_mean",
                    "test_finite_hit_rate_oracle_boundaries", "test_cross_sectional_hit_rate_counts_finite_ic_only"),
    "ic_decay_fit": ("test_decay_fit_optimal_and_derived_consistent", "test_decay_fit_reaches_oracle_minimum_on_hump_curve",
                     "test_decay_fit_failed_triggers", "test_peak_horizon_rule"),
    "long_short_tstat": ("test_long_short_tstat_matches_scipy_ttest_ind", "test_stage5_pit_stats_match_reference_on_real_kline"),
    "diversification_metrics": ("test_diversification_metrics_match_reference",),
    "marginal_ic": ("test_marginal_ic_views_match_statsmodels_oracle", "test_marginal_ic_matches_oracle_on_real_kline"),
    "marginal_ic.train_ic": ("test_marginal_ic_train_ic_matches_scipy", "test_marginal_ic_matches_oracle_on_real_kline"),
    "marginal_ic.composite": ("test_marginal_ic_composite_matches_oracle",
                              "test_marginal_ic_train_fields_unaffected_by_test_segment",
                              "test_marginal_ic_matches_oracle_on_real_kline"),
    "cross_sectional": ("test_cross_sectional_matches_oracle", "test_cross_sectional_hit_rate_counts_finite_ic_only",
                        "test_cross_sectional_matches_oracle_on_real_kline"),
    "point_ic.spearman": ("test_point_ic_matches_scipy",),
    "point_ic.pearson": ("test_point_ic_matches_scipy",),
    "point_ic.kendall": ("test_point_ic_matches_scipy",),
    "rolling_ic_icir": ("test_icir_definitions_match_oracle", "test_ic_mean_source_fallback_matches_oracle"),
    "rolling_ic_series_sampling": ("test_rolling_series_sampling_matches_reference",
                                   "test_rolling_series_sampling_default_cap_and_non_dict"),
    "ic_decay_values": ("test_decay_ic_values_match_scipy_on_real_kline",),
    "grouped_ic": ("test_grouped_ic_matches_scipy", "test_grouped_ic_matches_scipy_on_real_kline"),
    "hac": ("test_hac_se_matches_statsmodels", "test_hac_statistics_match_oracle", "test_hac_fail_closed_boundaries",
            "test_hac_statistics_match_oracle_on_real_kline"),
    "fdr": ("test_fdr_matches_statsmodels_multipletests",),
    "stage5_pit_stats": ("test_stage5_pit_stats_match_reference", "test_stage5_quantile_turnover_matches_per_bar_pit_reference",
                         "test_per_bar_top_quantile_oracle_boundaries", "test_stage5_pit_stats_match_reference_on_real_kline",
                         "test_stage5_quantile_turnover_matches_per_bar_pit_reference_on_real_kline"),
    "redundancy_correlation": ("test_redundancy_correlation_matches_oracle",
                               "test_redundancy_correlation_matches_oracle_on_real_kline"),
    "ic_mean_source": ("test_ic_mean_source_fallback_matches_oracle",),
    "prefix_invariance": ("test_prefix_invariance_of_pit_series", "test_turnover_time_series_prefix_invariant_with_late_bins",
                          "test_prefix_invariance_on_real_kline"),
}
VERDICTS = {"一致", "不一致", "未驗"}
NON_STAT = "非統計欄"
#: SPEC Task 0.3：縱向請求恆為空 dict 之跨標的兩欄（coverage 記非統計欄）
CROSS_SYMBOL_KEYS = ("/cross_sectional_symbol_ic", "/cross_symbol_validation")
#: §G 第 (1)(4) 項（回應涵蓋之來源）與小請求欄數
COVERAGE_ITEMS = ("ic_report", "event_report")
COVERAGE_FEATURES = 20
HEAVY_MARKERS = ("slow", "requires_kline")
FINDING_RECEIPT = "handoffs/run_receipts/<日期>-icperf-correctness.json"


def _load(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _watchdog_missing(markers: Sequence[str], environ: Mapping[str, str]) -> bool:
    """標 slow 或 requires_kline 而未在共用監看下執行 ⇒ True（共用監看對子行程恆注入 `WATCHDOG_STACK_FILE`）。"""
    return any(m in HEAVY_MARKERS for m in markers) and not environ.get("WATCHDOG_STACK_FILE")


@pytest.fixture(autouse=True)
def _heavy_tests_require_shared_watchdog(request: pytest.FixtureRequest) -> None:
    """同 test_icperf_gate.py：本檔重型／真實資料測試於執行端自證經共用監看，未經即 FAIL。"""
    if _watchdog_missing([m.name for m in request.node.iter_markers()], os.environ):
        pytest.fail("本檔標 slow／requires_kline 之測試須經共用監看執行："
                    "venv/bin/python scripts/run_watched.py --log <路徑> -- <pytest 命令>（背景）")


def _single(pattern: str) -> Dict[str, Any]:
    paths = sorted(REPO.glob(pattern))
    assert len(paths) == 1, f"{pattern} 須恰一份，實得 {[str(p) for p in paths]}（Task 0.3 收據尚未產出）"
    return json.loads(paths[0].read_text(encoding="utf-8"))


def _rel(a: float, b: float) -> float:
    """相對誤差（兩者皆 NaN ⇒ 0；一方 NaN ⇒ inf；b 為 0 ⇒ 絕對誤差）。"""
    if math.isnan(a) and math.isnan(b):
        return 0.0
    if math.isnan(a) or math.isnan(b):
        return math.inf
    return abs(a - b) / abs(b) if b != 0 else abs(a - b)


# ── 收據（施工前為紅） ─────────────────────────────────────────────────────────────────────────────────


def test_correctness_receipt_items_and_verdicts() -> None:
    """收據恰一份；items ⊇ SPEC 最少項；逐項 verdict ∈ 一致／不一致／未驗；一致者相對誤差 ≤ 1e-12（或精確比對 None）；
    不一致者附原因、差異之特徵、受影響之通過集合與下游判定、裁定紀錄欄與本檔 xfail(strict=True) 之測試；未驗只准跨標的
    （本機無多標的資料，附原因）；逐項 tests 綁定本檔實存之測試（最少項須含 `ITEM_TESTS` 之一）。"""
    receipt = _single(CORRECTNESS_PATTERN)
    assert re.fullmatch(r"[0-9a-f]{40}", str(receipt.get("head") or "")), "收據須記執行時之提交 head"
    assert receipt["tolerance"]["relative"] == REL_TOL
    items = receipt["items"]
    assert REQUIRED_ITEMS <= set(items), f"收據缺 SPEC 最少項：{sorted(REQUIRED_ITEMS - set(items))}"
    module = sys.modules[__name__]
    for iid, it in items.items():
        assert it["verdict"] in VERDICTS, f"{iid}：verdict {it['verdict']!r} 非法"
        assert str(it.get("oracle") or "").strip(), f"{iid}：缺 oracle 說明"
        if it["verdict"] == "一致":
            d = it.get("max_rel_diff")
            assert d is None or (isinstance(d, (int, float)) and 0 <= d <= REL_TOL), f"{iid}：一致而相對誤差 {d} > 1e-12"
        elif it["verdict"] == "不一致":
            for k in ("reason", "features", "affected"):
                assert it.get(k), f"{iid}：不一致須附 {k}"
            assert "ruling" in it, f"{iid}：不一致須有裁定紀錄欄（裁定前 None）"
            fn = getattr(module, str(it.get("xfail_test") or ""), None)
            marks = [m for m in getattr(fn, "pytestmark", []) if m.name == "xfail"]
            assert fn is not None and any(m.kwargs.get("strict") is True for m in marks), \
                f"{iid}：不一致須對應本檔標 xfail(strict=True) 之測試（{it.get('xfail_test')!r}）"
        else:
            assert iid == "cross_sectional" and str(it.get("blocked_reason") or "").strip(), \
                f"{iid}：未驗只准跨標的項且須附原因（SPEC Task 0.3：本機無可用多標的資料 ⇒ 白話報使用者）"
    # r30 CODEX-R30-P1-02：逐項綁定本檔實存之 oracle 測試；「一致」至少一支；最少項須含 ITEM_TESTS 之一；不一致之
    # xfail_test 須在綁定內
    for iid, it in items.items():
        bound = it.get("tests")
        assert isinstance(bound, list) and bound, f"{iid}：收據項須帶非空之 tests（本檔測試 nodeid 或函式名）"
        names = [_bound_test_name(t) for t in bound]
        for raw, name in zip(bound, names):
            fn = getattr(module, name or "", None)
            assert name and name.startswith("test_") and callable(fn), f"{iid}：綁定測試 {raw!r} 不存在於本檔"
        if it["verdict"] == "一致":
            assert len(names) >= 1, f"{iid}：一致須至少一支綁定測試"
        if iid in ITEM_TESTS:
            assert set(names) & set(ITEM_TESTS[iid]), f"{iid}：綁定須含本項 oracle 測試之一 {ITEM_TESTS[iid]}"
        if it["verdict"] == "不一致":
            assert str(it.get("xfail_test")) in names, f"{iid}：xfail_test {it.get('xfail_test')!r} 須在 tests 內"


def _bound_test_name(nodeid: Any) -> str:
    """收據 tests 元素 → 本檔測試函式名：可為函式名或 nodeid（`<本檔 repo 相對路徑>::<函式名>[<參數>]`）；路徑非本檔 ⇒ 空字串。"""
    s = str(nodeid or "")
    if "::" in s:
        path, s = s.split("::", 1)
        if path and path != Path(__file__).resolve().relative_to(REPO).as_posix():
            return ""
    return s.split("[", 1)[0]


def test_required_items_bound_to_oracle_tests() -> None:
    """`ITEM_TESTS` 涵蓋 SPEC 最少項全部（r30 CODEX-R30-P1-02／COMPOSER-R30-P1-02），每項非空且所列測試逐一實存於本檔。"""
    module = sys.modules[__name__]
    assert set(ITEM_TESTS) == REQUIRED_ITEMS, f"缺：{sorted(REQUIRED_ITEMS - set(ITEM_TESTS))}；多：{sorted(set(ITEM_TESTS) - REQUIRED_ITEMS)}"
    for iid, names in ITEM_TESTS.items():
        assert names, f"{iid}：無 oracle 測試"
        for name in names:
            assert name.startswith("test_") and callable(getattr(module, name, None)), f"{iid}：{name} 不存在於本檔"
    assert _bound_test_name("tests/momentum/Analysis/test_icperf_correctness.py::test_point_ic_matches_scipy[a-b]") == \
        "test_point_ic_matches_scipy"
    assert _bound_test_name("tests/other.py::test_point_ic_matches_scipy") == ""


def test_correctness_receipt_coverage_entries() -> None:
    """coverage 每一鍵對應 items 之 id 或「非統計欄」並附實存之產生檔:行；跨標的兩欄於縱向請求記為非統計欄（SPEC Task 0.3）。"""
    receipt = _single(CORRECTNESS_PATTERN)
    items = receipt["items"]
    coverage = receipt["coverage"]
    assert coverage, "coverage 為空"
    for key, rec in coverage.items():
        assert rec["oracle"] == NON_STAT or rec["oracle"] in items, f"{key}：oracle {rec['oracle']!r} 不在 items"
        m = re.match(r"^([\w./-]+\.py):(\d+)", str(rec.get("producer") or ""))
        assert m and (REPO / m.group(1)).is_file(), f"{key}：producer 須為實存之 檔:行，實得 {rec.get('producer')!r}"
        if key.startswith(CROSS_SYMBOL_KEYS):
            assert rec["oracle"] == NON_STAT, f"{key}：縱向請求之跨標的欄恆為空 dict，coverage 須記非統計欄"


def _ptr(seg: Any) -> str:
    return str(seg).replace("~", "~0").replace("/", "~1")


def _as_container(obj: Any) -> Any:
    import dataclasses

    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return dataclasses.asdict(obj)
    if hasattr(obj, "model_dump") and not isinstance(obj, (pd.DataFrame, pd.Series)):
        return obj.model_dump()
    return obj


def _paths(obj: Any, path: str = "") -> Set[str]:
    """回應物件之欄位路徑（同 `flatten_fields` 之規則；測試自寫）。"""
    obj = _as_container(obj)
    if isinstance(obj, pd.DataFrame):
        return {f"{path}#index"} | {f"{path}/{_ptr(c)}#values" for c in obj.columns}
    if isinstance(obj, (pd.Series, np.ndarray)):
        return {f"{path}#values"}
    if isinstance(obj, dict) and obj:
        return set().union(*(_paths(v, f"{path}/{_ptr(k)}") for k, v in obj.items()))
    if isinstance(obj, (list, tuple)) and obj and all(v is None or isinstance(v, (bool, int, float, str, np.generic))
                                                     for v in obj):
        return {f"{path}#values"}
    if isinstance(obj, (list, tuple)) and obj:
        return set().union(*(_paths(v, f"{path}/{i}") for i, v in enumerate(obj)))
    return {path}


def _coverage_keys(raw: Mapping[str, Any]) -> Set[str]:
    """涵蓋鍵：回應欄位路徑去 `#values`／`#index` 尾綴，特徵名段→`*`、list 索引段→`#`（特徵名取 summary_table 之
    feature_name）。"""
    feats = {_ptr(r.get("feature_name")) for r in raw.get("summary_table") or [] if isinstance(r, dict)}
    out = set()
    for p in _paths(raw):
        segs = re.sub(r"#(values|index)$", "", p).split("/")[1:]
        out.add("/" + "/".join("*" if s in feats else "#" if s.isdigit() else s for s in segs))
    return out


@pytest.mark.slow
@pytest.mark.requires_kline
def test_correctness_coverage_closed_over_response_keys(tmp_path: Path) -> None:
    """SPEC Task 0.3 涵蓋＝封閉可導出集合：§G 第 (1)(4) 項之 A 格小請求實際回應之涵蓋鍵集合 == 收據 coverage 鍵集合
    （任一欄位未對應 ⇒ FAIL；多記不存在之鍵亦 FAIL）。請求經凍結腳本之同一路徑（`default_request`／`small_request`／
    `freeze_item`，回應 pickle 原樣）。"""
    receipt = _single(CORRECTNESS_PATTERN)
    fb = _load("icperf_freeze_baseline", SCRIPT)
    keys: Set[str] = set()
    for item in COVERAGE_ITEMS:
        request = fb.small_request(item, fb.default_request(item, CELL), COVERAGE_FEATURES)
        fb.freeze_item(item, request=request, repo_root=REPO, work_root=tmp_path / item)
        with open(tmp_path / item / item / "response.pkl", "rb") as fh:
            keys |= _coverage_keys(pickle.load(fh))
    assert keys, "小請求回應無任何欄位"
    covered = set(receipt["coverage"])
    assert keys == covered, f"coverage 未對應之回應欄位 {sorted(keys - covered)[:10]}；多記 {sorted(covered - keys)[:10]}"


# ── 秒級 oracle 定義測試：HAC ─────────────────────────────────────────────────────────────────────────

#: 明列邊界輸入：逐根 Spearman 貢獻序列 z（含正負、非對稱、自相關）
HAC_Z = np.array([0.31, -1.22, 0.84, 2.07, -0.43, 0.0, 1.51, -0.92, 0.66, -2.18, 1.13, 0.24, 0.95, -0.37, 1.48, 0.12,
                  -0.81, 0.58, 1.9, -1.05], dtype=float)


def _sm_hac_se(z: np.ndarray, maxlags: int) -> float:
    """statsmodels oracle（SPEC Task 0.3 HAC 定死參數）：OLS(z, 1) 之 HAC Bartlett、無小樣本修正之 bse。"""
    res = sm.OLS(z, np.ones((z.size, 1))).fit(
        cov_type="HAC", cov_kwds={"maxlags": int(maxlags), "kernel": "bartlett", "use_correction": False})
    return float(res.bse[0])


@pytest.mark.parametrize("maxlags", [0, 1, 2, 3, 5, 8])
def test_hac_se_matches_statsmodels(maxlags: int) -> None:
    """現行 `_newey_west_bartlett_se`（statistical_validator.py:35-56）== statsmodels OLS HAC Bartlett（use_correction=False）
    之 bse，相對誤差 ≤ 1e-12。"""
    got = _newey_west_bartlett_se(HAC_Z, maxlags)
    assert _rel(got, _sm_hac_se(HAC_Z, maxlags)) <= REL_TOL


def _ref_spearman_z(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """測試自寫之逐根 Spearman 貢獻參考實作：u＝zscore(rank(x))、v＝zscore(rank(y))（平均秩、ddof=1）、z＝u·v。"""
    rx, ry = stats.rankdata(x, method="average"), stats.rankdata(y, method="average")
    return ((rx - rx.mean()) / rx.std(ddof=1)) * ((ry - ry.mean()) / ry.std(ddof=1))


def _hac_oracle(x: np.ndarray, y: np.ndarray, horizon: int, maxlags: Any = None) -> Dict[str, Any]:
    """HAC t／p 之 oracle（SPEC Task 0.3 鎖定之定義）：自動 L＝max(int(4·(n/100)^(2/9)), horizon−1)；SE＝statsmodels；
    t＝mean(z)／SE；p＝2·t.sf(|t|, n−1)。"""
    n = x.size
    lag = int(maxlags) if maxlags is not None else max(int(4 * (n / 100.0) ** (2.0 / 9.0)), horizon - 1)
    z = _ref_spearman_z(x, y)
    se = _sm_hac_se(z, lag)
    t = float(np.mean(z)) / se
    return {"t_stat": t, "p_value": float(2.0 * stats.t.sf(abs(t), df=n - 1)), "se": se, "n_obs": n, "maxlags": lag}


def _hac_inputs(n: int) -> pd.DataFrame:
    """明列邊界輸入：確定性算式之特徵與標籤（含同值、非單調）。"""
    i = np.arange(n, dtype=float)
    return pd.DataFrame({"f": ((7 * i) % 23) - 11.0, "label": ((5 * i + 3) % 19) - 9.0 + 0.05 * i})


@pytest.mark.parametrize("n,horizon", [(40, 1), (40, 5), (64, 3)])
def test_hac_statistics_match_oracle(n: int, horizon: int) -> None:
    """`compute_hac_ic_statistics`（statistical_validator.py:74）之 t／p／se／n_obs／maxlags == oracle（se、t、p 相對誤差
    ≤ 1e-12；整數欄完全相同）。"""
    df = _hac_inputs(n)
    got = compute_hac_ic_statistics(df[["f"]], df["label"], horizon)["f"]
    exp = _hac_oracle(df["f"].to_numpy(), df["label"].to_numpy(), horizon)
    assert got["n_obs"] == exp["n_obs"] and got["maxlags"] == exp["maxlags"]
    for k in ("se", "t_stat", "p_value"):
        assert _rel(got[k], exp[k]) <= REL_TOL, f"{k}：{got[k]} vs oracle {exp[k]}"


def test_hac_fail_closed_boundaries() -> None:
    """SPEC Task 0.3 HAC 邊界（明列輸入）：L＝n_valid−1、n_valid＝max(8, 2L)−1、常數 z 致 SE＝0 ⇒ 現行回 NaN 統計量且
    n_obs、maxlags 照記。"""
    df = _hac_inputs(12)
    r = compute_hac_ic_statistics(df[["f"]], df["label"], 1, maxlags=11)["f"]  # L＝n_valid−1
    assert all(math.isnan(r[k]) for k in ("t_stat", "p_value", "se")) and r["n_obs"] == 12 and r["maxlags"] == 11
    df9 = _hac_inputs(9)
    r = compute_hac_ic_statistics(df9[["f"]], df9["label"], 1, maxlags=5)["f"]  # n_valid＝max(8, 10)−1＝9
    assert all(math.isnan(r[k]) for k in ("t_stat", "p_value", "se")) and r["n_obs"] == 9 and r["maxlags"] == 5
    two = pd.DataFrame({"f": [0.0, 0, 0, 0, 1, 1, 1, 1], "label": [0.0, 0, 0, 0, 1, 1, 1, 1]})  # z 恆＝常數
    z = _ref_spearman_z(two["f"].to_numpy(), two["label"].to_numpy())
    assert np.ptp(z) == 0.0 and _newey_west_bartlett_se(z, 2) == 0.0, "邊界輸入未得常數 z（前提失效）"
    r = compute_hac_ic_statistics(two[["f"]], two["label"], 1)["f"]
    assert all(math.isnan(r[k]) for k in ("t_stat", "p_value", "se")) and r["n_obs"] == 8 and r["maxlags"] == 2


# ── 秒級 oracle 定義測試：滾動 IC 之 ic_mean／ic_std／ICIR／勝率 ─────────────────────────────────────────


def _icir_oracle(values: Sequence[float]) -> Dict[str, float]:
    """SPEC Task 0.3 現行定義（ic_engine.py:470-491）：空 ⇒ 全 NaN；ic_mean＝nanmean、ic_std＝nanstd（ddof=0）、
    ICIR＝ic_mean／ic_std（ic_std ≤ 0 ⇒ NaN）。"""
    v = np.asarray(values, dtype=float)
    finite = v[~np.isnan(v)]
    if v.size == 0 or finite.size == 0:
        return {"ic_mean": math.nan, "ic_std": math.nan, "icir": math.nan}
    mean, std = float(finite.mean()), float(np.sqrt(np.mean((finite - finite.mean()) ** 2)))
    return {"ic_mean": mean, "ic_std": std, "icir": mean / std if std > 0 else math.nan}


ICIR_CASES = {
    "mixed": [0.04, -0.01, 0.03, 0.02, -0.02, 0.05, 0.01],
    "with_nan": [0.04, math.nan, 0.03, -0.02, math.nan, 0.05],
    "constant": [0.02, 0.02, 0.02, 0.02],
    "all_nan": [math.nan, math.nan, math.nan],
    "empty": [],
}


@pytest.mark.parametrize("case", sorted(ICIR_CASES))
@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_icir_definitions_match_oracle(case: str) -> None:
    """`ICEngine.compute_icir` 之 ic_mean／ic_std／ICIR == 現行定義之獨立重算（含空序列、全 NaN、常數序列之邊界）。"""
    got = ICEngine({}).compute_icir({"f": {"window_63": list(ICIR_CASES[case])}})["f"]
    exp = _icir_oracle(ICIR_CASES[case])
    for k in ("ic_mean", "ic_std", "icir"):
        assert _rel(got[k], exp[k]) <= REL_TOL, f"{case}/{k}：{got[k]} vs oracle {exp[k]}"


def _finite_hit_rate(values: Sequence[float]) -> float:
    """勝率 oracle（SPEC Task 0.4 ②）：只計有限值（`np.isfinite` 遮罩，NaN 與 ±inf 皆不入分母）之 > 0 比例；空序列或
    無有限值 ⇒ NaN。"""
    v = np.asarray(values, dtype=float)
    finite = v[np.isfinite(v)]
    return float(np.mean(finite > 0)) if finite.size else math.nan


#: 勝率之非有限邊界輸入（明列）：NaN、±inf 混合、全非有限、只含 ±inf（皆含非有限值；現行與 oracle 不一致之案）
HIT_RATE_NON_FINITE_CASES = {
    "with_nan": ICIR_CASES["with_nan"],
    "all_nan": ICIR_CASES["all_nan"],
    "mixed_nan_inf": [0.04, math.nan, math.inf, -0.02, -math.inf, 0.03, math.nan],
    "all_non_finite": [math.nan, math.inf, -math.inf],
    "inf_only": [math.inf, -math.inf, math.inf],
}


def test_finite_hit_rate_oracle_boundaries() -> None:
    """勝率 oracle 本身（明列期望值，不經產品碼）：NaN／±inf 不入分母；空序列、全 NaN、全非有限、只含 ±inf ⇒ NaN。"""
    exp = {"with_nan": 0.75, "all_nan": math.nan, "mixed_nan_inf": 2.0 / 3.0, "all_non_finite": math.nan,
           "inf_only": math.nan}
    for case, values in HIT_RATE_NON_FINITE_CASES.items():
        assert _rel(_finite_hit_rate(values), exp[case]) == 0.0, f"{case}：oracle {_finite_hit_rate(values)} vs {exp[case]}"
    assert math.isnan(_finite_hit_rate([])), "空序列須為 NaN"
    assert _finite_hit_rate(ICIR_CASES["mixed"]) == float(np.mean(np.asarray(ICIR_CASES["mixed"]) > 0))


@pytest.mark.parametrize("case", ["mixed", "constant", "empty"])
def test_ic_hit_rate_definition_without_nan(case: str) -> None:
    """勝率（ic_engine.py:484-490）：無非有限值之序列 ⇒ 只計有限值之 oracle（＝序列 > 0 之比例）；空序列 ⇒ NaN。現行與
    oracle 於此類輸入一致，故照常斷言。"""
    values = ICIR_CASES[case]
    got = ICEngine({}).compute_icir({"f": {"window_63": list(values)}})["f"]["ic_hit_rate"]
    assert _rel(got, _finite_hit_rate(values)) == 0.0


# Task 0.3 稽核發現、SPEC Task 0.4 ② 已修：修正前勝率 np.mean(values > 0)（ic_engine.py:484）以含非有限值之序列長度為分母
# （NaN、-inf 計為未勝，+inf 計為勝）、無有限值之序列得 0.0 等而非 NaN；修正後只計有限值、無有限值 ⇒ NaN。
@pytest.mark.parametrize("case", sorted(HIT_RATE_NON_FINITE_CASES))
@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_ic_hit_rate_ignores_nan_like_ic_mean(case: str) -> None:
    """勝率之業界口徑（與 ic_mean＝nanmean 一致）：只計有限之滾動 IC 觀測（NaN、±inf 皆不入分母）；無有限值 ⇒ NaN。"""
    values = list(HIT_RATE_NON_FINITE_CASES[case])
    got = ICEngine({}).compute_icir({"f": {"window_63": values}})["f"]["ic_hit_rate"]
    exp = _finite_hit_rate(values)
    assert _rel(got, exp) == 0.0, f"{case}：現行 {got} vs 只計有限觀測之 {exp}"


# ── 秒級 oracle 定義測試：報告端 rolling_ic_series 抽樣 ────────────────────────────────────────────────


def _ref_sample(series: Any, max_points: int) -> Any:
    """測試自寫之抽樣參考實作（SPEC Task 0.3：ic_reporter.py:980-1002 之規則）：上限 ≤ 0、非 dict、窗非 list 或長度
    ≤ 上限 ⇒ 原樣；否則步長＝max(1, ceil(長度／上限))、取 values[::步長]。"""
    if not isinstance(series, dict) or max_points <= 0:
        return series
    out: Dict[Any, Any] = {}
    for feat, windows in series.items():
        if not isinstance(windows, dict):
            out[feat] = windows
            continue
        out[feat] = {}
        for key, values in windows.items():
            if not isinstance(values, list) or len(values) <= max_points:
                out[feat][key] = values
            else:
                step = max(1, -(-len(values) // max_points))
                out[feat][key] = [values[i] for i in range(0, len(values), step)]
    return out


@pytest.mark.parametrize("max_points,length", [(10, 10), (10, 11), (10, 25), (7, 100), (0, 30), (-1, 30), (1, 5)])
def test_rolling_series_sampling_matches_reference(max_points: int, length: int) -> None:
    """`ICReporter._sample_rolling_series` == 參考實作（上限邊界：長度＝上限、上限＋1、上限 ≤ 0；首點保留、順序不變）。"""
    vals = [round(0.001 * i - 0.01, 6) for i in range(length)]
    series = {"f": {"window_21": list(vals), "window_63": "not-a-list"}, "g": [1, 2], "h": {"window_21": [math.nan]}}
    got = ICReporter({"max_series_points": max_points})._sample_rolling_series(series)
    exp = _ref_sample(series, max_points)
    assert json.dumps(got, allow_nan=True, sort_keys=True) == json.dumps(exp, allow_nan=True, sort_keys=True)
    if length and max_points > 0:
        assert got["f"]["window_21"][0] == vals[0], "抽樣須保留首點"


def test_rolling_series_sampling_default_cap_and_non_dict() -> None:
    """未設 max_series_points ⇒ 上限 1000（設定預設）；非 dict 輸入原樣回傳。"""
    vals = list(range(2500))
    got = ICReporter({})._sample_rolling_series({"f": {"window_21": vals}})
    assert got["f"]["window_21"] == _ref_sample({"f": {"window_21": vals}}, 1000)["f"]["window_21"]
    assert ICReporter({})._sample_rolling_series(["x"]) == ["x"]


# ── 秒級 oracle 定義測試：衰減擬合與 peak_horizon ────────────────────────────────────────────────────────


def _model(h: np.ndarray, a: float, lam: float, c: float) -> np.ndarray:
    return a * np.exp(-lam * h) + c


def _oracle_min_ssr(horizons: Sequence[float], ic_values: Sequence[float]) -> float:
    """SPEC Task 0.3 衰減擬合 ② oracle：先套有限值遮罩，自固定起點集合 {None, [y0,1,0], [y0,0.1,0], [y0−y_last,0.5,y_last]}
    以 curve_fit(maxfev=20000、無 bounds) 各擬一次取最小殘差平方和；全部失敗 ⇒ inf（不含產品參數）。"""
    x, y = np.asarray(horizons, dtype=float), np.asarray(ic_values, dtype=float)
    mask = np.isfinite(x) & np.isfinite(y)
    x, y = x[mask], y[mask]
    best = math.inf
    for p0 in (None, [y[0], 1.0, 0.0], [y[0], 0.1, 0.0], [y[0] - y[-1], 0.5, y[-1]]):
        try:
            params, _ = optimize.curve_fit(_model, x, y, p0=p0, maxfev=ORACLE_MAXFEV)
        except (RuntimeError, ValueError, optimize.OptimizeWarning):
            continue
        ssr = float(np.sum((y - _model(x, *params)) ** 2))
        if math.isfinite(ssr):
            best = min(best, ssr)
    return best


def _product_ssr(ic_values: Sequence[float], fit: Mapping[str, Any]) -> float:
    """產品參數代入模型之殘差平方和：由產品之 r2 還原（r2＝1−SS_res／SS_tot，ic_engine.py:1170-1173；同遮罩）。"""
    y = np.asarray(ic_values, dtype=float)
    y = y[np.isfinite(y)]
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    return (1.0 - float(fit["r2"])) * ss_tot


def _assert_derived_consistent(fit: Mapping[str, Any]) -> None:
    """衰減衍生欄 ③（SPEC Task 0.3）：half_life＝ln2／λ（λ>0，否則 NaN）、decay_type 依 r2 ≥ 0.5、fit_warning 與
    fit_warning_reason 依 decay_type。"""
    lam = float(fit["decay_rate"])
    if lam > 0:
        assert _rel(float(fit["half_life"]), math.log(2) / lam) <= REL_TOL
    else:
        assert math.isnan(float(fit["half_life"]))
    assert fit["decay_type"] == ("exponential" if fit["r2"] >= 0.5 else "non_exponential")
    assert fit["fit_warning"] == (fit["decay_type"] != "exponential")
    assert fit["fit_warning_reason"] == ("low_r2" if fit["fit_warning"] else None)


#: 明列邊界輸入：典型衰減、峰後衰減、負號衰減、NaN 穿插之 IC 曲線（逐 horizon）
DECAY_CASES = {
    "smooth": [0.081, 0.062, 0.049, 0.031, 0.019, 0.012, 0.010],
    "negative": [-0.020, -0.018, -0.015, -0.011, -0.007, -0.004, -0.003],
    "with_nan": [0.050, math.nan, 0.035, 0.020, math.nan, 0.008, 0.006],
}
#: Task 0.4 ③ 前之產品只自 scipy 預設起點擬一次，於此曲線落於較差之局部解（SPEC Task 0.3 發現、Task 0.4 ③ 修正）
DECAY_LOCAL_MINIMUM_CASES = {
    "hump": [0.012, 0.031, 0.028, 0.015, -0.004, 0.006, 0.002],
}


@pytest.mark.parametrize("case", sorted(DECAY_CASES))
def test_decay_fit_optimal_and_derived_consistent(case: str) -> None:
    """衰減擬合 ②③：產品殘差平方和 ≤ oracle 最小 × (1＋1e-9)、雙向判定（產品 fit_failed 而 oracle 成功亦不一致）；
    衍生欄與產品參數一致。"""
    y = DECAY_CASES[case]
    fit = ICEngine._fit_exponential_decay(DECAY_HORIZONS, y)
    best = _oracle_min_ssr(DECAY_HORIZONS, y)
    assert fit["decay_type"] != "fit_failed" or not math.isfinite(best), f"{case}：產品 fit_failed 而 oracle 擬合成功"
    assert math.isfinite(best) or fit["decay_type"] == "fit_failed", f"{case}：產品成功而 oracle 全部起點失敗"
    assert _product_ssr(y, fit) <= best * (1 + SSR_SLACK), f"{case}：產品殘差 {_product_ssr(y, fit)} > oracle 最小 {best}"
    _assert_derived_consistent(fit)


# Task 0.3 稽核發現、SPEC Task 0.4 ③ 已修：修正前衰減擬合只自 scipy 預設起點擬一次（ic_engine.py:1168），峰後衰減曲線
# 落於較差之局部解或擬合失敗；修正後自固定起點集合逐一擬合、取殘差平方和最小者。
@pytest.mark.parametrize("case", sorted(DECAY_LOCAL_MINIMUM_CASES))
def test_decay_fit_reaches_oracle_minimum_on_hump_curve(case: str) -> None:
    """同 ②（雙向判定）：峰後衰減之 IC 曲線。"""
    y = DECAY_LOCAL_MINIMUM_CASES[case]
    fit = ICEngine._fit_exponential_decay(DECAY_HORIZONS, y)
    best = _oracle_min_ssr(DECAY_HORIZONS, y)
    assert fit["decay_type"] != "fit_failed" or not math.isfinite(best), f"{case}：產品 fit_failed 而 oracle 擬合成功"
    assert _product_ssr(y, fit) <= best * (1 + SSR_SLACK), f"{case}：產品殘差 {_product_ssr(y, fit)} > oracle 最小 {best}"


@pytest.mark.parametrize("ic_values,reason", [
    ([0.1, math.nan, math.nan, math.inf, math.nan, 0.05, math.nan], "insufficient_points"),  # 有限點 2 < 3
    ([math.nan] * 7, "insufficient_points"),
    ([0.05] * 7, "low_variance"),
    ([0.05, 0.05, 0.05 + 1e-10, 0.05, 0.05, 0.05, 0.05], "low_variance"),
])
def test_decay_fit_failed_triggers(ic_values: List[float], reason: str) -> None:
    """fit_failed 與 fit_warning_reason 之觸發（明列邊界）：有限點 < 3（先套有限值遮罩，±inf 非有限）⇒ insufficient_points；
    低變異（nanstd < 1e-8）⇒ low_variance；皆 decay_rate／half_life／r2 為 NaN、fit_warning 為 True。"""
    fit = ICEngine._fit_exponential_decay(DECAY_HORIZONS, ic_values)
    assert fit["decay_type"] == "fit_failed" and fit["fit_warning"] is True and fit["fit_warning_reason"] == reason
    assert all(math.isnan(fit[k]) for k in ("decay_rate", "half_life", "r2"))


def _ref_peak(horizons: Sequence[int], values: Sequence[float]) -> int:
    """peak_horizon 參考實作（SPEC Task 0.3）：|IC| 最大之 horizon，忽略 NaN、同值取首個；全非有限 ⇒ 首個 horizon。"""
    v = [abs(float(x)) for x in values]
    if not any(math.isfinite(x) for x in v):
        return horizons[0]
    best_i, best = 0, -math.inf
    for i, x in enumerate(v):
        if not math.isnan(x) and x > best:
            best_i, best = i, x
    return horizons[best_i]


@pytest.mark.parametrize("values", [
    [0.01, -0.05, 0.03, 0.05, 0.0, 0.01, 0.02],  # |−0.05| 與 0.05 同值 ⇒ 取首個
    [math.nan, 0.02, -0.04, math.nan, 0.01, 0.0, 0.0],
    [math.nan] * 7,
    [math.nan, -math.inf, 0.1, 0.0, 0.0, 0.0, 0.0],
])
def test_peak_horizon_rule(values: List[float]) -> None:
    """`ICEngine._select_peak_horizon` == 參考實作。"""
    assert ICEngine({})._select_peak_horizon(DECAY_HORIZONS, values) == _ref_peak(DECAY_HORIZONS, values)


# ── 秒級 oracle 定義測試：點 IC 三方法分支 ──────────────────────────────────────────────────────────────


def _point_inputs(with_nan: bool) -> pd.DataFrame:
    """明列邊界輸入：兩特徵（向量化路徑需多欄）、同值、可含 NaN（走逐對路徑）。"""
    i = np.arange(30, dtype=float)
    df = pd.DataFrame({"a": ((3 * i) % 11) - 5.0, "b": np.sin(i / 3.0) + 0.01 * i, "label": ((7 * i) % 13) - 6.0 + 0.1 * i})
    if with_nan:
        df.loc[[2, 9, 17], "a"] = np.nan
        df.loc[[5, 22], "label"] = np.nan
    return df


_SCIPY = {"spearman": stats.spearmanr, "pearson": stats.pearsonr, "kendall": stats.kendalltau}


@pytest.mark.parametrize("method", sorted(_SCIPY))
@pytest.mark.parametrize("with_nan", [False, True])
def test_point_ic_matches_scipy(method: str, with_nan: bool) -> None:
    """`ICEngine.compute_ic`（向量化與逐對兩路徑）== scipy 對應函式於兩欄共同有效列之相關（相對誤差 ≤ 1e-12）。"""
    df = _point_inputs(with_nan)
    got = ICEngine({}).compute_ic(df[["a", "b"]], df["label"], method)
    for feat in ("a", "b"):
        pair = df[[feat, "label"]].dropna()
        exp = float(_SCIPY[method](pair[feat], pair["label"])[0])
        assert _rel(float(got[feat]), exp) <= REL_TOL, f"{method}/{feat}：{got[feat]} vs scipy {exp}"


# ── 真實 kline（requires_kline，秒級）─────────────────────────────────────────────────────────────────


def _real_close(rows: int = 600, symbol: str = "BTCUSDT") -> pd.Series:
    import h5py

    assert KLINE_CACHE.is_file(), f"真實 kline 不存在：{KLINE_CACHE}"
    with h5py.File(KLINE_CACHE, "r") as f:
        data = f[f"{symbol}/1h/data"][-rows:]
    idx = pd.to_datetime(data["timestamp"].astype("int64"), unit="s", utc=True)
    return pd.Series(data["close"].astype("float64"), index=idx, name="close")


def _real_features(close: pd.Series) -> pd.DataFrame:
    """真實 kline 上之因果特徵（只用 0..t）：過去 1 根報酬、對 20 根均線之偏離。"""
    return pd.DataFrame({"ret1": close.pct_change(), "dev20": close / close.rolling(20).mean() - 1.0})


@pytest.mark.requires_kline
@pytest.mark.parametrize("horizon", [1, 5])
def test_hac_statistics_match_oracle_on_real_kline(horizon: int) -> None:
    """真實 BTCUSDT 1h：HAC t／p／se == oracle（同上之定義；對齊與 NaN 處理照現行之 inner join＋dropna）。"""
    close = _real_close()
    feats = _real_features(close)
    label = (close.shift(-horizon) / close - 1.0).rename("label")
    got = compute_hac_ic_statistics(feats, label, horizon)
    for feat in feats.columns:
        pair = pd.concat([feats[feat], label], axis=1, join="inner").dropna()
        exp = _hac_oracle(pair[feat].to_numpy(), pair["label"].to_numpy(), horizon)
        assert got[feat]["n_obs"] == exp["n_obs"] and got[feat]["maxlags"] == exp["maxlags"]
        for k in ("se", "t_stat", "p_value"):
            assert _rel(got[feat][k], exp[k]) <= REL_TOL, f"{feat}/{k}：{got[feat][k]} vs oracle {exp[k]}"


@pytest.mark.requires_kline
@pytest.mark.parametrize("method", sorted(_SCIPY))
def test_decay_ic_values_match_scipy_on_real_kline(method: str) -> None:
    """真實 BTCUSDT 1h：`compute_ic_decay` 之逐 horizon `ic_values` == scipy 對應函式（標籤＝簡單報酬
    close[t+h]／close[t]−1，label_generator.py:45-47；兩欄共同有效列）；peak_horizon 與衍生欄與產品參數一致。真實資料上
    擬合之最佳性（②）屬 Task 0.3 收據之稽核項（現行碼於此之結果未知，不於本秒級測試預設一致或不一致）。"""
    close = _real_close()
    feats = _real_features(close)
    out = ICEngine({}).compute_ic_decay(feats, close, DECAY_HORIZONS, method=method)
    for feat in feats.columns:
        exp_vals = []
        for h in DECAY_HORIZONS:
            pair = pd.concat([feats[feat], (close.shift(-h) / close - 1.0).rename("label")], axis=1).dropna()
            exp_vals.append(float(_SCIPY[method](pair[feat], pair["label"])[0]))
        got = out[feat]
        assert all(_rel(float(g), e) <= REL_TOL for g, e in zip(got["ic_values"], exp_vals)), \
            f"{method}/{feat}：ic_values {got['ic_values']} vs scipy {exp_vals}"
        assert got["peak_horizon"] == _ref_peak(DECAY_HORIZONS, got["ic_values"])
        if got["decay_type"] != "fit_failed":
            _assert_derived_consistent({**got, "r2": got["fit_r2"]})


# ── 共用：巢狀結果比對與點 IC oracle ───────────────────────────────────────────────────────────────────


def _assert_close_tree(got: Any, exp: Any, path: str = "") -> None:
    """巢狀 dict／list 逐葉比對：鍵集合相同、float 相對誤差 ≤ 1e-12（NaN＝NaN）、None 與其餘型別 `==`（None 不得視為 0）。"""
    if isinstance(exp, Mapping):
        assert isinstance(got, Mapping), f"{path}：產品 {type(got).__name__} 非 dict"
        assert set(map(str, got)) == set(map(str, exp)), \
            f"{path}：鍵 {sorted(map(str, got))} vs oracle {sorted(map(str, exp))}"
        gm = {str(k): v for k, v in got.items()}
        for k, v in exp.items():
            _assert_close_tree(gm[str(k)], v, f"{path}/{k}")
    elif isinstance(exp, (list, tuple)):
        assert isinstance(got, (list, tuple)) and len(got) == len(exp), f"{path}：長度 {len(got)} vs oracle {len(exp)}"
        for i, (g, e) in enumerate(zip(got, exp)):
            _assert_close_tree(g, e, f"{path}/{i}")
    elif isinstance(exp, (float, np.floating)) and not isinstance(exp, bool):
        assert isinstance(got, (int, float, np.number)) and not isinstance(got, bool), f"{path}：產品 {got!r} 非數值"
        assert _rel(float(got), float(exp)) <= REL_TOL, f"{path}：產品 {got!r} vs oracle {exp!r}"
    else:
        assert got == exp, f"{path}：產品 {got!r} vs oracle {exp!r}"


def _ic_oracle(x: Any, y: Any, method: str) -> float:
    """點 IC 之 oracle（同 `compute_ic` 之對齊與 NaN 處理，ic_engine.py:181-210、:1196-1213、:1513-1531）：兩欄共同非 NaN
    列；列數 < 2 或任一常數 ⇒ NaN；否則 scipy 對應函式。"""
    xa, ya = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    ok = ~np.isnan(xa) & ~np.isnan(ya)
    xa, ya = xa[ok], ya[ok]
    if xa.size < 2 or np.ptp(xa) == 0 or np.ptp(ya) == 0:
        return math.nan
    return float(_SCIPY[method](xa, ya)[0])


# ── 秒級 oracle 定義測試：分組 IC（grouped_ic） ───────────────────────────────────────────────────────


#: 分組設定（同 `GroupedConfig` 之鍵，ic_config_schema.py:109-131；另開 by_quarter）；無 "method" 鍵＝生產形狀（orchestrator
#: 以 `grouped_analysis.model_dump()` 傳入，ic_filter_orchestrator.py:4323-4329 ⇒ 方法取引擎 `methods[0]`）
GROUPED_CONFIG = {"by_year": True, "by_quarter": True, "by_regime": True, "by_volatility": False, "by_category": True,
                  "by_data_source": True, "by_layer": True, "regime_method": "rule",
                  "regime_definitions": {"high_vol_percentile": 80, "low_vol_percentile": 20}}


def _ref_regime_masks(close: pd.Series, low_pct: float = 20.0, high_pct: float = 80.0) -> Dict[str, np.ndarray]:
    """regime 規則分組之參考實作（ic_engine.py:1356-1389 之定義；只用 0..t）：bull／bear＝close 對 EMA55（adjust=False）；
    vol＝簡單報酬 55 根滾動標準差；high／low 門檻＝累計非 NaN 數 ≥ 100 時以 0..t 之有限 vol 取 np.quantile，否則 ±inf。"""
    c = close.to_numpy(dtype=float)
    ema = close.ewm(span=55, adjust=False).mean().to_numpy(dtype=float)
    vol = close.pct_change(fill_method=None).rolling(55).std().to_numpy(dtype=float)
    lo, hi = np.full(c.size, -np.inf), np.full(c.size, np.inf)
    seen = 0
    for t in range(c.size):
        seen += int(not np.isnan(vol[t]))
        if seen < 100:
            continue
        fin = vol[: t + 1][np.isfinite(vol[: t + 1])]
        if fin.size:
            lo[t], hi[t] = float(np.quantile(fin, low_pct / 100.0)), float(np.quantile(fin, high_pct / 100.0))
    with np.errstate(invalid="ignore"):
        return {"bull": c > ema, "bear": c < ema, "high_vol": vol >= hi, "low_vol": vol <= lo}


def _ref_grouped_ic(features: pd.DataFrame, label: pd.Series, close: pd.Series, metadata: Mapping[str, Mapping[str, Any]],
                    method: str) -> Dict[str, Any]:
    """分組 IC 之 oracle（SPEC Task 0.3：依請求方法逐群組以 scipy 重算）：年度、季度（`<年>Q<季>`）、regime 規則四組、
    metadata 之 category／data_source／layer（值為 None 者不入組）；組內列數 0 ⇒ {}。"""
    y = label.to_numpy(dtype=float)

    def ic_of(rows: np.ndarray, cols: Sequence[str]) -> Dict[str, float]:
        if rows.size == 0:
            return {}
        return {c: _ic_oracle(features[c].to_numpy(dtype=float)[rows], y[rows], method) for c in cols}

    cols = list(features.columns)
    idx = pd.DatetimeIndex(features.index)
    out: Dict[str, Any] = {
        "by_year": {str(yr): ic_of(np.flatnonzero(idx.year == yr), cols) for yr in sorted(set(idx.year))},
        "by_quarter": {f"{yr}Q{q}": ic_of(np.flatnonzero((idx.year == yr) & (idx.quarter == q)), cols)
                       for yr, q in sorted(set(zip(idx.year, idx.quarter)))},
        "by_regime": {k: ic_of(np.flatnonzero(m), cols) for k, m in _ref_regime_masks(close).items()},
    }
    for out_key, meta_key in (("by_category", "category"), ("by_data_source", "data_source"), ("by_layer", "layer")):
        groups: Dict[str, List[str]] = {}
        for c in cols:
            v = (metadata.get(c) or {}).get(meta_key)
            if v is not None:
                groups.setdefault(str(v), []).append(c)
        out[out_key] = {g: ic_of(np.arange(len(features)), members) for g, members in groups.items()}
    return out


#: 明列 metadata：類別兩組（含單特徵組＝向量化單欄分支）、來源兩組、層缺一特徵（None 不入組）
GROUPED_METADATA = {"a": {"category": "trend", "data_source": "kline", "layer": "L1"},
                    "b": {"category": "trend", "data_source": "onchain", "layer": "L2"},
                    "c": {"category": "volatility", "data_source": "kline"}}


def _grouped_inputs(with_nan: bool) -> Any:
    """明列邊界輸入：日頻 430 根（跨 3 個年度、6 個季度；regime 規則分組需 55＋100 根）、三特徵（含同值）、確定性收盤價
    （振幅調變使滾動波動率有高低段）；with_nan ⇒ 特徵與標籤穿插 NaN（逐對路徑），否則無 NaN（向量化路徑）。"""
    n = 430
    idx = pd.date_range("2021-10-01", periods=n, freq="D", tz="UTC")
    i = np.arange(n, dtype=float)
    ret = 0.012 * (1.0 + 0.8 * np.sin(i / 40.0)) * np.sin(i / 2.1) + 0.0004
    close = pd.Series(100.0 * np.exp(np.cumsum(ret)), index=idx, name="close")
    feats = pd.DataFrame({"a": ((7 * i) % 23) - 11.0 + 0.01 * i, "b": np.sin(i / 5.0) + 0.002 * i,
                          "c": np.cos(i / 3.3) * (1.0 + 0.5 * np.sin(i / 40.0))}, index=idx)
    label = pd.Series(0.001 * (((5 * i + 3) % 19) - 9.0) + 0.0003 * feats["b"].to_numpy(), index=idx, name="label")
    if with_nan:
        feats.iloc[[4, 100, 250], 0] = np.nan
        feats.iloc[[33, 301], 2] = np.nan
        label.iloc[[17, 300, 429]] = np.nan
    return feats, label, close


@pytest.mark.parametrize("method", sorted(_SCIPY))
@pytest.mark.parametrize("via", ["engine", "config"])
@pytest.mark.parametrize("with_nan", [False, True])
def test_grouped_ic_matches_scipy(method: str, via: str, with_nan: bool) -> None:
    """`ICEngine.compute_grouped_ic`（ic_engine.py:544-603）逐群組逐特徵 == scipy 對應函式（相對誤差 ≤ 1e-12）：方法來自
    引擎 `methods[0]`（生產形狀，設定無 method 鍵）或設定之 method 鍵；年度、季度、regime 規則、metadata 三種分組；
    群組鍵集合相同。"""
    feats, label, close = _grouped_inputs(with_nan)
    if via == "engine":
        engine, config = ICEngine({"methods": [method]}), dict(GROUPED_CONFIG)
    else:
        engine, config = ICEngine({"methods": ["pearson" if method != "pearson" else "spearman"]}), \
            {**GROUPED_CONFIG, "method": method}
    got = engine.compute_grouped_ic(feats, label, pd.DataFrame({"close": close}), GROUPED_METADATA, config)
    exp = _ref_grouped_ic(feats, label, close, GROUPED_METADATA, method)
    assert all(len(v) for v in exp["by_regime"].values()), "邊界輸入未使 regime 四組皆非空（前提失效）"
    _assert_close_tree(got, exp)


# ── 秒級 oracle 定義測試：第 5 段逐根 PIT 參考實作（分位報酬、多空、單調性、換手率、排名變化率、自相關、覆蓋率） ───────

#: 現行 PIT 最少樣本（pit_stats.py:39 MIN_SAMPLES；MonotonicityTester／TurnoverAnalyzer 設定無此鍵時之預設）
PIT_MIN = 100


def _ref_pit_qcut(x: np.ndarray, q: int, min_samples: int = PIT_MIN) -> np.ndarray:
    """PIT 分位標籤參考實作（只用 0..t；SPEC Task 1.1 之 pandas oracle）：累計非 NaN 數（±inf 計入）< min_samples 或當根
    非有限 ⇒ NaN；否則 `pd.qcut(0..t 之有限值, q, labels=False, duplicates="drop")` 之當根（最後一個有限值）整數標籤。"""
    out = np.full(x.size, np.nan)
    seen = 0
    for t in range(x.size):
        seen += int(not np.isnan(x[t]))
        if seen < min_samples or not np.isfinite(x[t]):
            continue
        fin = x[: t + 1][np.isfinite(x[: t + 1])]
        try:
            lab = np.asarray(pd.qcut(fin, q, labels=False, duplicates="drop"), dtype=float)
        except ValueError:
            continue
        if not np.isnan(lab[-1]):
            out[t] = float(lab[-1])
    return out


def _ref_pit_qcut_bins(x: np.ndarray, q: int, min_samples: int = PIT_MIN) -> Any:
    """PIT 分位標籤與當根自身箱數 k_t（SPEC Task 0.4 ①）：同 `_ref_pit_qcut` 之逐根規則，另以同一次
    `pd.qcut(..., retbins=True, duplicates="drop")` 之去重後邊界數 − 1 得 k_t（第 t 根自身分箱所得之箱數，不以請求 q
    代替；箱數計邊界而非已占用之標籤數——最高箱恆含當前歷史最大值，故有箱時標籤 k_t − 1 恆可達）。有限歷史全相同
    （去重後只一個邊界、無箱）⇒ pd.qcut 無標籤。標籤 NaN 處 k_t＝NaN。
    回 (labels, k)。"""
    out, k = np.full(x.size, np.nan), np.full(x.size, np.nan)
    seen = 0
    for t in range(x.size):
        seen += int(not np.isnan(x[t]))
        if seen < min_samples or not np.isfinite(x[t]):
            continue
        fin = x[: t + 1][np.isfinite(x[: t + 1])]
        try:
            lab, edges = pd.qcut(fin, q, labels=False, retbins=True, duplicates="drop")
        except ValueError:
            continue
        lab = np.asarray(lab, dtype=float)
        if not np.isnan(lab[-1]):
            out[t], k[t] = float(lab[-1]), float(len(edges) - 1)
    return out, k


def _ref_top_mask(x: np.ndarray, q: int) -> np.ndarray:
    """逐根 PIT 頂分位指示（SPEC Task 0.4 ①）：第 t 根屬頂分位 ⟺ 其 PIT 標籤＝k_t − 1（只用 0..t）；標籤 NaN 處 NaN。"""
    lab, k = _ref_pit_qcut_bins(x, q)
    return np.where(np.isnan(lab), np.nan, (lab == k - 1).astype(float))


def _ref_pit_rank(x: np.ndarray, min_samples: int = PIT_MIN) -> np.ndarray:
    """PIT 排名參考實作（SPEC Task 1.2 之定義）：當根值於 0..t 非 NaN 歷史（含 ±inf）之 average 排名＝嚴格小於之數＋
    （等於之數＋1）／2；累計非 NaN 數 < min_samples 或當根非有限 ⇒ NaN。"""
    out = np.full(x.size, np.nan)
    seen = 0
    for t in range(x.size):
        seen += int(not np.isnan(x[t]))
        if seen < min_samples or not np.isfinite(x[t]):
            continue
        h = x[: t + 1][~np.isnan(x[: t + 1])]
        out[t] = float(np.sum(h < x[t])) + (float(np.sum(h == x[t])) + 1.0) / 2.0
    return out


def _ref_select_q(n: int, requested: int, min_group: int = 30) -> int:
    """分位數選擇（monotonicity_tester.py:200-204 之規則）：requested > 3 且 n／requested < 最小組大小 ⇒ 3。"""
    requested = max(int(requested), 2)
    return 3 if requested > 3 and n / requested < min_group else requested


def _ref_mono_bins(x: np.ndarray, q: int, agg: Optional[np.ndarray] = None) -> Optional[np.ndarray]:
    """單調性之分組（monotonicity_tester.py `_assign_quantiles` 之規則）：PIT 標籤依特徵 x 之全部有限歷史（SPEC Task 0.4 ⑦：
    不因標籤缺值而剔除歷史）；聚合列 `agg`（標籤有限者；None＝全部）上之標籤全 NaN、或實際 bin 數 < q 且 q > 3 ⇒ 改 q=3
    重分；回聚合列以外為 NaN 之標籤陣列。"""
    lab = _ref_pit_qcut(x, q)
    agg = np.ones(x.size, dtype=bool) if agg is None else np.asarray(agg, dtype=bool)
    lab = np.where(agg, lab, np.nan)
    if np.isnan(lab).all():
        return _ref_mono_bins(x, 3, agg) if q > 3 else None
    if int(np.nanmax(lab)) + 1 < q and q > 3:
        return _ref_mono_bins(x, 3, agg)
    return lab


def _ref_mono_frame(feature: pd.Series, label: pd.Series) -> Any:
    """單調性輸入（SPEC Task 0.4 ⑦）：特徵非 NaN 之列（含標籤缺值者），回 (frame, agg＝標籤有限)。"""
    data = pd.concat([feature.rename("f"), label.rename("y")], axis=1)
    data = data[data["f"].notna()]
    return data, data["y"].notna().to_numpy()


def _ref_long_short(feature: pd.Series, label: pd.Series, q_req: int = 5) -> Dict[str, float]:
    """多空價差、t、p、pooled Sharpe 之 oracle（SPEC Task 0.3：測試自寫之 PIT 分組重得兩組報酬後呼叫
    `scipy.stats.ttest_ind(high, low, nan_policy="omit")`，同 monotonicity_tester.py:153-164 之參數）。"""
    nan4 = {"spread": math.nan, "tstat": math.nan, "pvalue": math.nan, "sharpe": math.nan}
    data, agg = _ref_mono_frame(feature, label)
    if not agg.any():
        return nan4
    bins = _ref_mono_bins(data["f"].to_numpy(dtype=float), _ref_select_q(int(agg.sum()), q_req), agg)
    if bins is None or np.isnan(bins).all():
        return nan4
    y = data["y"].to_numpy(dtype=float)
    low, high = y[bins == np.nanmin(bins)], y[bins == np.nanmax(bins)]
    if low.size == 0 or high.size == 0:
        return nan4
    spread = float(high.mean() - low.mean())
    tt = stats.ttest_ind(high, low, nan_policy="omit")
    sharpe = math.nan
    if low.size >= 2 and high.size >= 2:
        pooled = ((low.size - 1) * np.var(low, ddof=1) + (high.size - 1) * np.var(high, ddof=1)) / (low.size + high.size - 2)
        sharpe = float(spread / np.sqrt(pooled)) if pooled > 0 else math.nan
    return {"spread": spread, "tstat": float(tt.statistic), "pvalue": float(tt.pvalue), "sharpe": sharpe}


def _ref_monotonicity(feature: pd.Series, label: pd.Series, q_req: int = 5) -> Dict[str, Any]:
    """`MonotonicityTester.compute_all` 單一特徵之 oracle：分位平均報酬（預填 Q1..Qq，缺 bin ⇒ NaN）、各分位累積報酬
    （分位內依時間序之累加）、單調性分數（依分位序相鄰差 > 0 之比例，缺 bin 之差不計，monotonicity_tester.py:79-100）、
    多空（`_ref_long_short`）。"""
    data, agg = _ref_mono_frame(feature, label)
    n_agg = int(agg.sum())
    q = _ref_select_q(n_agg, q_req) if n_agg else q_req
    means: Dict[str, float] = {f"Q{i + 1}": math.nan for i in range(q)}
    cums: Dict[str, List[float]] = {f"Q{i + 1}": [] for i in range(q)}
    bins = _ref_mono_bins(data["f"].to_numpy(dtype=float), q, agg) if n_agg else None
    ls = _ref_long_short(feature, label, q_req)
    if bins is not None:
        y = data["y"].to_numpy(dtype=float)
        for b in sorted(set(bins[~np.isnan(bins)].astype(int))):
            if 0 <= b < q:
                vals = y[bins == b]
                means[f"Q{b + 1}"], cums[f"Q{b + 1}"] = float(np.mean(vals)), np.cumsum(vals).tolist()
    ordered = np.asarray([means[f"Q{i + 1}"] for i in range(q)], dtype=float)
    pair = np.isfinite(ordered[:-1]) & np.isfinite(ordered[1:])
    score = float(np.mean((ordered[1:] - ordered[:-1])[pair] > 0)) if ordered.size >= 2 and pair.any() else 0.0
    qr = {"quantile_mean_returns": means, "long_short_spread": ls["spread"] if bins is not None else math.nan,
          "long_short_tstat": ls["tstat"] if bins is not None else math.nan, "cumulative_returns": cums}
    return {"quantile_returns": qr, "monotonicity_score": score, "long_short": ls}


def _ref_mean_abs_diff(v: np.ndarray) -> float:
    d = np.abs(np.diff(v))
    d = d[np.isfinite(d)]
    return float(np.mean(d)) if d.size else 0.0


def _ref_turnover(x: pd.Series, q: int = 5) -> Dict[str, Any]:
    """`TurnoverAnalyzer.compute_all` 單一特徵之 oracle（turnover_analyzer.py:61-191、:221-244 之輸出形狀，不 dropna）：頂分位
    ＝逐根 PIT 定義（SPEC Task 0.4 ①，`_ref_top_mask`：第 t 根標籤＝其自身分箱之 k_t − 1；**非**現行之全序列 PIT 標籤
    最大值——該定義偷看未來，見 `test_turnover_time_series_prefix_invariant_with_late_bins`）之 0／1 指示（標籤 NaN 處 NaN），
    分位換手率＝其相鄰差絕對值之有限平均；排名變化率＝PIT 排名相鄰差絕對值之有限平均（全 NaN ⇒ NaN、無有限差 ⇒ 0）；
    自相關＝去 NaN 後 lag-1 之 `scipy.stats.pearsonr`（含 ±inf 或常數 ⇒ NaN，同 pandas）；逐根時序之 warmup（累計非 NaN
    數 < 100 之前）＝None、首個有效根之變化＝0、非有限＝None。換手率兩欄見 `TURNOVER_PATHS`。"""
    v = x.to_numpy(dtype=float)
    n = v.size
    lab, rk = _ref_pit_qcut(v, q), _ref_pit_rank(v)
    top = _ref_top_mask(v, q)
    turnover = math.nan if n < 2 or np.isnan(lab).all() else _ref_mean_abs_diff(top)
    rank_change = math.nan if n < 2 or np.isnan(rk).all() else _ref_mean_abs_diff(rk)
    nn = v[~np.isnan(v)]
    if nn.size < 3 or not np.isfinite(nn).all() or np.ptp(nn[:-1]) == 0 or np.ptp(nn[1:]) == 0:
        autocorr = math.nan
    else:
        autocorr = float(stats.pearsonr(nn[:-1], nn[1:])[0])
    hits = np.flatnonzero(np.cumsum(~np.isnan(v)) >= PIT_MIN)
    fv = int(hits[0]) if hits.size else None
    qt = np.concatenate([[np.nan], np.abs(np.diff(top))])
    rc = np.concatenate([[np.nan], np.abs(np.diff(rk))])
    if fv is not None:
        qt[fv] = rc[fv] = 0.0

    def ser(a: np.ndarray) -> List[Optional[float]]:
        return [None if fv is None or i < fv or not np.isfinite(a[i]) else float(a[i]) for i in range(n)]

    stamps = [ts.isoformat() if hasattr(ts, "isoformat") else ts for ts in x.index]
    return {"quantile_turnover": turnover, "rank_change_rate": rank_change, "autocorrelation": autocorr,
            "time_series": {"quantile_turnovers": ser(qt), "rank_change_rates": ser(rc), "timestamps": stamps}}


#: `TurnoverAnalyzer.compute_all` 單一特徵輸出中依頂分位定義之兩欄（SPEC Task 0.4 ①：單值分位換手率、逐根換手時序）
TURNOVER_PATHS = (("quantile_turnover",), ("time_series", "quantile_turnovers"))


def _split_turnover(d: Mapping[str, Any]) -> Any:
    """換手率輸出 → (頂分位兩欄, 其餘欄)：前者為 `TURNOVER_PATHS` 之值；後者為去除該兩欄後之巢狀副本（鍵集合仍逐層比對）。"""
    top = {"/".join(p): (d[p[0]] if len(p) == 1 else d[p[0]][p[1]]) for p in TURNOVER_PATHS}
    rest = {k: (dict(v) if isinstance(v, Mapping) else v) for k, v in d.items()}
    for p in TURNOVER_PATHS:
        if len(p) == 1:
            rest.pop(p[0])
        else:
            rest[p[0]].pop(p[1])
    return top, rest


def _ref_coverage(x: pd.Series) -> Dict[str, Any]:
    """`CoverageAnalyzer.compute_all` 單一特徵之 oracle（coverage_analyzer.py:28-60）：非 NaN 比例、首個非 NaN 之位置（無 ⇒ −1）、
    NaN 數。"""
    v = x.to_numpy(dtype=float)
    ok = ~np.isnan(v)
    return {"coverage": float(ok.sum() / v.size) if v.size else math.nan,
            "effective_start": int(np.argmax(ok)) if ok.any() else -1, "nan_count": int((~ok).sum())}


def _stage5_inputs(n: int = 320) -> Any:
    """明列邊界輸入（逐根時序，小時頻索引）：平滑趨勢特徵、含同值與 NaN 穿插之特徵、含 ±inf 之特徵（PIT 歷史含 inf、當根
    非有限 ⇒ NaN）、長 warmup 之特徵（前 150 根 NaN）；標籤含 NaN 與末段 NaN。"""
    idx = pd.date_range("2024-01-01", periods=n, freq="h", tz="UTC")
    i = np.arange(n, dtype=float)
    smooth = np.sin(i / 7.0) + 0.002 * i
    def at(*pos: int) -> List[int]:
        return [p for p in pos if p < n]

    ties = np.round(((11 * i) % 17) / 4.0)
    ties[at(3, 50, 51, 140, 260)] = np.nan
    infs = ((13 * i) % 29) - 14.0 + 0.001 * i
    infs[at(110, 120)], infs[at(115, 200)] = np.inf, -np.inf
    late = np.where(i < 150, np.nan, np.cos(i / 4.0) + 0.01 * ((3 * i) % 7))
    feats = pd.DataFrame({"smooth": smooth, "ties": ties, "infs": infs, "late": late}, index=idx)
    y = 0.01 * np.cos(i / 5.0) + 0.003 * smooth + 0.0005 * (((7 * i) % 13) - 6.0)
    y[at(10, 77, 300)] = np.nan
    y[-3:] = np.nan
    return feats, pd.Series(y, index=idx, name="label")


@pytest.mark.parametrize("n,expected_q", [(320, 5), (120, 3)])
def test_long_short_tstat_matches_scipy_ttest_ind(n: int, expected_q: int) -> None:
    """多空 t 值（monotonicity_tester.py:153-164；ic_reporter.py:395-401 透傳為 `quantile_returns.<特徵>.long_short_tstat`）
    == 測試自寫 PIT 分組後之 `scipy.stats.ttest_ind(high, low, nan_policy="omit")`；spread、p、pooled Sharpe 同；n＝120
    ⇒ 每組 < 30 退回 3 分位之分支。"""
    feats, label = _stage5_inputs(n)
    tester = MonotonicityTester({})
    for feat in ("smooth", "ties", "infs"):
        data = pd.concat([feats[feat], label], axis=1).dropna()
        assert _ref_select_q(len(data), 5) == expected_q, "邊界輸入未落預期分位數分支（前提失效）"
        exp = _ref_long_short(feats[feat], label)
        assert math.isfinite(exp["tstat"]), f"{feat}：oracle t 非有限（輸入退化）"
        _assert_close_tree(tester.compute_long_short_spread(feats[feat], label), exp, feat)
        got_t = tester.compute_quantile_returns(feats[feat], label)["long_short_tstat"]
        assert _rel(float(got_t), exp["tstat"]) <= REL_TOL, f"{feat}：quantile_returns.long_short_tstat {got_t} vs {exp['tstat']}"


@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_stage5_pit_stats_match_reference() -> None:
    """第 5 段逐特徵輸出（`MonotonicityTester.compute_all`、`TurnoverAnalyzer.compute_all`、`CoverageAnalyzer.compute_all`，
    ic_filter_orchestrator.py:4495-4507 之呼叫形狀）== 測試自寫之逐根 PIT 參考實作（只用 0..t）：分位平均與累積報酬、多空、
    單調性分數、排名變化率、自相關、逐根排名變化時序與時間戳、覆蓋率。頂分位兩欄（分位換手率、逐根換手時序）另見
    `test_stage5_quantile_turnover_matches_per_bar_pit_reference`。"""
    feats, label = _stage5_inputs()
    mono = MonotonicityTester({}).compute_all(feats, label)
    turn = TurnoverAnalyzer({}).compute_all(feats)
    cov = CoverageAnalyzer().compute_all(feats)
    for feat in feats.columns:
        _assert_close_tree(mono[feat], _ref_monotonicity(feats[feat], label), f"mono/{feat}")
        _assert_close_tree(_split_turnover(turn[feat])[1], _split_turnover(_ref_turnover(feats[feat]))[1], f"turnover/{feat}")
        _assert_close_tree(cov[feat], _ref_coverage(feats[feat]), f"coverage/{feat}")
    assert math.isfinite(mono["smooth"]["long_short"]["tstat"]) and turn["smooth"]["quantile_turnover"] > 0, \
        "邊界輸入退化（前提失效）"


def _stage5_turnover_inputs() -> pd.DataFrame:
    """頂分位換手率之明列輸入：`_stage5_inputs` 四欄加 `_late_bins_series` 同長（前 150 根三種離散值 ⇒ 逐根箱數 k_t < 5，
    其後漸得滿 5 箱——逐根定義與全序列最大標籤定義於前段不同）。"""
    feats, _ = _stage5_inputs()
    return feats.assign(late_bins=_late_bins_series(len(feats)).to_numpy())


# Task 0.3 稽核發現、SPEC Task 0.4 ① 已修：修正前分位換手率與逐根換手時序之頂分位以全序列 PIT 標籤最大值界定
# （turnover_analyzer.py 舊 :85-89、:168-172 `quantiles.max(skipna=True)`），於箱數隨歷史成長之序列偷看未來；修正後依逐根
# PIT 定義（第 t 根標籤＝其自身分箱之 k_t − 1，pit_stats.pit_expanding_qcut_top_mask）。
@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_stage5_quantile_turnover_matches_per_bar_pit_reference() -> None:
    """第 5 段頂分位兩欄（`TurnoverAnalyzer.compute_all` 之 `quantile_turnover`、`time_series.quantile_turnovers`）== 逐根
    PIT 參考實作（`_ref_turnover`：第 t 根屬頂分位 ⟺ 標籤＝k_t − 1，只用 0..t）；輸入含 `_late_bins_series`（逐根箱數成長）。"""
    feats = _stage5_turnover_inputs()
    turn = TurnoverAnalyzer({}).compute_all(feats)
    for feat in feats.columns:
        _assert_close_tree(_split_turnover(turn[feat])[0], _split_turnover(_ref_turnover(feats[feat]))[0], f"turnover/{feat}")


@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_per_bar_top_quantile_oracle_boundaries() -> None:
    """逐根頂分位 oracle 本身（不經產品碼）：`_ref_pit_qcut_bins` 之標籤 == `_ref_pit_qcut`；1 ≤ k_t ≤ q 且標籤 ≤ k_t − 1；
    頂分位指示前綴不變（截去後段不改前段）；`_late_bins_series` 前段 k_t < 5 且逐根定義與全序列最大標籤定義確有不同
    （上列 strict xfail 之前提：兩定義不同時方能區辨）。"""
    s = _late_bins_series()
    v = s.to_numpy(dtype=float)
    for q in (3, 5):
        lab, k = _ref_pit_qcut_bins(v, q)
        assert _same(lab, _ref_pit_qcut(v, q)), f"q={q}：帶箱數之標籤與 _ref_pit_qcut 不同"
        ok = ~np.isnan(lab)
        assert ok.any() and np.array_equal(np.isnan(k), ~ok), f"q={q}：k_t 與標籤之 NaN 位置不同"
        assert ((k[ok] >= 1) & (k[ok] <= q) & (lab[ok] <= k[ok] - 1)).all(), f"q={q}：k_t 或標籤越界"
        assert _same(_ref_top_mask(v, q)[:150], _ref_top_mask(v[:150], q)), f"q={q}：逐根頂分位指示前段隨後段改變"
    lab, k = _ref_pit_qcut_bins(v, 5)
    assert np.nanmax(k[:150]) < 5 and np.nanmax(k) == 5, "邊界輸入未使逐根箱數成長（前提失效）"
    whole_max = np.where(np.isnan(lab), np.nan, (lab == np.nanmax(lab)).astype(float))
    assert not _same(_ref_top_mask(v, 5), whole_max), "逐根定義與全序列最大標籤定義相同（前提失效）"


# ── 秒級 oracle 定義測試：FDR ─────────────────────────────────────────────────────────────────────────

#: 明列邊界輸入：同值 p、0 與 1、NaN、±inf、不可轉 float 者（非有限與不可轉者不入檢定集合、q 為 NaN）
FDR_P = {"a": 0.001, "b": 0.04, "c": 0.04, "d": math.nan, "e": 0.5, "f": 1.0, "g": 0.0, "h": "bad", "i": math.inf,
         "j": 0.012, "k": 0.3, "l": -math.inf}


def test_fdr_matches_statsmodels_multipletests() -> None:
    """`apply_fdr`（statistical_validator.py:161-219；第 5 段以進場全欄之 HAC p 呼叫，ic_filter_orchestrator.py:4425-4443）之
    q == `statsmodels.stats.multitest.multipletests(<有限 p>, method="fdr_bh")[1]`（同檢定集合＝有限 p，相對誤差 ≤ 1e-12），
    非有限／不可轉者 q＝NaN、n_tests＝有限 p 數；邊界：空 dict、全非有限、非精確 "fdr_bh" 之方法 ⇒ ValueError。"""
    q, n_tests = apply_fdr(dict(FDR_P), 0.05)
    finite = {k: float(v) for k, v in FDR_P.items() if isinstance(v, float) and math.isfinite(v)}
    adj = multipletests(list(finite.values()), method="fdr_bh")[1]
    exp = {k: math.nan for k in FDR_P}
    exp.update({k: float(a) for k, a in zip(finite, adj)})
    assert n_tests == len(finite) == 8
    _assert_close_tree(q, exp)
    assert apply_fdr({}, 0.05) == ({}, 0)
    q_nan, n_nan = apply_fdr({"x": math.nan, "y": math.inf}, 0.05)
    assert n_nan == 0 and all(math.isnan(v) for v in q_nan.values()) and set(q_nan) == {"x", "y"}
    with pytest.raises(ValueError):
        apply_fdr({"a": 0.1}, 0.05, method="FDR_BH")


# ── 秒級 oracle 定義測試：第 6 段相關矩陣與多元化指標 ─────────────────────────────────────────────────────


def _ref_corr(df: pd.DataFrame) -> np.ndarray:
    """第 6 段相關矩陣之 oracle（SPEC Task 0.3：redundancy_filter.py:161-178 之兩路徑分別對照）：無 NaN ⇒ `numpy.corrcoef`
    （截至 [-1, 1]；常數欄整列 NaN）；含 NaN ⇒ 逐對以兩欄共同有限列由 `scipy.stats.pearsonr` 重算（列數 < 2 或任一常數 ⇒
    NaN，同 pandas pairwise-complete 語意）。"""
    v = df.to_numpy(dtype=float)
    if not np.isnan(v).any():
        with np.errstate(invalid="ignore", divide="ignore"):
            return np.clip(np.corrcoef(v, rowvar=False), -1.0, 1.0)
    k = v.shape[1]
    out = np.full((k, k), np.nan)
    for a in range(k):
        for b in range(k):
            m = np.isfinite(v[:, a]) & np.isfinite(v[:, b])
            x, y = v[m, a], v[m, b]
            if x.size >= 2 and np.ptp(x) > 0 and np.ptp(y) > 0:
                out[a, b] = float(stats.pearsonr(x, y)[0])
    return out


def _corr_inputs(with_nan: bool) -> pd.DataFrame:
    """明列邊界輸入：正相關、負相關、部分相關、常數欄（std＝0 ⇒ NaN）；with_nan ⇒ 穿插 NaN（逐對有效列路徑）。"""
    i = np.arange(90, dtype=float)
    a = np.sin(i / 6.0) + 0.01 * i
    df = pd.DataFrame({"a": a, "b": -0.8 * a + 0.3 * np.cos(i / 2.0), "c": ((7 * i) % 19) - 9.0 + 0.5 * a,
                       "d": np.cos(i / 4.0) * 0.7 + 0.2 * a, "const": np.full(i.size, 2.5)})
    if with_nan:
        df.loc[[3, 17, 40], "a"] = np.nan
        df.loc[[17, 55], "c"] = np.nan
        df.loc[[60], "const"] = np.nan
    return df


@pytest.mark.parametrize("with_nan", [False, True])
@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_redundancy_correlation_matches_oracle(with_nan: bool) -> None:
    """`RedundancyFilter.compute_correlation_matrix` 逐元素 == oracle（無 NaN＝numpy.corrcoef、含 NaN＝逐對 pearsonr；NaN＝NaN；
    相對誤差 ≤ 1e-12）；行列名同輸入欄序。"""
    df = _corr_inputs(with_nan)
    got = RedundancyFilter({}).compute_correlation_matrix(df)
    assert list(got.index) == list(got.columns) == list(df.columns)
    exp = _ref_corr(df)
    for r, a in enumerate(df.columns):
        for c, b in enumerate(df.columns):
            assert _rel(float(got.loc[a, b]), float(exp[r, c])) <= REL_TOL, f"{a}/{b}：{got.loc[a, b]} vs oracle {exp[r, c]}"
    assert np.isfinite(exp[:4, :4]).all(), "邊界輸入退化（前提失效）"


def _ref_diversification(selected: Sequence[str], corr: pd.DataFrame, metadata: Mapping[str, Any]) -> Dict[str, Any]:
    """多元化指標之 oracle（SPEC Task 0.3：redundancy_filter.py:315-347、:393-409 之公式）：子矩陣（缺特徵或空矩陣 ⇒ 單位矩陣）
    上三角 |ρ|（NaN 計 0）之平均與最大；有效獨立數＝k／(1＋avg·(k−1))（k ≤ 1 ⇒ 1）；覆蓋率＝所選特徵之 metadata 值種數
    ／全體種數（無 metadata 或全為 None ⇒ 0）；空選集 ⇒ NaN、NaN、0、0、0、0。"""
    if not selected:
        return {"avg_abs_correlation": math.nan, "max_correlation": math.nan, "effective_independent_features": 0.0,
                "category_coverage": 0.0, "data_source_coverage": 0.0, "layer_coverage": 0.0}
    k = len(selected)
    if corr.empty or not set(selected) <= set(corr.index):
        m = np.eye(k)
    else:
        m = corr.loc[list(selected), list(selected)].to_numpy(dtype=float)
    upper = np.abs(np.nan_to_num(m, nan=0.0))[np.triu_indices(k, 1)]
    avg, mx = (float(np.mean(upper)), float(np.max(upper))) if upper.size else (0.0, 0.0)

    def cov(key: str) -> float:
        total = {(info or {}).get(key) for info in (metadata or {}).values() if info} - {None}
        if not total:
            return 0.0
        chosen = {(metadata.get(n) or {}).get(key) for n in selected} - {None}
        return float(len(chosen) / len(total))

    return {"avg_abs_correlation": avg, "max_correlation": mx,
            "effective_independent_features": 1.0 if k <= 1 else float(k / (1.0 + avg * (k - 1))),
            "category_coverage": cov("category"), "data_source_coverage": cov("data_source"), "layer_coverage": cov("layer")}


DIVERSIFICATION_METADATA = {"a": {"category": "trend", "data_source": "kline", "layer": "L1"},
                            "b": {"category": "trend", "data_source": "kline", "layer": "L2"},
                            "c": {"category": "volatility", "data_source": "onchain", "layer": None},
                            "d": {"category": "volume", "data_source": "kline", "layer": "L1"},
                            "const": {"category": "misc"}}


@pytest.mark.parametrize("case", ["multi", "with_const_nan", "single", "empty", "not_in_matrix", "no_metadata"])
@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_diversification_metrics_match_reference(case: str) -> None:
    """`RedundancyFilter.compute_diversification_metrics`（第 6 段以倖存者之相關矩陣與 metadata 呼叫，
    ic_filter_orchestrator.py:4706-4710）== 公式之獨立重算；相關矩陣取 oracle（`_ref_corr`）；邊界：單特徵、空選集、選集不在
    矩陣內、無 metadata、常數欄之 NaN 相關。"""
    df = _corr_inputs(False)
    corr = pd.DataFrame(_ref_corr(df), index=df.columns, columns=df.columns)
    selected = {"multi": ["a", "b", "c", "d"], "with_const_nan": ["a", "c", "const"], "single": ["c"], "empty": [],
                "not_in_matrix": ["a", "zz"], "no_metadata": ["a", "b"]}[case]
    meta = {} if case == "no_metadata" else DIVERSIFICATION_METADATA
    got = RedundancyFilter({}).compute_diversification_metrics(list(selected), corr, meta)
    _assert_close_tree(got, _ref_diversification(selected, corr, meta))


# ── 秒級 oracle 定義測試：邊際 IC（per_feature／sequential／removed_candidates、train_ic、composite） ─────────────

#: 邊際 IC 參數（`MarginalICParams` 預設，重抽樣次數減為 64 以保秒級；固定 seed 重現 ci95／delta_ci95）
MARGINAL_PARAMS = MarginalICParams(n_bootstrap=64)


def _sp(a: np.ndarray, b: np.ndarray) -> float:
    """Spearman ρ oracle（`scipy.stats.spearmanr`）；列數 < 2 或任一常數 ⇒ NaN（同 marginal_ic.py:213-217 之定義）。"""
    if a.shape[0] < 2 or np.ptp(a) == 0.0 or np.ptp(b) == 0.0:
        return math.nan
    return float(stats.spearmanr(a, b)[0])


def _none_if_nan(v: float) -> Optional[float]:
    return v if math.isfinite(v) else None


def _ref_nscore(x: np.ndarray) -> np.ndarray:
    """van der Waerden 秩常態分數 oracle：`scipy.stats.norm.ppf(scipy.stats.rankdata(x, "average")／(n＋1))`。"""
    return stats.norm.ppf(stats.rankdata(x, method="average") / (x.shape[0] + 1.0))


def _ref_block_ci(stat: Any, arrays: Sequence[np.ndarray], block_len: int, n_boot: int, seed: int) -> Optional[List[float]]:
    """成對 moving-block bootstrap 之測試自寫參考實作（固定 seed；factor_combiner.py:44-90 之規則）：每次以
    `default_rng(seed).integers(0, n−b＋1)` 抽 ceil(n／b) 個起點、串接切至 n；非有限統計量略過；percentile 2.5／97.5 與點估之
    包絡；全非有限 ⇒ None。"""
    n = arrays[0].shape[0]
    if n == 0:
        return None
    b = min(int(block_len), n)
    rng = np.random.default_rng(seed)
    point = float(stat(*arrays))
    vals = []
    for _ in range(int(n_boot)):
        starts = rng.integers(0, n - b + 1, size=int(math.ceil(n / b)))
        idx = np.concatenate([np.arange(s, s + b) for s in starts])[:n]
        v = float(stat(*[a[idx] for a in arrays]))
        if math.isfinite(v):
            vals.append(v)
    if not vals:
        return None
    lo, hi = float(np.quantile(vals, 0.025)), float(np.quantile(vals, 0.975))
    if math.isfinite(point):
        lo, hi = min(lo, point), max(hi, point)
    return [lo, hi]


def _ref_marginal_one(X: pd.DataFrame, y: np.ndarray, tr: np.ndarray, te: np.ndarray, f: str, S: Sequence[str],
                      p: MarginalICParams) -> Dict[str, Any]:
    """單候選邊際 IC 之 oracle（SPEC Task 0.3：投影迴歸以 `statsmodels.api.OLS`、R²＝其 rsquared、條件數
    `numpy.linalg.cond`、IC 以 `scipy.stats.spearmanr`；train／test 切分照現行——只在 f、S、標籤皆有限之列，投影只以 train
    段擬合後套於 test 段；marginal_ic.py:425-485 之列數、標籤退化、殘差退化分支）。"""
    cols = [f] + list(S)
    V = X[cols].to_numpy(dtype=float)
    fin = np.isfinite(V).all(axis=1) & np.isfinite(y)
    rtr, rte = tr & fin, te & fin
    ntr, nte = int(rtr.sum()), int(rte.sum())
    base = {"conditioning_set": list(S), "n_used_train": ntr, "n_used_test": nte}
    empty = {"marginal_ic": None, "gross_ic": None, "ic_retained_ratio": None, "marginal_ic_train_insample": None,
             "ci95": None, "condition_number": None, "r2_train": None}
    need = max(int(p.min_test_rows), int(p.min_rows_per_regressor) * len(S))
    if nte < need or ntr < need or ntr < 2 or nte < 2:
        return {"status": "not_computed", "reason": "insufficient_rows", **base, **empty}
    ytr, yte = y[rtr], y[rte]
    if np.ptp(yte) == 0.0 or np.ptp(ytr) == 0.0:
        return {"status": "not_computed", "reason": "label_degenerate", **base, **empty}
    Ztr = np.column_stack([np.ones(ntr)] + [_ref_nscore(V[rtr, j]) for j in range(1, len(cols))])
    Zte = np.column_stack([np.ones(nte)] + [_ref_nscore(V[rte, j]) for j in range(1, len(cols))])
    zf_tr, zf_te = _ref_nscore(V[rtr, 0]), _ref_nscore(V[rte, 0])
    fit = sm.OLS(zf_tr, Ztr).fit()
    r_te, r_tr = zf_te - Zte @ fit.params, zf_tr - Ztr @ fit.params
    thr = float(p.degenerate_threshold)
    if float(np.var(r_te)) <= thr:
        return {"status": "not_computed", "reason": "residual_degenerate", **base, **empty}
    marginal, gross = _sp(r_te, yte), _sp(V[rte, 0], yte)
    ratio = marginal / gross if math.isfinite(gross) and abs(gross) >= 1e-12 else math.nan
    insample = math.nan if float(np.var(r_tr)) <= thr else _sp(r_tr, ytr)
    # 只含截距 ⇒ 殘差＝離均差 ⇒ 依定義 R²＝0；statsmodels 對純截距模型回浮點殘值（實測 −2.2e-16），以定義值為 oracle
    r2 = 0.0 if len(S) == 0 else float(fit.rsquared)
    return {"status": "ok", "reason": None, **base, "marginal_ic": _none_if_nan(marginal), "gross_ic": _none_if_nan(gross),
            "ic_retained_ratio": _none_if_nan(ratio), "marginal_ic_train_insample": _none_if_nan(insample),
            "ci95": _ref_block_ci(_sp, (r_te, yte), p.block_len, p.n_bootstrap, p.seed),
            "condition_number": _none_if_nan(float(np.linalg.cond(Ztr))), "r2_train": _none_if_nan(r2)}


def _ref_train_ic(X: pd.DataFrame, y: np.ndarray, tr: np.ndarray, survivors: Sequence[str]) -> Dict[str, Optional[float]]:
    """`marginal_ic.train_ic` 之 oracle（SPEC Task 0.3：marginal_ic.py:394-405）：只用 train 段且該特徵與標籤皆有限之列，
    列數 < 2 ⇒ None，否則 `scipy.stats.spearmanr`（常數 ⇒ NaN ⇒ None；None 不得視為 0）。"""
    out: Dict[str, Optional[float]] = {}
    for name in survivors:
        x = X[name].to_numpy(dtype=float)
        rows = tr & np.isfinite(x) & np.isfinite(y)
        out[name] = None if rows.sum() < 2 else _none_if_nan(_sp(x[rows], y[rows]))
    return out


def _ref_marginal(X: pd.DataFrame, y: np.ndarray, tr: np.ndarray, te: np.ndarray, survivors: Sequence[str],
                  extra: Sequence[str], p: MarginalICParams) -> Dict[str, Any]:
    """邊際 IC 三視角之 oracle：loo（S＝其餘倖存者）、sequential（依 train_ic 之 (−|ic|，名) 排序、S＝前序；None 之鍵取 0，
    marginal_ic.py:407-410）、removed_candidates（S＝全部倖存者）。"""
    tic = _ref_train_ic(X, y, tr, survivors)
    order = sorted(survivors, key=lambda n: (-abs(tic[n]) if tic[n] is not None else 0.0, n))
    return {"train_ic": tic,
            "per_feature": {f: _ref_marginal_one(X, y, tr, te, f, [s for s in survivors if s != f], p) for f in survivors},
            "sequential": [{"feature": f, "step": i, **_ref_marginal_one(X, y, tr, te, f, order[:i], p)}
                           for i, f in enumerate(order)],
            "removed_candidates": {c: _ref_marginal_one(X, y, tr, te, c, list(survivors), p) for c in extra}}


def _ref_composite(X: pd.DataFrame, y: np.ndarray, tr: np.ndarray, te: np.ndarray, survivors: Sequence[str],
                   p: MarginalICParams) -> Dict[str, Any]:
    """組合因子之 oracle（SPEC Task 0.3：factor_combiner.py:150-302；序列化 :126-133）：complete-case 列；符號與權重只由 train
    段 Spearman（equal＝1／k′、ic_weighted＝|ic|／Σ|ic|；符號 0 或 NaN 者排除）；composite＝Σ w·sign·秩常態分數（各段內
    分別計分）；composite_ic 與 top_train_single_test_ic、best_single 只用 test 段；delta＝兩 test IC 相減；delta_ci95 成對重抽樣。"""
    V = X[list(survivors)].to_numpy(dtype=float)
    fin = np.isfinite(V).all(axis=1) & np.isfinite(y)
    rtr, rte = tr & fin, te & fin
    Vtr, Vte, ytr, yte = V[rtr], V[rte], y[rtr], y[rte]
    tic = {n: _sp(Vtr[:, j], ytr) for j, n in enumerate(survivors)}
    teic = {n: _sp(Vte[:, j], yte) for j, n in enumerate(survivors)}
    signs = {n: float(np.sign(v)) for n, v in tic.items() if math.isfinite(v) and np.sign(v) != 0}
    excluded = {n: "zero_train_ic" for n in survivors if n not in signs}
    kept = [n for n in survivors if n in signs]
    if p.weights_method == "equal":
        weights = {n: 1.0 / len(kept) for n in kept}
    else:
        tot = float(sum(abs(tic[n]) for n in kept))
        weights = {n: abs(tic[n]) / tot for n in kept}

    def comp(Vm: np.ndarray) -> np.ndarray:
        return np.sum(np.column_stack([weights[n] * signs[n] * _ref_nscore(Vm[:, survivors.index(n)]) for n in kept]), axis=1)

    c_te, c_tr = comp(Vte), comp(Vtr)
    cic, cic_tr = _sp(c_te, yte), _sp(c_tr, ytr)
    top = max(kept, key=lambda n: (abs(tic[n]), -survivors.index(n)))
    fin_te = {n: v for n, v in teic.items() if math.isfinite(v)}
    best = max(fin_te, key=lambda n: (abs(fin_te[n]), -survivors.index(n))) if fin_te else None
    delta = cic - teic[top] if math.isfinite(cic) and math.isfinite(teic[top]) else math.nan
    ci = _ref_block_ci(lambda c, f, yy: _sp(c, yy) - _sp(f, yy), (c_te, Vte[:, survivors.index(top)], yte),
                       p.block_len, p.n_bootstrap, p.seed)
    return {"status": "ok", "reason": None, "method": p.weights_method, "weights": weights, "signs": signs,
            "excluded": excluded, "composite_ic": _none_if_nan(cic), "composite_ic_train_insample": _none_if_nan(cic_tr),
            "top_train_single": top, "top_train_single_test_ic": _none_if_nan(teic[top]),
            "best_single_test_ic": _none_if_nan(fin_te[best]) if best is not None else None, "best_single_feature": best,
            "delta_vs_top_train_single": _none_if_nan(delta), "delta_ci95": ci, "n_used_test": int(rte.sum()),
            "n_used_train": int(rtr.sum()), "fit_scope": "train", "oos_guarantees": None}


MARGINAL_SURVIVORS = ["a", "b", "c", "d"]
MARGINAL_EXTRA = ["e_sparse", "e_dup"]


def _marginal_inputs() -> Any:
    """明列邊界輸入：160 根、前 100 根 train／後 60 根 test（時間切分）；a、b 部分共線、c 含同值、d 穿插 NaN（逐候選有限列
    過濾）、標籤穿插 NaN；移除候選 e_sparse（有限列不足 ⇒ insufficient_rows）、e_dup＝a 之複本（對含 a 之條件集殘差退化
    ⇒ residual_degenerate）。"""
    i = np.arange(160, dtype=float)
    a = np.sin(i / 4.0) + 0.01 * ((7 * i) % 11)
    sparse = np.full(i.size, np.nan)
    sparse[::9] = np.cos(i[::9])
    X = pd.DataFrame({"a": a, "b": 0.6 * a + 0.4 * np.cos(i / 3.0), "c": ((5 * i) % 17) - 8.0 + 0.001 * i,
                      "d": np.cos(i / 6.5), "e_sparse": sparse, "e_dup": a.copy()})
    X.loc[[12, 40, 41, 130], "d"] = np.nan
    y = 0.3 * a - 0.025 * X["c"].to_numpy() + 0.25 * np.sin(i / 2.2) + 0.1 * np.cos(i / 1.7)
    y[[7, 90]] = np.nan
    return X, pd.Series(y, name="label"), i < 100, i >= 100


def _run_marginal(X: pd.DataFrame, y: pd.Series, tr: np.ndarray, te: np.ndarray) -> Dict[str, Any]:
    return compute_marginal_ic(X, y, train_mask=tr, test_mask=te, survivors=list(MARGINAL_SURVIVORS),
                               extra_candidates=list(MARGINAL_EXTRA), params=MARGINAL_PARAMS, fit_scope="train").to_dict()


def test_marginal_ic_views_match_statsmodels_oracle() -> None:
    """邊際 IC 各欄（marginal_ic.py:222-236 序列化；per_feature、sequential、removed_candidates 三視角之 gross_ic、
    marginal_ic、ic_retained_ratio、marginal_ic_train_insample、ci95〔固定 seed〕、condition_number、r2_train、n_used_*、
    status／reason）== statsmodels OLS 投影＋scipy Spearman 之 oracle（相對誤差 ≤ 1e-12；None 精確比對）；含
    insufficient_rows 與 residual_degenerate 兩分支。"""
    X, y, tr, te = _marginal_inputs()
    got = _run_marginal(X, y, tr, te)
    exp = _ref_marginal(X, y.to_numpy(dtype=float), tr, te, MARGINAL_SURVIVORS, MARGINAL_EXTRA, MARGINAL_PARAMS)
    for key in ("per_feature", "sequential", "removed_candidates"):
        _assert_close_tree(got[key], exp[key], key)
    assert got["removed_candidates"]["e_sparse"]["reason"] == "insufficient_rows"
    assert got["removed_candidates"]["e_dup"]["reason"] == "residual_degenerate"
    assert all(v["status"] == "ok" for v in got["per_feature"].values()), "邊界輸入退化（前提失效）"
    assert got["n_train"] == int(tr.sum()) and got["n_test"] == int(te.sum())


def test_marginal_ic_train_ic_matches_scipy() -> None:
    """`marginal_ic.train_ic.<特徵>`（marginal_ic.py:394-405）鍵集合與值 == train 遮罩＋有限列之 `scipy.stats.spearmanr`；
    sequential 之順序 == 依 train_ic 之 (−|ic|，名) 重排；列數 < 2 ⇒ None（明列：train 段全 NaN 之特徵）。"""
    X, y, tr, te = _marginal_inputs()
    X = X.assign(z_nan=np.where(tr, np.nan, 1.0 + 0.1 * np.arange(len(X))))
    survivors = MARGINAL_SURVIVORS + ["z_nan"]
    got = compute_marginal_ic(X, y, train_mask=tr, test_mask=te, survivors=survivors, params=MARGINAL_PARAMS,
                              fit_scope="train").to_dict()
    exp = _ref_train_ic(X, y.to_numpy(dtype=float), tr, survivors)
    assert exp["z_nan"] is None
    _assert_close_tree(got["train_ic"], exp, "train_ic")
    order = sorted(survivors, key=lambda n: (-abs(exp[n]) if exp[n] is not None else 0.0, n))
    assert [e["feature"] for e in got["sequential"]] == order


@pytest.mark.parametrize("weights_method", ["equal", "ic_weighted"])
def test_marginal_ic_composite_matches_oracle(weights_method: str) -> None:
    """組合因子 `marginal_ic.composite` 逐欄（factor_combiner.py:126-133 序列化）== oracle：composite_ic_train_insample、
    top_train_single 只用 train 段；composite_ic、top_train_single_test_ic、best_single_* 只用 test 段；delta 為兩 test IC
    相減；delta_ci95 固定 seed 重抽樣。"""
    X, y, tr, te = _marginal_inputs()
    params = MarginalICParams(n_bootstrap=64, weights_method=weights_method)
    got = combine_factors(X, y, train_mask=tr, test_mask=te, survivors=list(MARGINAL_SURVIVORS), params=params,
                          fit_scope="train").to_dict()
    _assert_close_tree(got, _ref_composite(X, y.to_numpy(dtype=float), tr, te, MARGINAL_SURVIVORS, params))


def test_marginal_ic_train_fields_unaffected_by_test_segment() -> None:
    """無洩漏（SPEC Task 0.3「改動 test 段資料不影響 train 段各欄」）：只改 test 段之特徵與標籤（有限性不變之仿射與反序）⇒
    train_ic、sequential 順序、各候選之 marginal_ic_train_insample／r2_train／condition_number／n_used_train、組合之
    weights／signs／excluded／top_train_single／composite_ic_train_insample／n_used_train 皆 `==`；test 段欄確實改變（非空轉）。"""
    X, y, tr, te = _marginal_inputs()
    X2, y2 = X.copy(), y.copy()
    X2.loc[te, :] = X2.loc[te, :] * 1.7 + 0.3
    y2[te] = -y2[te].to_numpy() * 0.5 + 0.01
    a, b = _run_marginal(X, y, tr, te), _run_marginal(X2, y2, tr, te)
    assert a["train_ic"] == b["train_ic"]
    assert [e["feature"] for e in a["sequential"]] == [e["feature"] for e in b["sequential"]]
    for view in ("per_feature", "removed_candidates"):
        for f in a[view]:
            for k in ("marginal_ic_train_insample", "r2_train", "condition_number", "n_used_train", "conditioning_set"):
                assert a[view][f][k] == b[view][f][k], f"{view}/{f}/{k}：test 段改動影響 train 段欄"
    ca = combine_factors(X, y, train_mask=tr, test_mask=te, survivors=list(MARGINAL_SURVIVORS), params=MARGINAL_PARAMS,
                         fit_scope="train").to_dict()
    cb = combine_factors(X2, y2, train_mask=tr, test_mask=te, survivors=list(MARGINAL_SURVIVORS), params=MARGINAL_PARAMS,
                         fit_scope="train").to_dict()
    for k in ("weights", "signs", "excluded", "top_train_single", "composite_ic_train_insample", "n_used_train"):
        assert ca[k] == cb[k], f"composite/{k}：test 段改動影響 train 段欄"
    assert ca["composite_ic"] != cb["composite_ic"] and a["per_feature"]["a"]["marginal_ic"] != b["per_feature"]["a"]["marginal_ic"]


# ── 秒級 oracle 定義測試：summary_table.ic_mean 之來源切換（ic_mean_source） ───────────────────────────────


def _ref_rolling_spearman(x: np.ndarray, y: np.ndarray, window: int) -> List[float]:
    """滾動 IC 之測試自寫參考實作（stride 1、只用視窗內資料）：窗終點 window−1..n−1，窗內 `scipy.stats.spearmanr`（常數 ⇒
    NaN）；n < window ⇒ 空序列。"""
    return [_sp(x[e - window + 1:e + 1], y[e - window + 1:e + 1]) for e in range(window - 1, x.size)]


def _ref_ic_mean_source(X: pd.DataFrame, y: pd.Series, window: int) -> Any:
    """ic_mean 來源切換之 oracle（SPEC Task 0.3：ic_filter_orchestrator.py:4963-4974）：滾動 IC 均值（`_ref_rolling_spearman`
    之有限值平均；序列為空或全非有限 ⇒ NaN）有限 ⇒ 取之；否則 pooled 點 IC（scipy）有限 ⇒ 取之；皆否 ⇒ NaN、計 unavailable。"""
    aligned = pd.concat([X, y.rename("_y")], axis=1).dropna()
    yy = aligned["_y"].to_numpy(dtype=float)
    vals: Dict[str, float] = {}
    counts = {"rolling_mean": 0, "pooled_point_ic": 0, "unavailable": 0}
    for f in X.columns:
        roll = [v for v in _ref_rolling_spearman(aligned[f].to_numpy(dtype=float), yy, window) if math.isfinite(v)]
        rolling_mean = float(np.mean(roll)) if roll else math.nan
        pooled = _ic_oracle(X[f], y, "spearman")
        if math.isfinite(rolling_mean):
            vals[f], src = rolling_mean, "rolling_mean"
        elif math.isfinite(pooled):
            vals[f], src = pooled, "pooled_point_ic"
        else:
            vals[f], src = math.nan, "unavailable"
        counts[src] += 1
    return vals, counts


def _ic_mean_inputs(n: int) -> Any:
    """明列邊界輸入：正相關、負相關（ic_mean 為負；⑧ 後依 |ic_mean| 判，強負向應通過）、弱相關與常數特徵（滾動與 pooled 皆 NaN ⇒
    unavailable）；n＝200 ⇒ 63 窗有值，n＝50 ⇒ 滾動序列為空（SPEC 之邊界）⇒ 回退 pooled。"""
    i = np.arange(n, dtype=float)
    y = np.sin(i / 3.0) + 0.5 * np.cos(i / 1.3)
    X = pd.DataFrame({"pos": y + 0.8 * np.cos(i / 2.9), "neg": -y + 0.9 * np.sin(i / 1.9),
                      "weak": np.sin(i / 17.3 + 1.0) + 0.05 * y, "const": np.full(n, 3.0)})
    return X, pd.Series(y, name="label")


@pytest.mark.parametrize("n,expected_source", [(200, "rolling_mean"), (50, "pooled_point_ic")])
@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_ic_mean_source_fallback_matches_oracle(n: int, expected_source: str) -> None:
    """產品鏈 `compute_rolling_ic`→`compute_icir`→`compute_ic`→`_build_summary_table`（ic_filter_orchestrator.py:4942-5011）之
    `summary_table.ic_mean` 值、`_ic_mean_source` 來源計數與 `_apply_thresholds` 之 `ic_mean_min` 剔除集合（:5339-5341）==
    oracle 依同條件之切換（滾動序列為空之邊界：n＝50 < 窗 63）；同時以滾動參考實作對照滾動 IC 均值。"""
    X, y = _ic_mean_inputs(n)
    eng = ICEngine({})
    rolling = eng.compute_rolling_ic(X, y, [63])
    table_icir = eng.compute_icir(rolling)
    analyzer = create_ic_analyzer()
    table = analyzer._build_summary_table(list(X.columns), table_icir, {}, {}, {}, {}, {},
                                          point_ic=eng.compute_ic(X, y))
    exp_vals, exp_counts = _ref_ic_mean_source(X, y, 63)
    got_vals = {row["feature_name"]: row["ic_mean"] for row in table}
    _assert_close_tree(got_vals, exp_vals, "ic_mean")
    assert analyzer._ic_mean_source == exp_counts
    assert exp_counts[expected_source] == 3 and exp_counts["unavailable"] == 1, "邊界輸入未落預期來源（前提失效）"
    thr = analyzer._config.thresholds
    _, threshold_log = analyzer._apply_thresholds(table, thr, 0.05, fdr_enabled=False)
    # ICPERF Task 0.4 ⑧：ic_mean 門檻方向中立＝|ic_mean| ≥ ic_mean_min（強負向因子不再被剔除）
    exp_removed = sorted(f for f, v in exp_vals.items() if not (math.isfinite(v) and abs(v) >= thr.ic_mean_min))
    assert sorted(threshold_log["removed_features"]["ic_mean"]) == exp_removed
    assert set(exp_removed) not in (set(), set(X.columns)), "邊界輸入未使門檻兩側皆有（前提失效）"


# ── 秒級 oracle 定義測試：前綴不變性（防偷看未來） ──────────────────────────────────────────────────────


def _same(a: Any, b: Any) -> bool:
    return np.array_equal(np.asarray(a, dtype=float), np.asarray(b, dtype=float), equal_nan=True)


def _check_prefix_invariance(feats: pd.DataFrame, label: pd.Series, close: pd.Series, ks: Sequence[int]) -> None:
    """SPEC Task 0.3 防偷看未來：截去末 k 根後，前段之 PIT 分位標籤（q＝3、5）、PIT 排名、逐根換手時序、滾動 IC（spearman
    與 pearson，窗 21、63）與 regime 規則遮罩皆 `==`（NaN＝NaN；滾動序列為前段之全部窗終點）。"""
    eng = ICEngine({})
    for k in ks:
        n = len(feats) - k
        for col in feats.columns:
            x = feats[col]
            for q in (3, 5):
                assert _same(pit_expanding_qcut_label(x, q).to_numpy()[:n], pit_expanding_qcut_label(x.iloc[:n], q)), \
                    f"k={k}/{col}/q={q}：PIT 分位標籤前段改變"
            assert _same(pit_expanding_rank(x).to_numpy()[:n], pit_expanding_rank(x.iloc[:n])), f"k={k}/{col}：PIT 排名前段改變"
            full_ts = TurnoverAnalyzer({}).compute_turnover_time_series(x)
            pre_ts = TurnoverAnalyzer({}).compute_turnover_time_series(x.iloc[:n])
            for key in ("quantile_turnovers", "rank_change_rates", "timestamps"):
                assert full_ts[key][:n] == pre_ts[key], f"k={k}/{col}/{key}：逐根換手時序前段改變"
        for method in ("spearman", "pearson"):
            full = eng.compute_rolling_ic(feats, label, [21, 63], method=method)
            pre = eng.compute_rolling_ic(feats.iloc[:n], label.iloc[:n], [21, 63], method=method)
            for col in feats.columns:
                for w, values in pre[col].items():
                    assert _same(full[col][w][:len(values)], values), f"k={k}/{col}/{method}/{w}：滾動 IC 前段改變"
        full_m = eng._build_regime_rule_masks(close, GROUPED_CONFIG)
        pre_m = eng._build_regime_rule_masks(close.iloc[:n], GROUPED_CONFIG)
        for name in full_m:
            assert full_m[name].to_numpy()[:n].tolist() == pre_m[name].to_numpy().tolist(), f"k={k}/{name}：regime 遮罩前段改變"


def _late_bins_series(n: int = 450) -> pd.Series:
    """明列邊界輸入：前 150 根僅三種離散值（0／1／2；duplicates="drop" 使 PIT 分位不足 5 bin，實測前段最大標籤 2），其後為
    分散之連續值（PIT 分位漸得滿 5 bin，全序列最大標籤 4）——全序列 PIT 標籤最大值 > 前段最大值。"""
    i = np.arange(n, dtype=float)
    disc = np.where(i % 10 < 5, 0.0, np.where(i % 10 < 8, 1.0, 2.0))
    cont = 10.0 * np.sin(i * 0.7319) + 0.001 * i
    return pd.Series(np.where(i < 150, disc, cont), index=pd.date_range("2024-01-01", periods=n, freq="h", tz="UTC"),
                     name="late_bins")


@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_prefix_invariance_of_pit_series() -> None:
    """前綴不變性（明列輸入，k＝1、37）：第 5 段輸入形狀之特徵（`_stage5_inputs`）與分組輸入之收盤價；另對
    `_late_bins_series` 驗 PIT 標籤與排名本身前綴不變，且其全序列標籤最大值 > 截至第 150 根之最大值（下列 xfail 之前提）。"""
    feats, label = _stage5_inputs(360)
    _, _, close = _grouped_inputs(False)
    _check_prefix_invariance(feats, label, close.iloc[:360].set_axis(feats.index), (1, 37))
    s = _late_bins_series()
    full, pre = pit_expanding_qcut_label(s, 5).to_numpy(), pit_expanding_qcut_label(s.iloc[:150], 5).to_numpy()
    assert _same(full[:150], pre) and _same(pit_expanding_rank(s).to_numpy()[:150], pit_expanding_rank(s.iloc[:150]))
    assert np.nanmax(full) > np.nanmax(pre) and np.nanmax(pre) >= 1, "邊界輸入未使全序列最大標籤 > 前段（前提失效）"


# Task 0.3 稽核發現、SPEC Task 0.4 ① 已修：修正前逐根換手時序之頂分位以全序列 PIT 標籤最大值界定，後段新增之 bin 會改寫
# 前段每根之頂分位指示與換手值——截去後段即改變前段（偷看未來）；修正後截去後段前段不變。
def test_turnover_time_series_prefix_invariant_with_late_bins() -> None:
    """前綴不變性（同上）：`_late_bins_series` 截至第 150 根之逐根換手時序 == 全序列之前 150 根。"""
    s = _late_bins_series()
    full = TurnoverAnalyzer({}).compute_turnover_time_series(s)["quantile_turnovers"]
    pre = TurnoverAnalyzer({}).compute_turnover_time_series(s.iloc[:150])["quantile_turnovers"]
    assert full[:150] == pre, "逐根換手時序前段隨後段資料改變"


# ── 秒級 oracle 定義測試：跨標的路徑（cross_sectional） ──────────────────────────────────────────────────

XSEC_LABEL = "return_1"


def _ref_cross_symbol_validation(matrix: Mapping[str, Mapping[str, Any]], symbols: Sequence[str],
                                 features: Sequence[str]) -> Dict[str, Any]:
    """`cross_symbol_validation` 之測試自寫參考實作（SPEC Task 0.3：依 ic_filter_orchestrator.py:2446-2546 之公式）：各標的
    分數＝|IC| 平均；逐特徵（≥ 2 個有限值）方向一致度＝|Σsign|／k、離散度＝母體標準差、分數＝0.7·一致度＋0.3·max(0,
    1−min(離散度／0.1, 1))；一致性＝分數平均（無 ⇒ 0）；標的特有（最大 |IC| ≥ 0.02 且領先次大 ≥ 0.02）、通用（同向且 |IC| ≥
    0.015 之比例 ≥ 0.7）、方向衝突；建議依 0.7／0.4 門檻；標的 < 2 或無特徵 ⇒ skipped。"""
    if len(symbols) < 2 or not features:
        return {"status": "skipped", "reason": "insufficient_symbols_or_features", "consistency_score": None,
                "best_symbol": None, "worst_symbol": None, "symbol_scores": {},
                "suggestions": ["Symbol 或特徵數不足，無法進行跨 Symbol 一致性驗證"]}

    def finite(v: Any) -> bool:
        return isinstance(v, (int, float)) and math.isfinite(v)

    scores = {}
    for s in symbols:
        vals = [abs(float(matrix[f][s])) for f in features if finite(matrix[f].get(s))]
        if vals:
            scores[s] = float(np.mean(vals))
    feat_scores: List[float] = []
    conflict, specific, universal = [], [], []
    for f in features:
        vals = [float(matrix[f][s]) for s in symbols if finite(matrix[f].get(s))]
        if len(vals) < 2:
            continue
        sg = np.sign(np.asarray(vals))
        pos, neg = int(np.sum(sg > 0)), int(np.sum(sg < 0))
        if pos and neg:
            conflict.append(f)
        feat_scores.append(0.7 * abs(float(np.sum(sg))) / len(sg) + 0.3 * max(0.0, 1.0 - min(float(np.std(vals)) / 0.1, 1.0)))
        ab = sorted((abs(v) for v in vals), reverse=True)
        if ab[0] >= 0.02 and ab[0] - ab[1] >= 0.02:
            specific.append(f)
        if (pos == len(sg) or neg == len(sg)) and float(np.mean(np.abs(vals) >= 0.015)) >= 0.7:
            universal.append(f)
    consistency = float(np.mean(feat_scores)) if feat_scores else 0.0
    suggestions = ["跨 Symbol 一致性高，可優先納入聯合訓練候選" if consistency >= 0.7 else
                   "跨 Symbol 一致性中等，建議搭配 regime 條件做分組驗證" if consistency >= 0.4 else
                   "跨 Symbol 一致性偏弱，建議僅在特定 Symbol 場景使用"]
    if conflict:
        suggestions.append("部分因子在不同 Symbol 呈現方向衝突，需檢查市場結構差異")
    return {"status": "completed", "reason": None, "consistency_score": consistency,
            "best_symbol": max(scores, key=scores.get) if scores else None,
            "worst_symbol": min(scores, key=scores.get) if scores else None, "symbol_scores": scores,
            "feature_summary": {"total_features": len(features), "universal_features": len(universal),
                                "symbol_specific_features": len(specific), "sign_conflict_features": len(conflict)},
            "samples": {"universal_features": universal[:10], "symbol_specific_features": specific[:10],
                        "sign_conflict_features": conflict[:10]},
            "suggestions": suggestions}


def _ref_cross_sectional(df: pd.DataFrame, label_col: str = XSEC_LABEL) -> Dict[str, Any]:
    """跨標的路徑之 oracle（SPEC Task 0.3：`analyze_cross_sectional` 無 train／test 切分時，ic_filter_orchestrator.py:2208-2230、
    :2323-2329、:2392-2446）：每時點（≥ 2 標的）逐特徵以兩欄共同非 NaN 列（≥ 2）之 `scipy.stats.spearmanr` 得截面 IC 序列
    （NaN 不入）；ic_mean＝平均、ic_std＝母體標準差、ICIR、勝率；`cross_sectional_symbol_ic` 逐標的逐特徵以有限值遮罩加
    spearmanr（列數 < 2 或 NaN ⇒ None），特徵依 ICIR 遞減（非有限墊底、同值保序）；`cross_symbol_validation` 依參考實作。"""
    feats = [c for c in df.columns if c != label_col]
    series: Dict[str, List[float]] = {f: [] for f in feats}
    for _, g in df.groupby(level=0, sort=True):
        if len(g) < 2:
            continue
        y = g[label_col].to_numpy(dtype=float)
        for f in feats:
            x = g[f].to_numpy(dtype=float)
            m = ~np.isnan(x) & ~np.isnan(y)
            if m.sum() >= 2:
                v = _sp(x[m], y[m])
                if math.isfinite(v):
                    series[f].append(v)
    summary = {}
    for f in feats:
        v = np.asarray(series[f], dtype=float)
        if v.size == 0:
            summary[f] = {"ic_mean": math.nan, "ic_std": math.nan, "icir": math.nan, "ic_hit_rate": math.nan}
        else:
            mean, std = float(np.mean(v)), float(np.std(v))
            summary[f] = {"ic_mean": mean, "ic_std": std, "icir": mean / std if std > 0 else math.nan,
                          "ic_hit_rate": float(np.mean(v > 0))}
    # ICPERF Task 0.4 ⑧：預設排序＝icir_aligned＝direction·icir（direction＝sign(ic_mean)；0／NaN ⇒ icir_aligned NaN ⇒ 排末）
    def _aligned(f: str) -> float:
        mean, icir = summary[f]["ic_mean"], summary[f]["icir"]
        d = 0.0 if not math.isfinite(mean) else float(np.sign(mean))
        return d * icir if d != 0 and math.isfinite(icir) else -math.inf

    ranked = sorted(feats, key=_aligned, reverse=True)
    symbols = sorted(str(s) for s in df.index.get_level_values(1).unique())
    matrix: Dict[str, Dict[str, Optional[float]]] = {f: {} for f in ranked}
    for sym, g in df.groupby(level=1, sort=True):
        y = g[label_col].to_numpy(dtype=float)
        for f in ranked:
            x = g[f].to_numpy(dtype=float)
            m = ~np.isnan(x) & ~np.isnan(y)
            matrix[f][str(sym)] = None if m.sum() < 2 else _none_if_nan(_sp(x[m], y[m]))
    return {"series": series, "summary": summary,
            "symbol_ic": {"symbols": symbols, "features": ranked, "matrix": matrix},
            "validation": _ref_cross_symbol_validation(matrix, symbols, ranked)}


def _assert_cross_sectional(df: pd.DataFrame) -> Dict[str, Any]:
    """產品 `analyze_cross_sectional`（config_override 關 train／test 切分）之截面 IC 序列、summary 四欄、
    `cross_sectional_symbol_ic`、`cross_symbol_validation` == `_ref_cross_sectional`。回 oracle 供前提檢查。"""
    report = create_ic_analyzer().analyze_cross_sectional(df, config_override={"ic_train_test_split": False})
    exp = _ref_cross_sectional(df)
    for f, values in exp["series"].items():
        _assert_close_tree(report["rolling_ic_series"][f]["window_cross_sectional"], values, f"series/{f}")
    rows = {r["feature_name"]: r for r in report["summary_table"]}
    for f, fields in exp["summary"].items():
        _assert_close_tree({k: rows[f][k] for k in fields}, fields, f"summary/{f}")
    _assert_close_tree(report["cross_sectional_symbol_ic"], exp["symbol_ic"], "cross_sectional_symbol_ic")
    _assert_close_tree(report["cross_symbol_validation"], exp["validation"], "cross_symbol_validation")
    return exp


def _xsec_inputs() -> pd.DataFrame:
    """明列邊界輸入：5 標的 × 60 時點（MultiIndex timestamp、symbol）；f1 連續、f2 含同值與 NaN、f3 於 EEE 為常數（該格
    None）；第 10 時點只剩 1 標的（該截面跳過）；標籤 `return_1`（horizon 1）無 NaN。"""
    ts = pd.date_range("2024-03-01", periods=60, freq="h", tz="UTC")
    rows = []
    for t, stamp in enumerate(ts):
        for j, sym in enumerate(("AAA", "BBB", "CCC", "DDD", "EEE")):
            if t == 10 and j > 0:
                continue
            f1 = math.sin(t / 5.0 + j) + 0.1 * j
            f2 = math.nan if (t + j) % 13 == 0 else float(((3 * t + 7 * j) % 11) - 5)
            f3 = 1.5 if sym == "EEE" else math.cos(t / 4.0 + 0.5 * j)
            y = 0.01 * math.cos(t / 3.0 + 0.7 * j) + 0.002 * f1 - 0.001 * (f3 if sym != "EEE" else 0.0)
            rows.append((stamp, sym, f1, f2, f3, y))
    df = pd.DataFrame(rows, columns=["timestamp", "symbol", "f1", "f2", "f3", XSEC_LABEL])
    return df.set_index(["timestamp", "symbol"]).sort_index()


@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_cross_sectional_matches_oracle() -> None:
    """跨標的路徑（SPEC Task 0.3「跨標的欄」；明列輸入）：截面 IC 序列、summary、`cross_sectional_symbol_ic`（spearmanr 逐標的
    逐特徵）與 `cross_symbol_validation`（參考實作）== oracle；含單標的截面跳過、常數格 None。"""
    exp = _assert_cross_sectional(_xsec_inputs())
    assert exp["symbol_ic"]["matrix"]["f3"]["EEE"] is None and exp["validation"]["status"] == "completed"
    assert len(exp["series"]["f1"]) == 59, "邊界輸入未使單標的截面被跳過（前提失效）"


def _xsec_nan_ic_inputs() -> pd.DataFrame:
    """明列邊界輸入（截面 IC 為 NaN 之時點）：4 標的 × 40 時點；f1 於 t % 6 == 0 各標的同值（截面排名常數 ⇒ 該時點相關
    NaN），另含 +inf（t＝7、AAA）與 −inf（t＝13、BBB）；f2 於 t % 4 == 1 只剩 1 標的非 NaN（共同列 < 2 ⇒ 跳過）；
    t＝20 標籤各標的同值（該時點兩特徵相關皆 NaN）；標籤 `return_1`（horizon 1）無 NaN。"""
    ts = pd.date_range("2024-05-01", periods=40, freq="h", tz="UTC")
    rows = []
    for t, stamp in enumerate(ts):
        for j, sym in enumerate(("AAA", "BBB", "CCC", "DDD")):
            f1 = 0.5 if t % 6 == 0 else math.sin(t / 3.0 + 1.3 * j) + 0.05 * j
            if (t, sym) == (7, "AAA"):
                f1 = math.inf
            if (t, sym) == (13, "BBB"):
                f1 = -math.inf
            f2 = math.nan if (t % 4 == 1 and j > 0) else math.cos(t / 2.5 + 0.8 * j) + 0.02 * t
            y = 0.003 if t == 20 else 0.01 * math.cos(t / 2.0 + 0.9 * j)
            rows.append((stamp, sym, f1, f2, y))
    df = pd.DataFrame(rows, columns=["timestamp", "symbol", "f1", "f2", XSEC_LABEL])
    return df.set_index(["timestamp", "symbol"]).sort_index()


@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_cross_sectional_hit_rate_counts_finite_ic_only() -> None:
    """跨標的勝率之分母（ic_filter_orchestrator.py:2248，SPEC Task 0.4 ②）只計有限截面 IC：明列輸入含相關為 NaN 之時點
    與 ±inf 特徵值。現行 `analyze_cross_sectional` 建 `ic_series` 時已先濾除：:2224 `dropna()`、:2227-2229 先排名再
    pearson（排名恆有限 ⇒ 相關 ∈ [−1, 1] 或 NaN）、:2230 `if pd.notna(corr)` 才 append——故 :2248 之 `values` 恆有限、
    NaN 不可達該分母，現行即等於只計有限值之定義，照常斷言（不標 xfail）。本測試釘住此濾除：若移除 :2230 之 NaN 濾除，
    勝率分母含 NaN 時點而與 oracle 不同 ⇒ 紅（下列前提斷言兩者確有差異）。"""
    df = _xsec_nan_ic_inputs()
    exp = _assert_cross_sectional(df)
    report = create_ic_analyzer().analyze_cross_sectional(df, config_override={"ic_train_test_split": False})
    rows = {r["feature_name"]: r for r in report["summary_table"]}
    for f in ("f1", "f2"):
        n_nan = 0
        for _, g in df.groupby(level=0, sort=True):
            x, y = g[f].to_numpy(dtype=float), g[XSEC_LABEL].to_numpy(dtype=float)
            m = ~np.isnan(x) & ~np.isnan(y)
            n_nan += int(len(g) >= 2 and m.sum() >= 2 and not math.isfinite(_sp(x[m], y[m])))
        series = np.asarray(report["rolling_ic_series"][f]["window_cross_sectional"], dtype=float)
        assert np.isfinite(series).all(), f"{f}：截面 IC 序列含非有限值"
        assert n_nan >= 1, f"{f}：邊界輸入無 NaN 截面 IC 之時點（前提失效）"
        wins = float(np.sum(series > 0))
        assert 0 < wins < series.size and wins / (series.size + n_nan) != wins / series.size, f"{f}：前提失效"
        assert _rel(rows[f]["ic_hit_rate"], _finite_hit_rate(series)) == 0.0
        assert _rel(rows[f]["ic_hit_rate"], exp["summary"][f]["ic_hit_rate"]) == 0.0


# ── 真實 kline（requires_kline，秒級）：上列各組 oracle 於真實資料 ─────────────────────────────────────────
# 比對與 oracle 皆重用上列已以明列輸入驗過之 helper；只換輸入為 data_cache/feature_klines/kline_cache.h5 之真實小切片。


def _real_label(close: pd.Series, horizon: int = 1) -> pd.Series:
    """真實標籤：簡單報酬 close[t+h]／close[t]−1（label_generator.py:45-47）。"""
    return (close.shift(-horizon) / close - 1.0).rename("label")


def _real_features_wide(close: pd.Series) -> pd.DataFrame:
    """真實 kline 上之因果特徵（只用 0..t）：`_real_features` 兩欄加 20 根報酬波動率、10 根動量。"""
    ret = close.pct_change()
    return _real_features(close).assign(vol20=ret.rolling(20).std(), mom10=close / close.shift(10) - 1.0)


#: 真實特徵之明列 metadata（分組 IC 之 metadata 三種分組）
REAL_METADATA = {"ret1": {"category": "momentum", "data_source": "kline", "layer": "L1"},
                 "dev20": {"category": "mean_reversion", "data_source": "kline", "layer": "L1"}}


@pytest.mark.requires_kline
@pytest.mark.parametrize("method", sorted(_SCIPY))
def test_grouped_ic_matches_scipy_on_real_kline(method: str) -> None:
    """真實 BTCUSDT 1h 末 9,000 根（跨 2 個年度、≥ 4 個季度）：`compute_grouped_ic` 逐群組逐特徵 == scipy（同
    `test_grouped_ic_matches_scipy` 之 oracle；方法取引擎 methods[0]，設定為生產形狀）。"""
    close = _real_close(9000)
    feats, label = _real_features(close), _real_label(close)
    got = ICEngine({"methods": [method]}).compute_grouped_ic(feats, label, pd.DataFrame({"close": close}), REAL_METADATA,
                                                             dict(GROUPED_CONFIG))
    exp = _ref_grouped_ic(feats, label, close, REAL_METADATA, method)
    assert len(exp["by_year"]) >= 2 and len(exp["by_quarter"]) >= 4, "真實切片未跨年／季（前提失效）"
    _assert_close_tree(got, exp)


@pytest.mark.requires_kline
@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_stage5_pit_stats_match_reference_on_real_kline() -> None:
    """真實 BTCUSDT 1h 600 根：第 5 段逐特徵輸出（單調性含多空 t 值、換手之非頂分位欄、覆蓋）== 逐根 PIT 參考實作（同
    `test_stage5_pit_stats_match_reference`；頂分位兩欄見 `test_stage5_quantile_turnover_matches_per_bar_pit_reference_on_real_kline`）。"""
    close = _real_close()
    feats, label = _real_features_wide(close), _real_label(close)
    mono = MonotonicityTester({}).compute_all(feats, label)
    turn = TurnoverAnalyzer({}).compute_all(feats)
    cov = CoverageAnalyzer().compute_all(feats)
    for feat in feats.columns:
        _assert_close_tree(mono[feat], _ref_monotonicity(feats[feat], label), f"mono/{feat}")
        _assert_close_tree(_split_turnover(turn[feat])[1], _split_turnover(_ref_turnover(feats[feat]))[1], f"turnover/{feat}")
        _assert_close_tree(cov[feat], _ref_coverage(feats[feat]), f"coverage/{feat}")
    assert all(math.isfinite(mono[f]["long_short"]["tstat"]) for f in feats.columns), "真實切片之多空 t 非有限（前提失效）"


@pytest.mark.requires_kline
@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_stage5_quantile_turnover_matches_per_bar_pit_reference_on_real_kline() -> None:
    """真實 BTCUSDT 1h 600 根：頂分位兩欄 == 逐根 PIT 參考實作（同 `test_stage5_quantile_turnover_matches_per_bar_pit_reference`
    之 oracle）。真實連續特徵自首個有效根起逐根箱數 k_t 恆＝5（先斷言此前提），此時逐根定義與現行全序列最大標籤定義相同，
    故現行即一致、照常斷言（不標 xfail：strict xfail 於此會 XPASS）；前提若失效即以前提訊息失敗，改依合成輸入之 strict
    xfail 判讀。"""
    feats = _real_features_wide(_real_close())
    turn = TurnoverAnalyzer({}).compute_all(feats)
    for feat in feats.columns:
        lab, k = _ref_pit_qcut_bins(feats[feat].to_numpy(dtype=float), 5)
        assert (~np.isnan(lab)).any() and (k[~np.isnan(lab)] == 5).all(), f"{feat}：真實切片逐根箱數非恆為 5（前提失效）"
        _assert_close_tree(_split_turnover(turn[feat])[0], _split_turnover(_ref_turnover(feats[feat]))[0], f"turnover/{feat}")


@pytest.mark.requires_kline
@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_redundancy_correlation_matches_oracle_on_real_kline() -> None:
    """真實 BTCUSDT 1h 600 根：相關矩陣兩路徑（含 warmup NaN ⇒ 逐對 pearsonr；去 NaN 列 ⇒ numpy.corrcoef）== oracle。"""
    feats = _real_features_wide(_real_close())
    for df in (feats, feats.dropna()):
        got = RedundancyFilter({}).compute_correlation_matrix(df)
        exp = _ref_corr(df)
        for r, a in enumerate(df.columns):
            for c, b in enumerate(df.columns):
                assert _rel(float(got.loc[a, b]), float(exp[r, c])) <= REL_TOL, f"{a}/{b}：{got.loc[a, b]} vs {exp[r, c]}"


@pytest.mark.requires_kline
def test_marginal_ic_matches_oracle_on_real_kline() -> None:
    """真實 BTCUSDT 1h 600 根（前 360 根 train／後 240 根 test）：邊際 IC 三視角、train_ic 與組合因子 == oracle（同上列明列
    輸入之 oracle；倖存者＝四個真實因果特徵，移除候選無）。"""
    close = _real_close()
    X, y = _real_features_wide(close), _real_label(close)
    pos = np.arange(len(X))
    tr, te = pos < 360, pos >= 360
    survivors = list(X.columns)
    got = compute_marginal_ic(X, y, train_mask=tr, test_mask=te, survivors=survivors, params=MARGINAL_PARAMS,
                              fit_scope="train").to_dict()
    exp = _ref_marginal(X, y.to_numpy(dtype=float), tr, te, survivors, [], MARGINAL_PARAMS)
    for key in ("train_ic", "per_feature", "sequential"):
        _assert_close_tree(got[key], exp[key], key)
    comp = combine_factors(X, y, train_mask=tr, test_mask=te, survivors=survivors, params=MARGINAL_PARAMS,
                           fit_scope="train").to_dict()
    _assert_close_tree(comp, _ref_composite(X, y.to_numpy(dtype=float), tr, te, survivors, MARGINAL_PARAMS), "composite")


@pytest.mark.requires_kline
@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_prefix_invariance_on_real_kline() -> None:
    """真實 BTCUSDT 1h 600 根：截去末 1、50 根後前段之 PIT 標籤、排名、逐根換手時序、滾動 IC 與 regime 遮罩不變。"""
    close = _real_close()
    _check_prefix_invariance(_real_features_wide(close), _real_label(close), close, (1, 50))


def _real_cross_sectional_frame(rows: int = 400) -> pd.DataFrame:
    """真實多標的 1h（kline_cache.h5 全部標的，各取末 rows 根）：MultiIndex (timestamp, symbol)，特徵 ret1、dev20，標籤
    `return_1`。"""
    import h5py

    assert KLINE_CACHE.is_file(), f"真實 kline 不存在：{KLINE_CACHE}"
    with h5py.File(KLINE_CACHE, "r") as f:
        symbols = sorted(k for k in f.keys() if not k.startswith("_") and f"{k}/1h/data" in f)
    frames = []
    for sym in symbols:
        close = _real_close(rows, sym)
        part = _real_features(close).assign(**{XSEC_LABEL: _real_label(close).to_numpy()})
        part.index = pd.MultiIndex.from_arrays([close.index, [sym] * len(close)], names=["timestamp", "symbol"])
        frames.append(part)
    return pd.concat(frames).sort_index()


@pytest.mark.requires_kline
@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_cross_sectional_matches_oracle_on_real_kline() -> None:
    """真實多標的（本機 kline_cache.h5 之 10 標的 1h 末 400 根；SPEC Task 0.3「本機可得之多標的真實資料發一次跨標的請求」）：
    截面 IC 序列、summary、`cross_sectional_symbol_ic`（spearmanr）與 `cross_symbol_validation`（參考實作）== oracle。"""
    df = _real_cross_sectional_frame()
    assert df.index.get_level_values("symbol").nunique() >= 2, "本機無多標的真實資料（SPEC：收據記未驗並白話報使用者）"
    exp = _assert_cross_sectional(df)
    assert exp["validation"]["status"] == "completed"


# ── Task 0.4 ⑧⑩：方向中立門檻、預設排序、深度模組開關 ─────────────────────────────────────────────────────────


def _summary_row(name: str, ic_mean: float, icir: float, hit: float, neg: float, qmeans: List[float],
                 spread: float) -> Dict[str, Any]:
    """明列 summary 列：方向欄由產品 `_direction_fields` 依同一 ic_mean／icir 序列結果導出。"""
    from momentum.Analysis.ic_filter_orchestrator import _direction_fields

    q = {f"Q{i + 1}": v for i, v in enumerate(qmeans)}
    return {"feature_name": name, "ic_mean": ic_mean, "icir": icir, "ic_hit_rate": hit, "p_value": 0.001,
            "p_value_adj": 0.001, "monotonicity_score": float(np.mean(np.diff(qmeans) > 0)), "long_short_spread": spread,
            "coverage": 1.0, **_direction_fields(ic_mean, {"icir": icir, "ic_hit_rate": hit, "ic_neg_rate": neg},
                                               {"quantile_mean_returns": q})}


def test_direction_neutral_thresholds_pass_strong_reverse_factor() -> None:
    """SPEC Task 0.4 ⑧ 驗收①：強反向因子（ic_mean −0.08、icir −0.8、方向對齊勝率 0.6、分位均值遞減）通過全部門檻且
    direction −1；其鏡像正向因子同樣通過；|ic_mean| 不足、方向對齊勝率不足、icir 與 ic_mean 異號者各被對應門檻剔除。"""
    orch = create_ic_analyzer(None)
    th = orch._config.thresholds
    rows = [
        _summary_row("rev", -0.08, -0.8, 0.40, 0.60, [0.004, 0.002, 0.0, -0.002, -0.004], -0.008),
        _summary_row("fwd", 0.08, 0.8, 0.60, 0.40, [-0.004, -0.002, 0.0, 0.002, 0.004], 0.008),
        _summary_row("weak", -0.01, -0.8, 0.40, 0.60, [0.004, 0.002, 0.0, -0.002, -0.004], -0.008),
        _summary_row("flip_hit", -0.08, -0.8, 0.60, 0.40, [0.004, 0.002, 0.0, -0.002, -0.004], -0.008),
        _summary_row("sign_clash", -0.08, 0.8, 0.40, 0.60, [0.004, 0.002, 0.0, -0.002, -0.004], -0.008),
    ]
    passed, log = orch._apply_thresholds(rows, th, 0.05)
    assert passed == ["rev", "fwd"], log
    assert rows[0]["direction"] == -1 and rows[0]["icir_aligned"] == pytest.approx(0.8)
    assert rows[0]["monotonicity_score_aligned"] == 1.0 and rows[0]["ic_hit_rate_aligned"] == 0.60
    removed = log["removed_features"] if "removed_features" in log else log
    flat = {k: v for k, v in removed.items() if isinstance(v, list)}
    assert "weak" in flat["ic_mean"] and "flip_hit" in flat["ic_hit_rate"] and "sign_clash" in flat["icir"]


def test_top_features_default_sort_is_direction_aligned() -> None:
    """SPEC Task 0.4 ⑧ 驗收⑤：`get_top_features` 預設排序鍵＝icir_aligned——± 同強度因子名次相鄰且相同強度、弱者在後、
    direction 0 者排最後；明示 sort_by="icir" 時照有號排序。"""
    orch = create_ic_analyzer(None)
    rows = [
        _summary_row("pos_strong", 0.08, 0.9, 0.6, 0.4, [0, 1, 2, 3, 4], 0.01),
        _summary_row("neg_strong", -0.08, -0.9, 0.4, 0.6, [4, 3, 2, 1, 0], -0.01),
        _summary_row("pos_weak", 0.03, 0.2, 0.55, 0.45, [0, 1, 2, 3, 4], 0.01),
        {**_summary_row("zero", 0.0, 0.5, 0.5, 0.5, [0, 1, 2, 3, 4], 0.0)},
    ]
    orch._report = {"summary_table": rows}
    names = [r["feature_name"] for r in orch.get_top_features(n=4)]
    assert set(names[:2]) == {"pos_strong", "neg_strong"} and names[2] == "pos_weak" and names[3] == "zero"
    signed = [r["feature_name"] for r in orch.get_top_features(n=4, sort_by="icir")]
    assert signed[-1] == "neg_strong"


def test_explicit_deep_module_request_overrides_named_preset() -> None:
    """SPEC Task 0.4 ⑩：intermediate preset（disabled_modules＝正交化、曝險）下，深度請求明示開正交化 ⇒ 該模組開啟並揭露於
    tier_module_overrides；未明示之曝險維持 preset 之關閉；custom preset 不受此規則影響。"""
    from momentum.Analysis.ic_filter_orchestrator import ICFilterOrchestrator

    orch = create_ic_analyzer(None)
    base = orch._apply_tier_config(orch._apply_config_override({"feature_tiers": {"active_preset": "intermediate"}}))
    assert base.factor_orthogonalization.enabled is False, "前提：intermediate preset 關閉正交化"
    cfg, changed = ICFilterOrchestrator._apply_explicit_module_requests(
        base, {"factor_orthogonalization": {"enabled": True}})
    assert cfg.factor_orthogonalization.enabled is True and cfg.factor_exposure.enabled is False
    assert changed == {"factor_orthogonalization": {"requested": True, "preset": False}}
    custom = orch._apply_tier_config(orch._apply_config_override({"feature_tiers": {"active_preset": "custom"}}))
    _, changed_custom = ICFilterOrchestrator._apply_explicit_module_requests(
        custom, {"factor_orthogonalization": {"enabled": not custom.factor_orthogonalization.enabled}})
    assert changed_custom == {}


# ── Task 0.4 ⑦：單調性分箱歷史只依特徵自身（未來缺標籤不得改變過去分箱） ─────────────────────────────────────────


@pytest.mark.parametrize("gap", [130, 200, 260])
def test_monotonicity_bins_prefix_invariant_to_future_label_gap(gap: int) -> None:
    """SPEC Task 0.4 ⑦：第 g 根標籤由有限改為 NaN（如缺價——其值取決於 g＋h 之價格）時，**每一根**之 PIT 分箱皆不變
    （分箱只依特徵 0..t；舊版自歷史剔除第 g 根，使 t ≥ g 各根之分箱改變，即 t ∈ [g, g＋h) 偷看未來），且單調性輸出與只在
    聚合時排除第 g 根之 oracle 相同。明列邊界輸入：確定性特徵（含同值）與標籤，320 根小時頻索引。"""
    n = 320
    idx = pd.date_range("2025-01-01", periods=n, freq="h", tz="UTC")
    i = np.arange(n, dtype=float)
    f = pd.Series(np.sin(i / 7.0) + 0.01 * ((i * 13) % 17), index=idx)
    y = pd.Series(0.002 * np.cos(i / 5.0) + 0.0005 * f.to_numpy(), index=idx)
    y_gap = y.copy()
    y_gap.iloc[gap] = np.nan
    mt = MonotonicityTester({})
    b0 = mt._assign_quantiles(mt._prepare_data(f, y), 5)
    b1 = mt._assign_quantiles(mt._prepare_data(f, y_gap), 5)
    pd.testing.assert_series_equal(b0, b1)
    assert b0.iloc[gap:].notna().any(), "邊界輸入退化：缺值根之後無分箱（前提失效）"
    _assert_close_tree(mt.compute_all(f.to_frame("f"), y_gap)["f"]["quantile_returns"],
                       _ref_monotonicity(f, y_gap)["quantile_returns"], "mono")


# ── Task 0.4 ④⑤⑨：滾動 IC 逐特徵獨立、樣本外整窗、全樣本退回之 kline 對齊 ───────────────────────────────────────

ROLL_WINDOWS = [21, 63]


def _ref_rolling(F: pd.DataFrame, y: pd.Series, window: int, method: str) -> Dict[str, List[float]]:
    """滾動 IC 之 oracle（SPEC Task 0.4 ④）：時間軸＝標籤有限之列；每窗每特徵獨立，窗內該特徵或標籤有任一非有限值、
    或任一為常數 ⇒ NaN；否則 scipy（spearmanr／pearsonr）。"""
    yv = y.reindex(F.index).to_numpy(dtype=float)
    rows = np.flatnonzero(np.isfinite(yv))
    X = F.to_numpy(dtype=float)
    out: Dict[str, List[float]] = {c: [] for c in F.columns}
    for end in range(window - 1, rows.size):
        sel = rows[end - window + 1:end + 1]
        yw = yv[sel]
        for j, c in enumerate(F.columns):
            xw = X[sel, j]
            if not (np.all(np.isfinite(xw)) and np.all(np.isfinite(yw))) or np.ptp(xw) == 0 or np.ptp(yw) == 0:
                out[c].append(math.nan)
            else:
                out[c].append(float(_SCIPY[method](xw, yw)[0]))
    return out


def _assert_rolling_equal(got: Mapping[str, Any], exp: Mapping[str, List[float]], window: int, tol: float) -> None:
    for c, vals in exp.items():
        g = got[c][f"window_{window}"]
        assert len(g) == len(vals), f"{c}/window_{window}：長度 {len(g)} vs oracle {len(vals)}"
        for i, (a, b) in enumerate(zip(g, vals)):
            assert _rel(float(a), float(b)) <= tol, f"{c}/window_{window}[{i}]：產品 {a} vs oracle {b}"


def _rolling_inputs() -> Any:
    """明列邊界輸入於真實 kline 索引（BTCUSDT 1h 末 400 根）：ret1、dev20（前 19 根暖機 NaN）、mom10，標籤 1 根前瞻報酬。"""
    close = _real_close(400)
    F = _real_features_wide(close)[["ret1", "dev20", "mom10"]].iloc[20:]
    return F, _real_label(close).reindex(F.index)


# Pearson 分支以累積和計，窗長 63 之捨入相對誤差實測量級 1e-13；以 1e-9 判一致（Spearman 分支 1e-12）
ROLL_TOL = {"spearman": REL_TOL, "pearson": 1e-9}


@pytest.mark.requires_kline
@pytest.mark.parametrize("method", ["spearman", "pearson"])
@pytest.mark.parametrize("case", ["all_finite", "feature_nan", "label_nan", "all_nan_column"])
@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_rolling_ic_per_feature_matches_scipy(method: str, case: str) -> None:
    """SPEC Task 0.4 ④：`ICEngine.compute_rolling_ic` 每特徵獨立、時間軸＝標籤有限之列——逐窗等於 scipy oracle；同請求內
    其他欄之缺值（含整欄全 NaN）不改變某特徵之輸出（與該特徵單獨計算逐位元相同）。邊界：全有值、單一特徵中段缺值、
    標籤中段缺值、另加一欄全 NaN。"""
    F, y = _rolling_inputs()
    if case == "feature_nan":
        F.iloc[150, 0] = np.nan
    elif case == "label_nan":
        y.iloc[120] = np.nan
    elif case == "all_nan_column":
        F = F.assign(dead=np.nan)
    engine = ICEngine({})
    got = engine.compute_rolling_ic(F, y, ROLL_WINDOWS, 1, method)
    for w in ROLL_WINDOWS:
        _assert_rolling_equal(got, _ref_rolling(F, y, w, method), w, ROLL_TOL[method])
    for c in ("dev20", "mom10"):
        alone = engine.compute_rolling_ic(F[[c]], y, ROLL_WINDOWS, 1, method)
        assert alone[c] == got[c], f"{c}：與單獨計算不同（受同請求其他欄影響）"
    assert any(math.isfinite(v) for v in got["dev20"]["window_63"]), "邊界輸入退化（前提失效）"


@pytest.mark.requires_kline
@pytest.mark.parametrize("method", ["spearman", "pearson"])
@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_rolling_ic_test_slice_keeps_whole_test_windows_only(method: str) -> None:
    """SPEC Task 0.4 ④⑨：`_slice_rolling_ic_to_test` 以同一時間軸（標籤有限之列）判窗，只留窗首與窗尾皆在測試段之窗，
    值逐窗等於 oracle；窗跨入訓練段者不入。邊界：測試段＝末 150 列、標籤於測試段中段缺一根。"""
    F, y = _rolling_inputs()
    y.iloc[len(y) - 60] = np.nan
    test_mask = np.zeros(len(F), dtype=bool)
    test_mask[-150:] = True
    orch = create_ic_analyzer(None)
    full = orch._ic_engine.compute_rolling_ic(F, y, ROLL_WINDOWS, 1, method)
    sliced = orch._slice_rolling_ic_to_test(full, F, y, ROLL_WINDOWS, 1, test_mask)
    for w in ROLL_WINDOWS:
        Ft, yt = F.loc[test_mask], y.loc[test_mask]
        _assert_rolling_equal(sliced, _ref_rolling(Ft, yt, w, method), w, ROLL_TOL[method])
    n_axis_test = int(np.isfinite(y.loc[test_mask].to_numpy(dtype=float)).sum())
    assert len(sliced["ret1"]["window_63"]) == n_axis_test - 63 + 1


@pytest.mark.requires_kline
@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_full_sample_fallback_aligns_raw_kline_to_features() -> None:
    """SPEC Task 0.4 ⑤：mask 為 None 時 `_slice_raw_data_by_mask` 依時間軸對齊至特徵索引——整段 RangeIndex kline（含特徵窗外
    之列）對齊後之 close 逐根等於特徵索引上之真實 close；衰減逐 horizon IC 因而等於 scipy oracle。"""
    from momentum.Analysis.ic_filter_orchestrator import _slice_raw_data_by_mask

    close = _real_close(700)
    F = _real_features_wide(close).iloc[-300:]
    raw = pd.DataFrame({"timestamp": (close.index.asi8 // 10 ** 9).astype("int64"), "close": close.to_numpy()})
    aligned = _slice_raw_data_by_mask(raw, F, F, None)
    assert list(aligned.index) == list(F.index)
    np.testing.assert_array_equal(aligned["close"].to_numpy(dtype=float), close.reindex(F.index).to_numpy(dtype=float))
    decay = ICEngine({}).compute_ic_decay(F, aligned["close"], [1, 5], "spearman", "simple")
    for c in F.columns:
        for h, got in zip([1, 5], decay[c]["ic_values"]):
            r = (aligned["close"].shift(-h) / aligned["close"] - 1.0).to_numpy(dtype=float)
            assert _rel(float(got), _ic_oracle(F[c].to_numpy(dtype=float), r, "spearman")) <= REL_TOL, (c, h)
