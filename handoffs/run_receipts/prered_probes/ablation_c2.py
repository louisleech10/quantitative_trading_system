"""PRE-RED Task 2.0（SPEC v4）：對 ablation_classify.py 之 D 欄，以綁定同一份新版產物之獨立 reference 判 C2／U。

用法：python ablation_c2.py <new_prefix> <classify.json> <out.json> [--mutate-l3 <欄名>] [--mutate-upstream <L3 欄名>]
reference：
  Mean／Std／ZScore／Skew／Kurt ＝ tests/feature_engineering/test_ffstat_stable_start.py::_l3_oracle 之數學
    （本檔向量化重寫；啟動時以原版 _l3_oracle 對抽樣欄逐格對照，不等即拋錯）
  Slope ＝ 逐窗最小平方斜率（同 _slope_checks 之 np.polyfit 定義，向量化）
判準（同上兩測試）：新版有限之格 |新−ref| ≤ 1e-5×scale（Mean 等 scale＝max(|ref|,1)；Slope scale＝max(|ref|, nanstd(上游)×1e-3)）；
  新版有限而 ref 為 NaN ⇒ 不符；ref 有限而新版 NaN 只准在新版首個有限值之前（穩定點遮罩）。
依賴域：上游欄（L1）須於 classify 為 C1-full，否則 U（依賴未驗）。
負控制：--mutate-l3 把該欄公開窗有限值乘 1.01（期望 U）；--mutate-upstream 把該 L3 欄之上游於公開起點前、
  第一個公開窗內之一格乘 1.01 並以改壞上游重算該欄（期望 U，因上游不再 C1-full）。
"""

from __future__ import annotations

import importlib.util
import json
import math
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
STATS = ("Mean", "Std", "ZScore", "Skew", "Kurt")
NAME_RX = re.compile(r"^(?P<up>.+)_(?P<stat>Mean|Std|ZScore|Skew|Kurt|Slope)_W(?P<w>\d+)$")


def _test_oracle():
    spec = importlib.util.spec_from_file_location("ffstat_stable_start_t", ROOT / "tests/feature_engineering/test_ffstat_stable_start.py")
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(ROOT))
    spec.loader.exec_module(mod)
    return mod._l3_oracle


