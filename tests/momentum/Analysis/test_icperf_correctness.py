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
#: SPEC Task 0.3「驗證」：浮點對照之相對誤差門檻（直接統計量）
REL_TOL = 1e-12
#: SPEC v5.39 Task 0.3 ④ 分級判準：經最小平方或自相關累積之衍生量（封閉清單 `DERIVED_FIELD_PATTERNS`）之相對誤差門檻；
#: 清單外一律 `REL_TOL`；判定欄（旗標、trend 標籤、通過與否等非浮點欄）恆以 `==` 比。收據工具 `Tally`、本檔一致判準
#: （`_assert_close_tree`、收據測試）與深度測試檔 `compare_*`（含 p 值規則）三處皆經 `rel_tol_for` 取同一判準。
DERIVED_REL_TOL = 1e-9
#: 衍生量之封閉清單（SPEC v5.39 ④：趨勢分析各維之斜率、p 值、t 值、尾端估計、r_squared；品質診斷之有效樣本比與自相關
#: 衍生欄〔Ljung–Box 統計量與 p 值〕）。路徑形式：收據涵蓋鍵（`/results/<模組>/…`）、深度測試檔欄位（`<模組>/…`，可帶
#: `@<端到端項>` 尾綴）；特徵段為 `*` 或特徵名。
DERIVED_FIELD_PATTERNS = (
    r"(^|/)trend_analysis/[^/]+/[a-z_]+_trend/(slope|p_value|t_value|t_stat|tail_estimate|r_squared)(@[a-z_]+)?$",
    r"(^|/)feature_quality_diagnostics/autocorrelation_results/[^/]+/(effective_sample_ratio|ljungbox_stat|p_value)$",
)


def tolerance_class(path: Any) -> str:
    """欄位路徑之判準類別（SPEC v5.39 ④）：命中 `DERIVED_FIELD_PATTERNS` ⇒ "derived"，否則 "direct"。"""
    return "derived" if any(re.search(p, str(path)) for p in DERIVED_FIELD_PATTERNS) else "direct"


def rel_tol_for(path: Any) -> float:
    """欄位路徑之浮點相對誤差門檻（衍生量 `DERIVED_REL_TOL`、其餘 `REL_TOL`）。"""
    return DERIVED_REL_TOL if tolerance_class(path) == "derived" else REL_TOL


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
SPEC_PATH = REPO / "docs" / "ICPERF_SPEC.md"
RECEIPT_TOOL = REPO / "scripts" / "icperf_correctness_receipt.py"
#: SPEC v5.39 ⑦：收據 coverage 每鍵之狀態只准五態＋非統計欄（未逐值對照之統計鍵不另立狀態，列入 FAIL 原因）
COVERAGE_STATES = {"verified", "verified-na", "unimplemented", "metadata-missing", "insufficient-data", "non-stat"}


def _spec_version_of(text: Any) -> Optional[str]:
    """版本號：含 SPEC 版本行（`版本：v<主>.<次>`）者取該行之號，否則取首個 `v<主>.<次>`（收據 spec 欄
    `docs/ICPERF_SPEC.md v5.39 …`）；皆無 ⇒ None。"""
    s = str(text or "")
    m = re.search(r"版本：v(\d+\.\d+)", s) or re.search(r"\bv(\d+\.\d+)\b", s)
    return m.group(1) if m else None


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
    # SPEC v5.39 ⑪：收據 spec 欄之版本號＝SPEC 首個版本行（不寫死）；④：衍生量門檻同本檔
    assert _spec_version_of(receipt.get("spec")) == _spec_version_of(SPEC_PATH.read_text(encoding="utf-8")), \
        f"收據 spec 欄 {receipt.get('spec')!r} 與 SPEC 現行版本不符"
    assert receipt["tolerance"].get("derived_relative") == DERIVED_REL_TOL, "收據須記衍生量判準（SPEC v5.39 ④）"
    items = receipt["items"]
    assert REQUIRED_ITEMS <= set(items), f"收據缺 SPEC 最少項：{sorted(REQUIRED_ITEMS - set(items))}"
    module = sys.modules[__name__]
    for iid, it in items.items():
        assert it["verdict"] in VERDICTS, f"{iid}：verdict {it['verdict']!r} 非法"
        assert str(it.get("oracle") or "").strip(), f"{iid}：缺 oracle 說明"
        if it["verdict"] == "一致":
            # SPEC v5.39 ④ 分級判準：直接統計量 ≤ 1e-12、衍生量（封閉清單）≤ 1e-9（收據逐項分記兩類之最大相對誤差）
            d = it.get("max_rel_diff_direct", it.get("max_rel_diff"))
            assert d is None or (isinstance(d, (int, float)) and 0 <= d <= REL_TOL), f"{iid}：一致而直接統計量相對誤差 {d} > 1e-12"
            dd = it.get("max_rel_diff_derived")
            assert dd is None or (isinstance(dd, (int, float)) and 0 <= dd <= DERIVED_REL_TOL), \
                f"{iid}：一致而衍生量相對誤差 {dd} > 1e-9"
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
    # SPEC v5.39 ⑦：逐請求 coverage 之狀態 ⊆ 五態＋非統計欄；未逐值對照之統計鍵須逐鍵列入 fail_reasons
    for rid, req in (receipt.get("requests") or {}).items():
        for key, rec in (req.get("coverage") or {}).items():
            assert rec.get("status") in COVERAGE_STATES, f"{rid}{key}：狀態 {rec.get('status')!r} 不在 SPEC 五態＋非統計欄"
            if rec.get("uncompared"):
                assert any(f"{rid}" in r and key in r for r in receipt.get("fail_reasons") or []), \
                    f"{rid}{key}：未逐值對照之統計鍵須逐鍵列入 fail_reasons"


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


def _coverage_keys(raw: Mapping[str, Any], feature_names: Optional[Sequence[str]] = None) -> Set[str]:
    """涵蓋鍵：回應欄位路徑去 `#values`／`#index` 尾綴，特徵名段→`*`、list 索引段→`#`（特徵名取 `feature_names`；未給
    ⇒ summary_table 之 feature_name）。與收據工具 `coverage_keys`（凍結腳本 `flatten_fields`）為兩條獨立之抽取規則
    （SPEC v5.39 ⑧：逐請求封閉以本規則重算比對）。"""
    if feature_names is not None:
        feats = {_ptr(f) for f in feature_names}
    else:
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
    # SPEC v5.39 ⑧：逐請求封閉——收據全部請求之擷取檔，各以本檔之獨立抽取（`_paths`）重算實際回應鍵集合 == 收據該請求
    # coverage 鍵集合（擷取檔缺 ⇒ FAIL）
    cap_dir = Path(str((receipt.get("data") or {}).get("captures") or ""))
    requests = receipt.get("requests") or {}
    assert requests, "收據無逐請求 coverage"
    for rid, req in sorted(requests.items()):
        pkl = cap_dir / f"{rid}.pkl"
        assert pkl.is_file(), f"{rid}：擷取檔不存在 {pkl}（逐請求封閉須涵蓋全部請求之擷取檔）"
        with open(pkl, "rb") as fh:
            cap = pickle.load(fh)
        names = _capture_feature_names(fb, cap)
        got = _coverage_keys(cap["response"], names)
        cov = set(req.get("coverage") or {})
        assert got == cov, f"{rid}：獨立抽取之回應鍵未入 coverage {sorted(got - cov)[:10]}；coverage 多記 {sorted(cov - got)[:10]}"


def _capture_feature_names(fb: Any, cap: Mapping[str, Any]) -> List[str]:
    """擷取檔所指請求之特徵名全集（特徵段 → `*` 之依據）：跨標的＝各格 run 特徵之聯集與 `cross_df` 之欄；其餘＝該 run 之特徵
    （凍結腳本 `_run_feature_names`，讀 run 之特徵清單；不經涵蓋鍵抽取）。"""
    req = cap["request"]
    names: Set[str] = set()
    if req.get("kind") in ("cross", "cross_kline"):
        for cell in req.get("cells") or []:
            names |= set(fb._run_feature_names(cell))
        df = cap.get("cross_df")
        if df is not None:
            names |= {str(c) for c in df.columns}
        return sorted(names)
    return list(fb._run_feature_names(req))


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
    """巢狀 dict／list 逐葉比對：鍵集合相同、float 相對誤差 ≤ 1e-12（NaN＝NaN）、None 與其餘型別 `==`（None 不得視為 0）。
    本 helper 只用於直接統計量之秒級對照（SPEC v5.39 ④ 衍生量封閉清單之欄不經此處）。"""
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


