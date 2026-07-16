"""LA-0 B4 orchestrator 接線：fit_mode 注入 invariant / refilter revalidate / deep key。"""

from __future__ import annotations

import hashlib
import json

import numpy as np
import pandas as pd
import pytest

from momentum.Analysis.ic_config_schema import ICConfig, PreprocessingConfig
from momentum.Analysis.ic_filter_orchestrator import ICFilterOrchestrator
from momentum.Analysis.pit_stats import PIT_STATS_VERSION


def test_preprocessing_config_default_fit_mode_unset() -> None:
    """schema default=unset（禁 global default pit_expanding）。"""
    cfg = PreprocessingConfig()
    assert cfg.fit_mode == "unset"
    full = ICConfig()
    assert full.preprocessing.fit_mode == "unset"


def test_stage1_rejects_unset_fit_mode() -> None:
    """invariant：進 _stage1_preprocessing 的路徑 fit_mode != unset。"""
    orch = ICFilterOrchestrator(ICConfig())
    df = pd.DataFrame({"a": [1.0, 2.0, 3.0]})
    with pytest.raises(ValueError, match="fit_mode"):
        orch._stage1_preprocessing(df, metadata={}, fit_mask=None, fit_mode="unset")
    with pytest.raises(ValueError, match="fit_mode"):
        orch._stage1_preprocessing(df, metadata={}, fit_mask=None, fit_mode=None)


def test_resolve_stage1_fit_mapping() -> None:
    """split ON→train_mask；OFF→pit_expanding；config full_sample→full_sample。"""
    orch = ICFilterOrchestrator(ICConfig())
    train = np.array([True, True, False])
    mode, mask = orch._resolve_stage1_fit(
        ICConfig(), split_context={"train_mask": train}
    )
    assert mode == "train_mask"
    assert mask is train

    mode2, mask2 = orch._resolve_stage1_fit(ICConfig(), split_context=None)
    assert mode2 == "pit_expanding"
    assert mask2 is None

    cfg_fs = ICConfig.model_validate(
        {"preprocessing": {"fit_mode": "full_sample"}}
    )
    mode3, mask3 = orch._resolve_stage1_fit(cfg_fs, split_context=None)
    assert mode3 == "full_sample"
    assert mask3 is None
    # full_sample 優先於 split context（fallback 鎖）
    mode4, mask4 = orch._resolve_stage1_fit(
        cfg_fs, split_context={"train_mask": train}
    )
    assert mode4 == "full_sample"
    assert mask4 is None


def test_refilter_invalidates_on_version_or_mode_mismatch() -> None:
    """refilter 前 metadata version/mode 不符 → invalidate 重算（raise）。"""
    orch = ICFilterOrchestrator(ICConfig())
    orch._active_fit_mode = "train_mask"
    orch._ic_cache = {
        "features_df": pd.DataFrame({"a": [1.0]}),
        "label_series": pd.Series([0.1]),
        "metadata": {
            "pit_stats_version": "stale_version",
            "fit_mode": "train_mask",
        },
        "preproc_log": {"fit_mode": "train_mask", "pit_stats_version": "stale_version"},
        "icir": {},
        "event_info": {},
        "feature_filter_info": {},
        "stage0_log": {},
        "split_context": None,
    }
    orch._monotonicity_cache = {}

    with pytest.raises(ValueError, match="invalidated"):
        orch.refilter({})

    assert orch._ic_cache is None
    assert orch._monotonicity_cache is None

    # mode 不符
    orch2 = ICFilterOrchestrator(ICConfig())
    orch2._active_fit_mode = "pit_expanding"
    orch2._ic_cache = {
        "features_df": pd.DataFrame({"a": [1.0]}),
        "label_series": pd.Series([0.1]),
        "metadata": {
            "pit_stats_version": PIT_STATS_VERSION,
            "fit_mode": "train_mask",
        },
        "preproc_log": {},
        "icir": {},
        "event_info": {},
        "feature_filter_info": {},
        "stage0_log": {},
        "split_context": None,
    }
    orch2._monotonicity_cache = {}
    with pytest.raises(ValueError, match="invalidated"):
        orch2.refilter({})
    assert orch2._ic_cache is None


def test_deep_cache_key_includes_pit_version_and_fit_mode() -> None:
    """_compute_deep_cache_key 必含 pit_stats_version + fit_mode。"""
    orch = ICFilterOrchestrator(ICConfig())
    orch._active_fit_mode = "train_mask"
    cfg = ICConfig()
    key_a = orch._compute_deep_cache_key(["f1", "f2"], cfg)
    orch._active_fit_mode = "pit_expanding"
    key_b = orch._compute_deep_cache_key(["f1", "f2"], cfg)
    assert key_a != key_b

    # 直接驗證 payload 語意：相同 features+config+mode → 相同 key
    orch._active_fit_mode = "train_mask"
    key_a2 = orch._compute_deep_cache_key(["f1", "f2"], cfg)
    assert key_a == key_a2

    # 手工重算確認 version/mode 進入 hash
    deep_cfg = {
        "factor_return": cfg.factor_return.model_dump(),
        "factor_centrality": cfg.factor_centrality.model_dump(),
        "trend_analysis": cfg.trend_analysis.model_dump(),
        "parameter_sensitivity": cfg.parameter_sensitivity.model_dump(),
        "rolling_oos": cfg.rolling_oos.model_dump(),
        "factor_orthogonalization": cfg.factor_orthogonalization.model_dump(),
        "factor_exposure": cfg.factor_exposure.model_dump(),
        "long_short_analysis": cfg.long_short_analysis.model_dump(),
        "feature_quality_diagnostics": cfg.feature_quality_diagnostics.model_dump(),
        "net_ic_analysis": cfg.net_ic_analysis.model_dump(),
        "deep_analysis_global": cfg.deep_analysis_global.model_dump(),
    }
    payload = {
        "features": ["f1", "f2"],
        "deep_config": deep_cfg,
        "pit_stats_version": PIT_STATS_VERSION,
        "fit_mode": "train_mask",
    }
    expected = hashlib.md5(
        json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    assert key_a == expected
