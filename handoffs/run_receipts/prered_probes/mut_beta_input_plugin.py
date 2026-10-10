"""PRE-RED Task 2.4 mutant④a：BETA 輸入改回 (close, volume)（_INPUT_TYPE_MAP 由 hl 移到 close_volume）。"""
from momentum.FeatureEngineering.atomic.talib_wrapper import TALibWrapper as T
T._INPUT_TYPE_MAP["hl"].discard("BETA")
T._INPUT_TYPE_MAP["close_volume"].add("BETA")