# SPEC Task 0.4 ㉘：Pearson 分支改窗內中心化動差後與 scipy.stats.pearsonr 相對誤差 ≤ 1e-12（同 Spearman 分支；舊版以原值
# 累積和計而放寬至 1e-9）
ROLL_TOL = {"spearman": REL_TOL, "pearson": REL_TOL}


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


# ── Task 0.3 真實資料收據之綁定測試（收據項 `tests` 須為本檔實存之測試；scripts/icperf_correctness_receipt.py
#    `EXTRA_ITEM_TESTS`）：標籤、滾動窗邊界與深度十模組／regime_robust 之秒級 oracle 測試（後者執行各模組測試檔之明列輸入
#    oracle 測試，oracle 本體在該檔） ───────────────────────────────────────────────────────────────────────────


@pytest.mark.requires_kline
@pytest.mark.parametrize("return_type", ["simple", "log"])
@pytest.mark.parametrize("horizon", [1, 5])
def test_label_matches_float64_kline_oracle_on_real_kline(return_type: str, horizon: int) -> None:
    """收據項 label（SPEC Task 0.4 ⑥）：第 2 段之 K 線讀入（`_read_klines_float64`）價格欄為 float64 且逐值 == h5 原值；
    標籤（`LabelGenerator.generate_returns_by_type`）== close[t+h]／close[t]−1（log ⇒ ln 比值）之 float64 oracle（相對誤差
    ≤ 1e-12；末 h 根 NaN）。真實 BTCUSDT 1h。"""
    from momentum.Analysis.ic_filter_orchestrator import _read_klines_float64
    from momentum.factories import create_kline_storage_manager, create_label_generator

    raw = _read_klines_float64(create_kline_storage_manager(cache_dir=str(KLINE_CACHE.parent)), "BTCUSDT", "1h")
    assert raw["close"].dtype == np.float64
    close_h5 = _real_close(len(raw))
    np.testing.assert_array_equal(raw["close"].to_numpy(), close_h5.to_numpy())
    close = close_h5.iloc[-800:]
    got = create_label_generator().generate_returns_by_type(close, horizon, return_type).to_numpy(dtype=float)
    ratio = close.shift(-horizon).to_numpy(dtype=float) / close.to_numpy(dtype=float)
    exp = ratio - 1.0 if return_type == "simple" else np.log(ratio)
    assert np.isnan(got[-horizon:]).all() and np.isnan(exp[-horizon:]).all()
    for i, (a, b) in enumerate(zip(got[:-horizon], exp[:-horizon])):
        assert _rel(float(a), float(b)) <= REL_TOL, (i, a, b)


@pytest.mark.parametrize("method", ["spearman", "pearson"])
def test_rolling_ic_window_longer_than_axis_is_empty(method: str) -> None:
    """收據 verified-na 之明列邊界（SPEC Task 0.3 資料充足判準）：窗長 > 時間軸列數（標籤有限之列）⇒ 該窗之滾動 IC 序列為空
    （無窗終點），等於 oracle；窗長 ≤ 列數之窗照常有值。"""
    F, y = _rolling_inputs()
    n_axis = int(np.isfinite(y.to_numpy(dtype=float)).sum())
    got = ICEngine({}).compute_rolling_ic(F, y, [21, n_axis + 1], 1, method)
    for c in F.columns:
        assert got[c][f"window_{n_axis + 1}"] == [] == _ref_rolling(F, y, n_axis + 1, method)[c]
        assert len(got[c]["window_21"]) == n_axis - 21 + 1


# ── Task 0.3 真實資料收據之「不一致」項（照正確答案寫；裁定前 xfail(strict=True)，修正落 SPEC Task 0.4） ─────────


@pytest.mark.requires_kline
@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_rolling_ic_kendall_matches_kendalltau_xfail() -> None:
    """正確答案：method＝kendall 之滾動 IC 逐窗 == `scipy.stats.kendalltau`（同時間軸、窗內非有限或常數 ⇒ NaN；相對誤差
    ≤ 1e-12）。真實 BTCUSDT 1h 明列輸入（`_rolling_inputs`）。Task 0.3 收據 rolling_ic_icir（A.ic_report.kendall）之不一致
    已由 SPEC Task 0.4 ㉗ 修正（逐窗 Kendall τ-b），xfail 轉一般斷言（函式名沿用收據綁定）。"""
    F, y = _rolling_inputs()
    got = ICEngine({}).compute_rolling_ic(F, y, ROLL_WINDOWS, 1, "kendall")
    for w in ROLL_WINDOWS:
        _assert_rolling_equal(got, _ref_rolling(F, y, w, "kendall"), w, REL_TOL)


@pytest.mark.requires_kline
@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_rolling_ic_pearson_price_level_matches_scipy_xfail() -> None:
    """正確答案：Pearson 滾動 IC 逐窗 == `scipy.stats.pearsonr`（相對誤差 ≤ 1e-12），含價格水準之真實特徵（收盤、20 根均線）。
    Task 0.3 收據 rolling_ic_icir（A.ic_report.pearson）之不一致（原值累積和相消）已由 SPEC Task 0.4 ㉘ 修正（窗內中心化
    動差），xfail 轉一般斷言（函式名沿用收據綁定）。"""
    close = _real_close(400)
    F = pd.DataFrame({"close": close, "sma20": close.rolling(20).mean(), "ret1": close.pct_change()}).iloc[20:]
    y = _real_label(close).reindex(F.index)
    got = ICEngine({}).compute_rolling_ic(F, y, ROLL_WINDOWS, 1, "pearson")
    for w in ROLL_WINDOWS:
        _assert_rolling_equal(got, _ref_rolling(F, y, w, "pearson"), w, REL_TOL)


@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_point_ic_spearman_constant_label_returns_nan_xfail() -> None:
    """正確答案：標籤為常數（無缺值、多特徵）⇒ 每特徵 IC＝NaN（同 `_ic_oracle`：任一常數 ⇒ NaN；同 Pearson 分支），不得拋例外。
    Task 0.3 收據 extra_findings（向量化路徑 `corr[0, 1:]` TypeError）已由 SPEC Task 0.4 ㉚ 修正，xfail 轉一般斷言（函式名
    沿用收據綁定）。"""
    df = _point_inputs(False)
    label = pd.Series(np.full(len(df), 0.5), name="label")
    got = ICEngine({}).compute_ic(df[["a", "b"]], label, "spearman")
    assert set(got) == {"a", "b"} and all(math.isnan(float(v)) for v in got.values())
    assert all(math.isnan(_ic_oracle(df[c].to_numpy(dtype=float), label.to_numpy(dtype=float), "spearman")) for c in "ab")


@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_turnover_autocorrelation_constant_series_is_nan_xfail() -> None:
    """正確答案：常數特徵之 lag-1 自相關＝NaN（`_ref_turnover`：去 NaN 後任一半常數 ⇒ NaN，同 scipy.stats.pearsonr 之未定義），
    明列邊界：19 根同值之價格水準序列。Task 0.3 收據 stage5_pit_stats（L.event_import_report）之不一致已由 SPEC Task 0.4 ㉙
    修正，xfail 轉一般斷言（函式名沿用收據綁定）。"""
    x = pd.Series(np.full(19, 26767.52), index=pd.date_range("2026-02-24", periods=19, freq="4h", tz="UTC"), name="f")
    got = TurnoverAnalyzer({}).compute_all(x.to_frame())["f"]["autocorrelation"]
    assert math.isnan(_ref_turnover(x)["autocorrelation"])
    assert math.isnan(float(got)), f"常數序列自相關 {got!r}（應為 NaN）"


def _assert_graded(res: Mapping[str, Mapping[str, Any]]) -> None:
    """深度 compare_* 結果全一致，且逐欄最大相對誤差 ≤ 該欄之分級門檻（SPEC v5.39 ④：`rel_tol_for(欄位)`；直接統計量 1e-12、
    衍生量封閉清單 1e-9）——判準由欄位路徑決定，不得因任一欄落於 1e-9 內而放寬清單外之欄。"""
    bad = {k: v["detail"] for k, v in res.items() if v["verdict"] != "一致"}
    assert not bad, bad
    over = {k: v["max_rel_diff"] for k, v in res.items()
            if isinstance(v.get("max_rel_diff"), (int, float)) and math.isfinite(v["max_rel_diff"])
            and v["max_rel_diff"] > rel_tol_for(k.split("@", 1)[0]) and "@" not in k}
    assert not over, f"超過分級門檻之欄：{over}"


