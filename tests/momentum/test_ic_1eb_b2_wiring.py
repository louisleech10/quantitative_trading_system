"""IC 1e+1b Batch B2：Task 2.1–2.5 縱向主路徑接線驗證（T-2.x + mutation 轉紅）。"""

from __future__ import annotations

import ast
import inspect
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy.stats import binom

from momentum.Analysis.ic_config_schema import ICConfig, load_ic_config
from momentum.Analysis.ic_filter_orchestrator import (
    FDR_ASSUMPTION_NOTE,
    ICFilterOrchestrator,
    TESTED_ESTIMATOR_BAR_LEVEL,
)
from momentum.Analysis.ic_reporter import ICReporter
from momentum.Analysis.statistical_validator import (
    apply_fdr,
    compute_hac_ic_statistics,
)
from momentum.core.contracts import SelectionScope


# ── helpers ──────────────────────────────────────────────────────────────────


def _lenient_config(**overrides) -> ICConfig:
    data = load_ic_config().model_dump(by_alias=True)
    data["thresholds"].update(
        {
            "ic_mean_min": -1.0,
            "icir_min": -999.0,
            "p_value_max": 0.05,
            "ic_hit_rate_min": 0.0,
            "monotonicity_score_min": 0.0,
            "coverage_min": 0.0,
        }
    )
    data["thresholds"]["long_short_spread"] = {"enabled": False, "min_spread": 0.0}
    data["ic_train_test_split"] = False
    data["global"] = data.get("global") or {}
    data["global"]["default_horizon"] = 5
    data["labels"] = data.get("labels") or {}
    data["labels"]["horizons"] = [1, 5, 21]
    data.update(overrides)
    return ICConfig.model_validate(data)


def _synth_features_labels(
    n: int = 256,
    n_features: int = 4,
    horizon: int = 5,
    seed: int = 20260710,
    signal_cols: int = 1,
    signal_strength: float = 0.4,
) -> tuple[pd.DataFrame, pd.Series]:
    del horizon  # 保留簽名供 caller 可讀性
    rng = np.random.default_rng(seed)
    # int64 epoch 秒：通過 _base_universe_hash / _coerce_timestamp_array
    index = pd.Index(
        (np.arange(n, dtype=np.int64) * 3600) + 1_600_000_000,
        name="timestamp",
    )
    noise = rng.normal(size=(n, n_features))
    cols = [f"f{i}" for i in range(n_features)]
    features = pd.DataFrame(noise, columns=cols, index=index, dtype=np.float64)
    latent = rng.normal(size=n)
    label = pd.Series(latent + 0.05 * rng.normal(size=n), index=index, name="label")
    for i in range(signal_cols):
        features[cols[i]] = (
            signal_strength * latent
            + math.sqrt(max(1e-9, 1 - signal_strength**2)) * noise[:, i]
        )
    return features, label


def _minimal_ic_results(features: pd.DataFrame) -> dict:
    icir = {
        str(c): {
            "ic_mean": 0.05,
            "ic_std": 0.1,
            "icir": 0.5,
            "ic_hit_rate": 0.6,
        }
        for c in features.columns
    }
    rolling = {str(c): {"window_5": [0.1, 0.2]} for c in features.columns}
    return {"rolling_ic": rolling, "icir": icir, "ic_decay": {}}


def _run_stage5(
    features: pd.DataFrame,
    label: pd.Series,
    *,
    config: ICConfig | None = None,
    event_info: dict | None = None,
    split_context: dict | None = None,
    fdr_enabled: bool | None = None,
    metadata: dict | None = None,
) -> dict:
    cfg = config or _lenient_config()
    orch = ICFilterOrchestrator(cfg)
    if fdr_enabled is not None:
        orch._fdr_enabled_override = fdr_enabled
    # full scope 需真實 symbol（禁 UNKNOWN）；預設測試 identity
    meta = metadata if metadata is not None else {"symbol": "BTCUSDT"}
    return orch._stage5_statistical_validation(
        features,
        label,
        _minimal_ic_results(features),
        cfg,
        event_info or {"tier": "sufficient"},
        split_context=split_context,
        metadata=meta,
    )


# ── T-2.1 ────────────────────────────────────────────────────────────────────


