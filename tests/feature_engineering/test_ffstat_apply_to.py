"""FF-STAT Task 3.2：刪 `layer1_only`，平穩化步驟之 `apply_to` 只收 `non_stationary`／`all`
（docs/FFSTAT_SPEC.md §C「`apply_to` 封閉」）。實作前應為紅。
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import pytest

from momentum.factories import create_feature_factory
from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor
from tests.feature_engineering import ffstat_helpers as h

ALLOWED = h.CONTRACT["stationarity_apply_to_allowed"]
REJECTED = h.CONTRACT["stationarity_apply_to_rejected_examples"]


def _resolve(payload: dict) -> Any:
    return create_feature_factory(cache_dir=h.KLINE_DIR, validate_continuity=False)._resolve_config(payload)


@pytest.mark.parametrize("step", ["adf_differencing", "fractional_differencing"])
@pytest.mark.parametrize("value", REJECTED, ids=["layer1_only", "regex", "column_list"])
def test_stationarity_apply_to_rejects_non_closed_values(step: str, value: Any) -> None:
    """Task 3.2 驗證：兩平穩化步驟之 apply_to 為 layer1_only、regex 字串或欄名清單 ⇒ 設定驗證拋錯，
    訊息指名只收 non_stationary、all。"""
    payload = h.stat_payload()
    payload["preprocessing"][step]["apply_to"] = value
    with pytest.raises(ValueError) as err:
        _resolve(payload)
    assert all(v in str(err.value) for v in ALLOWED)


@pytest.mark.parametrize("step", ["adf_differencing", "fractional_differencing"])
@pytest.mark.parametrize("value", ALLOWED)
def test_stationarity_apply_to_accepts_closed_values(step: str, value: str) -> None:
    """Task 3.2 驗證：non_stationary、all 照常接受。"""
    payload = h.stat_payload()
    payload["preprocessing"][step]["apply_to"] = value
    config = _resolve(payload)
    assert getattr(config.preprocessing, step).apply_to == value


def test_boundary_20_scaling_steps_apply_to_list_unchanged() -> None:
    """Task 3.2 邊界①：winsor 等非平穩化步驟之 apply_to 清單不在本票，照常接受。"""
    payload = h.stat_payload()
    payload["preprocessing"]["winsorization"] = {"enabled": True, "apply_to": ["close_1h_trend_EMA_20"]}
    config = _resolve(payload)
    assert config.preprocessing.winsorization.apply_to == ["close_1h_trend_EMA_20"]


def test_select_columns_has_no_layer1_only_prefix_branch() -> None:
    """Task 3.2：`_select_columns` 不再有 layer1_only 寫死前綴分支（以真實欄名之 frame 驗：不得回傳前綴選欄結果）。"""
    import json

    names = sorted(json.loads(h.BASELINE_PATH.read_text(encoding="utf-8"))["base"])[:30]
    df = pd.DataFrame({n: [1.0, 2.0, 3.0] for n in names})
    pre = FeaturePreprocessor({})
    legacy = [c for c in names if c.startswith(("close_", "open_", "high_", "low_", "volume_"))]
    assert legacy, "真實欄名須含舊前綴（測試前提）"
    assert pre._select_columns(df, "layer1_only") != legacy


def test_mutation_layer1_only_branch_restored_is_caught(monkeypatch: pytest.MonkeyPatch) -> None:
    """§V mutant ⑤：layer1_only 分支恢復 ⇒ 前綴分支測試必紅。"""
    real = FeaturePreprocessor._select_columns

    def _mutant(self, df, apply_to):
        if apply_to == "layer1_only":
            prefixes = ("close_", "open_", "high_", "low_", "volume_", "quote_volume_", "taker_", "ms_", "ent_", "tr_")
            return [c for c in df.columns if str(c).startswith(prefixes)]
        return real(self, df, apply_to)

    monkeypatch.setattr(FeaturePreprocessor, "_select_columns", _mutant)
    with pytest.raises(AssertionError):
        test_select_columns_has_no_layer1_only_prefix_branch()


def test_mutation_regex_accepted_is_caught(monkeypatch: pytest.MonkeyPatch) -> None:
    """§V mutant ⑨：ADF 差分設定接受 regex ⇒ 拒收測試必紅。"""
    factory_cls = type(create_feature_factory(cache_dir=h.KLINE_DIR, validate_continuity=False))
    real = factory_cls._resolve_config

    def _mutant(self, payload):
        stripped = dict(payload)
        pre = dict(stripped.get("preprocessing", {}))
        for step in ("adf_differencing", "fractional_differencing"):
            if isinstance(pre.get(step, {}).get("apply_to"), (list, str)) and pre[step]["apply_to"] not in ALLOWED:
                pre[step] = {**pre[step], "apply_to": "non_stationary"}
        stripped["preprocessing"] = pre
        return real(self, stripped)

    monkeypatch.setattr(factory_cls, "_resolve_config", _mutant)
    with pytest.raises(pytest.fail.Exception):
        test_stationarity_apply_to_rejects_non_closed_values("adf_differencing", "^close_")
