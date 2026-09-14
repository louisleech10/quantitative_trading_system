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
H = "ab" * 32  # feature_manifest_hash（B1.6 產出；CODEX-R2-P2-02：缺則 fail-closed）


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
    rep = single_feature_binary_baseline(X, y_shuffled, plan, oracle_config=OC, feature_manifest_hash=H)
    assert rep["capability_status"] == "ok"
    assert all(f["auc_in_band"] for f in rep["features"].values())


def test_informative_out_of_band_noise_in_band():
    X, y, plan = synth()
    rep = single_feature_binary_baseline(X, y, plan, oracle_config=OC, feature_manifest_hash=H)
    assert rep["features"]["informative"]["auc_in_band"] is False
    assert rep["features"]["informative"]["auc"] > 0.9
    assert rep["features"]["noise"]["auc_in_band"] is True
    assert rep["features"]["informative"]["q_value"] <= rep["features"]["noise"]["q_value"]


def test_deterministic_same_seed():
    X, y, plan = synth()
    r1 = single_feature_binary_baseline(X, y, plan, oracle_config=OC, feature_manifest_hash=H)
    r2 = single_feature_binary_baseline(X, y, plan, oracle_config=OC, feature_manifest_hash=H)
    assert json.dumps(r1, sort_keys=True) == json.dumps(r2, sort_keys=True)


_BASELINE_KEYS_OK = {"statistic_kind", "n_test_events", "n_test_samples", "prevalence", "receipts",
                     "capability_status", "features"}


def test_baseline_splits_n_test_into_events_and_samples():
    """D-002 `Task 9.4`（`M-SU-D2-31`）：test 指派之事件數與實際樣本數**不恆等**——兩量分離。

    §V 母斷言逐字：test 含 `e1` 且物化 failures 含 `e1`（不在 features）⇒ `n_test_events=1` 且 `n_test_samples=0`。
    另以非退化批驗 ok 路徑：test 段 120 事件、其中 10 個物化失敗 ⇒ 120 與 110。
    """
    plan = EventSplitPlan(
        assignments=pd.DataFrame({"event_id": ["e0", "e1"], "symbol": "ETHUSDT", "split_label": ["train", "test"]}),
        purged=pd.DataFrame(columns=["event_id", "reason"]),
        clusters=pd.DataFrame(),
        summary={},
    )
    X = pd.DataFrame({"f": [0.5]}, index=["e0"])  # e1 物化失敗 ⇒ 不在 features
    y = pd.Series([1], index=["e0"])
    rep = single_feature_binary_baseline(X, y, plan, oracle_config=OC, feature_manifest_hash=H)
    assert rep["n_test_events"] == 1
    assert rep["n_test_samples"] == 0

    X2, y2, plan2 = synth()
    test_ids = plan2.assignments.loc[plan2.assignments["split_label"] == "test", "event_id"].tolist()
    dropped = set(test_ids[:10])
    keep = [i for i in X2.index if i not in dropped]
    rep2 = single_feature_binary_baseline(X2.loc[keep], y2.loc[keep], plan2, oracle_config=OC, feature_manifest_hash=H)
    assert rep2["capability_status"] == "ok", "fixture 前提變了：須走 ok 路徑"
    assert rep2["n_test_events"] == len(test_ids) == 120
    assert rep2["n_test_samples"] == 110, "不得宣稱事件數＝樣本數"


def test_baseline_dict_has_no_legacy_n_test_key():
    """D-002 `Task 9.4`（`M-SU-D2-32`）：回傳 dict 鍵集為 **exact** 契約——舊鍵 `n_test` 不得殘留、不得為 alias。"""
    X, y, plan = synth()
    rep = single_feature_binary_baseline(X, y, plan, oracle_config=OC, feature_manifest_hash=H)
    assert set(rep) == _BASELINE_KEYS_OK
    assert "n_test" not in rep
    one = single_feature_binary_baseline(X, pd.Series(1, index=y.index), plan, oracle_config=OC, feature_manifest_hash=H)
    assert set(one) == _BASELINE_KEYS_OK | {"reason"}, "unavailable 分支亦為 exact 鍵集"
    assert "n_test" not in one


