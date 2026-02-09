from __future__ import annotations

from typing import List, Dict

import numpy as np


class ParameterGenerator:
    """Generate parameter sequences for indicators and lag features."""

    FIBONACCI = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377]
    FIBONACCI_SHORT = [5, 8, 13, 21, 34, 55]
    FIBONACCI_FULL = [5, 8, 13, 21, 34, 55, 89, 144, 233]

    @staticmethod
    def generate(
        strategy: str,
        range_min: int = 5,
        range_max: int = 233,
        industry_standard: List[int] | None = None,
    ) -> List[int]:
        if range_min < 1:
            range_min = 1
        if range_max < range_min:
            range_max = range_min

        if strategy == "fibonacci":
            values = [v for v in ParameterGenerator.FIBONACCI if range_min <= v <= range_max]
        elif strategy == "fibonacci_short":
            values = [v for v in ParameterGenerator.FIBONACCI_SHORT if range_min <= v <= range_max]
        elif strategy == "fibonacci_full":
            values = [v for v in ParameterGenerator.FIBONACCI_FULL if range_min <= v <= range_max]
        elif strategy == "log_scale":
            values = list(np.unique(np.round(np.logspace(np.log10(range_min), np.log10(range_max), num=7)).astype(int)))
        elif strategy == "linear":
            values = list(np.linspace(range_min, range_max, num=6).round().astype(int))
        elif strategy == "adaptive":
            values = [v for v in ParameterGenerator.FIBONACCI_FULL if range_min <= v <= range_max]
        else:
            values = [range_min, range_max]

        merged = set(values)
        if industry_standard:
            merged.update(industry_standard)

        return sorted({v for v in merged if v >= 1})

    @staticmethod
    def generate_lag_sequence(
        sequence_length: int,
        max_lag_ratio: float,
        strategy: str = "adaptive",
        custom_lags: List[int] | None = None,
    ) -> List[int]:
        max_lag = max(1, int(sequence_length * max_lag_ratio))

        if strategy == "custom" and custom_lags:
            values = [lag for lag in custom_lags if 1 <= lag <= max_lag]
        elif strategy == "dense":
            values = list(range(1, max_lag + 1))
        elif strategy == "sparse_log":
            values = [2 ** i for i in range(0, 32) if 1 <= 2 ** i <= max_lag]
        else:
            values = [v for v in ParameterGenerator.FIBONACCI_FULL if v <= max_lag]

        return sorted({int(v) for v in values if v >= 1})

    @staticmethod
    def generate_combos(combo_type: str, custom_combos: List | None = None) -> List[Dict]:
        if custom_combos:
            combos: List[Dict] = []
            for combo in custom_combos:
                if isinstance(combo, dict):
                    combos.append(combo)
                elif isinstance(combo, (list, tuple)):
                    combos.append(ParameterGenerator._combo_list_to_dict(combo_type, combo))
            return combos

        combo_type_lower = combo_type.lower()
        if combo_type_lower == "macd":
            return [{"fastperiod": 12, "slowperiod": 26, "signalperiod": 9}]
        if combo_type_lower == "stoch":
            return [
                {
                    "fastk_period": 5,
                    "slowk_period": 3,
                    "slowk_matype": 0,
                    "slowd_period": 3,
                    "slowd_matype": 0,
                }
            ]
        if combo_type_lower == "stochf":
            return [{"fastk_period": 5, "fastd_period": 3, "fastd_matype": 0}]
        if combo_type_lower == "stochrsi":
            return [
                {
                    "timeperiod": 14,
                    "fastk_period": 5,
                    "fastd_period": 3,
                    "fastd_matype": 0,
                }
            ]

        return []

    @staticmethod
    def _combo_list_to_dict(combo_type: str, combo: List) -> Dict:
        combo_type_lower = combo_type.lower()
        if combo_type_lower == "macd" and len(combo) >= 3:
            return {"fastperiod": combo[0], "slowperiod": combo[1], "signalperiod": combo[2]}
        if combo_type_lower == "stoch" and len(combo) >= 5:
            return {
                "fastk_period": combo[0],
                "slowk_period": combo[1],
                "slowk_matype": combo[2],
                "slowd_period": combo[3],
                "slowd_matype": combo[4],
            }
        if combo_type_lower == "stochf" and len(combo) >= 3:
            return {"fastk_period": combo[0], "fastd_period": combo[1], "fastd_matype": combo[2]}
        if combo_type_lower == "stochrsi" and len(combo) >= 4:
            return {
                "timeperiod": combo[0],
                "fastk_period": combo[1],
                "fastd_period": combo[2],
                "fastd_matype": combo[3],
            }

        return {}