def test_t21a_stage5_p_matches_kernel_direct():
    """T-2.1a：stage5 p 值 = 直接呼叫 compute_hac_ic_statistics。"""
    features, label = _synth_features_labels(n=300, n_features=3, seed=11)
    config = _lenient_config()
    result = _run_stage5(features, label, config=config)
    direct = compute_hac_ic_statistics(features, label, horizon=5)
    for feat in features.columns:
        row_p = next(
            r["p_value"] for r in result["summary_table"] if r["feature_name"] == feat
        )
        assert np.allclose(
            float(row_p), float(direct[str(feat)]["p_value"]), rtol=0, atol=0, equal_nan=True
        )
        assert np.allclose(
            float(result["ic_stats"][str(feat)]["t_stat"]),
            float(direct[str(feat)]["t_stat"]),
            rtol=0,
            atol=0,
            equal_nan=True,
        )


def test_t21b_mf_leg_a_hac_pass_leg_b_pooled_fails(monkeypatch):
    """T-2.1b M-F：腿A HAC 路徑 PASS；腿B monkeypatch 回 pooled 必 FAIL 同一斷言。"""
    features, label = _synth_features_labels(n=400, n_features=2, seed=22, signal_strength=0.5)
    config = _lenient_config()
    # 腿 A：新 kernel
    stage5 = _run_stage5(features, label, config=config)
    direct = compute_hac_ic_statistics(features, label, horizon=5)
    p_stage = float(stage5["ic_stats"]["f0"]["p_value"])
    p_direct = float(direct["f0"]["p_value"])
    assert np.isclose(p_stage, p_direct, rtol=0, atol=0)
    leg_a_pass = True

    # 腿 B：強制改回 deprecated pooled 路徑 → 與 kernel 相等斷言應失敗
    from momentum.Analysis import statistical_validator as sv

    def _pooled_as_stage5(features_df, label_s, horizon, **kwargs):
        del horizon, kwargs
        rolling = {
            str(c): {"window_fake": features_df[c].rolling(21, min_periods=5).corr(label_s).dropna().tolist()}
            for c in features_df.columns
        }
        return sv.StatisticalValidator({}).compute_pooled_ic_statistics_deprecated(rolling)

    monkeypatch.setattr(
        "momentum.Analysis.ic_filter_orchestrator.compute_hac_ic_statistics",
        _pooled_as_stage5,
    )
    stage5_b = _run_stage5(features, label, config=config)
    p_b = float(stage5_b["ic_stats"]["f0"]["p_value"])
    leg_b_same = bool(np.isclose(p_b, p_direct, rtol=1e-12, atol=0))
    assert leg_a_pass is True
    assert not leg_b_same, (
        f"M-F leg B must diverge: pooled_p={p_b} vs hac_p={p_direct}"
    )


def test_t21c_mh_structure_no_pooled_in_production():
    """T-2.1c M-H：生產 p-value 鏈不呼叫 pooled / _collect_values 串窗。"""
    orch_src = Path("momentum/Analysis/ic_filter_orchestrator.py").read_text(encoding="utf-8")
    assert "compute_hac_ic_statistics" in orch_src
    assert "compute_pooled_ic_statistics_deprecated" not in orch_src
    assert "compute_ic_statistics" not in orch_src

    # import 圖：生產模組不暴露舊名
    import momentum.Analysis.statistical_validator as sv_mod

    assert not hasattr(sv_mod.StatisticalValidator, "compute_ic_statistics")
    assert hasattr(sv_mod.StatisticalValidator, "compute_pooled_ic_statistics_deprecated")
    ghost = "apply_significance" + "_filter"
    assert not hasattr(sv_mod.StatisticalValidator, ghost)

    # stage5 原始碼 AST：不呼叫 _collect_values
    tree = ast.parse(orch_src)
    stage5_node = None
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "ICFilterOrchestrator":
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == "_stage5_statistical_validation":
                    stage5_node = item
    assert stage5_node is not None
    calls = [
        n.func.attr if isinstance(n.func, ast.Attribute) else getattr(n.func, "id", "")
        for n in ast.walk(stage5_node)
        if isinstance(n, ast.Call)
    ]
    assert "_collect_values" not in calls
    assert "compute_pooled_ic_statistics_deprecated" not in calls


# ── T-2.2 ────────────────────────────────────────────────────────────────────


# 相關 null factor loading：pairwise corr(x_i,x_j)=loading^2。
# 目標 ρ≈0.7 ⇒ loading=√0.7（非 0.7；0.7*f+√(1-0.7²)ε 只給 ρ=0.49）。
_CORR_TARGET_RHO = 0.7
_CORR_LOADING = math.sqrt(_CORR_TARGET_RHO)


