"""IC 1d B0 baseline 驗收測試（Task 0.1 / D-9）。

驗收斷言（TODO §P B0 寫死）:
1. module_summary["factor_exposure"] != "skipped" 且 portfolio_exposure 非空
2. 同源斷言：close carrier 經 production `_stage4_ic_calculation` (:2913-2930)
   注入，**非**測試直接塞 `_ic_cache["close_series"]`；
   spy 記 stage4 回傳值，與 cache 等比對（B1）
3. analyzer real-OLS oracle dump → handoffs/ic1d_baseline/analyzer_oracle.json
   （獨立 np.linalg.lstsq 為 oracle 源，B3）
4. payload.module_summary == report.module_summary（B2）
5. cache_close_finite 欄存在於 payload（C；不斷言 finite>0）

禁合成 fixture 冒充；真實 kline = data_cache/feature_klines/kline_cache.h5。
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any, Optional
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.ic1d_baseline_freeze import (  # noqa: E402
    ANALYZER_ORACLE_N,
    ANALYZER_ORACLE_N_FACTORS,
    ANALYZER_ORACLE_SEED,
    GOLDEN_VOLATILE_TOP_KEYS,
    OUT_DIR,
    build_analyzer_oracle,
    build_baseline_payload,
    build_provenance_sidecar,
    run_production_deep_analysis,
)

KLINE_CACHE = REPO_ROOT / "data_cache" / "feature_klines" / "kline_cache.h5"


def _require_kline() -> None:
    if not KLINE_CACHE.is_file():
        pytest.fail(f"requires_kline: missing {KLINE_CACHE}")


def _portfolio_exposure_from_report(report: Any) -> dict:
    fe = (getattr(report, "results", {}) or {}).get("factor_exposure")
    if not isinstance(fe, dict):
        return {}
    pe = fe.get("portfolio_exposure")
    if isinstance(pe, dict) and pe:
        return pe
    payload = fe.get("payload")
    summary = getattr(payload, "summary", None) if payload is not None else None
    if summary is None and isinstance(payload, dict):
        summary = payload.get("summary")
    if isinstance(summary, dict):
        pe2 = summary.get("portfolio_exposure")
        if isinstance(pe2, dict):
            return pe2
    return {}


def _series_values_equal(a: Any, b: Any) -> bool:
    """比對兩 Series 值相等（含 NaN 位置）；禁只比鍵。"""
    if a is None or b is None:
        return a is b
    if not isinstance(a, pd.Series) or not isinstance(b, pd.Series):
        return False
    if len(a) != len(b):
        return False
    av = pd.to_numeric(a, errors="coerce").to_numpy(dtype=float)
    bv = pd.to_numeric(b, errors="coerce").to_numpy(dtype=float)
    if av.shape != bv.shape:
        return False
    # NaN↔NaN 相等；有限值必須 bit-level 一致
    both_nan = np.isnan(av) & np.isnan(bv)
    both_fin = np.isfinite(av) & np.isfinite(bv)
    ok = both_nan | (both_fin & (av == bv))
    return bool(np.all(ok))


def _independent_lstsq_oracle(
    portfolio: pd.Series,
    factor_returns: pd.DataFrame,
) -> tuple[float, float, dict[str, float], dict[str, float]]:
    """獨立 OLS oracle：自組 design matrix [1, factors] + np.linalg.lstsq。

    回傳 (alpha, r_squared, factor_betas, attribution)。
    attribution[name] = beta[name] * factor_mean[name]（與 analyzer 公式一致）。
    不呼叫 calculate_factor_attribution（B3 破循環）。
    """
    aligned = pd.concat(
        [portfolio.rename("portfolio"), factor_returns],
        axis=1,
    ).dropna()
    y = aligned["portfolio"].to_numpy(dtype=float)
    factor_names = list(aligned.drop(columns=["portfolio"]).columns)
    x_factors = aligned[factor_names].to_numpy(dtype=float)
    x = np.column_stack([np.ones(len(x_factors)), x_factors])
    beta, *_ = np.linalg.lstsq(x, y, rcond=None)
    y_pred = x @ beta
    residual = y - y_pred
    ss_res = float(np.sum(residual ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r_squared = float(1.0 - ss_res / ss_tot) if ss_tot > 0 else 0.0
    factor_betas = {
        name: float(beta[idx + 1]) for idx, name in enumerate(factor_names)
    }
    factor_means = aligned[factor_names].mean()
    attribution = {
        name: float(factor_betas[name] * float(factor_means[name]))
        for name in factor_names
    }
    return float(beta[0]), r_squared, factor_betas, attribution


def _independent_lstsq_alpha_r2(
    portfolio: pd.Series,
    factor_returns: pd.DataFrame,
) -> tuple[float, float]:
    """相容包裝：只回 alpha / r_squared（既有 mutation 用）。"""
    alpha, r2, _betas, _attr = _independent_lstsq_oracle(portfolio, factor_returns)
    return alpha, r2


def test_module_summary_not_skipped_and_portfolio_exposure_nonempty() -> None:
    """① module 非 skipped + portfolio_exposure 非空。"""
    _require_kline()
    _orch, report, source_close = run_production_deep_analysis(
        force_modules=["factor_exposure"]
    )

    # C3：源端 close 有效
    assert not source_close.empty
    assert not bool(source_close.isna().all())
    assert int(np.isfinite(source_close.to_numpy(dtype=float)).sum()) > 0

    # C2：直接讀 DeepAnalysisReport.module_summary（非 serialized receipt）
    module_summary = dict(report.module_summary or {})
    fe_status = module_summary.get("factor_exposure")
    assert fe_status != "skipped", (
        f"module_summary.factor_exposure={fe_status!r} must not be 'skipped'"
    )
    assert fe_status is not None

    pe = _portfolio_exposure_from_report(report)
    assert pe, "payload portfolio_exposure must be non-empty"
    assert isinstance(pe, dict)
    assert len(pe) > 0


def test_close_carrier_via_production_stage4_not_ad_hoc_ic_cache() -> None:
    """② 同源斷言（D-9 / B1）：stage4 回傳 close 值 == cache close（非只比鍵）。"""
    _require_kline()
    from momentum.Analysis.ic_filter_orchestrator import ICFilterOrchestrator

    stage4_calls: list[dict[str, Any]] = []
    stage4_close_values: list[Optional[pd.Series]] = []
    real_stage4 = ICFilterOrchestrator._stage4_ic_calculation

    def _spy_stage4(self: Any, *args: Any, **kwargs: Any) -> dict:
        result = real_stage4(self, *args, **kwargs)
        close_obj: Optional[pd.Series] = None
        has_key = isinstance(result, dict) and "close_series" in result
        if has_key and result.get("close_series") is not None:
            # 記**值**副本（非只記鍵），供與 cache 等比對
            raw = result["close_series"]
            close_obj = (
                raw.copy(deep=True) if isinstance(raw, pd.Series) else pd.Series(raw)
            )
        stage4_close_values.append(close_obj)
        stage4_calls.append(
            {
                "has_close_key": has_key,
                "close_is_none": (
                    result.get("close_series") is None
                    if isinstance(result, dict)
                    else True
                ),
            }
        )
        return result

    with patch.object(
        ICFilterOrchestrator, "_stage4_ic_calculation", _spy_stage4
    ):
        orch, report, source_close = run_production_deep_analysis(
            force_modules=["factor_exposure"]
        )

    # production 必須走過 stage4（carrier 寫入點）
    assert stage4_calls, (
        "D-9 FAIL: _stage4_ic_calculation was not called; "
        "close cannot claim production provenance"
    )
    assert any(c["has_close_key"] for c in stage4_calls), (
        "D-9 FAIL: stage4 result missing close_series key "
        "(expected production write at :2913-2930)"
    )
    assert any(s is not None for s in stage4_close_values), (
        "D-9 FAIL: stage4 did not return a non-None close_series value"
    )

    # cache 內 close_series 存在（由 analyze 收尾自 ic_results 寫入，非測試賦值）
    assert orch._ic_cache is not None
    close_series = orch._ic_cache.get("close_series")
    assert close_series is not None, (
        "D-9 FAIL: _ic_cache['close_series'] is None after production analyze"
    )
    assert isinstance(close_series, pd.Series)

    # B1：cache close 與 stage4 回傳**值**同源（含 NaN 位置）
    stage4_close = next(s for s in stage4_close_values if s is not None)
    assert _series_values_equal(close_series, stage4_close), (
        "D-9/B1 FAIL: _ic_cache['close_series'] values != stage4 returned "
        "close_series (provenance by value)"
    )

    # 源端有效 close（C3）；本測試**從未**執行 orch._ic_cache['close_series'] = ...
    assert not bool(source_close.isna().all())
    # 模組仍應可完成（production 僅拒 None，不拒 reindex 後 NaN）
    assert report.module_summary.get("factor_exposure") != "skipped"


def test_d9_mutation_stage4_carrier_diverges_must_fail() -> None:
    """B1 mutation ①：spy 記真實 stage4 close，回傳前改成全 999 → cache≠記錄 → FAIL。"""
    _require_kline()
    from momentum.Analysis.ic_filter_orchestrator import ICFilterOrchestrator

    recorded: list[pd.Series] = []
    real_stage4 = ICFilterOrchestrator._stage4_ic_calculation

    def _mutant_stage4(self: Any, *args: Any, **kwargs: Any) -> dict:
        result = real_stage4(self, *args, **kwargs)
        if not isinstance(result, dict):
            return result
        raw = result.get("close_series")
        if isinstance(raw, pd.Series):
            recorded.append(raw.copy(deep=True))
            # 改壞 stage4 carrier 後再回傳 → production 寫入 cache 的是 999
            result = dict(result)
            result["close_series"] = pd.Series(
                np.full(len(raw), 999.0, dtype=float),
                index=raw.index,
            )
        return result

    with patch.object(
        ICFilterOrchestrator, "_stage4_ic_calculation", _mutant_stage4
    ):
        orch, _report, _src = run_production_deep_analysis(
            force_modules=["factor_exposure"]
        )

    assert recorded, "mutation setup: stage4 must have returned close_series"
    cache_close = orch._ic_cache.get("close_series") if orch._ic_cache else None
    # 記錄的是改壞前真實值；cache 應為 999 → 值不等
    # 主測的 provenance assert 在此條件下必須觸發 FAIL
    provenance_ok = _series_values_equal(cache_close, recorded[0])
    assert provenance_ok is False, (
        "B1 mutation ①: stage4 carrier 改 999 後 cache 仍等於改壞前記錄，"
        "provenance-by-value 無法證偽"
    )
    with pytest.raises(AssertionError):
        assert _series_values_equal(cache_close, recorded[0])


def test_d9_mutation_adhoc_ic_cache_overwrite_must_fail() -> None:
    """B1 mutation ②：analyze 後 ad-hoc 覆寫 `_ic_cache['close_series']` → FAIL。"""
    _require_kline()
    from momentum.Analysis.ic_filter_orchestrator import ICFilterOrchestrator

    stage4_close_values: list[pd.Series] = []
    real_stage4 = ICFilterOrchestrator._stage4_ic_calculation

    def _spy_stage4(self: Any, *args: Any, **kwargs: Any) -> dict:
        result = real_stage4(self, *args, **kwargs)
        if isinstance(result, dict) and isinstance(result.get("close_series"), pd.Series):
            stage4_close_values.append(result["close_series"].copy(deep=True))
        return result

    with patch.object(
        ICFilterOrchestrator, "_stage4_ic_calculation", _spy_stage4
    ):
        orch, _report, _src = run_production_deep_analysis(
            force_modules=["factor_exposure"]
        )

    assert stage4_close_values, "spy must capture stage4 close"
    assert orch._ic_cache is not None
    # ② ad-hoc 覆寫（模擬假綠路徑）
    n = len(stage4_close_values[0])
    if orch._ic_cache.get("features_df") is not None:
        n = len(orch._ic_cache["features_df"])
        idx = orch._ic_cache["features_df"].index
    else:
        idx = stage4_close_values[0].index
    orch._ic_cache["close_series"] = pd.Series(
        np.linspace(1.0, 2.0, n), index=idx
    )

    provenance_ok = _series_values_equal(
        orch._ic_cache["close_series"], stage4_close_values[0]
    )
    assert provenance_ok is False, (
        "B1 mutation ②: ad-hoc 覆寫後仍等於 stage4 close，無法證偽"
    )
    with pytest.raises(AssertionError):
        assert _series_values_equal(
            orch._ic_cache["close_series"], stage4_close_values[0]
        )


def test_analyzer_real_ols_oracle_dump() -> None:
    """③ analyzer real-OLS oracle：固定種子 dump；獨立 lstsq 驗 alpha/r2/betas/attr。

    Bug3：不得只斷言 alpha/r_squared；factor_betas 與 attribution 亦須對齊獨立 lstsq。
    """
    from momentum.Analysis.factor_exposure_analyzer import FactorExposureAnalyzer

    oracle = build_analyzer_oracle()
    assert oracle["seed"] == ANALYZER_ORACLE_SEED
    assert oracle["n_rows"] == ANALYZER_ORACLE_N
    assert oracle["n_factors"] == ANALYZER_ORACLE_N_FACTORS

    # 現行成功回傳無 status；B0 dump 含 alpha/r2/unexplained/factor_betas/attribution
    assert "alpha" in oracle
    assert "r_squared" in oracle
    assert "unexplained" in oracle
    assert "factor_betas" in oracle and isinstance(oracle["factor_betas"], dict)
    assert "attribution" in oracle and isinstance(oracle["attribution"], dict)
    assert oracle["alpha"] is not None and math.isfinite(float(oracle["alpha"]))
    assert oracle["r_squared"] is not None and math.isfinite(float(oracle["r_squared"]))
    assert oracle["unexplained"] is not None and math.isfinite(
        float(oracle["unexplained"])
    )
    # 現行契約：unexplained == alpha
    assert oracle["unexplained"] == pytest.approx(oracle["alpha"], abs=0.0, rel=0.0)

    # B3：獨立 lstsq 重算（不呼叫 calculate_factor_attribution）
    rng = np.random.default_rng(ANALYZER_ORACLE_SEED)
    portfolio = pd.Series(rng.normal(0.0, 0.01, ANALYZER_ORACLE_N), name="portfolio")
    factor_returns = pd.DataFrame(
        rng.normal(0.0, 0.01, (ANALYZER_ORACLE_N, ANALYZER_ORACLE_N_FACTORS)),
        columns=[f"f{i + 1}" for i in range(ANALYZER_ORACLE_N_FACTORS)],
    )
    ind_alpha, ind_r2, ind_betas, ind_attr = _independent_lstsq_oracle(
        portfolio, factor_returns
    )
    assert float(oracle["alpha"]) == pytest.approx(ind_alpha)
    assert float(oracle["r_squared"]) == pytest.approx(ind_r2)
    # Bug3：oracle dump 的 betas / attribution 必須對齊獨立 lstsq
    assert set(oracle["factor_betas"].keys()) == set(ind_betas.keys())
    assert set(oracle["attribution"].keys()) == set(ind_attr.keys())
    for name in ind_betas:
        assert float(oracle["factor_betas"][name]) == pytest.approx(ind_betas[name])
        assert float(oracle["attribution"][name]) == pytest.approx(ind_attr[name])

    # analyzer 回傳亦應與獨立 lstsq 一致（非循環：基準是 lstsq）
    result = FactorExposureAnalyzer(config={}).calculate_factor_attribution(
        portfolio, factor_returns
    )
    assert float(result["alpha"]) == pytest.approx(ind_alpha)
    assert float(result["r_squared"]) == pytest.approx(ind_r2)
    assert float(result["unexplained"]) == pytest.approx(ind_alpha)
    assert set(result["factor_betas"].keys()) == set(ind_betas.keys())
    for name in ind_betas:
        assert float(result["factor_betas"][name]) == pytest.approx(ind_betas[name])
        assert float(result["attribution"][name]) == pytest.approx(ind_attr[name])

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    oracle_path = OUT_DIR / "analyzer_oracle.json"
    text = json.dumps(oracle, sort_keys=True, allow_nan=False, ensure_ascii=False)
    if not text.endswith("\n"):
        text = text + "\n"
    oracle_path.write_text(text, encoding="utf-8")
    assert oracle_path.is_file()

    disk = json.loads(oracle_path.read_text(encoding="utf-8"))
    assert disk["alpha"] == pytest.approx(oracle["alpha"])
    assert disk["r_squared"] == pytest.approx(oracle["r_squared"])
    assert "intercept" not in disk  # B1 才補（freeze dump 未納入）
    for name in ind_betas:
        assert float(disk["factor_betas"][name]) == pytest.approx(ind_betas[name])
        assert float(disk["attribution"][name]) == pytest.approx(ind_attr[name])


def test_b3_mutation_analyzer_hardcoded_alpha_must_fail() -> None:
    """B3 mutation：analyzer 硬改 alpha=123 → 與獨立 lstsq 不等 → FAIL。"""
    from momentum.Analysis.factor_exposure_analyzer import FactorExposureAnalyzer

    rng = np.random.default_rng(ANALYZER_ORACLE_SEED)
    portfolio = pd.Series(rng.normal(0.0, 0.01, ANALYZER_ORACLE_N), name="portfolio")
    factor_returns = pd.DataFrame(
        rng.normal(0.0, 0.01, (ANALYZER_ORACLE_N, ANALYZER_ORACLE_N_FACTORS)),
        columns=[f"f{i + 1}" for i in range(ANALYZER_ORACLE_N_FACTORS)],
    )
    ind_alpha, ind_r2 = _independent_lstsq_alpha_r2(portfolio, factor_returns)

    def _fake_attr(self: Any, *args: Any, **kwargs: Any) -> dict:
        return {
            "factor_betas": {},
            "alpha": 123.0,
            "r_squared": 0.5,
            "attribution": {},
            "unexplained": 123.0,
        }

    with patch.object(
        FactorExposureAnalyzer, "calculate_factor_attribution", _fake_attr
    ):
        result = FactorExposureAnalyzer(config={}).calculate_factor_attribution(
            portfolio, factor_returns
        )

    with pytest.raises(AssertionError):
        assert float(result["alpha"]) == pytest.approx(ind_alpha)
        assert float(result["r_squared"]) == pytest.approx(ind_r2)


def test_bug3_oracle_betas_mutation_must_fail() -> None:
    """Bug3 mutation：patch analyzer 後呼叫主 oracle 測試路徑 → 必須 FAIL。

    Codex caveat：不得只重複斷言 pattern；須實際走
    `test_analyzer_real_ols_oracle_dump` 主測，證明刪掉主 betas/attr 斷言
    → 本探針亦無法綠（刪主斷言後 mutant 不觸發 AssertionError）。
    alpha/r2 仍正確時舊測會綠；主測的 betas/attr 斷言才可證偽。
    """
    from momentum.Analysis.factor_exposure_analyzer import FactorExposureAnalyzer

    real_attr = FactorExposureAnalyzer.calculate_factor_attribution

    def _mutant_betas(self: Any, *args: Any, **kwargs: Any) -> dict:
        result = real_attr(self, *args, **kwargs)
        # 保持 alpha/r2/unexplained 正確，只改壞一個 beta（+ attribution）
        mutated = dict(result)
        betas = dict(result.get("factor_betas") or {})
        assert betas, "setup: analyzer must return non-empty factor_betas"
        first = next(iter(betas.keys()))
        betas[first] = float(betas[first]) + 99.0
        mutated["factor_betas"] = betas
        attr = dict(result.get("attribution") or {})
        if first in attr:
            attr[first] = float(attr[first]) + 99.0
        mutated["attribution"] = attr
        return mutated

    with patch.object(
        FactorExposureAnalyzer, "calculate_factor_attribution", _mutant_betas
    ):
        # 走主 oracle 測試（含 factor_betas / attribution 對齊獨立 lstsq）
        with pytest.raises(AssertionError):
            test_analyzer_real_ols_oracle_dump()


def test_baseline_payload_module_summary_from_report_not_serializer() -> None:
    """C2 / B2：payload.module_summary 必須等於 dict(report.module_summary)。"""
    _require_kline()
    _orch, report, _src = run_production_deep_analysis(force_modules=["factor_exposure"])
    payload = build_baseline_payload(report, profile="p0")

    assert "module_summary" in payload
    assert isinstance(payload["module_summary"], dict)
    # B2：等值（非只查 != skipped）
    assert payload["module_summary"] == dict(report.module_summary)
    assert payload["module_summary"].get("factor_exposure") != "skipped"
    # results 內不應被誤標為 module_summary 巢狀鍵來源
    assert "results" in payload
    fe = (payload.get("results") or {}).get("factor_exposure")
    assert isinstance(fe, dict)
    pe = fe.get("portfolio_exposure") or {}
    assert pe, "results.factor_exposure.portfolio_exposure must be non-empty"
    assert "canonical_sha256" in payload
    assert "fixture_sha256" in payload
    # golden 禁 volatile provenance（sidecar 專用）
    for key in GOLDEN_VOLATILE_TOP_KEYS:
        assert key not in payload, f"golden must not contain volatile key {key!r}"


def test_b2_mutation_hardcoded_module_summary_must_fail() -> None:
    """B2 mutation：build_baseline_payload 硬編 module_summary → 等值斷言 FAIL。"""
    _require_kline()
    _orch, report, _src = run_production_deep_analysis(force_modules=["factor_exposure"])

    real_build = build_baseline_payload

    def _mutant_build(report_arg: Any, *, profile: str, **kwargs: Any) -> dict:
        payload = real_build(report_arg, profile=profile, **kwargs)
        # 硬編（假綠舊路徑只查 != skipped 會過）
        payload["module_summary"] = {"factor_exposure": "completed"}
        return payload

    with patch(
        "scripts.ic1d_baseline_freeze.build_baseline_payload", _mutant_build
    ):
        # 直接呼叫 mutant 模擬被改壞的 builder
        payload = _mutant_build(report, profile="p0")

    with pytest.raises(AssertionError):
        assert payload["module_summary"] == dict(report.module_summary)


def test_payload_cache_close_finite_field_present() -> None:
    """C：payload 必須有 cache_close_finite 欄（存在性；不斷言 finite>0）。"""
    _require_kline()
    orch, report, source_close = run_production_deep_analysis(
        force_modules=["factor_exposure"]
    )
    from scripts.ic1d_baseline_freeze import _finite_count_label

    src_label = _finite_count_label(source_close)
    cache_close = (
        orch._ic_cache.get("close_series") if orch._ic_cache is not None else None
    )
    cache_label = _finite_count_label(
        cache_close if isinstance(cache_close, pd.Series) else None
    )
    payload = build_baseline_payload(
        report,
        profile="p0",
        source_close_finite=src_label,
        cache_close_finite=cache_label,
    )
    assert "cache_close_finite" in payload, (
        "C FAIL: cache_close_finite must be present in baseline payload"
    )
    assert "source_close_finite" in payload
    # 格式 finite/total；**不**斷言 finite>0（production all-NaN 另票）
    assert isinstance(payload["cache_close_finite"], str)
    assert "/" in payload["cache_close_finite"] or payload["cache_close_finite"] == "none"


def test_provenance_sidecar_holds_volatile_fields() -> None:
    """provenance sidecar 含 volatile 欄；golden 跨 profile 不含 profile/壁鐘。"""
    _require_kline()
    _orch, report, _src = run_production_deep_analysis(force_modules=["factor_exposure"])
    golden_p0 = build_baseline_payload(report, profile="p0")
    golden_p1 = build_baseline_payload(report, profile="p1")
    # 同一 report → golden 確定性內容跨 profile 應一致（含 canonical_sha256）
    assert golden_p0 == golden_p1
    for key in GOLDEN_VOLATILE_TOP_KEYS:
        assert key not in golden_p0

    side = build_provenance_sidecar(
        report, profile="p0", golden_filename="p0_before.json"
    )
    assert side["profile"] == "p0"
    assert side["generated_by"] == "ic1d_baseline_freeze --profile p0"
    assert "generated_at" in side
    assert "total_execution_time_s" in side
    assert isinstance(side.get("lineage"), dict)
    assert side["lineage"].get("close_carrier") == (
        "production:_stage4_ic_calculation:2913-2930"
    )
    assert side["golden_filename"] == "p0_before.json"


def test_deep_noop_results_mutation_must_fail(tmp_path: Path) -> None:
    """可證偽：改 results 真實葉值後零-allow compare 必須 FAIL（非空殼）。"""
    import subprocess

    _require_kline()
    _orch, report, _src = run_production_deep_analysis(force_modules=["factor_exposure"])
    base = build_baseline_payload(report, profile="p0")
    mutated = json.loads(json.dumps(base, sort_keys=True, allow_nan=False))

    # 改 results 內一真實葉（portfolio_exposure 任一數值）；禁只動 sidecar 欄
    fe = mutated.get("results", {}).get("factor_exposure") or {}
    pe = fe.get("portfolio_exposure") or {}
    assert pe, "setup: portfolio_exposure must be non-empty for mutation"
    first_key = next(iter(pe.keys()))
    original = pe[first_key]
    if isinstance(original, (int, float)) and not isinstance(original, bool):
        pe[first_key] = float(original) + 1.0
    else:
        pe[first_key] = "MUTATED_FOR_FALSIFIABILITY"
    assert pe[first_key] != original

    before_path = tmp_path / "before.json"
    after_path = tmp_path / "after_mutated.json"
    before_path.write_text(
        json.dumps(base, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8"
    )
    after_path.write_text(
        json.dumps(mutated, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8"
    )

    compare_script = REPO_ROOT / "scripts" / "ic1d_compare.py"
    # 零-allow deep no-op：有 results 差異 → exit != 0
    proc = subprocess.run(
        [sys.executable, str(compare_script), str(before_path), str(after_path)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode != 0, (
        "mutation FAIL: results leaf changed but zero-allow compare exited 0 "
        f"(stdout={proc.stdout!r} stderr={proc.stderr!r})"
    )
    # 正向對照：未改檔自比必須 PASS
    proc_ok = subprocess.run(
        [sys.executable, str(compare_script), str(before_path), str(before_path)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc_ok.returncode == 0, (
        "control FAIL: identical golden self-compare must exit 0 "
        f"(stdout={proc_ok.stdout!r} stderr={proc_ok.stderr!r})"
    )


# ---------------------------------------------------------------------------
# Bug1 / Bug2 comparator 單元探針（不依賴 kline / production）
# ---------------------------------------------------------------------------


def test_bug1_dict_vs_list_path_collision_must_report() -> None:
    """Bug1：dict key \"0\" vs list index 0 不得 flatten 成同 path 而漏報結構變更。"""
    from scripts.ic1d_compare import compare_payloads, flatten_leaves

    dict_side = {"data": {"0": 100}}
    list_side = {"data": [100]}
    flat_d = flatten_leaves(dict_side)
    flat_l = flatten_leaves(list_side)
    # 路徑必須可區分：dict → data.0；list → data[0]
    assert "data.0" in flat_d
    assert "data[0]" in flat_l
    assert set(flat_d.keys()) != set(flat_l.keys()), (
        "Bug1 FAIL: dict key '0' 與 list index 0 flatten path 碰撞"
    )
    violations = compare_payloads(dict_side, list_side)
    assert violations, (
        "Bug1 FAIL: dict{'0':100} vs list[100] 應報結構變更，卻回 []"
    )
    # 值相同的同構 dict 仍應 PASS
    assert compare_payloads(dict_side, {"data": {"0": 100}}) == []
    assert compare_payloads(list_side, {"data": [100]}) == []


