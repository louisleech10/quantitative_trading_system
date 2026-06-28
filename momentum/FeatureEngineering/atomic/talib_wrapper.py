from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Literal, Optional

import numpy as np
import pandas as pd
import talib
from talib import abstract

from momentum.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class IndicatorSpec:
    """Full indicator specification."""

    name: str
    talib_func: str
    category: str
    input_type: Literal["single", "hlc", "hl", "hlcv", "ohlc", "close_volume"]
    output_count: int
    output_names: List[str]
    default_params: Dict
    param_strategy: str
    computed_in_adapter: bool = False


class TALibWrapper:
    """Unified TA-Lib interface with multi-source support."""

    INDICATOR_REGISTRY: Dict[str, IndicatorSpec] = {}
    # Naming rule:
    # '_' separates major segments, while '-' separates values inside Params.
    PARAM_VALUE_DELIMITER = "-"

    @staticmethod
    def normalize_source_label(source_label: str) -> str:
        """Normalize source segment: use '-' inside segment, keep '_' for segment boundaries."""
        return str(source_label).replace("_", "-")

    @staticmethod
    def normalize_indicator_name(indicator_name: str) -> str:
        """Normalize indicator segment: use '-' inside segment, keep '_' for segment boundaries."""
        return str(indicator_name).replace("_", "-")

    _CATEGORY_MAP = {
        "trend": [
            "EMA",
            "SMA",
            "WMA",
            "DEMA",
            "TEMA",
            "TRIMA",
            "KAMA",
            "T3",
            "MAMA",
            "HT_TRENDLINE",
            "SAR",
            "SAREXT",
            "BBANDS",
            "MAVP",
            "MA",
            "MIDPOINT",
            "MIDPRICE",
        ],
        "momentum": [
            "RSI",
            "MACD",
            "MACDEXT",
            "MACDFIX",
            "ADX",
            "ADXR",
            "DX",
            "PLUS_DI",
            "MINUS_DI",
            "PLUS_DM",
            "MINUS_DM",
            "CCI",
            "CMO",
            "MOM",
            "ROC",
            "ROCP",
            "ROCR",
            "ROCR100",
            "APO",
            "PPO",
            "AROON",
            "AROONOSC",
            "BOP",
            "TRIX",
            "ULTOSC",
            "WILLR",
            "MFI",
            "STOCH",
            "STOCHF",
            "STOCHRSI",
        ],
        "volatility": ["ATR", "NATR", "TRANGE"],
        "volume": ["OBV", "AD", "ADOSC"],
        "cycle": [
            "HT_DCPERIOD",
            "HT_DCPHASE",
            "HT_PHASOR",
            "HT_SINE",
            "HT_TRENDMODE",
        ],
        "pattern": [
            "CDL2CROWS",
            "CDL3BLACKCROWS",
            "CDL3INSIDE",
            "CDL3LINESTRIKE",
            "CDL3OUTSIDE",
            "CDL3STARSINSOUTH",
            "CDL3WHITESOLDIERS",
            "CDLABANDONEDBABY",
            "CDLADVANCEBLOCK",
            "CDLBELTHOLD",
            "CDLBREAKAWAY",
            "CDLCLOSINGMARUBOZU",
            "CDLCONCEALBABYSWALL",
            "CDLCOUNTERATTACK",
            "CDLDARKCLOUDCOVER",
            "CDLDOJI",
            "CDLDOJISTAR",
            "CDLDRAGONFLYDOJI",
            "CDLENGULFING",
            "CDLEVENINGDOJISTAR",
            "CDLEVENINGSTAR",
            "CDLGAPSIDESIDEWHITE",
            "CDLGRAVESTONEDOJI",
            "CDLHAMMER",
            "CDLHANGINGMAN",
            "CDLHARAMI",
            "CDLHARAMICROSS",
            "CDLHIGHWAVE",
            "CDLHIKKAKE",
            "CDLHIKKAKEMOD",
            "CDLHOMINGPIGEON",
            "CDLIDENTICAL3CROWS",
            "CDLINNECK",
            "CDLINVERTEDHAMMER",
            "CDLKICKING",
            "CDLKICKINGBYLENGTH",
            "CDLLADDERBOTTOM",
            "CDLLONGLEGGEDDOJI",
            "CDLLONGLINE",
            "CDLMARUBOZU",
            "CDLMATCHINGLOW",
            "CDLMATHOLD",
            "CDLMORNINGDOJISTAR",
            "CDLMORNINGSTAR",
            "CDLONNECK",
            "CDLPIERCING",
            "CDLRICKSHAWMAN",
            "CDLRISEFALL3METHODS",
            "CDLSEPARATINGLINES",
            "CDLSHOOTINGSTAR",
            "CDLSHORTLINE",
            "CDLSPINNINGTOP",
            "CDLSTALLEDPATTERN",
            "CDLSTICKSANDWICH",
            "CDLTAKURI",
            "CDLTASUKIGAP",
            "CDLTHRUSTING",
            "CDLTRISTAR",
            "CDLUNIQUE3RIVER",
            "CDLUPSIDEGAP2CROWS",
            "CDLXSIDEGAP3METHODS",
        ],
        "statistics": [
            "BETA",
            "CORREL",
            "Beta_CloseVolume",
            "Correl_CloseVolume",
            "LINEARREG",
            "LINEARREG_ANGLE",
            "LINEARREG_INTERCEPT",
            "LINEARREG_SLOPE",
            "STDDEV",
            "TSF",
            "VAR",
        ],
        "price_transform": ["AVGPRICE", "MEDPRICE", "TYPPRICE", "WCLPRICE"],
    }

    _ALIAS_TALIB_FUNC: Dict[str, str] = {
        "Beta_CloseVolume": "BETA",
        "Correl_CloseVolume": "CORREL",
    }

    _INPUT_TYPE_MAP = {
        "hl": {
            "AROON",
            "AROONOSC",
            "MIDPRICE",
            "SAR",
            "SAREXT",
            "PLUS_DM",
            "MINUS_DM",
            "BETA",
            "CORREL",
        },
        "hlc": {
            "ADX",
            "ADXR",
            "DX",
            "PLUS_DI",
            "MINUS_DI",
            "CCI",
            "WILLR",
            "ULTOSC",
            "TRANGE",
            "ATR",
            "NATR",
            "STOCH",
            "STOCHF",
        },
        "hlcv": {"MFI", "AD", "ADOSC"},
        "ohlc": {"BOP"},
        "close_volume": {"OBV", "Beta_CloseVolume", "Correl_CloseVolume"},
    }

    _OUTPUT_NAME_OVERRIDES = {
        "MACD": ["Line", "Signal", "Hist"],
        "MACDEXT": ["Line", "Signal", "Hist"],
        "MACDFIX": ["Line", "Signal", "Hist"],
        "BBANDS": ["Upper", "Middle", "Lower"],
        "HT_PHASOR": ["InPhase", "Quadrature"],
        "HT_SINE": ["Sine", "LeadSine"],
        "MAMA": ["MAMA", "FAMA"],
    }

    _PARAM_ORDER = {
        "MACD": ["fastperiod", "slowperiod", "signalperiod"],
        "MACDEXT": ["fastperiod", "slowperiod", "signalperiod"],
        "MACDFIX": ["signalperiod"],
        "MAVP": ["periods"],
        "APO": ["fastperiod", "slowperiod", "matype"],
        "PPO": ["fastperiod", "slowperiod", "matype"],
        "ULTOSC": ["timeperiod1", "timeperiod2", "timeperiod3"],
        "STOCH": [
            "fastk_period",
            "slowk_period",
            "slowk_matype",
            "slowd_period",
            "slowd_matype",
        ],
        "STOCHF": ["fastk_period", "fastd_period", "fastd_matype"],
        "STOCHRSI": ["timeperiod", "fastk_period", "fastd_period", "fastd_matype"],
        "BBANDS": ["timeperiod", "nbdevup", "nbdevdn", "matype"],
        "SAR": ["acceleration", "maximum"],
        "SAREXT": [
            "startvalue",
            "offsetonreverse",
            "accelerationinitlong",
            "accelerationlong",
            "accelerationmaxlong",
            "accelerationinitshort",
            "accelerationshort",
            "accelerationmaxshort",
        ],
    }

    @classmethod
    def initialize(cls) -> None:
        if cls.INDICATOR_REGISTRY:
            return

        for category, names in cls._CATEGORY_MAP.items():
            for name in names:
                talib_func = cls._ALIAS_TALIB_FUNC.get(name, name)
                if name in cls._ALIAS_TALIB_FUNC:
                    func = abstract.Function(talib_func)
                    output_names = cls._OUTPUT_NAME_OVERRIDES.get(talib_func, func.output_names)
                    input_type = cls._resolve_input_type(name)
                    default_params = dict(func.parameters)
                    param_strategy = "fibonacci" if "timeperiod" in default_params else "fixed"
                    cls.INDICATOR_REGISTRY[name] = IndicatorSpec(
                        name=name,
                        talib_func=talib_func,
                        category=category,
                        input_type=input_type,
                        output_count=len(output_names),
                        output_names=output_names,
                        default_params=default_params,
                        param_strategy=param_strategy,
                        computed_in_adapter=False,
                    )
                    continue

                func = abstract.Function(name)
                output_names = cls._OUTPUT_NAME_OVERRIDES.get(name, func.output_names)
                input_type = cls._resolve_input_type(name)
                default_params = dict(func.parameters)
                param_strategy = "fibonacci" if "timeperiod" in default_params else "fixed"
                computed_in_adapter = category == "price_transform"

                cls.INDICATOR_REGISTRY[name] = IndicatorSpec(
                    name=name,
                    talib_func=name,
                    category=category,
                    input_type=input_type,
                    output_count=len(output_names),
                    output_names=output_names,
                    default_params=default_params,
                    param_strategy=param_strategy,
                    computed_in_adapter=computed_in_adapter,
                )

        logger.info(f"Loaded {len(cls.INDICATOR_REGISTRY)} TA-Lib indicators")

    @classmethod
    def compute(
        cls,
        indicator_name: str,
        data: pd.DataFrame | pd.Series,
        params: Dict,
        data_source: str = "close",
    ) -> pd.DataFrame:
        cls.initialize()
        spec = cls.get_indicator_spec(indicator_name)

        if spec.computed_in_adapter:
            return pd.DataFrame(index=cls._get_index(data))

        func = getattr(talib, spec.talib_func)
        params = dict(params or {})

        # Snapshot params before _prepare_inputs, because MAVP uses params.pop()
        # which would destroy the dict before _to_dataframe uses it for column naming.
        params_for_naming = dict(params)
        inputs, source_label = cls._prepare_inputs(spec, data, data_source, params)
        output = func(*inputs, **params)

        return cls._to_dataframe(
            output=output,
            index=cls._get_index(data),
            source_label=source_label,
            spec=spec,
            params=params_for_naming,
        )

    @classmethod
    def compute_batch(
        cls,
        indicator_name: str,
        data: pd.DataFrame,
        params_list: List[Dict],
        data_sources: List[str],
    ) -> pd.DataFrame:
        cls.initialize()
        spec = cls.get_indicator_spec(indicator_name)

        frames = []
        if spec.input_type == "single":
            for source in data_sources:
                for params in params_list:
                    frames.append(cls.compute(indicator_name, data, params, source))
        else:
            for params in params_list:
                frames.append(cls.compute(indicator_name, data, params, "close"))

        if not frames:
            return pd.DataFrame(index=data.index)

        return pd.concat(frames, axis=1)

    @classmethod
    def get_indicator_spec(cls, name: str) -> IndicatorSpec:
        cls.initialize()
        if name not in cls.INDICATOR_REGISTRY:
            raise KeyError(f"Indicator not registered: {name}")
        return cls.INDICATOR_REGISTRY[name]

    @classmethod
    def list_indicators(cls, category: Optional[str] = None) -> List[IndicatorSpec]:
        cls.initialize()
        if category is None:
            return list(cls.INDICATOR_REGISTRY.values())
        return [spec for spec in cls.INDICATOR_REGISTRY.values() if spec.category == category]

    @classmethod
    def list_categories(cls) -> List[str]:
        cls.initialize()
        return sorted({spec.category for spec in cls.INDICATOR_REGISTRY.values()})

    @classmethod
    def _resolve_input_type(cls, name: str) -> Literal["single", "hlc", "hl", "hlcv", "ohlc", "close_volume"]:
        for input_type, names in cls._INPUT_TYPE_MAP.items():
            if name in names:
                return input_type  # type: ignore[return-value]
        if name.startswith("CDL"):
            return "ohlc"
        return "single"

    @classmethod
    def _prepare_inputs(
        cls,
        spec: IndicatorSpec,
        data: pd.DataFrame | pd.Series,
        data_source: str,
        params: Dict,
    ) -> tuple[List[np.ndarray], str]:
        if spec.name == "MAVP":
            series = data if isinstance(data, pd.Series) else data[data_source]
            periods_value = params.pop("periods", None)
            if periods_value is None:
                periods_value = params.get("timeperiod", 30)
            if isinstance(periods_value, (list, tuple, np.ndarray)):
                periods_array = np.array(periods_value, dtype=float)
                if len(periods_array) != len(series):
                    periods_array = np.full(len(series), float(periods_array[0]))
            else:
                periods_array = np.full(len(series), float(periods_value))
            return [series.to_numpy(dtype=float), periods_array], data_source

        if isinstance(data, pd.Series):
            series = data
            if spec.input_type != "single":
                raise ValueError(f"Indicator {spec.name} requires multi-input data")
            return [series.to_numpy(dtype=float)], data_source

        if spec.input_type == "single":
            if data_source not in data.columns:
                raise KeyError(f"Missing data source {data_source}")
            return [data[data_source].to_numpy(dtype=float)], data_source

        if spec.input_type == "hlc":
            return [
                data["high"].to_numpy(dtype=float),
                data["low"].to_numpy(dtype=float),
                data["close"].to_numpy(dtype=float),
            ], "hlc"

        if spec.input_type == "hl":
            return [
                data["high"].to_numpy(dtype=float),
                data["low"].to_numpy(dtype=float),
            ], "hl"

        if spec.input_type == "hlcv":
            return [
                data["high"].to_numpy(dtype=float),
                data["low"].to_numpy(dtype=float),
                data["close"].to_numpy(dtype=float),
                data["volume"].to_numpy(dtype=float),
            ], "hlcv"

        if spec.input_type == "ohlc":
            return [
                data["open"].to_numpy(dtype=float),
                data["high"].to_numpy(dtype=float),
                data["low"].to_numpy(dtype=float),
                data["close"].to_numpy(dtype=float),
            ], "ohlc"

        if spec.input_type == "close_volume":
            return [
                data["close"].to_numpy(dtype=float),
                data["volume"].to_numpy(dtype=float),
            ], "close_volume"

        raise ValueError(f"Unknown input type: {spec.input_type}")

    @classmethod
    def _to_dataframe(
        cls,
        output: np.ndarray | tuple,
        index: pd.Index,
        source_label: str,
        spec: IndicatorSpec,
        params: Dict,
    ) -> pd.DataFrame:
        if isinstance(output, tuple):
            arrays = output
        else:
            arrays = (output,)

        frames = []
        param_str = cls._format_params(spec.name, params)
        for idx, array in enumerate(arrays):
            name_suffix = spec.output_names[idx] if len(spec.output_names) > idx else str(idx)
            if len(spec.output_names) == 1:
                indicator_name = spec.name
            else:
                indicator_name = spec.name if name_suffix == spec.name else f"{spec.name}_{name_suffix}"
            normalized_source = cls.normalize_source_label(source_label)
            normalized_indicator = cls.normalize_indicator_name(indicator_name)
            parts = [normalized_source, spec.category, normalized_indicator]
            if param_str:
                parts.append(param_str)
            col_name = "_".join(parts)
            frames.append(pd.Series(array, index=index, name=col_name))

        return pd.concat(frames, axis=1)

    @classmethod
    def _format_params(cls, indicator_name: str, params: Dict) -> str:
        if not params:
            return ""
        ordered_keys = cls._PARAM_ORDER.get(indicator_name)
        if ordered_keys:
            values = [params.get(key) for key in ordered_keys if key in params]
        else:
            values = [params[key] for key in sorted(params.keys())]

        parts = []
        for value in values:
            if value is None:
                continue
            if isinstance(value, float) and value.is_integer():
                parts.append(str(int(value)))
            elif isinstance(value, (list, tuple, np.ndarray)):
                parts.append(str(value[0]))
            else:
                parts.append(str(value))

        return cls.PARAM_VALUE_DELIMITER.join(parts)

    @staticmethod
    def _get_index(data: pd.DataFrame | pd.Series) -> pd.Index:
        return data.index if hasattr(data, "index") else pd.RangeIndex(0)