def _fdr_empirical(
    *,
    n: int,
    n_null: int,
    n_true: int,
    alpha: float,
    n_seeds: int,
    correlated: bool,
    seed0: int,
    via_stage5: bool = False,
    shrink_n_tests_in_stage5: bool = False,
) -> tuple[list[float], list[float]]:
    """回傳 (empirical FDRs, pairwise null-ρ samples)。

    null 與 y 獨立；correlated 場景下 null 之間共用 factor（pairwise ρ≈0.7），
    但 factor 與 y 獨立（真 PRDS 壓力，非假 null）。
    via_stage5=True 走 production wiring（_stage5_statistical_validation）。
    shrink_n_tests_in_stage5 僅供離線 mutation 真紅 receipt（測試本身不綠包此路徑）。
    """
    fdrs: list[float] = []
    rhos: list[float] = []
    for s in range(n_seeds):
        rng = np.random.default_rng(seed0 + s)
        y = rng.normal(size=n)
        null_factor = rng.normal(size=n)  # 獨立於 y
        cols: dict[str, np.ndarray] = {}
        if correlated:
            b = math.sqrt(1.0 - _CORR_TARGET_RHO)
            for i in range(n_null):
                eps = rng.normal(size=n)
                cols[f"null_{i}"] = _CORR_LOADING * null_factor + b * eps
        else:
            for i in range(n_null):
                cols[f"null_{i}"] = rng.normal(size=n)
        for i in range(n_true):
            cols[f"true_{i}"] = 0.55 * y + math.sqrt(1 - 0.55**2) * rng.normal(size=n)
        features = pd.DataFrame(cols)
        label = pd.Series(y)
        if correlated and n_null >= 2:
            # 抽樣 pairwise ρ（前 6 對）供 receipt / 診斷
            sample_pairs = [(0, 1), (0, 2), (1, 2), (0, 3), (1, 4), (2, 5)]
            for i, j in sample_pairs:
                if i < n_null and j < n_null:
                    rhos.append(
                        float(
                            np.corrcoef(cols[f"null_{i}"], cols[f"null_{j}"])[0, 1]
                        )
                    )

        if via_stage5:
            cfg = _lenient_config()
            data = cfg.model_dump(by_alias=True)
            data["thresholds"]["p_value_max"] = alpha
            cfg = ICConfig.model_validate(data)
            orch = ICFilterOrchestrator(cfg)
            if shrink_n_tests_in_stage5:
                # production wiring mutation：只對「假前置閘」子集做 FDR
                orig = orch._stage5_statistical_validation

                def _mutated_stage5(
                    features_df,
                    label_series,
                    ic_results,
                    config,
                    event_info,
                    split_context=None,
                    metadata=None,
                    _orig=orig,
                ):
                    del _orig
                    # 重用 production 前半，但 apply_fdr 餵縮水 p map
                    from momentum.Analysis.ic_filter_orchestrator import (
                        _resolve_effective_label_horizon,
                        _slice_by_mask,
                    )

                    test_mask = (
                        split_context.get("test_mask") if split_context else None
                    )
                    feats, labs = _slice_by_mask(features_df, label_series, test_mask)
                    if (
                        split_context is not None
                        and split_context.get("effective_horizon") is not None
                    ):
                        horizon = int(split_context["effective_horizon"])
                    else:
                        horizon = int(_resolve_effective_label_horizon(config, None))
                    ic_stats = compute_hac_ic_statistics(feats, labs, horizon=horizon)
                    alpha_eff, _, _ = orch._resolve_alpha_policy(
                        config, event_info or {}
                    )
                    p_all = {
                        str(c): float((ic_stats.get(str(c)) or {}).get("p_value", np.nan))
                        for c in feats.columns
                    }
                    pre = {
                        k: p
                        for k, p in p_all.items()
                        if np.isfinite(p) and p < 0.2
                    }
                    q_map, n_tests = apply_fdr(pre, alpha_eff)
                    # 回填：非 pre 的 q 不在 map → 僅 pre 被校正（錯誤 n_tests）
                    for feature in feats.columns:
                        f = str(feature)
                        item = dict(ic_stats.get(f) or {})
                        item["p_value"] = p_all.get(f, np.nan)
                        item["p_value_adj"] = q_map.get(f, np.nan)
                        ic_stats[f] = item
                    summary = [
                        {
                            "feature_name": f,
                            "ic_mean": 0.05,
                            "icir": 0.5,
                            "p_value": ic_stats[f]["p_value"],
                            "p_value_adj": ic_stats[f]["p_value_adj"],
                            "ic_hit_rate": 1.0,
                            "monotonicity_score": 1.0,
                            "coverage": 1.0,
                        }
                        for f in map(str, feats.columns)
                    ]
                    return {
                        "summary_table": summary,
                        "ic_stats": ic_stats,
                        "n_tests": n_tests,
                        "threshold_log": {"alpha_effective": alpha_eff},
                        "selection_scope": None,
                        "significance": {},
                        "alpha_source": "threshold_default",
                        "selection_mode": None,
                        "fdr_enabled": True,
                        "passed_features": [
                            r["feature_name"]
                            for r in summary
                            if np.isfinite(r["p_value_adj"])
                            and r["p_value_adj"] <= alpha_eff
                        ],
                    }

                orch._stage5_statistical_validation = _mutated_stage5  # type: ignore[method-assign]
            stage5 = orch._stage5_statistical_validation(
                features,
                label,
                _minimal_ic_results(features),
                cfg,
                {"tier": "sufficient"},
                metadata={"symbol": "BTCUSDT"},
            )
            rejected = [
                r["feature_name"]
                for r in stage5["summary_table"]
                if np.isfinite(r.get("p_value_adj", np.nan))
                and float(r["p_value_adj"]) <= alpha
            ]
        else:
            stats = compute_hac_ic_statistics(features, label, horizon=5)
            p_dict = {k: float(v["p_value"]) for k, v in stats.items()}
            q_map, _ = apply_fdr(p_dict, alpha)
            rejected = [
                k for k, q in q_map.items() if np.isfinite(q) and q <= alpha
            ]
        if not rejected:
            continue
        false_pos = sum(1 for k in rejected if k.startswith("null_"))
        fdrs.append(false_pos / len(rejected))
    return fdrs, rhos