@pytest.mark.requires_kline
@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_fq_effective_sample_ratio_price_level_matches_oracle_xfail() -> None:
    """（Task 0.3 收據 deep.feature_quality_diagnostics 之捨入級差異；SPEC v5.39 ④ 分級判準定案後轉一般斷言，函式名沿用
    以免未立碑改名）
    `FeatureQualityDiagnostics.run_full_diagnostics` 之全部統計欄 == 模組 oracle（test_icperf_deep_quality_netic.py
    `compare_feature_quality_diagnostics`）：effective_sample_ratio 與 Ljung–Box 衍生欄屬衍生量封閉清單（相對 ≤ 1e-9；收據實測
    1e-12–5e-11，兩條獨立浮點路徑於近單位自相關輸入之累積捨入），其餘欄相對 ≤ 1e-12、判定欄（旗標）完全相同。真實
    BTCUSDT 1h 末 500 根之價格水準特徵（13 根均線之 5 根滾動最小、收盤、55 根 EMA）。"""
    from momentum.Analysis.feature_quality_diagnostics import FeatureQualityDiagnostics

    QN = _sibling("deep_quality_netic")
    close = _real_close(500)
    F = pd.DataFrame({"sma13min5": close.rolling(13).mean().rolling(5).min(), "close": close,
                      "dema": close.ewm(span=55).mean()}).dropna()
    res = QN.compare_feature_quality_diagnostics(FeatureQualityDiagnostics({}).run_full_diagnostics(F), F)
    _assert_graded(res)


@pytest.mark.requires_kline
@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_trend_four_dimensions_wide_real_kline_matches_oracle_xfail() -> None:
    """（Task 0.3 收據 deep.trend_analysis 之捨入級差異；SPEC v5.39 ④ 分級判準定案後轉一般斷言，函式名沿用以免未立碑改名）
    真實 BTCUSDT 1h 寬特徵集
    （動量／均線偏離／波動前 30 欄）經 `run_deep_analysis`（因子報酬、中心性、多空、趨勢四維）之 trend_analysis 逐欄 == 模組
    oracle（test_icperf_deep_centrality_trend.py `compare_trend_analysis`）：各維斜率／p 值／尾端估計／r_squared 屬衍生量封閉清單
    （相對 ≤ 1e-9；收據實測 1e-12–8e-11），trend 標籤等判定欄完全相同。"""
    from momentum.Analysis.ic_config_schema import ICConfig

    CT = _sibling("deep_centrality_trend")
    rolling_ic, names, idx = CT._real("BTCUSDT", wide=True)
    k = CT._load_kline("BTCUSDT", CT.REAL_ROWS)
    feats = CT._real_features(k, wide=True).loc[idx]
    label = (k["close"].shift(-1) / k["close"] - 1.0).rename("label").loc[idx]
    names = names[:30]
    rep = CT._deep_orchestrator(feats[names], label, rolling_ic, 1).run_deep_analysis(
        selected_features=names, force_modules=CT._FOUR)
    cfg = ICConfig()
    res = CT.compare_trend_analysis(rep.results["trend_analysis"], rolling_ic, names, cfg.trend_analysis.model_dump(),
                                    sources=CT._ref_trend_sources(rep, rolling_ic, names, cfg, 1),
                                    dimensions=list(cfg.trend_analysis.dimensions))
    _assert_graded(res)


def _sibling(name: str) -> Any:
    """同目錄之 ICPERF 測試檔（深度十模組、regime_robust 之 oracle 所在）。"""
    return sys.modules.get(f"icperf_cr_sib_{name}") or _load(f"icperf_cr_sib_{name}",
                                                             Path(__file__).with_name(f"test_icperf_{name}.py"))


#: 收據項 → 其 oracle 所在測試檔之明列輸入（秒級）oracle 測試（函式名）
SIBLING_ORACLE_TESTS: Dict[str, tuple] = {
    "factor_returns": ("deep_factor_return", ("test_factor_return_matches_oracle_explicit",
                                              "test_factor_return_skip_branches_match_oracle")),
    "long_short_analysis": ("deep_factor_return", ("test_long_short_matches_oracle_explicit",
                                                   "test_long_short_skip_and_edge_branches_match_oracle")),
    "factor_centrality": ("deep_centrality_trend", ("test_factor_centrality_skip_boundaries",
                                                    "test_crowding_triggers_under_default_threshold")),
    "trend_analysis": ("deep_centrality_trend", ("test_trend_analysis_matches_oracle",
                                                 "test_trend_analysis_honors_configured_dimensions")),
    "parameter_sensitivity": ("deep_sensitivity_oos", ("test_parameter_sensitivity_kendall_ic_equals_scipy_kendalltau",
                                                       "test_parameter_sensitivity_best_param_sign_flip_invariant")),
    "rolling_oos": ("deep_sensitivity_oos", ("test_rolling_oos_split_generation_matches_ref",
                                             "test_rolling_oos_kendall_method_uses_kendall_tau")),
    "factor_orthogonalization": ("deep_orth_exposure", ("test_gram_schmidt_accepts_production_icir_cache_shape",
                                                        "test_gram_schmidt_degenerate_flag_matches_oracle")),
    "factor_exposure": ("deep_orth_exposure", ("test_exposure_beta_neutral_matches_oracle_on_common_sample",
                                               "test_exposure_uses_valid_rows_mean")),
    "feature_quality_diagnostics": ("deep_quality_netic", ("test_fq_adf_coverage_matches_oracle_boundaries",
                                                           "test_fq_drift_psi_breakpoint_match_oracle_boundaries")),
    "net_ic_analysis": ("deep_quality_netic", ("test_net_ic_turnover_consistent_with_series",
                                               "test_average_daily_quote_volume_unit_boundaries")),
    "regime_robust": ("regime_robust", ("test_regime_robust_decision_matches_oracle_exact",
                                        "test_regime_robust_reason_closed_set")),
}


def _run_sibling(item: str) -> None:
    mod_name, names = SIBLING_ORACLE_TESTS[item]
    mod = _sibling(mod_name)
    for name in names:
        getattr(mod, name)()


@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_deep_factor_returns_oracle_suite() -> None:
    """收據項 deep.factor_returns 之綁定：test_icperf_deep_factor_return.py 之因子報酬明列輸入 oracle 測試。"""
    _run_sibling("factor_returns")


@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_deep_long_short_analysis_oracle_suite() -> None:
    """收據項 deep.long_short_analysis 之綁定：test_icperf_deep_factor_return.py 之多空明列輸入 oracle 測試。"""
    _run_sibling("long_short_analysis")


@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_deep_factor_centrality_oracle_suite() -> None:
    """收據項 deep.factor_centrality 之綁定：test_icperf_deep_centrality_trend.py 之中心性明列輸入 oracle 測試。"""
    _run_sibling("factor_centrality")


@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_deep_trend_analysis_oracle_suite() -> None:
    """收據項 deep.trend_analysis 之綁定：test_icperf_deep_centrality_trend.py 之趨勢明列輸入 oracle 測試。"""
    _run_sibling("trend_analysis")


@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_deep_parameter_sensitivity_oracle_suite() -> None:
    """收據項 deep.parameter_sensitivity 之綁定：test_icperf_deep_sensitivity_oos.py 之參數敏感度明列輸入 oracle 測試。"""
    _run_sibling("parameter_sensitivity")


@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_deep_rolling_oos_oracle_suite() -> None:
    """收據項 deep.rolling_oos 之綁定：test_icperf_deep_sensitivity_oos.py 之滾動樣本外明列輸入 oracle 測試。"""
    _run_sibling("rolling_oos")


@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_deep_factor_orthogonalization_oracle_suite() -> None:
    """收據項 deep.factor_orthogonalization 之綁定：test_icperf_deep_orth_exposure.py 之正交化明列輸入 oracle 測試。"""
    _run_sibling("factor_orthogonalization")


@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_deep_factor_exposure_oracle_suite() -> None:
    """收據項 deep.factor_exposure 之綁定：test_icperf_deep_orth_exposure.py 之曝險明列輸入 oracle 測試。"""
    _run_sibling("factor_exposure")


@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_deep_feature_quality_diagnostics_oracle_suite() -> None:
    """收據項 deep.feature_quality_diagnostics 之綁定：test_icperf_deep_quality_netic.py 之品質診斷明列輸入 oracle 測試。"""
    _run_sibling("feature_quality_diagnostics")


@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_deep_net_ic_analysis_oracle_suite() -> None:
    """收據項 deep.net_ic_analysis 之綁定：test_icperf_deep_quality_netic.py 之淨 IC 明列輸入 oracle 測試。"""
    _run_sibling("net_ic_analysis")


@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_regime_robust_oracle_suite() -> None:
    """收據項 regime_robust 之綁定：test_icperf_regime_robust.py 之秒級精確判定表與 reason 封閉值集。"""
    _run_sibling("regime_robust")


# ── Task 0.3 補足（SPEC v5.38 ①–⑤、v5.39 ⑦–⑪）：收據工具契約、名單類欄位之邊界證明、事件標籤與跨標的預設分支 ───────────


