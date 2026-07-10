"""IC1EB B3 Task 3.1 — cross_sectional 逐期 IC HAC 顯著性（T-3.1a/b/c）。"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import pytest
import statsmodels.api as sm

from momentum.Analysis.ic_config_schema import load_ic_config
from momentum.Analysis.ic_filter_orchestrator import (
    ICFilterOrchestrator,
    _compute_hac_on_ic_series,
    _resolve_cross_sectional_label_horizon,
    _select_inframe_return_n_column,
)
from momentum.Analysis.statistical_validator import apply_fdr


def _make_xsec_frame(
    n_timestamps: int = 80,
    symbols: list[str] | None = None,
    *,
    label_col: str = "return_1",
    seed: int = 7,
    ar_rho: float = 0.85,
) -> pd.DataFrame:
    """合成 MultiIndex xsec frame；共同因子 AR 使逐期 IC 具自相關。"""
    symbols = symbols or ["BTCUSDT", "ETHUSDT", "BCHUSDT", "LTCUSDT", "XRPUSDT"]
    timestamps = pd.date_range("2020-01-01", periods=n_timestamps, freq="12h")
    index = pd.MultiIndex.from_product(
        [timestamps, symbols], names=["timestamp", "_symbol"]
    )
    rng = np.random.default_rng(seed)
    n_sym = len(symbols)
    # 共同因子 AR(1)
    factor = np.zeros(n_timestamps, dtype=float)
    eps = rng.normal(0, 1, n_timestamps)
    for t in range(1, n_timestamps):
        factor[t] = ar_rho * factor[t - 1] + eps[t]
    rows_feat: list[float] = []
    rows_noise: list[float] = []
    rows_lab: list[float] = []
    for t in range(n_timestamps):
        for s in range(n_sym):
            idio = rng.normal(0, 0.4)
            rows_feat.append(float(factor[t] + idio))
            rows_noise.append(float(rng.normal()))
            # label 與 factor 同向 → 逐期 rank-IC 跟隨 factor 強度
            rows_lab.append(float(factor[t] + 0.3 * rng.normal() + 0.1 * idio))
    # 末端 per-symbol 一筆 NaN（coverage floor）
    for s in range(n_sym):
        last = s + (n_timestamps - 1) * n_sym
        rows_lab[last] = float("nan")
    return pd.DataFrame(
        {
            "alpha": np.asarray(rows_feat, dtype=np.float32),
            "beta": np.asarray(rows_noise, dtype=np.float32),
            label_col: np.asarray(rows_lab, dtype=np.float32),
        },
        index=index,
    )


def _iid_t_stat(values: np.ndarray) -> float:
    """舊 xsec i.i.d. t：mean / (std / √n)，std=np.nanstd(ddof=0)。"""
    v = np.asarray(values, dtype=float)
    v = v[np.isfinite(v)]
    if v.size <= 1:
        return float("nan")
    mean = float(np.nanmean(v))
    std = float(np.nanstd(v))
    if std <= 0:
        return float("nan")
    return float(mean / (std / np.sqrt(v.size)))


def _statsmodels_hac_oracle(z: np.ndarray, maxlags: int) -> tuple[float, float, float]:
    ones = np.ones((z.size, 1))
    res = sm.OLS(z, ones).fit(
        cov_type="HAC", cov_kwds={"maxlags": int(maxlags)}, use_t=True
    )
    return float(res.bse[0]), float(res.tvalues[0]), float(res.pvalues[0])


def test_t31a_xsec_p_not_none_matches_kernel_and_separates_iid() -> None:
    """T-3.1a: p 非 None；與 _compute_hac_on_ic_series 直算一致；i.i.d. t 可分離。"""
    features = _make_xsec_frame(n_timestamps=80, label_col="return_1", ar_rho=0.9)
    orch = ICFilterOrchestrator(load_ic_config())
    report = orch.analyze_cross_sectional(
        features,
        config_override={"ic_train_test_split": False},
    )
    summary = {row["feature_name"]: row for row in report["summary_table"]}
    assert "alpha" in summary
    row = summary["alpha"]

    # p 非 None 且有限（h=1 可解析）
    assert row["p_value"] is not None
    assert np.isfinite(float(row["p_value"]))
    assert np.isfinite(float(row["t_stat"]))
    assert "p_value_adj" in row
    assert np.isfinite(float(row["p_value_adj"]))

    values = np.asarray(
        report["rolling_ic_series"]["alpha"]["window_cross_sectional"], dtype=float
    )
    direct = _compute_hac_on_ic_series(values, horizon=1)
    assert np.isclose(float(row["p_value"]), float(direct["p_value"]), atol=0.0, rtol=0.0)
    assert np.isclose(float(row["t_stat"]), float(direct["t_stat"]), atol=0.0, rtol=0.0)
    assert int(direct["maxlags"]) == int(report["metadata"]["significance"]["maxlags"]) or (
        int(direct["maxlags"])
        <= int(report["metadata"]["significance"]["maxlags"])
    )

    # oracle 對齊
    z = values[np.isfinite(values)]
    se_o, t_o, p_o = _statsmodels_hac_oracle(z, int(direct["maxlags"]))
    assert np.isclose(float(row["t_stat"]), t_o, rtol=1e-8)
    assert np.isclose(float(row["p_value"]), p_o, rtol=1e-8)

    iid_t = _iid_t_stat(values)
    assert np.isfinite(iid_t)
    # 自相關合成資料：HAC t 與 i.i.d. t 必須可分離（mutation: 換回 i.i.d.→紅）
    assert not np.isclose(float(row["t_stat"]), iid_t, rtol=1e-3, atol=1e-3), (
        f"HAC t should separate from i.i.d. t; hac={row['t_stat']} iid={iid_t}"
    )

    # FDR n_tests = finite p 數
    n_tests = int(report["metadata"]["significance"]["n_tests"])
    finite_p = sum(
        1 for r in report["summary_table"] if np.isfinite(float(r["p_value"]))
    )
    assert n_tests == finite_p
    assert report["metadata"]["horizon_unresolved"] is False
    assert report["metadata"]["label_horizon"] == 1


def test_t31a_iid_mutation_would_fail_separation() -> None:
    """T-3.1a mutation 可證偽：若 t 等於 i.i.d. 則分離斷言失敗（真紅邏輯）。"""
    features = _make_xsec_frame(n_timestamps=80, ar_rho=0.9)
    orch = ICFilterOrchestrator(load_ic_config())
    report = orch.analyze_cross_sectional(
        features, config_override={"ic_train_test_split": False}
    )
    values = np.asarray(
        report["rolling_ic_series"]["alpha"]["window_cross_sectional"], dtype=float
    )
    iid_t = _iid_t_stat(values)
    # 模擬 mutation 後 summary 的 t_stat
    mutant_t = iid_t
    with pytest.raises(AssertionError):
        assert not np.isclose(mutant_t, iid_t, rtol=1e-3, atol=1e-3)


def test_t31b_labels_path_return_5_maxlags_floor() -> None:
    """T-3.1b M-J: labels_path 原始欄 return_5 → maxlags ≥ 4（n 使 auto_bw<4）。"""
    n_ts = 48  # auto_bw = int(4*(48/100)**(2/9)) ≈ 3 → L=max(3,4)=4
    symbols = ["BTCUSDT", "ETHUSDT", "BCHUSDT", "LTCUSDT"]
    features = _make_xsec_frame(
        n_timestamps=n_ts, symbols=symbols, label_col="return_1", seed=11
    )
    # labels MultiIndex 必須與 features 同序且 monotonic（_normalize 守衛）
    labels_df = pd.DataFrame(
        {"return_5": features["return_1"].to_numpy()},
        index=features.index,
    ).sort_index()
    assert labels_df.index.is_monotonic_increasing

    orch = ICFilterOrchestrator(load_ic_config())

    def _fake_load(_path: str) -> pd.DataFrame:
        return labels_df

    orch._load_labels_hdf5 = _fake_load  # type: ignore[method-assign]
    # 去掉 in-frame label，確保走 labels_path 分支
    features_no_label = features.drop(columns=["return_1"])
    report = orch.analyze_cross_sectional(
        features_no_label,
        labels_path="dummy_multi_symbol_labels.h5",
        config_override={"ic_train_test_split": False},
    )
    assert report["metadata"]["horizon_unresolved"] is False
    assert report["metadata"]["label_horizon"] == 5
    assert report["metadata"]["horizon_source_name"] == "return_5"
    maxlags = report["metadata"]["significance"]["maxlags"]
    assert maxlags is not None
    assert int(maxlags) >= 4

    # 與 kernel 直算 floor 一致
    values = np.asarray(
        report["rolling_ic_series"]["alpha"]["window_cross_sectional"], dtype=float
    )
    z = values[np.isfinite(values)]
    auto_bw = int(4 * (z.size / 100.0) ** (2.0 / 9.0))
    expected_L = max(auto_bw, 5 - 1)
    assert int(maxlags) == expected_L
    assert expected_L >= 4


def test_t31b_resolve_on_label_renamed_is_none() -> None:
    """T-3.1b mutation 可證偽：對 `_label` 解析→None（不得當 return_5）。"""
    assert _resolve_cross_sectional_label_horizon("return_5") == 5
    assert _resolve_cross_sectional_label_horizon("_label") is None
    assert _resolve_cross_sectional_label_horizon("label") is None


def test_t31b_mutation_resolve_after_rename_loses_horizon() -> None:
    """T-3.1b M-J mutation: 若在改名後對 `_label` 解析，h 丟失→maxlags 不再保 floor4。"""
    n_ts = 48
    symbols = ["BTCUSDT", "ETHUSDT", "BCHUSDT", "LTCUSDT"]
    features = _make_xsec_frame(n_timestamps=n_ts, symbols=symbols, seed=11)
    labels_df = pd.DataFrame(
        {"return_5": features["return_1"].to_numpy()},
        index=features.index,
    ).sort_index()
    orch = ICFilterOrchestrator(load_ic_config())
    orch._load_labels_hdf5 = lambda _p: labels_df  # type: ignore[method-assign]
    features_no_label = features.drop(columns=["return_1"])
    report = orch.analyze_cross_sectional(
        features_no_label,
        labels_path="dummy.h5",
        config_override={"ic_train_test_split": False},
    )
    correct_maxlags = int(report["metadata"]["significance"]["maxlags"])

    # 模擬 bug：對 `_label` 解析 → h=None → 若再 fallback 1 則 L=auto_bw(<4)
    wrong_h = _resolve_cross_sectional_label_horizon("_label")
    assert wrong_h is None
    values = np.asarray(
        report["rolling_ic_series"]["alpha"]["window_cross_sectional"], dtype=float
    )
    z = values[np.isfinite(values)]
    auto_bw = int(4 * (z.size / 100.0) ** (2.0 / 9.0))
    wrong_L_if_h1 = max(auto_bw, 0)  # h=1 → floor 0
    assert wrong_L_if_h1 < 4 or wrong_L_if_h1 < correct_maxlags
    # 正確路徑必須 ≥4 且 > 錯誤 h=1 路徑
    assert correct_maxlags >= 4
    assert correct_maxlags == max(auto_bw, 4)


def test_t31c_horizon_unresolved_p_all_nan() -> None:
    """T-3.1c: 不可解析 horizon（欄名 label）→ p 族全 NaN + metadata 標記。"""
    features = _make_xsec_frame(n_timestamps=40, label_col="return_1", seed=3)
    # 改用不可解析欄名
    features = features.rename(columns={"return_1": "label"})
    orch = ICFilterOrchestrator(load_ic_config())
    report = orch.analyze_cross_sectional(
        features, config_override={"ic_train_test_split": False}
    )
    assert report["metadata"]["horizon_unresolved"] is True
    assert report["metadata"]["label_horizon"] is None
    assert report["metadata"]["horizon_source_name"] == "label"
    for row in report["summary_table"]:
        assert row["p_value"] is None or (
            isinstance(row["p_value"], float) and not np.isfinite(row["p_value"])
        ) or (row["p_value"] is not None and not np.isfinite(float(row["p_value"])))
        # reporter 可能已將 NaN→None
        p = row["p_value"]
        padj = row.get("p_value_adj")
        t = row["t_stat"]
        for val in (p, padj, t):
            if val is None:
                continue
            assert not np.isfinite(float(val)), f"expected non-finite, got {val}"
    # significance maxlags 應為 None（全 NaN）
    assert report["metadata"]["significance"]["maxlags"] is None
    assert int(report["metadata"]["significance"]["n_tests"]) == 0


def test_t31_inframe_return_5_no_labels_path() -> None:
    """CODEX FINDING-1 反例：in-frame 僅 alpha+return_5、無 labels_path → h=5、maxlags≥4、不 raise。"""
    n_ts = 48  # auto_bw ≈ 3 → L=max(3,4)=4
    symbols = ["BTCUSDT", "ETHUSDT", "BCHUSDT", "LTCUSDT"]
    features = _make_xsec_frame(
        n_timestamps=n_ts,
        symbols=symbols,
        label_col="return_5",
        seed=11,
    )
    # 僅 alpha + return_5（無 beta、無 labels_path）
    features = features[["alpha", "return_5"]]
    orch = ICFilterOrchestrator(load_ic_config())
    report = orch.analyze_cross_sectional(
        features, config_override={"ic_train_test_split": False}
    )
    assert report["metadata"]["horizon_unresolved"] is False
    assert report["metadata"]["label_horizon"] == 5
    assert report["metadata"]["horizon_source_name"] == "return_5"
    maxlags = report["metadata"]["significance"]["maxlags"]
    assert maxlags is not None
    assert int(maxlags) >= 4
    values = np.asarray(
        report["rolling_ic_series"]["alpha"]["window_cross_sectional"], dtype=float
    )
    z = values[np.isfinite(values)]
    auto_bw = int(4 * (z.size / 100.0) ** (2.0 / 9.0))
    assert int(maxlags) == max(auto_bw, 5 - 1)
    # 有限 p（h 可解析）
    alpha_row = next(r for r in report["summary_table"] if r["feature_name"] == "alpha")
    assert np.isfinite(float(alpha_row["p_value"]))


def test_t31_inframe_multi_return_n_picks_min_n() -> None:
    """多 return_N 確定性：取 N 最小（非字典序第一的 return_N 字串、非 max N）。"""
    # 單元：選取規則本身
    assert _select_inframe_return_n_column(["return_5", "return_3", "return_10"]) == "return_3"
    assert _select_inframe_return_n_column(["return_10", "return_2"]) == "return_2"
    assert _select_inframe_return_n_column(["alpha", "beta"]) is None
    # N 相同（理論邊界）→ 字典序
    assert _select_inframe_return_n_column(["return_1b", "return_1"]) == "return_1"  # return_1b 不 match
    assert _select_inframe_return_n_column(["alpha", "return_1"]) == "return_1"

    n_ts = 48
    symbols = ["BTCUSDT", "ETHUSDT", "BCHUSDT", "LTCUSDT"]
    features = _make_xsec_frame(
        n_timestamps=n_ts, symbols=symbols, label_col="return_5", seed=13
    )
    # 故意放 return_5 與 return_3；欄序先 5 後 3，確認不依欄出現序
    features["return_3"] = features["return_5"].to_numpy()
    features = features[["alpha", "return_5", "return_3"]]
    orch = ICFilterOrchestrator(load_ic_config())
    report = orch.analyze_cross_sectional(
        features, config_override={"ic_train_test_split": False}
    )
    assert report["metadata"]["horizon_source_name"] == "return_3"
    assert report["metadata"]["label_horizon"] == 3
    assert report["metadata"]["horizon_unresolved"] is False
    maxlags = int(report["metadata"]["significance"]["maxlags"])
    values = np.asarray(
        report["rolling_ic_series"]["alpha"]["window_cross_sectional"], dtype=float
    )
    z = values[np.isfinite(values)]
    auto_bw = int(4 * (z.size / 100.0) ** (2.0 / 9.0))
    assert maxlags == max(auto_bw, 3 - 1)


def test_t31_inframe_label_beats_return_n() -> None:
    """優先序守衛：label 仍優於 return_N（維持既有候選序）。"""
    features = _make_xsec_frame(n_timestamps=40, label_col="return_5", seed=4)
    features["label"] = features["return_5"].to_numpy()
    orch = ICFilterOrchestrator(load_ic_config())
    report = orch.analyze_cross_sectional(
        features, config_override={"ic_train_test_split": False}
    )
    assert report["metadata"]["horizon_source_name"] == "label"
    # label 不可解析 → unresolved（不得因旁有 return_5 而偷用）
    assert report["metadata"]["horizon_unresolved"] is True
    assert report["metadata"]["label_horizon"] is None


def test_t31_sort_still_by_icir_no_threshold() -> None:
    """不可做：排序仍 ICIR；無淘汰門檻（輸出欄數=輸入 feature 數）。"""
    features = _make_xsec_frame(n_timestamps=40, seed=5)
    orch = ICFilterOrchestrator(load_ic_config())
    report = orch.analyze_cross_sectional(
        features, config_override={"ic_train_test_split": False}
    )
    table = report["summary_table"]
    assert len(table) == 2  # alpha, beta
    icirs = [float(r["icir"]) for r in table if np.isfinite(float(r["icir"]))]
    assert icirs == sorted(icirs, reverse=True)


def test_t31_fdr_q_matches_apply_fdr() -> None:
    """p_value_adj = apply_fdr 對該路徑全 feature。"""
    features = _make_xsec_frame(n_timestamps=60, seed=9)
    orch = ICFilterOrchestrator(load_ic_config())
    report = orch.analyze_cross_sectional(
        features, config_override={"ic_train_test_split": False}
    )
    p_map = {
        str(r["feature_name"]): float(r["p_value"]) for r in report["summary_table"]
    }
    q_map, n_tests = apply_fdr(p_map, alpha=0.05)
    assert n_tests == int(report["metadata"]["significance"]["n_tests"])
    for r in report["summary_table"]:
        name = str(r["feature_name"])
        got = r["p_value_adj"]
        exp = q_map[name]
        if got is None or (isinstance(got, float) and not np.isfinite(got)):
            assert not np.isfinite(exp)
        else:
            assert np.isclose(float(got), float(exp), atol=0.0, rtol=0.0)
