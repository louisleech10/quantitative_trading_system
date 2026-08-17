"""GAP-1 J6-2：MinBTL 上界保守性統計 oracle 探針（G1-R7 部分收回之驗收⑨ 可行性驗證）。

主張：T = min_btl_years_upper_bound(N=100, SR_target=1.0) = 2*ln(100)/1.0**2 = 9.2103 年時，
100 條 iid 噪音策略之「最大年化 SR」平均值應 <= 1.0（若上界保守則成立）。
"""
import math
import numpy as np

N_TRIALS = 100
TARGET_SR = 1.0
T_YEARS = 2 * math.log(N_TRIALS) / TARGET_SR ** 2
PPY = 365  # 日頻（crypto 全年交易）
n_obs = int(round(T_YEARS * PPY))

maxima = []
for seed_off in range(20):
    rng = np.random.default_rng(20260817 + seed_off)
    M = rng.standard_normal((n_obs, N_TRIALS)) * 0.01
    sr_pp = M.mean(axis=0) / M.std(axis=0, ddof=1)
    maxima.append(float(np.max(sr_pp) * math.sqrt(PPY)))

print(f"T_YEARS={T_YEARS!r} n_obs={n_obs}")
print(f"mean(max annualized SR)={np.mean(maxima):.6f}  max={max(maxima):.6f}  min={min(maxima):.6f}")
print(f"assertion mean<=1.0 -> {np.mean(maxima) <= 1.0}；all<=1.0 -> {max(maxima) <= 1.0}")
g = 0.5772156649015329
from scipy.stats import norm
approx = (((1 - g) * norm.ppf(1 - 1 / N_TRIALS) + g * norm.ppf(1 - 1 / (N_TRIALS * math.e)))
          / math.sqrt(n_obs - 1) * math.sqrt(PPY))
print(f"analytic E[maxSR]_annualized approx={approx:.6f}")