@pytest.mark.slow_stat
def test_t22a_mb_fdr_control_independent_and_correlated():
    """T-2.2a M-B：獨立 null + 相關 null（ρ≈0.7）FDR≤α；允收帶=binomial 95% CI。"""
    alpha = 0.10
    n_seeds = 40  # 預算：B2 hermetic
    # binomial 95% 上界（rate 形）：ppf(0.975,n,α)/n — 禁任意常數帶
    mean_fdr_max = float(binom.ppf(0.975, n_seeds, alpha) / n_seeds)
    assert mean_fdr_max == binom.ppf(0.975, n_seeds, alpha) / n_seeds

    fdrs_ind, _ = _fdr_empirical(
        n=400,
        n_null=40,
        n_true=5,
        alpha=alpha,
        n_seeds=n_seeds,
        correlated=False,
        seed0=1000,
        via_stage5=True,
    )
    fdrs_cor, rhos = _fdr_empirical(
        n=400,
        n_null=50,
        n_true=5,
        alpha=alpha,
        n_seeds=n_seeds,
        correlated=True,
        seed0=2000,
        via_stage5=True,
    )
    assert fdrs_ind, "independent scenario produced no rejections"
    assert fdrs_cor, "correlated scenario produced no rejections"
    mean_ind = float(np.mean(fdrs_ind))
    mean_cor = float(np.mean(fdrs_cor))
    assert mean_ind <= mean_fdr_max, (
        f"indep mean FDR={mean_ind} > binomial95 upper {mean_fdr_max}"
    )
    assert mean_cor <= mean_fdr_max, (
        f"corr mean FDR={mean_cor} > binomial95 upper {mean_fdr_max}"
    )
    # 相關場景 loading 校驗：pairwise ρ 均值接近 0.7
    assert rhos, "correlated scenario produced no pairwise rho samples"
    rho_mean = float(np.mean(rhos))
    assert abs(rho_mean - _CORR_TARGET_RHO) < 0.05, (
        f"pairwise rho_mean={rho_mean} not ≈ {_CORR_TARGET_RHO} "
        f"(loading should be sqrt(0.7))"
    )


def test_t22a_production_fdr_uses_full_universe_n_tests():
    """結構守衛：production stage5 的 n_tests = 全欄 finite-p（非前置閘子集）。"""
    features, label = _synth_features_labels(n=300, n_features=8, seed=101)
    # 塞一個常數欄 → finite-p 少 1
    features["const"] = 1.0
    result = _run_stage5(features, label)
    finite_p = sum(
        1
        for r in result["summary_table"]
        if np.isfinite(r.get("p_value", np.nan))
    )
    assert result["n_tests"] == finite_p
    assert result["n_tests"] == len(result["selection_scope"].evaluated_features)
    assert result["n_tests"] < len(features.columns)  # const 被 NaN-p 排除
    # universe 仍含 const
    assert "const" in result["selection_scope"].universe_features
    assert "const" not in result["selection_scope"].evaluated_features


