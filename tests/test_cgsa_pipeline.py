"""Phase 2 整合測試（Task 2.12 / Gate 2->3）。"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

import pandas as pd

from momentum.FeatureEngineering.feature_factory import FeatureFactory
from momentum.FeatureEngineering.timeframe.multi_tf_generator import MultiTFGenerator
from scripts.validate_cgsa_ab import run_validation


def _write_layer_artifacts(base_dir: Path, layers: dict[str, pd.DataFrame]) -> dict[str, Path]:
    base_dir.mkdir(parents=True, exist_ok=True)
    mapping: dict[str, Path] = {}
    for layer, frame in layers.items():
        output_path = base_dir / f"{layer}.parquet"
        frame.to_parquet(output_path, index=False)
        mapping[layer] = output_path
    return mapping


def test_cgsa_vs_legacy_numeric_equivalence(tmp_path: Path):
    """T2.11: 逐層 CGSA vs legacy 數值應等價（含 NaN mask 與欄位順序）。"""
    legacy_l1 = pd.DataFrame(
        {
            "close_1h_trend_ADX_14": [20.0, 21.0, 22.0, float("nan")],
            "close_1h_trend_EMA_5": [1.0, 2.0, 3.0, 4.0],
        }
    )
    cgsa_l1 = legacy_l1.copy(deep=True)

    legacy_l2 = pd.DataFrame(
        {
            "close_1h_momentum_RSI_5_ratio": [0.1, 0.2, 0.3, 0.4],
            "close_1h_momentum_RSI_5_cross": [1.0, 0.0, 1.0, 0.0],
        }
    )
    cgsa_l2 = legacy_l2.copy(deep=True)
    cgsa_l2.loc[1, "close_1h_momentum_RSI_5_ratio"] += 5e-7

    legacy_l3 = pd.DataFrame(
        {
            "close_1h_trend_EMA_5_mean": [1.0, 1.2, 1.4, 1.6],
            "close_1h_trend_EMA_5_skew": [0.10, 0.12, 0.14, 0.16],
            "close_1h_trend_EMA_5_slope": [0.01, 0.01, 0.02, 0.02],
        }
    )
    cgsa_l3 = legacy_l3.copy(deep=True)
    cgsa_l3.loc[2, "close_1h_trend_EMA_5_mean"] += 6e-7
    cgsa_l3.loc[0, "close_1h_trend_EMA_5_skew"] += 8e-5
    cgsa_l3.loc[3, "close_1h_trend_EMA_5_slope"] += 7e-6

    legacy_layers = _write_layer_artifacts(
        tmp_path / "legacy",
        {"L1": legacy_l1, "L2": legacy_l2, "L3": legacy_l3},
    )
    cgsa_layers = _write_layer_artifacts(
        tmp_path / "cgsa",
        {"L1": cgsa_l1, "L2": cgsa_l2, "L3": cgsa_l3},
    )

    baseline_columns = (
        list(cgsa_l1.columns)
        + list(cgsa_l2.columns)
        + list(cgsa_l3.columns)
    )
    baseline_nan_ratio = (
        float(cgsa_l1.isna().mean().sum())
        + float(cgsa_l2.isna().mean().sum())
        + float(cgsa_l3.isna().mean().sum())
    ) / float(len(baseline_columns))
    structural_baseline = {
        "source": "tier1_structural",
        "columns": baseline_columns,
        "feature_count": len(baseline_columns),
        "nan_ratio_mean": baseline_nan_ratio,
    }

    report = run_validation(
        cgsa_layers=cgsa_layers,
        legacy_layers=legacy_layers,
        structural_baseline=structural_baseline,
        strict_missing_layers=True,
    )

    assert report["overall_status"] == "passed"
    assert report["layers"]["L1"]["status"] == "passed"
    assert report["layers"]["L2"]["status"] == "passed"
    assert report["layers"]["L3"]["status"] == "passed"
    assert report["structure"]["status"] == "passed"

    # TESTREG 4.4：原只有「容差內擾動判 passed」之正例，無「超容差判 failed」之反例（驗證器全回 passed 亦綠）；
    # legacy 生成路徑已於 5584102d 刪除，本測試之實際對象為 scripts/validate_cgsa_ab 之 A/B 比對契約 ⇒ 補反例：
    # 各層各取一欄超出其容差（L1 atol 1e-7、L2 1e-6、L3 skew 1e-4）、NaN 位置不同、少一層（strict）皆須判 failed
    def _report_with(cgsa_overrides: dict[str, pd.DataFrame], *, drop_layer: str | None = None) -> dict:
        frames = {"L1": cgsa_l1, "L2": cgsa_l2, "L3": cgsa_l3, **cgsa_overrides}
        if drop_layer is not None:
            frames.pop(drop_layer)
        paths = _write_layer_artifacts(tmp_path / f"neg_{len(list(tmp_path.iterdir()))}", frames)
        return run_validation(
            cgsa_layers=paths,
            legacy_layers=legacy_layers,
            structural_baseline=structural_baseline,
            strict_missing_layers=True,
        )

    bad_l1 = cgsa_l1.copy(deep=True)
    bad_l1.loc[0, "close_1h_trend_EMA_5"] += 1e-5
    bad_l2 = cgsa_l2.copy(deep=True)
    bad_l2.loc[0, "close_1h_momentum_RSI_5_cross"] += 1e-4
    bad_l3 = cgsa_l3.copy(deep=True)
    bad_l3.loc[1, "close_1h_trend_EMA_5_skew"] += 1e-2
    nan_l1 = cgsa_l1.copy(deep=True)
    nan_l1.loc[0, "close_1h_trend_EMA_5"] = float("nan")
    for layer, frame in (("L1", bad_l1), ("L2", bad_l2), ("L3", bad_l3), ("L1", nan_l1)):
        negative = _report_with({layer: frame})
        assert negative["layers"][layer]["status"] == "failed", (layer, negative["layers"][layer])
        assert negative["overall_status"] == "failed"
    missing = _report_with({}, drop_layer="L3")
    assert missing["layers"]["L3"]["status"] == "failed"
    assert missing["overall_status"] == "failed"


def test_cgsa_no_global_concat(monkeypatch):
    """T2.12（FRAMEPATH Task 1.2 改契約）：CGSA 不做全欄合併——layer7_final 具名拒絕，且不得呼叫 concat_with_memmap。"""
    import pytest

    from momentum.FeatureEngineering.feature_factory import CGSARegistryRequiredError

    def _raise_if_called(*_args, **_kwargs):
        raise AssertionError("concat_with_memmap should not be called in CGSA mode")

    monkeypatch.setattr(
        "momentum.FeatureEngineering.memmap_utils.concat_with_memmap",
        _raise_if_called,
    )

    sample = pd.DataFrame({"f": [1.0, 2.0, 3.0]})

    factory = FeatureFactory(config_manager=Mock(), adapter_registry=Mock())
    with pytest.raises(CGSARegistryRequiredError):
        factory._combine_layers([sample], context="layer7_final")
