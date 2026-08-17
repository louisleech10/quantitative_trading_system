"""Claude 自產審查探針：驗 §G PBO 全噪音 band、E[maxSR] 常數、mutation §V-4 對稱性。"""
import itertools, math
import numpy as np
from scipy.stats import norm, rankdata

def sharpe_pp(x):
    x = np.asarray(x, float)
    if x.size < 2:
        return np.nan
    s = x.std(ddof=1)
    if s == 0:
        return np.nan
    return x.mean() / s

def pbo(M, S, swap=False):
    T, N = M.shape
    base, rem = divmod(T, S)
    blocks, st = [], 0
    for i in range(S):
        L = base + (1 if i < rem else 0)
        blocks.append(np.arange(st, st + L)); st += L
    used, neg, logits = 0, 0, []
    for combo in itertools.combinations(range(S), S // 2):
        is_idx = np.concatenate([blocks[i] for i in combo])
        oos_idx = np.concatenate([blocks[i] for i in range(S) if i not in combo])
        if swap:
            is_idx, oos_idx = oos_idx, is_idx
        is_m = np.array([sharpe_pp(M[is_idx, j]) for j in range(N)])
        oos_m = np.array([sharpe_pp(M[oos_idx, j]) for j in range(N)])
        valid = np.isfinite(is_m) & np.isfinite(oos_m)
        if valid.sum() < 2:
            continue
        idx = np.where(valid)[0]
        champ = idx[np.argmax(is_m[idx])]  # argmax → first max = smallest index
        r = rankdata(oos_m[idx], method="average")[list(idx).index(champ)] / (len(idx) + 1)
        w = math.log(r / (1 - r)); logits.append(w)
        used += 1; neg += (w < 0)
    return neg / used, used, (min(logits), float(np.median(logits)), max(logits))

for label, gen in [("default_rng(T,N)", lambda: np.random.default_rng(20260817).normal(0, 0.01, size=(1200, 50))),
                   ("default_rng(N,T).T", lambda: np.random.default_rng(20260817).normal(0, 0.01, size=(50, 1200)).T),
                   ("legacy seed(T,N)", lambda: (np.random.seed(20260817), np.random.normal(0, 0.01, size=(1200, 50)))[1])]:
    M = gen()
    v, used, lg = pbo(M, 12)
    v2, _, _ = pbo(M, 12, swap=True)
    print(f"{label}: noise pbo={v:.4f} used={used} logits={lg}  swapped={v2:.4f}")
    M2 = M.copy(); M2[:, 0] += 0.01 * 1.0 / math.sqrt(8760)
    va, _, _ = pbo(M2, 12)
    print(f"   alpha(mu=1.0684e-4) pbo={va:.4f}")

g = 0.5772156649015329
for N in (10, 100, 1000):
    print(N, (1 - g) * norm.ppf(1 - 1 / N) + g * norm.ppf(1 - 1 / (N * math.e)))

print("--- alpha sweep (legacy seed, T,N) ---")
np.random.seed(20260817); M = np.random.normal(0, 0.01, size=(1200, 50))
for sr_pp in (0.0107, 0.05, 0.1, 0.15, 0.2, 0.3):
    M2 = M.copy(); M2[:, 0] += 0.01 * sr_pp
    v, _, _ = pbo(M2, 12)
    print(f"sr_pp={sr_pp}: pbo={v:.4f}")
print("--- alpha sweep (default_rng, T,N) ---")
M = np.random.default_rng(20260817).normal(0, 0.01, size=(1200, 50))
for sr_pp in (0.1, 0.15, 0.2, 0.3):
    M2 = M.copy(); M2[:, 0] += 0.01 * sr_pp
    v, _, _ = pbo(M2, 12)
    print(f"sr_pp={sr_pp}: pbo={v:.4f}")