def test_one_class_unavailable():
    X, y, plan = synth()
    rep = single_feature_binary_baseline(X, pd.Series(1, index=y.index), plan, oracle_config=OC, feature_manifest_hash=H)
    assert rep["capability_status"] == "unavailable"
    assert rep["reason"] == "one_class_test_segment"


def test_all_nan_feature_loud():
    X, y, plan = synth()
    X["dead"] = np.nan
    with pytest.raises(ValueError, match="非有限值"):
        single_feature_binary_baseline(X, y, plan, oracle_config=OC, feature_manifest_hash=H)


def test_partial_nonfinite_loud_no_silent_drop():
    """CODEX-R1-P1-06：單一 cell NaN/inf 亦 fail-closed，不做 pairwise 靜默刪列。"""
    X, y, plan = synth()
    X.iloc[200, X.columns.get_loc("noise")] = np.nan
    with pytest.raises(ValueError, match="非有限值"):
        single_feature_binary_baseline(X, y, plan, oracle_config=OC, feature_manifest_hash=H)
    X2, _, _ = synth()
    X2.iloc[200, X2.columns.get_loc("noise")] = np.inf
    with pytest.raises(ValueError, match="非有限值"):
        single_feature_binary_baseline(X2, y, plan, oracle_config=OC, feature_manifest_hash=H)


def test_feature_manifest_hash_in_receipts_and_required():
    """CODEX-R1-P2-07／R2-P2-02：hash 進 receipts 且不可省略（缺／格式錯 ⇒ fail-closed）。"""
    X, y, plan = synth()
    rep = single_feature_binary_baseline(X, y, plan, oracle_config=OC, feature_manifest_hash=H)
    assert rep["receipts"]["feature_manifest_hash"] == H
    assert rep["features"]["noise"]["n_used"] == N - N // 2
    for bad in (None, "", "short", "g" * 64, "AB" * 32):  # 非 hex／大寫皆拒（CODEX-R3-P2-01）
        with pytest.raises(ValueError, match="feature_manifest_hash"):
            single_feature_binary_baseline(X, y, plan, oracle_config=OC, feature_manifest_hash=bad)


def test_one_class_with_nonfinite_is_loud_not_unavailable():
    """CODEX-R2-P2-01：有限值閘在 one-class 分支之前——NaN 不得被誤報成 one_class_test_segment。"""
    X, y, plan = synth()
    X.iloc[200, 0] = np.nan
    with pytest.raises(ValueError, match="非有限值"):
        single_feature_binary_baseline(X, pd.Series(1, index=y.index), plan, oracle_config=OC, feature_manifest_hash=H)


def test_m8_identity_permutation_hard_check(monkeypatch):
    """M8：置亂改恆等排列 ⇒ 非退化/非恆等硬檢必觸發（假綠路徑封死）。"""
    X, y, plan = synth()
    monkeypatch.setattr(bl, "_permute", lambda rng, arr: arr.copy())
    with pytest.raises(ValueError, match="硬檢"):
        single_feature_binary_baseline(X, y, plan, oracle_config=OC, feature_manifest_hash=H)


def test_pit_shift_kills_signal():
    """ASSERT …WHEN mutation=pit_shift THEN rc!=0 之佐證：特徵錯位一列 ⇒ 資訊特徵訊號消失
    （正常版 out-of-band、mutation 版 in-band——兩態成對釘住，oracle 真的在量對齊）。"""
    X, y, plan = synth()
    shifted = X.copy()
    shifted["informative"] = np.roll(shifted["informative"].to_numpy(), 1)  # 決策列錯位＝PIT 破壞
    rep_ok = single_feature_binary_baseline(X, y, plan, oracle_config=OC, feature_manifest_hash=H)
    rep_mut = single_feature_binary_baseline(shifted, y, plan, oracle_config=OC, feature_manifest_hash=H)
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
