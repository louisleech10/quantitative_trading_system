"""TA-Lib 指標輸入語義表：indicator → input_type → DataFrame 欄位（ordered）。

C1-2 oracle：獨立硬編 mapping，不得從 TALibWrapper._INPUT_TYPE_MAP / list_indicators() 衍生。
"""

from __future__ import annotations

from typing import Dict, List, Literal, Tuple

import numpy as np
import pandas as pd

InputType = Literal["single", "hlc", "hl", "hlcv", "ohlc", "close_volume"]

# indicator → (input_type, ordered column names for talib direct call)
# 獨立 oracle — 變更須與 wrapper 行為對齊並更新 C1-2 測試
TALIB_INPUT_SEMANTICS: Dict[str, Tuple[InputType, Tuple[str, ...]]] = {
    "AD": ("hlcv", ("high", "low", "close", "volume")),
    "ADOSC": ("hlcv", ("high", "low", "close", "volume")),
    "ADX": ("hlc", ("high", "low", "close")),
    "ADXR": ("hlc", ("high", "low", "close")),
    "APO": ("single", ("close")),
    "AROON": ("hl", ("high", "low")),
    "AROONOSC": ("hl", ("high", "low")),
    "ATR": ("hlc", ("high", "low", "close")),
    "AVGPRICE": ("single", ("close")),
    "BBANDS": ("single", ("close")),
    "BETA": ("hl", ("high", "low")),
    "BOP": ("ohlc", ("open", "high", "low", "close")),
    "Beta_CloseVolume": ("close_volume", ("close", "volume")),
    "CCI": ("hlc", ("high", "low", "close")),
    "CDL2CROWS": ("ohlc", ("open", "high", "low", "close")),
    "CDL3BLACKCROWS": ("ohlc", ("open", "high", "low", "close")),
    "CDL3INSIDE": ("ohlc", ("open", "high", "low", "close")),
    "CDL3LINESTRIKE": ("ohlc", ("open", "high", "low", "close")),
    "CDL3OUTSIDE": ("ohlc", ("open", "high", "low", "close")),
    "CDL3STARSINSOUTH": ("ohlc", ("open", "high", "low", "close")),
    "CDL3WHITESOLDIERS": ("ohlc", ("open", "high", "low", "close")),
    "CDLABANDONEDBABY": ("ohlc", ("open", "high", "low", "close")),
    "CDLADVANCEBLOCK": ("ohlc", ("open", "high", "low", "close")),
    "CDLBELTHOLD": ("ohlc", ("open", "high", "low", "close")),
    "CDLBREAKAWAY": ("ohlc", ("open", "high", "low", "close")),
    "CDLCLOSINGMARUBOZU": ("ohlc", ("open", "high", "low", "close")),
    "CDLCONCEALBABYSWALL": ("ohlc", ("open", "high", "low", "close")),
    "CDLCOUNTERATTACK": ("ohlc", ("open", "high", "low", "close")),
    "CDLDARKCLOUDCOVER": ("ohlc", ("open", "high", "low", "close")),
    "CDLDOJI": ("ohlc", ("open", "high", "low", "close")),
    "CDLDOJISTAR": ("ohlc", ("open", "high", "low", "close")),
    "CDLDRAGONFLYDOJI": ("ohlc", ("open", "high", "low", "close")),
    "CDLENGULFING": ("ohlc", ("open", "high", "low", "close")),
    "CDLEVENINGDOJISTAR": ("ohlc", ("open", "high", "low", "close")),
    "CDLEVENINGSTAR": ("ohlc", ("open", "high", "low", "close")),
    "CDLGAPSIDESIDEWHITE": ("ohlc", ("open", "high", "low", "close")),
    "CDLGRAVESTONEDOJI": ("ohlc", ("open", "high", "low", "close")),
    "CDLHAMMER": ("ohlc", ("open", "high", "low", "close")),
    "CDLHANGINGMAN": ("ohlc", ("open", "high", "low", "close")),
    "CDLHARAMI": ("ohlc", ("open", "high", "low", "close")),
    "CDLHARAMICROSS": ("ohlc", ("open", "high", "low", "close")),
    "CDLHIGHWAVE": ("ohlc", ("open", "high", "low", "close")),
    "CDLHIKKAKE": ("ohlc", ("open", "high", "low", "close")),
    "CDLHIKKAKEMOD": ("ohlc", ("open", "high", "low", "close")),
    "CDLHOMINGPIGEON": ("ohlc", ("open", "high", "low", "close")),
    "CDLIDENTICAL3CROWS": ("ohlc", ("open", "high", "low", "close")),
    "CDLINNECK": ("ohlc", ("open", "high", "low", "close")),
    "CDLINVERTEDHAMMER": ("ohlc", ("open", "high", "low", "close")),
    "CDLKICKING": ("ohlc", ("open", "high", "low", "close")),
    "CDLKICKINGBYLENGTH": ("ohlc", ("open", "high", "low", "close")),
    "CDLLADDERBOTTOM": ("ohlc", ("open", "high", "low", "close")),
    "CDLLONGLEGGEDDOJI": ("ohlc", ("open", "high", "low", "close")),
    "CDLLONGLINE": ("ohlc", ("open", "high", "low", "close")),
    "CDLMARUBOZU": ("ohlc", ("open", "high", "low", "close")),
    "CDLMATCHINGLOW": ("ohlc", ("open", "high", "low", "close")),
    "CDLMATHOLD": ("ohlc", ("open", "high", "low", "close")),
    "CDLMORNINGDOJISTAR": ("ohlc", ("open", "high", "low", "close")),
    "CDLMORNINGSTAR": ("ohlc", ("open", "high", "low", "close")),
    "CDLONNECK": ("ohlc", ("open", "high", "low", "close")),
    "CDLPIERCING": ("ohlc", ("open", "high", "low", "close")),
    "CDLRICKSHAWMAN": ("ohlc", ("open", "high", "low", "close")),
    "CDLRISEFALL3METHODS": ("ohlc", ("open", "high", "low", "close")),
    "CDLSEPARATINGLINES": ("ohlc", ("open", "high", "low", "close")),
    "CDLSHOOTINGSTAR": ("ohlc", ("open", "high", "low", "close")),
    "CDLSHORTLINE": ("ohlc", ("open", "high", "low", "close")),
    "CDLSPINNINGTOP": ("ohlc", ("open", "high", "low", "close")),
    "CDLSTALLEDPATTERN": ("ohlc", ("open", "high", "low", "close")),
    "CDLSTICKSANDWICH": ("ohlc", ("open", "high", "low", "close")),
    "CDLTAKURI": ("ohlc", ("open", "high", "low", "close")),
    "CDLTASUKIGAP": ("ohlc", ("open", "high", "low", "close")),
    "CDLTHRUSTING": ("ohlc", ("open", "high", "low", "close")),
    "CDLTRISTAR": ("ohlc", ("open", "high", "low", "close")),
    "CDLUNIQUE3RIVER": ("ohlc", ("open", "high", "low", "close")),
    "CDLUPSIDEGAP2CROWS": ("ohlc", ("open", "high", "low", "close")),
    "CDLXSIDEGAP3METHODS": ("ohlc", ("open", "high", "low", "close")),
    "CMO": ("single", ("close")),
    "CORREL": ("hl", ("high", "low")),
    "Correl_CloseVolume": ("close_volume", ("close", "volume")),
    "DEMA": ("single", ("close")),
    "DX": ("hlc", ("high", "low", "close")),
    "EMA": ("single", ("close")),
    "HT_DCPERIOD": ("single", ("close")),
    "HT_DCPHASE": ("single", ("close")),
    "HT_PHASOR": ("single", ("close")),
    "HT_SINE": ("single", ("close")),
    "HT_TRENDLINE": ("single", ("close")),
    "HT_TRENDMODE": ("single", ("close")),
    "KAMA": ("single", ("close")),
    "LINEARREG": ("single", ("close")),
    "LINEARREG_ANGLE": ("single", ("close")),
    "LINEARREG_INTERCEPT": ("single", ("close")),
    "LINEARREG_SLOPE": ("single", ("close")),
    "MA": ("single", ("close")),
    "MACD": ("single", ("close")),
    "MACDEXT": ("single", ("close")),
    "MACDFIX": ("single", ("close")),
    "MAMA": ("single", ("close")),
    "MAVP": ("single", ("close")),
    "MEDPRICE": ("single", ("close")),
    "MFI": ("hlcv", ("high", "low", "close", "volume")),
    "MIDPOINT": ("single", ("close")),
    "MIDPRICE": ("hl", ("high", "low")),
    "MINUS_DI": ("hlc", ("high", "low", "close")),
    "MINUS_DM": ("hl", ("high", "low")),
    "MOM": ("single", ("close")),
    "NATR": ("hlc", ("high", "low", "close")),
    "OBV": ("close_volume", ("close", "volume")),
    "PLUS_DI": ("hlc", ("high", "low", "close")),
    "PLUS_DM": ("hl", ("high", "low")),
    "PPO": ("single", ("close")),
    "ROC": ("single", ("close")),
    "ROCP": ("single", ("close")),
    "ROCR": ("single", ("close")),
    "ROCR100": ("single", ("close")),
    "RSI": ("single", ("close")),
    "SAR": ("hl", ("high", "low")),
    "SAREXT": ("hl", ("high", "low")),
    "SMA": ("single", ("close")),
    "STDDEV": ("single", ("close")),
    "STOCH": ("hlc", ("high", "low", "close")),
    "STOCHF": ("hlc", ("high", "low", "close")),
    "STOCHRSI": ("single", ("close")),
    "T3": ("single", ("close")),
    "TEMA": ("single", ("close")),
    "TRANGE": ("hlc", ("high", "low", "close")),
    "TRIMA": ("single", ("close")),
    "TRIX": ("single", ("close")),
    "TSF": ("single", ("close")),
    "TYPPRICE": ("single", ("close")),
    "ULTOSC": ("hlc", ("high", "low", "close")),
    "VAR": ("single", ("close")),
    "WCLPRICE": ("single", ("close")),
    "WILLR": ("hlc", ("high", "low", "close")),
    "WMA": ("single", ("close")),
}

