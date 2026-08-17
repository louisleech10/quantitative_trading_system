"""驗 A1-3：§V-4 新形式（champion 改由 OOS metric 選）是否真會使 golden 轉紅。

原形式（IS 選、OOS 評）vs mutation（OOS 選、OOS 評）。
若 mutation 下 noise 案例仍落在新 band [0.30,0.70]，則 §V-4 仍不可證偽 ⇒ A1-3 沒修好。
"""
import itertools, math
import numpy as np
from scipy.stats import rankdata


def sharpe_pp(x):
    x = np.asarray(x, float)
    if x.size < 2:
        return np.nan
    s = x.std(ddof=1)
    return np.nan if s == 0 else x.mean() / s


def pbo(M, S, champion_from="is"):
    T, N = M.shape
    base, rem = divmod(T, S)
    blocks, st = [], 0
    for i in range(S):
        L = base + (1 if i < rem else 0)
        blocks.append(np.arange(st, st + L)); st += L
    used = neg = 0
    for combo in itertools.combinations(range(S), S // 2):
        is_idx = np.concatenate([blocks[i] for i in combo])
        oos_idx = np.concatenate([blocks[i] for i in range(S) if i not in combo])
        is_m = np.array([sharpe_pp(M[is_idx, j]) for j in range(N)])
        oos_m = np.array([sharpe_pp(M[oos_idx, j]) for j in range(N)])
        valid = np.where(np.isfinite(is_m) & np.isfinite(oos_m))[0]
        if valid.size < 2:
            continue
        pos = {c: i for i, c in enumerate(valid)}
        sel = is_m if champion_from == "is" else oos_m
        champ = valid[int(np.argmax(sel[valid]))]
        r = rankdata(oos_m[valid], method="average")[pos[champ]] / (valid.size + 1)
        neg += (math.log(r / (1 - r)) < 0); used += 1
    return neg / used


rng = np.random.default_rng(20260817)
M = rng.standard_normal((1200, 50)) * 0.01           # A1-2 逐字生成式
Ma = M.copy(); Ma[:, 0] += 0.01 * 0.15               # A1-1 alpha_detectable
Mu = M.copy(); Mu[:, 0] += 0.01 * 1.0 / math.sqrt(8760)   # A1-1 alpha_undetectable

for label, mat, cond in (("noise  ∈[0.30,0.70]", M, lambda v: 0.30 <= v <= 0.70),
                         ("alpha_detectable <0.30", Ma, lambda v: v < 0.30),
                         ("alpha_undetectable >0.40", Mu, lambda v: v > 0.40)):
    base_v = pbo(mat, 12, "is")
    mut_v = pbo(mat, 12, "oos")
    print(f"{label}: 原形式={base_v:.4f}({'綠' if cond(base_v) else '紅'})  "
          f"§V-4 mutation(OOS 選 champion)={mut_v:.4f}({'綠' if cond(mut_v) else '紅'})")
