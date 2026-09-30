from __future__ import annotations

import importlib
from typing import Dict, List, Optional

import pandas as pd

from momentum.FeatureEngineering.preprocessing.stable_mask import StableMaskError


def _check_declared_outputs(name: str, result: pd.DataFrame, outputs: Optional[Dict]) -> None:
    """FF-STAT SPEC §C v39②：回傳欄集合須＝`outputs` 宣告集合，且每欄宣告其 period_keys 所需之參數；否則 concat 前 fail-closed。"""
    declared = dict(outputs or {})
    returned = [str(c) for c in result.columns]
    undeclared = sorted(set(returned) - set(declared))
    missing = sorted(set(declared) - set(returned))
    if not declared or undeclared or missing:
        raise StableMaskError(
            f"L1 輸出點契約不成立：engine=custom indicator={name}：回傳欄未宣告 {undeclared}、宣告欄未回傳 {missing}"
        )
    for column, decl in declared.items():
        lacking = [k for k in (decl.get("period_keys") or []) if k not in (decl.get("params") or {})]
        if lacking:
            raise StableMaskError(
                f"L1 輸出點契約不成立：engine=custom column={column} indicator={name}：參數字典缺 period_keys {lacking}"
            )


def _mask_declared(name: str, result: pd.DataFrame, outputs: Dict, data: pd.DataFrame) -> pd.DataFrame:
    """FF-STAT Task 2.3：自訂指標之 L1 輸出點——以宣告之參數與 period_keys 逐欄遮罩；倍數表條目名＝指標名
    （表內須登記，否則 fail-closed，R5）；origin 取資料之 OHLCV 輸入欄皆有限之首列。"""
    from momentum.FeatureEngineering.atomic import l1_output_points as l1op
    from momentum.FeatureEngineering.preprocessing import stable_mask as sm
    from momentum.FeatureEngineering.atomic import warmup_lookup

    inputs = [data[c].to_numpy(dtype=float) for c in ("open", "high", "low", "close", "volume") if c in data.columns]
    origin = l1op.origin_of(inputs)
    masked = {}
    for column in result.columns:
        decl = outputs[str(column)]
        spec = sm.OutputPointSpec(engine="custom", indicator=str(name).upper(), column=str(column),
                                  params=dict(decl.get("params") or {}), period_keys=tuple(decl.get("period_keys") or ()))
        k = sm.instance_k(spec, warmup_lookup.warmup_table())
        masked[column] = sm.apply_l1_mask(result[column].to_numpy(dtype=float), origin, k)
    return pd.DataFrame(masked, index=result.index)


class CustomIndicatorEngine:
    """User-defined indicators loaded by module/function."""

    def compute_all(self, data: pd.DataFrame, custom_defs: List[Dict]) -> pd.DataFrame:
        frames = []
        for definition in custom_defs or []:
            module_path = definition.get("module")
            func_name = definition.get("function")
            params = definition.get("params", {})
            name = definition.get("name", "custom")

            if not module_path or not func_name:
                continue

            module = importlib.import_module(module_path)
            func = getattr(module, func_name)
            result = func(data, **params)
            if isinstance(result, pd.Series):
                result = result.to_frame(name=name)
            _check_declared_outputs(name, result, definition.get("outputs"))
            frames.append(_mask_declared(name, result, definition["outputs"], data))

        if not frames:
            return pd.DataFrame(index=data.index)

        return pd.concat(frames, axis=1)