# price_transform：L1 adapter 計算，排除 C1-2 byte 比對
C12_EXCLUDED_INDICATORS = frozenset({"AVGPRICE", "MEDPRICE", "TYPPRICE", "WCLPRICE"})

# MAVP 需 periods 陣列，C1-2 另測
C12_MAVP_ALLOWLIST = frozenset({"MAVP"})


def build_talib_input_semantics(
    registry_names: List[str] | None = None,
) -> Dict[str, Tuple[InputType, Tuple[str, ...]]]:
    """回傳獨立硬編語義表（registry_names 保留 API 相容，不影響內容）。"""
    return TALIB_INPUT_SEMANTICS


def arrays_from_dataframe(
    indicator_name: str,
    data: pd.DataFrame,
    *,
    data_source: str = "close",
) -> List[np.ndarray]:
    """依 TALIB_INPUT_SEMANTICS 從 DataFrame 取出 talib 直呼用 ndarray 列表。"""
    if indicator_name not in TALIB_INPUT_SEMANTICS:
        raise KeyError(f"No semantics for {indicator_name}")
    input_type, columns = TALIB_INPUT_SEMANTICS[indicator_name]
    if input_type == "single":
        col = data_source if data_source in data.columns else columns[0]
        return [data[col].to_numpy(dtype=float)]
    return [data[col].to_numpy(dtype=float) for col in columns]

