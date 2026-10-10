"""PRE-RED Task 2.4 mutant④b：L3 滾動統計輸出乘 1.01（替換 numba_rolling 之 fused 函式）。"""
from momentum.FeatureEngineering.operators import numba_rolling as nr
_f, _m = nr.fused_rolling_stats, nr.fused_rolling_stats_multi_window
nr.fused_rolling_stats = lambda data, window: _f(data, window) * 1.01
nr.fused_rolling_stats_multi_window = lambda values, windows: _m(values, windows) * 1.01