def oracle_vec(values: np.ndarray, window: int) -> np.ndarray:
    """_l3_oracle 之向量化重寫（同退化契約）。回傳 (n, 5)：mean、std、zscore、skew、kurt。"""
    n = len(values)
    out = np.full((n, 5), np.nan)
    if n < window:
        return out
    xs = np.lib.stride_tricks.sliding_window_view(values.astype(np.float64), window)
    ok = np.isfinite(xs).all(axis=1)
    idx = np.arange(window - 1, n)
    w = float(window)
    mean = xs.mean(axis=1)
    out[idx[ok], 0] = mean[ok]
    const = ok & (xs.max(axis=1) == xs.min(axis=1))
    out[idx[const], 1] = 0.0
    var = ok & ~const
    dev = xs - mean[:, None]
    std = np.sqrt((dev ** 2).sum(axis=1) / (w - 1.0))
    out[idx[var], 1] = std[var]
    out[idx[var], 2] = (xs[var, -1] - mean[var]) / std[var]
    m2 = (dev ** 2).sum(axis=1)
    nondeg = var & ~(m2 <= 1e-12 * (m2 + w * mean * mean))
    m2n, m3n, m4n = (dev ** 2).mean(axis=1), (dev ** 3).mean(axis=1), (dev ** 4).mean(axis=1)
    with np.errstate(all="ignore"):
        g1 = m3n / m2n ** 1.5
        g2 = m4n / m2n ** 2 - 3.0
        skew = g1 * math.sqrt(w * (w - 1.0)) / (w - 2.0) if window >= 3 else np.full_like(g1, np.nan)
        kurt = ((w + 1.0) * g2 + 6.0) * (w - 1.0) / ((w - 2.0) * (w - 3.0)) if window >= 4 else np.full_like(g2, np.nan)
    sk_ok = nondeg & (np.abs(skew) <= math.sqrt(w) * (1.0 + 1e-9)) if window >= 3 else np.zeros_like(nondeg)
    lo = -2.0 * (w - 1.0) / (w - 3.0) if window > 3 else -np.inf
    # 與 _l3_oracle 逐字同式：lo×(1+1e-9) ≤ kurt ≤ w×(1+1e-9)
    ku_ok = nondeg & (kurt >= lo * (1.0 + 1e-9)) & (kurt <= w * (1.0 + 1e-9)) if window >= 4 else np.zeros_like(nondeg)
    out[idx[sk_ok], 3] = skew[sk_ok]
    out[idx[ku_ok], 4] = kurt[ku_ok]
    # 邊界窗以原版同式（scipy 逐窗）重算：退化門檻 ×10 內、|skew| 距 √n 1e-6 相對內、kurt 距上下界 1e-6 內。
    # 向量化與 scipy 之末位差只在此類窗會翻轉遮罩（ETHUSDT/1h MIDPOINT／MIDPRICE Kurt_W5 實例），非邊界窗遮罩不受影響。
    if window >= 3:
        from scipy import stats

        with np.errstate(all="ignore"):
            near = var & (
                (m2 <= 1e-11 * (m2 + w * mean * mean))
                | (np.abs(np.abs(skew) - math.sqrt(w)) <= 1e-6 * math.sqrt(w))
                | ((window >= 4) & ((np.abs(kurt - w) <= 1e-6 * w) | (np.abs(kurt - lo) <= 1e-6 * abs(lo) if np.isfinite(lo) else False)))
            )
        for k in np.flatnonzero(near):
            win = xs[k]
            i = idx[k]
            out[i, 3] = out[i, 4] = np.nan
            mk = float(np.mean(win))
            m2k = float(np.sum((win - mk) ** 2))
            if m2k <= 1e-12 * (m2k + w * mk * mk):
                continue
            sk = float(stats.skew(win, bias=False))
            if abs(sk) <= math.sqrt(w) * (1.0 + 1e-9):
                out[i, 3] = sk
            if window >= 4:
                ku = float(stats.kurtosis(win, fisher=True, bias=False))
                if lo * (1.0 + 1e-9) <= ku <= w * (1.0 + 1e-9):
                    out[i, 4] = ku
    return out


def slope_vec(values: np.ndarray, window: int) -> np.ndarray:
    n = len(values)
    out = np.full(n, np.nan)
    if n < window:
        return out
    xs = np.lib.stride_tricks.sliding_window_view(values.astype(np.float64), window)
    ok = np.isfinite(xs).all(axis=1)
    x = np.arange(window, dtype=np.float64)
    xc = x - x.mean()
    sl = ((xs - xs.mean(axis=1, keepdims=True)) * xc).sum(axis=1) / (xc ** 2).sum()
    out[np.arange(window - 1, n)[ok]] = sl[ok]
    return out


def _judge(new_col, ref, rows, scale):
    y, r = new_col[rows], ref[rows]
    fin_y, fin_r = np.isfinite(y), np.isfinite(r)
    if (fin_y & ~fin_r).any():
        return False, "new finite where ref NaN"
    both = fin_y & fin_r
    if np.any(np.abs(y[both] - r[both]) > 1e-5 * scale[rows][both]):
        return False, "value beyond 1e-5"
    fv = int(np.argmax(fin_y)) if fin_y.any() else len(y)
    if (fin_r & ~fin_y)[fv:].any():
        return False, "new NaN after first finite where ref finite"
    return True, ""


