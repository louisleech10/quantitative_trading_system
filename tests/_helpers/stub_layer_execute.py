"""測試用 stub factory 的 _execute_layer1_6 薄包裝（對齊 Batch2 typed layer API）。"""

from __future__ import annotations

from typing import Any, Callable

import pandas as pd

from momentum.core.contracts import LayerExecutionResult, LayerStatus, derive_status
from momentum.FeatureEngineering.feature_factory import FeatureFactory

def stub_layer_data(_factory: object, layer: Any) -> pd.DataFrame:
    """Multi-TF legacy path：instance 呼叫 factory.layer_data(item)。"""
    del _factory
    return FeatureFactory.layer_data(layer)


def stub_execute_layer1_6(func: Callable[..., Any], *args: Any) -> LayerExecutionResult:
    """將回傳 DataFrame 的 stub layer 包成 LayerExecutionResult。"""
    index = pd.Index([])
    for arg in args:
        if isinstance(arg, pd.DataFrame) and len(arg.index) > 0:
            index = arg.index
            break

    try:
        raw = func(*args)
    except Exception as exc:
        return LayerExecutionResult(
            data=pd.DataFrame(index=index),
            status=LayerStatus.layer_failed,
            failed_engines=(),
            reason=str(exc),
            configured_engines=1,
            present_engines=0,
            required_engines=0,
            dependency_error=False,
        )

    if isinstance(raw, LayerExecutionResult):
        return raw

    data = raw if isinstance(raw, pd.DataFrame) else pd.DataFrame(index=index)
    if data is None:
        data = pd.DataFrame(index=index)
    cols = 0 if data.empty else data.shape[1]
    status = derive_status(
        configured_engines=1 if cols > 0 else 0,
        present_engines=1 if cols > 0 else 0,
        required_engines=0,
    )
    return LayerExecutionResult(
        data=data,
        status=status,
        failed_engines=(),
        reason=None,
        configured_engines=1 if cols > 0 else 0,
        present_engines=1 if cols > 0 else 0,
        required_engines=0,
        dependency_error=False,
    )


def stub_spill_to_memmap(df: pd.DataFrame, label: str) -> pd.DataFrame:
    """委派真實 FeatureFactory spill（小表為 no-op）。"""
    from momentum.FeatureEngineering.feature_factory import FeatureFactory

    return FeatureFactory._spill_to_memmap(df, label)
