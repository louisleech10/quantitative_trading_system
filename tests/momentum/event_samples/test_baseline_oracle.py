"""Task B1.4 驗證：label 置亂（固定 seed）⇒ 全特徵落帶內；資訊特徵出帶；決定性；
one-class unavailable；全 NaN loud；M8 恆等排列硬檢；pit_shift 訊號消失（可證偽佐證）。

合成的是特徵/label 序列（章程 §F 合法），非價格。conditional_ic 核心重用測試（W3）在檔尾。
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest
from scipy.stats import spearmanr

from momentum.Analysis.event_samples import baseline as bl
from momentum.Analysis.event_samples.baseline import permutation_oracle, single_feature_binary_baseline
from momentum.Analysis.event_samples.types import EventSplitPlan, OracleConfig

N = 240
OC = OracleConfig(seed=20260820, n_perm=300)  # 測試用 n_perm 降速（SPEC 定式 1000＝正式跑；帶語意不變）


def synth(seed=7):
    rng = np.random.default_rng(seed)
    ids = [f"e{i}" for i in range(N)]
    y = pd.Series(rng.integers(0, 2, N), index=ids)
    X = pd.DataFrame({
        "informative": y.to_numpy() * 2.0 + rng.normal(0, 0.5, N),
        "noise": rng.normal(0, 1, N),
    }, index=ids)
    plan = EventSplitPlan(
        assignments=pd.DataFrame({
            "event_id": ids,
            "symbol": "ETHUSDT",
            "split_label": ["train"] * (N // 2) + ["test"] * (N - N // 2),
        }),
        purged=pd.DataFrame(columns=["event_id", "reason"]),
        clusters=pd.DataFrame(),
        summary={},
    )
    return X, y, plan


def test_shuffled_labels_all_in_band():
    """§G-3(i)：置亂後（固定 seed）全特徵落 permutation quantile 帶內。"""
    X, y, plan = synth()
    rng = np.random.default_rng(20260820)
    y_shuffled = pd.Series(rng.permutation(y.to_numpy()), index=y.index)
    rep = single_feature_binary_baseline(X, y_shuffled, plan, oracle_config=OC)
    assert rep["capability_status"] == "ok"
    assert all(f["auc_in_band"] for f in rep["features"].values())


def test_informative_out_of_band_noise_in_band():
    X, y, plan = synth()
    rep = single_feature_binary_baseline(X, y, plan, oracle_config=OC)
    assert rep["features"]["informative"]["auc_in_band"] is False
    assert rep["features"]["informative"]["auc"] > 0.9
    assert rep["features"]["noise"]["auc_in_band"] is True
    assert rep["features"]["informative"]["q_value"] <= rep["features"]["noise"]["q_value"]


def test_deterministic_same_seed():
    X, y, plan = synth()
    r1 = single_feature_binary_baseline(X, y, plan, oracle_config=OC)
    r2 = single_feature_binary_baseline(X, y, plan, oracle_config=OC)
    assert json.dumps(r1, sort_keys=True) == json.dumps(r2, sort_keys=True)


def test_one_class_unavailable():
    X, y, plan = synth()
    rep = single_feature_binary_baseline(X, pd.Series(1, index=y.index), plan, oracle_config=OC)
    assert rep["capability_status"] == "unavailable"
    assert rep["reason"] == "one_class_test_segment"


def test_all_nan_feature_loud():
    X, y, plan = synth()
    X["dead"] = np.nan
    with pytest.raises(ValueError, match="全 NaN"):
        single_feature_binary_baseline(X, y, plan, oracle_config=OC)


def test_m8_identity_permutation_hard_check(monkeypatch):
    """M8：置亂改恆等排列 ⇒ 非退化/非恆等硬檢必觸發（假綠路徑封死）。"""
    X, y, plan = synth()
    monkeypatch.setattr(bl, "_permute", lambda rng, arr: arr.copy())
    with pytest.raises(ValueError, match="硬檢"):
        single_feature_binary_baseline(X, y, plan, oracle_config=OC)


def test_pit_shift_kills_signal():
    """ASSERT …WHEN mutation=pit_shift THEN rc!=0 之佐證：特徵錯位一列 ⇒ 資訊特徵訊號消失
    （正常版 out-of-band、mutation 版 in-band——兩態成對釘住，oracle 真的在量對齊）。"""
    X, y, plan = synth()
    shifted = X.copy()
    shifted["informative"] = np.roll(shifted["informative"].to_numpy(), 1)  # 決策列錯位＝PIT 破壞
    rep_ok = single_feature_binary_baseline(X, y, plan, oracle_config=OC)
    rep_mut = single_feature_binary_baseline(shifted, y, plan, oracle_config=OC)
    assert rep_ok["features"]["informative"]["auc_in_band"] is False
    assert rep_mut["features"]["informative"]["auc_in_band"] is True


def test_conditional_ic_core_reuse():
    """W3：同一 permutation 核心以 statistic_kind=conditional_ic（Spearman IC，null 中心 0）重用。"""
    rng = np.random.default_rng(11)
    v = rng.normal(0, 1, 300)
    label_value = 0.8 * v + rng.normal(0, 1, 300)   # 連續 label（非價格）

    def ic(values, yy):
        return float(spearmanr(values, yy).statistic)

    out = permutation_oracle(v, label_value, ic, OC)
    assert out["in_band"] is False and out["observed"] > 0.5
    assert out["band_low"] < 0 < out["band_high"]    # null 中心 0 由置亂分布自然給出
    shuffled = np.random.default_rng(OC.seed).permutation(label_value)
    out2 = permutation_oracle(v, shuffled, ic, OC)
    assert out2["in_band"] is True