def _receipt_tool() -> Any:
    """收據工具模組（`scripts/icperf_correctness_receipt.py`；其 oracle 取本檔，故以獨立名載入）。"""
    return sys.modules.get("icperf_receipt_tool_t") or _load("icperf_receipt_tool_t", RECEIPT_TOOL)


def test_graded_tolerance_closed_list_and_mutation() -> None:
    """SPEC v5.39 ④ 分級判準：(i) 分類表——封閉清單內之衍生量（趨勢各維之斜率／p 值／尾端估計／r_squared、品質診斷之
    有效樣本比與 Ljung–Box 衍生欄，收據鍵與深度欄兩種路徑形式、含 `@` 端到端尾綴）為 1e-9，清單外（判定欄、中心性、ICIR、
    ADF p 值等）為 1e-12；(ii) 突變——同一欄相對偏差 1e-9 之內（×(1−ε)）判一致、之外（×(1+ε)）判不一致，直接統計量偏差
    5e-10 即判不一致；三處（收據 `Tally`、深度 compare_* 之數值／斜率／p 值規則、品質診斷 `_value_diff`）結果相同。"""
    derived = ["/results/trend_analysis/*/ic_trend/slope", "trend_analysis/*/centrality_trend/p_value@hac",
               "trend_analysis/f1/factor_return_trend/tail_estimate", "trend_analysis/*/ls_spread_trend/r_squared",
               "/results/feature_quality_diagnostics/autocorrelation_results/*/effective_sample_ratio",
               "feature_quality_diagnostics/autocorrelation_results/*/ljungbox_stat",
               "feature_quality_diagnostics/autocorrelation_results/*/p_value"]
    direct = ["trend_analysis/*/ic_trend/trend", "factor_centrality/features/*/centrality", "/summary_table/#/icir",
              "feature_quality_diagnostics/adf_results/*/p_value", "/rolling_ic_series/*/window_252",
              "feature_quality_diagnostics/autocorrelation_results/*/significant_autocorrelation"]
    assert all(rel_tol_for(p) == DERIVED_REL_TOL and tolerance_class(p) == "derived" for p in derived), \
        {p: rel_tol_for(p) for p in derived}
    assert all(rel_tol_for(p) == REL_TOL and tolerance_class(p) == "direct" for p in direct), {p: rel_tol_for(p) for p in direct}
    inside, outside = 1.0 + DERIVED_REL_TOL * (1 - 1e-3), 1.0 + DERIVED_REL_TOL * (1 + 1e-3)
    R = _receipt_tool()
    for key, factor, miss in (("/results/trend_analysis/*/ic_trend/slope", inside, 0),
                              ("/results/trend_analysis/*/ic_trend/slope", outside, 1),
                              ("/summary_table/#/icir", 1.0 + 5e-10, 1)):
        t = R.Tally("突變")
        t.num(key, key, 0.37 * factor, 0.37)
        assert t.n_mismatch == miss, (key, factor, t.n_mismatch)
    rec = R.Tally("類別")
    rec.num("/results/trend_analysis/*/ic_trend/slope", "a", 0.37 * inside, 0.37)
    rec.num("/summary_table/#/icir", "b", 0.5, 0.5)
    r = rec.record()
    assert r["max_rel_diff_derived"] > REL_TOL and r["max_rel_diff_direct"] == 0.0, r
    # 深度 compare_*：趨勢之數值／斜率／p 值規則與品質診斷 `_value_diff` 依欄位路徑取同一門檻
    CT, QN = _sibling("deep_centrality_trend"), _sibling("deep_quality_netic")
    for path, verdict_of in (("trend_analysis/*/ic_trend/tail_estimate",
                              lambda f, p: CT._verdict_numeric([("x", 0.37 * f, 0.37)], tol=CT._tol(p))["verdict"]),
                             ("trend_analysis/*/ic_trend/slope",
                              lambda f, p: CT._verdict_slope([("x", 0.37 * f, 0.37, math.nan)], tol=CT._tol(p))["verdict"]),
                             ("trend_analysis/*/ic_trend/p_value",
                              lambda f, p: CT._verdict_pvalue([("x", 0.037 * f, 0.037, math.nan, math.nan)],
                                                              tol=CT._tol(p))["verdict"]),
                             ("feature_quality_diagnostics/autocorrelation_results/*/effective_sample_ratio",
                              lambda f, p: "一致" if QN._value_diff(0.37 * f, 0.37, QN._tolerance_policy().rel_tol_for(p))[0]
                              else "不一致")):
        assert verdict_of(inside, path) == "一致" and verdict_of(outside, path) == "不一致", path
    assert CT._verdict_numeric([("x", 0.37 * (1 + 5e-10), 0.37)], tol=CT._tol("factor_centrality/features/*/centrality"))[
        "verdict"] == "不一致"
    assert not QN._value_diff(0.37 * (1 + 5e-10), 0.37, QN._tolerance_policy().rel_tol_for(
        "feature_quality_diagnostics/adf_results/*/adf_statistic"))[0]


def test_isolated_env_sets_numba_cache_inside_iso(tmp_path: Path) -> None:
    """SPEC v5.38 ⑤：凍結腳本 `isolated_env` 將 `NUMBA_CACHE_DIR` 設於隔離目錄內（覆寫呼叫端之值，如 conftest 之系統暫存），
    目錄已建立；TMPDIR／HOME 仍在隔離目錄、其餘鍵原樣（改壞對照：保留呼叫端之 NUMBA_CACHE_DIR ⇒ 不在 iso 之下）。"""
    fb = _load("icperf_freeze_baseline_t05", SCRIPT)
    iso = tmp_path / "iso"
    env = fb.isolated_env({"NUMBA_CACHE_DIR": "/tmp/qts_numba_cache", "PATH": "/usr/bin"}, iso)
    nb = Path(env["NUMBA_CACHE_DIR"]).resolve()
    assert nb.is_dir() and nb.is_relative_to(iso.resolve()), f"NUMBA_CACHE_DIR {nb} 不在隔離目錄 {iso} 之下"
    for k in ("TMPDIR", "HOME"):
        assert Path(env[k]).resolve().is_relative_to(iso.resolve())
    assert len({env["NUMBA_CACHE_DIR"], env["TMPDIR"], env["HOME"]}) == 3 and env["PATH"] == "/usr/bin"


def test_receipt_spec_version_read_from_spec() -> None:
    """SPEC v5.39 ⑪：收據工具之 spec 版本＝SPEC 首個版本行之號（不寫死；本檔獨立以 `_spec_version_of` 取）。"""
    R = _receipt_tool()
    assert R.spec_version() == "v" + str(_spec_version_of(SPEC_PATH.read_text(encoding="utf-8")))


def test_receipt_key_status_only_five_states_and_uncompared() -> None:
    """SPEC v5.39 ⑦：`key_status` 只出五態＋非統計欄；已對映 oracle 項而無逐值對照 ⇒ insufficient-data 且 `uncompared`
    （FAIL 原因逐鍵列出）；寫死佔位之鍵 ⇒ unimplemented；有內容 ⇒ verified；皆空且有明列邊界證明 ⇒ verified-na；皆空無證明
    ⇒ insufficient-data（非 uncompared）。"""
    R = _receipt_tool()
    t = R.Tally("x")
    t.num("/summary_table/#/icir", "a", 0.5, 0.5)
    t.eq("/marginal_ic/train_ic", "b", {}, {})
    t.eq("/grouped_ic/by_regime/high_vol", "c", {}, {})
    t.na("/grouped_ic/by_regime/high_vol", "test_grouped_ic_regime_without_rows_is_empty")
    items = {"x": t}
    cases = {"/summary_table/#/icir": ("verified", False), "/marginal_ic/train_ic": ("insufficient-data", False),
             "/grouped_ic/by_regime/high_vol": ("verified-na", False), "/summary_table/#/t_stat": ("insufficient-data", True)}
    for key, (state, unc) in cases.items():
        st = R.key_status(key, "x", items)
        assert st["status"] == state and bool(st.get("uncompared")) is unc, (key, st)
    assert R.key_status("/filter_log/x", NON_STAT, items)["status"] == "non-stat"
    # SPEC Task 0.4 ㊱ 後跨標的五欄已實算（`UNIMPLEMENTED` 為空）⇒ 未對照即 insufficient-data＋uncompared；
    # 寫死佔位之判定路徑以注入一條清單項驗（清單日後再出現佔位時同一路徑生效）
    for kind in ("cross", "cross_kline"):
        st = R.key_status("/summary_table/#/monotonicity_score", "x", items, kind=kind)
        assert st["status"] == "insufficient-data" and st.get("uncompared") is True, st
    saved = list(R.UNIMPLEMENTED)
    R.UNIMPLEMENTED[:] = [(r"^/summary_table/#/monotonicity_score$", ("cross", "cross_kline"), "x.py:1-1", "佔位")]
    try:
        for kind in ("cross", "cross_kline"):
            st = R.key_status("/summary_table/#/monotonicity_score", "x", items, kind=kind)
            assert st["status"] == "unimplemented" and st["reason"] == "x.py:1-1：佔位", st
        assert R.key_status("/summary_table/#/monotonicity_score", "x", items)["status"] == "insufficient-data"
    finally:
        R.UNIMPLEMENTED[:] = saved
    assert R.key_status("/summary_table/#/icir", "x", items, kind="cross")["status"] == "verified"
    assert set(R.COVERAGE_STATES) == COVERAGE_STATES
    per_req = {"r1": {"unmapped": [], "closure": {"closed": True}, "uncompared": ["/summary_table/#/t_stat"],
                      "coverage": {"/summary_table/#/monotonicity_score": {"status": "unimplemented", "reason": "佔位"}},
                      "facts": {}}}
    reasons = R.receipt_fail_reasons(per_req)
    assert any("r1" in s and "/summary_table/#/t_stat" in s for s in reasons), reasons
    assert any("unimplemented" in s and "monotonicity_score" in s for s in reasons), reasons


