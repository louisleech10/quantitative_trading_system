from __future__ import annotations

import importlib
from typing import Dict, List

import pandas as pd


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
            frames.append(result)

        if not frames:
            return pd.DataFrame(index=data.index)

        return pd.concat(frames, axis=1)