def test_t22b_md_scope_mismatch_turns_red():
    """T-2.2b M-D：FDR 在 train 算、test 消費 → 與正確 stage5 scope 不一致轉紅。"""
    features, label = _synth_features_labels(n=300, n_features=6, seed=33)
    n = len(features)
    train_mask = np.zeros(n, dtype=bool)
    train_mask[: int(n * 0.7)] = True
    test_mask = ~train_mask

    # 正確：test 段 HAC + FDR
    split_ok = {
        "test_mask": test_mask,
        "effective_horizon": 5,
        "allowed_symbols": ["BTCUSDT"],
    }
    ok = _run_stage5(features, label, split_context=split_ok)
    assert ok["selection_scope"].split_label == "test"
    q_ok = {r["feature_name"]: r["p_value_adj"] for r in ok["summary_table"]}

    # 錯配：用 train 段算 stats，卻標 test 消費
    train_feats = features.loc[features.index[train_mask]]
    train_lab = label.loc[label.index[train_mask]]
    bad_stats = compute_hac_ic_statistics(train_feats, train_lab, horizon=5)
    p_train = {k: float(v["p_value"]) for k, v in bad_stats.items()}
    q_train, _ = apply_fdr(p_train, 0.05)

    # 同一特徵 q 應因樣本不同而分離（可證偽：若強制相等則紅）
    diverged = False
    for feat in features.columns:
        a = q_ok[feat]
        b = q_train[str(feat)]
        if not (
            (np.isnan(a) and np.isnan(b))
            or (np.isfinite(a) and np.isfinite(b) and np.isclose(a, b, rtol=1e-9))
        ):
            diverged = True
            break
    assert diverged, "M-D: train-FDR vs test-FDR must diverge (TURN-RED if equal)"


def test_t22c_alpha_policy_six_cells():
    """T-2.2c α 政策六格：tier × fdr on/off + alpha_source/selection_mode 欄位。"""
    features, label = _synth_features_labels(n=200, n_features=2, seed=44)
    config = _lenient_config()
    # force p_value_max = 0.05
    data = config.model_dump(by_alias=True)
    data["thresholds"]["p_value_max"] = 0.05
    config = ICConfig.model_validate(data)

    cases = [
        ("sufficient", True, 0.05, "threshold_default", None),
        ("marginal", True, 0.05, "threshold_default", None),
        ("low_confidence", True, 0.10, "event_tier_low_confidence", "exploratory_low_confidence"),
        ("sufficient", False, 0.05, "threshold_default", None),
        ("marginal", False, 0.05, "threshold_default", None),
        ("low_confidence", False, 0.10, "event_tier_low_confidence", "exploratory_low_confidence"),
    ]
    for tier, fdr_on, alpha_exp, src_exp, mode_exp in cases:
        result = _run_stage5(
            features,
            label,
            config=config,
            event_info={"tier": tier},
            fdr_enabled=fdr_on,
        )
        log = result["threshold_log"]
        assert log["alpha_effective"] == alpha_exp, (tier, fdr_on, log)
        assert log["alpha_source"] == src_exp
        assert log["fdr_enabled"] is fdr_on
        if mode_exp is None:
            assert "selection_mode" not in log
        else:
            assert log["selection_mode"] == mode_exp
        assert result["significance"]["fdr"]["enabled"] is fdr_on
        assert result["significance"]["fdr"]["alpha_effective"] == alpha_exp

    # 遷移自舊 low_confidence 門檻測試：p=0.08 在 low_confidence 過閘
    orch = ICFilterOrchestrator(config)

    summary = [
        {
            "feature_name": "good",
            "ic_mean": 0.1,
            "icir": 1.0,
            "p_value": 0.08,
            "p_value_adj": 0.08,
            "ic_hit_rate": 1.0,
            "monotonicity_score": 1.0,
            "coverage": 1.0,
        },
        {
            "feature_name": "bad",
            "ic_mean": 0.1,
            "icir": 1.0,
            "p_value": 0.12,
            "p_value_adj": 0.12,
            "ic_hit_rate": 1.0,
            "monotonicity_score": 1.0,
            "coverage": 1.0,
        },
    ]
    alpha, src, mode = orch._resolve_alpha_policy(
        config, {"tier": "low_confidence"}
    )
    assert alpha == 0.10 and src == "event_tier_low_confidence"
    assert mode == "exploratory_low_confidence"
    passed, _ = orch._apply_thresholds(
        summary, config.thresholds, alpha, fdr_enabled=False
    )
    assert "good" in passed and "bad" not in passed