def test_receipt_unimplemented_anchors_hardcode_placeholders() -> None:
    """SPEC v5.39 ⑦：`UNIMPLEMENTED` 每條之產生處（檔:起訖行）確為寫死之佔位（None／空容器），非計算值。
    SPEC Task 0.4 ㊱ 實作跨標的五欄與相關／多元化後清單為空（其值改由 `test_icperf_xsec_placeholders.py` 之 oracle 驗）。"""
    R = _receipt_tool()
    for rx, kinds, prod, why in R.UNIMPLEMENTED:
        m = re.match(r"^([\w./-]+\.py):(\d+)-(\d+)$", prod)
        assert m, prod
        lines = (REPO / m.group(1)).read_text(encoding="utf-8").splitlines()[int(m.group(2)) - 1:int(m.group(3))]
        assert lines and all(re.search(r":\s*(None|\{\}|\{\"features\": \[\], \"matrix\": \[\]\})\s*,", ln) for ln in lines), \
            (prod, lines)


def test_receipt_closure_independent_of_coverage_extractor() -> None:
    """SPEC v5.39 ⑧：`closure_check` 以本檔 `_coverage_keys`（`_paths`，與收據工具 `coverage_keys`／凍結腳本 `flatten_fields`
    獨立）重算回應鍵：coverage 與之相同 ⇒ closed；coverage 漏一鍵（如 extractor 漏抽）或多記一鍵 ⇒ 不 closed 並列出。"""
    R = _receipt_tool()
    resp = {"summary_table": [{"feature_name": "f1", "icir": 0.1}, {"feature_name": "f2", "icir": None}],
            "rolling_ic_series": {"f1": {"window_21": [0.1, 0.2]}}, "grouped_ic": {"by_regime": {"high_vol": {}}},
            "metadata": {"warnings": []}}
    full = {k: None for k in _coverage_keys(resp, ["f1", "f2"])}
    assert R.closure_check(resp, ["f1", "f2"], full)["closed"]
    drop = dict(full)
    drop.pop("/rolling_ic_series/*/window_21")
    res = R.closure_check(resp, ["f1", "f2"], drop)
    assert not res["closed"] and res["missing"] == ["/rolling_ic_series/*/window_21"], res
    res = R.closure_check(resp, ["f1", "f2"], {**full, "/ghost": None})
    assert not res["closed"] and res["extra"] == ["/ghost"], res


def test_receipt_metadata_missing_on_default_or_unsourced_values() -> None:
    """SPEC v5.39 ⑨：任一特徵之 category／data_source／layer 為服務預設值（無來源欄）、或來源欄記為非持久化、或帶缺漏原因
    ⇒ 該欄之分組鍵 metadata-missing（by_layer 同）；三欄皆有持久化來源（含 layer＝1 之真值）⇒ 不判缺。"""
    R = _receipt_tool()
    t = R.Tally("g")
    t.num("/grouped_ic/by_layer/#/*", "a", 0.2, 0.2)
    persisted = {"a": {"category": "trend", "data_source": "kline", "layer": 1,
                       "metadata_source": {"category": "catalog", "data_source": "catalog", "layer": "catalog"}}}
    assert not any(R.metadata_missing_fields(persisted, ["a"]).values())
    # 路 F 之實際形狀（ic_analysis_service.py `_feature_metadata_entry`）：metadata_source 為字串、三欄同源
    by_name = {"a": {"category": "trend", "data_source": "close", "layer": "layer1", "metadata_source": "feature_name"}}
    assert not any(R.metadata_missing_fields(by_name, ["a"]).values())
    gone = {"a": {"category": None, "data_source": None, "layer": None, "metadata_source": "missing",
                  "metadata_missing_reason": "label_column"}}
    assert all(R.metadata_missing_fields(gone, ["a"])[f] for f in ("category", "data_source", "layer"))
    assert R.key_status("/grouped_ic/by_layer/#/*", "g", {"g": t},
                        meta_missing=R.metadata_missing_fields(persisted, ["a"]))["status"] == "verified"
    cases = [({"a": {"category": "trend", "data_source": "kline", "layer": 1}}, "layer", "/grouped_ic/by_layer/#/*"),
             ({"a": {"category": "unknown", "data_source": "kline", "layer": 2}}, "category", "/grouped_ic/by_category/unknown/*"),
             ({"a": {"category": "trend", "layer": 2}}, "data_source", "/grouped_ic/by_data_source"),
             ({"a": {**persisted["a"], "metadata_source": {**persisted["a"]["metadata_source"], "layer": "default"}}},
              "layer", "/diversification_metrics/layer_coverage"),
             ({"a": {**persisted["a"], "data_source_missing_reason": "catalog_missing"}}, "data_source",
              "/grouped_ic/by_data_source/kline/*")]
    for meta, field, key in cases:
        miss = R.metadata_missing_fields(meta, ["a"])
        assert miss[field] == {"a": miss[field]["a"]} and miss[field]["a"], (meta, miss)
        st = R.key_status(key, "g", {"g": t}, meta_missing=miss)
        assert st["status"] == "metadata-missing" and field in st["reason"], (key, st)


@pytest.mark.requires_kline
def test_deep_requests_include_complete_parameter_family() -> None:
    """SPEC v5.38 ②：兩深度請求之特徵子集依明列規則納入一組完整參數家族（名稱規則同產品自動偵測、成員數 ≥ 3、該 run 之
    全部成員），子集欄數 ≤ 深度 top_n（top_n 選取路徑選入全部欄）；請求定義記家族與成員。"""
    R = _receipt_tool()
    fb = _load("icperf_freeze_baseline_t02", SCRIPT)
    for rid in ("A.deep_analysis", "L.deep_analysis"):
        req = R.request_for(rid)
        fam = req["parameter_family"]
        names = set(req["feature_filter"]["include_features"])
        run = fb._run_feature_names(req)
        members = [n for n in run if re.match(rf"^{re.escape(fam['family'])}_(\d+)$", n)]
        assert len(members) >= 3 and set(members) == set(fam["members"]) <= names, (rid, fam, members)
        assert len(names) <= int(req["deep"]["top_n"]), (rid, len(names), req["deep"]["top_n"])


def test_marginal_ic_no_survivors_leaves_are_empty() -> None:
    """SPEC v5.38 ③（邊際 IC 空葉之明列邊界證明）：倖存者為空 ⇒ `compute_marginal_ic` 三視角與 train_ic 為空容器、狀態
    not_applicable／no_survivors；`combine_factors` 權重與符號為空 dict、組合 IC 等數值欄 None、使用列數 0（同收據工具
    `_evaluate_marginal_empty` 之 oracle）；對照組：倖存者非空 ⇒ 各葉非空（此空非恆常）。"""
    X, y, tr, te = _marginal_inputs()
    got = compute_marginal_ic(X, y, train_mask=tr, test_mask=te, survivors=[], params=MARGINAL_PARAMS,
                              fit_scope="train").to_dict()
    assert (got["status"], got["reason"]) == ("not_applicable", "no_survivors")
    assert got["per_feature"] == {} and got["sequential"] == [] and got["removed_candidates"] == {} and got["train_ic"] == {}
    comp = combine_factors(X, y, train_mask=tr, test_mask=te, survivors=[], params=MARGINAL_PARAMS,
                           fit_scope="train").to_dict()
    assert comp["weights"] == {} and comp["signs"] == {} and comp["n_used_test"] == 0 and comp["n_used_train"] == 0
    assert all(comp[k] is None for k in ("composite_ic", "composite_ic_train_insample", "top_train_single",
                                         "top_train_single_test_ic", "best_single_test_ic", "best_single_feature",
                                         "delta_vs_top_train_single", "delta_ci95"))
    full = compute_marginal_ic(X, y, train_mask=tr, test_mask=te, survivors=MARGINAL_SURVIVORS, params=MARGINAL_PARAMS,
                               fit_scope="train").to_dict()
    assert full["per_feature"] and full["train_ic"], "對照組：倖存者非空時各葉應非空"


