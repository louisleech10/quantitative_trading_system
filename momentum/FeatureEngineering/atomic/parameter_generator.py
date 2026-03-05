from __future__ import annotations

import logging
from typing import List, Dict

import numpy as np

logger = logging.getLogger(__name__)


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
                    try:
                        entry = ParameterGenerator._combo_list_to_dict(combo_type, combo)
                        combos.append(entry)
                    except ValueError as exc:
                        logger.warning("Skipping invalid combo for %s: %s", combo_type, exc)
            return combos

        combo_type_lower = combo_type.lower()
        if combo_type_lower == "macd":
            return [{"fastperiod": 12, "slowperiod": 26, "signalperiod": 9}]
        if combo_type_lower == "macdext":
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

        if combo_type_lower == "macd":
            if len(combo) < 3:
                raise ValueError(
                    f"MACD combo requires [fastperiod, slowperiod, signalperiod], got {combo!r}"
                )
            return {"fastperiod": combo[0], "slowperiod": combo[1], "signalperiod": combo[2]}

        if combo_type_lower == "macdext":
            if len(combo) < 3:
                raise ValueError(
                    f"MACDEXT combo requires [fastperiod, slowperiod, signalperiod], got {combo!r}"
                )
            return {"fastperiod": combo[0], "slowperiod": combo[1], "signalperiod": combo[2]}

        if combo_type_lower == "stoch":
            # Semantic: [fastk_period, slowk_period, slowd_period, slowk_matype, slowd_matype]
            # Config typically provides [fastk, slowk, slowd] with matype defaulting to 0.
            if len(combo) < 1:
                raise ValueError(f"STOCH combo requires at least [fastk_period], got {combo!r}")
            fastk = combo[0]
            slowk = combo[1] if len(combo) > 1 else 3
            slowd = combo[2] if len(combo) > 2 else 3
            slowk_matype = combo[3] if len(combo) > 3 else 0
            slowd_matype = combo[4] if len(combo) > 4 else 0
            if len(combo) < 5:
                logger.warning(
                    "STOCH combo %r is missing %d parameter(s); using defaults "
                    "slowk=%s slowd=%s slowk_matype=%s slowd_matype=%s",
                    combo,
                    5 - len(combo),
                    slowk,
                    slowd,
                    slowk_matype,
                    slowd_matype,
                )
            return {
                "fastk_period": fastk,
                "slowk_period": slowk,
                "slowk_matype": slowk_matype,
                "slowd_period": slowd,
                "slowd_matype": slowd_matype,
            }

        if combo_type_lower == "stochf":
            # Semantic: [fastk_period, fastd_period, fastd_matype]
            if len(combo) < 1:
                raise ValueError(f"STOCHF combo requires at least [fastk_period], got {combo!r}")
            fastk = combo[0]
            fastd = combo[1] if len(combo) > 1 else 3
            fastd_matype = combo[2] if len(combo) > 2 else 0
            if len(combo) < 3:
                logger.warning(
                    "STOCHF combo %r is missing %d parameter(s); using defaults "
                    "fastd_period=%s fastd_matype=%s",
                    combo,
                    3 - len(combo),
                    fastd,
                    fastd_matype,
                )
            return {"fastk_period": fastk, "fastd_period": fastd, "fastd_matype": fastd_matype}

        if combo_type_lower == "stochrsi":
            # Semantic: [timeperiod, fastk_period, fastd_period, fastd_matype]
            if len(combo) < 1:
                raise ValueError(f"STOCHRSI combo requires at least [timeperiod], got {combo!r}")
            timeperiod = combo[0]
            fastk = combo[1] if len(combo) > 1 else 5
            fastd = combo[2] if len(combo) > 2 else 3
            fastd_matype = combo[3] if len(combo) > 3 else 0
            if len(combo) < 4:
                logger.warning(
                    "STOCHRSI combo %r is missing %d parameter(s); using defaults "
                    "fastk_period=%s fastd_period=%s fastd_matype=%s",
                    combo,
                    4 - len(combo),
                    fastk,
                    fastd,
                    fastd_matype,
                )
            return {
                "timeperiod": timeperiod,
                "fastk_period": fastk,
                "fastd_period": fastd,
                "fastd_matype": fastd_matype,
            }

        if combo_type_lower == "apo":
            if len(combo) < 2:
                raise ValueError(
                    f"APO combo requires [fastperiod, slowperiod], got {combo!r}"
                )
            return {
                "fastperiod": combo[0],
                "slowperiod": combo[1],
                "matype": combo[2] if len(combo) > 2 else 0,
            }

        if combo_type_lower == "ppo":
            if len(combo) < 2:
                raise ValueError(
                    f"PPO combo requires [fastperiod, slowperiod], got {combo!r}"
                )
            return {
                "fastperiod": combo[0],
                "slowperiod": combo[1],
                "matype": combo[2] if len(combo) > 2 else 0,
            }

        if combo_type_lower == "ultosc":
            if len(combo) < 3:
                raise ValueError(
                    f"ULTOSC combo requires [timeperiod1, timeperiod2, timeperiod3], got {combo!r}"
                )
            return {"timeperiod1": combo[0], "timeperiod2": combo[1], "timeperiod3": combo[2]}

        raise ValueError(
            f"Unknown combo_type: {combo_type!r} with combo {combo!r}. "
            "Supported types: macd, macdext, stoch, stochf, stochrsi, apo, ppo, ultosc."
        )