def test_bug1_mutation_list_to_dict_zero_allow_must_fail(tmp_path: Path) -> None:
    """Bug1 mutation：before=dict key / after=list → CLI 零-allow 必須 exit!=0。"""
    import subprocess

    before = {"data": {"0": 100}}
    after = {"data": [100]}
    bp = tmp_path / "bug1_before.json"
    ap = tmp_path / "bug1_after.json"
    bp.write_text(json.dumps(before) + "\n", encoding="utf-8")
    ap.write_text(json.dumps(after) + "\n", encoding="utf-8")
    compare_script = REPO_ROOT / "scripts" / "ic1d_compare.py"
    proc = subprocess.run(
        [sys.executable, str(compare_script), str(bp), str(ap)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode != 0, (
        "Bug1 mutation FAIL: dict vs list 結構變更卻 exit0 "
        f"(stdout={proc.stdout!r} stderr={proc.stderr!r})"
    )


def test_bug2_dotted_key_allow_change_must_pass() -> None:
    """Bug2：含點 key 的 --allow-change 未 escape 字面必須生效（對稱匹配）。"""
    from scripts.ic1d_compare import compare_payloads, flatten_leaves

    before = {"metrics": {"return_1d.ic": 1.0}}
    after = {"metrics": {"return_1d.ic": 2.0}}
    flat = flatten_leaves(before)
    # flatten 對 key 內點做 escape
    assert any("return_1d" in p and "ic" in p for p in flat)
    # 無 allow → 必須報變更
    assert compare_payloads(before, after), "setup: dotted-key change must violate"
    # 未 escape allow 字面 → 修後必須 PASS（Bug2 主驗收）
    assert (
        compare_payloads(
            before, after, allow_change=["metrics.return_1d.ic"]
        )
        == []
    ), "Bug2 FAIL: unescaped allow-change 應涵蓋含點 key"
    # 明確 escape 形式仍可用
    assert (
        compare_payloads(
            before, after, allow_change=[r"metrics.return_1d\.ic"]
        )
        == []
    )
    # 正常無點階層路徑語意不變
    nested_b = {"metrics": {"return_1d": {"ic": 1.0}}}
    nested_a = {"metrics": {"return_1d": {"ic": 2.0}}}
    assert (
        compare_payloads(
            nested_b, nested_a, allow_change=["metrics.return_1d.ic"]
        )
        == []
    )
    # 無關 allow 不得吞掉其他變更
    other_b = {"metrics": {"return_1d.ic": 1.0, "other": 1}}
    other_a = {"metrics": {"return_1d.ic": 2.0, "other": 9}}
    viol = compare_payloads(
        other_b, other_a, allow_change=["metrics.return_1d.ic"]
    )
    assert viol and any("other" in v for v in viol)


def test_bug2_dotted_key_allow_cli_exit0(tmp_path: Path) -> None:
    """Bug2 CLI：--allow-change metrics.return_1d.ic 對含點 key 變更 → exit0。"""
    import subprocess

    before = {"metrics": {"return_1d.ic": 1.0}}
    after = {"metrics": {"return_1d.ic": 2.0}}
    bp = tmp_path / "bug2_before.json"
    ap = tmp_path / "bug2_after.json"
    bp.write_text(json.dumps(before) + "\n", encoding="utf-8")
    ap.write_text(json.dumps(after) + "\n", encoding="utf-8")
    compare_script = REPO_ROOT / "scripts" / "ic1d_compare.py"
    # 無 allow → exit1
    proc_fail = subprocess.run(
        [sys.executable, str(compare_script), str(bp), str(ap)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc_fail.returncode != 0, "control: no-allow dotted change must fail"
    # 未 escape allow → exit0
    proc_ok = subprocess.run(
        [
            sys.executable,
            str(compare_script),
            str(bp),
            str(ap),
            "--allow-change",
            "metrics.return_1d.ic",
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc_ok.returncode == 0, (
        "Bug2 CLI FAIL: unescaped allow-change 應 exit0 "
        f"(stdout={proc_ok.stdout!r} stderr={proc_ok.stderr!r})"
    )


def test_path_collision_bracket_key_vs_list_must_not_silent_pass() -> None:
    """B0 rem3：dict key \"x[0]\" vs list x[0] 不得靜默漏報；path 可區分或 raise。

    修前：兩者皆 flatten 成 x[0] → 值同則 zero-allow exit0（漏報）。
    修後：key 內括號 escape → 路徑不同 → compare 報差異；
    同物件同時含兩者時 → PathCollisionError fail-closed。
    """
    from scripts.ic1d_compare import (
        PathCollisionError,
        compare_payloads,
        flatten_leaves,
    )

    bracket_key = {"data": {"x[0]": 100}}
    list_side = {"data": {"x": [100]}}
    flat_k = flatten_leaves(bracket_key)
    flat_l = flatten_leaves(list_side)
    # escape 後路徑必須可區分：key → data.x\\[0\\]；list → data.x[0]
    assert "data.x[0]" in flat_l
    assert "data.x[0]" not in flat_k, (
        "bracket-key 不得與 list index 共用 path data.x[0]"
    )
    assert any("x" in p and "0" in p for p in flat_k)
    assert set(flat_k.keys()) != set(flat_l.keys())
    violations = compare_payloads(bracket_key, list_side)
    assert violations, (
        "dict{'x[0]':100} vs dict{'x':[100]} 應報結構差異，不得靜默 []"
    )
    # 同物件同時含「含括號 key」與「list 子樹」：escape 後路徑可區分、不誤 raise
    colliding = {"x[0]": 100, "x": [100]}
    flat_c = flatten_leaves(colliding)
    assert len(flat_c) == 2
    assert "x[0]" in flat_c  # list 結構 index
    assert r"x\[0\]" in flat_c  # dict key 含括號（已 escape）
    # 模擬 metachar 漏 escape → 兩結構位置撞成同 path → fail-closed raise
    import scripts.ic1d_compare as cmp

    def _no_bracket_escape(key: Any) -> str:
        # 只 escape \\ 與 .，故意不 escape [ ] → 觸發 path 碰撞
        text = str(key)
        return text.replace("\\", "\\\\").replace(".", "\\.")

    with patch.object(cmp, "_escape_path_segment", _no_bracket_escape):
        with pytest.raises(PathCollisionError, match="多個結構位置"):
            flatten_leaves({"x[0]": 100, "x": [100]})
    # patch 結束後真實 escape 仍含括號
    assert cmp._escape_path_segment("x[0]") == r"x\[0\]"


def test_path_collision_raise_via_cli_exit1(tmp_path: Path) -> None:
    """B0 rem3 CLI：bracket-key vs list 結構變更 → exit!=0（非靜默 exit0）。"""
    import subprocess

    before = {"data": {"x[0]": 100}}
    after = {"data": {"x": [100]}}
    bp = tmp_path / "coll_before.json"
    ap = tmp_path / "coll_after.json"
    bp.write_text(json.dumps(before) + "\n", encoding="utf-8")
    ap.write_text(json.dumps(after) + "\n", encoding="utf-8")
    compare_script = REPO_ROOT / "scripts" / "ic1d_compare.py"
    proc = subprocess.run(
        [sys.executable, str(compare_script), str(bp), str(ap)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode != 0, (
        "path collision class FAIL: bracket-key vs list 卻 exit0 "
        f"(stdout={proc.stdout!r} stderr={proc.stderr!r})"
    )