def _decaying_vol_close(n: int = 420) -> pd.Series:
    """明列邊界輸入：日頻、報酬振幅指數遞減之確定性收盤（55 根滾動波動率逐根下降 ⇒ PIT 80 分位門檻恆高於當根 ⇒ 無 high_vol 根）。"""
    i = np.arange(n, dtype=float)
    ret = 0.03 * np.exp(-i / 120.0) * np.sin(i / 1.7) + 0.0002
    return pd.Series(100.0 * np.exp(np.cumsum(ret)), index=pd.date_range("2022-01-01", periods=n, freq="D", tz="UTC"),
                     name="close")


def test_grouped_ic_regime_without_rows_is_empty() -> None:
    """SPEC v5.38 ③（regime 空組之明列邊界證明；如 L 格測試段之 high_vol 0 列）：無任一根落入 high_vol ⇒ 產品
    `compute_grouped_ic` 之 `by_regime.high_vol` == {}，同 oracle `_ref_grouped_ic`（組內列數 0 ⇒ {}）；其餘 regime 非空。"""
    close = _decaying_vol_close()
    i = np.arange(len(close), dtype=float)
    feats = pd.DataFrame({"a": np.sin(i / 5.0), "b": np.cos(i / 3.1) + 0.001 * i}, index=close.index)
    label = (close.shift(-1) / close - 1.0).rename("label")
    masks = _ref_regime_masks(close)
    assert not masks["high_vol"].any() and masks["low_vol"].any(), "邊界輸入未使 high_vol 為空（前提失效）"
    got = ICEngine({"methods": ["spearman"]}).compute_grouped_ic(feats, label, pd.DataFrame({"close": close}), {},
                                                                 dict(GROUPED_CONFIG))
    exp = _ref_grouped_ic(feats, label, close, {}, "spearman")
    assert got["by_regime"]["high_vol"] == {} == exp["by_regime"]["high_vol"]
    _assert_close_tree(got["by_regime"], exp["by_regime"], "by_regime")


@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_deep_factor_exposure_concentration_warnings_boundaries() -> None:
    """SPEC v5.38 ③（曝險集中度警告名單之明列邊界證明；concentration 與 neutralized_concentration 同一
    `monitor_exposure_concentration`）：test_icperf_deep_orth_exposure.py `test_exposure_concentration_branches` 四分支
    （空、全 0、≥21 欄均分 ⇒ near_zero 警告、門檻內不警告）。"""
    mod = _sibling("deep_orth_exposure")
    for case in ("empty", "all_zero", "many_features", "below_threshold"):
        mod.test_exposure_concentration_branches(case)


@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_deep_fq_low_coverage_flag_boundaries() -> None:
    """SPEC v5.38 ③（品質診斷 low_coverage 旗標名單之明列邊界證明；真實資料 A／L 格全部欄覆蓋皆高於門檻 ⇒ 名單空）：
    test_icperf_deep_quality_netic.py `test_fq_flags_summary_match_oracle_when_all_tested`（前 100 根缺值之欄 ⇒ 入
    low_coverage、四旗標與摘要 == oracle）。"""
    _sibling("deep_quality_netic").test_fq_flags_summary_match_oracle_when_all_tested()


def test_deep_parameter_sensitivity_risk_lists_boundaries() -> None:
    """SPEC v5.38 ③（參數敏感度 high_risk／robust 名單之明列邊界證明）：test_icperf_deep_sensitivity_oos.py
    `test_parameter_sensitivity_risk_lists_with_thresholds`（門檻分出 high、名單 == oracle），另斷言同一輸入之 robust 名單非空。"""
    SO = _sibling("deep_sensitivity_oos")
    SO.test_parameter_sensitivity_risk_lists_with_thresholds()
    df, label, _ = SO._ps_inputs("base")
    ref0 = SO.ref_parameter_sensitivity(df, label, None, SO.PS_SMALL)
    stds = sorted(f["stability_metrics"]["ic_std_across_params"] for f in ref0["families"].values())
    cfg = {**SO.PS_SMALL, "ic_std_threshold_low": (stds[0] + stds[1]) / 2, "ic_std_threshold_high": (stds[1] + stds[2]) / 2}
    got = SO._run_ps(df, label, None, cfg)
    assert got["high_risk_families"] and got["robust_families"], got


@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_cross_symbol_validation_skipped_and_conflict_branches() -> None:
    """SPEC v5.38 ③（`cross_symbol_validation` 之 reason 與方向衝突名單之明列邊界證明）：(i) 單一標的 ⇒ skipped、reason
    非空；(ii) 兩標的之特徵方向相反 ⇒ sign_conflict_features 非空；兩者產品 == `_ref_cross_symbol_validation`。"""
    one = _xsec_inputs().xs("AAA", level="symbol", drop_level=False)
    rep1 = create_ic_analyzer().analyze_cross_sectional(one, config_override={"ic_train_test_split": False})
    exp1 = _ref_cross_symbol_validation({}, ["AAA"], [])
    assert rep1["cross_symbol_validation"]["status"] == "skipped" and rep1["cross_symbol_validation"]["reason"]
    assert rep1["cross_symbol_validation"]["reason"] == exp1["reason"]
    ts = pd.date_range("2024-03-01", periods=80, freq="h", tz="UTC")
    rows = []
    for t, stamp in enumerate(ts):
        for j, sym in enumerate(("AAA", "BBB", "CCC")):
            y = 0.01 * math.cos(t / 3.0 + 0.7 * j)
            f = (y if sym != "CCC" else -y) + 0.001 * math.sin(t + j)
            rows.append((stamp, sym, f, y))
    df = pd.DataFrame(rows, columns=["timestamp", "symbol", "f1", XSEC_LABEL]).set_index(["timestamp", "symbol"]).sort_index()
    exp = _assert_cross_sectional(df)
    assert exp["validation"]["samples"]["sign_conflict_features"] == ["f1"], exp["validation"]


@pytest.mark.requires_kline
def test_cross_sectional_label_float64_matches_kline_oracle_xfail() -> None:
    """（ICPERF Task 0.4 ㉞ 已修：收盤轉 float64 後計標籤；函式名保留供收據綁定）正確答案：跨標的標籤 return_1 == ln(close[t+1]／close[t])（kline_cache.h5 直接讀、float64；kline 全序列；相對誤差
    ≤ 1e-12），同主線標籤之 float64 定義（SPEC Task 0.4 ⑥）。真實 BTCUSDT／SOLUSDT 1h 末 300 根。"""
    from api.services.ic_analysis_service import ICAnalysisService

    df = _real_cross_sectional_frame(300)
    df = df[df.index.get_level_values("symbol").isin(["BTCUSDT", "SOLUSDT"])][["ret1", "dev20"]]
    df.index = df.index.set_names(["timestamp", "_symbol"])
    df.index = df.index.set_levels(df.index.levels[0].tz_localize(None), level=0)
    got = ICAnalysisService._append_cross_sectional_labels(None, df, ["BTCUSDT", "SOLUSDT"], "1h")  # type: ignore[arg-type]
    for sym in ("BTCUSDT", "SOLUSDT"):
        close = _real_close(20352, sym)
        exp = np.log(close.shift(-1) / close)
        g = got.xs(sym, level="_symbol")["return_1"]
        e = exp.reindex(pd.DatetimeIndex(g.index).tz_localize("UTC")).to_numpy(dtype=float)
        bad = [(i, a, b) for i, (a, b) in enumerate(zip(g.to_numpy(dtype=float), e)) if _rel(float(a), float(b)) > REL_TOL]
        assert not bad, f"{sym}：{len(bad)} 列 > 1e-12（例 {bad[:3]}）"


def _xsec_split_inputs(tz: Optional[str]) -> pd.DataFrame:
    """明列邊界輸入（足使預設切分成立）：3 標的 × 900 時點 1h、兩特徵、標籤 `return_1`；時間層 tz＝`tz`（None ⇒ naive）。"""
    ts = pd.date_range("2024-01-01", periods=900, freq="h", tz=tz)
    rows = []
    for t, stamp in enumerate(ts):
        for j, sym in enumerate(("AAA", "BBB", "CCC")):
            y = 0.01 * math.cos(t / 3.0 + 0.7 * j)
            rows.append((stamp, sym, y + 0.002 * math.sin(t + j), math.cos(t / 5.0 + j), y))
    return pd.DataFrame(rows, columns=["timestamp", "symbol", "f1", "f2", XSEC_LABEL]).set_index(["timestamp", "symbol"])