def main() -> None:
    new_p, cls_p, out_p = sys.argv[1:4]
    opts = sys.argv[4:]
    mutate_l3 = opts[opts.index("--mutate-l3") + 1] if "--mutate-l3" in opts else None
    mutate_up = opts[opts.index("--mutate-upstream") + 1] if "--mutate-upstream" in opts else None
    new = np.load(new_p + ".npz")
    meta = json.load(open(new_p + ".json"))
    cls = json.load(open(cls_p))
    rows = np.asarray(meta["public_rows"], dtype=np.int64)
    c1_full = set(cls["classes"]["C1-full"])
    d_cols = list(cls["classes"]["D"])

    # 自檢：向量化 oracle 與測試檔原版 _l3_oracle 逐格一致（抽 6 欄 × 其窗）
    l3_oracle = _test_oracle()
    checked = 0
    for c in d_cols[:: max(1, len(d_cols) // 6)][:6]:
        m = NAME_RX.match(c)
        if not m or m["stat"] == "Slope" or m["up"] not in new.files:
            continue
        up = np.asarray(new[m["up"]], dtype=np.float64)
        a, b = oracle_vec(up, int(m["w"])), l3_oracle(up, int(m["w"]))
        if not np.allclose(a, b, rtol=1e-9, atol=1e-12, equal_nan=True):
            raise RuntimeError(f"向量化 oracle 與 _l3_oracle 不一致：{c}")
        checked += 1

    overrides = {}
    if mutate_l3:
        v = np.asarray(new[mutate_l3], dtype=np.float64).copy()
        sel = rows[np.isfinite(v[rows])]
        v[sel] = v[sel] * 1.01
        overrides[mutate_l3] = v
    up_mutated = None
    if mutate_up:
        m = NAME_RX.match(mutate_up)
        w = int(m["w"])
        up = np.asarray(new[m["up"]], dtype=np.float64).copy()
        cell = int(rows[0]) - 1  # 公開起點前一格，落在第一個公開窗內
        up[cell] = up[cell] * 1.01
        up_mutated = m["up"]
        stat = m["stat"]
        overrides[mutate_up] = slope_vec(up, w) if stat == "Slope" else oracle_vec(up, w)[:, STATS.index(stat)]
        overrides[("__up__", up_mutated)] = up

    cache: dict = {}
    result = {"C2": [], "U": []}
    reasons = {}
    for c in d_cols:
        m = NAME_RX.match(c)
        if not m:
            result["U"].append(c); reasons[c] = "no reference for name"; continue
        upn, stat, w = m["up"], m["stat"], int(m["w"])
        if upn not in new.files:
            result["U"].append(c); reasons[c] = "upstream missing"; continue
        upstream_c1 = (upn in c1_full) and (upn != up_mutated)
        if not upstream_c1:
            result["U"].append(c); reasons[c] = "upstream not C1-full"; continue
        up = overrides.get(("__up__", upn), np.asarray(new[upn], dtype=np.float64))
        key = (upn, w, stat == "Slope")
        if key not in cache:
            cache[key] = slope_vec(up, w) if stat == "Slope" else oracle_vec(up, w)
        ref = cache[key] if stat == "Slope" else cache[key][:, STATS.index(stat)]
        col = overrides.get(c, np.asarray(new[c], dtype=np.float64))
        if stat == "Slope":
            scale = np.maximum(np.abs(np.nan_to_num(ref)), np.nanstd(up) * 1e-3)
        else:
            scale = np.maximum(np.abs(np.nan_to_num(ref)), 1.0)
        ok, why = _judge(col, ref, rows, scale)
        (result["C2"] if ok else result["U"]).append(c)
        if not ok:
            reasons[c] = why
    summary = {"D": len(d_cols), "C2": len(result["C2"]), "U": len(result["U"]), "oracle_selfcheck_cols": checked,
               "mutate_l3": mutate_l3, "mutate_upstream": mutate_up}
    json.dump({"summary": summary, "U_reasons": reasons, "C2": result["C2"]}, open(out_p, "w"), ensure_ascii=False)
    print(json.dumps({"summary": summary, "U_sample": dict(list(reasons.items())[:10])}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