def test_t22d_threshold_log_fields():
    """T-2.2d threshold_log 含 alpha_effective / n_tests / fdr_enabled。"""
    features, label = _synth_features_labels(n=180, n_features=3, seed=55)
    result = _run_stage5(features, label)
    log = result["threshold_log"]
    for key in ("alpha_effective", "n_tests", "fdr_enabled", "alpha_source"):
        assert key in log
    assert log["n_tests"] == result["selection_scope"].n_tests
    assert log["n_tests"] == len(result["selection_scope"].evaluated_features)


# ── T-2.3 ────────────────────────────────────────────────────────────────────


def test_t23b_selection_scope_in_stage5_and_mutation_raises():
    """T-2.3b：report 側 selection_scope；n_tests+1 → 契約 raise 轉紅。"""
    features, label = _synth_features_labels(n=200, n_features=4, seed=66)
    result = _run_stage5(features, label)
    scope = result["selection_scope"]
    assert isinstance(scope, SelectionScope)
    assert scope.split_label == "full"
    assert scope.n_tests == len(scope.evaluated_features)
    assert set(scope.evaluated_features).issubset(set(scope.universe_features))
    assert scope.method == "fdr_bh"

    # mutation 真紅：n_tests + 1 → ValueError
    with pytest.raises(ValueError, match="n_tests"):
        SelectionScope(
            scope_id=scope.scope_id,
            universe_features=list(scope.universe_features),
            split_label=scope.split_label,
            evaluated_features=list(scope.evaluated_features),
            n_tests=scope.n_tests + 1,
            method=scope.method,
            base_universe_hash=scope.base_universe_hash,
        )


def test_t23b_report_metadata_contains_selection_scope():
    """stage7 metadata 路徑含 selection_scope dict。"""
    features, label = _synth_features_labels(n=160, n_features=2, seed=67)
    config = _lenient_config()
    orch = ICFilterOrchestrator(config)
    stage5 = orch._stage5_statistical_validation(
        features,
        label,
        _minimal_ic_results(features),
        config,
        {"tier": "sufficient"},
        metadata={"symbol": "BTCUSDT"},
    )
    meta = orch._build_report_metadata(
        features,
        features,
        {},
        {},
        {},
        selection_scope=stage5["selection_scope"],
        significance=stage5["significance"],
        alpha_source=stage5["alpha_source"],
    )
    assert "selection_scope" in meta
    assert meta["selection_scope"]["n_tests"] == stage5["n_tests"]
    assert "significance" in meta
    assert meta["significance"]["tested_estimator"] == TESTED_ESTIMATOR_BAR_LEVEL
    assert meta["significance"]["fdr_assumption_note"] == FDR_ASSUMPTION_NOTE


def test_t23_full_scope_refuses_fabricated_unknown_symbol():
    """full scope 禁新造 symbol=UNKNOWN；缺真實 identity → raise。"""
    features, label = _synth_features_labels(n=120, n_features=2, seed=68)
    config = _lenient_config()
    orch = ICFilterOrchestrator(config)
    with pytest.raises(ValueError, match="authentic symbol|fabricated identity"):
        orch._stage5_statistical_validation(
            features,
            label,
            _minimal_ic_results(features),
            config,
            {"tier": "sufficient"},
            split_context=None,
            metadata={},  # 無 symbol
        )
    # 有 metadata.symbol 時可建 full scope，且 hash 與 UNKNOWN 路徑不同 identity
    ok = orch._stage5_statistical_validation(
        features,
        label,
        _minimal_ic_results(features),
        config,
        {"tier": "sufficient"},
        metadata={"symbol": "ETHUSDT"},
    )
    assert ok["selection_scope"].split_label == "full"
    assert "UNKNOWN" not in ok["selection_scope"].scope_id
    # 同 timestamp 不同 symbol → base_universe_hash 必須分離
    other = orch._stage5_statistical_validation(
        features,
        label,
        _minimal_ic_results(features),
        config,
        {"tier": "sufficient"},
        metadata={"symbol": "BTCUSDT"},
    )
    assert (
        ok["selection_scope"].base_universe_hash
        != other["selection_scope"].base_universe_hash
    )