@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_cross_sectional_default_split_tz_aware_index_xfail() -> None:
    """（ICPERF Task 0.4 ㉟ 已修：時間陣列一律轉 UTC 去時區標記；函式名保留供收據綁定）正確答案：時間層 tz-aware（UTC）與 naive 之同一跨標的輸入，預設切分（`ic_train_test_split` 開）皆成立且截面 IC 序列與
    summary 相同（時區表示不得改變結果或使之崩潰）。"""
    naive = create_ic_analyzer().analyze_cross_sectional(_xsec_split_inputs(None), timeframe="1h")
    aware = create_ic_analyzer().analyze_cross_sectional(_xsec_split_inputs("UTC"), timeframe="1h")
    _assert_close_tree(aware["rolling_ic_series"], naive["rolling_ic_series"], "rolling_ic_series")
    _assert_close_tree({r["feature_name"]: r["icir"] for r in aware["summary_table"]},
                       {r["feature_name"]: r["icir"] for r in naive["summary_table"]}, "icir")


def _ref_cross_split(df: pd.DataFrame, oos: float, min_rows: int, embargo: int, horizon: int,
                     freq: Optional[pd.Timedelta]) -> Dict[str, Any]:
    """跨標的預設切分之參考實作（全域同步時間邊界 holdout，依 ic_filter_orchestrator.py:986-1036 之定義獨立重寫）：唯一時點
    排序後 train＝前 floor((1−oos)·n) 個時點（含）；test＝≥ train 末時點＋(horizon＋embargo)×K 線間距（間距由資料導出，
    不假設週期）；全域 train／test 列數與每標的 test 列數皆 ≥ min_rows 方成立。"""
    ts = pd.DatetimeIndex(df.index.get_level_values(0))
    sym = np.asarray(df.index.get_level_values(-1)).astype(str)
    uts = ts.unique().sort_values()
    n = int(len(uts))
    sp = int(math.floor((1.0 - oos) * n))
    if n < 2 or sp < 1 or sp >= n or freq is None:
        return {"ok": False, "reason": "no_train_or_test_timestamps", "n_ts": n, "test_mask": np.zeros(len(df), bool)}
    t_end = uts[sp - 1]
    t_start = t_end + (int(horizon) + int(embargo)) * freq
    train, test = np.asarray(ts <= t_end), np.asarray(ts >= t_start)
    per = {s: int((test & (sym == s)).sum()) for s in sorted(set(sym))}
    ok = int(train.sum()) >= min_rows and int(test.sum()) >= min_rows and all(v >= min_rows for v in per.values())
    return {"ok": ok, "n_ts": n, "split_point": sp, "train_end": str(t_end), "test_start": str(t_start),
            "train_rows": int(train.sum()), "test_rows": int(test.sum()), "per_symbol_test_rows": per, "test_mask": test}


@pytest.mark.requires_kline
@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_cross_sectional_default_split_matches_oracle_on_real_kline() -> None:
    """SPEC v5.39 ⑩（跨標的預設分支）：本機 kline_cache.h5 之全部 1h 標的末 2,000 根真實資料（足使預設切分成立）、預設設定
    （`ic_train_test_split` 開）之 `analyze_cross_sectional` 截面 IC 序列、summary、`cross_sectional_symbol_ic`、
    `cross_symbol_validation` == 以 `_ref_cross_split` 重建之測試段上之 `_ref_cross_sectional`；切分參考實作須成立且每標的
    測試段 ≥ min_test_rows。"""
    from momentum.Analysis.ic_config_schema import ICConfig

    df = _real_cross_sectional_frame(2000)
    # 時間層取 naive UTC（同服務端跨標的路徑：特徵庫之時間索引為 naive；tz-aware 索引之崩潰另見
    # `test_cross_sectional_default_split_tz_aware_index_xfail`）
    df.index = df.index.set_levels(df.index.levels[0].tz_localize(None), level=0)
    cfg = ICConfig()
    assert cfg.ic_train_test_split, "前提：預設設定之切分為開"
    ts = pd.DatetimeIndex(df.index.get_level_values(0)).unique().sort_values()
    freq = pd.Timedelta(np.median(np.diff(ts.asi8)), unit="ns")
    osp = _ref_cross_split(df, float(cfg.oos_test_size), int(cfg.min_test_rows), int(cfg.embargo), 1, freq)
    assert osp["ok"], f"預設切分不成立（資料不足）：{osp}"
    report = create_ic_analyzer().analyze_cross_sectional(df, timeframe="1h")
    exp = _ref_cross_sectional(df.iloc[np.flatnonzero(osp["test_mask"])])
    for f, values in exp["series"].items():
        _assert_close_tree(report["rolling_ic_series"][f]["window_cross_sectional"], values, f"series/{f}")
    rows = {r["feature_name"]: r for r in report["summary_table"]}
    for f, fields in exp["summary"].items():
        _assert_close_tree({k: rows[f][k] for k in fields}, fields, f"summary/{f}")
    _assert_close_tree(report["cross_sectional_symbol_ic"], exp["symbol_ic"], "cross_sectional_symbol_ic")
    _assert_close_tree(report["cross_symbol_validation"], exp["validation"], "cross_symbol_validation")


# ── 事件匯入批標籤 oracle（SPEC v5.38 ①） ─────────────────────────────────────────────────────────────────────


def _contract_k_min() -> int:
    """事件匯入契約 `decision_offset_bars` 之 min（momentum/Analysis/contracts/event_import_contract.json；分析用 k 之初始值
    ＝契約 min，event_label_spec_resolution.py:149-151）。"""
    contract = json.loads((REPO / "momentum" / "Analysis" / "contracts" / "event_import_contract.json").read_text(encoding="utf-8"))

    def find(o: Any) -> Optional[int]:
        if isinstance(o, dict):
            v = o.get("decision_offset_bars")
            if isinstance(v, dict) and "min" in v:
                return int(v["min"])
            for x in o.values():
                r = find(x)
                if r is not None:
                    return r
        elif isinstance(o, list):
            for x in o:
                r = find(x)
                if r is not None:
                    return r
        return None

    k = find(contract)
    assert k is not None, "契約無 decision_offset_bars.min"
    return k