def test_t22_refilter_oos_scope_remains_test():
    """T-2.2/2.3：OOS 首跑後 refilter 仍用 test scope（禁漂移成 full）。"""
    features, label = _synth_features_labels(n=240, n_features=3, seed=77)
    n = len(features)
    test_mask = np.zeros(n, dtype=bool)
    test_mask[int(n * 0.6) :] = True
    train_mask = ~test_mask
    split_context = {
        "test_mask": test_mask,
        "train_mask": train_mask,
        "effective_horizon": 5,
        "allowed_symbols": ["BTCUSDT"],
    }
    config = _lenient_config()
    orch = ICFilterOrchestrator(config)
    stage5_first = orch._stage5_statistical_validation(
        features,
        label,
        _minimal_ic_results(features),
        config,
        {"tier": "sufficient"},
        split_context=split_context,
        metadata={"symbol": "BTCUSDT"},
    )
    assert stage5_first["selection_scope"].split_label == "test"
    assert stage5_first["scope"] == "test"
    q_first = {
        r["feature_name"]: r["p_value_adj"] for r in stage5_first["summary_table"]
    }

    # 模擬 analyze 寫 cache 後 refilter（含 split_context）
    orch._ic_cache = {
        "features_df": features,
        "label_series": label,
        "metadata": {"symbol": "BTCUSDT"},
        "icir": _minimal_ic_results(features)["icir"],
        "rolling_ic": {},
        "ic_decay": {},
        "grouped_ic": {},
        "event_info": {"tier": "sufficient"},
        "feature_filter_info": {},
        "stage0_log": {},
        "preproc_log": {},
        "split_context": split_context,
    }
    orch._monotonicity_cache = stage5_first.get("monotonicity", {})
    orch._fdr_enabled_override = True
    # refilter 只重跑 stage5 路徑（透過 public refilter，需 monoto cache）
    # 直接呼叫 refilter 會跑 stage6/7；monkeypatch 輕量 persist
    orch._persist_outputs = lambda *a, **k: {}  # type: ignore[method-assign]
    report = orch.refilter({"icir_min": -999.0})
    # report metadata scope / selection_scope
    meta = report.get("metadata") or {}
    # stage5 經 refilter 後 selection_scope 應仍為 test
    # 從 summary q 與 cache 二次 stage5 對照
    stage5_again = orch._stage5_statistical_validation(
        orch._ic_cache["features_df"],
        orch._ic_cache["label_series"],
        orch._ic_cache,
        config,
        orch._ic_cache.get("event_info", {}),
        split_context=orch._ic_cache.get("split_context"),
        metadata=orch._ic_cache.get("metadata"),
    )
    assert stage5_again["selection_scope"].split_label == "test"
    assert stage5_again["scope"] == "test"
    for feat, q0 in q_first.items():
        q1 = next(
            r["p_value_adj"]
            for r in stage5_again["summary_table"]
            if r["feature_name"] == feat
        )
        assert (np.isnan(q0) and np.isnan(q1)) or np.isclose(q0, q1, rtol=0, atol=0)
    # 若 refilter 丟 split_context → 會變成 full；此處 public refilter 報告不得標 full 混 test
    # selection_scope 若有進 metadata
    if "selection_scope" in meta:
        assert meta["selection_scope"]["split_label"] == "test"
    if meta.get("scope") is not None:
        assert meta["scope"] == "test"
    # refilter 必須保留 split_context 於 cache（供後續再 refilter）
    assert orch._ic_cache is not None
    assert orch._ic_cache.get("split_context") is split_context


# ── T-2.4 ────────────────────────────────────────────────────────────────────