def _ref_event_spec(records: Sequence[Mapping[str, Any]], declared: Mapping[str, Any], k_min: int,
                    requested: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    """分析用 event_label_spec 之參考實作（後端預設導出規則，event_label_spec_resolution.py:130-151，獨立重寫）：請求明給之鍵
    優先；單一觸發週期且宣告深度 d ≥ 1 ⇒ trigger_open／open_to_horizon_close／h＝d；否則 trigger_open／open_to_close／h＝1；
    decision_offset_bars＝契約 min。"""
    tfs = sorted({str(r.get("timeframe")) for r in records if r.get("timeframe")})
    depth = int((declared or {}).get(tfs[0], 0)) if len(tfs) == 1 else 0
    preset = ("trigger_open", "open_to_horizon_close", depth) if depth >= 1 else ("trigger_open", "open_to_close", 1)
    spec = {"entry_price_semantic": preset[0], "label_return_mode": preset[1], "horizon_bars": int(preset[2]),
            "decision_offset_bars": int(k_min)}
    spec.update({k: v for k, v in (requested or {}).items() if v is not None})
    return spec


def _ref_event_label_values(records: Sequence[Mapping[str, Any]], spec: Mapping[str, Any],
                            kline: Path = KLINE_CACHE) -> Dict[str, Dict[str, Any]]:
    """事件標籤之參考實作（依 label_value_from_case.py:359-384、:1213-1241 之定義獨立重寫；kline_cache.h5 直接讀 open／close
    〔float64〕）：t0 根＝開盤時間 == t0 之根；entry 根＝trigger_*：t0、next_open：t0＋1、decision_bar_*：t0−k；基準價＝
    close_to_close：t0 根收盤，否則 entry 根之 open（*_open）或 close（*_close）；終點根＝close_to_close：t0＋h、open_to_close：
    entry、open_to_horizon_close：entry＋h；值＝方向乘號（short ⇒ −1）×(終點收盤−基準價)／基準價；越界或基準價 ≤ 0 ⇒ None。
    特徵列＝決策根（t0−k）前一根之開盤時間（毫秒）。另回 `close_to_close`＝同終點根、基準改為 entry 前一根收盤之報酬
    （定因用：*_open 基準之 open[entry] 與 close[entry−1] 相同時兩者相等，相異時即為首份收據所見之微差）。"""
    import h5py

    bars: Dict[tuple, Dict[str, np.ndarray]] = {}
    out: Dict[str, Dict[str, Any]] = {}
    k, h = int(spec["decision_offset_bars"]), int(spec["horizon_bars"])
    entry, mode = str(spec["entry_price_semantic"]), str(spec["label_return_mode"])
    for r in records:
        key = (str(r["symbol"]), str(r["timeframe"]))
        if key not in bars:
            with h5py.File(kline, "r") as f:
                d = f[f"{key[0]}/{key[1]}/data"][:]
            ts = d["timestamp"].astype("int64")
            ms = ts if int(ts[-1]) > 10 ** 12 else ts * 1000
            bars[key] = {"ms": ms, "open": d["open"].astype("float64"), "close": d["close"].astype("float64")}
        b = bars[key]
        pos = np.flatnonzero(b["ms"] == int(r["t0"]))
        val: Optional[float] = None
        row = c2c = None
        if pos.size == 1:
            t0 = int(pos[0])
            e = {"trigger_open": t0, "trigger_close": t0, "next_open": t0 + 1,
                 "decision_bar_open": t0 - k, "decision_bar_close": t0 - k}[entry]
            end = {"close_to_close": t0 + h, "open_to_close": e, "open_to_horizon_close": e + h}[mode]
            field = "open" if entry.endswith("_open") else "close"
            base = b["close"][t0] if mode == "close_to_close" else (b[field][e] if 0 <= e < b["ms"].size else math.nan)
            sign = -1.0 if str(r.get("direction")) == "short" else 1.0
            if 0 <= end < b["ms"].size and math.isfinite(base) and base > 0:
                val = sign * (float(b["close"][end]) - float(base)) / float(base)
                prev = float(b["close"][e - 1]) if mode != "close_to_close" and e >= 1 else float(base)
                c2c = sign * (float(b["close"][end]) - prev) / prev
            r_idx = t0 - k - 1
            if r_idx >= 0:
                row = int(b["ms"][r_idx])
        out[str(r["event_id"])] = {"row_open_ms": row, "value": val, "close_to_close": c2c}
    return out


def test_event_label_oracle_boundaries_explicit(tmp_path: Path) -> None:
    """事件標籤 oracle 之明列邊界：(i) spec 導出——單週期深度 12 ⇒ trigger_open／open_to_horizon_close／12、深度 0 與混週期
    ⇒ open_to_close／1、請求明給之鍵優先；(ii) 取價——open[t0] ≠ close[t0−1] 之根使 open_to_horizon_close 與
    close[t+h]／close[t]−1 不同（首份收據 93 筆中 53 筆約 1e-6 差之成因）、short 取負、越界 ⇒ None、列＝t0−k−1。"""
    import h5py

    recs = [{"symbol": "S", "timeframe": "4h", "event_id": "e1", "t0": 5 * 3_600_000 * 4, "direction": "long"},
            {"symbol": "S", "timeframe": "4h", "event_id": "e2", "t0": 7 * 3_600_000 * 4, "direction": "short"},
            {"symbol": "S", "timeframe": "4h", "event_id": "e3", "t0": 9 * 3_600_000 * 4, "direction": "long"}]
    assert _ref_event_spec(recs, {"4h": 12}, 0)["label_return_mode"] == "open_to_horizon_close"
    assert _ref_event_spec(recs, {"4h": 0}, 0)["label_return_mode"] == "open_to_close"
    assert _ref_event_spec([*recs, {"timeframe": "1h"}], {"4h": 3}, 0)["horizon_bars"] == 1
    assert _ref_event_spec(recs, {"4h": 3}, 0, {"horizon_bars": 2})["horizon_bars"] == 2
    n = 11
    ms = np.arange(n, dtype="int64") * 3_600_000 * 4
    close = 100.0 + np.arange(n, dtype="float64")
    opn = np.r_[100.0, close[:-1]]
    opn[5] = close[4] + 0.37   # 開盤跳空：open[t0] ≠ close[t0−1]
    arr = np.zeros(n, dtype=[("timestamp", "<i8"), ("open", "<f4"), ("close", "<f4")])
    # 同 kline_cache.h5 之格式：時間戳為 epoch 秒、價格 float32
    arr["timestamp"], arr["open"], arr["close"] = ms // 1000 + 1_700_000_000, opn, close
    ms = (arr["timestamp"].astype("int64")) * 1000
    for r, i in zip(recs, (5, 7, 9)):
        r["t0"] = int(ms[i])
    path = tmp_path / "k.h5"
    with h5py.File(path, "w") as f:
        f.create_dataset("S/4h/data", data=arr)
    spec = _ref_event_spec(recs, {"4h": 3}, 0)
    out = _ref_event_label_values(recs, spec, path)
    o32, c32 = arr["open"].astype("float64"), arr["close"].astype("float64")
    assert out["e1"]["row_open_ms"] == int(ms[4])
    assert out["e1"]["value"] == (c32[8] - o32[5]) / o32[5]
    # 定因：同終點根、基準改 close[t0−1]；e1 之 t0 根跳空 ⇒ 相異，e2 之 open[t0]＝close[t0−1] ⇒ 相同
    assert out["e1"]["close_to_close"] == (c32[8] - c32[4]) / c32[4] and out["e1"]["close_to_close"] != out["e1"]["value"]
    assert out["e2"]["value"] == -(c32[10] - o32[7]) / o32[7] == out["e2"]["close_to_close"]
    assert out["e3"]["value"] is None   # t0＋h 越界


@pytest.mark.requires_kline
@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_event_label_oracle_matches_product_on_real_batch() -> None:
    """SPEC v5.38 ①：收據所用之事件匯入批（收據工具 `REQUESTS["L.event_import_report"]` 之 FACT-RECEIPT；真實 kline 依明列
    規則所建）——產品後端 spec 解析（`resolve_event_label_spec`）== `_ref_event_spec`；產品事件管線（`prepare_analysis_windows`
    → `resolve_label_value_at_analyze`，真實 kline bars）逐事件 label_value == `_ref_event_label_values`（相對 ≤ 1e-12）；並
    證定因：至少一筆 open[t0] ≠ close[t0−1] 而與 close[t+h]／close[t]−1 相異。"""
    from momentum.Analysis.event_samples.event_label_spec_resolution import resolve_event_label_spec
    from momentum.factories import create_event_sample_pipeline

    R = _receipt_tool()
    iid = R._event_batch_import_id(R.REQUESTS["L.event_import_report"]["event_batch_receipt"])
    batch = json.loads((REPO / "data_cache" / "events" / f"{iid}.json").read_text(encoding="utf-8"))
    records = list(batch["records"])
    declared = (batch.get("lookahead_declaration") or {}).get("lookahead_bars_declared") or {}
    spec = _ref_event_spec(records, declared, _contract_k_min())
    pipeline = create_event_sample_pipeline()
    resolved = resolve_event_label_spec(records, requested_spec=None, declared_receipt={"lookahead_bars_declared": declared},
                                        k_domain=pipeline.int_field_domain("decision_offset_bars"))
    assert resolved.spec == spec, (resolved.spec, spec)
    symbols = sorted({str(r["symbol"]) for r in records})
    tfs = sorted({str(r["timeframe"]) for r in records})
    bars = pipeline.bars_from_kline_cache(symbols, tfs)
    prepared = pipeline.prepare_analysis_windows(records, bars, event_label_spec=spec, event_import_id=iid,
                                                 lookahead_bars_declared=declared,
                                                 timeframe_seconds=pipeline.timeframe_seconds_for(tfs),
                                                 feature_timeframe=tfs[0])
    got = pipeline.resolve_label_value_at_analyze(prepared, bars, event_label_spec=spec).label_values
    exp = _ref_event_label_values(records, spec)
    assert set(got) <= set(exp) and len(got) >= 30, (len(got), len(exp))
    for eid, v in got.items():
        e = exp[eid]["value"]
        assert (v is None and e is None) or _rel(float(v), float(e)) <= REL_TOL, (eid, v, e)
    diff = [eid for eid, v in got.items() if v is not None and exp[eid]["close_to_close"] is not None
            and abs(exp[eid]["close_to_close"] - float(v)) > 1e-12]
    same = [eid for eid, v in got.items() if v is not None and exp[eid]["close_to_close"] is not None
            and abs(exp[eid]["close_to_close"] - float(v)) <= 1e-12]
    assert diff and same, f"定因：open[t0] ≠ close[t0−1] 之事件須相異、相同者須相等（相異 {len(diff)}、相同 {len(same)}）"