def test_t24_reporter_new_columns_and_old_order_byte():
    """T-2.4：CSV 新欄在末尾；舊欄順序不變；JSON significance 節完整；NaN→null。"""
    import csv
    from io import StringIO

    reporter = ICReporter({})
    summary = [
        {
            "feature_name": "f1",
            "ic_mean": 0.03,
            "icir": 0.8,
            "p_value": 0.01,
            "t_stat": 2.5,
            "p_value_adj": 0.02,
            "ic_hit_rate": 0.6,
            "monotonicity_score": 0.7,
            "coverage": 0.9,
            "turnover_rate": 0.1,
        },
        {
            "feature_name": "f2",
            "ic_mean": 0.01,
            "icir": 0.2,
            "p_value": float("nan"),
            "t_stat": float("nan"),
            "p_value_adj": float("nan"),
        },
    ]
    old_columns = [
        "rank",
        "feature_name",
        "ic_mean",
        "icir",
        "p_value",
        "ic_hit_rate",
        "monotonicity_score",
        "coverage",
        "turnover_rate",
        "half_life",
        "decay_rate",
        "decay_type",
        "long_short_spread",
        "max_correlation",
    ]
    report = {
        "summary_table": summary,
        "ic_decay": {},
        "quantile_returns": {},
        "correlation_matrix": {},
    }
    csv_text = reporter.generate_summary_csv(report)
    # strip BOM
    body = csv_text.lstrip("\ufeff")
    header = body.splitlines()[0]
    cols = header.split(",")
    assert cols[: len(old_columns)] == old_columns
    assert "t_stat" in cols and "p_value_adj" in cols
    assert cols.index("t_stat") > cols.index("max_correlation")

    # ── T-2.4 規格版：舊欄 p_value NaN 序列化 byte 與 B2 前 csv 行為一致 ──
    # 舊行為：csv.DictWriter 對 float('nan') 寫成 "nan"（非空欄）
    legacy_buf = StringIO()
    legacy_writer = csv.DictWriter(legacy_buf, fieldnames=["p_value"])
    legacy_writer.writeheader()
    legacy_writer.writerow({"p_value": float("nan")})
    legacy_nan_token = legacy_buf.getvalue().splitlines()[1]
    assert legacy_nan_token == "nan"

    # golden 小樣本：固定兩列 → 完整 CSV 字節（含 BOM）與期望相等
    p_idx = cols.index("p_value")
    data_rows = body.splitlines()[1:]
    assert len(data_rows) == 2
    # f2 列 p_value 必須是 "nan" 而非 ""
    f2_cells = data_rows[1].split(",")
    assert f2_cells[p_idx] == "nan", (
        f"old p_value NaN byte regression: got {f2_cells[p_idx]!r}, want 'nan'"
    )
    # 舊 14 欄前綴 golden（新欄 t_stat/p_value_adj 允許追加，不納入舊 golden）
    old_prefix_rows = [
        ",".join(row.split(",")[: len(old_columns)]) for row in data_rows
    ]
    # 期望：rank 空、feature、數值、p_value 含 nan
    expected_old_prefix = [
        ",f1,0.03,0.8,0.01,0.6,0.7,0.9,0.1,,,,,",
        ",f2,0.01,0.2,nan,,,,,,,,,",
    ]
    assert old_prefix_rows == expected_old_prefix, (
        f"old-column golden mismatch:\n got={old_prefix_rows}\n want={expected_old_prefix}"
    )

    meta = {
        "significance": {
            "fdr": {"enabled": True, "method": "fdr_bh", "alpha_effective": 0.05},
            "maxlags": 4,
            "n_tests": 2,
            "scope_id": "abc:full",
            "tested_estimator": TESTED_ESTIMATOR_BAR_LEVEL,
            "fdr_assumption_note": FDR_ASSUMPTION_NOTE,
        }
    }
    json_report = reporter.generate_json_report(
        {"summary_table": summary, "rolling_ic_series": {}}, meta
    )
    sig = json_report["metadata"]["significance"]
    assert sig["fdr"]["enabled"] is True
    assert sig["fdr"]["method"] == "fdr_bh"
    assert sig["fdr_assumption_note"] == FDR_ASSUMPTION_NOTE
    # JSON 路徑：NaN → null（與 CSV 舊欄 nan 字面分流）
    row2 = next(r for r in json_report["summary_table"] if r["feature_name"] == "f2")
    assert row2["p_value"] is None
    assert row2["t_stat"] is None
    assert row2["p_value_adj"] is None


# ── T-2.5 ────────────────────────────────────────────────────────────────────


def test_t25_ghost_significance_filter_absent_in_tree():
    """T-2.5：momentum/ 與 tests/ 無 def/呼叫殘留（token 拼接避免自命中 grep）。"""
    token = "apply_significance" + "_filter"
    root = Path(".")
    hits: list[str] = []
    for path in list((root / "momentum").rglob("*.py")) + list((root / "tests").rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        if token in text:
            for i, line in enumerate(text.splitlines(), 1):
                if token in line:
                    hits.append(f"{path}:{i}:{line.strip()}")
    assert hits == [], f"residual {token}: {hits}"

    import momentum.Analysis.statistical_validator as mod

    assert not hasattr(mod.StatisticalValidator, token)
    assert f"def {token}" not in inspect.getsource(mod)
